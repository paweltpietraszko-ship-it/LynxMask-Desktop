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
    # LYNX-NER-GEO-EXACT: miasto, miasto-nazwisko, adres i FIRMA z nazwą ulicy nadal odrzucane
    ("Radom", "OSOBA"), ("Zając", "OSOBA"), ("ul. Kowalskiego 7", "OSOBA"), ("Kowalskiego", "FIRMA"),
])
def test_filtr_ner_nadal_odrzuca_nie_osoby(text, label):
    from ner_layer import _filter_institutions
    assert not _filter_institutions([_NER(text, label, 0.9, 0, len(text))]), text


# LYNX-NER-GEO-EXACT: forma nazwiska kolidująca wyłącznie z nazwą ulicy przechodzi filtr exact i strict.
@pytest.mark.parametrize("name", ["Kowalskiego", "Nowaka", "Adamczyka"])
def test_filtr_ner_nazwisko_z_nazwy_ulicy(name):
    import ner_blocklist as nb
    from ner_layer import _filter_institutions
    low = name.lower()
    assert low in nb._PERSON_FORMS and low in nb._GEO_BY_SOURCE["street"], "przykład spoza przecięcia osoby/ulicy"
    assert low not in nb._GEO_BY_SOURCE["city"] | nb._GEO_BY_SOURCE["med"], "przykład ma inne pochodzenie geo"
    assert low in nb._STREET_ONLY_PERSON_FORMS, "ręczny wpis blocklisty"
    assert _filter_institutions([_NER(name, "OSOBA", 0.9, 0, len(name))]), f"odrzucono OSOBA {name[:3]}***"


# LYNX-NER-GEO-EXACT E1: warstwa inicjałów (spaCy nic nie wykrył) maskuje nazwisko z nazwy ulicy.
def test_inicjal_z_nazwiskiem_z_ulicy_bez_spacy():
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        out, rev, _ = run_pipeline_new("Zgoda K. Nowaka na zabieg.", anon_map={})
    assert "Nowaka" not in out and list(rev.values()) == ["K. Nowaka"], (out, rev)


# LYNX-NER-GEO-EXACT E2: ręczne dodanie do profilu — nazwisko z nazwy ulicy jako OSOBA tak, miasto i inny typ nie.
@pytest.mark.parametrize("text,token_type,status", [("Kowalskiego", "OSOBA", 200), ("Radom", "OSOBA", 400), ("Kowalskiego", "FIRMA", 400)])
def test_profil_dodaje_nazwisko_z_ulicy(api_client, monkeypatch, text, token_type, status):
    client, api = api_client
    added = []
    monkeypatch.setattr(api._app_state, "anon_map", type("M", (), {"add_entity": lambda self, t, k: added.append((t, k)) or "OSOBA_001"})())
    r = client.post("/profile/add-entity", json={"text": text, "token_type": token_type}, headers={"X-Api-Token": _FULL})
    assert r.status_code == status and bool(added) == (status == 200), (r.status_code, r.text)


# LYNX-NER-GEO-EXACT: pion NER → adapter → pipeline z kontrolowaną detekcją spaCy.
@pytest.mark.parametrize("text,token,value", [
    ("Wniosek Kowalskiego został przyjęty.", "OSOBA_001", "Kowalskiego"),
    ("Mieszka przy ul. Kowalskiego 7 w Radomiu.", "ADRES_001", "ul. Kowalskiego 7"),
])
def test_nazwisko_z_ulicy_w_pipeline(text, token, value):
    import spacy_ner
    from pipeline_new import run_pipeline_new
    start = text.index("Kowalskiego")
    hit = [spacy_ner.NERResult("Kowalskiego", "OSOBA", 0.9, start, start + len("Kowalskiego"))]
    with patch.object(spacy_ner, "detect_entities", return_value=hit):
        out, rev, _ = run_pipeline_new(text, anon_map={})
    assert "Kowalskiego" not in out and rev == {token: value}, (out, rev)


