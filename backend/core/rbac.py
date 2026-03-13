from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.config import settings
from backend.database.models import RoleEnum

security = HTTPBearer(auto_error=False)


@dataclass
class UserContext:
    user_id: int | None
    company_id: int | None
    username: str | None
    role: str


def _normalize_role(role: str | RoleEnum | None) -> str:
    if isinstance(role, RoleEnum):
        return role.value
    if isinstance(role, str):
        return role.lower().strip()
    return RoleEnum.worker.value


def get_current_user_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserContext:
    # Prefer payload decoded by middleware to avoid duplicate JWT parsing.
    state_role = getattr(request.state, "role", None)
    state_user_id = getattr(request.state, "user_id", None)
    state_company_id = getattr(request.state, "company_id", None)
    state_username = getattr(request.state, "username", None)

    if state_role:
        return UserContext(
            user_id=state_user_id,
            company_id=state_company_id,
            username=state_username,
            role=_normalize_role(state_role),
        )

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
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    role = _normalize_role(payload.get("role"))
    return UserContext(
        user_id=payload.get("user_id"),
        company_id=payload.get("company_id"),
        username=payload.get("sub"),
        role=role,
    )


def require_roles(*allowed_roles: str):
    allowed = {role.lower().strip() for role in allowed_roles}

    def _dependency(user: UserContext = Depends(get_current_user_context)) -> UserContext:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return user

    return _dependency
