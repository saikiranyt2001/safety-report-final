import os
import json
from io import BytesIO
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import Company, Project, Report
from backend.agents.safety_score_agent import calculate_safety_score
from backend.core.rbac import require_roles
from backend.core.ai_client import chat_completion
from backend.services.activity_service import log_activity
from backend.services.notification_service import notify_incident_reported, notify_report_generated
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
    contributing_hazards: str | None = None
    risk_assessment_basis: str | None = None
    ppe_info: str | None = None
    risk_score: int | None = None
    severity: str | None = None
    probability: str | None = None
    root_cause: str | None = None
    control_implementation: str | None = None
    compliance_references: str | None = None
    immediate_action: str | None = None
    preventive_action: str | None = None
    responsible_person: str | None = None
    deadline: str | None = None
    status: str | None = None
    reporter_name: str | None = None
    reporter_signature: str | None = None
    reporter_date: str | None = None
    supervisor_name: str | None = None
    supervisor_signature: str | None = None
    supervisor_date: str | None = None
    safety_name: str | None = None
    safety_signature: str | None = None
    safety_date: str | None = None
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
    layout_template_style: str | None = None


class LayoutPreviewPayload(BaseModel):
    company_name: str | None = None
    company_address: str | None = None
    layout_reference_url: str | None = None
    layout_reference_name: str | None = None
    layout_primary_color: str | None = None
    layout_accent_color: str | None = None


class RiskAnalysisPayload(BaseModel):
    hazard_type: str | None = None
    risk_level: str | None = None
    description: str | None = None
    location: str | None = None
    department: str | None = None


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
    "contributing_hazards": "Contributing Hazards",
    "risk_assessment_basis": "Risk Assessment Basis",
    "ppe_info": "PPE Information",
    "risk_score": "Risk Score",
    "severity": "Severity Label",
    "probability": "Probability",
    "root_cause": "Root Cause",
    "control_implementation": "Control Implementation",
    "compliance_references": "Compliance References",
    "immediate_action": "Immediate Action",
    "preventive_action": "Preventive Action",
    "responsible_person": "Responsible Person",
    "deadline": "Deadline",
    "status": "Status",
    "reporter_name": "Reporter Name",
    "reporter_signature": "Reporter Signature",
    "reporter_date": "Reporter Date",
    "supervisor_name": "Supervisor Name",
    "supervisor_signature": "Supervisor Signature",
    "supervisor_date": "Supervisor Date",
    "safety_name": "Safety Name",
    "safety_signature": "Safety Signature",
    "safety_date": "Safety Date",
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
    "layout_template_style": "Layout Template Style",
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
        "template_style": "incident-grid",
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
        "Return compact JSON only with keys: margin_style, header_style, template_style, preview_note. "
        "Allowed margin_style values: wide-frame, double-frame, rounded-frame, banded-frame. "
        "Allowed header_style values: image-band, boxed-header, top-ribbon, split-banner. "
        "Allowed template_style values: incident-grid, compact-grid. "
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
            "template_style": parsed.get("template_style") or "incident-grid",
            "preview_note": parsed.get("preview_note") or "AI generated a template-aware outer frame.",
            "company_name": payload.company_name or "Safety AI Platform",
            "company_address": payload.company_address or "Worksite address pending",
            "primary_color": payload.layout_primary_color or "#364fc7",
            "accent_color": payload.layout_accent_color or "#0c8599",
        }
    except Exception:
        return _fallback_layout_plan(payload)