# LYNX-T01 (tryb degraded): bez Morfeusza nierozstrzygnięta jednowyrazowa OSOBA nie ginie w filtrze prefiksów.
def test_filtr_ner_bez_morfeusza_nie_odrzuca_osoby_prefiksem():
    import ner_layer
    with patch.object(ner_layer, "_morfeusz", False):
        assert ner_layer._filter_institutions([_NER("Wiśniewska", "OSOBA", 0.9, 0, 10)])
        # dokładna nazwa miejscowości nadal odrzucana (filtr exact, nie prefiks)
        assert not ner_layer._filter_institutions([_NER("Radom", "OSOBA", 0.9, 0, 5)])


# BUG-IBAN-RECEPTA — naprawione w LYNX-T07 (xfail zdjęty): jeden NUMER za cały numer, nic jawnego.
@pytest.mark.parametrize("text,span", [
    ("Przelew na konto: PL61 1090 1014 0000 0712 1981 2874.", "PL61 1090 1014 0000 0712 1981 2874"),
    ("Konto 61109010140000071219812874 w banku.", "61109010140000071219812874"),
])
def test_iban_pl_bez_jawnej_resztki(text, span):
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        out, rev, blocked = run_pipeline_new(text, anon_map={})
    tok = [t for t in rev if t.startswith("NUMER_")]
    assert len(rev) == 1 and len(tok) == 1 and out == text.replace(span, tok[0]) and not blocked, (out, rev)
    assert rev[tok[0]].replace(" ", "") == span.replace(" ", ""), rev  # cała wartość (financial normalizuje spacje — F3)


# LYNX-T07: recepta tylko z etykietą i jako cała wartość; credentials nie tnie dłuższych numerów.
@pytest.mark.parametrize("text,masked", [
    ("numer recepty: 1234567890123456789012", True), ("Recepta nr 1234567890123456789012", True),
    ("Ciąg 1234567890123456789012 bez etykiety.", False), ("Konto 61109010140000071219812874 w banku.", False),
    ("recepta 61109010140000071219812874", False),
])
def test_credentials_recepta_cala_wartosc(text, masked):
    from pipeline_core import PipelineState, TokenAllocator
    from layers.credentials import apply_credentials_layer
    s = PipelineState(text=text, allocator=TokenAllocator())
    apply_credentials_layer(s)
    rev = s.allocator.reverse_map
    assert bool(rev) == masked and (not masked or s.text == next(iter(rev))), (s.text, rev)  # całość jednym tokenem


# LYNX-T07: końcowy fallback ≥15 cyfr (oba tryby) — jedna wartość, tekst wokół bez zmian; K1 Codexa (e-mail z cyframi).
@pytest.mark.parametrize("express", [False, True])
@pytest.mark.parametrize("text,spans", [
    ("Ciąg 1234567890123456789012 bez etykiety.", ["1234567890123456789012"]),
    ("Nr 123456789012345.", ["123456789012345"]),
    ("Nr 123 456 789 012 345.", ["123 456 789 012 345"]),  # E1: telefon nie zabiera pierwszych 9 cyfr
    ("Nr 123-456-789-012-345.", ["123-456-789-012-345"]),
    ("Konto PL6110 9010 1400 000.", ["PL6110 9010 1400 000"]),  # E2: tablica rejestracyjna nie zabiera „PL6110”
    # Codex r3 F2: wielokrotne spacje/taby między grupami; O1/E3: 30 cyfr nie cięte przez financial
    ("Id 123  456  789  012  345.", ["123  456  789  012  345"]), ("Id 123\t\t456\t\t789\t\t012\t\t345.", ["123\t\t456\t\t789\t\t012\t\t345"]),
    ("Id 123 \t456 \t789 \t012 \t345.", ["123 \t456 \t789 \t012 \t345"]),
    ("Ciąg 12 3456 7890 1234 5678 9012 3456 7890 koniec.", ["12 3456 7890 1234 5678 9012 3456 7890"]),
    ("Wiersz 123456789012345\nDalej.", ["123456789012345"]),
    ("Kontakt: 123456789012345@example.pl. Numer: 123456789012345.", ["123456789012345@example.pl", "123456789012345"]),
])
def test_fallback_dlugie_numery_w_calosci(text, spans, express):
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new, run_pipeline_express
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        out, rev, blocked = (run_pipeline_express if express else run_pipeline_new)(text, anon_map={})
    expected = text
    for span in spans:
        tok = next(t for t, v in rev.items() if v == span)
        expected = expected.replace(span, tok, 1)
    assert out == expected and len(rev) == len(spans) and not blocked, (out, rev)
    assert not any(t in v for v in rev.values() for t in rev), rev  # brak zagnieżdżonych tokenów w mapie


