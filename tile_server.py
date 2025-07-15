"""
Tile server for serving pyramid TIFF tiles to OpenSeadragon using rasterio
"""
import os
import json
from flask import Flask, Response, jsonify
from flask_cors import CORS
import rasterio
from rasterio.enums import Resampling
import numpy as np
from PIL import Image
import io
import threading
import time
import math

app = Flask(__name__)
CORS(app)

# Global cache for rasterio datasets
raster_cache = {}
cache_lock = threading.Lock()

def get_raster_info(filepath):
    """Get pyramid information from raster file using rasterio"""
    try:
        with rasterio.open(filepath) as dataset:
            # Get basic info
            width = dataset.width
            height = dataset.height
            
            # Check for overviews (pyramid levels)
            overview_count = dataset.overviews(1) if dataset.count > 0 else []
            
            # Calculate max DZI level properly - DZI level is the number of times
            # we can halve the larger dimension until it's <= tile_size
            max_dimension = max(width, height)
            max_level = 0
            temp_size = max_dimension
            while temp_size > 256:  # tile_size
                temp_size = temp_size // 2
                max_level += 1
            
            print(f"Raster info: {width}x{height}, max DZI level: {max_level}, overviews: {overview_count}")
            
            return {
                'width': width,
                'height': height,
                'levels': max_level + 1,  # +1 because level 0 is included
                'tile_size': 256,
                'overviews': overview_count
            }
    except Exception as e:
        print(f"Error getting raster info: {e}")
        return None

