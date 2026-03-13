# Dependency functions for FastAPI

# Add reusable dependency functions (e.g., get_db, get_current_user)
from backend.database.database import get_db
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.security import get_current_user


def get_database(db: Session = Depends(get_db)):
    return db


def require_role(role: str):

    def role_checker(user=Depends(get_current_user)):
        user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if user_role != role:
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )
        return user

    return role_checker
