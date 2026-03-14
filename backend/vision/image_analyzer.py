import os
import cv2
from ultralytics import YOLO

from backend.services.alert_service import send_alert
from backend.services.incident_ai import generate_incident_report


class ImageAnalyzer:
    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            # Load YOLO model once
            cls._model = YOLO("yolov8n.pt")
        return cls._model

    @staticmethod
    def _severity_for_label(label: str) -> str:
        high_labels = {
            "person", "truck", "bus", "car", "motorcycle", "bicycle", "forklift"
        }
        medium_labels = {"ladder", "knife", "scissors", "fire hydrant"}

        normalized = label.lower().strip()

        if normalized in high_labels:
            return "high"
        if normalized in medium_labels:
            return "medium"

        return "low"

    @staticmethod
    def _risk_level_from_detections(detections: list) -> str:
        if not detections:
            return "LOW"

        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        peak = max(order.get(item.get("severity", "low"), 1) for item in detections)

        reverse = {
            1: "LOW",
            2: "MEDIUM",
            3: "HIGH",
            4: "CRITICAL"
        }

        return reverse.get(peak, "LOW")

    def analyze(self, image_path: str):

        if not os.path.exists(image_path):
            return {"error": "Image not found"}

        image = cv2.imread(image_path)

        if image is None:
            return {"error": "Invalid image file"}

        height, width = image.shape[:2]

        model = self._get_model()

        # Run YOLO detection
        results = model.predict(source=image_path, conf=0.25, verbose=False)

        detections = []

        if results:
            result = results[0]
            names = result.names

            if result.boxes is not None:
                for box in result.boxes:

                    cls_id = int(box.cls[0].item())

                    if isinstance(names, dict):
                        label = names.get(cls_id, str(cls_id))
                    else:
                        label = str(cls_id)

                    confidence = float(box.conf[0].item())

                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    bbox = {
                        "x": round(x1 / width, 4),
                        "y": round(y1 / height, 4),
                        "w": round((x2 - x1) / width, 4),
                        "h": round((y2 - y1) / height, 4),
                    }

                    detections.append({
                        "label": label,
                        "issue": f"Detected {label}",
                        "confidence": round(confidence, 4),
                        "bbox": bbox,
                        "severity": self._severity_for_label(label),
                    })

        hazards = [
            f"{item['label']} ({item['confidence']})"
            for item in detections
        ]

        risk_level = self._risk_level_from_detections(detections)
        incident_report = None

        if detections and risk_level in {"MEDIUM", "HIGH", "CRITICAL"}:
            incident_report = generate_incident_report(hazards, risk_level)

        if risk_level in {"HIGH", "CRITICAL"}:
            send_alert(f"🔥 {risk_level.title()} risk hazard detected!")

        return {
            "image": image_path,
            "image_size": {
                "width": width,
                "height": height
            },
            "hazards": hazards,
            "detections": detections,
            "risk_level": risk_level,
            "incident_report": incident_report,
        }