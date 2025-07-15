# Image Excluder

A Streamlit application for reviewing and excluding pyramid tiled TIFF images with an interactive OpenSeadragon viewer and dedicated tile server.

![showcase](showcase.gif)

## Key Features

- **🖼️ Interactive Viewer**: OpenSeadragon viewer with smooth zooming and panning for pyramid TIFFs
- **❌ Image Exclusion**: Exclude images with customizable reasons
- **🔄 Batch Operations**: Exclude or include all images on current page at once
- **📄 Smart Pagination**: 30 images per page with 5-image overlap for better context
- **📊 CSV Export**: Export excluded images list with reasons and paths
- **💾 Auto Backup**: Automatic session backup and restore functionality
- **⚡ High Performance**: Dedicated Flask tile server for efficient pyramid TIFF handling

## Architecture

- **Tile Server** (Flask): Serves pyramid TIFF tiles at `http://localhost:5000`
- **Web Interface** (Streamlit): Main UI at `http://localhost:8501`

## Quick Start

```bash
# Install dependencies
uv sync

# Run application
./run.sh
```

Access the app at `http://localhost:8501`

## Usage

1. **Load Images**: Enter directory path and click "🔍 Load Images"
2. **Review**: Use OpenSeadragon viewer to zoom/pan through images
3. **Exclude**: Select exclusion reason from dropdown to exclude images
4. **Batch Operations**: Use batch exclude/include for entire pages
5. **Export**: Download excluded images list as CSV

## Supported Formats

- **Primary**: `.tif`, `.tiff` (pyramid tiled TIFFs)
- **Basic**: `.jpg`, `.jpeg`, `.png`

## Technical Details

- **Pagination**: 30 images/page with 5-image overlap for context continuity
- **Performance**: Direct pyramid tile access, efficient caching
- **Export Format**: CSV with image stems, exclusion reasons, and full paths
- **Backup**: Automatic session backups in `/backups` directory

## Dependencies

- `streamlit` - Web framework
- `flask` + `flask-cors` - Tile server
- `pillow` - Image processing
- `pandas` - Data export
- `tifffile` - Pyramid TIFF reading
- `requests` - HTTP communication

## Troubleshooting

- **Port Issues**: Ensure ports 5000 and 8501 are available
- **Performance**: Reduce images per page if experiencing slowness
- **Images not loading**: Check directory path and TIFF file format
