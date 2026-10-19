# LYNX-ADDR-EMAIL-LEAKS: adresy z numerem OCR / skrótem / nazwą liczbową i e-maile z polską literą lub NFD nie zostają jawne.
# Uruchamiać jawnie: py -3 -m pytest tests/test_addr_email_leaks.py -q (plik spoza pytest.ini python_files).
import contextlib
import io
import os
import re
import sys
import tempfile
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

TOKEN = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)")
GLUED = re.compile(r"\w(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}|_\d{3}[^\W\d_]")
_FULL = "a" * 64

# (tekst, wartość, która musi trafić do JEDNEGO tokenu w całości)
LEAKS = [
    ("Adres: ul. Polna l2/8", "ul. Polna l2/8"),                      # L1
    ("Adres: ul. Św. Marcin 5", "ul. Św. Marcin 5"),                  # L2
    ("Adres: ul. 3 Maja 12/4; tel.", "ul. 3 Maja 12/4"),              # L3
    ("Kontakt: żaneta@firma.pl", "żaneta@firma.pl"),                  # L4
    ("Kontakt: aléx@firma.pl", "aléx@firma.pl"),          # L5 NFD
    ("Siedziba: ul. Gen. Andersa 4a/12.", "ul. Gen. Andersa 4a/12"),  # rodzina
    ("Lokal: al. 11 Listopada 7", "al. 11 Listopada 7"),
    ("Adres: ul. Polna O5", "ul. Polna O5"),
    ("Adres: ul. Polna 12/l4", "ul. Polna 12/l4"),
    ("Pisz: łukasz.żak@firma.pl", "łukasz.żak@firma.pl"),
    ("Pisz: Ąnna@firma.pl dziś", "Ąnna@firma.pl"),
]
# bez PII — nie mogą się zmienić (C5 „Dz. U.” znane, nie pogarszać: tylko „Nr 223” po normalizacji, jak na main)
CLEAN = ["Skrót ul. w instrukcji nie oznacza tu adresu.", "Profil: @administrator", "Profil: @jan_kowalski",
         "Mieszkam na pl. zabaw obok.", "Al. 5 razy pytał."]


def _run(text):
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        return run_pipeline_new(text, anon_map={})


def _restore(out, rev):
    return TOKEN.sub(lambda m: rev.get(m.group(0), m.group(0)), out)


@pytest.mark.parametrize("text,value", LEAKS, ids=[t for t, _ in LEAKS])
def test_wartosc_w_calosci_w_jednym_tokenie(text, value):
    out, rev, blocked = _run(text)
    assert not blocked and value in rev.values(), (out, rev)
    assert not GLUED.search(out), out
    assert _restore(out, rev) == text, (out, rev)


@pytest.mark.parametrize("text", CLEAN)
def test_bez_pii_bez_zmian(text):
    out, rev, _ = _run(text)
    assert out == text and rev == {}, (out, rev)


def test_dz_u_bez_pogorszenia():
    out, rev, _ = _run("Źródło: Dz. U. Nr 223")
    assert len(rev) <= 1 and "Źródło: Dz." in out                  # C5 (K3) bez zmian względem main, poza zakresem


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    import pseudominizer_api as api
    from anonymizer import build_anonymizer
    import spacy_ner
    d = tempfile.mkdtemp(prefix="lynx_addr_email_")
    st = api.AppState()
    st.spacy_ner_mod = spacy_ner
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(os.path.join(d, "p"), os.path.join(d, "hw.json"))
    old = (api._API_TOKEN, api._app_state)
    api._API_TOKEN, api._app_state = _FULL, st
    yield TestClient(api.app, base_url="http://127.0.0.1:8765", raise_server_exceptions=False)
    api._API_TOKEN, api._app_state = old


@pytest.mark.parametrize("text,value", LEAKS[:5], ids=["L1", "L2", "L3", "L4", "L5"])
def test_preview_pelny_silnik(client, text, value):
    r = client.post("/preview", files={"file": ("d.txt", text.encode("utf-8"), "text/plain")}, headers={"X-Api-Token": _FULL})
    assert r.status_code == 200, r.text[:200]
    out = r.json()["anonymized_preview"].split("]\n\n", 1)[-1]
    for part in re.findall(r"[^\W\d_]{2,}", value):                   # żaden człon wartości nie zostaje jawny
        if part.lower() not in ("ul", "al", "gen"):
            assert part not in out, (part, out)
    assert not GLUED.search(out), out