def _enhance_report_fields(payload: ReportCreatePayload) -> dict[str, str]:
    prompt = (
        "You improve safety report text while preserving facts. "
        "Return compact JSON with keys: description, root_cause, immediate_action, preventive_action. "
        "Keep each field concise, professional, and actionable. "
        f"Description: {payload.description or '-'}\n"
        f"Root Cause: {payload.root_cause or '-'}\n"
        f"Immediate Action: {payload.immediate_action or '-'}\n"
        f"Preventive Action: {payload.preventive_action or '-'}"
    )
    try:
        raw = chat_completion(prompt, max_tokens=260)
        parsed = _extract_json_object(raw or "") or {}
        return {
            "description": (parsed.get("description") or payload.description or "").strip(),
            "root_cause": (parsed.get("root_cause") or payload.root_cause or "").strip(),
            "immediate_action": (parsed.get("immediate_action") or payload.immediate_action or "").strip(),
            "preventive_action": (parsed.get("preventive_action") or payload.preventive_action or "").strip(),
        }
    except Exception:
        return {
            "description": (payload.description or "").strip(),
            "root_cause": (payload.root_cause or "").strip(),
            "immediate_action": (payload.immediate_action or "").strip(),
            "preventive_action": (payload.preventive_action or "").strip(),
        }


def _ai_risk_analysis(payload: RiskAnalysisPayload) -> dict[str, str | int]:
    prompt = (
        "You are a safety risk analyst. "
        "Return compact JSON only with keys: score, severity, probability. "
        "score must be integer 0-100. "
        "severity must be one of: Minor, Moderate, Major, Catastrophic. "
        "probability must be one of: Rare, Unlikely, Possible, Likely, Almost Certain. "
        f"Hazard Type: {payload.hazard_type or '-'}\n"
        f"Risk Level: {payload.risk_level or '-'}\n"
        f"Description: {payload.description or '-'}\n"
        f"Location: {payload.location or '-'}\n"
        f"Department: {payload.department or '-'}"
    )
    try:
        raw = chat_completion(prompt, max_tokens=140)
        parsed = _extract_json_object(raw or "") or {}
        score = int(parsed.get("score", 50))
        score = max(0, min(100, score))
        severity = str(parsed.get("severity") or "Moderate").strip()
        probability = str(parsed.get("probability") or "Possible").strip()

        allowed_severity = {"Minor", "Moderate", "Major", "Catastrophic"}
        allowed_probability = {"Rare", "Unlikely", "Possible", "Likely", "Almost Certain"}
        if severity not in allowed_severity:
            severity = "Moderate"
        if probability not in allowed_probability:
            probability = "Possible"

        return {
            "engine": "AI",
            "score": score,
            "severity": severity,
            "probability": probability,
        }
    except Exception:
        # Conservative fallback if AI is unavailable.
        base_score = 50
        level = (payload.risk_level or "").strip().lower()
        if level == "low":
            base_score = 35
        elif level == "medium":
            base_score = 55
        elif level == "high":
            base_score = 75
        elif level == "critical":
            base_score = 90

        return {
            "engine": "RULES",
            "score": base_score,
            "severity": "Moderate" if base_score < 70 else "Major",
            "probability": "Possible" if base_score < 70 else "Likely",
        }


def _validate_report_payload(payload: ReportCreatePayload) -> dict[str, list[str]]:
    required_pairs = [
        ("date", "Date"),
        ("time", "Time"),
        ("location", "Location"),
        ("department", "Department"),
        ("hazard_type", "Hazard Type"),
        ("risk_level", "Risk Level"),
        ("description", "Description"),
        ("immediate_action", "Immediate Action"),
        ("preventive_action", "Preventive Action"),
        ("responsible_person", "Responsible Person"),
        ("deadline", "Deadline"),
        ("status", "Status"),
        ("reporter_name", "Reporter Name"),
        ("reporter_date", "Reporter Date"),
        ("supervisor_name", "Supervisor Name"),
        ("supervisor_date", "Supervisor Date"),
        ("safety_name", "Safety Officer Name"),
        ("safety_date", "Safety Officer Date"),
    ]

    missing_fields = [label for key, label in required_pairs if not (getattr(payload, key, None) or "").strip()]
    warnings: list[str] = []

    if (payload.deadline or "").strip() and (payload.date or "").strip():
        try:
            event_date = datetime.strptime(payload.date, "%Y-%m-%d")
            due_date = datetime.strptime(payload.deadline, "%Y-%m-%d")
            if due_date < event_date:
                warnings.append("Deadline is earlier than incident date.")
        except Exception:
            warnings.append("Date format appears invalid for date/deadline.")

    return {
        "missing_fields": missing_fields,
        "warnings": warnings,
    }


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
    paragraphs = (text or "-").splitlines() or ["-"]
    lines: list[str] = []

    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
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


