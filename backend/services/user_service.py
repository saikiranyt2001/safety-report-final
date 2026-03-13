
from sqlalchemy.orm import Session
from backend.database.models import User


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db: Session, company_id: int | None):
    return (
        db.query(User)
        .filter(User.company_id == company_id)
        .order_by(User.username.asc())
        .all()
    )


def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        db.delete(user)
        db.commit()

    return user
