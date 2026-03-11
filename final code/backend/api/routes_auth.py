from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.database.models import User
from backend.database.database import SessionLocal
from datetime import datetime, timedelta
import jwt
import hashlib
from pydantic import BaseModel

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class LoginData(BaseModel):
    username: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# Signup
@router.post("/signup")
def signup(data: LoginData, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password)
    )

    db.add(user)
    db.commit()

    return {"message": "User created"}

# Login
@router.post("/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    if not user or user.password_hash != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {
            "sub": user.username,
            "exp": datetime.utcnow() + timedelta(hours=2)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {"access_token": token, "token_type": "bearer"}

# Get profile
@router.get("/me")
def get_profile(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload["sub"]}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
