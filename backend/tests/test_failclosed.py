# LYNX-FAILCLOSED-S3: awaria/obejście nie zwraca surowych danych jako wyniku maskowania (S3), powody/logi bez wartości (S5).
# Uruchamiać jawnie: py -3 -m pytest tests/test_failclosed.py -q (plik spoza pytest.ini python_files).
import contextlib
import io
import json
import logging
import os
import sys
import tempfile
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_LOCAL = "http://127.0.0.1:8765"
_FULL, _EXPR = "a" * 64, "b" * 64
PESEL = "44051401359"
DOC = f"Pozew złożył Zenobiusz Audytowy, PESEL: {PESEL}, zam. w Krakowie."


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
        state = eq.build_state(tempfile.mkdtemp(prefix="lynx_failclosed_"))
    old = (api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state)
    api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state = _FULL, _EXPR, state
    yield TestClient(api.app, base_url=_LOCAL, raise_server_exceptions=False)
    api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state = old


def _post(cl, path, text, token=_FULL):  # Express = /preview z tokenem Express (LYNX-EXPRESS-ONE-ENGINE)
    return cl.post(path, files={"file": ("d.txt", text.encode("utf-8"), "text/plain")}, headers={"X-Api-Token": token})


def _no_raw(resp, *raw):
    body = resp.text
    for r in raw:
        assert r not in body, (r, body[:300])
    data = resp.json()
    assert not data.get("anonymized_preview") and not data.get("tokens") and not data.get("original_text"), data


# ── A: awaria silnika → 500, blocked, bez treści (F1, F1b, F2) ─────────────────
def _boom(*a, **k):
    raise RuntimeError(f"awaria z danymi {PESEL}")


@pytest.mark.parametrize("token,target", [
    (_EXPR, "pipeline_new.apply_identity_layer"),     # F1: wyjątek warstwy w trybie Express
    (_FULL, "pipeline_new.apply_identity_layer"),     # warstwa Full
    (_FULL, "pipeline._run_pipeline"),                # F1b: wyjątek całego pipeline Full
])
def test_awaria_warstwy_blokuje_bez_tresci(client, token, target):
    with patch(target, _boom):
        r = _post(client, "/preview", DOC, token)
    assert r.status_code == 500 and r.json()["blocked"] is True, r.text[:200]
    _no_raw(r, PESEL, "Zenobiusz", "Audytowy")


@pytest.mark.parametrize("exc", [ValueError("model"), MemoryError()])
def test_awaria_ner_to_nie_zero_encji(client, exc):
    """F2: wyjątek SpaCy (model/pamięć) nie może zamienić się w „brak osób” i wypuścić nazwisko."""
    def broken():
        raise exc
    with patch("spacy_ner._get_nlp", broken):
        r = _post(client, "/preview", DOC)
    assert r.status_code == 500 and r.json()["blocked"] is True, r.text[:200]
    _no_raw(r, PESEL, "Zenobiusz", "Audytowy")


def test_zero_encji_bez_wyjatku_to_normalny_wynik(client):
    r = _post(client, "/preview", "Termin złożenia ofert upływa w poniedziałek o godzinie dziesiątej.")
    data = r.json()
    assert r.status_code == 200 and not data["blocked"] and data["anonymized_preview"], r.text[:200]


# ── B: Guard — podgląd i powody bez wartości (F3), allowlista dokładna (F4) ─────
def test_map_leak_podglad_i_powody_bez_wartosci(caplog):
    from output_guard import guard_output_with_map, GuardMode
    text = f"Pacjent Zenobiusz Audytowy, PESEL {PESEL}."
    with caplog.at_level(logging.DEBUG):
        r = guard_output_with_map(text, None, mode=GuardMode.REDACT, known_plain=["Zenobiusz Audytowy"])
    assert r.blocked
    for raw in (PESEL, "Zenobiusz"):
        assert raw not in r.redacted_text and raw not in r.safe_text, r.redacted_text
        assert raw not in json.dumps(r.reasons, ensure_ascii=False), r.reasons
        assert raw not in caplog.text, caplog.text


def test_map_leak_w_sciezce_pipeline_bez_surowej_wartosci(client):
    """Wspólna ścieżka Guarda, z której API bierze podgląd: wartość z mapy jawna w wyniku → MAP_LEAK, blokada,
    tekst podglądu i powody bez surowej wartości (wcześniej redacted_text=text)."""
    import pipeline
    import pseudominizer_api as api
    out = f"Pozew złożył OSOBA_001. W nagłówku ponownie: Zenobiusz Audytowy, PESEL {PESEL}."
    res = pipeline._apply_guard(out, {"OSOBA_001": "Zenobiusz Audytowy"}, api._app_state)
    assert res.guard_blocked and not res.error, res
    assert "Zenobiusz" not in res.text and PESEL not in res.text and "OSOBA_001" in res.text, res.text
    assert "Zenobiusz" not in json.dumps(res.guard_reasons, ensure_ascii=False), res.guard_reasons
    assert res.guard_values == ["Zenobiusz Audytowy"], res.guard_values   # decyzja Pawła: ostrzeżenie → allowlista w UI


