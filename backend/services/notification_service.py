import logging
from sqlalchemy.orm import Session

from backend.services.integration_service import dispatch_event

logger = logging.getLogger("notifications")


def send_notification(message: str, level: str = "info"):

    if level == "warning":
        logger.warning(message)

    elif level == "error":
        logger.error(message)

    else:
        logger.info(message)

    print(f"[NOTIFICATION] {message}")


def notify_hazard_detected(
    db: Session,
    company_id: int,
    project: str,
    hazard: str,
    risk_level: str,
):
    title = "Hazard detected"
    body = (
        f"Project: {project}\n"
        f"Hazard: {hazard}\n"
        f"Risk Level: {risk_level}\n"
        "Action Required Immediately"
    )
    send_notification(f"{title} | {project} | {risk_level}", "warning")
    return dispatch_event(
        db,
        company_id=company_id,
        event="hazard_detected",
        title=title,
        body=body,
        payload={"project": project, "hazard": hazard, "risk_level": risk_level.lower()},
    )


def notify_report_generated(
    db: Session,
    company_id: int,
    project: str,
    task_id: str,
):
    title = "Inspection report generation started"
    body = (
        f"Project: {project}\n"
        f"Task ID: {task_id}\n"
        "A safety report pipeline run has started."
    )
    send_notification(f"{title} | {project}")
    return dispatch_event(
        db,
        company_id=company_id,
        event="report_generated",
        title=title,
        body=body,
        payload={"project": project, "task_id": task_id},
    )


def notify_incident_reported(
    db: Session,
    company_id: int,
    incident_id: int,
    incident_type: str,
    severity: str,
):
    title = "Incident reported"
    body = (
        f"Incident ID: {incident_id}\n"
        f"Type: {incident_type}\n"
        f"Severity: {severity}"
    )
    send_notification(f"{title} | #{incident_id} | {severity}", "warning")
    return dispatch_event(
        db,
        company_id=company_id,
        event="incident_reported",
        title=title,
        body=body,
        payload={
            "incident_id": incident_id,
            "incident_type": incident_type,
            "severity": severity.lower(),
        },
    )


def notify_task_assigned(
    db: Session,
    company_id: int,
    task_id: int,
    task_title: str,
    assigned_to: str | None,
):
    title = "Task assigned"
    body = (
        f"Task ID: {task_id}\n"
        f"Title: {task_title}\n"
        f"Assigned To: {assigned_to or 'Unassigned'}"
    )
    send_notification(f"{title} | #{task_id}")
    return dispatch_event(
        db,
        company_id=company_id,
        event="task_assigned",
        title=title,
        body=body,
        payload={
            "task_id": task_id,
            "task_title": task_title,
            "assigned_to": assigned_to,
        },
    )


def notify_training_expiring(
    db: Session,
    company_id: int,
    worker: str,
    training: str,
    days_to_expiry: int,
):
    title = "Training expiring soon"
    body = (
        f"Worker: {worker}\n"
        f"Training: {training}\n"
        f"Days to expiry: {days_to_expiry}"
    )
    send_notification(f"{title} | {worker}", "warning")
    return dispatch_event(
        db,
        company_id=company_id,
        event="training_expiring",
        title=title,
        body=body,
        payload={
            "worker": worker,
            "training": training,
            "days_to_expiry": days_to_expiry,
        },
    )


# Legacy compatibility wrappers used by older workflow modules.
def hazard_alert(project_name: str, risk_level: str):
    message = f"Hazard detected in {project_name} | Risk Level: {risk_level}"
    if str(risk_level).lower() in {"high", "critical"}:
        send_notification(message, "warning")
    else:
        send_notification(message)
    return message


def report_generated(report_id: int):
    message = f"Safety report #{report_id} generated successfully"
    send_notification(message)
    return message


def incident_prediction_alert(prediction: str):
    message = f"Incident prediction warning: {prediction}"
    send_notification(message, "warning")
    return message