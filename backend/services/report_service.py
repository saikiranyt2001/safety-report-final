import uuid
import os
from openai import OpenAI

from backend.celery_app import celery
from backend.document_export.pdf_generator import generate_pdf_report

# ----------------------------
# CONFIGURATION
# ----------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables")

client = OpenAI(api_key=OPENAI_API_KEY)

STORAGE_DIR = "storage/reports"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Simple in-memory user storage (for testing)
users = {}

# ----------------------------
# USER FUNCTIONS
# ----------------------------

def create_user(name, email, password):
    user_id = str(uuid.uuid4())

    users[user_id] = {
        "id": user_id,
        "name": name,
        "email": email,
        "password": password
    }

    return users[user_id]


def get_user(user_id):
    return users.get(user_id)


def get_all_users():
    return list(users.values())


# ----------------------------
# AI SAFETY ANALYSIS
# ----------------------------

def generate_ai_analysis(hazards, risk_score):

    prompt = f"""
You are a professional workplace safety inspector.

Analyze the following hazards and risk score.

Hazards detected:
{hazards}

Risk score:
{risk_score}

Provide a structured response including:
1. Hazard summary
2. Risk level explanation
3. Safety recommendations
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI analysis failed: {str(e)}"


# ----------------------------
# IMAGE HAZARD ANALYSIS
# ----------------------------

def analyze_image_hazards(image_description):

    prompt = f"""
You are a safety expert.

Based on the following image description, identify possible workplace hazards.

Image description:
{image_description}

List hazards clearly.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Image analysis failed: {str(e)}"


# ----------------------------
# REPORT GENERATION
# ----------------------------

def generate_report(project_id, hazards, risk_score):

    report_id = str(uuid.uuid4())

    # Generate AI analysis
    ai_analysis = generate_ai_analysis(hazards, risk_score)

    report_data = {
        "Report ID": report_id,
        "Project ID": project_id,
        "Hazards": hazards,
        "Risk Score": risk_score,
        "AI Safety Analysis": ai_analysis
    }

    output_path = os.path.join(STORAGE_DIR, f"{report_id}.pdf")

    # Generate PDF
    generate_pdf_report(report_data, output_path)

    return {
        "report_id": report_id,
        "file_path": output_path,
        "hazards": hazards,
        "risk_score": risk_score,
        "analysis": ai_analysis
    }


@celery.task(name="backend.services.report_service.generate_report_task")
def generate_report_task(project_id, hazards, risk_score):
    print("Generating report...")
    return generate_report(project_id, hazards, risk_score)