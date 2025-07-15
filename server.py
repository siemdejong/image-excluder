"""
FastAPI server for serving TIFF files to GeoTIFFTileSource plugin
"""
import os
import uvicorn
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import argparse

app = FastAPI(title="TIFF File Server", description="Simple server for serving TIFF files with range request support")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/{file_path:path}")
async def serve_file(file_path: str, request: Request):
    """Serve TIFF files with HTTP range support"""
    try:
        # Decode the file path
        file_path = file_path.replace('__SLASH__', '/')
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get file info
        file_size = os.path.getsize(file_path)
        
        # Handle range requests
        range_header = request.headers.get('range')
        if range_header:
            # Parse range header (e.g., "bytes=0-1023")
            byte_start = 0
            byte_end = file_size - 1
            
            if range_header.startswith('bytes='):
                ranges = range_header[6:].split('-')
                if len(ranges) == 2:
                    if ranges[0]:
                        byte_start = int(ranges[0])
                    if ranges[1]:
                        byte_end = int(ranges[1])
            
            # Ensure valid range
            byte_start = max(0, byte_start)
            byte_end = min(file_size - 1, byte_end)
            content_length = byte_end - byte_start + 1
            
            # Read the requested range
            with open(file_path, 'rb') as f:
                f.seek(byte_start)
                file_data = f.read(content_length)
            
            headers = {
                'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                'Content-Length': str(content_length),
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'public, max-age=3600'
            }
            
            return Response(
                content=file_data,
                status_code=206,  # Partial Content
                media_type='image/tiff',
                headers=headers
            )
        else:
            # Serve entire file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            headers = {
                'Content-Length': str(file_size),
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'public, max-age=3600'
            }
            
            return Response(
                content=file_data,
                media_type='image/tiff',
                headers=headers
            )
            
    except Exception as e:
        print(f"Error serving file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Error serving file")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start TIFF file server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run server on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()
    
    print(f"Starting FastAPI TIFF server on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
