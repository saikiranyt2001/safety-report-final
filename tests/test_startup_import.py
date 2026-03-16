import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_imports_without_openai_key():
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, "-c", "import main; print('startup import ok')"],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "startup import ok" in result.stdout


def test_ai_chat_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "response=client.post('/api/ai-chat', json={'prompt':'hi'}); "
                "print(response.status_code); "
                "print(response.json()['response'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout


def test_upload_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from io import BytesIO; "
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "response=client.post('/api/upload', files={'file':('evidence.png', BytesIO(b'fake'), 'image/png')}); "
                "print(response.status_code); "
                "print(response.json()['url'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout
    assert "/storage/reports/" in result.stdout


def test_report_create_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "response=client.post('/api/reports', json={'description':'demo incident','risk_level':'High'}); "
                "print(response.status_code); "
                "print(response.json()['message'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "201" in result.stdout
    assert "Report saved" in result.stdout


def test_report_list_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "client.post('/api/reports', json={'description':'history item','risk_level':'Medium'}); "
                "response=client.get('/api/reports'); "
                "print(response.status_code); "
                "print(len(response.json()))"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout


def test_report_detail_and_download_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "created=client.post('/api/reports', json={'description':'detail item','risk_level':'High'}).json(); "
                "detail=client.get(f\"/api/reports/{created['id']}\"); "
                "download=client.get(f\"/api/reports/{created['id']}/download\"); "
                "print(detail.status_code); "
                "print(detail.json()['id']); "
                "print(download.status_code); "
                "print(download.headers['content-type'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout
    assert "application/pdf" in result.stdout


def test_report_layout_metadata_round_trips_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "created=client.post('/api/reports', json={"
                "'description':'Layout-aware incident',"
                "'location':'print block',"
                "'risk_level':'High',"
                "'layout_style':'executive',"
                "'layout_reference_url':'/storage/reports/template.png',"
                "'layout_reference_name':'template.png',"
                "'layout_primary_color':'#223344',"
                "'layout_accent_color':'#dd8844'"
                "}).json(); "
                "detail=client.get(f\"/api/reports/{created['id']}\").json(); "
                "download=client.get(f\"/api/reports/{created['id']}/download\"); "
                "print(detail['layout_style']); "
                "print(detail['layout_reference_name']); "
                "print(detail['layout_primary_color']); "
                "print(detail['layout_accent_color']); "
                "print(detail['location']); "
                "print(download.status_code)"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "executive" in result.stdout
    assert "template.png" in result.stdout
    assert "#223344" in result.stdout
    assert "#dd8844" in result.stdout
    assert "print block" in result.stdout
    assert "200" in result.stdout


def test_layout_preview_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "response=client.post('/api/reports/layout-preview', json={"
                "'company_name':'Sai Works Safety Division',"
                "'company_address':'Print Block Campus, Hyderabad',"
                "'layout_reference_name':'incident-template.png',"
                "'layout_primary_color':'#224466',"
                "'layout_accent_color':'#ee8844'"
                "}); "
                "data=response.json(); "
                "print(response.status_code); "
                "print(data['company_name']); "
                "print(data['margin_style']); "
                "print(data['header_style'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout
    assert "Sai Works Safety Division" in result.stdout


def test_validate_report_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "response=client.post('/api/validate-report', json={'report_text':'Worker entered electrical room without PPE and no corrective action was documented.'}); "
                "print(response.status_code); "
                "print(response.json()['issues'][0])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout


def test_rag_report_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "response=client.post('/api/rag-report', json={'context':'Hazard: Fire in print block. Immediate action: fire controlled.'}); "
                "print(response.status_code); "
                "print(response.json()['report'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout


def test_analytics_reflect_saved_reports_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "client.post('/api/reports', json={'description':'Fire near electrical panel with missing PPE','risk_level':'High'}); "
                "summary=client.get('/api/analytics/safety-summary').json(); "
                "distribution=client.get('/api/analytics/risk-distribution').json(); "
                "print(summary['hazards_detected']); "
                "print(distribution['high'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip().isdigit()]
    assert len(lines) >= 2
    assert int(lines[0]) >= 1
    assert int(lines[1]) >= 1


def test_dashboard_reflects_saved_reports_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "client.post('/api/reports', json={'description':'Fire near printer area with missing PPE','risk_level':'Critical'}); "
                "response=client.get('/api/dashboard/executive-summary/1'); "
                "data=response.json(); "
                "print(response.status_code); "
                "print(data['hazards']); "
                "print(data['total_reports'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip().isdigit()]
    assert len(lines) >= 3
    assert lines[0] == "200"
    assert int(lines[1]) >= 1
    assert int(lines[2]) >= 1


def test_compliance_analysis_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "response=client.post('/api/compliance/analyze-text', json={'text':'Worker entered electrical panel room without PPE.'}); "
                "print(response.status_code); "
                "print(response.json()['status'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout


def test_incident_prediction_available_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "response=client.post('/api/incident-prediction', json={'environment':'Factory Floor','workers':12,'violations':2,'shift_hours':12,'fatigue_level':'high','ppe_compliance':55,'high_risk_task':'electrical panel maintenance','weather':'hot'}); "
                "print(response.status_code); "
                "print(response.json()['risk_level'])"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout


def test_zone_heatmap_reflects_saved_reports_without_auth():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from main import app; "
                "client=TestClient(app); "
                "client.post('/api/reports', json={'description':'Fire near panel','location':'print block','risk_level':'High'}); "
                "response=client.get('/api/analytics/zone-heatmap'); "
                "data=response.json(); "
                "print(response.status_code); "
                "print(data['updated_from_reports']); "
                "print(len(data['zones']))"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "200" in result.stdout
    assert "True" in result.stdout
