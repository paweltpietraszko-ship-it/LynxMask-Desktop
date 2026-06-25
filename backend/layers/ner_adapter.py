"""
layers/ner_adapter.py  v1.1
Adapter NER — wywołuje ner_layer.process_ner() i rejestruje tokeny w allocatorze.
ner_layer.py nie jest modyfikowany.
v1.1: Dodano extract_ner_results() — pre-ekstrakcja NER z tekstu PRZED apply_address_layer.
  SpaCy musi widzieć pełny adres (ul. X, kod miasto) żeby poprawnie rozpoznać
  poprzedzające imię/nazwisko jako OSOBA. Po zamaskowaniu adresu traci ten kontekst.
  apply_ner_layer() używa state.ner_results jeśli wypełnione (pre-cache),
  w przeciwnym razie wywołuje process_ner() bezpośrednio (fallback).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ner_layer import process_ner
from pipeline_core import PipelineState, TokenAllocator


def extract_ner_results(state: PipelineState, anon_map: dict) -> None:
    """Ekstrahuje wyniki NER z bieżącego state.text i zapisuje w state.ner_results.

    NIE modyfikuje state.text. Wywoływana PRZED apply_address_layer,
    żeby SpaCy widział pełne adresy jako kontekst dla rozpoznania imion/nazwisk.
    apply_ner_layer() wykryje wypełnione state.ner_results i użyje ich zamiast
    ponownie wywoływać process_ner().
    """
    ner_reverse, ner_variants = process_ner(state.text, anon_map)
    state.ner_results = ner_reverse
    state.ner_variants = ner_variants


def apply_ner_layer(state: PipelineState, anon_map: dict) -> None:
    """Rejestruje tokeny OSOBA/FIRMA w state.allocator i zastępuje w tekście.

    Jeśli state.ner_results jest wypełnione przez extract_ner_results()
    (pre-ekstrakcja przed adresami), używa tych wyników.
    W przeciwnym razie wywołuje process_ner() bezpośrednio (fallback).
    """
    if state.ner_results:
        ner_reverse = state.ner_results
    else:
        ner_reverse, ner_variants = process_ner(state.text, anon_map)
        state.ner_variants = ner_variants

    for token_id, value in ner_reverse.items():
        start = state.text.find(value)
        if start >= 0:
            end = start + len(value)
            state.allocator.register(token_id, value, start, end)

    for token_id, value in sorted(
        ner_reverse.items(),
        key=lambda x: state.text.find(x[1]),
        reverse=True,
    ):
        state.text = state.text.replace(value, token_id)


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_ner_adapter() -> bool:
    import sys as _sys
    import unittest.mock as _mock

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

    print("=== test_ner_adapter ===\n")

    # sys.modules[__name__] działa zarówno przy python layers/ner_adapter.py
    # (wtedy __name__ == "__main__") jak i przy imporcie jako moduł.
    this_module = _sys.modules[__name__]

    # ── Test 1: jedna encja OSOBA ─────────────────────────────────────────────
    print("1. Jedna encja OSOBA:")
    mock_reverse = {"OSOBA_001": "Jan Kowalski"}
    mock_variants = {}

    with _mock.patch.object(this_module, "process_ner",
                            return_value=(mock_reverse, mock_variants)):
        state = PipelineState(
            text="Pozwany: Jan Kowalski zamieszkały w Warszawie.",
            allocator=TokenAllocator(),
        )
        apply_ner_layer(state, anon_map={})

    check("Jan Kowalski usunięty z tekstu",
          "Jan Kowalski" not in state.text,
          f"text={state.text!r}")
    check("OSOBA_001 w tekście",
          "OSOBA_001" in state.text,
          f"text={state.text!r}")
    check("OSOBA_001 w reverse_map",
          "OSOBA_001" in state.allocator.reverse_map,
          f"reverse_map={state.allocator.reverse_map}")
    check("ner_variants zapisane",
          state.ner_variants == mock_variants)

    # ── Test 2: dwie encje, różne typy ───────────────────────────────────────
    print("\n2. Dwie encje — OSOBA i FIRMA:")
    mock_reverse2 = {
        "OSOBA_001": "Anna Nowak",
        "FIRMA_001": "ABC Sp. z o.o.",
    }

    with _mock.patch.object(this_module, "process_ner",
                            return_value=(mock_reverse2, {})):
        state2 = PipelineState(
            text="Anna Nowak reprezentuje ABC Sp. z o.o. w sprawie.",
            allocator=TokenAllocator(),
        )
        apply_ner_layer(state2, anon_map={})

    check("Anna Nowak usunięta",     "Anna Nowak"     not in state2.text)
    check("ABC Sp. z o.o. usunięta", "ABC Sp. z o.o." not in state2.text)
    check("OSOBA_001 w reverse_map",
          "OSOBA_001" in state2.allocator.reverse_map)
    check("FIRMA_001 w reverse_map",
          "FIRMA_001" in state2.allocator.reverse_map)

    # ── Test 3: encja nie występuje w tekście — brak rejestracji ─────────────
    print("\n3. Encja nieobecna w tekście — brak rejestracji spanu:")
    mock_reverse3 = {"OSOBA_001": "Nie Ma Takiego"}

    with _mock.patch.object(this_module, "process_ner",
                            return_value=(mock_reverse3, {})):
        state3 = PipelineState(
            text="Tekst bez żadnych encji.",
            allocator=TokenAllocator(),
        )
        apply_ner_layer(state3, anon_map={})

    check("Tekst niezmieniony",
          state3.text == "Tekst bez żadnych encji.")
    rm3 = state3.allocator.reverse_map
    check("reverse_map pusty (find=-1 → nie rejestruje)",
          len(rm3) == 0, f"reverse_map={rm3}")

    # ── Test 4: pusta odpowiedź NER ───────────────────────────────────────────
    print("\n4. Pusta odpowiedź NER:")
    with _mock.patch.object(this_module, "process_ner",
                            return_value=({}, {})):
        state4 = PipelineState(
            text="Zwykły tekst.",
            allocator=TokenAllocator(),
        )
        original = state4.text
        apply_ner_layer(state4, anon_map={})

    check("Tekst niezmieniony", state4.text == original)
    check("reverse_map pusty", len(state4.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_ner_adapter() else 1)
