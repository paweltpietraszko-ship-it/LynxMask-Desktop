"""
layers/address.py  v1.9
Warstwa address — adresy z kodem pocztowym, kody pocztowe jako kotwice.
v1.9: [BUG-ADDR-OCR-DIACRITICS] OCR często gubi diakrytyki w nazwach miast
  ("Krakow" zamiast "Kraków"). _match_city teraz sprawdza też ASCII-folded formę
  z _CITY_FORMS_ASCII. Wersja kanoniczna = oryginalna forma z SIMC.
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
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer_init import STRUCTURAL_PATTERNS, TOKEN_ADRES
from pipeline_core import PipelineState, TokenAllocator

# ---------------------------------------------------------------------------
# Baza miast SIMC (GUS) — formy morfologiczne wygenerowane przez Morfeusz2.
# ---------------------------------------------------------------------------
_CITIES_PATH = pathlib.Path(__file__).parent.parent / 'cities_forms.json'
_L_STROKE = str.maketrans('łŁ', 'lL')
def _ascii_fold(s: str) -> str:
    # [LYNX-OCR-GATE-COMPARE E2] ł/Ł nie rozkłada się w NFD — bez tego „Bielsko-Biała” → „Bielsko-Biaa”, a OCR czyta „Biala”
    return unicodedata.normalize('NFD', s.translate(_L_STROKE)).encode('ascii', 'ignore').decode('ascii')


try:
    with open(_CITIES_PATH, encoding='utf-8') as _f:
        _raw_city_list: list[str] = json.load(_f)
    _CITY_FORMS: frozenset[str] = frozenset(_raw_city_list)
    # [BUG-ADDR-OCR-DIACRITICS] OCR gubi diakrytyki — mapujemy ascii → oryginalna forma SIMC
    _CITY_FORMS_ASCII: dict[str, str] = {
        _ascii_fold(f): f for f in _raw_city_list
    }
except FileNotFoundError:
    _CITY_FORMS = frozenset()
    _CITY_FORMS_ASCII = {}

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
            # [BUG-ADDR-OCR-DIACRITICS] OCR bez diakrytyków
            two_ascii = _ascii_fold(two)
            if two_ascii in _CITY_FORMS_ASCII:
                return (m2.end(), _CITY_FORMS_ASCII[two_ascii])
    # Próbuj jedno słowo
    if word1 in _CITY_FORMS:
        return (pos2, word1)
    # [BUG-ADDR-OCR-DIACRITICS] OCR bez diakrytyków
    word1_ascii = _ascii_fold(word1)
    if word1_ascii in _CITY_FORMS_ASCII:
        return (pos2, _CITY_FORMS_ASCII[word1_ascii])
    return None


# ---------------------------------------------------------------------------
# Wzorce adresów
# ---------------------------------------------------------------------------

# [LYNX-ADDR-REVERSED] Kod pocztowy NN-NNN jako całość (bez \b na końcu — „31-001”
# w „II 15 31-001” kończy się cyfrą; sam kod nie może być cięty w połowie).
_POSTAL_RE = re.compile(r'\d{2}-\d{3}(?!\d)')
# [LYNX-ADDR-REVERSED] Ulica bez prefiksu „ul.”: 1–2 członów + numer ze ściężkiem
# („Twarda 18”, „Powązek 3”). Tylko w Fazie 4, zaraz po „kod + miasto”.
_STREET_BARE_RE = re.compile(
    r'[A-ZŁŚŹĆŃĄĘÓŻ][a-złśźćńąęóż]+(?:-[A-ZŁŚŹĆŃĄĘÓŻ][a-złśźćńąęóż]+)?'
    r'(?: [A-ZŁŚŹĆŃĄĘÓŻ][a-złśźćńąęóż]+)?[ ,]\d+[a-zA-Z]?(?:/\d+)?(?![\w/-])'
)


def _skip_sep(text: str, pos: int) -> int:
    """[LYNX-ADDR-REVERSED] Przeskocz spacje/przecinki; None gdy brak separatora."""
    end = pos
    while end < len(text) and text[end] in ' \t,\n\r':
        end += 1
    return end if end > pos else None


def _find_postal_before(text: str, pos: int):
    """[LYNX-ADDR-REVERSED] Kod NN-NNN kończący się tuż przed pozycją pos.

    Dopuszcza między kodem a pozycją wyłącznie przecinki/spacje; zwraca ostatni
    taki kod (albo None)."""
    last = None
    for m in _POSTAL_RE.finditer(text[:pos]):
        if re.fullmatch(r'[ \t,\n\r]*', text[m.end():pos]):
            last = m
    return last


def _street_end_after(text: str, pos: int) -> int | None:
    """[LYNX-ADDR-REVERSED] Koniec ulicy z numerem, która zaczyna się tuż za pozycją pos."""
    p = _skip_sep(text, pos)
    if p is None:
        return None
    m = _STREET_BARE_RE.match(text, p)
    return m.end() if m else None


def _city_after(text: str, pos: int):
    """[LYNX-ADDR-REVERSED] Miasto SIMC tuż za pozycją pos (przecinek/spacje) albo None."""
    p = _skip_sep(text, pos)
    if p is None:
        return None
    return _match_city(text, p)


def _reversed_addr_hit(text: str, s: int, e: int) -> tuple[int, int] | None:
    """[LYNX-ADDR-REVERSED] Rozszerzenie hitu (s,e) o bezpośrednio sąsiadujące elementy.

    Polityka OWNERA: miasto jest częścią adresu tylko gdy bezpośrednio sąsiaduje
    (przecinek/spacja) z rozpoznaną ulicą z numerem albo z kodem pocztowym;
    samo miasto pozostaje jawne. Zwraca nowy span albo None (bez zmian).
    - przed hitem kod (+miasto po tym kodzie): „Opole, 45-407, ul. …”;
    - za hitem miasto SIMC: „ul. Polna 5, Radom”, „Warszawa, ul. …, 00-001”;
      jeśli to miasto stoi zaraz po kodzie — rozszerzamy też wstecz do tego kodu;
    - za hitem ulica bez prefiksu („Twarda 18”), tylko gdy hit = „kod + miasto”
      i miasto potwierdza bazę SIMC (Faza 2b).
    """
    pm = _find_postal_before(text, s)
    if pm is not None:
        city_r = _city_after(text, pm.end())
        return (pm.start(), max(e, city_r[0]) if city_r else e)
    city_r = _city_after(text, e)
    if city_r:
        base_end = city_r[0]
        inner = _find_postal_before(text, city_r[1] - len(city_r[0]))
        if inner is not None:
            return (inner.start(), base_end)
        return (s, base_end)
    if _POSTAL_RE.match(text, s):
        mid = _match_city(text, e)
        if mid and mid[1] == e:
            se = _street_end_after(text, mid[0])
            if se:
                return (s, se)
    return None


def _untruncated_postal_end(text: str, start: int, end: int) -> int:
    """[LYNX-ADDR-REVERSED] Jeśli hit kończy się uciętym kodem NN-NNN (przyklejona
    reszta \\d{1,3}, np. „… 15 31” z „31-001”) — zwróć koniec pełnego kodu."""
    m = re.match(r'\d-(\d{1,3})(\d{1,3})(?!\d)', text[end - 2:])
    if m and '-' not in text[start:end]:
        return end + m.end() - 2
    return end


def _extend_reversed_hits(text: str, all_hits: list) -> None:
    """[LYNX-ADDR-REVERSED] Faza 3: przygotuj hity faz 1–2b przed wspólnym _apply_hits.

    Naprawia ucięte kody pocztowe i rozszerza hity o bezpośrednio sąsiadujące
    miasto/kod/ulicę bez prefiksu. Zmiany nanosimy od prawej strony tekstu, więc
    rozszerzenia lewe nie przesuwają już przetworzonych right-hitów; na końcu
    usuwamy hity wewnętrznie sprzeczne (token w tokenie), a _apply_hits rozwiązuje
    resztę nakłań przez wybór największego spanu.
    """
    order = sorted(range(len(all_hits)), key=lambda i: all_hits[i][0], reverse=True)
    for i in order:
        start, end, value, token_type = all_hits[i]
        end = _untruncated_postal_end(text, start, end)
        ext = _reversed_addr_hit(text, start, end)
        if ext:
            start, end = ext
        all_hits[i] = (start, end, text[start:end], token_type)
    kept: list[tuple[int, int, str, str]] = []
    for start, end, value, token_type in all_hits:
        if any(a < end and start < b and (start, end) != (a, b) for a, b, _, _ in kept):
            continue
        kept.append((start, end, value, token_type))
    all_hits[:] = kept


# Faza 1: pełne adresy z prefiksem ul./al./etc.
# Zatrzymuje się na kodzie pocztowym — miasto dopisuje _match_city (SIMC lookup).
_ADDR_RE = re.compile(
    r"(?<!\w)(?:ul|al|pl|os|aleja|ulica|plac|osiedle|skwer|rondo|bulwar)"  # [LYNX-MAP-FIDELITY] nie „Szpit|al X 5”
    r"\.?[ \t]+"
    r"(?:\d{1,2}[ \t]+)?"                                  # [LYNX-ADDR-EMAIL-LEAKS] L3: „3 Maja”, „11 Listopada”
    r"(?:[A-ZŁŚŹĆŃ][\wóżźćńłśąę]{0,3}\.[ \t]+)?"           # L2: jeden skrót z kropką („Św.”, „Gen.”, „Ks.”)
    r"[A-ZŁŚŹĆŃ]"
    r"[\wóżźćńłśąę\- ]{1,40}"
    r"[ \t]+[lIO]?\d+(?:[a-zA-Z])?(?:/[lIO]?\d+(?:[a-zA-Z])?)?"  # L1: litera OCR przed cyfrą („l2/8”)
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
    # [BUG-ADDR-STREET-LOST] Alokuj od największego spanu — większy hit wygrywa
    # gdy nakładają się (np. faza1: ul.+kod+miasto vs faza2b: sam kod+miasto).
    # Podmianę tekstu wykonuj osobno od prawej, żeby pozycje pozostały spójne.
    hits.sort(key=lambda x: (-(x[1] - x[0]), -x[0]))
    valid: list[tuple[int, int, str]] = []
    for start, end, value, token_type in hits:
        if allocator.is_occupied(start, end):
            continue
        tid = allocator.allocate(token_type, value, start, end)
        if tid is None:
            continue
        valid.append((start, end, tid))
    valid.sort(key=lambda x: x[0], reverse=True)
    for start, end, tid in valid:
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
    Faza 3 [LYNX-ADDR-REVERSED]: _extend_reversed_hits — miasto/kod/ulica bezpośrednio
      sąsiadujące z hitem nie zostają jawne; ucięty kod NN-NNN nigdy nie jest cięty.
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

    # Faza 3 [LYNX-ADDR-REVERSED] — miasto/kod/ulica tuż przy adresie nie zostają jawne.
    _extend_reversed_hits(text, all_hits)

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
