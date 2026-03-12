# Project Repository

# Add database access logic for project-related operations.

from sqlalchemy.orm import Session
from backend.database.models import Project


def create_project(db: Session, name: str, description: str):

    project = Project(
        name=name,
        description=description
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


def get_project(db: Session, project_id: int):

    return db.query(Project).filter(Project.id == project_id).first()




def delete_project(db: Session, project_id: int):

    project = db.query(Project).filter(Project.id == project_id).first()

    if project:
        db.delete(project)
        db.commit()

    return project
def get_projects_by_company(db: Session, company_id: int):

    return db.query(Project).filter(
        Project.company_id == company_id
    ).all()