"""
FastAPI main application - File-based (no database)
"""
import mimetypes
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

# Fix MIME types for JavaScript modules (Windows fix)
mimetypes.init()
mimetypes.add_type("application/javascript", ".js", strict=True)
mimetypes.add_type("text/css", ".css", strict=True)
mimetypes.add_type("text/html", ".html", strict=True)


class FixMimeTypeMiddleware(BaseHTTPMiddleware):
    """Fix MIME types for static files"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.endswith('.js'):
            response.headers['content-type'] = 'application/javascript; charset=utf-8'
        elif path.endswith('.css'):
            response.headers['content-type'] = 'text/css; charset=utf-8'
        elif path.endswith('.html'):
            response.headers['content-type'] = 'text/html; charset=utf-8'
        return response

from backend.routers import video, labeling, export
from backend.config import FRAMES_DIR, UPLOADS_DIR, LABELS_DIR, BASE_DIR

# Initialize FastAPI app
app = FastAPI(
    title="Human-in-the-Loop Labeling Tool",
    description="Video frame extraction and YOLO-based labeling with human verification",
    version="2.0.0 (File-based)"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fix MIME types middleware
app.add_middleware(FixMimeTypeMiddleware)

# Mount static files for serving images
app.mount("/static/frames", StaticFiles(directory=str(FRAMES_DIR)), name="frames")
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/static/labels", StaticFiles(directory=str(LABELS_DIR)), name="labels")

# Mount web frontend (original simple UI)
WEB_DIR = BASE_DIR / "frontend" / "web"
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

# Mount Svelte frontend (new UI)
SVELTE_DIR = BASE_DIR / "frontend" / "svelte" / "build"
if SVELTE_DIR.exists():
    app.mount("/svelte", StaticFiles(directory=str(SVELTE_DIR), html=True), name="svelte")

# Include routers
app.include_router(video.router)
app.include_router(labeling.router)
app.include_router(export.router)


@app.on_event("startup")
async def startup_event():
    """Startup event - ensure directories exist"""
    for d in [FRAMES_DIR, UPLOADS_DIR, LABELS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    print("Labeling Tool started (file-based, no database)")
    print("  Simple UI: http://localhost:8000/web/")
    print("  Svelte UI: http://localhost:8000/svelte/")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Human-in-the-Loop Labeling Tool API",
        "docs": "/docs",
        "version": "2.0.0",
        "mode": "file-based (no database)"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
