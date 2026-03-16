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

        # Allow mounted storage assets used by the frontend
        if path.startswith("/storage"):
            return await call_next(request)

        # Allow basic public app entrypoints
        if path == "/" or path == "/metrics":
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

        # Allow lightweight assistant chat without auth
        if path.startswith("/api/ai-chat"):
            return await call_next(request)

        # Allow health checks
        if path.startswith("/api/health"):
            return await call_next(request)

        # Allow image analyze (optional public)
        if path.startswith("/api/analyze-image"):
            return await call_next(request)

        # Allow direct evidence uploads used by the report flow
        if path.startswith("/api/upload"):
            return await call_next(request)

        # Allow frontend incident form submissions without auth
        if path == "/api/reports" and request.method == "POST":
            return await call_next(request)

        if path == "/api/reports/layout-preview" and request.method == "POST":
            return await call_next(request)

        # Allow report history lookup for the local/demo frontend flow
        if path == "/api/reports" and request.method == "GET":
            return await call_next(request)

        if path.startswith("/api/reports/") and request.method == "GET":
            return await call_next(request)

        if path == "/api/validate-report" and request.method == "POST":
            return await call_next(request)

        if path == "/api/rag-report" and request.method == "POST":
            return await call_next(request)

        if path.startswith("/api/analytics/") and request.method == "GET":
            return await call_next(request)

        if path.startswith("/api/dashboard/executive-summary/") and request.method == "GET":
            return await call_next(request)

        if path == "/api/compliance/analyze-text" and request.method == "POST":
            return await call_next(request)

        if path == "/api/incident-prediction" and request.method == "POST":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        return await call_next(request)
