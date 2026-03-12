from backend.database.database import SessionLocal
from backend.database.models import Project


def create_project(name, description):

    db = SessionLocal()

    project = Project(
        name=name,
        description=description
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


def get_projects():

    db = SessionLocal()

    return db.query(Project).all()