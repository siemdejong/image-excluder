import streamlit as st
import pandas as pd
import os
from pathlib import Path
from PIL import Image
import subprocess
import threading
import time
import requests
import pyvips
import io
import json
from datetime import datetime
from config import (
    DEFAULT_IMAGES_PER_PAGE, 
    PAGE_OVERLAP,
    THUMBNAIL_SIZE, 
    SUPPORTED_EXTENSIONS,
    DEFAULT_EXCLUSION_REASONS
)

# Tile server configuration
TILE_SERVER_PORT = 5000
TILE_SERVER_URL = f"http://127.0.0.1:{TILE_SERVER_PORT}"

# Backup configuration
BACKUP_DIR = Path("backups")
AUTO_BACKUP_INTERVAL = 300  # 5 minutes in seconds

# Configure page
st.set_page_config(
    page_title="Image Excluder",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def ensure_backup_dir():
    """Ensure backup directory exists"""
    BACKUP_DIR.mkdir(exist_ok=True)

def save_backup(filename=None):
    """Save current session state to a backup file"""
    try:
        ensure_backup_dir()
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_backup_{timestamp}.json"
        
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "excluded_images": st.session_state.excluded_images,
            "current_page": st.session_state.current_page,
            "images_per_page": st.session_state.images_per_page,
            "image_files": st.session_state.image_files,
            "exclusion_reasons": st.session_state.exclusion_reasons,
            "use_thumbnail_view": st.session_state.use_thumbnail_view,
            "total_images": len(st.session_state.image_files),
            "excluded_count": len(st.session_state.excluded_images)
        }
        
        backup_path = BACKUP_DIR / filename
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        return backup_path
    except Exception as e:
        st.error(f"Failed to save backup: {e}")
        return None

def load_backup(backup_path):
    """Load session state from a backup file"""
    try:
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        # Restore session state
        st.session_state.excluded_images = backup_data.get("excluded_images", {})
        st.session_state.current_page = backup_data.get("current_page", 0)
        st.session_state.images_per_page = backup_data.get("images_per_page", DEFAULT_IMAGES_PER_PAGE)
        st.session_state.image_files = backup_data.get("image_files", [])
        st.session_state.exclusion_reasons = backup_data.get("exclusion_reasons", DEFAULT_EXCLUSION_REASONS.copy())
        st.session_state.use_thumbnail_view = backup_data.get("use_thumbnail_view", False)
        
        return True
    except Exception as e:
        st.error(f"Failed to load backup: {e}")
        return False

def get_backup_files():
    """Get list of available backup files"""
    ensure_backup_dir()
    backup_files = list(BACKUP_DIR.glob("*.json"))
    return sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True)

def auto_backup():
    """Automatically save backup if conditions are met"""
    current_time = time.time()
    
    # Initialize last backup time if not exists
    if 'last_backup_time' not in st.session_state:
        st.session_state.last_backup_time = current_time
    
    # Check if it's time for auto backup
    if (current_time - st.session_state.last_backup_time >= AUTO_BACKUP_INTERVAL and 
        st.session_state.excluded_images):  # Only backup if there are exclusions
        
        backup_path = save_backup()
        if backup_path:
            st.session_state.last_backup_time = current_time
            # Show a brief success message
            with st.sidebar:
                st.success(f"🔄 Auto-backup saved: {backup_path.name}")

def load_latest_backup_on_startup():
    """Load the most recent backup on startup"""
    if 'backup_loaded_on_startup' not in st.session_state:
        backup_files = get_backup_files()
        if backup_files and not st.session_state.excluded_images:  # Only auto-load if no current data
            latest_backup = backup_files[0]
            if load_backup(latest_backup):
                st.success(f"🔄 Auto-restored from backup: {latest_backup.name}")
        st.session_state.backup_loaded_on_startup = True

