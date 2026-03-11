from .celery_app import celery_app
from .agents.hazard_agent import identify_hazards
from .agents.risk_agent import assess_risk

@celery_app.task
def hazard_task(site_type):
    return identify_hazards(site_type)

@celery_app.task
def risk_task(likelihood, severity):
    return assess_risk(likelihood, severity)
