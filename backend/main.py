"""
FastAPI main application - File-based (no database)
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# Mount static files for serving images
app.mount("/static/frames", StaticFiles(directory=str(FRAMES_DIR)), name="frames")
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/static/labels", StaticFiles(directory=str(LABELS_DIR)), name="labels")

# Mount web frontend
WEB_DIR = BASE_DIR / "frontend" / "web"
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

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
