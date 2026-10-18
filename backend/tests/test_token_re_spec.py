# LYNX-TOKEN-RE-SPEC: rozpoznawanie tokenu zgodne z zamrożonym S2 ((?!\d) na końcu, pełna taksonomia) we wszystkich kopiach;
# kontrola wejścia 422 (S3) także dla przyklejonego tokenu; batch profilu działa.
# Uruchamiać jawnie: py -3 -m pytest tests/test_token_re_spec.py -q (plik spoza pytest.ini python_files).
import contextlib
import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_LOCAL = "http://127.0.0.1:8765"
_FULL, _EXPR = "a" * 64, "b" * 64

# tekst → oczekiwane dopasowane fragmenty (porównujemy teksty/spany, nie kształt findall)
CASES = [
    ("Zobacz OSOBA_001 tutaj", ["OSOBA_001"]),
    ("Zobacz OSOBA_001x tutaj", ["OSOBA_001"]),               # przyklejona litera — S2
    ("NUMER_004Teresa", ["NUMER_004"]),
    ("INSTYTUCJA_002, EMAIL_003.", ["INSTYTUCJA_002", "EMAIL_003"]),
    ("KWOTA_005_ADRES_006", ["KWOTA_005"]),                   # podkreślnik po NNN nie blokuje (jak litera)
    ("OSOBA_0012", []),                                        # czwarta cyfra — nie token
    ("xOSOBA_001", []),                                        # początek \b bez zmian (jak Mobile)
    ("FIRMA_01 i FIRMA_1", []),
]


def _copies():
    import anonymizer_init
    import ner_layer
    import output_guard
    import pipeline
    import pseudominizer_api
    import verbal_amounts
    from layers import ner_adapter
    return {
        "anonymizer_init.TOKEN_RE": anonymizer_init.TOKEN_RE,
        "anonymizer_init.TOKEN_SPAN_RE": anonymizer_init.TOKEN_SPAN_RE,
        "pseudominizer_api._TOKEN_RE": pseudominizer_api._TOKEN_RE,
        "pipeline._TOKEN_RE": pipeline._TOKEN_RE,
        "ner_layer._TOKEN_RE": ner_layer._TOKEN_RE,
        "layers.ner_adapter._TOKEN_RE": ner_adapter._TOKEN_RE,
        "output_guard._TOKEN_RE": output_guard._TOKEN_RE,
        "verbal_amounts._TOKEN_RE": verbal_amounts._TOKEN_RE,
    }


@pytest.mark.parametrize("text,expected", CASES)
def test_wszystkie_kopie_wzorca_zgodne_z_s2(text, expected):
    got = {name: [m.group(0) for m in rx.finditer(text)] for name, rx in _copies().items()}
    assert all(v == expected for v in got.values()), got


def test_grupy_bez_zmian():
    import anonymizer_init
    assert anonymizer_init.TOKEN_RE.findall("OSOBA_001x") == [("OSOBA", "001")]     # findall/sub w anonymizer.py
    assert anonymizer_init.TOKEN_SPAN_RE.findall("OSOBA_001x") == ["OSOBA_001"]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    import pseudominizer_api as api
    from anonymizer import build_anonymizer
    import spacy_ner
    d = tempfile.mkdtemp(prefix="lynx_token_re_")
    st = api.AppState()
    st.spacy_ner_mod = spacy_ner
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(os.path.join(d, "p"), os.path.join(d, "hw.json"))
    old = (api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state)
    api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state = _FULL, _EXPR, st
    yield TestClient(api.app, base_url=_LOCAL, raise_server_exceptions=False)
    api._API_TOKEN, api._EXPRESS_TOKEN, api._app_state = old


@pytest.mark.parametrize("token", [_FULL, _EXPR], ids=["pelny", "express"])
@pytest.mark.parametrize("fake", ["OSOBA_001x", "NUMER_004Teresa", "INSTYTUCJA_002"])
def test_przyklejony_token_w_wejsciu_to_422(client, token, fake):
    r = client.post("/preview", files={"file": ("d.txt", f"Pełnomocnik {fake} w sprawie.".encode(), "text/plain")},
                    headers={"X-Api-Token": token})
    assert r.status_code == 422, (r.status_code, r.text[:120])


def test_tekst_bez_tokenu_nadal_200(client):
    r = client.post("/preview", files={"file": ("d.txt", "Numer sprawy OSOBA0012 bez podkreślnika.".encode(), "text/plain")},
                    headers={"X-Api-Token": _FULL})
    assert r.status_code == 200, r.text[:120]


def test_add_entities_batch_dziala_na_izolowanym_profilu():
    from anonymizer import build_anonymizer
    d = tempfile.mkdtemp(prefix="lynx_batch_")
    with contextlib.redirect_stdout(io.StringIO()):
        _, _, amap, _ = build_anonymizer(os.path.join(d, "p"), os.path.join(d, "hw.json"))
    res = amap.add_entities_batch([("Anna Nowak", "OSOBA"), ("Testowa Budowa Sp. z o.o.", "FIRMA")])
    assert len(res) == 2, res


def test_start_nie_wola_seedu():
    import inspect
    import pseudominizer_api as api
    assert "seed_if_needed" not in inspect.getsource(api._lifespan)
