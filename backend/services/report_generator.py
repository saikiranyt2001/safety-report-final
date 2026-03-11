# backend/services/report_generator.py

from reportlab.pdfgen import canvas

def generate_pdf(report_text, filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, report_text)
    c.save()
