
from backend.celery_app import celery_app
from backend.agents.orchestrator import run_safety_pipeline

from backend.core.ai_client import chat_completion
@celery_app.task
def safety_pipeline_task(site_type, site_data):
    """
    Run the full safety analysis pipeline
    """

    result = run_safety_pipeline(site_type, site_data)

    return {
        "status": "completed",
        "report": result
    }
@celery_app.task
def ai_analysis_task(prompt):
    return chat_completion(prompt)