@pytest.mark.parametrize("allow,blocked", [(["Jan"], True), (["mapy", "encja", "text"], True),
                                            (["janina kowalska"], False), ([" Janina Kowalska "], False)])
def test_allowlista_tylko_cala_wartosc(allow, blocked):
    from output_guard import guard_output_with_map, GuardMode
    r = guard_output_with_map("Świadek Janina Kowalska zeznała.", None, mode=GuardMode.REDACT,
                              known_plain=["Janina Kowalska"], allowlist=allow)
    assert r.blocked is blocked, (allow, r.reasons)


def test_guard_error_nigdy_wyciszony():
    from output_guard import guard_output_with_map, GuardMode

    class BrokenMap:
        def get_entity_names(self):
            raise RuntimeError("zepsuta mapa")
    with patch("anonymizer.check_blacklist_context", return_value=[]):
        r = guard_output_with_map("Dowolny tekst bez danych.", BrokenMap(), mode=GuardMode.REDACT,
                                  allowlist=["guard", "error", "fallback", "blokada", "wyjątek"])
    assert r.blocked and r.error and any("GUARD_ERROR" in x for x in r.reasons), r.reasons


@pytest.mark.parametrize("exc", [ValueError(f"guard {PESEL}"), MemoryError()])
def test_awaria_guarda_to_odmowa_s3_nie_ostrzezenie(client, exc):
    """Codex r4 F2: wyjątek wewnątrz Guarda → 500 S3 bez original_text/tokens/podglądu, nie 200 z blokadą S4."""
    with patch("anonymizer.check_blacklist_context", side_effect=exc):
        r = _post(client, "/preview", DOC)
    assert r.status_code == 500 and r.json()["blocked"] is True, r.text[:200]
    _no_raw(r, PESEL, "Zenobiusz", "Audytowy")


# ── C: token powstały w normalizacji OCR (F5) ──────────────────────────────────
@pytest.mark.parametrize("token", [_FULL, _EXPR], ids=["pelny", "express"])
@pytest.mark.parametrize("fake_token", ["OSOBA_0O1", "FIRMA_1l2"])
def test_token_po_ocr_odrzucony(client, token, fake_token):
    r = _post(client, "/preview", f"Pełnomocnik: {fake_token}, pozwany Jan Kowalski.", token)
    assert r.status_code == 422, r.text[:200]
    _no_raw(r, "Kowalski")


@pytest.mark.parametrize("token", [_FULL, _EXPR], ids=["pelny", "express"])
def test_zwykla_korekta_ocr_bez_falszywego_alarmu(client, token):
    r = _post(client, "/preview", "Numer konta: PL61 1090 1014 0000 0712 l981 2874, PESEL: 4405140l359.", token)
    assert r.status_code == 200, r.text[:200]


# ── D: nieobsłużony wyjątek endpointu (np. extractor) na prawdziwym serwerze ASGI (Codex r3) ──
MARKER = f"SYNTETYCZNY_ZNACZNIK_{PESEL}"


@pytest.fixture
def real_server():
    import socket
    import threading
    import uvicorn
    import pseudominizer_api as api
    logs = io.StringIO()
    handler = logging.StreamHandler(logs)
    loggers = [logging.getLogger(n) for n in ("", "uvicorn", "uvicorn.error", "pseudominizer")]
    for lg in loggers:
        lg.addHandler(handler)
    old_level = logging.getLogger().level
    logging.getLogger().setLevel(logging.DEBUG)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.app, lifespan="off", log_config=None, access_log=False))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    with patch.object(api, "_API_TOKEN", _FULL), patch.object(api, "_EXPRESS_TOKEN", _EXPR), \
            patch.object(api, "_extract_text", side_effect=ValueError(MARKER)):
        thread.start()
        for _ in range(200):
            if server.started:
                break
            threading.Event().wait(.05)
        assert server.started
        yield sock.getsockname()[1], logs
    server.should_exit = True
    thread.join(timeout=5)
    sock.close()
    logging.getLogger().setLevel(old_level)
    for lg in loggers:
        lg.removeHandler(handler)


@pytest.mark.parametrize("path,token", [("/preview", _FULL), ("/preview", _EXPR)])
def test_wyjatek_endpointu_json_s3_bez_tresci_w_logu(real_server, path, token):
    import threading
    import requests
    port, logs = real_server
    r = requests.post(f"http://127.0.0.1:{port}{path}", headers={"X-Api-Token": token, "Host": "127.0.0.1:8765"},
                      files={"file": ("d.txt", b"neutralny tekst", "text/plain")}, timeout=10)
    for _ in range(50):
        if "ValueError" in logs.getvalue():
            break
        threading.Event().wait(.02)
    from pipeline import S3_FAILURE
    assert r.status_code == 500 and r.json() == S3_FAILURE, (r.status_code, r.text[:200])
    assert "ValueError" in logs.getvalue(), "granica błędu nie zalogowała typu"
    assert MARKER not in logs.getvalue() and PESEL not in logs.getvalue(), logs.getvalue()[-500:]
