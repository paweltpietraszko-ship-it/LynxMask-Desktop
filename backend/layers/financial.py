"""
layers/financial.py  v1.0
Warstwa financial — IBAN, numery kont bankowych.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer_init import STRUCTURAL_PATTERNS, TOKEN_NUMER
from pipeline_core import PipelineState, TokenAllocator

# Explicit set — "PL" in pat.pattern złapałoby też NIP-PL i PLN (waluta)
_FINANCIAL_SOURCES: frozenset[str] = frozenset({
    r"(?<!\d)\d{24}(?!\d)",           # 24-cyfrowy numer konta/przesyłki
    r"\bPL\s?\d{2}(?:\s?\d{4}){6}\b", # IBAN PL (ze spacjami lub bez)
    r"\b\d{2}(?:\s\d{4}){5,6}\b",     # konto bez prefiksu PL (spacje)
    r"\b\d{2}-\d[\d\-]{20,28}\d\b",   # konto bez prefiksu PL (myślniki)
})

_FINANCIAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    (tok, pat) for tok, pat in STRUCTURAL_PATTERNS
    if pat.pattern in _FINANCIAL_SOURCES
]


def apply_financial_layer(state: PipelineState) -> None:
    """Stosuje wzorce IBAN i kont bankowych na state.text."""
    hits: list[tuple[int, int, str, str]] = []
    for token_type, pat in _FINANCIAL_PATTERNS:
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


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_financial_layer() -> bool:
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

    print("=== test_financial_layer ===\n")

    # ── Test podstawowy: dwa IBAN PL ─────────────────────────────────────────
    print("1. IBAN PL ze spacjami i bez spacjami:")
    state = PipelineState(
        text=(
            "konto: PL61 1090 1014 0000 0712 1981 2874, "
            "lub PL58325000032630362440455236"
        ),
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state)
    check("PL61 usunięty", "PL61" not in state.text,
          f"text={state.text!r}")
    check("PL58 usunięty", "PL58" not in state.text,
          f"text={state.text!r}")
    rm = state.allocator.reverse_map
    check("Dwa wpisy w reverse_map", len(rm) == 2,
          f"reverse_map={rm}")

    # ── Test konta bez prefiksu PL (spacje) ──────────────────────────────────
    print("\n2. Konto bez PL (spacje 2+4+4+4+4+4+4):")
    state2 = PipelineState(
        text="Przelew na: 61 1090 1014 0000 0712 1981 2874",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state2)
    check("Konto bez PL usunięte",
          "1090 1014 0000 0712 1981 2874" not in state2.text,
          f"text={state2.text!r}")

    # ── Test 24-cyfrowy numer ─────────────────────────────────────────────────
    print("\n3. 24-cyfrowy numer konta/przesyłki:")
    state3 = PipelineState(
        text="Nr: 612345678901234567890123",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state3)
    check("24-cyfrowy usunięty",
          "612345678901234567890123" not in state3.text,
          f"text={state3.text!r}")

    # ── Test deduplikacji — ten sam IBAN dwa razy ────────────────────────────
    print("\n4. Deduplication — ten sam IBAN dwa razy:")
    state4 = PipelineState(
        text="konto: PL58325000032630362440455236 i PL58325000032630362440455236",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state4)
    check("IBAN usunięty", "PL58" not in state4.text)
    rm4 = state4.allocator.reverse_map
    check("Jeden token (dedup)", len(rm4) == 1,
          f"reverse_map={rm4}")

    # ── Test brak dopasowań ───────────────────────────────────────────────────
    print("\n5. Brak dopasowań — tekst niezmieniony:")
    original = "Kwota: 1234 PLN, NIP: 855-019-31-23"
    state5 = PipelineState(text=original, allocator=TokenAllocator())
    apply_financial_layer(state5)
    check("Tekst niezmieniony", state5.text == original,
          f"text={state5.text!r}")
    check("reverse_map pusty", len(state5.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_financial_layer() else 1)
