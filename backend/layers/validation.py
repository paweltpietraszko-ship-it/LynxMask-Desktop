"""
layers/validation.py  v1.0
Warstwa walidacyjna — stdnum (PESEL/NIP/IBAN/REGON przez python-stdnum)
i phonenumbers (libphonenumber). Deleguje do _layer4_stdnum() i
_layer5_phonenumbers() z anonymizer.py bez ich przepisywania.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer import Anonymizer
from pipeline_core import PipelineState


def apply_validation_layer(state: PipelineState, anonymizer: Anonymizer) -> None:
    """
    Wywołuje walidatory stdnum i phonenumbers z anonymizer.py.
    Nowe tokeny rejestruje w state.allocator przez register() — bez tworzenia
    własnych liczników (licznik pochodzi z allocatora).
    """
    # Zaseeduj licznik NUMER tak żeby _layer4/_layer5 startowały powyżej
    # tokenów już wstawionych przez wcześniejsze warstwy.
    numer_n = state.allocator._counters.get("NUMER", 0)
    seed: dict[str, str] = {f"NUMER_{i:03d}": "__seed__" for i in range(1, numer_n + 1)}

    # ── Warstwa 4: stdnum ─────────────────────────────────────────────────────
    text4, map4 = anonymizer._layer4_stdnum(state.text, dict(seed))
    for tid, value in map4.items():
        if tid in seed:          # wpis siewny — pomijamy
            continue
        pos = text4.find(tid)
        if pos >= 0:
            state.allocator.register(tid, value, pos, pos + len(tid))

    # ── Warstwa 5: phonenumbers ───────────────────────────────────────────────
    # Przekazujemy map4 (z wpisami sewnymi + nowymi z L4) żeby L5 nie kolizjonował.
    text5, map5 = anonymizer._layer5_phonenumbers(text4, dict(map4))
    for tid, value in map5.items():
        if tid in map4:          # znany z L4 lub seed — pomijamy
            continue
        pos = text5.find(tid)
        if pos >= 0:
            state.allocator.register(tid, value, pos, pos + len(tid))

    state.text = text5


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_validation_layer() -> bool:
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

    print("=== test_validation_layer ===\n")

    # Zbuduj minimalna instancje Anonymizer z pustym anon_map
    class _EmptyMap:
        def lookup(self, v): return None
        def load_trie(self): return {}
        def all_entities(self): return []

    anon = Anonymizer(_EmptyMap())

    # ── 1. PESEL przez stdnum ─────────────────────────────────────────────────
    print("1. PESEL przez stdnum (walidacja cyfry kontrolnej):")
    state = PipelineState(text="PESEL: 85010112345", allocator=__import__("pipeline_core").TokenAllocator())
    apply_validation_layer(state, anon)
    check("PESEL usunięty", "85010112345" not in state.text,
          f"text={state.text!r}")
    check("token w reverse_map", len(state.allocator.reverse_map) > 0,
          f"map={state.allocator.reverse_map}")

    # ── 2. Nie duplikuje tokenów już wstawionych przez wcześniejszą warstwę ──
    print("\n2. Brak duplikacji — PESEL już zamaskowany jako NUMER_001:")
    from pipeline_core import TokenAllocator
    alloc2 = TokenAllocator()
    alloc2.register("NUMER_001", "85010112345", 7, 18)
    state2 = PipelineState(text="PESEL: NUMER_001", allocator=alloc2)
    apply_validation_layer(state2, anon)
    check("NUMER_001 nienaruszony", "NUMER_001" in state2.text,
          f"text={state2.text!r}")
    check("brak NUMER_002 (nie zduplikowano)", "NUMER_002" not in state2.text)
    check("reverse_map ma tylko 1 wpis", len(state2.allocator.reverse_map) == 1,
          f"map={state2.allocator.reverse_map}")

    # ── 3. Licznik kontynuuje za allocatorem ─────────────────────────────────
    print("\n3. Licznik NUMER kontynuuje za istniejącym NUMER_003:")
    alloc3 = TokenAllocator()
    alloc3.register("NUMER_001", "111", 0, 3)
    alloc3.register("NUMER_002", "222", 5, 8)
    alloc3.register("NUMER_003", "333", 10, 13)
    # tekst bez tokenów — nowy PESEL powinien dostać NUMER_004
    state3 = PipelineState(text="PESEL: 85010112345", allocator=alloc3)
    apply_validation_layer(state3, anon)
    rm3 = state3.allocator.reverse_map
    new_tokens = {k: v for k, v in rm3.items() if k not in {"NUMER_001", "NUMER_002", "NUMER_003"}}
    if new_tokens:
        new_tid = list(new_tokens.keys())[0]
        check("nowy token = NUMER_004", new_tid == "NUMER_004",
              f"nowy={new_tid}")
    else:
        check("nowy token PESEL powstał", False, "stdnum nie wykrył PESEL")

    # ── 4. Tekst bez PII — brak zmian ────────────────────────────────────────
    print("\n4. Tekst bez PII — allocator nienaruszony:")
    state4 = PipelineState(text="Zwykly tekst bez danych.", allocator=TokenAllocator())
    apply_validation_layer(state4, anon)
    check("tekst niezmieniony", state4.text == "Zwykly tekst bez danych.")
    check("reverse_map pusty", len(state4.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_validation_layer() else 1)
