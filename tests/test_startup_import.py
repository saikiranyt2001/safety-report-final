import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_imports_without_openai_key():
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)

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
