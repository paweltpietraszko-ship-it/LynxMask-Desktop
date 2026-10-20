# LYNX-NER-MULTILINE: encja NER, której span przechodzi przez koniec wiersza, nie może zniknąć w podmianie.
# Uruchamiać jawnie: py -3 -m pytest tests/test_ner_multiline.py -q (plik spoza pytest.ini python_files).
import contextlib
import io
import os
import re
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

TOKEN = re.compile(r"(?:FIRMA|OSOBA|ADRES|INSTYTUCJA|NUMER|EMAIL|KWOTA)_\d{3}")


def _restore(out: str, rev: dict) -> str:
    return TOKEN.sub(lambda m: rev.get(m.group(0), m.group(0)), out)


def _check(text: str, out: str, rev: dict, hidden: list, visible: list = ()):
    assert out.count("\n") == text.count("\n"), out                   # struktura wierszy zachowana
    assert not any("\n" in v for v in rev.values()), rev              # koniec wiersza nigdy w wartości mapy
    assert not any(t in v for v in rev.values() for t in rev), rev     # brak tokenu w tokenie
    assert _restore(out, rev) == text, (out, rev)                     # Przywróć 1:1
    for word in hidden:
        assert word not in out, (word, out)
    for word in visible:
        assert word in out and word not in rev.values(), (word, out, rev)


# 1. Podstawiony wynik SpaCy (dokładne offsety, span z \n) → prawdziwa logika ner_layer + adapter + pipeline Full.
def _fake_ner(*frags):
    from spacy_ner import NERResult

    def detect(text):
        out = []
        for label, frag in frags:
            start = text.find(frag)
            if start >= 0:
                out.append(NERResult(text=frag, label=label, confidence=0.9, start=start, end=start + len(frag)))
        return out
    return detect


@pytest.mark.parametrize("text,frags,hidden,visible", [
    ("Członkowie:\nBeata Zielińska\nDariusz Wróblewski\nkoniec",                       # dwie osoby w dwóch liniach
     [("OSOBA", "Beata Zielińska\nDariusz Wróblewski")], ["Zielińska", "Wróblewski", "Beata", "Dariusz"], []),
    ("w składzie:\nAdam Kowalczyk\nProtokolant: Celina Dąbrowska",                  # osoba + rola w następnej linii
     [("OSOBA", "Adam Kowalczyk\nProtokolant")], ["Kowalczyk"], ["Protokolant"]),
    ("Pismo podpisała Joanna \nKotecka z działu kadr.",                             # jedna osoba przełamana
     [("OSOBA", "Joanna \nKotecka")], ["Joanna", "Kotecka"], []),
    ("Odwołanie wniosła Alfa Systemy \nSpółka Akcyjna z siedzibą w Gdańsku.",       # firma przełamana; sama forma
     [("FIRMA", "Alfa Systemy \nSpółka Akcyjna")], ["Alfa Systemy"], ["Spółka Akcyjna"]),  # nie identyfikuje
    ("Ofertę złożyła Beta Serwis Sp. z o.o.\nw Warszawie oraz inni.",               # część FIRMA od małej litery
     [("FIRMA", "Beta Serwis Sp. z o.o.\nw Warszawie")], ["Beta Serwis"], ["w Warszawie"]),
    ("Pismo Prezesa Urzędu\nZamówień Publicznych; Prawo zamówień publicznych.",     # bez formy prawnej: instytucja,
     [("FIRMA", "Urzędu\nZamówień Publicznych")], [], ["Zamówień Publicznych"]),     # nie dzielić (MAP_LEAK Guarda)
    ("Pismo podpisał Adam Kowalczyk\nw dniu 3 marca.",                              # tylko końcowy \n
     [("OSOBA", "Adam Kowalczyk\n")], ["Kowalczyk"], []),
])
def test_span_z_nowa_linia_podstawiony_ner(text, frags, hidden, visible):
    import spacy_ner
    from pipeline_new import run_pipeline_new
    with patch.object(spacy_ner, "detect_entities", _fake_ner(*frags)), contextlib.redirect_stdout(io.StringIO()):
        out, rev, blocked = run_pipeline_new(text, anon_map={})
    assert not blocked, (out, rev)
    _check(text, out, rev, hidden, visible)


@pytest.mark.parametrize("span", ["Testopolia Systemy\n", "Testopolia Systemy\r\n", "\nTestopolia Systemy", "Testopolia\n",
                                  "Testopolia Systemy\nSp. z o.o."])
def test_firma_koniec_wiersza_na_brzegu_lub_z_forma(span):
    """Codex r2 F1: koniec wiersza tylko na brzegu spanu = dotychczasowa ścieżka (FIRMA bez formy nadal maskowana);
    forma prawna w następnej linii nie dokleja \\n do wartości (podział po _firma_bounds)."""
    import spacy_ner
    from pipeline_new import run_pipeline_new
    text = "Wykonawca: " + span + "; koniec."
    with patch.object(spacy_ner, "detect_entities", _fake_ner(("FIRMA", span))), contextlib.redirect_stdout(io.StringIO()):
        out, rev, blocked = run_pipeline_new(text, anon_map={})
    assert not blocked, (out, rev)
    _check(text, out, rev, ["Testopolia"])


