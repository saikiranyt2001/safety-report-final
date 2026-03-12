# Authentication Middleware

# Add FastAPI middleware for authentication, e.g., JWT validation, session checks, etc.
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from jose import jwt, JWTError
from backend.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        # Public routes that don't require auth
        public_paths = [
            "/login",
            "/signup",
            "/docs",
            "/openapi.json"
        ]

        if request.url.path in public_paths:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        try:
            token = auth_header.split(" ")[1]
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        response = await call_next(request)
        return response