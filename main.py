from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from prometheus_fastapi_instrumentator import Instrumentator
from backend.core.config import settings

load_dotenv()

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
from backend.api.routes_health import router as health_router
from backend.api.routes_activity import router as activity_router
from backend.api.routes_inspection import router as inspection_router
from backend.api.routes_tasks import router as tasks_router
from backend.api.routes_incidents import router as incidents_router
from backend.api.routes_training import router as training_router
from backend.api.routes_equipment import router as equipment_router
from backend.api.routes_compliance import router as compliance_router
from backend.api.routes_integrations import router as integrations_router
from backend.api.routes_projects import router as projects_router
from backend.api.routes_tools import router as tools_router
from backend.api.routes_settings import router as settings_router
from backend.database.database import Base, engine
import backend.database.models 

print("🚀 Starting AI Safety Platform...")

app = FastAPI(title="AI Safety Platform")

# attach limiter
app.state.limiter = limiter

# Prometheus monitoring
Instrumentator().instrument(app).expose(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantMiddleware)

# Routers
app.include_router(report_router, prefix="/api",tags=["reports"])
app.include_router(analytics_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")
app.include_router(activity_router, prefix="/api")
app.include_router(inspection_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(equipment_router, prefix="/api")
app.include_router(compliance_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(health_router,prefix="/api")

Base.metadata.create_all(bind=engine)
# Static frontend
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
if os.path.exists("storage"):
    app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# Root
@app.get("/")
def home():
    return {"message": "AI Safety Platform Running"}
