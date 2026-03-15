from sqlalchemy.orm import Session

from backend.database.models import User, UserAccountState


def get_or_create_account_state(db: Session, user: User) -> UserAccountState:
    state = db.query(UserAccountState).filter(UserAccountState.user_id == user.id).first()
    if state:
        return state

    state = UserAccountState(user_id=user.id, is_active=1)
    db.add(state)
    db.flush()
    return state


def is_user_active(db: Session, user: User | None) -> bool:
    if user is None:
        return False
    state = get_or_create_account_state(db, user)
    return bool(state.is_active)


def set_user_active(db: Session, user: User, is_active: bool) -> UserAccountState:
    state = get_or_create_account_state(db, user)
    state.is_active = 1 if is_active else 0
    db.flush()
    return state
