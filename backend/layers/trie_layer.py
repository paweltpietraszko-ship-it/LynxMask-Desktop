"""
layers/trie_layer.py  v1.0
Warstwa 0b — słownik klienta (Aho-Corasick trie).
Deleguje do _layer1_trie() z anonymizer.py. Musi działać jako PIERWSZA
warstwa maskowania — przed regex, NER, adresami — żeby dopasowania
ze słownika klienta miały priorytet i nie były rozbijane przez inne wzorce.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer import Anonymizer
from pipeline_core import PipelineState


def apply_trie_layer(state: PipelineState, anonymizer: Anonymizer) -> None:
    """
    Wywołuje Aho-Corasick trie słownika klienta.
    Nowe tokeny rejestruje w state.allocator — bez tworzenia własnych liczników.
    Jeśli anonymizer jest None lub trie jest puste, warstwa jest no-op.
    """
    if anonymizer is None:
        return

    # Zaseeduj liczniki typów już obecnych w allocatorze
    seed: dict[str, str] = {}
    for tok_id in state.allocator.reverse_map:
        seed[tok_id] = "__seed__"

    text1, map1 = anonymizer._layer1_trie(state.text, dict(seed))

    for tid, value in map1.items():
        if tid in seed:
            continue
        pos = text1.find(tid)
        if pos >= 0:
            state.allocator.register(tid, value, pos, pos + len(tid))

    state.text = text1
