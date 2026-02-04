"""
Labeling endpoints - File-based (no database)
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.services.file_manager import file_manager
from backend.services.auto_labeler import get_auto_labeler
from backend.config import CLASS_NAMES, get_class_color

router = APIRouter(prefix="/api", tags=["labeling"])


@router.get("/classes")
async def get_classes():
    """Get all available classes with colors"""
    return [
        {
            "class_id": i,
            "class_name": name,
            "color": get_class_color(i),
            "auto_detectable": True
        }
        for i, name in enumerate(CLASS_NAMES)
    ]


@router.get("/frames/{video_id}/{frame_id}")
async def get_frame(video_id: str, frame_id: str):
    """Get frame details with labels"""
    frame = file_manager.get_frame(video_id, frame_id)

    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")

    # Add colors to labels
    for label in frame["labels"]:
        label["color"] = get_class_color(label["class_id"])

    return frame


@router.get("/frames/{video_id}/{frame_id}/image")
async def get_frame_image(video_id: str, frame_id: str):
    """Get frame image file"""
    frame = file_manager.get_frame(video_id, frame_id)

    if not frame or not os.path.exists(frame["image_path"]):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(frame["image_path"])


@router.post("/frames/{video_id}/{frame_id}/auto-label")
async def auto_label_frame(video_id: str, frame_id: str, request: dict = None):
    """Run YOLO auto-labeling on a frame"""
    request = request or {}
    confidence = request.get("confidence_threshold", 0.5)

    frame = file_manager.get_frame(video_id, frame_id)
    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")

    try:
        auto_labeler = get_auto_labeler()
        predictions = auto_labeler.predict(
            frame["image_path"],
            confidence_threshold=confidence,
            image_width=frame["width"],
            image_height=frame["height"]
        )

        # Save labels
        file_manager.save_labels(video_id, frame_id, predictions)

        # Add colors
        for pred in predictions:
            pred["color"] = get_class_color(pred["class_id"])

        return {
            "frame_id": frame_id,
            "labels_count": len(predictions),
            "labels": predictions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-labeling failed: {e}")


@router.put("/frames/{video_id}/{frame_id}/labels")
async def update_frame_labels(video_id: str, frame_id: str, request: dict):
    """Update all labels for a frame"""
    labels = request.get("labels", [])

    file_manager.save_labels(video_id, frame_id, labels)

    return {
        "frame_id": frame_id,
        "labels_count": len(labels),
        "status": "saved"
    }


@router.post("/frames/{video_id}/{frame_id}/approve")
async def approve_frame(video_id: str, frame_id: str):
    """Approve frame - labels are already saved as txt"""
    frame = file_manager.get_frame(video_id, frame_id)
    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")

    return {
        "frame_id": frame_id,
        "status": "approved",
        "label_file": frame.get("label_path")
    }


@router.post("/frames/{video_id}/{frame_id}/reject")
async def reject_frame(video_id: str, frame_id: str):
    """Reject frame - delete label file"""
    file_manager.delete_label(video_id, frame_id)

    return {
        "frame_id": frame_id,
        "status": "rejected"
    }


@router.get("/stats")
async def get_stats():
    """Get labeling statistics"""
    videos = file_manager.list_videos()

    total_frames = sum(v["frames_count"] for v in videos)
    total_approved = sum(v["approved_count"] for v in videos)
    total_pending = sum(v["pending_count"] for v in videos)

    return {
        "total_videos": len(videos),
        "total_frames": total_frames,
        "approved_frames": total_approved,
        "pending_frames": total_pending
    }


@router.get("/model-info")
async def get_model_info():
    """Get YOLO model info for debugging"""
    auto_labeler = get_auto_labeler()

    class_mapping = []
    for model_id, model_name in auto_labeler.model_class_names.items():
        mapping = auto_labeler._map_model_class_to_project(model_id)
        class_mapping.append({
            "model_class_id": model_id,
            "model_class_name": model_name,
            "project_class_id": mapping[0] if mapping else None,
            "project_class_name": mapping[1] if mapping else None,
            "mapped": mapping is not None
        })

    return {
        "model_path": auto_labeler.model_path,
        "is_custom_model": auto_labeler.is_custom_model,
        "model_loaded": auto_labeler.model is not None,
        "model_classes": auto_labeler.model_class_names,
        "project_classes": CLASS_NAMES,
        "class_mapping": class_mapping
    }
