"""
Auto-labeling service using YOLO.
Maps YOLO class names to project class names for correct labeling.
"""
import os
from typing import List, Optional, Dict, Any
from pathlib import Path

from backend.config import (
    YOLO_MODEL_PATH,
    CLASS_NAMES,
    DEFAULT_CONFIDENCE,
    AUTO_DETECTABLE_CLASSES,
    get_class_name,
    get_class_id
)


class AutoLabeler:
    """
    YOLO-based auto-labeling.
    Maps YOLO model's class names to project class names.
    Works with both custom trained and COCO models.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or YOLO_MODEL_PATH
        self.model = None
        self.model_class_names = {}  # model_class_id -> class_name from model
        self.is_custom_model = False
        self._load_model()

    def _load_model(self):
        """Load YOLO model and read its class names"""
        try:
            from ultralytics import YOLO
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
                self.is_custom_model = True
                print(f"[AutoLabeler] Custom model loaded: {self.model_path}")
            else:
                print(f"[AutoLabeler] WARNING: Model not found at {self.model_path}")
                print(f"[AutoLabeler] Loading fallback COCO model (yolo11n.pt)...")
                self.model = YOLO("yolo11n.pt")
                self.is_custom_model = False

            # Read model's class names
            if self.model is not None and hasattr(self.model, 'names'):
                self.model_class_names = self.model.names
                print(f"[AutoLabeler] Model classes: {self.model_class_names}")

        except Exception as e:
            print(f"[AutoLabeler] Failed to load YOLO model: {e}")
            self.model = None

    def _map_model_class_to_project(self, model_class_id: int) -> Optional[tuple]:
        """
        Map model's class ID to project class ID using class NAME matching.
        Returns (project_class_id, project_class_name) or None if not found.
        """
        if model_class_id not in self.model_class_names:
            return None

        # Get the class name from the model
        model_class_name = self.model_class_names[model_class_id].lower()

        # Try to find matching project class by name
        for i, project_name in enumerate(CLASS_NAMES):
            if project_name.lower() == model_class_name:
                return (i, project_name)

        # Not found in our project classes
        return None

    def predict(
        self,
        image_path: str,
        confidence_threshold: float = DEFAULT_CONFIDENCE,
        image_width: Optional[int] = None,
        image_height: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Run YOLO prediction on image and filter to allowed classes.

        Returns list of dicts with:
            - class_id: Project class ID
            - class_name: Class name
            - confidence: Detection confidence
            - x_center, y_center, width, height: Normalized YOLO format (0-1)
            - x1, y1, x2, y2: Pixel coordinates
        """
        if self.model is None:
            raise RuntimeError("YOLO model not loaded")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Run inference
        results = self.model.predict(image_path, verbose=False)[0]

        if results.boxes is None or len(results.boxes) == 0:
            return []

        # Get image dimensions if not provided
        if image_width is None or image_height is None:
            from backend.services.file_manager import get_cv2
            cv2 = get_cv2()
            img = cv2.imread(image_path)
            if img is not None:
                image_height, image_width = img.shape[:2]
            else:
                raise ValueError("Cannot read image dimensions")

        filtered_labels = []

        boxes_xyxy = results.boxes.xyxy  # [x1, y1, x2, y2] pixel coords
        classes = results.boxes.cls
        confidences = results.boxes.conf

        for box, cls_tensor, conf_tensor in zip(boxes_xyxy, classes, confidences):
            model_class_id = int(cls_tensor.item())
            confidence = float(conf_tensor.item())

            # Skip if below threshold
            if confidence < confidence_threshold:
                continue

            # Map model class to project class by NAME (not by ID!)
            mapping = self._map_model_class_to_project(model_class_id)
            if mapping is None:
                # Class not in our project (e.g., COCO classes we don't use)
                continue

            project_class_id, class_name = mapping

            # Get pixel coordinates
            x1, y1, x2, y2 = box.tolist()

            # Calculate normalized YOLO format
            box_width = x2 - x1
            box_height = y2 - y1
            x_center = x1 + box_width / 2
            y_center = y1 + box_height / 2

            # Normalize (0-1)
            x_center_norm = x_center / image_width
            y_center_norm = y_center / image_height
            width_norm = box_width / image_width
            height_norm = box_height / image_height

            filtered_labels.append({
                "class_id": project_class_id,
                "class_name": class_name,
                "confidence": confidence,
                "x_center": x_center_norm,
                "y_center": y_center_norm,
                "width": width_norm,
                "height": height_norm,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "source": "auto"
            })

        return filtered_labels

    def predict_batch(
        self,
        image_paths: List[str],
        confidence_threshold: float = DEFAULT_CONFIDENCE
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run prediction on multiple images.
        Returns dict mapping image_path -> list of labels.
        """
        results = {}
        for path in image_paths:
            try:
                results[path] = self.predict(path, confidence_threshold)
            except Exception as e:
                print(f"Error processing {path}: {e}")
                results[path] = []
        return results

    def is_model_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model is not None

    def get_supported_classes(self) -> List[Dict[str, Any]]:
        """
        Get list of classes that can be auto-detected.
        Custom trained model - all classes are auto-detectable.
        """
        classes = []
        for i, name in enumerate(CLASS_NAMES):
            classes.append({
                "class_id": i,
                "class_name": name,
                "auto_detectable": i in AUTO_DETECTABLE_CLASSES
            })
        return classes


# Singleton instance (lazy loaded)
_auto_labeler: Optional[AutoLabeler] = None


def get_auto_labeler() -> AutoLabeler:
    """Get or create auto labeler instance"""
    global _auto_labeler
    if _auto_labeler is None:
        _auto_labeler = AutoLabeler()
    return _auto_labeler
