import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from main import app

print("🚀 Starting AI Safety Platform...")

client = TestClient(app)

# ----------------------------
# Login to obtain JWT token
# ----------------------------

login = client.post(
    "/api/login",
    json={          # OAuth2 form login
        "username": "admin",
        "password": "admin"
    }
)

print("Login status:", login.status_code)

token = None
try:
    token = login.json().get("access_token")
except:
    pass

headers = {"Authorization": f"Bearer {token}"} if token else {}

if token:
    print("✅ Auth token obtained\n")
else:
    print("⚠️ No auth token received — endpoints may return 401\n")


# ----------------------------
# Replace path params
# /api/tasks/{task_id} -> /api/tasks/1
# ----------------------------

def clean_path(path: str):
    return re.sub(r"\{.*?\}", "1", path)


# ----------------------------
# Endpoint Scanner
# ----------------------------

def test_all_endpoints():

    print("🔍 Checking all endpoints...\n")

    total = 0
    success = 0
    errors = 0

    for route in app.routes:

        if not isinstance(route, APIRoute):
            continue

        path = clean_path(route.path)
        methods = route.methods or []

        for method in methods:

            if method in ("HEAD", "OPTIONS"):
                continue

            total += 1

            try:

                if method == "GET":
                    response = client.get(path, headers=headers)

                elif method == "POST":
                    response = client.post(path, json={}, headers=headers)

                elif method == "PUT":
                    response = client.put(path, json={}, headers=headers)

                elif method == "DELETE":
                    response = client.delete(path, headers=headers)

                else:
                    continue

                code = response.status_code

                if code < 500:
                    success += 1
                else:
                    errors += 1

                print(f"{method:6} {path:55} -> {code}")

            except Exception as e:

                errors += 1
                print(f"{method:6} {path:55} -> ERROR: {str(e)}")

    print("\n📊 API HEALTH REPORT")
    print("----------------------------")
    print(f"Total endpoints: {total}")
    print(f"Working responses: {success}")
    print(f"Errors: {errors}")

    coverage = round((success / total) * 100, 2) if total else 0
    print(f"Coverage: {coverage}%")

    print("\n✅ Endpoint scan complete\n")


# ----------------------------
# Run scanner
# ----------------------------

if __name__ == "__main__":
    test_all_endpoints()