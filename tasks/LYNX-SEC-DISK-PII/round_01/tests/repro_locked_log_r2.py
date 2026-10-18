"""Exact-SHA witness: ordinary Windows open legacy log survives successful reset.
No monkeypatched exception, no real profile, no real data.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

repo = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo / "backend"))
root = Path(tempfile.mkdtemp(prefix="lynx_reset_legacy_lock_"))
os.environ.update(ANONYMIZER_PROFILE_DIR=str(root / "profile"), PROFILE_DIR=str(root / "allow"),
                  ARCHIVE_DIR=str(root / "archive"), HARDWARE_PROFILE=str(root / "hw.json"),
                  PSE_REGISTRY=str(root / "pse.json"))
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import pseudominizer_api as api
    from anonymizer import build_anonymizer
    from fastapi.testclient import TestClient
    api._app_state.anonymizer, _, api._app_state.anon_map, api._app_state.morf_env = build_anonymizer(
        root / "profile", root / "hw.json")
    api._API_TOKEN = "f" * 64
    api._LAUNCHER_LOG = root / "pseudominizer.log"
    api._LAUNCHER_LOG.write_text("SYNTHETIC_LEGACY_LOG_MARKER", encoding="utf-8")
    with api._LAUNCHER_LOG.open("a", encoding="utf-8"):
        response = TestClient(api.app, base_url="http://127.0.0.1:8765", raise_server_exceptions=False).post(
            "/profile/reset", json={"confirm": True}, headers={"X-Api-Token": api._API_TOKEN})
        result = {"http": response.status_code, "ok": response.json().get("ok"),
                  "log_still_exists": api._LAUNCHER_LOG.exists(),
                  "synthetic_marker_retained": api._LAUNCHER_LOG.exists() and
                    "SYNTHETIC_LEGACY_LOG_MARKER" in api._LAUNCHER_LOG.read_text(encoding="utf-8")}
print(json.dumps(result))