def _draw_reference_outer_border(
    pdf: canvas.Canvas,
    width: float,
    height: float,
) -> None:
    # Keep only the border vibe from the reference by masking the inner body area.
    pdf.setFillColor(colors.Color(1, 1, 1, alpha=0.94))
    pdf.roundRect(34, 30, width - 68, height - 60, 18, fill=1, stroke=0)


def _draw_template_section(
    pdf: canvas.Canvas,
    title: str,
    x: float,
    y: float,
    width: float,
    height: float,
    header_color: colors.Color,
    body_color: colors.Color,
    text_color: colors.Color,
    text: str,
) -> None:
    pdf.setFillColor(body_color)
    pdf.roundRect(x, y - height, width, height, 8, fill=1, stroke=0)
    pdf.setFillColor(header_color)
    pdf.roundRect(x, y - 18, width, 18, 8, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(x + 8, y - 12, title)
    pdf.setFillColor(text_color)
    pdf.setFont("Helvetica", 9)
    _draw_wrapped_text(pdf, text or "-", x + 8, y - 30, width - 16, 10)


def _draw_label_value(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    label: str,
    value: str,
    label_color: colors.Color,
    text_color: colors.Color,
    max_width: float,
) -> None:
    def _fit_text_to_width(text: str, width: float) -> str:
        raw = (text or "-").strip() or "-"
        if pdf.stringWidth(raw, "Helvetica", 8) <= width:
            return raw
        ellipsis = "..."
        trimmed = raw
        while trimmed and pdf.stringWidth(trimmed + ellipsis, "Helvetica", 8) > width:
            trimmed = trimmed[:-1]
        return (trimmed + ellipsis) if trimmed else ellipsis

    pdf.setFillColor(label_color)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(x, y, label)
    label_width = pdf.stringWidth(label, "Helvetica-Bold", 8)
    value_x = x + label_width + 4
    value_width = max(20, max_width - (value_x - x))
    pdf.setFillColor(text_color)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(value_x, y, _fit_text_to_width(value or "-", value_width))


def _draw_reference_template_page(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    report: Report,
    fields: dict[str, str],
    palette: dict[str, colors.Color | tuple[colors.Color, colors.Color]],
    company_name: str,
    company_address: str,
) -> None:
    header_color = palette["header"]
    accent_color = palette["accent"]
    text_color = palette["text"]
    panel_color = colors.Color(1, 1, 1, alpha=0.94)

    # Hazard stripe with tighter spacing to match uploaded template proportion.
    stripe_y_top = height - 50
    stripe_y_bottom = 34
    stripe_step = 16
    stripe_w = 16
    stripe_h = 14
    for i in range(0, int(width), stripe_step):
        fill = colors.HexColor("#111827") if (i // stripe_step) % 2 == 0 else colors.HexColor("#fbbf24")
        pdf.setFillColor(fill)
        pdf.rect(i, stripe_y_top, stripe_w, stripe_h, fill=1, stroke=0)
        pdf.rect(i, stripe_y_bottom, stripe_w, stripe_h, fill=1, stroke=0)

    pdf.setFillColor(panel_color)
    panel_x = 44
    panel_y = 54
    panel_w = width - 88
    panel_h = height - 118
    pdf.roundRect(panel_x, panel_y, panel_w, panel_h, 10, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    header_x = 56
    header_y = height - 108
    header_w = width - 112
    header_h = 34
    pdf.roundRect(header_x, header_y, header_w, header_h, 8, fill=1, stroke=0)
    pdf.setStrokeColor(colors.Color(0.2, 0.25, 0.34, alpha=0.35))
    pdf.setLineWidth(0.8)
    pdf.roundRect(header_x, header_y, header_w, header_h, 8, fill=0, stroke=1)

    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(header_x + 10, height - 95, "SAFETY INCIDENT REPORT")

    # Metadata row aligned in four equal blocks.
    meta_x = 56
    meta_y = height - 124
    meta_h = 16
    meta_w = width - 112
    cell_w = meta_w / 4
    pdf.setFillColor(colors.HexColor("#f8fafc"))
    pdf.rect(meta_x, meta_y, meta_w, meta_h, fill=1, stroke=0)
    pdf.setStrokeColor(colors.Color(0.2, 0.25, 0.34, alpha=0.2))
    pdf.setLineWidth(0.6)
    pdf.rect(meta_x, meta_y, meta_w, meta_h, fill=0, stroke=1)
    for idx in range(1, 4):
        divider_x = meta_x + cell_w * idx
        pdf.line(divider_x, meta_y, divider_x, meta_y + meta_h)

    _draw_label_value(pdf, meta_x + 6, meta_y + 5, "ID:", fields.get("report_id") or f"INC-{report.id:04d}", colors.HexColor("#374151"), text_color, cell_w - 12)
    _draw_label_value(pdf, meta_x + cell_w + 6, meta_y + 5, "Date:", fields.get("date") or "-", colors.HexColor("#374151"), text_color, cell_w - 12)
    _draw_label_value(pdf, meta_x + (cell_w * 2) + 6, meta_y + 5, "Time:", fields.get("time") or "-", colors.HexColor("#374151"), text_color, cell_w - 12)
    _draw_label_value(pdf, meta_x + (cell_w * 3) + 6, meta_y + 5, "Dept:", fields.get("department") or "-", colors.HexColor("#374151"), text_color, cell_w - 12)

    pdf.setFillColor(text_color)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.setFillColor(header_color)
    pdf.drawString(66, height - 134, company_name[:54])
    pdf.setFillColor(text_color)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(66, height - 145, company_address[:86])

    left_x = 62
    right_x = width / 2 + 6
    col_w = width / 2 - 74
    top_y = height - 170

    # Top row mirrors details + incident snapshot split.
    _draw_template_section(
        pdf, "1. INCIDENT DETAILS", left_x, top_y, col_w, 126,
        header_color, colors.Color(1, 1, 1, alpha=0.96), text_color,
        f"Location: {fields.get('location') or '-'}\nEmployee: {fields.get('employee_name') or '-'}\nRole: {fields.get('role') or '-'}\nHazard: {fields.get('hazard_type') or '-'}\nRisk: {fields.get('risk_level') or '-'}",
    )

    pdf.setFillColor(colors.Color(1, 1, 1, alpha=0.96))
    pdf.roundRect(right_x, top_y - 126, col_w, 126, 8, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#1f2937"))
    pdf.roundRect(right_x, top_y - 18, col_w, 18, 8, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(right_x + 8, top_y - 12, "2. INCIDENT SNAPSHOT")
    pdf.setFillColor(colors.HexColor("#f1f5f9"))
    pdf.roundRect(right_x + 8, top_y - 118, col_w - 16, 94, 4, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#64748b"))
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(right_x + (col_w / 2), top_y - 74, "Field Area")

    _draw_template_section(
        pdf, "3. DESCRIPTION OF INCIDENT", left_x, top_y - 140, col_w, 114,
        colors.HexColor("#1f2937"), colors.Color(1, 1, 1, alpha=0.97), text_color,
        fields.get("description") or "-",
    )
    _draw_template_section(
        pdf, "4. ROOT CAUSE", right_x, top_y - 140, col_w, 114,
        colors.HexColor("#1f2937"), colors.Color(1, 1, 1, alpha=0.97), text_color,
        fields.get("root_cause") or "-",
    )

    _draw_template_section(
        pdf, "5. IMMEDIATE ACTION", left_x, top_y - 266, col_w, 88,
        accent_color, colors.Color(1, 1, 1, alpha=0.97), text_color,
        fields.get("immediate_action") or "-",
    )
    _draw_template_section(
        pdf, "6. CORRECTIVE ACTION", right_x, top_y - 266, col_w, 88,
        accent_color, colors.Color(1, 1, 1, alpha=0.97), text_color,
        fields.get("preventive_action") or "-",
    )

    _draw_template_section(
        pdf, "7. RESPONSIBLE / DEADLINE", left_x, top_y - 368, col_w, 74,
        header_color, colors.Color(1, 1, 1, alpha=0.97), text_color,
        f"Owner: {fields.get('responsible_person') or '-'}\nDeadline: {fields.get('deadline') or '-'}\nStatus: {fields.get('status') or '-'}",
    )
    _draw_template_section(
        pdf, "8. APPROVAL", right_x, top_y - 368, col_w, 96,
        header_color, colors.Color(1, 1, 1, alpha=0.97), text_color,
        "\n".join([
            f"Reporter: {(fields.get('reporter_name') or fields.get('employee_name') or '-')} ({fields.get('reporter_date') or fields.get('date') or '-'})",
            f"Supervisor: {(fields.get('supervisor_name') or fields.get('responsible_person') or '-')} ({fields.get('supervisor_date') or fields.get('deadline') or '-'})",
            f"Safety Officer: {(fields.get('safety_name') or company_name or '-')} ({fields.get('safety_date') or fields.get('date') or '-'})",
        ]),
    )


def _build_report_pdf(report: Report) -> BytesIO:
    fields = _parse_report_content(report.content or "")
    layout_style = (fields.get("layout_style") or "classic").strip().lower()
    if layout_style not in {"classic", "executive", "audit", "reference"}:
        layout_style = "classic"
    palette = _style_palette(layout_style, fields)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    reference_path = _resolve_local_storage_path(fields.get("layout_reference_url"))
    company_name = fields.get("company_name") or "Safety AI Platform"
    company_address = fields.get("company_address") or "Worksite address pending"
    margin_style = fields.get("layout_margin_style") or "wide-frame"
    header_style = fields.get("layout_header_style") or "image-band"

    pdf.setTitle(f"report_{report.id}")
    has_reference_image = bool(reference_path)
    if has_reference_image:
        _draw_reference_outer_border(pdf, width, height)
        _draw_reference_template_page(
            pdf,
            width,
            height,
            report,
            fields,
            palette,
            company_name,
            company_address,
        )
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

    notify_incident_reported(
        db,
        company_id=report.company_id,
        incident_id=report.id,
        incident_type=payload.hazard_type or "General Incident",
        severity=payload.risk_level or _risk_level_from_severity(report.severity),
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


@router.post("/reports/ai-risk-analysis")
async def generate_ai_risk_analysis(payload: RiskAnalysisPayload):
    return _ai_risk_analysis(payload)


@router.post("/reports/enhance-validate")
async def enhance_and_validate_report(payload: ReportCreatePayload):
    enhanced = _enhance_report_fields(payload)

    # Validate using enhanced text for required text fields.
    payload.description = enhanced.get("description") or payload.description
    payload.root_cause = enhanced.get("root_cause") or payload.root_cause
    payload.immediate_action = enhanced.get("immediate_action") or payload.immediate_action
    payload.preventive_action = enhanced.get("preventive_action") or payload.preventive_action

    validation = _validate_report_payload(payload)
    return {
        "enhanced_fields": enhanced,
        "validation": validation,
    }


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
