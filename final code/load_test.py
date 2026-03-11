try:
    from locust import HttpUser, task, between
except ImportError:
    HttpUser = object
    def task(fn): return fn
    def between(a, b): return None


class SafetyPlatformUser(HttpUser):
    host = "http://127.0.0.1:8000"   # IMPORTANT LINE
    wait_time = between(1, 3)

    @task
    def health_check(self):
        response = self.client.get("/")
        if response.status_code != 200:
            response.failure("Health check failed")

    @task
    def generate_report(self):
        payload = {
            "industry": "Construction",
            "hazard": "Fall from height",
            "location": "Site A",
            "crew": "Team Alpha",
            "project_id": 1,
            "severity": 3,
            "likelihood": 2,
            "user": "loadtest@example.com"
        }
        response = self.client.post(
            "/api/generate-report",
            json=payload
        )
        if response.status_code != 200:
            response.failure("Report generation failed")
