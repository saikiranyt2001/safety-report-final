from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv()
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
from backend.api.routes_health import router as health_router
from backend.api.routes_activity import router as activity_router
from backend.api.routes_inspection import router as inspection_router
from backend.api.routes_tasks import router as tasks_router
from backend.api.routes_incidents import router as incidents_router
from backend.api.routes_training import router as training_router
from backend.api.routes_equipment import router as equipment_router
from backend.api.routes_compliance import router as compliance_router
from backend.api.routes_integrations import router as integrations_router
from backend.api.routes.ai_routes import router as ai_router
from fastapi.middleware.cors import CORSMiddleware


print("🚀 Starting AI Safety Platform...")

app = FastAPI(title="AI Safety Platform")

# attach limiter
app.state.limiter = limiter

# Prometheus monitoring
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
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
app.include_router(activity_router, prefix="/api")
app.include_router(inspection_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(equipment_router, prefix="/api")
app.include_router(compliance_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(health_router)
app.include_router(ai_router, prefix="/api")

# Static frontend
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Root
@app.get("/")
def home():
    return {"message": "AI Safety Platform Running"}
