# pipeline_tasks.py

"""
Celery tasks for orchestrating the safety pipeline.
"""

from backend.workflow.safety_pipeline import run_safety_pipeline

from backend.celery_app import celery_app

@celery_app.task(name="pipeline.run_safety_pipeline")
def run_pipeline_task(project_id):
    """
    Run the safety pipeline for a given project.
    """
    return run_safety_pipeline(project_id)
