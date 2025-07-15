# Image Excluder

A Streamlit application for reviewing and excluding pyramid tiled TIFF images with OpenSeadragon viewer using the GeoTIFFTileSource plugin.

![showcase](showcase.gif)

## Key Features

- **🖼️ Interactive Viewer**: OpenSeadragon viewer with smooth zooming and panning for pyramid TIFFs
- **❌ Image Exclusion**: Exclude images with customizable reasons
- **🔄 Batch Operations**: Exclude or include all images on current page at once
- **📄 Smart Pagination**: 30 images per page with 5-image overlap for better context
- **📊 CSV Export**: Export excluded images list with reasons and paths
- **💾 Auto Backup**: Automatic session backup and restore functionality
- **⚡ High Performance**: Direct TIFF file access with browser-based tile generation

## Architecture

**Simplified Design:**
- **Streamlit Frontend**: User interface for image browsing and management
- **FastAPI Server**: Lightweight HTTP server for serving TIFF files with range request support
- **GeoTIFFTileSource**: Browser-based TIFF reading and tile generation

## GeoTIFF Support

Uses **GeoTIFFTileSource** plugin for efficient TIFF viewing:
- **FastAPI Server**: High-performance server with HTTP range request support
- **Cloud Optimized GeoTIFF (COG) Ready**: Works best with COG files
- **Memory Efficient**: Streams data on demand via HTTP range requests
- **CORS Enabled**: Allows browser access to TIFF files

## Dependencies

- `streamlit` - Web framework
- `fastapi` + `uvicorn` - Fast HTTP server
- `pillow` - Image processing
- `pandas` - Data export
- `pyvips` - Fast thumbnail generation

## Troubleshooting

- **Performance**: Reduce images per page if experiencing slowness
- **Images not loading**: Check directory path and TIFF file format
- **Browser compatibility**: Modern browsers required for GeoTIFFTileSource
