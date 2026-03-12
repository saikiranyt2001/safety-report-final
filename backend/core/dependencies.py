# Dependency functions for FastAPI

# Add reusable dependency functions (e.g., get_db, get_current_user)
from backend.database.database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session


def get_database(db: Session = Depends(get_db)):
    return db