# LYNX-T07: pełny tryb zachowuje fallback 8–14 cyfr; Express go nie dostaje (tylko ≥15).
def test_fallback_8_14_tylko_pelny_tryb():
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new, run_pipeline_express
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        full = run_pipeline_new("Ref 12345678.", anon_map={})
        expr = run_pipeline_express("Ref 12345678.", anon_map={})
    assert full[0] == "Ref NUMER_001." and expr[0] == "Ref 12345678.", (full, expr)


# Codex r3 F1: krótki numer 8+ po długim 15+ nadal maskowany w pełnym trybie (jedno przejście fallbacku).
@pytest.mark.parametrize("long", ["123456789012345", "123 456 789 012 345"])
def test_fallback_krotki_po_dlugim(long):
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new, run_pipeline_express
    text = f"Nr {long}, ref 12345678."
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        full = run_pipeline_new(text, anon_map={})
        expr = run_pipeline_express(text, anon_map={})
    assert full[0] == "Nr NUMER_001, ref NUMER_002." and sorted(full[1].values()) == sorted([long, "12345678"]), full
    assert expr[0] == "Nr NUMER_001, ref 12345678." and expr[1] == {"NUMER_001": long}, expr


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


# BUG-GLOBAL-SPACE-GLUE — naprawione w LYNX-T11 F1 (xfail zdjęty).
@pytest.mark.parametrize("text,fragment", [
    ("Pacjent był w szpitalu. Dłużnik mieszka w Radomiu.", "szpitalu. Dłużnik"),
    ("1. Strony zawierają umowę na czas nieokreślony.\n2. Umowa wchodzi w życie.", "nieokreślony.\n2."),
    ("Faktura nr 12/2026. Termin płatności 14 dni.", "12/2026. Termin"),
    ("Kontakt. jan@example.pl", "Kontakt. jan@"),
    ("Adres: anna. nowak@example.pl", "anna.nowak@example.pl"),  # OCR w lokalnej części e-maila nadal sklejany
])
def test_fix_ocr_email_nie_skleja_zdan(text, fragment):
    from layers.ner_adapter import _fix_ocr_email
    assert fragment in _fix_ocr_email(text)


