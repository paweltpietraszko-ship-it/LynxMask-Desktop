"""
layers/amount.py  v1.0
Warstwa kwot i dat urodzenia — port z Kotlin StructuralEngine.kt.

Obsługuje:
  - Kwoty cyfrowe: "3 500,00 PLN", "78,69 EUR", "1234 zł" (TOKEN_KWOTA)
  - Data urodzenia kontekstowa: "data urodzenia: 21.05.1979",
    "Data ur. 17.09.1985", "Data urodzenía: DD.MM.RRRR" (TOKEN_NUMER)
  - Data DD.MM.YYYY strukturalna (rok 19xx/20xx) (TOKEN_NUMER)

Uruchamiana PO identity (która obsługuje "ur. DD.MM.RRRR")
i PRZED NER — kwota nie powinna trafiać do SpaCy jako encja.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer_init import STRUCTURAL_PATTERNS, TOKEN_KWOTA, TOKEN_NUMER
from pipeline_core import PipelineState, TokenAllocator

# ── Kwoty cyfrowe ─────────────────────────────────────────────────────────────
# Port z StructuralEngine.kt linia 370-373.
# (?!00\s) wyklucza "00 PLN" — artefakt OCR gdy kwota łamana przez linię.
# Separator tysięcy: spacja, przecinek lub kropka (PL: spacja+przecinek, EU: kropka+przecinek).
_AMOUNT_RE = re.compile(
    r"\b(?!00\s)\d{1,6}(?:[.,\s]\d{3})*(?:[.,]\d{1,2})?\s*"
    r"(?:zł|PLN|EUR|USD|GBP|CHF|DKK|NOK|CZK|HUF|RON)\b",
    re.IGNORECASE,
)
# [LYNX-AMOUNTS-NUMBERS] Waluta słowna po cyfrach („813 złotych”, „15 000 złotych”); pomijana, gdy przed liczbą
# stoi liczebnik/mnożnik (także dla _AMOUNT_RE: „tysięcy 813 zł”) — wtedy całą kwotę bierze verbal_amounts.
_AMOUNT_WORD_RE = re.compile(r"\b(?!00\s)\d{1,6}(?:[.,\s]\d{3})*(?:[.,]\d{1,2})?\s*z[łl]ot(?:ych|e|y)\b", re.IGNORECASE)
# [SILENT-PACK1] Jednostka po liczbie — to nie kwota („1234,56 mm”, „575,63 cm”).
_UNIT = r"(?:kg|g|mg|mm|cm|dm|m2|m²|m3|m³|m|km|ml|l|szt|godz|h|min|kWh|kW|MWh)\b"
# [LYNX-AMOUNTS-NUMBERS] Kwota bez waluty (Mobile A.9c): przecinek + 2 cyfry groszy („2 800,00”); nie procent, jednostka, wersja.
_AMOUNT_NOCUR_RE = re.compile(
    r"(?<![\d.,/\-])\d{1,3}(?:[  ]\d{3})*,\d{2}(?!\d|[.,]\d|/|-)"
    rf"(?!\s*%)(?!\s*{_UNIT})",
    re.IGNORECASE,
)
_VERSION_BEFORE_RE = re.compile(r"(?i)(?:\bwersj\w*|\bwer\.|\bv\.?)\s*$")
# [SILENT-PACK1] Kwota bez waluty i bez spacji tysięcy („1049,63”, „12.345,67”) — tylko ze słowem kwotowym w tym samym zdaniu.
_AMOUNT_NOCUR_CTX_RE = re.compile(
    r"(?<![\d.,/\-])(?:\d{4,6}|\d{1,3}(?:\.\d{3})+),\d{2}(?!\d|[.,]\d|/|-)"
    rf"(?!\s*%)(?!\s*{_UNIT})",
    re.IGNORECASE,
)
# [LYNX-AMOUNT-OCR-MULT] Liczba z mnożnikiem („15 tys. zł”, „2,5 mln zł”, „15 tysięcy” przy słowie kwotowym) oraz „O” zamiast zera
# w liczbie przy znaku pieniędzy („15 OOO zł”) — rozpoznanie bez zmiany tekstu (Przywróć zwraca fragment tak, jak dotarł do warstwy).
_CUR = r"(?:zł|PLN|EUR|USD|GBP|CHF|DKK|NOK|CZK|HUF|RON|z[łl]ot(?:ych|e|y))"
_MULT = r"(?:tys\.|tys\b|tysi[ąę]c\w*|mln\b\.?|milion\w*|mld\b\.?|miliard\w*)"
_MULT_CUR_RE = re.compile(rf"(?<![\d.,])\d{{1,4}}(?:[.,]\d{{1,2}})?\s*{_MULT}\s*{_CUR}(?!\w)", re.IGNORECASE)
_MULT_CTX_RE = re.compile(rf"(?<![\d.,])\d{{1,4}}(?:[.,]\d{{1,2}})?\s*{_MULT}(?!\s*{_UNIT})", re.IGNORECASE)
_O_NUM = r"(?<![\w.,])\d[\dOo]{0,5}(?:[.,  ][\dOo]{3})*(?:[.,][\dOo]{1,2})?"
_AMOUNT_O_RE = re.compile(rf"{_O_NUM}\s*{_CUR}(?!\w)", re.IGNORECASE)
_AMOUNT_O_CTX_RE = re.compile(rf"(?<![\w.,])\d[\dOo]{{0,2}}(?:[  .][\dOo]{{3}})+(?:[.,][\dOo]{{1,2}})?(?![\w.,]?\d)(?!\s*%)(?!\s*{_UNIT})",
                              re.IGNORECASE)
_AMOUNT_CTX_WORD_RE = re.compile(
    r"(?i)\b(?:kwot|zwrot|zapłat|należno|sald|brutto|netto|wartoś|cen[aiyęą]\b|wynagrodze|opłat|kar[aąyęe]\b|koszt|"
    r"złot|zł\b|pln\b|walut|grosz|zaliczk|odsetk|rat[aąyęe]\b|podatk|faktur|wpłat|wypłat|przelew)"
)


def _after_number_word(text: str, m: re.Match) -> bool:
    from verbal_amounts import _PL_NUMBER_WORDS
    prev = text[:m.start()].split()
    word = prev[-1].strip(",:;()").lower() if prev else ""
    return word != "i" and word in _PL_NUMBER_WORDS


def _not_amount_nocur(text: str, m: re.Match) -> bool:
    if _VERSION_BEFORE_RE.search(text[max(0, m.start() - 12):m.start()]):
        return True
    return any(a.start() <= m.start() < a.end() for a in _AMOUNT_RE.finditer(text, max(0, m.start() - 30), m.end() + 12))


def _not_amount_ctx(text: str, m: re.Match) -> bool:
    """[SILENT-PACK1] Brak słowa kwotowego w zdaniu (granica: „. ”, „! ”, „? ”, koniec wiersza) — to nie kwota (wersja, wynik pomiaru)."""
    start = max(text.rfind(c, 0, m.start()) for c in (". ", "! ", "? ", "\n")) + 1
    ends = [i for i in (text.find(c, m.end()) for c in (". ", "! ", "? ", "\n")) if i >= 0]
    return _not_amount_nocur(text, m) or not _AMOUNT_CTX_WORD_RE.search(text[start:min(ends, default=len(text))])


def _no_letter_o(m: re.Match) -> bool:
    """[LYNX-AMOUNT-OCR-MULT] Wzorce O/o tylko dla liczb z literą O (pozostałe kwoty biorą dotychczasowe wzorce)."""
    return not re.search(r"[Oo]", re.match(r"[\dOo.,  ]*", m.group(0)).group(0))


def _skip_o_cur(text: str, m: re.Match) -> bool:
    return _no_letter_o(m) or _after_number_word(text, m)


def _skip_o_ctx(text: str, m: re.Match) -> bool:
    return _no_letter_o(m) or _not_amount_ctx(text, m)


def _skip_mult_ctx(text: str, m: re.Match) -> bool:
    """Mnożnik z dalszym ciągiem liczby („44 tysięcy 813 złotych”) bierze w całości verbal_amounts."""
    from verbal_amounts import _PL_NUMBER_WORDS
    nxt = text[m.end():m.end() + 30].split()
    return bool(nxt) and (nxt[0][:1].isdigit() or nxt[0].strip(",.;:()").lower() in _PL_NUMBER_WORDS) \
        or _not_amount_ctx(text, m)

# ── Data urodzenia kontekstowa ─────────────────────────────────────────────────
# Port z StructuralEngine.kt linia 223.
# dat[aą] ur(odzenia)? + DD.MM.RRRR — obsługuje warianty:
#   "data urodzenia: 21.05.1979"    ← pełne słowo
#   "data ur. 21.05.1979"           ← skrót z kropką
#   "Data urodzenía: 17.09.1985"    ← OCR í zamiast i
#   "Data urodzenia:\n21.05.1979"   ← newline po dwukropku
_BIRTH_DATE_CTX_RE = re.compile(
    r"(?i)\bdat[aą]\s+ur(?:odzen[ií][^\s:–\-\d]{0,2})?\b\.?"
    r"[^\S\n]*[:–\-]?\n?[^\S\n]*\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}\b"
)

# ── Data DD.MM.YYYY strukturalna ──────────────────────────────────────────────
# Port z StructuralEngine.kt linia 228.
# Rok ograniczony do 19xx/20xx — blokuje FP: art. 10.12.98 (rok 98 bez prefiksu → skip).
_DATE_PL_RE = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])[.,/\-](?:0?[1-9]|1[0-2])[.,/\-](?:19|20)\d{2}\b"
)
# [LYNX-FIRMA-PROOF] Data pisma w nagłówku jest jawna (nie jest informacją o osobie — Reguły anonimizacji Portalu Orzeczeń
# pkt 3.2: czas jawny poza datą urodzenia): linia „Miejscowość, [dnia] DD.MM.RRRR [r.]” albo odwrotnie, rok z ostatnich 5 lat.
# Każda inna data (urodzenia, zdarzenia, w zdaniu, w tabeli bez miejscowości) zostaje zakryta — silnik nie odróżni jej od urodzenia.
_PLACE_WORDS_RE = re.compile(r"[A-ZĄĆĘŁŃÓŚŹŻ][\w-]+(?:[ \t-][A-ZĄĆĘŁŃÓŚŹŻ]?[\w-]+){0,3}")


def _doc_date(text: str, m: re.Match) -> bool:
    """True = data pisma (pominąć): w linii poza datą tylko miejscowość po jednej stronie przecinka, „dnia”, „r.”."""
    import datetime
    s, e = text.rfind("\n", 0, m.start()) + 1, text.find("\n", m.end())
    before, after = text[s:m.start()], text[m.end():e if e >= 0 else len(text)]
    if ":" in before + after or int(m.group(0)[-4:]) < datetime.date.today().year - 5:
        return False
    before = re.sub(r"(?i)\bdnia\s*$", "", before.strip()).strip()
    after = re.sub(r"(?i)^\s*(?:r\.|roku)?", "", after).strip()
    place = (before[:-1].strip() if before.endswith(",") and not after.strip(".") else
             after[1:].strip() if after.startswith(",") and not before else None)
    return bool(place) and _PLACE_WORDS_RE.fullmatch(place.rstrip(".")) is not None


# [LYNX-FORMATS-PACK2] Data ISO RRRR-MM-DD — ten sam zakres lat co DD.MM.RRRR („ur. 1989-01-05”); bez fragmentu „1989-01-05-001”.
_DATE_ISO_RE = re.compile(r"(?<![\d-])(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?!\d|-\d)")


def _apply_patterns(
    state: PipelineState,
    patterns: list[tuple],
) -> None:
    hits: list[tuple[int, int, str, str]] = []
    for token_type, pat, *skip in patterns:
        for m in pat.finditer(state.text):
            if skip and skip[0](state.text, m):
                continue
            hits.append((m.start(), m.end(), m.group(0), token_type))

    # [LYNX-AMOUNT-OCR-MULT] z nakładających się trafień wygrywa najdłuższe („15 OOO,50 zł”, nie same „50 zł”); przy równej długości
    # — wcześniejszy wzorzec z listy (sortowanie stabilne)
    chosen: list[tuple[int, int, str, str]] = []
    for h in sorted(hits, key=lambda x: x[1] - x[0], reverse=True):
        if not any(c[0] < h[1] and h[0] < c[1] for c in chosen):
            chosen.append(h)
    hits = sorted(chosen, key=lambda x: x[0], reverse=True)

    text = state.text
    for start, end, value, token_type in hits:
        if state.allocator.is_occupied(start, end):
            continue
        tid = state.allocator.allocate(token_type, value, start, end)
        if tid is None:
            continue
        text = text[:start] + tid + text[end:]

    state.text = text


def apply_amount_layer(state: PipelineState) -> None:
    """Maskuje kwoty cyfrowe i daty urodzenia (kontekstowe + strukturalne DD.MM.YYYY)."""
    _apply_patterns(state, [
        (TOKEN_KWOTA,  _MULT_CUR_RE, _after_number_word),  # [LYNX-AMOUNT-OCR-MULT] dłuższe przed krótszymi (ten sam start)
        (TOKEN_KWOTA,  _MULT_CTX_RE, _skip_mult_ctx),
        (TOKEN_KWOTA,  _AMOUNT_O_RE, _skip_o_cur),
        (TOKEN_KWOTA,  _AMOUNT_O_CTX_RE, _skip_o_ctx),
        (TOKEN_KWOTA,  _AMOUNT_RE, _after_number_word),
        (TOKEN_KWOTA,  _AMOUNT_WORD_RE, _after_number_word),
        (TOKEN_KWOTA,  _AMOUNT_NOCUR_RE, _not_amount_nocur),
        (TOKEN_KWOTA,  _AMOUNT_NOCUR_CTX_RE, _not_amount_ctx),
        (TOKEN_NUMER,  _BIRTH_DATE_CTX_RE),
        (TOKEN_NUMER,  _DATE_PL_RE, _doc_date),  # [LYNX-FIRMA-PROOF] data pisma jawna
        (TOKEN_NUMER,  _DATE_ISO_RE),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_amount_layer() -> bool:
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

    print("=== test_amount_layer ===\n")

    print("1. Kwoty cyfrowe:")
    state = PipelineState(text="Wynagrodzenie: 3 500,00 PLN, zaliczka 1200 EUR",
                          allocator=TokenAllocator())
    apply_amount_layer(state)
    check("3 500,00 PLN usunięte", "3 500,00 PLN" not in state.text, state.text)
    check("1200 EUR usunięte", "1200 EUR" not in state.text, state.text)
    check("KWOTA tokeny", any("KWOTA" in k for k in state.allocator.reverse_map))

    print("\n2. Data urodzenia kontekstowa:")
    for txt, label in [
        ("data urodzenia: 21.05.1979", "pełne słowo"),
        ("Data ur. 17.09.1985", "skrót"),
        ("Data urodzenía: 05.11.2001", "OCR í"),
        ("Data urodzenia:\n15.03.1990", "newline"),
    ]:
        state2 = PipelineState(text=txt, allocator=TokenAllocator())
        apply_amount_layer(state2)
        check(f"data urodzenia ({label}) zakryta",
              all(c not in state2.text for c in ["1979", "1985", "2001", "1990"]),
              state2.text)

    print("\n3. Data DD.MM.YYYY strukturalna:")
    state3 = PipelineState(text="Umowa z dnia 15.06.2024 roku.", allocator=TokenAllocator())
    apply_amount_layer(state3)
    check("15.06.2024 zakryta", "15.06.2024" not in state3.text, state3.text)

    print("\n4. Brak false positive — rok samodzielny:")
    state4 = PipelineState(text="Art. 22 ustawy z 2024 roku.", allocator=TokenAllocator())
    apply_amount_layer(state4)
    check("2024 (rok) niezmieniony", "2024" in state4.text, state4.text)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_amount_layer() else 1)
