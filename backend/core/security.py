from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.core.config import settings
from backend.database.database import SessionLocal
from backend.database.models import User
from backend.services.account_state_service import is_user_active

security = HTTPBearer(auto_error=False)


@dataclass
class UserContext:
    user_id: Optional[int]
    company_id: Optional[int]
    username: Optional[str]
    role: str


def get_current_user_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserContext:

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == payload.get("user_id")).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        if not is_user_active(db, user):
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )
        user_id = user.id
        company_id = user.company_id
        username = user.username
        role = user.role.value if hasattr(user.role, "value") else str(user.role)
        db.commit()
    finally:
        db.close()

    return UserContext(
        user_id=user_id,
        company_id=company_id,
        username=username,
        role=role,
    )

get_current_user = get_current_user_context