def start_tile_server():
    """Start the tile server in the background"""
    if 'tile_server_started' not in st.session_state:
        try:
            # Check if server is already running
            response = requests.get(f"{TILE_SERVER_URL}/health", timeout=1)
            if response.status_code == 200:
                st.session_state.tile_server_started = True
                return True
        except Exception:
            pass
        
        # Start the tile server
        try:
            def run_server():
                subprocess.run([
                    "uv", "run", "python", "tile_server.py"
                ], cwd=os.getcwd(), capture_output=True)
            
            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()
            
            # Wait for server to start
            for _ in range(10):  # Wait up to 10 seconds
                try:
                    response = requests.get(f"{TILE_SERVER_URL}/health", timeout=1)
                    if response.status_code == 200:
                        st.session_state.tile_server_started = True
                        return True
                except Exception:
                    time.sleep(1)
            
            return False
        except Exception as e:
            st.error(f"Failed to start tile server: {e}")
            return False
    return True

def encode_filepath(filepath):
    """Encode filepath for URL"""
    return filepath.replace('/', '__SLASH__')

def create_openseadragon_viewer(image_path, container_id, height=350):
    """Create OpenSeadragon viewer with DZI source"""
    encoded_path = encode_filepath(image_path)
    dzi_url = f"{TILE_SERVER_URL}/dzi/{encoded_path}"
    
    viewer_html = f"""
    <div id="{container_id}" style="width: 100%; height: {height}px; border: 2px solid #ddd; border-radius: 8px; background: #f8f9fa;"></div>
    <script src="https://cdn.jsdelivr.net/npm/openseadragon@4.1.0/build/openseadragon/openseadragon.min.js"></script>
    <script>
        if (typeof OpenSeadragon !== 'undefined') {{
            try {{
                var viewer_{container_id} = OpenSeadragon({{
                    id: "{container_id}",
                    prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@4.1.0/build/openseadragon/images/",
                    tileSources: "{dzi_url}",
                    showNavigationControl: true,
                    showZoomControl: true,
                    showHomeControl: true,
                    showFullPageControl: false,
                    gestureSettingsMouse: {{
                        clickToZoom: false,
                        dblClickToZoom: true
                    }},
                    zoomInButton: "zoom-in",
                    zoomOutButton: "zoom-out", 
                    homeButton: "home",
                    immediateRender: true,
                    blendTime: 0.1,
                    animationTime: 0.5,
                    springStiffness: 10.0,
                    visibilityRatio: 0.5,
                    minZoomLevel: 0.1,
                    maxZoomLevel: 20,
                    constrainDuringPan: true,
                    wrapHorizontal: false,
                    wrapVertical: false
                }});
                
                // Add error handling
                viewer_{container_id}.addHandler('open-failed', function(event) {{
                    document.getElementById("{container_id}").innerHTML = 
                        '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666; font-size: 14px;">Failed to load image</div>';
                }});
                
            }} catch (error) {{
                console.error('OpenSeadragon error:', error);
                document.getElementById("{container_id}").innerHTML = 
                    '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666; font-size: 14px;">Error loading viewer</div>';
            }}
        }} else {{
            document.getElementById("{container_id}").innerHTML = 
                '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666; font-size: 14px;">OpenSeadragon not loaded</div>';
        }}
    </script>
    """
    return viewer_html

def create_thumbnail(image_path):
    """Create a simple thumbnail for fallback display"""
    try:
        with Image.open(image_path) as img:
            # For pyramid TIFFs, try to get a smaller level
            if hasattr(img, 'n_frames') and img.n_frames > 1:
                img.seek(min(img.n_frames - 1, 3))  # Use a smaller level
            
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            return img
    except Exception as e:
        st.error(f"Error creating thumbnail for {image_path}: {e}")
        return None

