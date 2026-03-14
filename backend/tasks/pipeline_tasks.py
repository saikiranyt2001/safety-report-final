import os

from backend.celery_app import celery
from backend.agents.orchestrator import run_safety_pipeline
from backend.core.ai_client import chat_completion
from backend.vision.image_analyzer import ImageAnalyzer


analyzer = ImageAnalyzer()


@celery.task
def safety_pipeline_task(site_type, site_data):
    """
    Run the full safety analysis pipeline
    """

    result = run_safety_pipeline(site_type, site_data)

    return {
        "status": "completed",
        "report": result
    }


@celery.task
def ai_analysis_task(prompt):
    return chat_completion(prompt)


@celery.task(name="backend.tasks.pipeline_tasks.analyze_image_task")
def analyze_image_task(image_path):
    try:
        result = analyzer.analyze(image_path)

        if "error" in result:
            raise ValueError(result["error"])

        return result
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)