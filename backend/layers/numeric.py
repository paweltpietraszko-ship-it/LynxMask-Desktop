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
# [LYNX-AMOUNTS-NUMBERS] Numer dokumentu po „nr”/„numer” (Mobile A.12): zawiera cyfrę i separator albo ≥ 4 znaki; tylko gdy
# w 60 znakach wstecz jest słowo dokumentu. Maskowany sam numer, „nr” zostaje.
_NUM_DOC_RE = re.compile(r'(?i)\b(?:nr|numer)\.?[ \t]*:?[ \t]*(?P<num>(?=[A-Za-z0-9/.\-]*\d)[A-Za-z0-9]+(?:[/\-.][A-Za-z0-9]+)*)(?![_\w])')
_DOC_SIGNAL_RE = re.compile(r'(?i)\b(?:faktur|umow|umów|zlecen|zamówien|zamowien|aneks)')
# [SILENT-PACK1] Numer rozbity spacjami OCR po etykiecie („numerklienta: K L 7017 O”): ≥3 krótkie człony WIELKIE/cyfry, ≥3 cyfry
# z rzędu. Maskowany sam numer, etykieta zostaje.
_NUM_SPACED_RE = re.compile(r'(?i:\b(?:nr|numer)\.?[ \t]*(?:klienta|polisy|umowy|faktury|zamówienia|zlecenia|sprawy)?[ \t]*:?[ \t]*)'
                            r'(?P<num>(?=[A-Z0-9 ]*\d{3})[A-Z0-9]{1,4}(?: [A-Z0-9]{1,4}){2,7})(?![\w/\-])')

_NUMERIC_PATTERNS: list[re.Pattern] = [
    _NUM_KLIENTA_RE,
    _NUM_FAKTURY_RE,
    _NUM_UMOWY_RE,
    _NUM_DOC_RE,
    _NUM_SPACED_RE,
]


def _doc_number_span(text: str, m: re.Match) -> tuple[int, int] | None:
    num = m.group("num")
    if not (re.search(r"[/\-.]", num) or len(num) >= 4) or not _DOC_SIGNAL_RE.search(text[max(0, m.start() - 60):m.start()]):
        return None
    return m.span("num")


def apply_numeric_layer(state: PipelineState) -> None:
    """Maskuje numery klienta (KL-), faktury (FV-/VAT/), umowy (UMW/) i numer dokumentu po „nr”."""
    hits: list[tuple[int, int, str]] = []
    for pat in _NUMERIC_PATTERNS:
        for m in pat.finditer(state.text):
            span = _doc_number_span(state.text, m) if pat is _NUM_DOC_RE else m.span("num" if "num" in pat.groupindex else 0)
            if span:
                hits.append((span[0], span[1], state.text[span[0]:span[1]]))

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