def create_pyvips_thumbnail(image_path, max_size=800):
    """Create a thumbnail using pyvips for better handling of pyramid TIFFs"""
    try:
        # Load image with pyvips
        image = pyvips.Image.new_from_file(image_path, access='sequential')
        max_page = image.get_n_pages() - 4
        image = pyvips.Image.new_from_file(image_path, access='sequential', page=max_page)
        
        # Calculate scaling factor to fit within max_size while maintaining aspect ratio
        scale = min(max_size / image.width, max_size / image.height)
        
        if scale < 1.0:
            # Resize the image
            thumbnail = image.resize(scale)
        else:
            thumbnail = image
        
        # Convert to RGB if needed and export as JPEG for display
        if thumbnail.bands == 4:  # RGBA
            thumbnail = thumbnail.flatten(background=[255, 255, 255])
        elif thumbnail.bands == 1:  # Grayscale
            thumbnail = thumbnail.colourspace('srgb')
        
        # Convert to PIL Image for Streamlit
        buffer = thumbnail.jpegsave_buffer(Q=85)
        return Image.open(io.BytesIO(buffer))
        
    except Exception as e:
        st.error(f"Error creating pyvips thumbnail for {image_path}: {e}")
        # Fallback to PIL thumbnail
        return create_thumbnail(image_path)

def load_image_files(directory: str) -> list:
    """Load all supported image files from the directory."""
    if not directory or not os.path.exists(directory):
        return []
    
    image_files = []
    for ext in SUPPORTED_EXTENSIONS:
        pattern = f"*{ext}"
        image_files.extend(Path(directory).glob(pattern))
    
    return sorted([str(f) for f in image_files])

def export_excluded_images():
    """Export excluded images to CSV."""
    if not st.session_state.excluded_images:
        st.warning("No excluded images to export.")
        return
    
    # Create DataFrame
    data = []
    for filepath, reason in st.session_state.excluded_images.items():
        stem = Path(filepath).stem
        data.append({"image_stem": stem, "exclusion_reason": reason, "full_path": filepath})
    
    df = pd.DataFrame(data)
    
    # Convert to CSV
    csv = df.to_csv(index=False)
    
    # Create download button
    st.download_button(
        label="📥 Download Excluded Images CSV",
        data=csv,
        file_name=f"excluded_images_{int(time.time())}.csv",
        mime="text/csv",
        type="primary"
    )

@st.fragment
def render_batch_operations(current_images):
    """Render batch operations section - using fragment for performance"""
    # Get images on current page that are not excluded
    non_excluded_current = [img for img in current_images if img not in st.session_state.excluded_images]
    excluded_current = [img for img in current_images if img in st.session_state.excluded_images]
    
    # Batch exclusion controls
    st.markdown("---")
    st.subheader("🔄 Batch Operations for Current Page")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if non_excluded_current:
            batch_reason = st.selectbox(
                "Reason for batch exclusion:",
                ["Select reason..."] + st.session_state.exclusion_reasons,
                key="batch_exclude_reason"
            )
            
            if st.button(f"🚫 Exclude All {len(non_excluded_current)} Images on Page", 
                        type="primary", 
                        disabled=(batch_reason == "Select reason...")):
                if batch_reason != "Select reason...":
                    for image_path in non_excluded_current:
                        st.session_state.excluded_images[image_path] = batch_reason
                    
                    # Trigger backup after batch operation
                    save_backup()
                    st.success(f"✅ Excluded {len(non_excluded_current)} images with reason: {batch_reason}")
                    # Rerun the entire app for batch operations to update all fragments
                    st.rerun()
        else:
            st.info("All images on this page are already excluded")
    
    with col2:
        if excluded_current:
            if st.button(f"✅ Include All {len(excluded_current)} Images on Page", 
                        type="secondary"):
                for image_path in excluded_current:
                    del st.session_state.excluded_images[image_path]
                
                # Trigger backup after batch operation
                save_backup()
                st.success(f"✅ Included {len(excluded_current)} images back")
                # Rerun the entire app for batch operations to update all fragments
                st.rerun()
        else:
            st.info("No excluded images on this page")
    
    with col3:
        st.write("**Page Status:**")
        st.write(f"📄 Total on page: {len(current_images)}")
        st.write(f"✅ Included: {len(non_excluded_current)}")
        st.write(f"🚫 Excluded: {len(excluded_current)}")
    
    st.markdown("---")

