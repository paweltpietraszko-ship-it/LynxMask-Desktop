"""
layers/address.py  v1.7
Warstwa address — adresy z kodem pocztowym, kody pocztowe jako kotwice.
v1.7: [OBS-ADRES-DOUBLE-TOKEN] Wszystkie trzy fazy zbierają hity na tym samym
  tekście wejściowym, potem jeden wspólny _apply_hits. Wcześniej każda faza
  modyfikowała state.text niezależnie — po fazie 1 offsety w alokatorze
  nie odpowiadały pozycjom w zmienionym tekście → is_occupied nie wykrywał
  pokrywających się dopasowań z faz 2a/2b.
v1.6: [BUG-ADDR-FP] Faza 2a — gdy brak kodu pocztowego w dopasowaniu,
  wymagamy że przynajmniej jedno słowo z dopasowania pasuje do bazy SIMC.
  Wcześniej wzorce bez kodu pocztowego były akceptowane bez walidacji miasta
  co powodowało FP (precision 68.3%). Faza 1 i 2b bez zmian.
v1.5: _CITY_FORMS (frozenset z cities_forms.json — baza SIMC GUS, 179k form)
  + _match_city(text, pos) zastępuje wzorzec regex dla nazwy miasta.
  Miasto musi być w bazie SIMC — redukuje FP z ogólnego wzorca [A-Z][a-z]+.
  Faza 2b przebudowana na _POSTAL_ANCHOR_RE + _match_city zamiast
  _ADDR_STRUCTURAL_POSTAL z anonymizer_init.
v1.4: _fix_city() — wzorce _ADDR_STRUCTURAL_FULL recompilowane z dokładnym
  fragmentem miasta zamiast chciwego [\\w ,]{2,40}.
v1.3: faza 2 split na sub-fazy 2a/2b.
v1.2: miasto w _ADDR_RE dopasowuje tylko litery.
v1.1: dwie fazy — _ADDR_RE (pełny adres) przed _ADDR_STRUCTURAL (sam kod).
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer_init import STRUCTURAL_PATTERNS, TOKEN_ADRES
from pipeline_core import PipelineState, TokenAllocator

# ---------------------------------------------------------------------------
# Baza miast SIMC (GUS) — formy morfologiczne wygenerowane przez Morfeusz2.
# ---------------------------------------------------------------------------
_CITIES_PATH = pathlib.Path(__file__).parent.parent / 'cities_forms.json'
try:
    with open(_CITIES_PATH, encoding='utf-8') as _f:
        _CITY_FORMS: frozenset[str] = frozenset(json.load(_f))
except FileNotFoundError:
    _CITY_FORMS = frozenset()

# Jeden człon nazwy miejscowości (obsługuje łączniki: Bielsko-Biała, Zielona-Góra)
_CITY_WORD_RE = re.compile(
    r'[A-ZŁŚŹĆŃĄĘÓŻ][a-złśźćńąęóż]+(?:-[A-ZŁŚŹĆŃĄĘÓŻ][a-złśźćńąęóż]+)*'
)


def _match_city(text: str, pos: int) -> tuple[int, str] | None:
    """Po pozycji pos szuka nazwy miasta w _CITY_FORMS.

    Pomija wiodące spacje, tabulatory, przecinki i znaki nowej linii.
    Próbuje najpierw dwa słowa (np. 'Nowa Sól', 'Jelenia Góra'),
    potem jedno (np. 'Kraków', 'Wrocław').
    Zwraca (end_pos, nazwa) lub None jeśli nie znaleziono.
    """
    while pos < len(text) and text[pos] in ' \t,\n\r':
        pos += 1
    m1 = _CITY_WORD_RE.match(text, pos)
    if not m1:
        return None
    word1 = m1.group(0)
    pos2 = m1.end()
    # Próbuj dwa słowa
    if pos2 < len(text) and text[pos2] == ' ':
        m2 = _CITY_WORD_RE.match(text, pos2 + 1)
        if m2:
            two = word1 + ' ' + m2.group(0)
            if two in _CITY_FORMS:
                return (m2.end(), two)
    # Próbuj jedno słowo
    if word1 in _CITY_FORMS:
        return (pos2, word1)
    return None


# ---------------------------------------------------------------------------
# Wzorce adresów
# ---------------------------------------------------------------------------

# Faza 1: pełne adresy z prefiksem ul./al./etc.
# Zatrzymuje się na kodzie pocztowym — miasto dopisuje _match_city (SIMC lookup).
_ADDR_RE = re.compile(
    r"(?:ul|al|pl|os|aleja|ulica|plac|osiedle|skwer|rondo|bulwar)"
    r"\.?[ \t]+[A-ZŁŚŹĆŃ]"
    r"[\wóżźćńłśąę\- ]{1,40}"
    r"[ \t]+\d+(?:[a-zA-Z])?(?:/\d+(?:[a-zA-Z])?)?"
    r"(?:[,\s]+\d{2}-\d{3})?",
    re.IGNORECASE | re.UNICODE,
)

_ADDR_STRUCTURAL: list[tuple[str, re.Pattern]] = [
    (tok, pat) for tok, pat in STRUCTURAL_PATTERNS if tok == TOKEN_ADRES
]

# Dokładny fragment miasta — zastępuje chciwy \w[\w ,]{2,40}\b z anonymizer_init.
_CITY_NEW = r"[A-ZŁŚŹĆŃĄĘÓŻ][a-złśźćńąęóż]+(?: [A-ZŁŚŹĆŃĄĘÓŻ][a-złśźćńąęóż]+)*"
_CITY_GREEDY = (r"\w[\w ,]{2,40}\b", r"\w[\w ]{2,40}\b")


def _fix_city(pat: re.Pattern) -> re.Pattern:
    s = pat.pattern
    for greedy in _CITY_GREEDY:
        if greedy in s:
            return re.compile(s.replace(greedy, _CITY_NEW), pat.flags)
    return pat


# Faza 2a: pełne wzorce strukturalne (OCR-linebreak, ulica bez prefiksu).
# _match_city waliduje/przycina miasto po kodzie pocztowym w każdym dopasowaniu.
_ADDR_STRUCTURAL_FULL: list[tuple[str, re.Pattern]] = [
    (tok, _fix_city(pat)) for tok, pat in _ADDR_STRUCTURAL
    if not pat.pattern.startswith(r"\b\d")
]

# Faza 2b: kotwica kodu pocztowego — _match_city dostarcza nazwę miasta z SIMC.
# Zastępuje _ADDR_STRUCTURAL_POSTAL z anonymizer_init (pewniejsze od regex).
_POSTAL_ANCHOR_RE = re.compile(r'\b\d{2}-\d{3}\b')

# Pomocnicze: czy dopasowanie kończy się kodem pocztowym?
_POSTAL_END_RE = re.compile(r'\d{2}-\d{3}$')
# Pomocnicze: ostatni kod pocztowy wewnątrz dopasowania strukturalnego.
_POSTAL_IN_MATCH_RE = re.compile(r'\d{2}-\d{3}')


def _apply_hits(
    text: str,
    hits: list[tuple[int, int, str, str]],
    allocator,
) -> str:
    hits.sort(key=lambda x: x[0], reverse=True)
    for start, end, value, token_type in hits:
        if allocator.is_occupied(start, end):
            continue
        tid = allocator.allocate(token_type, value, start, end)
        if tid is None:
            continue
        text = text[:start] + tid + text[end:]
    return text


def apply_address_layer(state: PipelineState) -> None:
    """Stosuje wzorce adresów i kodów pocztowych na state.text.

    [OBS-ADRES-DOUBLE-TOKEN] Wszystkie fazy zbierają hity na tym samym tekście,
    potem jeden _apply_hits. Wcześniej każda faza modyfikowała state.text — offsety
    allokatora nie zgadzały się z pozycjami w zmienionym tekście.

    Faza 1: _ADDR_RE + _match_city — adresy z prefiksem ul./al./os.
    Faza 2a: _ADDR_STRUCTURAL_FULL + _match_city — wzorce bez prefiksu (OCR).
    Faza 2b: _POSTAL_ANCHOR_RE + _match_city — sam kod pocztowy + miasto (SIMC).
    """
    text = state.text
    all_hits: list[tuple[int, int, str, str]] = []

    # Faza 1 — pełne adresy z prefiksem ul./al./os./pl./osiedle/…
    for m in _ADDR_RE.finditer(text):
        end = m.end()
        if _POSTAL_END_RE.search(m.group(0)):
            city_r = _match_city(text, end)
            if city_r:
                end = city_r[0]
        all_hits.append((m.start(), end, text[m.start():end], "ADRES"))

    # Faza 2a — pełne wzorce strukturalne (OCR-linebreak, ulica bez prefiksu).
    for tok, pat in _ADDR_STRUCTURAL_FULL:
        for m in pat.finditer(text):
            start, end = m.start(), m.end()
            postals = list(_POSTAL_IN_MATCH_RE.finditer(m.group(0)))
            if postals:
                after_postal = start + postals[-1].end()
                city_r = _match_city(text, after_postal)
                if city_r:
                    end = city_r[0]
                else:
                    end = after_postal
            else:
                # [BUG-ADDR-FP] Brak kodu pocztowego — wymagaj SIMC na końcu dopasowania.
                match_text = m.group(0)
                last_city: tuple[int, str] | None = None
                for cm in _CITY_WORD_RE.finditer(match_text):
                    candidate_pos = start + cm.start()
                    cr = _match_city(text, candidate_pos)
                    if cr and cr[0] <= end + 5:
                        last_city = cr
                if last_city is None:
                    continue
            all_hits.append((start, end, text[start:end], tok))

    # Faza 2b — kod pocztowy + miasto z SIMC.
    for m in _POSTAL_ANCHOR_RE.finditer(text):
        city_r = _match_city(text, m.end())
        if city_r:
            city_end, _ = city_r
            all_hits.append((m.start(), city_end, text[m.start():city_end], "ADRES"))

    state.text = _apply_hits(text, all_hits, state.allocator)


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_address_layer() -> bool:
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

    print("=== test_address_layer ===\n")

    # ── Test podstawowy: dwa adresy z ul./al. i kodem pocztowym ─────────────
    print("1. Dwa adresy z prefiksem i kodem pocztowym:")
    state = PipelineState(
        text=(
            "zamieszkały: ul. Marszałkowska 12/4, 00-001 Warszawa, "
            "korespondencja: al. Jana Pawła II 15, 31-001 Kraków"
        ),
        allocator=TokenAllocator(),
    )
    apply_address_layer(state)
    check("00-001 Warszawa usunięty", "00-001 Warszawa" not in state.text,
          f"text={state.text!r}")
    check("31-001 Kraków usunięty",   "31-001 Kraków"   not in state.text,
          f"text={state.text!r}")
    rm = state.allocator.reverse_map
    check("ADRES_ token istnieje",
          any(k.startswith("ADRES_") for k in rm),
          f"keys={list(rm)}")

    # ── Test samego kodu pocztowego + miasto ─────────────────────────────────
    print("\n2. Sam kod pocztowy + miasto (bez ulicy):")
    state2 = PipelineState(
        text="Nadawca: 80-286 Gdańsk",
        allocator=TokenAllocator(),
    )
    apply_address_layer(state2)
    check("80-286 Gdańsk usunięty", "80-286 Gdańsk" not in state2.text,
          f"text={state2.text!r}")

    # ── Test wzorca ul. bez kodu pocztowego ──────────────────────────────────
    print("\n3. Adres z ul. bez kodu pocztowego:")
    state3 = PipelineState(
        text="mieszka: ul. Kwiatowa 5a",
        allocator=TokenAllocator(),
    )
    apply_address_layer(state3)
    check("ul. Kwiatowa 5a usunięty", "Kwiatowa 5a" not in state3.text,
          f"text={state3.text!r}")

    # ── Test deduplikacji — ten sam adres dwa razy ───────────────────────────
    print("\n4. Deduplication — ten sam adres dwa razy:")
    state4 = PipelineState(
        text="Adres: 00-001 Warszawa (poprzednio 00-001 Warszawa)",
        allocator=TokenAllocator(),
    )
    apply_address_layer(state4)
    check("Adres usunięty", "00-001 Warszawa" not in state4.text)
    rm4 = state4.allocator.reverse_map
    check("Jeden token ADRES (dedup)", len(rm4) == 1,
          f"reverse_map={rm4}")

    # ── Test brak dopasowań ───────────────────────────────────────────────────
    print("\n5. Brak dopasowań — tekst niezmieniony:")
    original = "Data: 2024-01-15, kwota: 1234 PLN."
    state5 = PipelineState(text=original, allocator=TokenAllocator())
    apply_address_layer(state5)
    check("Tekst niezmieniony", state5.text == original,
          f"text={state5.text!r}")
    check("reverse_map pusty", len(state5.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_address_layer() else 1)
