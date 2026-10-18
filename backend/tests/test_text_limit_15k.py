# LYNX-TEXT-LIMIT-15K: /preview (token pełny i Express) przetwarza cały tekst; ponad INPUT_LIMIT_BYTES jawna odmowa 413.
# Uruchamiać jawnie: py -3 -m pytest tests/test_text_limit_15k.py -q (plik spoza pytest.ini python_files).
import contextlib
import io
import os
import re
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_LOCAL = "http://127.0.0.1:8765"
_FULL, _EXPR = "a" * 64, "b" * 64
TOKEN = re.compile(r"(?:FIRMA|OSOBA|ADRES|INSTYTUCJA|NUMER|EMAIL|KWOTA)_\d{3}")
FILLER = "Zamawiający prowadzi postępowanie o udzielenie zamówienia w trybie podstawowym bez negocjacji. "
TAIL = "\nDane kontaktowe: PESEL: 44051401359, e-mail jan.testowy@example.pl, koniec dokumentu."


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
        state = eq.build_state(tempfile.mkdtemp(prefix="lynx_limit_"))
    old = (api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state)
    api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state = _FULL, _EXPR, state
    yield TestClient(api.app, base_url=_LOCAL), api  # bez lifespanu: nie dotyka api_token.txt ani profilu
    api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state = old


def _post(cl, path, text, token):
    return cl.post(path, files={"file": ("dok.txt", text.encode("utf-8"), "text/plain")}, headers={"X-Api-Token": token})


def _body(r):
    data = r.json()
    out = (data.get("anonymized_preview") or "").split("]\n\n", 1)[-1]   # bez nagłówka PSE
    return data, out, {t["token"]: t["original"] for t in data.get("tokens", [])}


@pytest.mark.parametrize("path,token", [("/preview", _FULL), ("/preview", _EXPR)])
def test_pii_w_koncowce_dlugiego_dokumentu_maskowane(client, path, token):
    """RED na bazie: tekst ucięty do 15 000 znaków — końcówka nie wraca, original_text niepełny."""
    cl, _ = client
    text = FILLER * (17_000 // len(FILLER) + 1) + TAIL
    assert 15_000 < len(text) < 20_000
    r = _post(cl, path, text, token)
    assert r.status_code == 200, r.text[:200]
    data, out, rev = _body(r)
    assert data["original_text"] == text.strip()
    assert not data.get("blocked"), data.get("guard_reasons")
    assert "44051401359" not in out and "jan.testowy@example.pl" not in out, out[-200:]
    assert TOKEN.sub(lambda m: rev.get(m.group(0), m.group(0)), out) == text.strip()   # Przywróć 1:1 (symulacja)


def test_granica_bajtow_utf8_nie_znaki():
    """B = INPUT_LIMIT_BYTES przechodzi do pipeline, B+1 → 413; polskie litery mają 2 bajty (nie 1 znak = 1 bajt)."""
    import pseudominizer_api as api
    unit = "żółć "                                             # 5 znaków, 9 bajtów
    n = len(unit.encode("utf-8"))
    text = unit * (api.INPUT_LIMIT_BYTES // n) + "a" * (api.INPUT_LIMIT_BYTES % n)
    assert len(text.encode("utf-8")) == api.INPUT_LIMIT_BYTES and len(text) < api.INPUT_LIMIT_BYTES
    assert api._text_rejection(text, "[T]", "PSE-T") is None
    r = api._text_rejection(text + "a", "[T]", "PSE-T")
    assert r is not None and r.status_code == 413


@pytest.mark.parametrize("path,token", [("/preview", _FULL), ("/preview", _EXPR)])
def test_ponad_limitem_413_bez_wyniku(client, path, token):
    cl, api = client
    text = "a" * api.INPUT_LIMIT_BYTES + " PESEL 44051401359"
    r = _post(cl, path, text, token)
    data = r.json()
    assert r.status_code == 413 and data["blocked"] is True and "za długi" in data["error"], data
    assert not ({"anonymized_preview", "tokens", "original_text"} & set(data)), data
    assert "44051401359" not in r.text


@pytest.mark.parametrize("path,token", [("/preview", _FULL), ("/preview", _EXPR)])
def test_regresje_wejscia(client, path, token):
    cl, _ = client
    assert _post(cl, path, "   \n  ", token).status_code == 400                                    # pusty
    assert _post(cl, path, "Treść z OSOBA_001 w środku.", token).status_code == 422                 # token injection
    r = _post(cl, path, "Krótki tekst: PESEL 44051401359, łódź.", token)
    data, out, _ = _body(r)
    assert r.status_code == 200 and "44051401359" not in out and data["original_text"].endswith("łódź."), data
