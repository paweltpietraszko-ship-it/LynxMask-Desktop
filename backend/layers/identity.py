"""
layers/identity.py  v1.1
Warstwa identity — PESEL, NIP, REGON, dowód osobisty, paszport.
"""
from __future__ import annotations

import os
import re
import sys

# Pozwala uruchamiać plik bezpośrednio (python layers/identity.py)
# oraz jako moduł (python -m layers.identity) z katalogu projektu.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer_init import STRUCTURAL_PATTERNS
from pipeline_core import PipelineState, TokenAllocator

# Klucze do filtrowania STRUCTURAL_PATTERNS — muszą dokładnie pasować do pat.pattern
_IDENTITY_SOURCES: frozenset[str] = frozenset({
    r"(?<!\d)\d{11}(?!\d)",                                    # PESEL
    r"(?<!\d)\d{14}(?!\d)",                                    # REGON 14
    r"(?<!\d)\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}(?!\d)",  # NIP format 3-3-2-2 (lookup)
    r"(?<!\d)\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3}(?!\d)",  # NIP format 3-2-2-3 [BUG-NIP-LEAK]
    r"\bPL\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b",          # NIP z PL
    r"(?<!\d)\d{9}(?!\d)",                                     # REGON 9
    r"(?<![A-Za-z])[A-Z]{3}\s?\d{6}(?!\d)",                   # Dowód osobisty
    r"(?<![A-Z])\b[A-Z]{2}\d{7}\b",                           # Paszport
    r"\bur\.\s*\d{1,2}\.\d{1,2}\.\d{4}(?:\s+w\s+[A-ZŁŚŹĆŃ][\w\-]{1,30})?",  # ur. DD.MM.RRRR
})

# Wzorzec NIP z rozszerzonym separatorem: OCR czasem zastępuje myślnik kropką
# (np. "766-444-75.06"). STRUCTURAL_PATTERNS ma stary [-\s]? — podmieniamy lokalnie.
_NIP_PATTERN_ORIG = r"(?<!\d)\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}(?!\d)"
_NIP_RE_OCR = re.compile(r"(?<!\d)\d{3}[-\s.]?\d{3}[-\s.]?\d{2}[-\s.]?\d{2}(?!\d)")

_IDENTITY_PATTERNS: list[tuple[str, re.Pattern]] = [
    (tok, _NIP_RE_OCR if pat.pattern == _NIP_PATTERN_ORIG else pat)
    for tok, pat in STRUCTURAL_PATTERNS
    if pat.pattern in _IDENTITY_SOURCES
]


def apply_identity_layer(state: PipelineState) -> None:
    """Stosuje wzorce identity (PESEL/NIP/REGON/dowód/paszport) na state.text."""
    hits: list[tuple[int, int, str, str]] = []
    for token_type, pat in _IDENTITY_PATTERNS:
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

def test_identity_layer() -> bool:
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

    print("=== test_identity_layer ===\n")

    print("1. PESEL + dowód + paszport:")
    state = PipelineState(
        text="PESEL: 85010112345, dowód: AOK171495, paszport: ZX1234567",
        allocator=TokenAllocator(),
    )
    apply_identity_layer(state)
    check("PESEL usunięty",    "85010112345" not in state.text,
          f"text={state.text!r}")
    check("Dowód usunięty",    "AOK171495"   not in state.text,
          f"text={state.text!r}")
    check("Paszport usunięty", "ZX1234567"   not in state.text,
          f"text={state.text!r}")
    check("3 wpisy w reverse_map", len(state.allocator.reverse_map) == 3,
          f"reverse_map={state.allocator.reverse_map}")

    print("\n2. NIP + REGON 9 + REGON 14:")
    state2 = PipelineState(
        text="NIP: 855-019-31-23, REGON: 123456789, REGON14: 12345678901234",
        allocator=TokenAllocator(),
    )
    apply_identity_layer(state2)
    check("NIP usunięty",      "855-019-31-23" not in state2.text)
    check("REGON 9 usunięty",  "123456789"      not in state2.text,
          f"text={state2.text!r}")
    check("REGON 14 usunięty", "12345678901234" not in state2.text)

    print("\n3. Ochrona spanu — ten sam PESEL dwa razy:")
    state3 = PipelineState(
        text="85010112345 i znowu 85010112345",
        allocator=TokenAllocator(),
    )
    apply_identity_layer(state3)
    check("Oba PESEL zastąpione", "85010112345" not in state3.text)
    rm3 = state3.allocator.reverse_map
    check("Jeden token (deduplication)", len(rm3) == 1,
          f"reverse_map={rm3}")
    check("Token poprawny", list(rm3.values()) == ["85010112345"],
          f"values={list(rm3.values())}")

    print("\n4. Brak dopasowań — tekst niezmieniony:")
    original = "Zwykły tekst bez PII: data 2024-01-15."
    state4 = PipelineState(text=original, allocator=TokenAllocator())
    apply_identity_layer(state4)
    check("Tekst niezmieniony", state4.text == original,
          f"text={state4.text!r}")
    check("reverse_map pusty", len(state4.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if test_identity_layer() else 1)
