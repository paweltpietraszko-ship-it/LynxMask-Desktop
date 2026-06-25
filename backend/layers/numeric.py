"""
layers/numeric.py  v1.0
Warstwa numeric — identyfikatory biurowe: numer klienta, faktury, umowy.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_core import PipelineState, TokenAllocator

_NUM_KLIENTA_RE = re.compile(r'\bKL-\d{4,6}\b')
_NUM_FAKTURY_RE = re.compile(
    r'\b(?:FV-\d{4,6}/\d{2}/\d{4}|VAT/\d{4}/\d{3,6}|\d{4,6}/\d{2}/\d{4})\b'
)
_NUM_UMOWY_RE = re.compile(r'\bUMW/\d{4}/\d{3,6}\b')

_NUMERIC_PATTERNS: list[re.Pattern] = [
    _NUM_KLIENTA_RE,
    _NUM_FAKTURY_RE,
    _NUM_UMOWY_RE,
]


def apply_numeric_layer(state: PipelineState) -> None:
    """Maskuje numery klienta (KL-), faktury (FV-/VAT/) i umowy (UMW/)."""
    hits: list[tuple[int, int, str]] = []
    for pat in _NUMERIC_PATTERNS:
        for m in pat.finditer(state.text):
            hits.append((m.start(), m.end(), m.group(0)))

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
