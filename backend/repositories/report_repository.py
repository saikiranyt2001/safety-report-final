# Report Repository

# Add database access logic for report-related operations.
from sqlalchemy.orm import Session
from backend.database.models import Report


def create_report(db: Session, project_id: int, risk_level: str, content: str):
    """Create a new safety report"""

    report = Report(
        project_id=project_id,
        risk_level=risk_level,
        content=content
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


def get_report(db: Session, report_id: int):
    """Get report by ID"""

    return db.query(Report).filter(Report.id == report_id).first()


def get_reports_by_project(db: Session, project_id: int):
    """Get all reports for a project"""

    return db.query(Report).filter(Report.project_id == project_id).all()


def get_reports_by_company(db: Session, company_id: int):

    return db.query(Report).filter(
        Report.company_id == company_id
    ).all()


def delete_report(db: Session, report_id: int):
    """Delete report"""

    report = db.query(Report).filter(Report.id == report_id).first()

    if report:
        db.delete(report)
        db.commit()

    return report