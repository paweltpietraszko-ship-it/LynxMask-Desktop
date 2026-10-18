"""Independent API audit: synthetic data, temporary engine, no lifespan/profile."""
import base64
import contextlib
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SHA = "f1ffa59bc050b0445b91ad996e8cc0cd8185aad4"
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "audyt")]
TOKEN = re.compile(r"[A-Z]+_\d{3}")


def main():
    src = subprocess.check_output(["git", "show", f"{SHA}:backend/pseudominizer_api.py"], cwd=ROOT).decode()
    assert (ROOT / "backend/pseudominizer_api.py").read_text(encoding="utf-8") == src
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import pseudominizer_api as api
        import engine_quality
        import pipeline_new
        from pipeline import PipelineResult
        from fastapi.testclient import TestClient
    full, express = "x" * 64, "y" * 64
    checks = 0
    with tempfile.TemporaryDirectory(prefix="lynx_text_r2_") as folder:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            state = engine_quality.build_state(folder)
        with patch.object(api, "_API_TOKEN", full), patch.object(api, "_EXPRESS_TOKEN", express), \
                patch.object(api, "_app_state", state), patch.object(api, "record_preview"):
            cl = TestClient(api.app, base_url="http://127.0.0.1:8765")  # no lifespan
            def post(path, text, key):
                return cl.post(path, files={"file": ("synthetic.txt", text.encode(), "text/plain")},
                               headers={"X-Api-Token": key})
            for path, key, symbol in [("/preview", full, "pseudonymize_document"),
                                      ("/preview-express", express, "run_pipeline_express")]:
                owner = api if path == "/preview" else pipeline_new
                for n in (15000, 15001, 19000):
                    text = "ą" * n
                    result = PipelineResult(text=text) if path == "/preview" else (text, {}, False)
                    with patch.object(owner, symbol, return_value=result) as engine:
                        r = post(path, " \n" + text + "\n ", key)
                        assert r.status_code == 200 and r.json()["original_text"] == text
                        assert engine.call_args.args[0] == text
                    checks += 1
                boundary = "ą" * 249999 + "xx"
                assert len(boundary.encode()) == 500000
                for extra in ("", "z"):
                    text = boundary + extra
                    result = PipelineResult(text=text) if path == "/preview" else (text, {}, False)
                    with patch.object(owner, symbol, return_value=result) as engine:
                        r = post(path, text, key)
                        if extra:
                            assert r.status_code == 413 and r.json()["blocked"] is True
                            assert set(r.json()) == {"error", "blocked"} and not engine.called
                        else:
                            assert r.status_code == 200 and engine.call_args.args[0] == text
                    checks += 1
                with patch.object(owner, symbol) as engine:
                    assert post(path, "a" * (api.MAX_FILE_BYTES + 1), key).status_code == 400
                    assert not engine.called
                checks += 1
                tail = "\nPESEL: 44051401359; e-mail: osoba.synthetic@example.pl."
                if path == "/preview":
                    tail += "\nCzłonkowie:\nBeata Zielińska\nDariusz Wróblewski\nProtokolant:"
                text = "Treść pisma. " * 1450 + tail
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    r = post(path, text, key)
                b = r.json()
                assert r.status_code == 200 and not b["blocked"] and not b["error"]
                out = b["anonymized_preview"].split("]\n\n", 1)[-1]
                assert b["original_text"] == text
                assert "44051401359" not in out and "osoba.synthetic@example.pl" not in out
                if path == "/preview":
                    assert "Zielińska" not in out and "Wróblewski" not in out
                rev = {t["token"]:t["original"] for t in b["tokens"]}
                assert TOKEN.sub(lambda m: rev.get(m[0], m[0]), out) == text
                checks += 1
            assert post("/preview-express", "Treść", "z" * 64).status_code in (401, 403)
            assert cl.get("/profile/export-dict", headers={"X-Api-Token":express}).status_code in (401, 403)
            blob = base64.b64encode(b"x" * (api.MAX_BLOB_BYTES + 1)).decode()
            r = cl.post("/archive", json={"pse":"PSE-1234-5678", "enc_blob":blob},
                        headers={"X-Api-Token":full})
            assert r.status_code == 400 and "Blob za duży" in r.json()["error"]
            checks += 3
            # Existing separate finding: Express discards the force_block flag.
            with patch.object(pipeline_new, "run_pipeline_express", return_value=("kontrolny wynik", {}, True)):
                b = post("/preview-express", "Treść", express).json()
                assert b["blocked"] is False
    print(f"{checks} independent API checks PASS; existing Express force_block suppression reproduced separately")


if __name__ == "__main__":
    main()
