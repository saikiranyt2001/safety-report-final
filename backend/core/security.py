from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.core.config import settings

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

    return UserContext(
        user_id=payload.get("user_id"),
        company_id=payload.get("company_id"),
        username=payload.get("sub"),
        role=payload.get("role", "worker"),
    )

get_current_user = get_current_user_context