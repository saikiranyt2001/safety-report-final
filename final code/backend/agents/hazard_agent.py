#done
import logging
logger = logging.getLogger(__name__)

from backend.rag.hazard_database import get_hazards

def identify_hazards(site_type, site_data=None):
    hazards = get_hazards(site_type)
    detected = hazards.copy()
    if isinstance(site_data, dict) and "unsafe_conditions" in site_data:
        detected.extend(site_data["unsafe_conditions"])
    detected = list(set(detected))
    logger.info(f"Hazards detected: {detected}")
    return {
        "site_type": site_type,
        "hazards_detected": detected,
        "count": len(detected)
    }
