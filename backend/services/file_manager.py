"""
File-based video/frame/label management - No database needed.
Just scans folders and checks file existence.
"""
import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Generator
from datetime import datetime
from contextlib import contextmanager

# Suppress OpenCV/ffmpeg codec warnings - MUST be before cv2 import
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_FFMPEG_DEBUG"] = "0"
os.environ["FFREPORT"] = ""

from backend.config import (
    UPLOADS_DIR, FRAMES_DIR, LABELS_DIR,
    SUPPORTED_VIDEO_EXTENSIONS, CLASS_NAMES
)


@contextmanager
def suppress_stderr():
    """Context manager to suppress stderr at OS level (ffmpeg/C libraries)"""
    try:
        # Save the original stderr file descriptor
        stderr_fd = sys.stderr.fileno()
        saved_stderr_fd = os.dup(stderr_fd)

        # Open devnull and redirect stderr to it
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, stderr_fd)
        os.close(devnull)
        try:
            yield
        finally:
            # Restore original stderr
            os.dup2(saved_stderr_fd, stderr_fd)
            os.close(saved_stderr_fd)
    except (OSError, AttributeError):
        # Fallback if file descriptors don't work (e.g., some Windows configs)
        yield


# Lazy load cv2 with stderr suppression
_cv2 = None

def get_cv2():
    """Get cv2 module with suppressed warnings on first import"""
    global _cv2
    if _cv2 is None:
        with suppress_stderr():
            import cv2
            try:
                cv2.setLogLevel(0)  # LOG_LEVEL_SILENT
            except:
                pass
            _cv2 = cv2
    return _cv2


# For backwards compatibility, also import numpy here
import numpy as np


def cv2_video_capture(video_path: str):
    """
    Open video file with OpenCV, handling non-ASCII paths on Windows.
    Suppresses ffmpeg codec warnings.
    """
    cv2 = get_cv2()
    with suppress_stderr():
        # Try normal open first
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            return cap

        # For non-ASCII paths on Windows, copy to temp file
        try:
            import tempfile
            ext = Path(video_path).suffix
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp_path = tmp.name

            shutil.copy2(video_path, tmp_path)
            cap = cv2.VideoCapture(tmp_path)
            cap._temp_file = tmp_path  # Store for cleanup
            return cap
        except:
            return cv2.VideoCapture(video_path)