@st.fragment
def render_image_card(image_path, image_name, container_id, cols_per_row):
    """Render a single image card with exclusion controls - using fragment for performance"""
    # Image header
    is_excluded = image_path in st.session_state.excluded_images
    
    if is_excluded:
        st.markdown(f"**🚫 {image_name}**")
        st.error(f"Excluded: {st.session_state.excluded_images[image_path]}")
    else:
        st.markdown(f"**✅ {image_name}**")
    
    # Display image based on selected viewer type
    if st.session_state.use_thumbnail_view:
        # Use pyvips thumbnail view
        thumbnail = create_pyvips_thumbnail(image_path)
        if thumbnail:
            st.image(thumbnail, caption=image_name, use_container_width=True)
        else:
            st.error("Failed to load image thumbnail")
    else:
        # Use OpenSeadragon viewer with adaptive height based on grid size
        viewer_height = 300 if cols_per_row >= 5 else 400
        try:
            viewer_html = create_openseadragon_viewer(image_path, container_id, viewer_height)
            st.components.v1.html(viewer_html, height=viewer_height + 50)
        except Exception as e:
            st.error(f"Failed to create viewer: {e}")
            # Fallback to thumbnail
            thumbnail = create_thumbnail(image_path)
            if thumbnail:
                st.image(thumbnail, caption=image_name, use_container_width=True)
            else:
                st.error("Failed to load image")
    
    # Exclusion controls
    if is_excluded:
        if st.button("✅ Include", key=f"include_{image_path}", type="secondary"):
            del st.session_state.excluded_images[image_path]
            # Trigger immediate backup on state change
            if len(st.session_state.excluded_images) % 5 == 0:  # Backup every 5 changes
                save_backup()
            st.rerun(scope="fragment")
    else:
        # Reason selection and automatic exclusion
        reason_key = f"reason_{image_path}"
        reason = st.selectbox(
            "Select reason to exclude:",
            ["Select reason..."] + st.session_state.exclusion_reasons,
            key=reason_key
        )
        
        # Automatically exclude when a reason is selected
        if reason != "Select reason...":
            st.session_state.excluded_images[image_path] = reason
            # Trigger immediate backup on state change
            if len(st.session_state.excluded_images) % 5 == 0:  # Backup every 5 changes
                save_backup()
            st.rerun(scope="fragment")

# Initialize session state
if 'excluded_images' not in st.session_state:
    st.session_state.excluded_images = {}  # {filepath: reason}
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'images_per_page' not in st.session_state:
    st.session_state.images_per_page = DEFAULT_IMAGES_PER_PAGE
if 'image_files' not in st.session_state:
    st.session_state.image_files = []
if 'exclusion_reasons' not in st.session_state:
    st.session_state.exclusion_reasons = DEFAULT_EXCLUSION_REASONS.copy()
if 'use_thumbnail_view' not in st.session_state:
    st.session_state.use_thumbnail_view = False
if 'last_backup_time' not in st.session_state:
    st.session_state.last_backup_time = time.time()
if 'backup_loaded_on_startup' not in st.session_state:
    st.session_state.backup_loaded_on_startup = False

