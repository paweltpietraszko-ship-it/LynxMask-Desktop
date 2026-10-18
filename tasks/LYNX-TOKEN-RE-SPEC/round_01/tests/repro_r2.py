"""Independent S2/S3, batch, and no-seed startup witness; synthetic isolated data."""
import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

repo = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo / "backend"))
root = Path(tempfile.mkdtemp(prefix="lynx_token_spec_audit_"))
os.environ.update(ANONYMIZER_PROFILE_DIR=str(root / "profile"), PROFILE_DIR=str(root / "allow"),
                  ARCHIVE_DIR=str(root / "archive"), HARDWARE_PROFILE=str(root / "hw.json"),
                  PSE_REGISTRY=str(root / "pse.json"))
result = {}
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import anonymizer_init as init
    import pseudominizer_api as api
    import pipeline
    import ner_layer
    import output_guard
    import verbal_amounts
    import seed_profile
    from layers import ner_adapter
    from fastapi.testclient import TestClient
    patterns = [init.TOKEN_RE, init.TOKEN_SPAN_RE, api._TOKEN_RE, pipeline._TOKEN_RE,
                ner_layer._TOKEN_RE, ner_adapter._TOKEN_RE, output_guard._TOKEN_RE, verbal_amounts._TOKEN_RE]
    categories = ["FIRMA", "OSOBA", "NUMER", "KWOTA", "ADRES", "INSTYTUCJA", "EMAIL"]
    checked = 0
    for category in categories:
        for suffix in ("", "x", "Teresa", "."):
            text = category + "_001" + suffix
            for pattern in patterns:
                assert [m.group(0) for m in pattern.finditer(text)] == [category + "_001"]
                checked += 1
        for text in (category + "_0012", "x" + category + "_001", category + "_01"):
            assert all(not pattern.search(text) for pattern in patterns)
            checked += len(patterns)
    assert init.TOKEN_RE.groups == 2 and init.TOKEN_SPAN_RE.groups == 0
    result["regex_checks"] = checked
    api._API_TOKEN_PATH = root / "token.txt"
    api._STARTUP_ERROR_PATH = root / "error.json"

    async def check_runtime():
        cm = api._lifespan(api.app)
        with patch.object(seed_profile, "seed_if_needed", side_effect=AssertionError("unexpected seed")) as seed:
            await cm.__aenter__()
            try:
                assert seed.call_count == 0
                result["real_start_seed_calls"] = seed.call_count
                client = TestClient(api.app, base_url="http://127.0.0.1:8765", raise_server_exceptions=False)
                rejected = 0
                for token in (api._API_TOKEN, api._EXPRESS_TOKEN):
                    for category in categories:
                        response = client.post("/preview", files={"file": ("audit.txt", (category + "_001x").encode(), "text/plain")},
                            headers={"X-Api-Token": token})
                        assert response.status_code == 422
                        rejected += 1
                    ordinary = client.post("/preview", files={"file": ("audit.txt", b"Termin skladania ofert uplywa jutro.", "text/plain")},
                        headers={"X-Api-Token": token})
                    assert ordinary.status_code == 200
                result["http_rejections"] = rejected
                response = client.post("/profile/add-entity", json={"text": "Jan Kowalski OSOBA_001x", "token_type": "OSOBA"},
                    headers={"X-Api-Token": api._API_TOKEN})
                assert response.status_code == 200
                assert "Jan Kowalski" in api._app_state.anon_map.get_entity_names()
                assert not any("OSOBA_001" in name for name in api._app_state.anon_map.get_entity_names())
                result["inline_trim"] = True
                try:
                    api._app_state.anon_map.add_entities_batch([("Syntetyk", "OSOBA")] * (init.MAX_ONBOARD_BATCH + 1))
                except ValueError:
                    result["batch_limit_preserved"] = True
                else:
                    raise AssertionError("batch limit missing")
                added = api._app_state.anon_map.add_entities_batch([("Anna Nowak", "OSOBA"), ("Piotr Zielinski", "OSOBA")])
                assert len(added) == 2
                result["batch_two_entities"] = True
            finally:
                await cm.__aexit__(None, None, None)
    asyncio.run(check_runtime())
print(json.dumps(result))
