
# backend/vision/image_analyzer.py

import cv2
import os


class ImageAnalyzer:

    def analyze(self, image_path: str):
        """
        Analyze inspection image for safety hazards.
        Currently placeholder logic.
        """
        if not os.path.exists(image_path):
            return {"error": "Image not found"}
        image = cv2.imread(image_path)
        if image is None:
            return {"error": "Invalid image file"}

        height, width = image.shape[:2]

        # Placeholder detections with normalized bounding boxes.
        detections = [
            {
                "label": "Worker",
                "issue": "No Helmet",
                "bbox": {"x": 0.18, "y": 0.2, "w": 0.22, "h": 0.46},
                "severity": "critical",
            },
            {
                "label": "Ladder",
                "issue": "Unsafe Angle",
                "bbox": {"x": 0.56, "y": 0.18, "w": 0.2, "h": 0.62},
                "severity": "high",
            },
            {
                "label": "Edge",
                "issue": "Fall Hazard",
                "bbox": {"x": 0.8, "y": 0.06, "w": 0.14, "h": 0.82},
                "severity": "high",
            },
        ]

        hazards = [f"{item['label']} -> {item['issue']}" for item in detections]

        return {
            "image": image_path,
            "image_size": {"width": width, "height": height},
            "hazards": hazards,
            "detections": detections,
            "risk_level": "HIGH",
        }
