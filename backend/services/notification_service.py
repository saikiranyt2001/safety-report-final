# Notification Service Layer

# Add business logic for sending notifications (email, SMS, in-app, etc.)
import logging

logger = logging.getLogger("notifications")


def send_notification(message: str, level: str = "info"):

    if level == "warning":
        logger.warning(message)

    elif level == "error":
        logger.error(message)

    else:
        logger.info(message)

    print(f"[NOTIFICATION] {message}")

def hazard_alert(project_name: str, risk_level: str):

    message = f"Hazard detected in {project_name} | Risk Level: {risk_level}"

    if risk_level == "High" or risk_level == "Critical":
        send_notification(message, "warning")


def report_generated(report_id: int):

    message = f"Safety report #{report_id} generated successfully"

    send_notification(message)        

def incident_prediction_alert(prediction: str):

    message = f"Incident prediction warning: {prediction}"

    send_notification(message, "warning")    