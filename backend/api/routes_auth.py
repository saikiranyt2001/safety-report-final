from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.database.models import Company, RoleEnum, User
from backend.database.database import SessionLocal
from datetime import datetime, timedelta
from jose import JWTError, jwt
import hashlib
from pydantic import BaseModel
from backend.core.config import settings
from backend.services.activity_service import log_activity

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

class LoginData(BaseModel):
    username: str
    password: str


class SignupData(LoginData):
    company_name: str | None = None
    role: RoleEnum | None = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


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

    company = Company(name=_unique_company_name(db, data.company_name or f"{data.username} Workspace"))
    db.add(company)
    db.flush()

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role or RoleEnum.worker,
        company_id=company.id,
    )

    db.add(user)
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

    if not user or user.password_hash != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

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
            "exp": datetime.utcnow() + timedelta(hours=2)
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
def get_profile(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "username": payload.get("sub"),
            "user_id": payload.get("user_id"),
            "company_id": payload.get("company_id"),
            "role": payload.get("role", RoleEnum.worker.value),
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")