from sqlalchemy.orm import Session

from backend.database.models import InspectionTemplate, InspectionQuestion, InspectionResponse


# -------------------------
# Templates
# -------------------------

def create_template(
    db: Session,
    company_id: int | None,
    name: str,
    description: str,
    category: str | None = None,
    json_schema: dict | None = None,
    created_by_id: int | None = None,
):
    template = InspectionTemplate(
        company_id=company_id,
        name=name,
        description=description,
        category=category,
        json_schema=json_schema,
        created_by_id=created_by_id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def list_templates(db: Session, company_id: int | None):
    return (
        db.query(InspectionTemplate)
        .filter(InspectionTemplate.company_id == company_id)
        .order_by(InspectionTemplate.created_at.desc())
        .all()
    )


def get_template(db: Session, company_id: int | None, template_id: int):
    return (
        db.query(InspectionTemplate)
        .filter(InspectionTemplate.id == template_id, InspectionTemplate.company_id == company_id)
        .first()
    )


def update_template(
    db: Session,
    company_id: int | None,
    template_id: int,
    name: str,
    description: str,
    category: str | None = None,
    json_schema: dict | None = None,
):
    template = get_template(db, company_id, template_id)
    if not template:
        return None
    template.name = name
    template.description = description
    template.category = category
    template.json_schema = json_schema
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, company_id: int | None, template_id: int):
    template = get_template(db, company_id, template_id)
    if template:
        db.delete(template)
        db.commit()
    return template


# -------------------------
# Questions
# -------------------------

def add_question(
    db: Session,
    company_id: int | None,
    template_id: int,
    question_text: str,
    question_code: str | None = None,
    section_name: str | None = None,
    risk_level: str | None = None,
    question_type: str | None = None,
):
    template = get_template(db, company_id, template_id)
    if not template:
        return None
    count = (
        db.query(InspectionQuestion)
        .filter(InspectionQuestion.template_id == template_id)
        .count()
    )
    question = InspectionQuestion(
        template_id=template_id,
        question=question_text,
        question_code=question_code,
        section_name=section_name,
        risk_level=risk_level,
        question_type=question_type,
        order=count,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, company_id: int | None, question_id: int):
    question = (
        db.query(InspectionQuestion)
        .join(InspectionTemplate, InspectionQuestion.template_id == InspectionTemplate.id)
        .filter(
            InspectionQuestion.id == question_id,
            InspectionTemplate.company_id == company_id,
        )
        .first()
    )
    if question:
        db.delete(question)
        db.commit()
    return question


# -------------------------
# Responses (inspection fill)
# -------------------------

def submit_responses(
    db: Session,
    company_id: int | None,
    template_id: int,
    answers: list[dict],
    answered_by_id: int | None = None,
):
    template = get_template(db, company_id, template_id)
    if not template:
        return None

    valid_question_ids = {question.id for question in template.questions}
    created = []
    for item in answers:
        if item["question_id"] not in valid_question_ids:
            continue
        response = InspectionResponse(
            question_id=item["question_id"],
            company_id=company_id,
            answered_by_id=answered_by_id,
            answer=item.get("answer", "na"),
            notes=item.get("notes", ""),
        )
        db.add(response)
        created.append(response)
    db.commit()
    return created


def _template_to_dict(template: InspectionTemplate) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description or "",
        "category": template.category,
        "json_schema": template.json_schema,
        "created_by": template.created_by.username if template.created_by else "system",
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "question_count": len(template.questions),
        "questions": [
            {
                "id": q.id,
                "question": q.question,
                "question_code": q.question_code,
                "section_name": q.section_name,
                "risk_level": q.risk_level,
                "question_type": q.question_type,
                "order": q.order,
            }
            for q in template.questions
        ],
    }