# Main app
def main():
    st.title("🖼️ Image Excluder")
    st.markdown("Select pyramid tiled TIFF images to exclude from your dataset with OpenSeadragon viewer or thumbnail view")
    
    # Load latest backup on startup
    load_latest_backup_on_startup()
    
    # Auto backup
    auto_backup()
    
    # Start tile server
    if not start_tile_server():
        st.error("❌ Failed to start tile server. Please restart the application.")
        return
    else:
        st.success("✅ Tile server is running")
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Directory Selection")
        
        directory = st.text_input(
            "Image Directory Path",
            value="",
            help="Enter the path to the directory containing TIFF images"
        )
        
        if st.button("🔍 Load Images", type="primary") and directory:
            if os.path.exists(directory):
                st.session_state.image_files = load_image_files(directory)
                st.session_state.current_page = 0
                st.success(f"✅ Loaded {len(st.session_state.image_files)} images")
            else:
                st.error("❌ Directory not found!")
        
        st.header("⚙️ Settings")
        st.session_state.images_per_page = st.selectbox(
            "Images per page",
            [15, 30, 45, 60],
            index=1,
            help=f"Number of images to display per page (with {PAGE_OVERLAP} image overlap between pages)"
        )
        
        # Viewer type selection
        st.session_state.use_thumbnail_view = st.toggle(
            "🖼️ Use thumbnail view (faster loading)",
            value=st.session_state.use_thumbnail_view,
            help="Toggle between OpenSeadragon zoomable viewer and simple thumbnail view"
        )
        
        # Exclusion reasons management
        st.subheader("📝 Exclusion Reasons")
        
        # Add new reason
        new_reason = st.text_input("Add new reason:")
        if st.button("➕ Add Reason") and new_reason:
            if new_reason not in st.session_state.exclusion_reasons:
                st.session_state.exclusion_reasons.append(new_reason)
                st.success(f"✅ Added reason: {new_reason}")
            else:
                st.warning("⚠️ Reason already exists")
        
        # Display current reasons
        if st.session_state.exclusion_reasons:
            st.write("**Current reasons:**")
            for i, reason in enumerate(st.session_state.exclusion_reasons, 1):
                st.write(f"{i}. {reason}")
        
        # Export section
        st.subheader("📊 Export Data")
        if st.session_state.excluded_images:
            st.write(f"**Excluded images:** {len(st.session_state.excluded_images)}")
            
            # Show breakdown by reason
            reason_counts = {}
            for reason in st.session_state.excluded_images.values():
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            for reason, count in reason_counts.items():
                st.write(f"• {reason}: {count}")
            
            export_excluded_images()
        else:
            st.write("No excluded images yet")
        
        # Backup section
        st.subheader("💾 Backup & Restore")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Backup", help="Manually save current progress"):
                backup_path = save_backup()
                if backup_path:
                    st.success(f"✅ Backup saved: {backup_path.name}")
        
        with col2:
            if st.button("🔄 Auto-backup", help=f"Auto-backup every {AUTO_BACKUP_INTERVAL//60} minutes when excluding images"):
                if st.session_state.excluded_images:
                    backup_path = save_backup()
                    if backup_path:
                        st.success("✅ Manual backup saved!")
                else:
                    st.info("ℹ️ No exclusions to backup yet")
        
        # Load backup
        backup_files = get_backup_files()
        if backup_files:
            st.write("**Available backups:**")
            
            # Show backup info
            for backup_file in backup_files[:5]:  # Show last 5 backups
                try:
                    with open(backup_file, 'r') as f:
                        backup_info = json.load(f)
                    
                    backup_time = datetime.fromisoformat(backup_info["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    excluded_count = backup_info.get("excluded_count", 0)
                    total_images = backup_info.get("total_images", 0)
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📅 {backup_time}")
                        st.write(f"   🚫 {excluded_count}/{total_images} excluded")
                    with col2:
                        if st.button("📂", key=f"load_{backup_file.name}", help="Load this backup"):
                            if load_backup(backup_file):
                                st.success(f"✅ Restored from {backup_file.name}")
                                st.rerun()
                            else:
                                st.error("❌ Failed to restore backup")
                
                except Exception:
                    st.write(f"📄 {backup_file.name} (corrupted)")
        else:
            st.info("No backups available yet")

    # Main content
    if not st.session_state.image_files:
        st.info("👈 Please select a directory containing images using the sidebar.")
        return
    
    # Pagination controls with overlap
    total_images = len(st.session_state.image_files)
    images_per_page = st.session_state.images_per_page
    overlap = PAGE_OVERLAP
    
    # Calculate total pages with overlap
    # Each page shows images_per_page images, but we advance by (images_per_page - overlap) each time
    step_size = images_per_page - overlap
    if step_size <= 0:
        step_size = images_per_page  # Fallback if overlap is too large
    
    # Calculate how many pages we need
    if total_images <= images_per_page:
        total_pages = 1
    else:
        remaining_after_first = total_images - images_per_page
        total_pages = 1 + ((remaining_after_first + step_size - 1) // step_size)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous") and st.session_state.current_page > 0:
            st.session_state.current_page -= 1
            st.rerun()
    
    with col2:
        st.markdown(f"**Page {st.session_state.current_page + 1} of {total_pages}**")
        st.markdown(f"Total: {total_images} images | Excluded: {len(st.session_state.excluded_images)}")
        
        # Show backup status
        backup_files = get_backup_files()
        if backup_files:
            latest_backup = backup_files[0]
            backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime).strftime("%H:%M")
            st.markdown(f"💾 Last backup: {backup_time}")
    
    with col3:
        if st.button("➡️ Next") and st.session_state.current_page < total_pages - 1:
            st.session_state.current_page += 1
            st.rerun()
    
    # Calculate current page images with overlap
    if st.session_state.current_page == 0:
        # First page starts at 0
        start_idx = 0
    else:
        # Subsequent pages advance by step_size but may overlap
        start_idx = st.session_state.current_page * step_size
    
    end_idx = min(start_idx + images_per_page, total_images)
    current_images = st.session_state.image_files[start_idx:end_idx]
    
    # Show overlap information
    if st.session_state.current_page > 0 and overlap > 0:
        overlapping_images = min(overlap, len(current_images))
        st.info(f"📄 Page {st.session_state.current_page + 1} of {total_pages} | Showing {len(current_images)} images | {overlapping_images} overlap from previous page")
    
    # Batch exclusion controls
    st.markdown("---")
    st.subheader("🔄 Batch Operations for Current Page")
    
    # Get images on current page that are not excluded
    non_excluded_current = [img for img in current_images if img not in st.session_state.excluded_images]
    excluded_current = [img for img in current_images if img in st.session_state.excluded_images]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if non_excluded_current:
            batch_reason = st.selectbox(
                "Reason for batch exclusion:",
                ["Select reason..."] + st.session_state.exclusion_reasons,
                key="batch_exclude_reason"
            )
            
            if st.button(f"🚫 Exclude All {len(non_excluded_current)} Images on Page", 
                        type="primary", 
                        disabled=(batch_reason == "Select reason...")):
                if batch_reason != "Select reason...":
                    for image_path in non_excluded_current:
                        st.session_state.excluded_images[image_path] = batch_reason
                    
                    # Trigger backup after batch operation
                    save_backup()
                    st.success(f"✅ Excluded {len(non_excluded_current)} images with reason: {batch_reason}")
                    st.rerun()
        else:
            st.info("All images on this page are already excluded")
    
    with col2:
        if excluded_current:
            if st.button(f"✅ Include All {len(excluded_current)} Images on Page", 
                        type="secondary"):
                for image_path in excluded_current:
                    del st.session_state.excluded_images[image_path]
                
                # Trigger backup after batch operation
                save_backup()
                st.success(f"✅ Included {len(excluded_current)} images back")
                st.rerun()
        else:
            st.info("No excluded images on this page")
    
    with col3:
        st.write("**Page Status:**")
        st.write(f"📄 Total on page: {len(current_images)}")
        st.write(f"✅ Included: {len(non_excluded_current)}")
        st.write(f"🚫 Excluded: {len(excluded_current)}")
    
    st.markdown("---")
    
    # Display images in grid - adaptive layout based on images per page
    if st.session_state.images_per_page <= 15:
        cols_per_row = 3  # 3 columns for smaller counts
    elif st.session_state.images_per_page <= 30:
        cols_per_row = 5  # 5 columns for medium counts
    else:
        cols_per_row = 6  # 6 columns for larger counts
    
    for i in range(0, len(current_images), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            if i + j < len(current_images):
                image_path = current_images[i + j]
                image_name = Path(image_path).name
                container_id = f"viewer_{abs(hash(image_path)) % 100000}"
                
                with col:
                    # Use fragment to render each image card independently
                    render_image_card(image_path, image_name, container_id, cols_per_row)

if __name__ == "__main__":
    main()
