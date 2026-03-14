import os
import smtplib
from email.message import EmailMessage


SMTP_HOST = os.getenv("ALERT_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("ALERT_SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("ALERT_SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("ALERT_SMTP_PASSWORD")
ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "safety@system.com")
ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "admin@factory.com")


def send_alert(message: str, subject: str = "Safety Alert"):
    print(f"ALERT: {message}")

    try:
        email = EmailMessage()
        email["Subject"] = subject
        email["From"] = ALERT_FROM_EMAIL
        email["To"] = ALERT_TO_EMAIL
        email.set_content(message)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()

            if SMTP_USERNAME and SMTP_PASSWORD:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)

            server.send_message(email)

    except Exception as e:
        print("Alert failed:", e)


def send_hazard_alert(source: str, detections: list[dict], risk_level: str):
    if not detections:
        return

    hazard_labels = ", ".join(item.get("label", "unknown") for item in detections[:5])
    message = (
        f"Hazard detected by {source}.\n"
        f"Risk level: {risk_level}.\n"
        f"Detected items: {hazard_labels}.\n"
        f"Total detections: {len(detections)}"
    )
    send_alert(message)