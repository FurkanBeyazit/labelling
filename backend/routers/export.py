"""
Export endpoints - File-based YOLO format export
"""
import os
import zipfile
from io import BytesIO
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.services.file_manager import file_manager
from backend.config import CLASS_NAMES

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/{video_id}")
async def export_video_labels(
    video_id: str,
    only_approved: bool = True,
    use_class_id: bool = False
):
    """
    Export labels for a video in YOLO format as ZIP file.
    """
    frames = file_manager.list_frames(video_id)

    if not frames:
        raise HTTPException(status_code=404, detail="Video not found or no frames")

    # Filter to only approved (has label)
    if only_approved:
        frames = [f for f in frames if f["has_label"]]

    try:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add classes.txt
            classes_content = "\n".join(CLASS_NAMES)
            zf.writestr("classes.txt", classes_content)

            for frame in frames:
                # Add image
                img_path = frame["image_path"]
                if os.path.exists(img_path):
                    img_filename = os.path.basename(img_path)
                    zf.write(img_path, f"images/{img_filename}")

                # Add label
                if frame["label_path"] and os.path.exists(frame["label_path"]):
                    label_filename = os.path.basename(frame["label_path"])

                    if use_class_id:
                        # Convert class names to IDs
                        labels = file_manager.read_labels(frame["label_path"])
                        lines = []
                        for label in labels:
                            line = f"{label['class_id']} {label['x_center']:.6f} {label['y_center']:.6f} {label['width']:.6f} {label['height']:.6f}"
                            lines.append(line)
                        zf.writestr(f"labels/{label_filename}", "\n".join(lines))
                    else:
                        zf.write(frame["label_path"], f"labels/{label_filename}")

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={video_id}_labels.zip"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.get("/{video_id}/stats")
async def export_stats(video_id: str):
    """Get export statistics for a video"""
    frames = file_manager.list_frames(video_id)

    if not frames:
        raise HTTPException(status_code=404, detail="Video not found")

    # Count labels per class
    class_counts = {}
    for frame in frames:
        if frame["has_label"] and frame["label_path"]:
            labels = file_manager.read_labels(frame["label_path"])
            for label in labels:
                name = label["class_name"]
                class_counts[name] = class_counts.get(name, 0) + 1

    total = len(frames)
    approved = sum(1 for f in frames if f["has_label"])

    return {
        "video_id": video_id,
        "total_frames": total,
        "approved_frames": approved,
        "pending_frames": total - approved,
        "exportable_frames": approved,
        "class_distribution": class_counts
    }
