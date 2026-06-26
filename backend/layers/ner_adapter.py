"""
layers/ner_adapter.py  v1.6
Adapter NER — wywołuje ner_layer.process_ner() i rejestruje tokeny w allocatorze.
ner_layer.py nie jest modyfikowany.

v1.4: [BUG-NER-WRONG-ARG] process_ner(text, spacy_ner_mod) — drugi argument
  to moduł spacy_ner, nie anon_map. ner_adapter importuje spacy_ner i przekazuje
  moduł. Poprzednio: process_ner(state.text, anon_map) → spacy_ner_mod=dict →
  spacy_ner_mod.NERBlockError → AttributeError → ner_error=True → force_block.
  Efekt: NER zawsze crashował w ner_adapter, każda odpowiedź była blokowana.
v1.3: [WYS-1] extract_ner_results() i apply_ner_layer() mają teraz try/except.
  Błąd NER → state.ner_error = True. run_pipeline_new() sprawdza tę flagę
  i zwraca force_block=True do callera zamiast cicho kontynuować bez NER.
v1.2: Port z PseudonymEngine.kt / NameEngine.kt:
  - Pre-processing: naprawa emaili z błędami OCR (spacja wokół @, spacja po kropce
    przed @) — port z PseudonymEngine.kt pre-processing bloku
  - Propagacja OSOBA (Warstwa 3c): jeśli SpaCy wykrył "Jan Kowalski" → OSOBA_001,
    to wszystkie formy fleksyjne nazwiska z surnames_top1000.json też stają się OSOBA_001
  - Inicjały: "K. Kowalski" → OSOBA gdy nazwisko w słowniku
  - Filtr @: odrzuca fragmenty emaili (OCR: "@firma.pl" jako OSOBA)

v1.1: Dodano extract_ner_results() — pre-ekstrakcja NER z tekstu PRZED apply_address_layer.
  SpaCy musi widzieć pełny adres (ul. X, kod miasto) żeby poprawnie rozpoznać
  poprzedzające imię/nazwisko jako OSOBA. Po zamaskowaniu adresu traci ten kontekst.
  apply_ner_layer() używa state.ner_results jeśli wypełnione (pre-cache),
  w przeciwnym razie wywołuje process_ner() bezpośrednio (fallback).
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spacy_ner as _spacy_ner_mod
from ner_layer import process_ner
from pipeline_core import PipelineState, TokenAllocator

# ── Słownik form fleksyjnych nazwisk (port: LookupTables.surnamesForms) ─────
_DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load_surnames_forms() -> dict[str, list[str]]:
    path = os.path.join(_DATA_DIR, "surnames_top1000.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_SURNAMES_FORMS: dict[str, list[str]] = _load_surnames_forms()

# Płaski zbiór wszystkich form fleksyjnych → szybkie sprawdzenie
_SURNAMES_FORMS_FLAT: frozenset[str] = frozenset(
    form
    for forms in _SURNAMES_FORMS.values()
    for form in forms
)

# ── Regex inicjałów: "K. Kowalski" → OSOBA (port: INITIALS_REGEX NameEngine.kt v1.12)
_INITIALS_RE = re.compile(
    r"\b([A-ZŁŚŹĆŃĄĘÓŻ]\.)[^\S\n]+([A-ZŁŚŹĆŃĄĘÓŻ][a-ząćęłńóśźż]{3,})\b"
)

# ── Token RE — żeby nie podmieniać już zamaskowanych fragmentów ──────────────
_TOKEN_RE = re.compile(r"\b(FIRMA|OSOBA|NUMER|EMAIL|KWOTA|ADRES)_\d{3}\b")

# ── Filtry NER (port: FIX-NER-GLOBAL stary pipeline + Cursor review) ─────────
# Odrzuć warianty będące prefiksem adresu ("os. Bolesława..." jako OSOBA)
_ADDR_PREFIX_RE = re.compile(
    r"^(?:ul\.|al\.|pl\.|os\.|sk\.|rondo\s|park\s)", re.IGNORECASE
)
# Odrzuć śmieciowe jednowyrazowe FIRMA (sama forma prawna bez nazwy)
_BARE_SUFFIX_RE = re.compile(
    r"^(?:sp\.?\s*z\.?\s*o\.?\s*o\.?|s\.a\.|sp\.?\s*k\.?|sp\.?\s*j\.?|"
    r"spółka|spółki|spółce|spółkę|s\.?\s*c\.?)$",
    re.IGNORECASE,
)
# Oczyść token z przyrostka prawnego: "FIRMA_001 S.A." → "FIRMA_001"
_FIRMA_CLEANUP_RE = re.compile(
    r"(FIRMA_\d{3})\s+(?:S\.A\.|Sp\.?\s*z\s*o\.o\.|Sp\.?\s*k\.|Sp\.?\s*j\.|S\.C\.)",
    re.IGNORECASE,
)

# ── Polskie diakrytyki do strip (NFD) ────────────────────────────────────────
def _strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _fix_ocr_email(text: str) -> str:
    """Port z PseudonymEngine.kt pre-processing bloku emaili OCR.

    Naprawia typowe błędy OCR w adresach email:
      anna. nowak@wp.pl  → anna.nowak@wp.pl   (spacja po kropce przed @)
      anna.nowak@ wp.pl  → anna.nowak@wp.pl   (spacja po @)
      anna.nowak @wp.pl  → anna.nowak@wp.pl   (spacja przed @)
    """
    # "(@" → "@"
    text = text.replace("(@", "@")
    # "a. b@" → "a.b@" (spacja po kropce w local-part, lookbehind na ≥2 znaki)
    text = re.sub(
        r"(?<=[a-zA-Z0-9]{2})([a-zA-Z0-9])\.\s+([a-zA-Z0-9])",
        lambda m: f"{m.group(1)}.{m.group(2)}",
        text,
    )
    # "@ wp" → "@wp"
    text = re.sub(r"@\s+([a-zA-Z0-9])", lambda m: f"@{m.group(1)}", text)
    # "abc @wp" → "abc@wp"
    text = re.sub(r"([a-zA-Z0-9])\s+@([a-zA-Z0-9])", lambda m: f"{m.group(1)}@{m.group(2)}", text)
    return text


def _propagate_osoba(text: str, token_id: str, full_name: str) -> str:
    """Port z PseudonymEngine.kt Warstwa 3c — propagacja nazwisk.

    Jeśli SpaCy wykrył "Jan Kowalski" → OSOBA_001, propaguje token na:
    1. Regex-based: "Kowalski[a-ząćęłńóśźż]{0,6}" (odmiany przez przypadki)
    2. Lookup-based: formy z surnames_top1000.json zaczynające się od tych samych 5 liter
    """
    words = full_name.strip().split()
    if len(words) < 2:
        return text

    for name_part in words:
        if len(name_part) <= 3 or not name_part[0].isupper():
            continue

        # 1. Regex-based propagacja (odmiany przez przypadki)
        escaped = re.escape(name_part)
        prop_re = re.compile(
            rf"\b{escaped}[a-ząćęłńóśźż]{{0,6}}\b",
            re.IGNORECASE,
        )
        def _replace_if_not_token(m: re.Match, tid: str = token_id) -> str:
            if _TOKEN_RE.search(m.group(0)):
                return m.group(0)
            return tid
        text = prop_re.sub(_replace_if_not_token, text)

        # 2. Lookup-based: formy fleksyjne z surnamesForms (take 5 liter)
        name_lower = name_part.lower()
        name_lower_nodiac = _strip_diacritics(name_lower)
        prefix5 = name_lower_nodiac[:5]
        for base, forms in _SURNAMES_FORMS.items():
            base_nodiac = _strip_diacritics(base)
            if not base_nodiac.startswith(prefix5):
                continue
            for form in forms:
                form_re = re.compile(rf"\b{re.escape(form)}\b", re.IGNORECASE)
                text = form_re.sub(
                    lambda m, tid=token_id: m.group(0) if _TOKEN_RE.search(m.group(0)) else tid,
                    text,
                )

    return text


def _apply_initials(text: str, allocator: TokenAllocator) -> str:
    """Port z NameEngine.kt v1.12 INITIALS_REGEX: "K. Kowalski" → OSOBA.

    Warunek: nazwisko MUSI być w surnames_top1000.json (zerowe FP przy nieznanym nazwisku).
    Uruchamiany na tekście PO głównym NER, żeby nie duplikować już zamaskowanych.
    """
    from ner_blocklist import _NER_BLOCKLIST

    def _replace(m: re.Match) -> str:
        if _TOKEN_RE.search(m.group(0)):
            return m.group(0)
        surname = m.group(2)
        surname_lower = surname.lower()
        if surname_lower not in _SURNAMES_FORMS_FLAT:
            return m.group(0)
        if surname_lower in _NER_BLOCKLIST:
            return m.group(0)
        token_id = allocator.allocate("OSOBA", m.group(0), m.start(), m.end())
        return token_id if token_id else m.group(0)

    return _INITIALS_RE.sub(_replace, text)


def extract_ner_results(state: PipelineState, anon_map: dict) -> None:
    """Ekstrahuje wyniki NER z bieżącego state.text i zapisuje w state.ner_results.

    NIE modyfikuje state.text. Wywoływana PRZED apply_address_layer,
    żeby SpaCy widział pełne adresy jako kontekst dla rozpoznania imion/nazwisk.
    apply_ner_layer() wykryje wypełnione state.ner_results i użyje ich zamiast
    ponownie wywoływać process_ner().

    [WYS-1] Błąd NER ustawia state.ner_error = True — run_pipeline_new() blokuje
    odpowiedź (force_block). Fail-closed: lepiej zablokować niż puścić bez NER.
    """
    try:
        state.text = _fix_ocr_email(state.text)
        ner_reverse, ner_variants = process_ner(state.text, _spacy_ner_mod)
        state.ner_results = ner_reverse
        state.ner_variants = ner_variants
    except Exception as e:
        import logging as _logging
        _logging.getLogger("lynxmask.ner_adapter").error(
            f"[NER] extract_ner_results crash — blokowanie odpowiedzi: {e}"
        )
        state.ner_error = True


def apply_ner_layer(state: PipelineState, anon_map: dict) -> None:
    """Rejestruje tokeny OSOBA/FIRMA w state.allocator i zastępuje w tekście.

    Jeśli state.ner_results jest wypełnione przez extract_ner_results()
    (pre-ekstrakcja przed adresami), używa tych wyników.
    W przeciwnym razie wywołuje process_ner() bezpośrednio (fallback).

    Po podstawowym NER:
    - Propagacja OSOBA (Warstwa 3c): formy fleksyjne wykrytych nazwisk
    - Inicjały: "K. Kowalski" → OSOBA (jeśli nazwisko w słowniku)
    """
    # [WYS-1] Jeśli extract_ner_results() już zgłosiło błąd — nie próbuj ponownie
    if getattr(state, "ner_error", False):
        return

    try:
        if state.ner_results:
            ner_reverse = state.ner_results
        else:
            state.text = _fix_ocr_email(state.text)
            ner_reverse, ner_variants = process_ner(state.text, _spacy_ner_mod)
            state.ner_variants = ner_variants
    except Exception as e:
        import logging as _logging
        _logging.getLogger("lynxmask.ner_adapter").error(
            f"[NER] apply_ner_layer crash — blokowanie odpowiedzi: {e}"
        )
        state.ner_error = True
        return

    for token_id, value in ner_reverse.items():
        # Odrzuć fragmenty email (OCR rozbija "user@firma.pl" na dwa tokeny,
        # część "@firma.pl" trafia do SpaCy jako OSOBA — filtrujemy).
        if value.startswith("@"):
            continue
        start = state.text.find(value)
        if start >= 0:
            end = start + len(value)
            state.allocator.register(token_id, value, start, end)

    for token_id, value in sorted(
        ner_reverse.items(),
        key=lambda x: state.text.find(x[1]),
        reverse=True,
    ):
        if value.startswith("@"):
            continue
        state.text = state.text.replace(value, token_id)

    # ── Warstwa 3c: Propagacja wykrytych nazwisk ─────────────────────────────
    for token_id, value in ner_reverse.items():
        if not token_id.startswith("OSOBA"):
            continue
        if value.startswith("@"):
            continue
        state.text = _propagate_osoba(state.text, token_id, value)

    # ── Inicjały: "K. Kowalski" → OSOBA (port: INITIALS_REGEX) ──────────────
    state.text = _apply_initials(state.text, state.allocator)

    # ── Warianty SpaCy (port: FIX-NER-GLOBAL) ────────────────────────────────
    # ner_variants zawiera WSZYSTKIE formy wykryte przez SpaCy (odmiany fleksyjne,
    # wersje bez cudzysłowów, warianty FIRMA). Stary pipeline.py stosował je przez
    # FIX-NER-GLOBAL w Warstwie 6. Nowy pipeline wcześniej ustawiał state.ner_variants
    # ale nigdy nie używał do zamiany tekstu → regres: odmiany nie były maskowane.
    _variants = getattr(state, "ner_variants", None) or {}
    for _var_text, _tok_id in sorted(
        _variants.items(),
        key=lambda x: state.text.find(x[0]),
        reverse=True,
    ):
        if _var_text.startswith("@"):
            continue
        if _TOKEN_RE.search(_var_text):
            continue
        if _ADDR_PREFIX_RE.match(_var_text):
            continue
        if _tok_id.startswith("FIRMA") and _BARE_SUFFIX_RE.match(_var_text.strip()):
            continue
        _stripped = re.sub(r"[,\.;:!?\s]+$", "", _var_text).rstrip()
        _target = _stripped if _stripped else _var_text
        if not _target:
            continue
        if _stripped and _stripped != _var_text:
            state.text = state.text.replace(_var_text, _tok_id)
        state.text = state.text.replace(_target, _tok_id)

    # Oczyść "FIRMA_001 S.A." → "FIRMA_001" (forma prawna przyklejona do tokenu)
    state.text = _FIRMA_CLEANUP_RE.sub(r"\1", state.text)


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_ner_adapter() -> bool:
    import sys as _sys
    import unittest.mock as _mock

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))
            failed += 1

    print("=== test_ner_adapter ===\n")

    this_module = _sys.modules[__name__]

    # ── Test 1: jedna encja OSOBA ─────────────────────────────────────────────
    print("1. Jedna encja OSOBA:")
    mock_reverse = {"OSOBA_001": "Jan Kowalski"}
    mock_variants = {}

    with _mock.patch.object(this_module, "process_ner",
                            return_value=(mock_reverse, mock_variants)):
        state = PipelineState(
            text="Pozwany: Jan Kowalski zamieszkały w Warszawie.",
            allocator=TokenAllocator(),
        )
        apply_ner_layer(state, anon_map={})

    check("Jan Kowalski usunięty z tekstu",
          "Jan Kowalski" not in state.text,
          f"text={state.text!r}")
    check("OSOBA_001 w tekście",
          "OSOBA_001" in state.text,
          f"text={state.text!r}")
    check("OSOBA_001 w reverse_map",
          "OSOBA_001" in state.allocator.reverse_map,
          f"reverse_map={state.allocator.reverse_map}")
    check("ner_variants zapisane",
          state.ner_variants == mock_variants)

    # ── Test 2: dwie encje, różne typy ───────────────────────────────────────
    print("\n2. Dwie encje — OSOBA i FIRMA:")
    mock_reverse2 = {
        "OSOBA_001": "Anna Nowak",
        "FIRMA_001": "ABC Sp. z o.o.",
    }

    with _mock.patch.object(this_module, "process_ner",
                            return_value=(mock_reverse2, {})):
        state2 = PipelineState(
            text="Anna Nowak reprezentuje ABC Sp. z o.o. w sprawie.",
            allocator=TokenAllocator(),
        )
        apply_ner_layer(state2, anon_map={})

    check("Anna Nowak usunięta",     "Anna Nowak"     not in state2.text)
    check("ABC Sp. z o.o. usunięta", "ABC Sp. z o.o." not in state2.text)
    check("OSOBA_001 w reverse_map",
          "OSOBA_001" in state2.allocator.reverse_map)
    check("FIRMA_001 w reverse_map",
          "FIRMA_001" in state2.allocator.reverse_map)

    # ── Test 3: encja nie występuje w tekście — brak rejestracji ─────────────
    print("\n3. Encja nieobecna w tekście — brak rejestracji spanu:")
    mock_reverse3 = {"OSOBA_001": "Nie Ma Takiego"}

    with _mock.patch.object(this_module, "process_ner",
                            return_value=(mock_reverse3, {})):
        state3 = PipelineState(
            text="Tekst bez żadnych encji.",
            allocator=TokenAllocator(),
        )
        apply_ner_layer(state3, anon_map={})

    check("Tekst niezmieniony",
          state3.text == "Tekst bez żadnych encji.")
    rm3 = state3.allocator.reverse_map
    check("reverse_map pusty (find=-1 → nie rejestruje)",
          len(rm3) == 0, f"reverse_map={rm3}")

    # ── Test 4: propagacja OSOBA ──────────────────────────────────────────────
    print("\n4. Propagacja OSOBA — formy fleksyjne:")
    mock_reverse4 = {"OSOBA_001": "Jan Kowalski"}

    with _mock.patch.object(this_module, "process_ner",
                            return_value=(mock_reverse4, {})):
        state4 = PipelineState(
            text="Jan Kowalski mieszka tu. Pismo Kowalskiego odrzucono. Kowalskiemu odmówiono.",
            allocator=TokenAllocator(),
        )
        apply_ner_layer(state4, anon_map={})

    check("Jan Kowalski zamaskowany", "Jan Kowalski" not in state4.text, state4.text)
    check("Kowalskiego zamaskowane",  "Kowalskiego" not in state4.text, state4.text)
    check("Kowalskiemu zamaskowane",  "Kowalskiemu" not in state4.text, state4.text)

    # ── Test 5: inicjały K. Kowalski ─────────────────────────────────────────
    print("\n5. Inicjały — K. Kowalski → OSOBA:")
    with _mock.patch.object(this_module, "process_ner", return_value=({}, {})):
        state5 = PipelineState(
            text="Pismo podpisał K. Kowalski w dniu dzisiejszym.",
            allocator=TokenAllocator(),
        )
        apply_ner_layer(state5, anon_map={})

    check("K. Kowalski zamaskowany", "Kowalski" not in state5.text, state5.text)
    check("OSOBA token w tekście", "OSOBA_" in state5.text, state5.text)

    # ── Test 6: fix emaili OCR ────────────────────────────────────────────────
    print("\n6. Fix emaili OCR:")
    check("spacja po @", _fix_ocr_email("email: jan@ wp.pl") == "email: jan@wp.pl")
    check("spacja przed @", _fix_ocr_email("jan @wp.pl") == "jan@wp.pl")

    # ── Test 7: pusta odpowiedź NER ───────────────────────────────────────────
    print("\n7. Pusta odpowiedź NER:")
    with _mock.patch.object(this_module, "process_ner", return_value=({}, {})):
        state7 = PipelineState(text="Zwykły tekst.", allocator=TokenAllocator())
        original = state7.text
        apply_ner_layer(state7, anon_map={})

    check("Tekst niezmieniony", state7.text == original)
    check("reverse_map pusty", len(state7.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_ner_adapter() else 1)
