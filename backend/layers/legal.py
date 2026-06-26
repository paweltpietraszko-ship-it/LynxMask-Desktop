"""
layers/legal.py  v1.1
Warstwa legal — sygnatury sądowe, komornicze, administracyjne, KW.
v1.1: Dodano KRS i sygnaturę ukośnikową (brakujące z STRUCTURAL_PATTERNS).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_core import PipelineState, TokenAllocator

# Wzorce lustrzane z pipeline.py (_CASE_SIG_RE, _ADMIN_SIG_RE).
# Nie importujemy pipeline.py bezpośrednio — jego import ładuje ner_layer,
# verbal_amounts i ner_blocklist ze skutkami ubocznymi.
_CASE_SIG_RE = re.compile(
    r"\b(?:"
    r"(?:I{1,3}V?|VI{0,3}|IX|XI{0,2}|XII)\s+[A-Z][A-Za-z]{0,4}"
    r"|Km|Kmp|Ko|Kms|GC|C|K|W"
    r")\s+\d{1,6}/\d{2,4}\b",
    re.UNICODE,
)

_ADMIN_SIG_RE = re.compile(
    r"\b[A-Z]{2}\.\d{6}\.\d{4}\b",
    re.UNICODE,
)

# Numer księgi wieczystej — format XX9X/NNNNNNN/N (np. KA1K/00075119/1)
_KW_RE = re.compile(
    r"\b[A-Z]{2}\d[A-Z]/\d+/\d+\b",
    re.UNICODE,
)

# KRS — 10 cyfr z prefiksem
_KRS_RE = re.compile(r"\bKRS\s*\d{10}\b", re.IGNORECASE)

# Sygnatura ukośnikowa — co najmniej 3 segmenty, przynajmniej jedna litera.
# Pasuje: 15/2Pm/P/JAG3/2024/EO, I/ACa/123/2024
# Nie pasuje: 1/2/2024 (same cyfry = data), Sokola 4/6 (2 segmenty)
_SLASH_SIG_RE = re.compile(
    r"(?<!\w)"
    r"(?=[0-9A-Za-z/]*[A-Za-z])"
    r"[A-Z0-9]{1,8}"
    r"(?:/[A-Z0-9]{1,8}){2,}"
    r"(?!\w)",
    re.IGNORECASE,
)

_LEGAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("NUMER", _CASE_SIG_RE),
    ("NUMER", _ADMIN_SIG_RE),
    ("NUMER", _KW_RE),
    ("NUMER", _KRS_RE),
    ("NUMER", _SLASH_SIG_RE),
]


def apply_legal_layer(state: PipelineState) -> None:
    """Stosuje wzorce sygnatur i KW na state.text."""
    hits: list[tuple[int, int, str, str]] = []
    for token_type, pat in _LEGAL_PATTERNS:
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

def test_legal_layer() -> bool:
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

    print("=== test_legal_layer ===\n")

    # ── Test podstawowy: sygnatura sądowa + komornicza + admin + KW ──────────
    print("1. Sądowa + komornicza + administracyjna + KW:")
    state = PipelineState(
        text="sygn. I C 123/2024, Km 10478/2024, OW.085394.2025, KW: KA1K/00075119/1",
        allocator=TokenAllocator(),
    )
    apply_legal_layer(state)
    check("I C 123/2024 usunięta",   "I C 123/2024"   not in state.text,
          f"text={state.text!r}")
    check("Km 10478/2024 usunięta",  "Km 10478/2024"  not in state.text,
          f"text={state.text!r}")
    check("OW.085394.2025 usunięty", "OW.085394.2025" not in state.text,
          f"text={state.text!r}")
    check("KA1K/00075119/1 usunięty","KA1K/00075119/1" not in state.text,
          f"text={state.text!r}")
    rm = state.allocator.reverse_map
    check("4 wpisy w reverse_map", len(rm) == 4,
          f"reverse_map={rm}")

    # ── Test wariantów sądowych ────────────────────────────────────────────────
    print("\n2. Warianty sygnatur sądowych:")
    state2 = PipelineState(
        text="XII Ns 6221/2016, II ACa 45/2023, Kmp 987/2024",
        allocator=TokenAllocator(),
    )
    apply_legal_layer(state2)
    check("XII Ns 6221/2016 usunięta",  "XII Ns 6221/2016" not in state2.text)
    check("II ACa 45/2023 usunięta",    "II ACa 45/2023"   not in state2.text)
    check("Kmp 987/2024 usunięta",      "Kmp 987/2024"     not in state2.text)

    # ── Test sygnatur administracyjnych ──────────────────────────────────────
    print("\n3. Sygnatury administracyjne (różne prefiksy):")
    state3 = PipelineState(
        text="ref. PT.046166.2021 i SA.092213.2021",
        allocator=TokenAllocator(),
    )
    apply_legal_layer(state3)
    check("PT.046166.2021 usunięty", "PT.046166.2021" not in state3.text)
    check("SA.092213.2021 usunięty", "SA.092213.2021" not in state3.text)
    rm3 = state3.allocator.reverse_map
    check("Dwa osobne tokeny", len(rm3) == 2, f"reverse_map={rm3}")

    # ── Test deduplikacji ────────────────────────────────────────────────────
    print("\n4. Deduplication — ta sama sygnatura dwa razy:")
    state4 = PipelineState(
        text="sygn. I C 123/2024 (poprzednio I C 123/2024)",
        allocator=TokenAllocator(),
    )
    apply_legal_layer(state4)
    check("Sygnatura usunięta", "I C 123/2024" not in state4.text)
    rm4 = state4.allocator.reverse_map
    check("Jeden token (dedup)", len(rm4) == 1, f"reverse_map={rm4}")

    # ── Test brak dopasowań ──────────────────────────────────────────────────
    print("\n5. Brak dopasowań — tekst niezmieniony:")
    original = "Zwykły tekst bez sygnatur."
    state5 = PipelineState(text=original, allocator=TokenAllocator())
    apply_legal_layer(state5)
    check("Tekst niezmieniony", state5.text == original)
    check("reverse_map pusty", len(state5.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_legal_layer() else 1)
