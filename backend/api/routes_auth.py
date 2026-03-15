from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.models import Company, RoleEnum, User
from backend.database.database import SessionLocal
from datetime import UTC, datetime, timedelta
from jose import jwt
from pydantic import BaseModel
from backend.core.config import settings
from backend.core.passwords import hash_password, verify_password
from backend.core.security import get_current_user_context
from backend.services.account_state_service import get_or_create_account_state, is_user_active
from backend.services.activity_service import log_activity

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

router = APIRouter()

class LoginData(BaseModel):
    username: str
    password: str


class SignupData(LoginData):
    company_name: str | None = None
    role: RoleEnum | None = RoleEnum.worker

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _unique_company_name(db: Session, base_name: str) -> str:
    candidate = (base_name or "Workspace").strip() or "Workspace"
    suffix = 1
    while db.query(Company).filter(Company.name == candidate).first():
        suffix += 1
        candidate = f"{base_name} {suffix}".strip()
    return candidate


def _ensure_user_company(db: Session, user: User) -> Company:
    if user.company_id:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        if company:
            return company

    company = Company(name=_unique_company_name(db, f"{user.username} Workspace"))
    db.add(company)
    db.flush()
    user.company_id = company.id
    db.commit()
    db.refresh(user)
    db.refresh(company)
    return company

# Signup
@router.post("/signup")
def signup(data: SignupData, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    requested_role = data.role or RoleEnum.worker
    if requested_role != RoleEnum.worker:
        raise HTTPException(status_code=403, detail="Public signup can only create worker accounts")

    company = Company(name=_unique_company_name(db, data.company_name or f"{data.username} Workspace"))
    db.add(company)
    db.flush()

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=RoleEnum.worker,
        company_id=company.id,
    )

    db.add(user)
    db.flush()
    get_or_create_account_state(db, user)
    db.commit()
    db.refresh(user)

    log_activity(
        db,
        user.id,
        "Created user account",
        event_type="user",
        details=f"User {user.username} was created with role {(user.role.value if user.role else RoleEnum.worker.value)}",
        company_id=user.company_id,
    )

    return {
        "message": "User created",
        "company": {"id": company.id, "name": company.name},
    }

# Login
@router.post("/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    is_valid, upgraded_hash = verify_password(data.password, user.password_hash if user else None)
    if not user or not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if upgraded_hash:
        user.password_hash = upgraded_hash
        db.commit()
        db.refresh(user)
    if not is_user_active(db, user):
        db.commit()
        raise HTTPException(status_code=403, detail="Account is inactive")

    company = _ensure_user_company(db, user)

    log_activity(
        db,
        user.id,
        "User login",
        event_type="user",
        details=f"User {user.username} logged in",
        company_id=user.company_id,
    )

    token = jwt.encode(
        {
            "sub": user.username,
            "user_id": user.id,
            "company_id": user.company_id,
            "role": user.role.value if user.role else RoleEnum.worker.value,
            "exp": datetime.now(UTC) + timedelta(hours=2)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value if user.role else RoleEnum.worker.value,
        "username": user.username,
        "company": {"id": company.id, "name": company.name},
    }
@router.get("/me")
def get_profile(current_user=Depends(get_current_user_context)):
    return {
        "username": current_user.username,
        "user_id": current_user.user_id,
        "company_id": current_user.company_id,
        "role": current_user.role,
    }
