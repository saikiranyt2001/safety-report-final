from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.database.models import Equipment, EquipmentInspection
from backend.services import task_service


VALID_EQUIPMENT_STATUSES = {"safe", "inspection_due", "under_repair"}
VALID_INSPECTION_RESULTS = {"passed", "failed", "needs_attention"}


def _normalize_equipment_status(value: str | None) -> str:
    normalized = (value or "safe").strip().lower()
    return normalized if normalized in VALID_EQUIPMENT_STATUSES else "safe"


def _normalize_inspection_result(value: str | None) -> str:
    normalized = (value or "passed").strip().lower()
    return normalized if normalized in VALID_INSPECTION_RESULTS else "passed"


def _equipment_to_dict(equipment: Equipment) -> dict:
    return {
        "id": equipment.id,
        "name": equipment.name,
        "location": equipment.location or "",
        "serial_number": equipment.serial_number or "",
        "status": equipment.status,
        "inspection_interval_days": equipment.inspection_interval_days,
        "last_inspection_date": equipment.last_inspection_date.isoformat() if equipment.last_inspection_date else None,
        "next_inspection_date": equipment.next_inspection_date.isoformat() if equipment.next_inspection_date else None,
        "created_at": equipment.created_at.isoformat() if equipment.created_at else None,
        "updated_at": equipment.updated_at.isoformat() if equipment.updated_at else None,
    }


def _inspection_to_dict(inspection: EquipmentInspection) -> dict:
    return {
        "id": inspection.id,
        "equipment_id": inspection.equipment_id,
        "equipment_name": inspection.equipment.name if inspection.equipment else None,
        "equipment_location": inspection.equipment.location if inspection.equipment else None,
        "inspector_id": inspection.inspector_id,
        "inspector_name": inspection.inspector.username if inspection.inspector else None,
        "status": inspection.status,
        "inspection_date": inspection.inspection_date.isoformat() if inspection.inspection_date else None,
        "checklist_summary": inspection.checklist_summary or "",
        "issues_found": inspection.issues_found or "",
        "maintenance_task_id": inspection.maintenance_task_id,
    }


def create_equipment(
    db: Session,
    company_id: int | None,
    name: str,
    location: str = "",
    serial_number: str = "",
    inspection_interval_days: int = 30,
    status: str = "safe",
) -> Equipment:
    interval_days = max(1, inspection_interval_days)
    equipment = Equipment(
        company_id=company_id,
        name=name,
        location=location,
        serial_number=serial_number,
        inspection_interval_days=interval_days,
        status=_normalize_equipment_status(status),
        next_inspection_date=datetime.utcnow() + timedelta(days=interval_days),
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def list_equipment(db: Session, company_id: int | None, status: str | None = None) -> list[Equipment]:
    query = db.query(Equipment).filter(Equipment.company_id == company_id)
    if status:
        query = query.filter(Equipment.status == _normalize_equipment_status(status))
    return query.order_by(Equipment.created_at.desc()).all()


def get_equipment(db: Session, company_id: int | None, equipment_id: int) -> Equipment | None:
    return (
        db.query(Equipment)
        .filter(Equipment.id == equipment_id, Equipment.company_id == company_id)
        .first()
    )


def add_inspection(
    db: Session,
    company_id: int | None,
    equipment_id: int,
    inspector_id: int | None,
    status: str,
    checklist_summary: str = "",
    issues_found: str = "",
    create_maintenance_task: bool = False,
    task_priority: str = "high",
    assign_to_id: int | None = None,
) -> EquipmentInspection | None:
    equipment = get_equipment(db, company_id, equipment_id)
    if not equipment:
        return None

    normalized_status = _normalize_inspection_result(status)
    maintenance_task_id = None

    if create_maintenance_task and normalized_status != "passed":
        task = task_service.create_task(
            db,
            company_id=company_id,
            title=f"Maintenance required for {equipment.name}",
            description=issues_found or checklist_summary or "Inspection issue detected",
            hazard_type=f"Equipment: {equipment.name}",
            priority=task_priority,
            assigned_to_id=assign_to_id,
            created_by_id=inspector_id,
        )
        maintenance_task_id = task.id

    inspection_date = datetime.utcnow()
    inspection = EquipmentInspection(
        company_id=company_id,
        equipment_id=equipment_id,
        inspector_id=inspector_id,
        status=normalized_status,
        inspection_date=inspection_date,
        checklist_summary=checklist_summary,
        issues_found=issues_found,
        maintenance_task_id=maintenance_task_id,
    )
    db.add(inspection)

    equipment.last_inspection_date = inspection_date
    equipment.next_inspection_date = inspection_date + timedelta(days=equipment.inspection_interval_days)
    if normalized_status == "passed":
        equipment.status = "safe"
    elif normalized_status == "failed":
        equipment.status = "under_repair"
    else:
        equipment.status = "inspection_due"
    equipment.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(inspection)
    return inspection


def get_inspection_history(db: Session, company_id: int | None, equipment_id: int) -> list[EquipmentInspection]:
    return (
        db.query(EquipmentInspection)
        .filter(
            EquipmentInspection.equipment_id == equipment_id,
            EquipmentInspection.company_id == company_id,
        )
        .order_by(EquipmentInspection.inspection_date.desc())
        .all()
    )


def list_all_inspections(db: Session, company_id: int | None) -> list[EquipmentInspection]:
    return (
        db.query(EquipmentInspection)
        .filter(EquipmentInspection.company_id == company_id)
        .order_by(EquipmentInspection.inspection_date.desc())
        .all()
    )


def equipment_summary(db: Session, company_id: int | None) -> dict:
    equipment_list = db.query(Equipment).filter(Equipment.company_id == company_id).all()
    counts = {"safe": 0, "inspection_due": 0, "under_repair": 0}

    for item in equipment_list:
        status = item.status if item.status in counts else "safe"
        counts[status] += 1

    return {"total": len(equipment_list), **counts}
