"""
layers/fallback.py  v1.0
Warstwa fallback — siatka bezpieczeństwa dla luźnych liczb 8+ cyfr.
Łapie tylko to co nie zostało zamaskowane przez wcześniejsze warstwy.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_core import PipelineState, TokenAllocator

_FALLBACK_RE = re.compile(r"(?<!\d)\d{8,}(?!\d)")


def apply_fallback_layer(state: PipelineState) -> None:
    """Maskuje ciągi 8+ cyfr które przeżyły wszystkie wcześniejsze warstwy."""
    hits: list[tuple[int, int, str]] = [
        (m.start(), m.end(), m.group(0))
        for m in _FALLBACK_RE.finditer(state.text)
    ]

    hits.sort(key=lambda x: x[0], reverse=True)

    text = state.text
    for start, end, value in hits:
        if state.allocator.is_occupied(start, end):
            continue
        tid = state.allocator.allocate("NUMER", value, start, end)
        if tid is None:
            continue
        text = text[:start] + tid + text[end:]

    state.text = text


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_fallback_layer() -> bool:
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

    print("=== test_fallback_layer ===\n")

    # ── Test podstawowy: 8-cyfrowy numer złapany, NUMER_001 nienaruszony ─────
    print("1. Fallback łapie 8+ cyfr, pomija już zamaskowane spany:")
    state = PipelineState(
        text="nr ref: 12345678, kod: ABC123 (już zamaskowane: NUMER_001)",
        allocator=TokenAllocator(),
    )
    state.allocator.register("NUMER_001", "cokolwiek", 37, 46)
    apply_fallback_layer(state)
    check("12345678 usunięty",   "12345678"  not in state.text,
          f"text={state.text!r}")
    check("NUMER_001 nienaruszony", "NUMER_001" in state.text,
          f"text={state.text!r}")

    # ── Test: liczby 7-cyfrowe NIE są łapane ─────────────────────────────────
    print("\n2. Liczby 7-cyfrowe poza zasięgiem fallback:")
    state2 = PipelineState(
        text="Numer: 1234567",
        allocator=TokenAllocator(),
    )
    apply_fallback_layer(state2)
    check("7-cyfrowy nienaruszony", "1234567" in state2.text,
          f"text={state2.text!r}")
    check("reverse_map pusty", len(state2.allocator.reverse_map) == 0)

    # ── Test: span zajęty przez poprzednią warstwę → fallback pomija ─────────
    print("\n3. Span zajęty → fallback pomija:")
    state3 = PipelineState(
        text="12345678901",  # 11 cyfr (PESEL — już zamaskowany przez identity)
        allocator=TokenAllocator(),
    )
    state3.allocator.register("NUMER_001", "12345678901", 0, 11)
    apply_fallback_layer(state3)
    check("11-cyfrowy nienaruszony (span zajęty)", "12345678901" in state3.text,
          f"text={state3.text!r}")

    # ── Test: deduplikacja — ten sam numer dwa razy ───────────────────────────
    print("\n4. Deduplication — ten sam numer dwa razy:")
    state4 = PipelineState(
        text="a: 12345678 b: 12345678",
        allocator=TokenAllocator(),
    )
    apply_fallback_layer(state4)
    check("Oba numery usunięte", "12345678" not in state4.text)
    rm4 = state4.allocator.reverse_map
    check("Jeden token (dedup)", len(rm4) == 1, f"reverse_map={rm4}")

    # ── Test: wiele różnych 8+ cyfrowych numerów ──────────────────────────────
    print("\n5. Wiele różnych numerów 8+ cyfrowych:")
    state5 = PipelineState(
        text="X: 12345678 Y: 987654321 Z: 1234567890",
        allocator=TokenAllocator(),
    )
    apply_fallback_layer(state5)
    check("Wszystkie numery usunięte",
          "12345678" not in state5.text
          and "987654321" not in state5.text
          and "1234567890" not in state5.text,
          f"text={state5.text!r}")
    rm5 = state5.allocator.reverse_map
    check("3 różne tokeny", len(rm5) == 3, f"reverse_map={rm5}")

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_fallback_layer() else 1)
