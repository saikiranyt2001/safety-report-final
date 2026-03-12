
# User Service Layer
# Business logic for user management

from sqlalchemy.orm import Session
from backend.database.models import User


def create_user(db: Session, name: str, email: str, password: str):
    """Create a new user"""

    user = User(
        name=name,
        email=email,
        password=password
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user(db: Session, user_id: int):
    """Get a single user by ID"""

    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    """Find user by email"""

    return db.query(User).filter(User.email == email).first()


def get_all_users(db: Session):
    """Return all users"""

    return db.query(User).all()


def delete_user(db: Session, user_id: int):
    """Delete a user"""

    user = db.query(User).filter(User.id == user_id).first()

    if user:
        db.delete(user)
        db.commit()

    return user
