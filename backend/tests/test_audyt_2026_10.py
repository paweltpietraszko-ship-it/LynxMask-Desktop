# tests/test_audyt_2026_10.py — reproduktory błędów z audytu 2026-10
"""
Reproduktory błędów znalezionych w audycie (arch/FINDING_2026-10_AUDYT.md).

Każdy test opisuje POPRAWNE zachowanie i jest oznaczony
@pytest.mark.xfail(strict=True, reason="BUG-..."): dziś pada (xfail), po naprawie
błędu zacznie przechodzić i wtedy strict=True zgłosi XPASS — sygnał, żeby
zdjąć marker w Tasku naprawczym.

Uwaga: pytest.ini ogranicza python_files do listy plików, więc ten plik NIE jest
zbierany przez `pytest tests/`. Uruchomienie jawne:
    cd backend && py -3 -m pytest tests/test_audyt_2026_10.py -q -rx
Nie wymaga działającego backendu. Testy z NER wymagają modelu pl_core_news_lg
(skip, jeśli go brak). Dane syntetyczne.
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections import namedtuple
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_NER = namedtuple("_NER", "text label confidence start end")


def _spacy_available() -> bool:
    try:
        import spacy
        spacy.load("pl_core_news_lg")
        return True
    except Exception:
        return False


needs_spacy = pytest.mark.skipif(not _spacy_available(), reason="brak modelu pl_core_news_lg")


def _fresh_state(with_ner: bool = True):
    """AppState jak w API (anonymizer + opcjonalnie spaCy) na pustym profilu w katalogu tymczasowym."""
    from pipeline import AppState
    from anonymizer import build_anonymizer
    st = AppState()
    if with_ner:
        import spacy_ner
        st.spacy_ner_mod = spacy_ner
    d = tempfile.mkdtemp(prefix="lynx_audyt_test_")
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
    return st


# ── Crashe ────────────────────────────────────────────────────────────────────

@pytest.mark.xfail(strict=True, reason="BUG-ONBOARD-BATCH: MAX_ONBOARD_BATCH nie jest importowany w anonymizer.py (NameError)")
def test_add_entities_batch_dziala():
    st = _fresh_state(with_ner=False)
    result = st.anon_map.add_entities_batch([("Zenobiusz", "OSOBA")])
    assert len(result) == 1


@pytest.mark.xfail(strict=True, reason="BUG-SEED-DEAD: seed_profile nie zasila trie (NameError, a po imporcie limit 100 < ~12 tys. wpisów)")
def test_seed_profile_zasila_trie():
    from seed_profile import seed_if_needed
    st = _fresh_state(with_ner=False)
    seed_if_needed(st.anon_map)
    assert len(st.anon_map.get_entity_names()) > 1000


# ── Wycieki PII ───────────────────────────────────────────────────────────────

# BUG-NER-PREFIX-FILTER — naprawione w LYNX-T01 (xfail zdjęty).
@pytest.mark.parametrize("name", ["Katarzyna Wiśniewska", "Kowalski", "Wiśniewski", "Aleksandra Kwiatkowska",
                                  # r2: imię/nazwisko będące też nazwą miejscowości (benchmark 27.06, lvl0/1)
                                  "Aleksandra Piotrowska", "Karolina Kozłowska", "Karolina Zając"])
def test_filtr_ner_nie_odrzuca_osob(name):
    from ner_layer import _filter_institutions
    assert _filter_institutions([_NER(name, "OSOBA", 0.9, 0, len(name))]), f"odrzucono OSOBA {name[:3]}***"


# BUG-NER-ADJ-FILTER — naprawione w LYNX-T01 (xfail zdjęty).
@pytest.mark.parametrize("name", ["Bartłomiej", "Maciej", "Nowakowej"])
def test_filtr_ner_nie_odrzuca_odmienionych_imion(name):
    from ner_layer import _filter_institutions
    assert _filter_institutions([_NER(name, "OSOBA", 0.9, 0, len(name))]), f"odrzucono OSOBA {name[:3]}***"


# LYNX-T01: potwierdzenie osoby nie może otworzyć drogi miejscowościom, przymiotnikom i słowom pospolitym.
@pytest.mark.parametrize("text,label", [
    ("Warszawie", "OSOBA"), ("KONTROLNA", "OSOBA"), ("Piątek", "OSOBA"), ("Encje", "OSOBA"),
    ("Warszawa", "FIRMA"), ("ZUS", "FIRMA"), ("Sąd Rejonowy w Krakowie", "FIRMA"),
    # r2: FP z benchmarku r1 — wielowyrazowe instytucje bez imienia/nazwiska nadal łapie filtr prefiksów
    ("Samorządowego Kolegium Odwoławczego", "FIRMA"), ("Komornik Sądowy'", "FIRMA"),
])
def test_filtr_ner_nadal_odrzuca_nie_osoby(text, label):
    from ner_layer import _filter_institutions
    assert not _filter_institutions([_NER(text, label, 0.9, 0, len(text))]), text


# LYNX-T01 (tryb degraded): bez Morfeusza nierozstrzygnięta jednowyrazowa OSOBA nie ginie w filtrze prefiksów.
def test_filtr_ner_bez_morfeusza_nie_odrzuca_osoby_prefiksem():
    import ner_layer
    with patch.object(ner_layer, "_morfeusz", False):
        assert ner_layer._filter_institutions([_NER("Wiśniewska", "OSOBA", 0.9, 0, 10)])
        # dokładna nazwa miejscowości nadal odrzucana (filtr exact, nie prefiks)
        assert not ner_layer._filter_institutions([_NER("Radom", "OSOBA", 0.9, 0, 5)])


@pytest.mark.xfail(strict=True, reason="BUG-IBAN-RECEPTA: wzorzec 'Numer recepty' \\d{22}(?!\\d) w credentials łapie końcówkę IBAN, 'PL6110' zostaje jawne")
@pytest.mark.parametrize("text", [
    "Przelew na konto: PL61 1090 1014 0000 0712 1981 2874.",
    "Konto 61109010140000071219812874 w banku.",
])
def test_iban_pl_bez_jawnej_resztki(text):
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        out, rev, _ = run_pipeline_new(text, anon_map={})
    assert "6110" not in out, out


@pytest.mark.xfail(strict=True, reason="BUG-EXPRESS-FAIL-OPEN: wyjątek w run_pipeline_express zwraca oryginał z force_block=False (S3)")
def test_express_fail_closed():
    import pipeline_new
    def boom(state):
        raise RuntimeError("awaria warstwy")
    with patch.object(pipeline_new, "apply_identity_layer", boom):
        out, rev, force_block = pipeline_new.run_pipeline_express("PESEL 44051401458", {})
    assert force_block is True


@pytest.mark.xfail(strict=True, reason="BUG-GUARD-MAPLEAK-UNREDACTED: przy MAP_LEAK guard zwraca redacted_text=text, zamazanie HIGH ginie")
def test_guard_map_leak_nie_odslania_pesel():
    from output_guard import guard_output_with_map, GuardMode
    text = "Pacjent Zenobiusz Audytowy, PESEL 44051401458."
    r = guard_output_with_map(text, None, mode=GuardMode.REDACT, known_plain=["Zenobiusz Audytowy"])
    assert r.blocked
    assert "44051401458" not in r.redacted_text


@pytest.mark.xfail(strict=True, reason="BUG-ALLOWLIST-SUBSTRING: allowlista porównuje frazę z treścią komunikatu naruszenia, nie z wartością")
def test_allowlist_nie_wylacza_innych_naruszen():
    from output_guard import guard_output_with_map, GuardMode
    text = "Spotkanie z Zenobiuszem Audytowym."
    r = guard_output_with_map(text, None, mode=GuardMode.REDACT,
                              known_plain=["Zenobiuszem Audytowym"], allowlist=["encja"])
    assert r.blocked


# ── Integralność tokenów / przywracanie ───────────────────────────────────────

# BUG-TOKEN-COLLISION — naprawione w LYNX-T03 (xfail zdjęty).
@needs_spacy
def test_dwie_osoby_dwa_tokeny():
    from pipeline import pseudonymize_document
    st = _fresh_state(with_ner=True)
    st.anon_map.add_entity("Jan Kowalski", "OSOBA")
    r = pseudonymize_document("Pacjent Jan Kowalski był w szpitalu. Dłużnik Piotr Nowak mieszka w Radomiu.", st)
    assert "Piotr Nowak" in r.reverse_map.values(), r.reverse_map


# LYNX-T03: numer z profilu nigdy nie trafia do innej osoby — także w dokumencie bez tej osoby.
@needs_spacy
def test_token_profilu_zarezerwowany_miedzy_dokumentami():
    from pipeline import pseudonymize_document
    st = _fresh_state(with_ner=True)
    jan = st.anon_map.add_entity("Jan Kowalski", "OSOBA")
    r1 = pseudonymize_document("Dłużnik Piotr Nowak mieszka w Radomiu.", st)
    piotr = [t for t, v in r1.reverse_map.items() if v == "Piotr Nowak"]
    assert piotr and piotr[0] != jan, r1.reverse_map
    assert jan not in r1.reverse_map, "encja profilu nieobecna w dokumencie nie może trafić do jego mapy"
    r2 = pseudonymize_document("Pacjent Jan Kowalski był w szpitalu.", st)
    assert r2.reverse_map.get(jan) == "Jan Kowalski", r2.reverse_map


# LYNX-T03: dwie formy osoby z profilu → ten sam token profilu, bez drugiego tokenu dla niej.
@needs_spacy
def test_formy_osoby_z_profilu_jeden_token():
    from pipeline import pseudonymize_document
    st = _fresh_state(with_ner=True)
    jan = st.anon_map.add_entity("Jan Kowalski", "OSOBA")
    r = pseudonymize_document("Pacjent Jan Kowalski był w szpitalu. Wniosek Jana Kowalskiego odrzucono.", st)
    assert "Kowalsk" not in r.text, r.text
    jana = [t for t, v in r.reverse_map.items() if "Kowalsk" in v]
    assert jana == [jan], r.reverse_map


# LYNX-T03: alokator — jeden token = jedna wartość; konflikt zatrzymuje pipeline (fail-closed przez WYS-2).
def test_alokator_odrzuca_drugą_wartosc_dla_tego_samego_tokenu():
    from pipeline_core import TokenAllocator
    a = TokenAllocator()
    a.register("OSOBA_001", "Jan Kowalski", 0, 12)
    a.register("OSOBA_001", "Jan  Kowalski", 20, 33)  # ta sama wartość kanoniczna — OK
    with pytest.raises(ValueError):
        a.register("OSOBA_001", "Piotr Nowak", 40, 51)
    a.reserve("OSOBA_007")
    assert a.assign("OSOBA", "Piotr Nowak") == "OSOBA_008"
    assert a.assign("OSOBA", "Piotr  Nowak") == "OSOBA_008"


# Korekta 2026-10-16 (FINDING_2026-10_MOBILE_PORT): Mobile TOKEN_RE = \b(...)_(\d{3})(?!\d)
# (PseudonymEngine.kt:89) — \b na początku zostaje, (?!\d) dotyczy końca. Tokeny 4-cyfrowe
# i token przyklejony z przodu do cyfr/liter nie pasują także w Mobile, więc nie są tu testowane.
@pytest.mark.xfail(strict=True, reason="BUG-TOKEN-RE-SPEC: koniec TOKEN_RE to \\b, spec S2/Mobile wymaga (?!\\d)")
@pytest.mark.parametrize("text,token", [("Zobacz OSOBA_001x tutaj", "OSOBA_001"), ("NUMER_004Teresa", "NUMER_004")])
def test_token_re_zgodny_z_spec(text, token):
    from anonymizer_init import TOKEN_SPAN_RE
    assert [m.group(0) for m in TOKEN_SPAN_RE.finditer(text)] == [token]


@pytest.mark.xfail(strict=True, reason="BUG-GLOBAL-SPACE-GLUE: _fix_ocr_email usuwa białe znaki po każdej kropce (nie tylko w e-mailach) — spec S2")
@pytest.mark.parametrize("text,fragment", [
    ("Pacjent był w szpitalu. Dłużnik mieszka w Radomiu.", "szpitalu. Dłużnik"),
    ("1. Strony zawierają umowę na czas nieokreślony.\n2. Umowa wchodzi w życie.", "nieokreślony.\n2."),
])
def test_fix_ocr_email_nie_skleja_zdan(text, fragment):
    from layers.ner_adapter import _fix_ocr_email
    assert fragment in _fix_ocr_email(text)


@pytest.mark.xfail(strict=True, reason="BUG-OCR-NORMALIZER-WORDS: normalizator OCR zamienia litery na cyfry w zwykłych słowach")
def test_ocr_normalizer_nie_psuje_slow():
    from pipeline_core import PipelineState, TokenAllocator
    from layers.ocr_normalizer import apply_ocr_normalizer
    s = PipelineState(text="Pan (nr tel. 512 987 654) zglosil sie do urzedu", allocator=TokenAllocator())
    apply_ocr_normalizer(s)
    assert "zglosil" in s.text, s.text


# ── False negatives / false positives ─────────────────────────────────────────

@pytest.mark.xfail(strict=True, reason="BUG-NER-FIRMA-INST: _INSTITUTION_IN_FIRMA_RE z IGNORECASE odrzuca firmy typu 'Nik-Pol Sp. z o.o.'")
@pytest.mark.parametrize("name", ["Nik-Pol Sp. z o.o.", "Agro-Gus S.A."])
def test_firma_z_fragmentem_skrotu_nie_odrzucona(name):
    from ner_layer import _filter_institutions
    assert _filter_institutions([_NER(name, "FIRMA", 0.9, 0, len(name))])


@needs_spacy
@pytest.mark.xfail(strict=True, reason="BUG-NER-FP: 'Kont0' (OCR z 'Konto:') rozpoznany jako OSOBA")
def test_kont0_nie_jest_osoba():
    from pipeline import pseudonymize_document
    st = _fresh_state(with_ner=True)
    r = pseudonymize_document("LISTA KONTROLNA\nEncje do sprawdzenia: Kont0: 123.", st)
    assert "Kont0" not in r.reverse_map.values(), r.reverse_map


# ── Bezpieczeństwo API ────────────────────────────────────────────────────────

@pytest.fixture
def api_client(monkeypatch):
    from fastapi.testclient import TestClient
    import pseudominizer_api as api
    monkeypatch.setattr(api, "_API_TOKEN", "a" * 64)
    monkeypatch.setattr(api, "_EXPRESS_TOKEN", "b" * 64)
    return TestClient(api.app), api  # bez lifespanu: nie dotyka api_token.txt ani profilu


@pytest.mark.xfail(strict=True, reason="BUG-EXPRESS-TOKEN-SCOPE: token z /express/token (bez auth) otwiera wszystkie endpointy")
def test_express_token_nie_otwiera_profilu(api_client):
    client, _ = api_client
    tok = client.get("/express/token").json()["token"]
    r = client.get("/profile/entities", headers={"X-Api-Token": tok})
    assert r.status_code == 401


@pytest.mark.xfail(strict=True, reason="BUG-CORS-WILDCARD: allow_origins=['*'] pozwala obcej stronie czytać odpowiedzi backendu")
def test_cors_nie_wpuszcza_obcego_origin(api_client):
    client, _ = api_client
    r = client.get("/express/token", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") not in ("*", "https://evil.example")


@pytest.mark.xfail(strict=True, reason="BUG-AUTH-EMPTY-TOKEN: przed lifespanem _API_TOKEN='' i compare_digest('', '') przepuszcza żądanie bez tokenu")
def test_pusty_token_nie_przepuszcza(monkeypatch):
    from fastapi.testclient import TestClient
    import pseudominizer_api as api
    monkeypatch.setattr(api, "_API_TOKEN", "")
    monkeypatch.setattr(api, "_EXPRESS_TOKEN", "")
    r = TestClient(api.app).get("/version")
    assert r.status_code == 401
