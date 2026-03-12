import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_pdf_report(report_data, output_path):

    c = canvas.Canvas(output_path, pagesize=A4)

    y = 800

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "AI Safety Inspection Report")

    y -= 40
    c.setFont("Helvetica", 12)

    for key, value in report_data.items():
        c.drawString(50, y, f"{key}: {value}")
        y -= 20

    c.save()

    return output_path