from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from prometheus_fastapi_instrumentator import Instrumentator

from backend.middleware.auth_middleware import AuthMiddleware
from backend.middleware.logging_middleware import LoggingMiddleware
from backend.middleware.tenant_middleware import TenantMiddleware

from backend.core.limiter import limiter

from backend.api.routes_pipeline import router as pipeline_router
from backend.api.routes_chat import router as chat_router
from backend.api.routes_reports import router as report_router
from backend.api.routes_analytics import router as analytics_router
from backend.api.routes_admin import router as admin_router
from backend.api.routes_uploads import router as uploads_router
from backend.api.routes_validation import router as validation_router
from backend.api.routes_auth import router as auth_router


print("🚀 Starting AI Safety Platform...")

app = FastAPI(title="AI Safety Platform")

# attach limiter
app.state.limiter = limiter

# Prometheus monitoring
Instrumentator().instrument(app).expose(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantMiddleware)

# Routers
app.include_router(report_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")

# Static frontend
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Root
@app.get("/")
def home():
    return {"message": "AI Safety Platform Running"}

# Health
@app.get("/health")
def health():
    return {"status": "ok"}