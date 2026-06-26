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


def _apply_patterns(
    state: PipelineState,
    patterns: list[tuple[str, re.Pattern]],
) -> None:
    hits: list[tuple[int, int, str, str]] = []
    for token_type, pat in patterns:
        for m in pat.finditer(state.text):
            hits.append((m.start(), m.end(), m.group(0), token_type))

    hits.sort(key=lambda x: x[0], reverse=True)

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
        (TOKEN_KWOTA,  _AMOUNT_RE),
        (TOKEN_NUMER,  _BIRTH_DATE_CTX_RE),
        (TOKEN_NUMER,  _DATE_PL_RE),
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