class FileManager:
    """File-based management without database"""

    def __init__(self):
        self.uploads_dir = UPLOADS_DIR
        self.frames_dir = FRAMES_DIR
        self.labels_dir = LABELS_DIR

    # ==================== VIDEO OPERATIONS ====================

    def get_video_id(self, filename: str) -> str:
        """Generate video ID from filename (remove extension, sanitize)"""
        name = Path(filename).stem
        # Keep only ASCII alphanumeric and underscore, limit length
        safe_name = "".join(c if c.isascii() and (c.isalnum() or c == '_') else '_' for c in name)
        # Remove consecutive underscores and trim
        while '__' in safe_name:
            safe_name = safe_name.replace('__', '_')
        safe_name = safe_name.strip('_')[:50]  # Limit to 50 chars
        return safe_name or "video"

    def save_video(self, file_content: bytes, filename: str, folder_name: Optional[str] = None, custom_name: Optional[str] = None) -> Dict:
        """Save uploaded video and return info"""
        # Clean filename
        if '/' in filename or '\\' in filename:
            filename = Path(filename.replace('\\', '/')).name

        # Use custom name for video_id if provided, otherwise use filename
        if custom_name and custom_name.strip():
            video_id = self.get_video_id(custom_name.strip())
            # Also rename the file with custom name (keep extension)
            ext = Path(filename).suffix
            new_filename = f"{video_id}{ext}"
        else:
            video_id = self.get_video_id(filename)
            new_filename = filename

        # Save to uploads folder
        if folder_name:
            save_dir = self.uploads_dir / folder_name
        else:
            save_dir = self.uploads_dir

        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / new_filename

        with open(save_path, "wb") as f:
            f.write(file_content)

        # Get video info
        info = self.get_video_info(str(save_path))

        return {
            "video_id": video_id,
            "filename": new_filename,
            "path": str(save_path),
            "folder_name": folder_name,
            **info
        }

    def get_video_info(self, video_path: str) -> Dict:
        """Get video metadata (handles non-ASCII filenames)"""
        cap = cv2_video_capture(video_path)
        temp_file = getattr(cap, '_temp_file', None)

        if not cap.isOpened():
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            raise ValueError(f"Cannot open video: {video_path}")

        try:
            cv2 = get_cv2()
            # Suppress stderr during property access (ffmpeg codec warnings)
            with suppress_stderr():
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0

            return {
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height,
                "duration": duration
            }
        finally:
            cap.release()
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def list_videos(self) -> List[Dict]:
        """List all videos by scanning uploads folder"""
        videos = []

        # Scan uploads directory recursively
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            for path in self.uploads_dir.rglob(f"*{ext}"):
                video_id = self.get_video_id(path.name)

                # Count frames and labels
                frames_dir = self.frames_dir / video_id
                labels_dir = self.labels_dir / video_id

                frames_count = len(list(frames_dir.glob("*.jpg"))) if frames_dir.exists() else 0
                labels_count = len(list(labels_dir.glob("*.txt"))) if labels_dir.exists() else 0

                # Get relative folder name
                rel_path = path.relative_to(self.uploads_dir)
                folder_name = str(rel_path.parent) if rel_path.parent != Path('.') else None

                videos.append({
                    "video_id": video_id,
                    "filename": path.name,
                    "path": str(path),
                    "folder_name": folder_name,
                    "frames_count": frames_count,
                    "approved_count": labels_count,  # Has label = approved
                    "pending_count": max(0, frames_count - labels_count)
                })

        return sorted(videos, key=lambda x: x["filename"])

    def delete_video(self, video_id: str) -> Dict:
        """Delete video and all associated files"""
        deleted = {"video": False, "frames": 0, "labels": 0}

        # Find and delete video file
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            for path in self.uploads_dir.rglob(f"*{ext}"):
                if self.get_video_id(path.name) == video_id:
                    path.unlink()
                    deleted["video"] = True
                    break

        # Delete frames
        frames_dir = self.frames_dir / video_id
        if frames_dir.exists():
            deleted["frames"] = len(list(frames_dir.glob("*.jpg")))
            shutil.rmtree(frames_dir)

        # Delete labels
        labels_dir = self.labels_dir / video_id
        if labels_dir.exists():
            deleted["labels"] = len(list(labels_dir.glob("*.txt")))
            shutil.rmtree(labels_dir)

        return deleted

    # ==================== FRAME OPERATIONS ====================

    def extract_frames(self, video_path: str, video_id: str, interval_seconds: int = 10) -> List[Dict]:
        """Extract frames from video (handles non-ASCII filenames, suppresses warnings)"""
        cap = cv2_video_capture(video_path)
        temp_file = getattr(cap, '_temp_file', None)

        if not cap.isOpened():
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            raise ValueError(f"Cannot open video: {video_path}")

        frames = []
        try:
            cv2 = get_cv2()
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                raise ValueError("Invalid FPS")

            # Create frames directory
            frames_dir = self.frames_dir / video_id
            frames_dir.mkdir(parents=True, exist_ok=True)

            frame_interval = int(fps * interval_seconds)
            if frame_interval < 1:
                frame_interval = 1

            frame_count = 0
            extracted_count = 0

            # Suppress stderr during frame reading (ffmpeg codec warnings)
            with suppress_stderr():
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    if frame_count % frame_interval == 0:
                        timestamp_sec = frame_count / fps

                        # Unique filename
                        frame_filename = f"{video_id}_frame_{extracted_count:04d}.jpg"
                        frame_path = frames_dir / frame_filename

                        cv2.imwrite(str(frame_path), frame)

                        frames.append({
                            "frame_id": f"{video_id}_{extracted_count:04d}",
                            "frame_number": extracted_count,
                            "timestamp_sec": timestamp_sec,
                            "image_path": str(frame_path),
                            "filename": frame_filename
                        })

                        extracted_count += 1

                    frame_count += 1

        finally:
            cap.release()
            # Cleanup temp file if used
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

        return frames

    def list_frames(self, video_id: str) -> List[Dict]:
        """List all frames for a video"""
        frames_dir = self.frames_dir / video_id
        labels_dir = self.labels_dir / video_id

        if not frames_dir.exists():
            return []

        frames = []
        for img_path in sorted(frames_dir.glob("*.jpg")):
            frame_name = img_path.stem
            label_path = labels_dir / f"{frame_name}.txt"

            # Parse frame number from filename
            parts = frame_name.split("_frame_")
            frame_number = int(parts[1]) if len(parts) > 1 else 0

            has_label = label_path.exists()

            frames.append({
                "frame_id": frame_name,
                "frame_number": frame_number,
                "image_path": str(img_path),
                "filename": img_path.name,
                "status": "approved" if has_label else "pending",
                "has_label": has_label,
                "label_path": str(label_path) if has_label else None
            })

        return frames

    def get_frame(self, video_id: str, frame_id: str) -> Optional[Dict]:
        """Get single frame info with labels"""
        frames_dir = self.frames_dir / video_id
        labels_dir = self.labels_dir / video_id

        # Find frame image
        img_path = frames_dir / f"{frame_id}.jpg"
        if not img_path.exists():
            return None

        # Check for label
        label_path = labels_dir / f"{frame_id}.txt"
        labels = []

        if label_path.exists():
            labels = self.read_labels(str(label_path))

        # Get image dimensions
        cv2 = get_cv2()
        img = cv2.imread(str(img_path))
        height, width = img.shape[:2] if img is not None else (0, 0)

        return {
            "frame_id": frame_id,
            "video_id": video_id,
            "image_path": str(img_path),
            "label_path": str(label_path),
            "status": "approved" if labels else "pending",
            "width": width,
            "height": height,
            "labels": labels
        }

    # ==================== LABEL OPERATIONS ====================

    def read_labels(self, label_path: str) -> List[Dict]:
        """
        Read labels from txt file
        Format: class_name x_center y_center width height [confidence] [source]
        """
        labels = []

        if not os.path.exists(label_path):
            return labels

        with open(label_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_name = parts[0]
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])

                    class_id = CLASS_NAMES.index(class_name) if class_name in CLASS_NAMES else 0

                    labels.append({
                        "class_id": class_id,
                        "class_name": class_name,
                        "x_center": x_center,
                        "y_center": y_center,
                        "width": width,
                        "height": height
                    })

        return labels

    def save_labels(self, video_id: str, frame_id: str, labels: List[Dict]) -> str:
        """
        Save labels to txt file
        Format: class_name x_center y_center width height confidence source
        """
        labels_dir = self.labels_dir / video_id
        labels_dir.mkdir(parents=True, exist_ok=True)

        label_path = labels_dir / f"{frame_id}.txt"

        if labels:
            lines = []
            for label in labels:
                class_name = label.get("class_name", CLASS_NAMES[label.get("class_id", 0)])
                # Format: class x y w h (YOLO standard format, nothing else)
                line = f"{class_name} {label['x_center']:.6f} {label['y_center']:.6f} {label['width']:.6f} {label['height']:.6f}"
                lines.append(line)

            with open(label_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
        else:
            # Remove label file if no labels
            if label_path.exists():
                label_path.unlink()

        return str(label_path)

    def delete_label(self, video_id: str, frame_id: str) -> bool:
        """Delete label file"""
        label_path = self.labels_dir / video_id / f"{frame_id}.txt"
        if label_path.exists():
            label_path.unlink()
            return True
        return False


# Singleton
file_manager = FileManager()
