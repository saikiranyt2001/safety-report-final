import logging
logger = logging.getLogger(__name__)

from backend.rag.hazard_database import get_hazards


def identify_hazards(site_type, site_data=None):

    hazards = get_hazards(site_type)

    detected = hazards.copy()

    if isinstance(site_data, dict):

        # user supplied hazards
        if "unsafe_conditions" in site_data:
            detected.extend(site_data["unsafe_conditions"])

        # simple text analysis
        if "description" in site_data:
            text = site_data["description"].lower()

            if "oil" in text or "spill" in text:
                detected.append("slip hazard")

            if "machine" in text:
                detected.append("equipment hazard")

            if "height" in text:
                detected.append("fall from height")

    detected = list(set(detected))

    logger.info(f"Hazards detected: {detected}")

    return {
        "site_type": site_type,
        "hazards_detected": detected,
        "count": len(detected)
    }