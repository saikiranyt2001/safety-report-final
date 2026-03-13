# Authentication Middleware

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from jose import jwt, JWTError
from backend.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM



class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        path = request.url.path

        public_routes = [
            "/api/ai-chat",
            "/api/analyze-image",
            "/api/login",
            "/api/signup",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics"
        ]

        # Allow public routes
        if any(path.startswith(route) for route in public_routes):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        try:
            token = auth_header.split(" ")[1]

            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            request.state.user_id = payload.get("user_id")
            request.state.company_id = payload.get("company_id")
            request.state.username = payload.get("sub")
            request.state.role = payload.get("role")

        except (JWTError, IndexError):
            raise HTTPException(status_code=401, detail="Invalid token")

        return await call_next(request)