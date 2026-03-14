from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException


class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        path = request.url.path

        # Allow OPTIONS (CORS)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Allow frontend static files
        if path.startswith("/frontend"):
            return await call_next(request)

        # Allow favicon
        if path == "/favicon.ico":
            return await call_next(request)

        # Allow API docs
        if path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        # ✅ Allow login & signup
        if path.startswith("/api/login") or path.startswith("/api/signup"):
            return await call_next(request)

        # Allow health checks
        if path.startswith("/api/health"):
            return await call_next(request)

        # Allow image analyze (optional public)
        if path.startswith("/api/analyze-image"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        return await call_next(request)