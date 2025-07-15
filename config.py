# Configuration for Image Excluder

# Default settings
DEFAULT_IMAGES_PER_PAGE = 15  # Show 15 images per page
PAGE_OVERLAP = 5  # Overlap 5 images between consecutive pages
THUMBNAIL_SIZE = (400, 400)  # Increased for better quality
SUPPORTED_EXTENSIONS = ['.tif', '.tiff', '.TIF', '.TIFF', '.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']

# Default exclusion reasons
DEFAULT_EXCLUSION_REASONS = [
    "grid",
    "little or no tissue",
    "scanning artifact",
    "partially scanned",
    "non-representative tissue",
    "different depth available",
]

# OpenSeadragon viewer settings
VIEWER_HEIGHT = 350  # Reduced for better performance
SHOW_NAVIGATION_CONTROL = True
SHOW_ZOOM_CONTROL = True
SHOW_HOME_CONTROL = True
SHOW_FULLPAGE_CONTROL = False
