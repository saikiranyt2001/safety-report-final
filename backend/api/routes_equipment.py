from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services import equipment_service
from backend.services.activity_service import log_activity

router = APIRouter(tags=["Equipment"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class EquipmentCreate(BaseModel):
    name: str
    location: str = ""
    serial_number: str = ""
    inspection_interval_days: int = 30
    status: str = "safe"


class EquipmentInspectionCreate(BaseModel):
    status: str
    checklist_summary: str = ""
    issues_found: str = ""
    create_maintenance_task: bool = False
    task_priority: str = "high"
    assign_to_id: Optional[int] = None


@router.get("/equipment/summary")
def get_equipment_summary(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    return equipment_service.equipment_summary(db, company_id=user.company_id)


@router.post("/equipment", status_code=201)
def create_equipment(
    payload: EquipmentCreate,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    equipment = equipment_service.create_equipment(
        db,
        company_id=user.company_id,
        name=payload.name,
        location=payload.location,
        serial_number=payload.serial_number,
        inspection_interval_days=payload.inspection_interval_days,
        status=payload.status,
    )
    log_activity(
        db,
        user.user_id,
        "Created equipment record",
        event_type="equipment",
        details=f"Equipment '{payload.name}' registered",
        company_id=user.company_id,
    )
    return equipment_service._equipment_to_dict(equipment)


@router.get("/equipment")
def list_equipment(
    status: Optional[str] = Query(None),
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    items = equipment_service.list_equipment(db, company_id=user.company_id, status=status)
    return [equipment_service._equipment_to_dict(item) for item in items]


@router.post("/equipment/{equipment_id}/inspection", status_code=201)
def add_equipment_inspection(
    equipment_id: int,
    payload: EquipmentInspectionCreate,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    inspection = equipment_service.add_inspection(
        db,
        company_id=user.company_id,
        equipment_id=equipment_id,
        inspector_id=user.user_id,
        status=payload.status,
        checklist_summary=payload.checklist_summary,
        issues_found=payload.issues_found,
        create_maintenance_task=payload.create_maintenance_task,
        task_priority=payload.task_priority,
        assign_to_id=payload.assign_to_id,
    )
    if not inspection:
        raise HTTPException(status_code=404, detail="Equipment not found")

    details = f"Inspection added for equipment {equipment_id} with status {inspection.status}"
    if inspection.maintenance_task_id:
        details += f"; maintenance task #{inspection.maintenance_task_id} created"

    log_activity(
        db,
        user.user_id,
        "Completed equipment inspection",
        event_type="equipment",
        details=details,
        company_id=user.company_id,
    )
    return equipment_service._inspection_to_dict(inspection)


@router.get("/equipment/{equipment_id}/inspections")
def get_equipment_inspections(
    equipment_id: int,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    equipment = equipment_service.get_equipment(db, user.company_id, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    history = equipment_service.get_inspection_history(db, user.company_id, equipment_id)
    return [equipment_service._inspection_to_dict(item) for item in history]


@router.get("/equipment/inspections")
def list_all_equipment_inspections(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    history = equipment_service.list_all_inspections(db, company_id=user.company_id)
    return [equipment_service._inspection_to_dict(item) for item in history]