# BUG-OCR-NORMALIZER-WORDS — naprawione w LYNX-T11 F2 (xfail zdjęty).
@pytest.mark.parametrize("text,expected", [
    ("Pan (nr tel. 512 987 654) zglosil sie do urzedu", "654) zglosil"),
    ("tel. +48 512 987 654. Termin płatności", "654. Termin"),
    ("Tel: +48 606 219 T2T", "606 219 727"),  # cyfry OCR w samym numerze nadal poprawiane
    # Codex r2 R1: ostatnia grupa złożona wyłącznie ze znaków OCR domyka 9 cyfr — nadal część numeru
    ("Tel: +48 606 219 TTT", "606 219 777"), ("Tel: +48 606 219 OOO", "606 219 000"), ("Tel: +48 606 219 III", "606 219 111"),
    ("tel. 123 45 To jest", "45 To jest"),  # człon bez cyfry niedomykający numeru zostaje słowem
    # Codex r3 R1: prefiks +48 sklejony z pierwszą grupą; 0048 i 48 bez plusa
    ("Tel: +48606 219 TTT", "606 219 777"), ("Tel: +48606 219 OOO", "606 219 000"), ("Tel: +48606 219 III", "606 219 111"),
    ("Tel: 0048 606 219 TTT", "606 219 777"), ("Tel: 48 606 219 TTT", "606 219 777"),
    ("tel. 48 362 12 34 To jest", "34 To jest"),  # 9 cyfr bez prefiksu + słowo „To” — słowo nietknięte
    # Codex r4 R1: grupy OCR wielką + małymi literami to nadal cyfry numeru
    ("Tel: +48 606 219 Ill", "606 219 111"), ("Tel: +48 606 219 Ooo", "606 219 000"), ("Tel: +48 606 219 Tll", "606 219 711"),
    ("tel. +48 512 987 654 To jest", "654 To jest"),
])
def test_ocr_normalizer_nie_psuje_slow(text, expected):
    from pipeline_core import PipelineState, TokenAllocator
    from layers.ocr_normalizer import apply_ocr_normalizer
    s = PipelineState(text=text, allocator=TokenAllocator())
    apply_ocr_normalizer(s)
    assert expected in s.text, s.text


# LYNX-T11: pion pipeline — tekst poza tokenami wierny, e-mail i telefon nadal maskowane (wynik + reverse_map).
@pytest.mark.parametrize("text,value", [
    ("Faktura nr 12/2026. Kontakt: anna.nowak@example.pl. Termin płatności 14 dni.", "anna.nowak@example.pl"),  # E1
    ("Faktura nr 12/2026. Kontakt: tel. 512 987 654. Termin płatności 14 dni.", "512987654"),
    ("Faktura nr 12/2026. Kontakt: jan@wp. pl. Termin płatności 14 dni.", "jan@wp.pl"),  # OCR TLD nadal łączony
    # Codex r2 R2: pełna domena + „. słowo” małą literą to koniec zdania, nie TLD
    ("Faktura nr 12/2026. Kontakt: nowak@example.pl. termin. Termin płatności 14 dni.", "nowak@example.pl"),
    ("Faktura nr 12/2026. Kontakt: nowak@example.pl. dalej. Termin płatności 14 dni.", "nowak@example.pl"),
])
def test_wiernosc_tekstu_i_maskowanie(text, value):
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        out, rev, _ = run_pipeline_new(text, anon_map={})
    assert "12/2026. Kontakt" in out and ". Termin płatności 14 dni." in out, out
    joined = "".join(rev.values()).lower()
    assert [v for v in rev.values() if value in v.replace(" ", "")] and "termin" not in joined and "dalej" not in joined, (out, rev)
    assert value not in out.replace(" ", ""), out


# Codex r2 R1 (pion): telefon z ostatnią grupą wyłącznie ze znaków OCR nadal zamaskowany, końcówka nie jest jawna.
@pytest.mark.parametrize("prefix", ["+48 ", "+48"])  # Codex r3: także prefiks sklejony z pierwszą grupą
@pytest.mark.parametrize("tail", ["TTT", "OOO", "III", "Ill", "Ooo", "Tll"])  # Codex r4: także wielka + małe
def test_telefon_ocr_ostatnia_grupa_zamaskowany(tail, prefix):
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        out, rev, _ = run_pipeline_new(f"Kontakt: Tel: {prefix}606 219 {tail}", anon_map={})
    assert tail not in out and any(v.startswith("48606219") for v in rev.values()), (out, rev)


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

# Dozwolony Host jawnie w kliencie testowym (LYNX-T02) — bez produkcyjnego wyjątku dla "testserver".
_LOCAL = "http://127.0.0.1:8765"
_FULL, _EXPR = "a" * 64, "b" * 64


@pytest.fixture
def api_client(monkeypatch):
    from fastapi.testclient import TestClient
    import pseudominizer_api as api
    monkeypatch.setattr(api, "_API_TOKEN", _FULL)
    monkeypatch.setattr(api, "_EXPRESS_TOKEN", _EXPR)
    return TestClient(api.app, base_url=_LOCAL), api  # bez lifespanu: nie dotyka api_token.txt ani profilu


