import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from main import app

print("🚀 Starting AI Safety Platform...\n")

client = TestClient(app)

# LOGIN AND GET TOKEN
login = client.post(
    "/api/login",
    json={
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

if not token:
    print("❌ Login failed. Cannot test protected endpoints.")
    print(login.json())
    exit()

print("✅ Auth token obtained\n")

headers = {"Authorization": f"Bearer {token}"}

# Replace {id} params
def clean_path(path):
    return re.sub(r"\{.*?\}", "1", path)

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

                if code < 500 or code == 422:
                    success += 1
                else:
                    errors += 1

                print(f"{method:6} {path:55} -> {code}")

            except Exception as e:

                errors += 1
                print(f"{method:6} {path:55} -> ERROR: {str(e)}")

    print("\n📊 API HEALTH REPORT")
    print("----------------------------")
    print("Total endpoints:", total)
    print("Working responses:", success)
    print("Errors:", errors)

    coverage = round((success / total) * 100, 2) if total else 0
    print("Coverage:", coverage, "%")

    print("\n✅ Endpoint scan complete\n")


if __name__ == "__main__":
    test_all_endpoints()