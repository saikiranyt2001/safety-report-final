from fastapi import Depends, HTTPException, status

from backend.core.security import get_current_user_context, UserContext


ROLE_PERMISSIONS = {

    "admin": {
        "users:create",
        "users:view",
        "users:update",
        "users:delete",
        "report:create",
        "report:view",
        "analytics:view",
    },

    "manager": {
        "report:create",
        "report:view",
        "analytics:view",
    },

    "worker": {
        "report:create",
        "report:view",
    }
}


def require_roles(*allowed_roles: str):

    allowed = {r.lower().strip() for r in allowed_roles}

    def dependency(user: UserContext = Depends(get_current_user_context)):

        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )

        return user

    return dependency


def require_permissions(*permissions: str):

    required = set(permissions)

    def dependency(user: UserContext = Depends(get_current_user_context)):

        user_permissions = ROLE_PERMISSIONS.get(user.role, set())

        missing = required - user_permissions

        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )

        return user

    return dependency