# BUG-EXPRESS-TOKEN-SCOPE — naprawione w LYNX-T02 (xfail zdjęty).
def test_express_token_nie_otwiera_profilu(api_client):
    client, _ = api_client
    tok = client.get("/express/token").json()["token"]
    r = client.get("/profile/entities", headers={"X-Api-Token": tok})
    assert r.status_code == 401


# BUG-CORS-WILDCARD — naprawione w LYNX-T02 (xfail zdjęty).
def test_cors_nie_wpuszcza_obcego_origin(api_client):
    client, _ = api_client
    r = client.get("/express/token", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") not in ("*", "https://evil.example")


# BUG-AUTH-EMPTY-TOKEN — naprawione w LYNX-T02 (xfail zdjęty).
def test_pusty_token_nie_przepuszcza(monkeypatch):
    from fastapi.testclient import TestClient
    import pseudominizer_api as api
    monkeypatch.setattr(api, "_API_TOKEN", "")
    monkeypatch.setattr(api, "_EXPRESS_TOKEN", "")
    r = TestClient(api.app, base_url=_LOCAL).get("/version")
    assert r.status_code == 401


# LYNX-T02: token Express otwiera wyłącznie maskowanie; pełny token — wszystko.
@pytest.mark.parametrize("method,path", [
    ("GET", "/profile/entities"), ("GET", "/profile/export-dict"), ("GET", "/archive"), ("GET", "/version"),
])
def test_express_token_bez_dostepu_poza_maskowaniem(api_client, method, path):
    client, _ = api_client
    assert client.request(method, path, headers={"X-Api-Token": _EXPR}).status_code == 401
    assert client.request(method, path, headers={"X-Api-Token": _FULL}).status_code != 401


@pytest.mark.parametrize("path", ["/preview", "/preview-express"])
@pytest.mark.parametrize("tok", [_EXPR, _FULL], ids=["express", "pelny"])
def test_maskowanie_przechodzi_auth_z_tokenem_express_i_pelnym(api_client, path, tok):
    client, _ = api_client
    files = {"file": ("t.txt", b"Jan Kowalski, PESEL 90040512345.", "text/plain")}
    r = client.post(path, files=files, headers={"X-Api-Token": tok})
    assert r.status_code not in (400, 401), r.status_code


# LYNX-T02: DNS rebinding — obcy Host odrzucany zanim dostanie token, także bez Origin.
def test_obcy_host_odrzucony_przed_tokenem_express(api_client):
    client, _ = api_client
    r = client.get("/express/token", headers={"Host": "evil.example:8765"})
    assert r.status_code == 400 and _EXPR not in r.text
    r = client.get("/profile/entities", headers={"Host": "evil.example:8765", "X-Api-Token": _FULL})
    assert r.status_code == 400


@pytest.mark.parametrize("host", ["127.0.0.1:8765", "localhost:8765"])
def test_lokalny_host_przechodzi(api_client, host):
    client, _ = api_client
    r = client.get("/express/token", headers={"Host": host})
    assert r.status_code == 200 and r.json()["token"] == _EXPR


@pytest.mark.parametrize("origin", ["http://localhost:1420", "http://tauri.localhost"])
def test_cors_wpuszcza_ui_tauri(api_client, origin):
    client, _ = api_client
    r = client.get("/health", headers={"Origin": origin})
    assert r.headers.get("access-control-allow-origin") == origin


# ── LYNX-DICT-LEAKTEST: wiarygodność runnera audyt/engine_quality.py (bez spaCy) ──────────────────────

def _eq():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "audyt"))
    import engine_quality
    return engine_quality


def _res(text, rev=None, blocked=False, error=None):
    from pipeline import PipelineResult
    return PipelineResult(text=text, reverse_map=rev or {}, guard_blocked=blocked, error=error)


