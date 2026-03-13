from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services import inspection_service
from backend.services.activity_service import log_activity

router = APIRouter(tags=["Inspection"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- Pydantic models ----

class TemplateCreate(BaseModel):
    name: str
    description: str = ""


class QuestionCreate(BaseModel):
    question: str


class ResponseItem(BaseModel):
    question_id: int
    answer: str       # "pass" | "fail" | "na"
    notes: str = ""


class SubmitInspection(BaseModel):
    answers: list[ResponseItem]


# ---- Template CRUD ----

@router.get("/inspection-templates")
def list_templates(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    templates = inspection_service.list_templates(db, company_id=user.company_id)
    return [inspection_service._template_to_dict(t) for t in templates]


@router.post("/inspection-templates", status_code=201)
def create_template(
    payload: TemplateCreate,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    template = inspection_service.create_template(
        db,
        company_id=user.company_id,
        name=payload.name,
        description=payload.description,
        created_by_id=user.user_id,
    )
    log_activity(
        db,
        user.user_id,
        "Created inspection template",
        event_type="user",
        details=f"Template '{payload.name}' created",
        company_id=user.company_id,
    )
    return inspection_service._template_to_dict(template)


@router.get("/inspection-templates/{template_id}")
def get_template(
    template_id: int,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    template = inspection_service.get_template(db, user.company_id, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return inspection_service._template_to_dict(template)


@router.put("/inspection-templates/{template_id}")
def update_template(
    template_id: int,
    payload: TemplateCreate,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    template = inspection_service.update_template(
        db,
        user.company_id,
        template_id,
        payload.name,
        payload.description,
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    log_activity(
        db,
        user.user_id,
        "Updated inspection template",
        event_type="user",
        details=f"Template {template_id} renamed to '{payload.name}'",
        company_id=user.company_id,
    )
    return inspection_service._template_to_dict(template)


@router.delete("/inspection-templates/{template_id}")
def delete_template(
    template_id: int,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    template = inspection_service.delete_template(db, user.company_id, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    log_activity(
        db,
        user.user_id,
        "Deleted inspection template",
        event_type="user",
        details=f"Template {template_id} deleted",
        company_id=user.company_id,
    )
    return {"deleted": template_id}


# ---- Question management ----

@router.post("/inspection-templates/{template_id}/questions", status_code=201)
def add_question(
    template_id: int,
    payload: QuestionCreate,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    template = inspection_service.get_template(db, user.company_id, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    question = inspection_service.add_question(db, user.company_id, template_id, payload.question)
    if not question:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": question.id, "question": question.question, "order": question.order}


@router.delete("/inspection-questions/{question_id}")
def delete_question(
    question_id: int,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    question = inspection_service.delete_question(db, user.company_id, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"deleted": question_id}


# ---- Submit inspection responses ----

@router.post("/inspection-templates/{template_id}/respond")
def submit_inspection(
    template_id: int,
    payload: SubmitInspection,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    answers = [item.model_dump() for item in payload.answers]
    created = inspection_service.submit_responses(
        db,
        company_id=user.company_id,
        template_id=template_id,
        answers=answers,
        answered_by_id=user.user_id,
    )
    if created is None:
        raise HTTPException(status_code=404, detail="Template not found")

    pass_count = sum(1 for a in answers if a["answer"] == "pass")
    fail_count = sum(1 for a in answers if a["answer"] == "fail")
    total = len(answers)
    score = round((pass_count / total) * 100) if total else 0

    log_activity(
        db,
        user.user_id,
        "Submitted inspection checklist",
        event_type="user",
        details=f"Template {template_id}: {pass_count} pass, {fail_count} fail — score {score}%",
        company_id=user.company_id,
    )

    return {
        "template_id": template_id,
        "total": total,
        "pass": pass_count,
        "fail": fail_count,
        "score": score,
        "risk_level": "Low" if score >= 80 else "Medium" if score >= 60 else "High",
    }
