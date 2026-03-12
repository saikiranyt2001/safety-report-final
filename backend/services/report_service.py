import uuid
import os

from backend.document_export.pdf_generator import generate_pdf_report

STORAGE_DIR = "storage/reports"
os.makedirs(STORAGE_DIR, exist_ok=True)


# USER FUNCTIONS
def create_user(name, email, password):
    pass


def get_user(user_id):
    pass


def get_all_users():
    pass


# REPORT GENERATION
def generate_report(project_id, hazards, risk_score):

    report_id = str(uuid.uuid4())

    report_data = {
        "Project ID": project_id,
        "Hazards": hazards,
        "Risk Score": risk_score
    }

    output_path = f"{STORAGE_DIR}/{report_id}.pdf"

    generate_pdf_report(report_data, output_path)

    return {
        "report_id": report_id,
        "file_path": output_path
    }