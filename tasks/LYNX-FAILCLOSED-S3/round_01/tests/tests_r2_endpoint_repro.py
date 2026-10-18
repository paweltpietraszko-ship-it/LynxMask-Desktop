"""Observation before OWNER gate: endpoint-level exception response, synthetic data."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SHA = "8194c0d3b84f47535089ed07c98ed15a61a33a1a"
sys.path.insert(0, str(ROOT / "backend"))


def main():
    expected = subprocess.check_output(["git", "show", f"{SHA}:backend/pseudominizer_api.py"], cwd=ROOT).decode()
    assert (ROOT / "backend/pseudominizer_api.py").read_text(encoding="utf-8") == expected
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import pseudominizer_api as api
        from fastapi.testclient import TestClient
    client = TestClient(api.app, base_url="http://127.0.0.1:8765", raise_server_exceptions=False)
    with patch.object(api, "_API_TOKEN", "a" * 64), patch.object(api, "_EXPRESS_TOKEN", "b" * 64), \
            patch.object(api, "_extract_text", side_effect=ValueError("synthetic endpoint failure")):
        for path, token in (("/preview", "a" * 64), ("/preview-express", "b" * 64)):
            response = client.post(path, files={"file": ("synthetic.txt", b"neutral text", "text/plain")},
                                   headers={"X-Api-Token": token})
            assert response.status_code == 500
            assert response.text == "Internal Server Error"
            assert response.headers["content-type"].startswith("text/plain")
            print(path, "HTTP 500 text/plain; no JSON blocked/error; no source text returned")


if __name__ == "__main__":
    main()
