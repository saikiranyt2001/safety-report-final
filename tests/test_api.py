from fastapi.testclient import TestClient
from backend.main import app
from backend.database.database import Base, engine, SessionLocal
from backend.database.models import Project

# Reset database for testing
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_health():
    response = client.get("/")
    assert response.status_code == 200

def test_generate_report():
    db = SessionLocal()

    # create test project
    project = Project(
        name="Test Project",
        description="Testing",
        company_id=1
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    payload = {
        "industry": "construction",
        "hazard": "workers without helmets",
        "location": "Test Site",
        "crew": "Team A",
        "project_id": project.id,
        "severity": 3,
        "likelihood": 2,
        "user": "test@example.com"
    }

    response = client.post(
        "/api/generate-report",
        json=payload
    )

    assert response.status_code == 200

    data = response.json()

    assert "report" in data
    assert "report_id" in data

    db.close()
