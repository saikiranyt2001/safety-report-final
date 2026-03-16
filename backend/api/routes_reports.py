import os
import json
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import Company, Project, Report
from backend.agents.safety_score_agent import calculate_safety_score
from backend.core.rbac import require_roles
from backend.core.ai_client import chat_completion
from backend.services.activity_service import log_activity
from backend.services.notification_service import notify_report_generated
from backend.tasks.report_task import generate_report_task

router = APIRouter(tags=["Reports"])

STORAGE_DIR = "storage/reports"
os.makedirs(STORAGE_DIR, exist_ok=True)


class ReportCreatePayload(BaseModel):
    report_id: str | None = None
    project_id: int | None = None
    date: str | None = None
    time: str | None = None
    location: str | None = None
    department: str | None = None
    employee_name: str | None = None
    employee_id: str | None = None
    role: str | None = None
    hazard_type: str | None = None
    risk_level: str | None = None
    description: str | None = None
    risk_score: int | None = None
    severity: str | None = None
    probability: str | None = None
    root_cause: str | None = None
    immediate_action: str | None = None
    preventive_action: str | None = None
    responsible_person: str | None = None
    deadline: str | None = None
    status: str | None = None
    evidence_url: str | None = None
    layout_style: str | None = None
    layout_reference_url: str | None = None
    layout_reference_name: str | None = None
    layout_primary_color: str | None = None
    layout_accent_color: str | None = None
    company_name: str | None = None
    company_address: str | None = None
    layout_margin_style: str | None = None
    layout_header_style: str | None = None
    layout_preview_note: str | None = None


class LayoutPreviewPayload(BaseModel):
    company_name: str | None = None
    company_address: str | None = None
    layout_reference_url: str | None = None
    layout_reference_name: str | None = None
    layout_primary_color: str | None = None
    layout_accent_color: str | None = None


# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _risk_level_from_score(score: int) -> str:
    if score >= 80:
        return "Low"
    if score >= 60:
        return "Medium"
    return "High"


def _severity_score_from_risk_level(risk_level: str | None) -> int:
    mapping = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    return mapping.get((risk_level or "").strip().lower(), 2)


def _risk_level_from_severity(severity: int | None) -> str:
    mapping = {
        1: "Low",
        2: "Medium",
        3: "High",
        4: "Critical",
    }
    return mapping.get(severity or 2, "Medium")


def _resolve_report_company_id(db: Session, project_id: int | None) -> int:
    if project_id is not None:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            return project.company_id

    company = db.query(Company).order_by(Company.id.asc()).first()
    if company:
        return company.id

    company = Company(name="Local Demo Company")
    db.add(company)
    db.commit()
    db.refresh(company)
    return company.id


def _serialize_report(row: Report) -> dict:
    fields = _parse_report_content(row.content or "")
    return {
        "id": row.id,
        "project_id": row.project_id,
        "content": row.content or "",
        "severity": row.severity,
        "likelihood": row.likelihood,
        "risk_level": _risk_level_from_severity(row.severity),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "layout_style": fields.get("layout_style") or "classic",
        "layout_reference_url": fields.get("layout_reference_url"),
        "layout_reference_name": fields.get("layout_reference_name"),
        "layout_primary_color": fields.get("layout_primary_color"),
        "layout_accent_color": fields.get("layout_accent_color"),
        "location": fields.get("location"),
        "department": fields.get("department"),
        "report_id": fields.get("report_id"),
        "hazard_type": fields.get("hazard_type"),
        "description": fields.get("description"),
    }


def _get_demo_report(db: Session, report_id: int) -> Report:
    demo_company_id = _resolve_report_company_id(db, None)
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.company_id == demo_company_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


FIELD_LABELS = {
    "report_id": "Report ID",
    "date": "Date",
    "time": "Time",
    "location": "Location",
    "department": "Department",
    "employee_name": "Employee Name",
    "employee_id": "Employee ID",
    "role": "Role",
    "hazard_type": "Hazard Type",
    "risk_level": "Risk Level",
    "description": "Description",
    "risk_score": "Risk Score",
    "severity": "Severity Label",
    "probability": "Probability",
    "root_cause": "Root Cause",
    "immediate_action": "Immediate Action",
    "preventive_action": "Preventive Action",
    "responsible_person": "Responsible Person",
    "deadline": "Deadline",
    "status": "Status",
    "evidence_url": "Evidence URL",
    "layout_style": "Layout Style",
    "layout_reference_url": "Layout Reference URL",
    "layout_reference_name": "Layout Reference Name",
    "layout_primary_color": "Layout Primary Color",
    "layout_accent_color": "Layout Accent Color",
    "company_name": "Company Name",
    "company_address": "Company Address",
    "layout_margin_style": "Layout Margin Style",
    "layout_header_style": "Layout Header Style",
    "layout_preview_note": "Layout Preview Note",
}