def test_quality_przypadki_i_holdout_deterministyczne(tmp_path):
    eq = _eq()
    assert eq.build_cases() == eq.build_cases()
    src = tmp_path / "h.json"
    src.write_text('{"nowak": ["nowaka"], "zzyxowski": [], "qwertyk": ["qwertyka"], "abcdzki": []}', encoding="utf-8")
    a, info = eq.load_holdout(str(src), 7)
    assert a == eq.load_holdout(str(src), 7)[0] and info["status"] == "OK" and info["rejected_overlap"] == 1
    assert all("Nowak" not in c[3] for c in a)  # forma ze słownika silnika odrzucona
    assert eq.load_holdout(str(tmp_path / "brak.json"), 7) == (None, {"status": "NOT_MEASURED", "reason": "brak pliku holdout"})


def test_quality_m1_blocked_i_bledy_nie_sa_sukcesem():
    eq = _eq()
    t, s = "Nabywca: Jan Kowalski.", "Jan Kowalski"
    assert eq.classify_m1(t, s, "OSOBA", _res("Nabywca: OSOBA_001.", {"OSOBA_001": s})) == "masked"
    assert eq.classify_m1(t, s, "OSOBA", _res("Nabywca: OSOBA_001.", {"OSOBA_001": s}, blocked=True)) == "blocked"
    assert eq.classify_m1(t, s, "OSOBA", _res(t, error="boom")) == "error"
    assert eq.classify_m1(t, s, "OSOBA", _res(t)) == "leak"
    assert eq.classify_m1(t, s, "OSOBA", _res("Nabywca: OSOBA_001 Kowalski.", {"OSOBA_001": "Jan"})) == "leak_partial"
    assert eq.classify_m1(t, s, "OSOBA", _res("Nabywca: FIRMA_001.", {"FIRMA_001": s})) == "wrong_category"
    iban = "PL61 1090 1014 0000 0712 1981 2874"
    assert eq.classify_m1(f"Konto {iban}.", iban, "NUMER", _res("Konto PL6110NUMER_001.", {"NUMER_001": "9010140000071219812874"})) == "partial_mask"
    # Codex r2 R1: tokeny o różnych kategoriach na jednej osobie i wpis w mapie bez tokenu w wyniku to nie sukces
    assert eq.classify_m1(t, s, "OSOBA", _res("Nabywca: OSOBA_001 FIRMA_001.", {"OSOBA_001": "Jan", "FIRMA_001": "Kowalski"})) == "wrong_category"
    assert eq.classify_m1(t, s, "OSOBA", _res("Nabywca: EMAIL_001 OSOBA_001.", {"EMAIL_001": "Jan", "OSOBA_001": "Kowalski"})) == "wrong_category"
    assert eq.classify_m1(t, s, "OSOBA", _res("Nabywca: .", {"OSOBA_001": s})) == "no_mapping"
    boom = eq.measure([("X", "M1", "OSOBA", t, s, {})], lambda _: 1 / 0)
    assert boom[0]["status"] == "error" and boom[0]["m3"]["status"] == "blocked_or_error"


def test_quality_m2_fp_a_kontrakt():
    eq = _eq()
    kwota = {"KWOTA": ["10 zł"]}
    assert eq.classify_m2({}, _res("w OSOBA_001", {"OSOBA_001": "piątek"})) == "fp"
    assert eq.classify_m2(kwota, _res("Do zapłaty KWOTA_001.", {"KWOTA_001": "10 zł"})) == "contract"
    # Codex r2 R2: dozwolona kategoria na zwykłym słowie (kwota prawdziwa jawna) to FP
    assert eq.classify_m2(kwota, _res("Do KWOTA_001 10 zł.", {"KWOTA_001": "zapłaty"})) == "fp"
    # Codex r3 R2: dozwolona kategoria na zwykłym słowie dzielącym litery z oczekiwaną wartością, adres nietknięty
    adres = {"ADRES": ["ul. Kowalskiego 7"]}
    assert eq.classify_m2(adres, _res("Biuro przy ul. Kowalskiego 7; ADRES_001 naprawia bramę.", {"ADRES_001": "kowal"})) == "fp"
    assert eq.classify_m2(adres, _res("Biuro przy ul. Kowalskiego 7 ADRES_001 centrum.", {"ADRES_001": "w"})) == "fp"
    assert eq.classify_m2(adres, _res("Biuro przy ADRES_001 w centrum.", {"ADRES_001": "ul. Kowalskiego 7"})) == "contract"
    assert eq.classify_m2({}, _res("Zapłata przelewem.")) == "clean"
    assert eq.classify_m2({}, _res("x", blocked=True)) == "blocked"


