import hashlib
import os
import sys
import uuid

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.passwords import hash_password
from backend.database.database import SessionLocal
from backend.database.models import Company, RoleEnum, User
from main import app


client = TestClient(app)


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _create_user(username: str, password_hash: str, role: RoleEnum, company_name: str | None = None) -> User:
    db = SessionLocal()
    try:
        company = Company(name=company_name or _unique_name("company"))
        db.add(company)
        db.flush()

        user = User(
            username=username,
            password_hash=password_hash,
            role=role,
            company_id=company.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _login(username: str, password: str):
    return client.post("/api/login", json={"username": username, "password": password})


def test_admin_can_deactivate_and_reactivate_user():
    admin_username = _unique_name("status_admin")
    worker_username = _unique_name("status_worker")
    password = "TestPass123"

    _create_user(admin_username, hash_password(password), RoleEnum.admin)

    login_response = _login(admin_username, password)
    assert login_response.status_code == 200

    admin_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_user_response = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": worker_username,
            "password": password,
            "role": "worker",
        },
    )
    assert create_user_response.status_code == 201
    created_user = create_user_response.json()
    assert created_user["is_active"] is True

    active_worker_login_response = _login(worker_username, password)
    assert active_worker_login_response.status_code == 200
    inactive_check_headers = {
        "Authorization": f"Bearer {active_worker_login_response.json()['access_token']}"
    }

    deactivate_response = client.put(
        f"/api/admin/users/{created_user['id']}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["status"] == "inactive"

    inactive_login_response = _login(worker_username, password)
    assert inactive_login_response.status_code == 403
    assert inactive_login_response.json()["detail"] == "Account is inactive"

    inactive_token_response = client.get("/api/me", headers=inactive_check_headers)
    assert inactive_token_response.status_code == 403
    assert inactive_token_response.json()["detail"] == "Account is inactive"

    reactivate_response = client.put(
        f"/api/admin/users/{created_user['id']}/status",
        headers=headers,
        json={"is_active": True},
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["status"] == "active"

    active_login_response = _login(worker_username, password)
    assert active_login_response.status_code == 200
    worker_headers = {
        "Authorization": f"Bearer {active_login_response.json()['access_token']}"
    }

    profile_response = client.get("/api/me", headers=worker_headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["username"] == worker_username


def test_public_signup_cannot_create_admin_account():
    response = client.post(
        "/api/signup",
        json={
            "username": _unique_name("public_admin"),
            "password": "TestPass123",
            "company_name": _unique_name("public_company"),
            "role": "admin",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Public signup can only create worker accounts"


def test_role_changes_take_effect_for_existing_token():
    admin_username = _unique_name("role_admin")
    password = "TestPass123"

    admin_user = _create_user(admin_username, hash_password(password), RoleEnum.admin)

    login_response = _login(admin_username, password)
    assert login_response.status_code == 200
    admin_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    db = SessionLocal()
    try:
        target = db.query(User).filter(User.id == admin_user.id).first()
        target.role = RoleEnum.worker
        db.commit()
    finally:
        db.close()

    stale_token_response = client.get("/api/admin/users", headers=admin_headers)
    assert stale_token_response.status_code == 403
    assert stale_token_response.json()["detail"] == "Not enough permissions"


def test_legacy_sha256_password_is_upgraded_on_login():
    username = _unique_name("legacy_user")
    password = "LegacyPass123"
    legacy_hash = hashlib.sha256(password.encode()).hexdigest()

    user = _create_user(username, legacy_hash, RoleEnum.worker)

    login_response = _login(username, password)
    assert login_response.status_code == 200

    db = SessionLocal()
    try:
        updated_user = db.query(User).filter(User.id == user.id).first()
        assert updated_user.password_hash != legacy_hash
        assert updated_user.password_hash.startswith("$pbkdf2-sha256$")
    finally:
        db.close()