LABEL_TO_FIELD = {label: key for key, label in FIELD_LABELS.items()}


def _build_report_content(payload: ReportCreatePayload) -> str:
    lines: list[str] = []
    for field_name, label in FIELD_LABELS.items():
        value = getattr(payload, field_name, None)
        if value is None or value == "":
            continue
        serialized = str(value).replace("\r\n", " ").replace("\n", " ").strip()
        lines.append(f"{label}: {serialized}")
    return "\n".join(lines)


def _parse_report_content(content: str) -> dict[str, str]:
    data: dict[str, str] = {}
    unlabeled: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        label, separator, value = line.partition(":")
        key = LABEL_TO_FIELD.get(label.strip()) if separator else None
        if key:
            data[key] = value.strip()
        else:
            unlabeled.append(line)

    if unlabeled and "description" not in data:
        data["description"] = "\n".join(unlabeled)
    return data


def _resolve_local_storage_path(url: str | None) -> str | None:
    if not url or not url.startswith("/storage/"):
        return None
    relative_path = url.lstrip("/").replace("/", os.sep)
    full_path = os.path.abspath(relative_path)
    return full_path if os.path.exists(full_path) else None


def _safe_hex_color(value: str | None, fallback: str) -> colors.Color:
    try:
        return colors.HexColor(value or fallback)
    except Exception:
        return colors.HexColor(fallback)


def _extract_json_object(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _fallback_layout_plan(payload: LayoutPreviewPayload) -> dict:
    return {
        "engine": "RULES",
        "margin_style": "wide-frame",
        "header_style": "image-band",
        "preview_note": "Outer frame borrowed from uploaded layout; important text stays in a clean readable panel.",
        "company_name": payload.company_name or "Safety AI Platform",
        "company_address": payload.company_address or "Worksite address pending",
        "primary_color": payload.layout_primary_color or "#364fc7",
        "accent_color": payload.layout_accent_color or "#0c8599",
    }


def _ai_layout_plan(payload: LayoutPreviewPayload) -> dict:
    prompt = (
        "You are helping style a safety incident report. "
        "Use the uploaded layout only as inspiration for outer margin treatment and header framing. "
        "Do not restyle the body fields heavily; keep company name, address, and form details readable. "
        "Return compact JSON only with keys: margin_style, header_style, preview_note. "
        "Allowed margin_style values: wide-frame, double-frame, rounded-frame, banded-frame. "
        "Allowed header_style values: image-band, boxed-header, top-ribbon, split-banner. "
        f"Template file name: {payload.layout_reference_name or 'unknown'}. "
        f"Primary color: {payload.layout_primary_color or '#364fc7'}. "
        f"Accent color: {payload.layout_accent_color or '#0c8599'}. "
        f"Company name: {payload.company_name or 'Safety AI Platform'}. "
        f"Company address: {payload.company_address or 'Worksite address pending'}."
    )
    try:
        raw = chat_completion(prompt, max_tokens=180)
        parsed = _extract_json_object(raw or "")
        if not parsed:
            raise ValueError("Could not parse AI layout plan")
        return {
            "engine": "AI",
            "margin_style": parsed.get("margin_style") or "wide-frame",
            "header_style": parsed.get("header_style") or "image-band",
            "preview_note": parsed.get("preview_note") or "AI generated a template-aware outer frame.",
            "company_name": payload.company_name or "Safety AI Platform",
            "company_address": payload.company_address or "Worksite address pending",
            "primary_color": payload.layout_primary_color or "#364fc7",
            "accent_color": payload.layout_accent_color or "#0c8599",
        }
    except Exception:
        return _fallback_layout_plan(payload)


def _style_palette(
    layout_style: str,
    fields: dict[str, str] | None = None,
) -> dict[str, colors.Color | tuple[colors.Color, colors.Color]]:
    fields = fields or {}
    palettes = {
        "classic": {
            "header": colors.HexColor("#0b7285"),
            "accent": colors.HexColor("#2f9e44"),
            "panel": colors.HexColor("#f8fbfd"),
            "text": colors.HexColor("#102a43"),
        },
        "executive": {
            "header": colors.HexColor("#102a43"),
            "accent": colors.HexColor("#c77d00"),
            "panel": colors.HexColor("#fff8e7"),
            "text": colors.HexColor("#1f2937"),
        },
        "audit": {
            "header": colors.HexColor("#5f3dc4"),
            "accent": colors.HexColor("#d9480f"),
            "panel": colors.HexColor("#f7f2ff"),
            "text": colors.HexColor("#2d1b4e"),
        },
        "reference": {
            "header": colors.HexColor("#364fc7"),
            "accent": colors.HexColor("#0c8599"),
            "panel": colors.HexColor("#eff8ff"),
            "text": colors.HexColor("#102a43"),
        },
    }
    palette = dict(palettes.get(layout_style, palettes["classic"]))
    if layout_style == "reference":
        palette["header"] = _safe_hex_color(fields.get("layout_primary_color"), "#364fc7")
        palette["accent"] = _safe_hex_color(fields.get("layout_accent_color"), "#0c8599")
    return palette


def _draw_wrapped_text(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    line_height: float = 14,
) -> float:
    words = (text or "-").split()
    current = ""
    lines: list[str] = []

    for word in words:
        candidate = f"{current} {word}".strip()
        if pdf.stringWidth(candidate, "Helvetica", 10) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)

    if not lines:
        lines = ["-"]

    for line in lines:
        pdf.drawString(x, y, line)
        y -= line_height
    return y


