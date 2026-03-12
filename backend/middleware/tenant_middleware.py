
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from jose import jwt, JWTError
from backend.core.settings import settings


class TenantMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        request.state.company_id = None
        request.state.user_id = None

        auth_header = request.headers.get("Authorization")

        if auth_header:

            try:
                token = auth_header.split(" ")[1]

                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=["HS256"]
                )

                request.state.user_id = payload.get("user_id")
                request.state.company_id = payload.get("company_id")

            except JWTError:
                pass

        response = await call_next(request)

        return response
