import cv2
import os

from backend.services.alert_service import send_alert
from backend.services.incident_ai import generate_incident_report

class HazardDetector:

    def __init__(self):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("ultralytics is not installed") from exc
        self.model = YOLO("yolov8n.pt")

    def detect(self, image_path):

        results = self.model(image_path)

        annotated_path = "storage/reports/annotated.jpg"

        hazards = []
        risk_score = 0

        for r in results:

            img = r.plot()  # draw bounding boxes

            for box in r.boxes:
                label = r.names[int(box.cls)]
                hazards.append(label)

                if label in ["fire", "smoke"]:
                    risk_score += 3
                else:
                    risk_score += 1

        cv2.imwrite(annotated_path, img)

        risk_level = "LOW"

        if risk_score >= 5:
            risk_level = "HIGH"
        elif risk_score >= 3:
            risk_level = "MEDIUM"

        incident_report = None
        if hazards and risk_level in {"MEDIUM", "HIGH"}:
            incident_report = generate_incident_report(list(set(hazards)), risk_level)

        if risk_level == "HIGH":
            send_alert("🔥 High risk hazard detected!")

        return {
            "hazards": list(set(hazards)),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "annotated_image": annotated_path,
            "incident_report": incident_report,
        }