def test_quality_m3_spacja_i_brak_mapy():
    eq = _eq()
    t = "Nabywca: Jan Kowalski. Termin 14 dni."
    assert eq.roundtrip(t, _res("Nabywca: OSOBA_001. Termin 14 dni.", {"OSOBA_001": "Jan Kowalski"}), ["Jan Kowalski"])["status"] == "identical"
    r = eq.roundtrip(t, _res("Nabywca: OSOBA_001.Termin 14 dni.", {"OSOBA_001": "Jan Kowalski"}), ["Jan Kowalski"])
    assert r["status"] == "diff" and r["diff_outside_spans"] == 1
    assert eq.roundtrip(t, _res("Nabywca: OSOBA_002. Termin 14 dni.", {"OSOBA_001": "Jan Kowalski"}))["status"] == "missing_map"
    assert eq.roundtrip(t, _res(t, blocked=True))["status"] == "blocked_or_error"


def test_quality_profil_tylko_w_temp_i_sprzatany_przy_bledzie(tmp_path, monkeypatch):
    import glob
    eq = _eq()
    with pytest.raises(SystemExit):
        eq.main(["--out", os.path.join(eq.ROOT, "quality.json")])  # zapis do repo zabroniony
    if os.name == "nt":  # Codex r2 R3: ta sama ścieżka inną wielkością liter
        with pytest.raises(SystemExit):
            eq._out_path(os.path.join(eq.ROOT, "quality.json").swapcase())
    seen = []
    def boom(tmp):
        seen.append(tmp)
        raise RuntimeError("awaria")
    monkeypatch.chdir(os.getcwd())  # main() przechodzi do backend/ — przywróć cwd po teście
    with (patch.object(eq, "_engine_available", return_value=(True, "")), patch.object(eq, "build_state", boom),
          patch.object(eq.logging, "disable")):
        with pytest.raises(RuntimeError):
            eq.main(["--out", str(tmp_path / "q.json")])
    assert seen and os.path.commonpath([seen[0], tempfile.gettempdir()]) == tempfile.gettempdir()
    assert not os.path.exists(seen[0]) and not glob.glob(os.path.join(tempfile.gettempdir(), "lynx_quality_*"))
    with patch.object(eq, "_engine_available", return_value=(False, "ImportError")), patch.object(eq.logging, "disable"):
        assert eq.main(["--out", str(tmp_path / "n.json")]) == 2  # brak NER: NOT_RUN, nie atrapa
    assert '"status": "NOT_RUN"' in (tmp_path / "n.json").read_text(encoding="utf-8")


# LYNX-EMAIL-LOCALPART-OCR: „anna. nowak@…” w obu trybach jednym EMAIL, „anna.” niejawne, Przywróć znak w znak.
@pytest.mark.parametrize("express", [False, True])
def test_email_localpart_ocr_bez_jawnego_fragmentu(express):
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new, run_pipeline_express
    text = "Kontakt: anna. nowak@example.pl. Termin płatności."
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        out, rev, _ = (run_pipeline_express if express else run_pipeline_new)(text, anon_map={})
    assert out == "Kontakt: EMAIL_001. Termin płatności." and rev == {"EMAIL_001": "anna. nowak@example.pl"}
