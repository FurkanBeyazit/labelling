"""
Configuration for the labeling tool.
Class definitions and YOLO mapping based on user's existing script.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
FRAMES_DIR = DATA_DIR / "frames"
LABELS_DIR = DATA_DIR / "labels"
WEIGHTS_DIR = BASE_DIR / "weights"

# Ensure directories exist
for d in [UPLOADS_DIR, FRAMES_DIR, LABELS_DIR, WEIGHTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{DATA_DIR}/labeling.db"

# Project class definitions (index -> name)
# Custom trained YOLO model (best.pt) - 12 classes
CLASS_NAMES = [
    "person",      # 0
    "car",         # 1
    "falldown",    # 2
    "bus",         # 3
    "truck",       # 4
    "bicycle",     # 5
    "motorcycle",  # 6
    "boar",        # 7
    "tractor",     # 8
    "scooter",     # 9
    "cat",         # 10
    "dog",         # 11
]

# Class colors for visualization (hex format for web)
CLASS_COLORS = [
    "#FF0000",  # person - red
    "#0000FF",  # car - blue
    "#FFFF00",  # falldown - yellow
    "#00FF00",  # bus - green
    "#800080",  # truck - purple
    "#FFA500",  # bicycle - orange
    "#00FFFF",  # motorcycle - cyan
    "#8B4513",  # boar - brown
    "#CCCCCC",  # tractor - gray
    "#FFC0CB",  # scooter - pink
    "#32CD32",  # cat - lime green
    "#FFD700",  # dog - gold
]

# All classes are auto-detectable with custom model
AUTO_DETECTABLE_CLASSES = list(range(12))

# Frame extraction intervals (seconds)
FRAME_INTERVALS = [1,5, 10, 15, 30]

# YOLO settings - Custom trained model with 13 classes
YOLO_MODEL_PATH = str(WEIGHTS_DIR / "best.pt")
DEFAULT_CONFIDENCE = 0.35

# Video settings
SUPPORTED_VIDEO_EXTENSIONS = [".avi", ".mp4", ".mov", ".mkv", ".wmv"]
SUPPORTED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"]


def get_class_color(class_id: int) -> str:
    """Get color for a class ID"""
    if 0 <= class_id < len(CLASS_COLORS):
        return CLASS_COLORS[class_id]
    return "#FF0000"


def get_class_name(class_id: int) -> str:
    """Get class name for a class ID"""
    if 0 <= class_id < len(CLASS_NAMES):
        return CLASS_NAMES[class_id]
    return "unknown"


def get_class_id(class_name: str) -> int:
    """Get class ID for a class name"""
    try:
        return CLASS_NAMES.index(class_name)
    except ValueError:
        return -1
