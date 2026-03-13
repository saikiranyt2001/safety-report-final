from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from prometheus_fastapi_instrumentator import Instrumentator
from backend.middleware.auth_middleware import AuthMiddleware
from backend.middleware.logging_middleware import LoggingMiddleware
from backend.middleware.tenant_middleware import TenantMiddleware
from backend.api.routes_pipeline import router as pipeline_router

from backend.core.limiter import limiter


print("🚀 Starting AI Safety Platform...")

# Import API routers
try:
    from backend.api.routes_chat import router as chat_router
    from backend.api.routes_reports import router as report_router
    from backend.api.routes_analytics import router as analytics_router
    from backend.api.routes_admin import router as admin_router
    from backend.api.routes_uploads import router as uploads_router
    from backend.api.routes_validation import router as validation_router
    from backend.api.routes_auth import router as auth_router

    print("✅ Routers imported successfully")

except Exception as e:
    print("❌ Router import error:", e)
    raise


# Check environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("⚠️ OPENAI_API_KEY environment variable is missing.")


# Create FastAPI app
app = FastAPI(title="AI Safety Platform")

# Enable Prometheus monitoring
Instrumentator().instrument(app).expose(app)


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(report_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(pipeline_router)

app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantMiddleware)
# Serve frontend if folder exists
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


# Root route
@app.get("/")
def home():
    return {"message": "AI Safety Platform Running"}


# Health check route
@app.get("/health")
def health():
    return {"status": "ok"}

app = FastAPI()
app.state.limiter = limiter    