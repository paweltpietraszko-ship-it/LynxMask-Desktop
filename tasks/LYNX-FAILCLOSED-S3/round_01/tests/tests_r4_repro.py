"""Exact-r2 F1 re-check and distinct S3 Guard-failure observation; synthetic data."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SHA = "9bf6131732087a183db45bc0bcb3dc799c365096"
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "audyt")]


def main():
    # Preserve original r3. Adapt only SHA, expected response/log outcome and API log capture.
    p = Path(__file__).with_name("tests_r3_server_repro.py")
    s = p.read_text(encoding="utf-8").replace("8194c0d3b84f47535089ed07c98ed15a61a33a1a", SHA)
    s = s.replace('logger.handlers = [logging.StreamHandler(logs)]',
        'logger.handlers = [logging.StreamHandler(logs)]\n    extra = logging.getLogger("pseudominizer")\n    handler = logging.StreamHandler(logs)\n    extra.addHandler(handler)')
    s = s.replace('response.text == "Internal Server Error"', 'response.json() == api.S3_FAILURE')
    s = s.replace('if MARKER in logs.getvalue():', 'if "ValueError" in logs.getvalue():')
    s = s.replace('assert MARKER in logs.getvalue(), "expected server log disclosure not reproduced"',
                  'assert MARKER not in logs.getvalue()\n                assert "ValueError" in logs.getvalue()')
    s = s.replace('HTTP 500 text/plain; full exception value in actual ASGI server log',
                  'F1 closed: HTTP 500 safe JSON, no exception value in server/API logs')
    s = s.replace('logger.handlers, logger.propagate, logger.level = old',
                  'logger.handlers, logger.propagate, logger.level = old\n        extra.removeHandler(handler)')
    exec(compile(s, str(p), "exec"), {"__file__": str(p), "__name__": "__main__"})
    for file in ("backend/pipeline.py", "backend/output_guard.py"):
        expected = subprocess.check_output(["git", "show", f"{SHA}:{file}"], cwd=ROOT).decode()
        assert (ROOT / file).read_text(encoding="utf-8") == expected
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import pseudominizer_api as api
        import engine_quality
        from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory(prefix="lynx_guard_failure_r4_") as folder:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            state = engine_quality.build_state(folder)
        client = TestClient(api.app, base_url="http://127.0.0.1:8765", raise_server_exceptions=False)
        with patch.object(api, "_API_TOKEN", "a" * 64), patch.object(api, "_app_state", state), \
                patch.object(api, "record_preview"):
            for error in (ValueError("synthetic guard failure"), MemoryError()):
                with patch("anonymizer.check_blacklist_context", side_effect=error) as owner, \
                        contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    response = client.post("/preview", headers={"X-Api-Token": "a" * 64},
                        files={"file": ("synthetic.txt", b"PESEL: 44051401359.", "text/plain")})
                data = response.json()
                assert owner.called and response.status_code == 200 and data["blocked"] is True
                assert any("GUARD_ERROR" in reason for reason in data["guard_reasons"])
                assert data["error"] is None
                assert "44051401359" in data["original_text"]
                assert any(t["original"] == "44051401359" for t in data["tokens"])
                assert "anonymized_preview" in data
                print("F2", type(error).__name__, "Guard failure: HTTP 200, original text and token map returned")


if __name__ == "__main__":
    main()
