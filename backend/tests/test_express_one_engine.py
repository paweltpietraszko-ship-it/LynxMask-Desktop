# LYNX-EXPRESS-ONE-ENGINE: Express to ten sam silnik (/preview z tokenem Express); brak ścieżki maskowania bez NER/Guarda.
# Uruchamiać jawnie: py -3 -m pytest tests/test_express_one_engine.py -q (plik spoza pytest.ini python_files).
import contextlib
import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_LOCAL = "http://127.0.0.1:8765"
_FULL, _EXPR = "a" * 64, "b" * 64
DOC = "Pozew złożył Zenobiusz Audytowy, PESEL: 44051401359, wobec firmy Testowa Budowa Sp. z o.o. w Krakowie."


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    import pseudominizer_api as api
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "audyt")))
    import engine_quality as eq
    ok, why = eq._engine_available()
    if not ok:
        pytest.skip(f"silnik niedostępny: {why}")
    with contextlib.redirect_stdout(io.StringIO()):
        state = eq.build_state(tempfile.mkdtemp(prefix="lynx_express_"))
    old = (api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state)
    api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state = _FULL, _EXPR, state
    yield TestClient(api.app, base_url=_LOCAL, raise_server_exceptions=False)
    api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state = old


def _preview(cl, token):
    r = cl.post("/preview", files={"file": ("d.txt", DOC.encode("utf-8"), "text/plain")}, headers={"X-Api-Token": token})
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    body = data["anonymized_preview"].split("]\n\n", 1)[-1]   # bez nagłówka z kodem sesji (inny w każdym wywołaniu)
    return body, {t["token"]: t["original"] for t in data["tokens"]}, data


def test_stara_sciezka_bez_ner_nie_istnieje(client):
    r = client.post("/preview-express", files={"file": ("d.txt", DOC.encode("utf-8"), "text/plain")},
                    headers={"X-Api-Token": _FULL})
    assert r.status_code == 404, r.status_code
    import pipeline_new
    assert not hasattr(pipeline_new, "run_pipeline_express")


def test_express_daje_ten_sam_wynik_co_pelny(client):
    full = _preview(client, _FULL)
    expr = _preview(client, _EXPR)
    assert expr[0] == full[0] and expr[1] == full[1], (expr[0], full[0])
    body, rev, data = expr
    assert "Audytowy" not in body and "44051401359" not in body, body                 # osoba (NER) i PESEL zakryte
    assert any(t.startswith("OSOBA_") for t in rev), rev
    assert not data["blocked"], data.get("guard_reasons")


@pytest.mark.parametrize("method,path", [
    ("POST", "/archive"), ("POST", "/profile/add-entity"), ("POST", "/profile/guard-allowlist"), ("GET", "/archive"),
])
def test_token_express_tylko_maskowanie(client, method, path):
    assert client.request(method, path, headers={"X-Api-Token": _EXPR}).status_code == 401
