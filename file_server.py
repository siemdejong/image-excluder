"""
Simple HTTP file server for serving TIFF files to GeoTIFFTileSource plugin
"""
import os
import socketserver
from http.server import SimpleHTTPRequestHandler
from urllib.parse import unquote
import threading

class CORSHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with CORS support and range request handling"""
    
    def end_headers(self):
        """Add CORS headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Range, Content-Range')
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests with range support"""
        # Decode the file path
        file_path = unquote(self.path[1:])  # Remove leading '/'
        
        if not os.path.exists(file_path):
            self.send_error(404, "File not found")
            return
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Check for range request
        range_header = self.headers.get('Range')
        if range_header:
            try:
                # Parse range header (e.g., "bytes=0-1023")
                range_match = range_header.replace('bytes=', '').split('-')
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else file_size - 1
                
                # Ensure valid range
                start = max(0, min(start, file_size - 1))
                end = max(start, min(end, file_size - 1))
                content_length = end - start + 1
                
                # Send partial content response
                self.send_response(206)
                self.send_header('Content-Type', 'image/tiff')
                self.send_header('Content-Length', str(content_length))
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.end_headers()
                
                # Read and send the requested range
                with open(file_path, 'rb') as f:
                    f.seek(start)
                    data = f.read(content_length)
                    self.wfile.write(data)
                    
            except (ValueError, IndexError):
                # Invalid range, serve entire file
                self.serve_entire_file(file_path, file_size)
        else:
            # No range request, serve entire file
            self.serve_entire_file(file_path, file_size)
    
    def serve_entire_file(self, file_path, file_size):
        """Serve the entire file"""
        self.send_response(200)
        self.send_header('Content-Type', 'image/tiff')
        self.send_header('Content-Length', str(file_size))
        self.end_headers()
        
        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())

def start_file_server(port=5000):
    """Start the file server"""
    handler = CORSHTTPRequestHandler
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"File server running on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Start server in a separate thread so it doesn't block
    server_thread = threading.Thread(target=start_file_server, daemon=True)
    server_thread.start()
    
    try:
        # Keep the main thread alive
        server_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down file server...")
