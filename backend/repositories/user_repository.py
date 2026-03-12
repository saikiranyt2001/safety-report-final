# User Repository

# Add database access logic for user-related operations.
from sqlalchemy.orm import Session
from backend.database.models import User


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, name: str, email: str, password: str):
    user = User(name=name, email=email, password=password)

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_all_users(db: Session):
    return db.query(User).all()