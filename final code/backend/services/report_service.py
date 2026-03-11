from backend.celery_app import celery_app

@celery_app.task(name="backend.services.report_service.generate_report_task")
def generate_report_task(payload):
    report_type = payload.get("report_type")
    project_id = payload.get("project_id")

    # your report logic
    print(f"Generating {report_type} report for project {project_id}")

    return {"status": "generated"}
