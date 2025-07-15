# Image Ex- **🔄 Batch Operations**: Exclude or include all images on current page at once
- **📄 Pagination**: Navigate through large collections with overlapping pages (5 image overlap for better context)
- **⚙️ Exclusion Management**: Add custom exclusion reasons and manage excluded imagesder

A Streamlit application for reviewing and excluding pyramid tiled TIFF images with an interactive OpenSeadragon viewer and dedicated tile server.

## Features

- **🔍 Fast Tile Server**: Dedicated Flask server for serving pyramid TIFF tiles efficiently
- **📁 Directory Browser**: Load TIFF images from any directory
- **🖼️ Interactive Viewer**: OpenSeadragon viewer with smooth zooming and panning
- **❌ Image Exclusion**: Click to exclude images with customizable reasons
- **� Batch Operations**: Exclude or include all images on current page at once
- **�📄 Pagination**: Navigate through large collections of images
- **⚙️ Exclusion Management**: Add custom exclusion reasons and manage excluded images
- **📊 CSV Export**: Export excluded images list with stems and reasons
- **💾 Backup & Restore**: Automatic and manual backup functionality
- **⚡ Performance**: Optimized for large pyramid TIFF files

## Architecture

The application consists of two components:
1. **Tile Server** (Flask): Serves pyramid TIFF tiles at `http://localhost:5000`
2. **Web Interface** (Streamlit): Main UI at `http://localhost:8501`

## Installation

This project uses `uv` for dependency management. Make sure you have `uv` installed.

1. Clone or download this project
2. Navigate to the project directory
3. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

### Quick Start
```bash
./run.sh
```

### Manual Start
1. Start the application:
   ```bash
   uv run streamlit run app.py
   ```
   The tile server will start automatically.

2. Open your browser to `http://localhost:8501`

3. In the sidebar:
   - Enter the path to your directory containing TIFF images
   - Click "🔍 Load Images" to scan the directory
   - Adjust "Images per page" as needed

4. Review images:
   - Use the OpenSeadragon viewer to zoom and pan each image
   - Simply select an exclusion reason from the dropdown to automatically exclude an image
   - Use batch operations to exclude or include all images on the current page at once
   - Use "Previous" and "Next" buttons to navigate through pages

5. Manage exclusions:
   - Add custom exclusion reasons in the sidebar
   - View excluded images count and breakdown
   - Remove images from exclusion if needed
   - Export the excluded images list as CSV

## Batch Operations

The app now supports batch operations for efficient image management:

### 🔄 Batch Exclusion
- **Exclude All Images on Page**: Select a reason and exclude all non-excluded images on the current page with one click
- **Include All Images on Page**: Remove all excluded images on the current page from the exclusion list

### Page Status Display
- Shows the total number of images on the current page
- Displays count of included vs excluded images
- Real-time updates as you make changes

### Smart Controls
- Batch exclude button is disabled until you select a reason
- Shows helpful messages when all images are already excluded/included
- Automatic backup after batch operations

## Pagination with Overlap

The app features intelligent pagination designed for efficient image review:

### 📄 Page Overlap Feature
- **Default**: 30 images per page with 5 image overlap between consecutive pages
- **Context Preservation**: The last 5 images from the previous page appear as the first 5 images on the next page
- **Better Review Flow**: Overlap helps maintain context when reviewing similar images
- **Visual Indicator**: Pages show overlap information when applicable

### Benefits
- **Reduced Missed Images**: Overlap ensures images at page boundaries get proper attention
- **Context Continuity**: Seeing images from the previous page helps with consistent decision-making
- **Flexible Navigation**: Still allows jumping between pages while maintaining context

## Supported Image Formats

- `.tif`, `.tiff` (case insensitive) - Primary focus on pyramid tiled TIFFs
- `.jpg`, `.jpeg`, `.png` (case insensitive) - Basic support

## Performance Features

- **Pyramid Tile Serving**: Direct access to TIFF pyramid levels for fast loading
- **Efficient Caching**: Tile server caches opened TIFF files
- **Thumbnail Fallback**: Fast thumbnail generation if tile server fails
- **Background Processing**: Tile server runs independently from UI

## CSV Export Format

The exported CSV contains:
- `image_stem`: Filename without extension
- `exclusion_reason`: Reason for exclusion
- `full_path`: Complete file path

## Dependencies

- `streamlit`: Web application framework
- `flask` + `flask-cors`: Tile server
- `pillow`: Image processing
- `pandas`: Data manipulation and CSV export
- `tifffile`: Pyramid TIFF reading
- `requests`: HTTP communication

## Project Structure

```
image-excluder/
├── app.py              # Main Streamlit application
├── tile_server.py      # Flask tile server for pyramid TIFFs
├── config.py           # Configuration settings
├── run.sh              # Startup script
├── pyproject.toml      # Project configuration
├── README.md           # This file
└── .venv/              # Virtual environment (created by uv)
```

## Tips

- **Large Files**: The tile server efficiently handles multi-gigabyte pyramid TIFFs
- **Network Issues**: If tile server fails, the app falls back to thumbnail display
- **Performance**: Reduce "Images per page" if experiencing slowness
- **Memory**: The tile server uses minimal memory by streaming tiles on demand

## Troubleshooting

- **Tile Server Issues**: Check that port 5000 is available
- **Images not loading**: Ensure directory path is correct and contains TIFF files
- **Black images**: The tile server may need a moment to start - wait and refresh
- **Performance issues**: Reduce "Images per page" or check available memory
- **Port conflicts**: Modify `TILE_SERVER_PORT` in `app.py` if port 5000 is in use

## Technical Details

The tile server:
- Serves DZI (Deep Zoom Images) format for OpenSeadragon
- Extracts tiles directly from TIFF pyramid levels
- Handles different bit depths and color spaces
- Provides CORS headers for cross-origin requests
- Includes error handling and fallback mechanisms
