from backend.celery_app import celery_app
from backend.agents.hazard_agent import identify_hazards
from backend.agents.risk_agent import assess_risk


@celery_app.task
def hazard_task(site_type, site_data=None):
    """
    Background task to identify hazards
    """
    return identify_hazards(site_type, site_data)


@celery_app.task
def risk_task(hazards):
    """
    Background task to assess risk based on detected hazards
    """
    return assess_risk(hazards)