def _draw_reference_background(
    pdf: canvas.Canvas,
    reference_path: str,
    width: float,
    height: float,
) -> None:
    pdf.drawImage(ImageReader(reference_path), 0, 0, width=width, height=height, mask="auto")


def _draw_reference_cover(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    report: Report,
    fields: dict[str, str],
) -> None:
    pdf.setFillColor(colors.Color(0.05, 0.12, 0.22, alpha=0.58))
    pdf.roundRect(36, 36, width - 72, 108, 18, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(56, 110, fields.get("report_id") or f"Safety Report #{report.id}")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(56, 90, f"Location: {fields.get('location') or '-'}")
    pdf.drawString(56, 74, f"Risk Level: {_risk_level_from_severity(report.severity)}")
    pdf.drawString(56, 58, f"Generated: {report.created_at.strftime('%Y-%m-%d %H:%M') if report.created_at else '-'}")


def _draw_reference_content_page(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    report: Report,
    fields: dict[str, str],
    palette: dict[str, colors.Color | tuple[colors.Color, colors.Color]],
    reference_name: str | None,
) -> None:
    pdf.setFillColor(colors.Color(1, 1, 1, alpha=0.82))
    pdf.roundRect(34, 28, width - 68, height - 56, 18, fill=1, stroke=0)

    pdf.setFillColor(palette["header"])
    pdf.roundRect(48, height - 92, width - 96, 34, 12, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(62, height - 79, "Report Styled From Uploaded Layout")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width - 62, height - 78, reference_name or "Image reference")

    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(58, height - 118, "Incident Summary")
    pdf.setFont("Helvetica", 10)
    y = _draw_wrapped_text(pdf, fields.get("description") or "No report details available.", 58, height - 136, width - 116, 12)

    blocks = [
        ("Hazard Type", fields.get("hazard_type") or "-"),
        ("Immediate Action", fields.get("immediate_action") or "-"),
        ("Preventive Action", fields.get("preventive_action") or "-"),
        ("Responsible Person", fields.get("responsible_person") or "-"),
        ("Deadline", fields.get("deadline") or "-"),
        ("Status", fields.get("status") or "-"),
    ]

    y -= 10
    for label, value in blocks:
        if y < 90:
            break
        pdf.setFillColor(palette["accent"])
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(58, y, label)
        pdf.setFillColor(palette["text"])
        pdf.setFont("Helvetica", 10)
        y = _draw_wrapped_text(pdf, value, 160, y, width - 220, 12)
        y -= 8


def _build_report_pdf(report: Report) -> BytesIO:
    fields = _parse_report_content(report.content or "")
    layout_style = (fields.get("layout_style") or "classic").strip().lower()
    if layout_style not in {"classic", "executive", "audit", "reference"}:
        layout_style = "classic"
    palette = _style_palette(layout_style, fields)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    reference_path = _resolve_local_storage_path(fields.get("layout_reference_url"))
    reference_suffix = Path(reference_path).suffix.lower() if reference_path else ""
    company_name = fields.get("company_name") or "Safety AI Platform"
    company_address = fields.get("company_address") or "Worksite address pending"
    margin_style = fields.get("layout_margin_style") or "wide-frame"
    header_style = fields.get("layout_header_style") or "image-band"

    pdf.setTitle(f"report_{report.id}")
    if reference_path and reference_suffix in {".png", ".jpg", ".jpeg"}:
        _draw_reference_background(pdf, reference_path, width, height)
        _draw_reference_cover(pdf, width, height, report, fields)
        pdf.showPage()
        _draw_reference_background(pdf, reference_path, width, height)
        _draw_reference_content_page(
            pdf,
            width,
            height,
            report,
            fields,
            palette,
            fields.get("layout_reference_name"),
        )
        pdf.setFillColor(palette["header"])
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(58, height - 108, company_name)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(58, height - 122, company_address[:95])
        if fields.get("layout_reference_name") or fields.get("layout_reference_url"):
            pdf.setFillColor(palette["text"])
            pdf.setFont("Helvetica", 9)
            pdf.drawString(44, 20, f"Reference asset: {fields.get('layout_reference_name') or fields.get('layout_reference_url')}")
        pdf.save()
        buffer.seek(0)
        return buffer

    frame_inset = 44
    frame_radius = 18
    if margin_style == "double-frame":
        pdf.setStrokeColor(palette["accent"])
        pdf.setLineWidth(2)
        pdf.roundRect(28, 28, width - 56, height - 56, 22, fill=0, stroke=1)
        pdf.roundRect(40, 40, width - 80, height - 80, 18, fill=0, stroke=1)
    elif margin_style == "rounded-frame":
        frame_inset = 36
        frame_radius = 26
    elif margin_style == "banded-frame":
        pdf.setFillColor(colors.Color(0.96, 0.98, 1, alpha=1))
        pdf.rect(0, height - 120, width, 120, fill=1, stroke=0)

    pdf.setFillColor(palette["header"])
    if header_style == "boxed-header":
        pdf.roundRect(frame_inset, height - 126, width - (frame_inset * 2), 64, frame_radius, fill=1, stroke=0)
    elif header_style == "split-banner":
        pdf.roundRect(frame_inset, height - 126, width - (frame_inset * 2), 36, frame_radius, fill=1, stroke=0)
        pdf.setFillColor(palette["accent"])
        pdf.roundRect(frame_inset, height - 88, width - (frame_inset * 2), 26, frame_radius, fill=1, stroke=0)
        pdf.setFillColor(palette["header"])
    else:
        pdf.roundRect(frame_inset, height - 118, width - (frame_inset * 2), 54, frame_radius, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(62, height - 85, company_name)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(62, height - 100, company_address[:78])
    pdf.drawRightString(width - 62, height - 84, fields.get("report_id") or f"Safety Report #{report.id}")

    pdf.setFillColor(palette["accent"])
    pdf.roundRect(44, height - 155, 170, 24, 10, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(56, height - 146, f"Risk Level: {_risk_level_from_severity(report.severity)}")

    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica", 10)
    meta_pairs = [
        ("Project", str(report.project_id or "-")),
        ("Date", fields.get("date") or "-"),
        ("Time", fields.get("time") or "-"),
        ("Created", report.created_at.strftime("%Y-%m-%d %H:%M") if report.created_at else "-"),
        ("Location", fields.get("location") or "-"),
        ("Department", fields.get("department") or "-"),
    ]
    meta_y = height - 190
    for index, (label, value) in enumerate(meta_pairs):
        x = 52 if index % 2 == 0 else width / 2 + 10
        if index and index % 2 == 0:
            meta_y -= 24
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x, meta_y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x + 54, meta_y, value[:42])

    box_top = height - 262
    sections = [
        ("Incident Summary", fields.get("description") or "No report details available."),
        ("Hazard And Controls", "\n".join([
            f"Hazard Type: {fields.get('hazard_type') or '-'}",
            f"Immediate Action: {fields.get('immediate_action') or '-'}",
            f"Preventive Action: {fields.get('preventive_action') or '-'}",
        ])),
        ("Assignments And Approval", "\n".join([
            f"Responsible Person: {fields.get('responsible_person') or '-'}",
            f"Deadline: {fields.get('deadline') or '-'}",
            f"Status: {fields.get('status') or '-'}",
            f"Root Cause: {fields.get('root_cause') or '-'}",
        ])),
    ]

    for section_title, section_text in sections:
        if box_top < 130:
            pdf.showPage()
            box_top = height - 72
        pdf.setFillColor(palette["panel"])
        pdf.roundRect(44, box_top - 96, width - 88, 88, 14, fill=1, stroke=0)
        pdf.setFillColor(palette["header"])
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(58, box_top - 26, section_title)
        pdf.setFillColor(palette["text"])
        pdf.setFont("Helvetica", 10)
        text_y = box_top - 44
        for paragraph in section_text.splitlines():
            text_y = _draw_wrapped_text(pdf, paragraph, 58, text_y, width - 120, 12)
        box_top -= 108

    if fields.get("layout_reference_name") or fields.get("layout_reference_url"):
        pdf.setFillColor(palette["accent"])
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(44, 66, "Layout Reference")
        pdf.setFillColor(palette["text"])
        pdf.setFont("Helvetica", 9)
        reference_text = fields.get("layout_reference_name") or fields.get("layout_reference_url") or "-"
        _draw_wrapped_text(pdf, reference_text, 44, 52, width - 88, 11)

    pdf.save()
    buffer.seek(0)
    return buffer


# Generate Report
@router.post("/generate-report")
async def generate_report(
    project_id: int,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.company_id == user.company_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    hazards = "Slip hazard near machine"
    risk_score = "High"

    task = generate_report_task.delay(project_id, hazards, risk_score)

    log_activity(
        db,
        user.user_id,
        "Generated safety report",
        event_type="user",
        details=f"Started report generation for project {project_id} with task {task.id}",
        company_id=user.company_id,
    )

    notify_report_generated(
        db,
        company_id=user.company_id,
        project=project.name,
        task_id=str(task.id),
    )

    return {
        "message": "Report generation started",
        "task_id": task.id
    }


@router.post("/reports", status_code=201)
async def create_report_record(
    payload: ReportCreatePayload,
    db: Session = Depends(get_db),
):
    report = Report(
        company_id=_resolve_report_company_id(db, payload.project_id),
        project_id=payload.project_id,
        content=_build_report_content(payload),
        severity=_severity_score_from_risk_level(payload.risk_level),
        likelihood=_severity_score_from_risk_level(payload.risk_level),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    log_activity(
        db,
        None,
        "Created incident report record",
        event_type="system",
        details=f"Created report {report.id} from frontend incident form",
        company_id=report.company_id,
    )

    return {
        "id": report.id,
        "message": "Report saved",
    }


@router.post("/reports/layout-preview")
async def generate_layout_preview(payload: LayoutPreviewPayload):
    plan = _ai_layout_plan(payload)
    plan["layout_reference_url"] = payload.layout_reference_url
    plan["layout_reference_name"] = payload.layout_reference_name
    return plan


@router.get("/reports")
def list_reports(
    db: Session = Depends(get_db),
):
    demo_company_id = _resolve_report_company_id(db, None)
    rows = (
        db.query(Report)
        .filter(Report.company_id == demo_company_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [_serialize_report(row) for row in rows]


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = _get_demo_report(db, report_id)
    return _serialize_report(report)


@router.get("/reports/{report_id}/download")
def download_report_record(report_id: int, db: Session = Depends(get_db)):
    report = _get_demo_report(db, report_id)
    pdf_buffer = _build_report_pdf(report)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="report_{report.id}.pdf"'
        },
    )


@router.get("/projects/{project_id}/safety-score")
def get_project_safety_score(
    project_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "manager", "worker")),
):
    reports = (
        db.query(Report)
        .filter(Report.project_id == project_id, Report.company_id == user.company_id)
        .all()
    )

    if reports:
        hazards = len(reports)
        critical = sum(
            1
            for report in reports
            if (report.severity or 0) >= 4 or (report.likelihood or 0) >= 4
        )
        avg_severity = round(
            sum((report.severity or 1) for report in reports) / hazards
        )
        avg_likelihood = round(
            sum((report.likelihood or 1) for report in reports) / hazards
        )
    else:
        hazards = 0
        critical = 0
        avg_severity = 2
        avg_likelihood = 2

    score = calculate_safety_score(avg_severity, avg_likelihood)
    recommendations = critical * 2 if hazards else 0

    return {
        "project_id": project_id,
        "score": score,
        "risk_level": _risk_level_from_score(score),
        "hazards": hazards,
        "critical": critical,
        "recommendations": recommendations,
    }


# Download Report
@router.get("/download-report")
def download_report(
    file_name: str,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):

    file_path = os.path.join(STORAGE_DIR, file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    log_activity(
        db,
        user.user_id,
        "Downloaded safety report",
        event_type="user",
        details=f"Downloaded file {file_name}",
        company_id=user.company_id,
    )

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/pdf"
    )
