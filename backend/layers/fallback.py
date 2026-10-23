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
# [LYNX-T07] Resztka ≥15 cyfr łącznie, ze spacjami/tabami (także wielokrotnymi) lub myślnikiem między cyframi, jako JEDNA
# wartość (także z przyklejonym prefiksem kraju „PL61…”). Bez przejścia przez newline, interpunkcję, wyraz ani token.
_LONG_NUMBER_RE = re.compile(r"(?<!\w)(?:[A-Z]{2}(?=\d{2}))?\d(?:(?:[ \t]*-[ \t]*|[ \t]*)\d){14,}(?!\w)")


# [LYNX-FIRMA-PROOF] Wartość zakryta raz jest zakryta wszędzie. Warstwy regułowe łapią numer, datę czy znak sprawy w jednym
# kontekście („nr 75/06”, „dnia 02.11.2011 r.”), a to samo powtórzone gdzie indziej („zaświadczenia nr 75/06.”, „02.11.2011r.”)
# zostawało jawne — Guard zgłaszał czerwone MAP_LEAK. Po wszystkich warstwach każda wartość z cyfrą (NUMER, KWOTA, ADRES, EMAIL,
# INSTYTUCJA) zastępuje swoje pozostałe dokładne wystąpienia tym samym tokenem (OSOBA/FIRMA mają warianty w ner_adapter).
# Granica: przed wartością nie litera/cyfra/„/”; po cyfrze — nie cyfra ani „/” („02.11.2011r.” tak, „75/061” nie), po literze — nie litera.
_TOKEN_RE = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)")
_TYPES = ("NUMER", "KWOTA", "ADRES", "EMAIL", "INSTYTUCJA")


def _pattern(value: str) -> re.Pattern:
    tail = r"(?![\d/])" if value[-1].isdigit() else r"(?!\w)"
    return re.compile(rf"(?<![\w/]){re.escape(value)}{tail}")


def apply_value_propagation(state: PipelineState) -> None:
    """Pozostałe wystąpienia zakrytych wartości z cyfrą (≥4 znaki) → ten sam token; najdłuższe wartości najpierw."""
    items = [(tok, val) for tok, val in state.allocator.reverse_map.items()
             if tok.startswith(_TYPES) and len(val.strip()) >= 4 and any(c.isdigit() for c in val)]
    for tok, val in sorted(items, key=lambda x: -len(x[1])):
        val = val.strip()
        tokens = [m.span() for m in _TOKEN_RE.finditer(state.text)]
        parts, pos = [], 0
        for m in _pattern(val).finditer(state.text):
            if any(a < m.end() and m.start() < b for a, b in tokens):
                continue
            parts += [state.text[pos:m.start()], tok]
            pos = m.end()
        if parts:
            state.text = "".join(parts) + state.text[pos:]


def long_number_runs(text: str) -> list[tuple[int, int]]:
    """[LYNX-T07] Spany całych ciągów ≥15 cyfr w tekście (to samo, co przejmie końcowy fallback)."""
    return [(m.start(), m.end()) for m in _LONG_NUMBER_RE.finditer(text)]


def cuts_long_number(runs: list[tuple[int, int]], start: int, end: int) -> bool:
    """Trafienie warstwy przecina długi numer, ale nie obejmuje go całego — pełna wartość albo nic."""
    return any(a < end and start < b and not (start <= a and b <= end) for a, b in runs)


def apply_fallback_layer(state: PipelineState, full: bool = True) -> None:
    """Ostatnia warstwa: całe resztki ≥15 cyfr (oba tryby), w pełnym trybie także ciągi 8+ cyfr. Jedno przejście —
    dłuższe dopasowanie wygrywa, krótsze nakładające się pominięte (LYNX-T07 r3 F1)."""
    hits = [(m.start(), m.end(), m.group(0)) for pat in ((_LONG_NUMBER_RE, _FALLBACK_RE) if full else (_LONG_NUMBER_RE,))
            for m in pat.finditer(state.text)]
    taken: list[tuple[int, int, str]] = []
    for start, end, value in sorted(hits, key=lambda h: (h[0] - h[1], h[0])):
        if any(a < end and start < b for a, b, _ in taken) or state.allocator.is_occupied(start, end):
            continue
        tid = state.allocator.allocate("NUMER", value, start, end)
        if tid is not None:
            taken.append((start, end, tid))
    text = state.text
    for start, end, tid in sorted(taken, reverse=True):
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
