from backend.celery_app import celery_app
from backend.services.report_service import generate_report

@celery_app.task
def generate_report_task(project_id, hazards, risk_score):
    result = generate_report(project_id, hazards, risk_score)
    return result
