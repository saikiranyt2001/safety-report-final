import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.passwords import hash_password
from backend.database.database import SessionLocal
from backend.database.models import Company, RoleEnum, User


pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_server(base_url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(base_url + "/", timeout=1)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise RuntimeError("Timed out waiting for local server to start")


@pytest.fixture(scope="module")
def live_server():
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _create_admin_user(username: str, password: str) -> None:
    db = SessionLocal()
    try:
        company = Company(name=_unique_name("e2e_company"))
        db.add(company)
        db.flush()
        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role=RoleEnum.admin,
                company_id=company.id,
            )
        )
        db.commit()
    finally:
        db.close()


def test_frontend_login_and_user_management_flow(live_server):
    admin_username = _unique_name("e2e_admin")
    new_username = _unique_name("e2e_worker")
    password = "BrowserPass123"
    _create_admin_user(admin_username, password)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(live_server + "/frontend/pages/login.html", wait_until="networkidle")
            page.fill("#username", admin_username)
            page.fill("#password", password)
            page.get_by_role("button", name="Login").click()
            page.wait_for_url("**/frontend/pages/dashboard.html")

            page.goto(live_server + "/frontend/pages/users.html", wait_until="networkidle")
            page.wait_for_selector("#usersTable tbody tr")
            page.locator("#usersTable tbody").wait_for()
            page.locator(f"tr:has(td:text-is('{admin_username}'))").first.wait_for()

            page.evaluate(
                """(values) => {
                    window.__promptValues = [...values];
                    window.prompt = () => window.__promptValues.shift() || "";
                    window.confirm = () => true;
                }""",
                [new_username, password, "worker"],
            )
            page.get_by_role("button", name="Add User").click()
            page.get_by_text("User created.").wait_for()

            new_row = page.locator(f"tr:has-text('{new_username}')")
            new_row.wait_for()
            new_row.get_by_role("button", name="Deactivate").click()
            page.get_by_text("User deactivated.").wait_for()
            expect_text = new_row.locator(".status-pill")
            expect_text.wait_for()
            assert "Inactive" in expect_text.text_content()
        finally:
            browser.close()