def get_tile_rasterio(filepath, level, x, y, tile_size=256):
    """Extract tile from pyramid raster using rasterio"""
    try:
        cache_key = f"{filepath}"
        
        with cache_lock:
            if cache_key not in raster_cache:
                try:
                    raster_cache[cache_key] = rasterio.open(filepath)
                    print(f"Cached rasterio dataset: {filepath}")
                except Exception as e:
                    print(f"Error opening raster file {filepath}: {e}")
                    return None
        
        dataset = raster_cache[cache_key]
        
        # Get overview levels
        overviews = dataset.overviews(1) if dataset.count > 0 else []
        
        print(f"Request: level={level}, x={x}, y={y}")
        print(f"Available overviews: {overviews}")
        
        # Calculate the image dimensions at the requested DZI level
        # DZI level 0 = highest resolution (base image), higher levels = lower resolution
        base_width = dataset.width
        base_height = dataset.height
        
        # Calculate max DZI level based on image size  
        max_dimension = max(base_width, base_height)
        max_level = 0
        temp_size = max_dimension
        while temp_size > tile_size:
            temp_size = temp_size // 2
            max_level += 1
        
        print(f"Base size: {base_width}x{base_height}, Max DZI level: {max_level}")
        
        # DZI level mapping (CORRECTED):
        # Level 0 = LOWEST resolution (most zoomed out)
        # Higher levels = HIGHER resolution (more zoomed in)  
        # Max level = base image (highest resolution, most zoomed in)
        
        # Calculate which resolution level this DZI level represents
        levels_from_top = max_level - level  # How many levels down from the top
        
        print(f"DZI level {level}, max_level {max_level}, levels_from_top {levels_from_top}")
        
        if level >= max_level:
            # OpenSeadragon is requesting a level at or above our max level
            # This means it wants the highest resolution (base image)
            # BUT we need to scale the tile coordinates to match the expected zoom level
            overview_level = -1
            scale_factor = 1.0
            
            # Calculate the effective scale factor for this level
            # Level 12 means the image should appear 2^(12-6) = 2^6 = 64 times larger than level 6
            zoom_scale = 2 ** (level - max_level)
            print(f"Using base image for DZI level {level} (>= max_level {max_level}), zoom_scale: {zoom_scale}")
        elif levels_from_top <= 0:
            # This is also the highest level (base image)
            overview_level = -1
            scale_factor = 1.0
            zoom_scale = 1.0
            print(f"Using base image for DZI level {level}")
        else:
            # Calculate target resolution for this DZI level
            target_scale = 1.0 / (2 ** levels_from_top)
            target_width = int(base_width * target_scale)
            zoom_scale = 1.0
            
            print(f"DZI level {level} (levels from top: {levels_from_top}): target scale={target_scale:.4f}, target width={target_width}")
            
            # Find the best overview level that provides this resolution
            # We want the overview that most closely matches our target resolution
            overview_level = -1  # Default to base image
            best_match_diff = float('inf')
            
            for i, overview_factor in enumerate(overviews):
                overview_width = base_width // overview_factor
                width_diff = abs(overview_width - target_width)
                print(f"  Overview {i} (factor {overview_factor}): width={overview_width}, diff from target={width_diff}")
                
                # Use this overview if it's the closest match so far
                # and the overview resolution is not higher than needed
                if width_diff < best_match_diff and overview_width <= target_width * 1.5:
                    overview_level = i
                    best_match_diff = width_diff
                    scale_factor = overview_width / base_width
            
            # If no suitable overview found, use base image
            if overview_level == -1:
                scale_factor = 1.0
                print("No suitable overview found, using base image")
            else:
                print(f"Selected overview {overview_level} with scale factor {scale_factor:.4f}")
        
        print(f"Scale factor: {scale_factor:.4f}, using overview level: {overview_level}, zoom_scale: {zoom_scale}")
        
        # Get the actual dimensions at this overview level
        if overview_level == -1:
            # Use base image
            actual_width = base_width
            actual_height = base_height
        else:
            # Use overview
            overview_factor = overviews[overview_level]
            actual_width = base_width // overview_factor
            actual_height = base_height // overview_factor
        
        print(f"Actual image size at this level: {actual_width}x{actual_height}")
        
        # Calculate tile boundaries - need to account for zoom scale
        # When zoom_scale > 1, we're zoomed in beyond the native resolution
        # Instead of making effective_tile_size smaller, we should keep tile_size the same
        # and adjust the coordinates to show the appropriate part of the image
        
        if zoom_scale > 1:
            # We're beyond the native resolution - tile coordinates need to be scaled up
            # to map to the base image coordinate system
            tile_left = x * tile_size
            tile_top = y * tile_size  
            tile_right = min(tile_left + tile_size, actual_width)
            tile_bottom = min(tile_top + tile_size, actual_height)
            print(f"Zoom scale: {zoom_scale} (beyond native), using full tile_size")
        else:
            # Normal case - within native resolution
            effective_tile_size = int(tile_size / zoom_scale) if zoom_scale > 0 else tile_size
            tile_left = x * effective_tile_size
            tile_top = y * effective_tile_size
            tile_right = min(tile_left + effective_tile_size, actual_width)
            tile_bottom = min(tile_top + effective_tile_size, actual_height)
            print(f"Zoom scale: {zoom_scale}, effective tile size: {effective_tile_size}")
        
        print(f"Tile coordinates: x={x}, y={y} -> [{tile_left}, {tile_top}, {tile_right}, {tile_bottom}]")
        
        # Check bounds
        if tile_left >= actual_width or tile_top >= actual_height:
            print(f"Tile out of bounds: {tile_left},{tile_top} vs {actual_width}x{actual_height}")
            return None
        
        print(f"Tile bounds: [{tile_top}:{tile_bottom}, {tile_left}:{tile_right}] from {actual_width}x{actual_height}")
        
        # Calculate the window in the original image coordinates
        if overview_level == -1:
            # Base image coordinates
            window_left = tile_left
            window_top = tile_top
            window_right = tile_right
            window_bottom = tile_bottom
        else:
            # Scale up to base image coordinates
            overview_factor = overviews[overview_level]
            window_left = tile_left * overview_factor
            window_top = tile_top * overview_factor
            window_right = tile_right * overview_factor
            window_bottom = tile_bottom * overview_factor
        
        # Create rasterio window - use basic coordinates
        # Window(col_off, row_off, width, height)
        window_width = window_right - window_left
        window_height = window_bottom - window_top
        
        print(f"Window: col_off={window_left}, row_off={window_top}, width={window_width}, height={window_height}")
        
        # Read the tile data
        try:
            if overview_level == -1:
                # Read from base image
                tile_data = dataset.read(
                    indexes=[1] if dataset.count == 1 else [1, 2, 3] if dataset.count >= 3 else list(range(1, min(4, dataset.count + 1))),
                    window=((window_top, window_bottom), (window_left, window_right)),
                    out_shape=(len([1] if dataset.count == 1 else [1, 2, 3] if dataset.count >= 3 else list(range(1, min(4, dataset.count + 1)))), tile_size, tile_size),
                    resampling=Resampling.nearest
                )
            else:
                # Read from specific overview
                # For overviews, we need to read at the overview's resolution and then scale the window
                overview_factor = overviews[overview_level]
                
                # Calculate window in overview coordinates
                overview_window_left = window_left // overview_factor
                overview_window_top = window_top // overview_factor
                overview_window_right = window_right // overview_factor
                overview_window_bottom = window_bottom // overview_factor
                
                print(f"Overview window: [{overview_window_top}:{overview_window_bottom}, {overview_window_left}:{overview_window_right}]")
                
                # Read from the overview
                tile_data = dataset.read(
                    indexes=[1] if dataset.count == 1 else [1, 2, 3] if dataset.count >= 3 else list(range(1, min(4, dataset.count + 1))),
                    window=((overview_window_top, overview_window_bottom), (overview_window_left, overview_window_right)),
                    out_shape=(len([1] if dataset.count == 1 else [1, 2, 3] if dataset.count >= 3 else list(range(1, min(4, dataset.count + 1)))), tile_size, tile_size),
                    resampling=Resampling.nearest,
                    overview_level=overview_level + 1  # rasterio uses 1-based indexing for overviews
                )
            
            print(f"Read tile data shape: {tile_data.shape}")
            
            # Handle different numbers of bands
            if tile_data.shape[0] == 1:
                # Grayscale - duplicate to 3 channels
                tile_data = np.stack([tile_data[0], tile_data[0], tile_data[0]], axis=0)
            elif tile_data.shape[0] == 2:
                # Two bands - add a third
                tile_data = np.stack([tile_data[0], tile_data[1], tile_data[0]], axis=0)
            elif tile_data.shape[0] > 3:
                # Take first 3 bands
                tile_data = tile_data[:3]
            
            # Convert from CHW to HWC format
            tile_data = np.transpose(tile_data, (1, 2, 0))
            
        except Exception as e:
            print(f"Error reading tile data: {e}")
            return None
        
        if tile_data.size == 0:
            print("Empty tile data")
            return None
        
        print(f"Read tile shape: {tile_data.shape}")
        
        # Normalize to 0-255 if needed
        if tile_data.dtype != np.uint8:
            if tile_data.max() > 1:
                tile_data = (tile_data / tile_data.max() * 255).astype(np.uint8)
            else:
                tile_data = (tile_data * 255).astype(np.uint8)
        
        # Create PIL Image
        img = Image.fromarray(tile_data)
        
        # Ensure RGB mode
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to exact tile size if needed
        if img.size != (tile_size, tile_size):
            # Resize to tile_size
            img = img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
        
        print(f"Returning tile of size: {img.size}")
        return img
        
    except Exception as e:
        print(f"Error getting tile: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/info/<path:filepath>')
def get_info(filepath):
    """Get image info for DZI format"""
    try:
        # Decode the filepath
        filepath = filepath.replace('__SLASH__', '/')
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        info = get_raster_info(filepath)
        if not info:
            return jsonify({'error': 'Could not read raster info'}), 500
        
        # Return DZI-style info
        dzi_info = {
            'Image': {
                'Format': 'jpg',
                'Overlap': '0',
                'TileSize': str(info['tile_size']),
                'Size': {
                    'Width': str(info['width']),
                    'Height': str(info['height'])
                }
            }
        }
        
        response = Response(
            json.dumps(dzi_info),
            mimetype='application/json'
        )
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tile/<path:filepath>/<int:level>/<int:x>_<int:y>.jpg')
def get_tile_endpoint(filepath, level, x, y):
    """Get a specific tile"""
    try:
        # Decode the filepath
        filepath = filepath.replace('__SLASH__', '/')
        
        if not os.path.exists(filepath):
            return Response('File not found', status=404)
        
        tile = get_tile_rasterio(filepath, level, x, y)
        if tile is None:
            return Response('Tile not found', status=404)
        
        # Convert to JPEG
        img_io = io.BytesIO()
        tile.save(img_io, 'JPEG', quality=85, optimize=True)
        img_io.seek(0)
        
        response = Response(img_io.getvalue(), mimetype='image/jpeg')
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
        
    except Exception as e:
        print(f"Error serving tile: {e}")
        return Response('Error serving tile', status=500)

@app.route('/dzi/<path:filepath>_files/<int:level>/<int:x>_<int:y>.jpg')
def get_dzi_tile(filepath, level, x, y):
    """Get a DZI-format tile (OpenSeadragon expects this pattern)"""
    print(f"=== DZI TILE REQUEST: level={level}, x={x}, y={y} ===")
    try:
        # Decode the filepath
        filepath = filepath.replace('__SLASH__', '/')
        
        if not os.path.exists(filepath):
            return Response('File not found', status=404)
        
        tile = get_tile_rasterio(filepath, level, x, y)
        if tile is None:
            return Response('Tile not found', status=404)
        
        # Convert to JPEG
        img_io = io.BytesIO()
        tile.save(img_io, 'JPEG', quality=85, optimize=True)
        img_io.seek(0)
        
        response = Response(img_io.getvalue(), mimetype='image/jpeg')
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
        
    except Exception as e:
        print(f"Error serving DZI tile: {e}")
        return Response('Error serving tile', status=500)

@app.route('/dzi/<path:filepath>')
def get_dzi(filepath):
    """Get DZI file for OpenSeadragon"""
    try:
        # Decode the filepath
        filepath = filepath.replace('__SLASH__', '/')
        
        if not os.path.exists(filepath):
            return Response('File not found', status=404)
        
        info = get_raster_info(filepath)
        if not info:
            return Response('Could not read raster info', status=500)
        
        # Create DZI XML with proper level structure
        dzi_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008"
       Format="jpg"
       Overlap="0"
       TileSize="{info['tile_size']}">
    <Size Width="{info['width']}" Height="{info['height']}"/>
</Image>'''
        
        response = Response(dzi_xml, mimetype='application/xml')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        return Response(f'Error: {str(e)}', status=500)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': time.time()})

def cleanup_cache():
    """Cleanup raster cache periodically"""
    with cache_lock:
        for raster in raster_cache.values():
            try:
                raster.close()
            except Exception:
                pass
        raster_cache.clear()

if __name__ == '__main__':
    import atexit
    atexit.register(cleanup_cache)
    
    port = int(os.environ.get('TILE_SERVER_PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