def test_propagacja_nie_rozsyla_imienia():
    """ROZSZERZENIE CC (C047, Paweł): token „Piotr Masłowski” nie trafia na „Piotr” innej osoby ani na „Piotrowski"."""
    import spacy_ner
    from pipeline_new import run_pipeline_new
    text = "Pismo podpisał Piotr Masłowski.\nKopia: Piotr Wrona oraz Jan Piotrowski."
    with patch.object(spacy_ner, "detect_entities", _fake_ner(("OSOBA", "Piotr Masłowski"))), \
            contextlib.redirect_stdout(io.StringIO()):
        out, rev, blocked = run_pipeline_new(text, anon_map={})
    # [LYNX-OCR-GATE-COMPARE E2b] inne imiona/nazwiska ze słownika są teraz zakryte własnymi tokenami (port Mobile 3a);
    # sedno C047 bez zmian: token „Piotr Masłowski” stoi tylko w jego miejscu, nie na „Piotr” innej osoby ani „Piotrowski”.
    tok = [t for t, v in rev.items() if v == "Piotr Masłowski"]
    assert len(tok) == 1 and out.count(tok[0]) == 1 and "Masłowski" not in out, (out, rev)
    assert not blocked and _restore(out, rev) == text


@pytest.mark.parametrize("text,frags,name", [
    ("Zielińska Katarzyna złożyła wniosek. Katarzyna Zielińska podpisała.", [("OSOBA", "Katarzyna Zielińska")], "Katarzyna"),
    ("Wniosek złożyła Pani Wiktoria, Róża rośnie w ogrodzie.", [], "Wiktoria"),          # Pan/Pani; „Róża” — E2b: własny token
])
def test_imie_przy_osobie_dostaje_wlasny_token(text, frags, name):
    """Propozycja Pawła: imię obok tokenu osoby lub po Pan/Pani → własny token z dosłowną wartością (nie cudzy, nie jawne).
    Pełne Przywróć nie jest tu sprawdzane: propagowane nazwisko ma wartość pełnej formy — znany finding K2."""
    import spacy_ner
    from pipeline_new import run_pipeline_new
    with patch.object(spacy_ner, "detect_entities", _fake_ner(*frags)), contextlib.redirect_stdout(io.StringIO()):
        out, rev, blocked = run_pipeline_new(text, anon_map={})
    # [LYNX-OCR-GATE-COMPARE E2b] samotna „Róża” (słownik imion) zakryta jak w Mobile — świadome nadmaskowanie; nie sklejona z imieniem
    assert not blocked and name not in out and name in rev.values() and "Wiktoria Róża" not in rev.values(), (out, rev)


def test_dwie_osoby_w_liniach_to_dwa_tokeny():
    import spacy_ner
    from pipeline_new import run_pipeline_new
    text = "Członkowie:\nBeata Zielińska\nDariusz Wróblewski\nkoniec"
    with patch.object(spacy_ner, "detect_entities", _fake_ner(("OSOBA", "Beata Zielińska\nDariusz Wróblewski"))), \
            contextlib.redirect_stdout(io.StringIO()):
        out, rev, _ = run_pipeline_new(text, anon_map={})
    assert sorted(rev.values()) == ["Beata Zielińska", "Dariusz Wróblewski"], rev


def test_instytucja_przelamana_nie_jest_firma():
    """Całość spanu przechodzi filtr instytucji przed podziałem — kawałki sądu nie stają się FIRMA."""
    import spacy_ner
    from pipeline_new import run_pipeline_new
    text = "Skarga wniesiona do Sądu Okręgowego\nw Gdańsku w terminie."
    with patch.object(spacy_ner, "detect_entities", _fake_ner(("FIRMA", "Sądu Okręgowego\nw Gdańsku"))), \
            contextlib.redirect_stdout(io.StringIO()):
        out, rev, blocked = run_pipeline_new(text, anon_map={})
    assert not any(k.startswith("FIRMA") for k in rev) and "w Gdańsku" in out, (out, rev)
    assert not blocked and _restore(out, rev) == text


# test_express_bez_ner_bez_regresji usunięty: ścieżka Express bez NER usunięta (LYNX-EXPRESS-ONE-ENGINE).


# 2. Prawdziwy SpaCy + pełny pipeline (Guard): syntetyki, dla których model faktycznie zwraca span z \n.
@pytest.fixture(scope="module")
def _full():
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "audyt")))
    import engine_quality as eq
    ok, why = eq._engine_available()
    if not ok:
        pytest.skip(f"NER/Morfeusz niedostępny: {why}")
    import tempfile
    import pipeline
    import spacy_ner
    st = eq.build_state(tempfile.mkdtemp(prefix="lynx_multiline_"))
    return spacy_ner, (lambda t: pipeline.pseudonymize_document(t, st))


@pytest.mark.parametrize("text,hidden", [
    ("Członkowie:\nBeata Zielińska\nDariusz Wróblewski\nProtokolant:", ["Zielińska", "Wróblewski"]),
    ("Oświadczenie złożyli senatorowie: Halina Wrzos, Andrzej Lipka,\nZygmunt Mazurek, Joanna Sowa\noraz inni.",
     ["Wrzos", "Lipka", "Mazurek", "Sowa"]),
    ("Pismo podpisała Joanna \nKotecka z działu kadr.", ["Joanna", "Kotecka"]),
    ("Halina Wrzos \nAndrzej Lipka \nZygmunt Mazurek \nJoanna Sowa", ["Wrzos", "Lipka", "Mazurek", "Sowa"]),
])
def test_prawdziwy_spacy_span_z_nowa_linia(_full, text, hidden):
    spacy_ner, run = _full
    with contextlib.redirect_stdout(io.StringIO()):
        ents = spacy_ner.detect_entities(text)
        res = run(text)
    assert any("\n" in text[e.start:e.end] for e in ents), "model nie zwrócił spanu z \\n — syntetyk nie falsyfikuje"
    assert not res.guard_blocked, res.guard_reasons
    _check(text, res.text, res.reverse_map, hidden)
