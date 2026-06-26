"""
layers/verbal_amount_layer.py  v1.0
Adapter verbal_amounts.mask_verbal_amounts() → PipelineState/TokenAllocator.

mask_verbal_amounts() używa własnego kwota_counter i reverse_map.
Adapter synchronizuje licznik KWOTA z allocatorem żeby nie było kolizji
z tokenami KWOTA wstawionymi przez apply_amount_layer (cyfrowe).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_core import PipelineState
import verbal_amounts as _va


def apply_verbal_amount_layer(state: PipelineState) -> None:
    """Maskuje kwoty słowne (sto dwadzieścia złotych 00/100 itp.)"""
    # Zaseeduj licznik KWOTA powyżej tokenów już wstawionych przez amount_layer
    kwota_n = state.allocator._counters.get("KWOTA", 0)
    seed: dict[str, str] = {f"KWOTA_{i:03d}": "__seed__" for i in range(1, kwota_n + 1)}
    kwota_counter = [kwota_n]

    new_text, new_map = _va.mask_verbal_amounts(state.text, dict(seed), kwota_counter)

    for tid, value in new_map.items():
        if tid in seed:
            continue
        pos = new_text.find(tid)
        if pos >= 0:
            state.allocator.register(tid, value, pos, pos + len(tid))

    state.text = new_text
