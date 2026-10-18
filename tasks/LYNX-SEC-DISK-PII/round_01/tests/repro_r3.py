"""Independent A1 re-check: real Windows handles; log/allowlist/both, then retry.
Synthetic isolated directories; no patched filesystem exceptions.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))
root = Path(tempfile.mkdtemp(prefix="lynx_reset_r3_"))
os.environ.update(ANONYMIZER_PROFILE_DIR=str(root / "profile"), PROFILE_DIR=str(root / "allow"),
                  ARCHIVE_DIR=str(root / "archive"), HARDWARE_PROFILE=str(root / "hw.json"),
                  PSE_REGISTRY=str(root / "pse.json"))
results = []
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import pseudominizer_api as api
    from anonymizer import build_anonymizer
    from fastapi.testclient import TestClient
    api._API_TOKEN = "f" * 64
    api._LAUNCHER_LOG = root / "pseudominizer.log"
    client = TestClient(api.app, base_url="http://127.0.0.1:8765", raise_server_exceptions=False)
    marker = "SYNTHETIC_RESET_R3"
    for mode in ("log", "allowlist", "both"):
        api._app_state.anonymizer, _, api._app_state.anon_map, api._app_state.morf_env = build_anonymizer(
            root / "profile", root / "hw.json")
        log = api._LAUNCHER_LOG
        allow = api._guard_allowlist_path()
        allow.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(marker, encoding="utf-8")
        allow.write_text(json.dumps([marker]), encoding="utf-8")
        with contextlib.ExitStack() as handles:
            if mode in ("log", "both"):
                handles.enter_context(log.open("a", encoding="utf-8"))
            if mode in ("allowlist", "both"):
                handles.enter_context(allow.open("a", encoding="utf-8"))
            response = client.post("/profile/reset", json={"confirm": True}, headers={"X-Api-Token": api._API_TOKEN})
            assert response.status_code == 500 and not response.json().get("ok")
            assert "Reset częściowy" in response.json()["error"] and marker not in response.text
            if mode in ("log", "both"):
                assert log.exists() and "plik logu silnika" in response.json()["error"]
            if mode in ("allowlist", "both"):
                assert allow.exists() and "to nie PII" in response.json()["error"]
        retry = client.post("/profile/reset", json={"confirm": True}, headers={"X-Api-Token": api._API_TOKEN})
        assert retry.status_code == 200 and retry.json().get("ok") is True
        assert not log.exists() and not allow.exists()
        results.append({"case": mode, "blocked_delete_http": response.status_code,
                        "retry_http": retry.status_code, "files_removed_after_retry": True})
print(json.dumps(results))
