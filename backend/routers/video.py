"""
Video upload and frame extraction endpoints - File-based (no database)
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from backend.services.file_manager import file_manager
from backend.config import SUPPORTED_VIDEO_EXTENSIONS

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    folder_name: Optional[str] = Form(None)
):
    """Upload a single video file"""
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Supported: {SUPPORTED_VIDEO_EXTENSIONS}"
        )

    content = await file.read()

    try:
        result = file_manager.save_video(content, file.filename, folder_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_videos():
    """List all videos"""
    return file_manager.list_videos()


@router.get("/{video_id}")
async def get_video(video_id: str):
    """Get video details"""
    videos = file_manager.list_videos()
    for v in videos:
        if v["video_id"] == video_id:
            return v
    raise HTTPException(status_code=404, detail="Video not found")


@router.get("/{video_id}/delete-info")
async def get_delete_info(video_id: str):
    """Get info about what will be deleted"""
    videos = file_manager.list_videos()
    video = next((v for v in videos if v["video_id"] == video_id), None)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "video_id": video_id,
        "filename": video["filename"],
        "frames_count": video["frames_count"],
        "labels_count": video["approved_count"],
        "warning": f"Bu islemi yaparsaniz {video['frames_count']} frame ve {video['approved_count']} label silinecek!"
    }


@router.delete("/{video_id}")
async def delete_video(video_id: str):
    """Delete video and all associated files"""
    result = file_manager.delete_video(video_id)

    if not result["video"] and result["frames"] == 0:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "message": "Video silindi",
        "video_id": video_id,
        "deleted_frames": result["frames"],
        "deleted_labels": result["labels"]
    }


@router.post("/{video_id}/extract")
async def extract_frames(video_id: str, request: dict):
    """Extract frames from video"""
    interval = request.get("frame_interval", 10)

    # Find video path
    videos = file_manager.list_videos()
    video = next((v for v in videos if v["video_id"] == video_id), None)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        frames = file_manager.extract_frames(video["path"], video_id, interval)
        return {
            "video_id": video_id,
            "frames_extracted": len(frames),
            "interval_seconds": interval
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/frames")
async def get_video_frames(video_id: str, limit: int = 1000):
    """Get frames for a video"""
    frames = file_manager.list_frames(video_id)

    return {
        "video_id": video_id,
        "total": len(frames),
        "frames": frames[:limit]
    }
