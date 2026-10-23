"""
layers/institution.py  v1.0
Warstwa institution — polskie instytucje publiczne (ZUS, sądy, urzędy, itp.).
Przeniesiona z _INSTITUTION_RE w pipeline.py do nowej architektury warstw.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_core import PipelineState, TokenAllocator

# [LYNX-FIRMA-PROOF] Zasada (RODO art. 4 pkt 1 / motyw 26; Reguły anonimizacji Portalu Orzeczeń pkt 3.3, 2.6, 2.8; UODO,
# Biuletyn 4/06/23 — szkoła + klasa identyfikuje): nazwa instytucji publicznej nie jest daną osobową — zostaje jawna („ZUS”,
# „Sąd Najwyższy”, „Urząd Skarbowy”). Zakrywamy instytucję z tym, co ją zawęża: miejscowością („w Legnicy”), numerem („nr 18”)
# albo wydziałem („Wydział I Cywilny”) — wtedy cała fraza to INSTYTUCJA.
_UP = "A-ZĄĆĘŁŃÓŚŹŻ"
_TOK = r"(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d"   # miejscowość nie jest tokenem
_ROLE = r"(?!(?:Zamawiając|Wykonawc|Odwołując|Przystępując)\w*)"   # słowo roli nie jest częścią nazwy
_HEAD = (r"(?:Sąd(?!ownictw)|Urz[ąę]d(?!ow)|Prokuratur|Starostw|Komend|Komisariat|Zarząd|Szpital|Przychodni|Przedszkol|Szkoł|Zesp[oó]ł\s+Szkół"
         r"|Gimnazj|Liceum|Technikum|Żłob|Ośrod|Inspektorat|Izb[aąęy]\s+(?:Skarbow|Administracji)|Kuratori|Trybunał)\w*")
_PLACE = rf"(?:[ \t]+nr[ \t]*\d+[A-Za-z]?)?[ \t]+(?:w|we|dla)[ \t]+(?!{_TOK})[{_UP}][\w-]+(?:[ \t-](?!{_TOK})[{_UP}][\w-]+)?"
_NUMBER = r"[ \t]+nr[ \t]*\d+[A-Za-z]?"
_INSTITUTION_RE = re.compile(
    rf"(?<![\w-])(?:{_ROLE}[{_UP}][\w-]+[ \t]+){{0,2}}{_HEAD}(?:[ \t]+(?:[{_UP}][\w-]*|i|ds\.)){{0,6}}?(?:{_PLACE}|{_NUMBER})(?![\w-])"
    r"|Wydział[ \t]+(?:[IVX]+|[0-9]+)[ \t]+[\wÀ-ž][\w \t\-À-ž]{0,30}"
)

_INSTITUTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("INSTYTUCJA", _INSTITUTION_RE),
]


def apply_institution_layer(state: PipelineState) -> None:
    """Zakrywa instytucje publiczne z miejscowością / numerem / wydziałem (sama nazwa instytucji zostaje jawna)."""
    hits: list[tuple[int, int, str, str]] = []
    for token_type, pat in _INSTITUTION_PATTERNS:
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

def test_institution_layer() -> bool:
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

    print("=== test_institution_layer ===\n")

    cases = [  # [LYNX-FIRMA-PROOF] sama nazwa instytucji jawna; z miejscowością / numerem / wydziałem — INSTYTUCJA
        ("ZUS jawny", "Sprawa dotyczy Zakładu Ubezpieczeń Społecznych.", False),
        ("Sąd Najwyższy jawny", "Wyrok Sądu Najwyższego z dnia 5 maja.", False),
        ("Sąd Rejonowy z miastem", "Sąd Rejonowy w Legnicy wydał wyrok.", True),
        ("Wydział", "Sprawę prowadzi Wydział I Cywilny.", True),
        ("Szkoła z numerem", "Uczeń Szkoły Podstawowej nr 18 w Elblągu.", True),
        ("KNF skrót jawny", "Decyzja KNF z dnia 01.01.2024.", False),
    ]

    for name, text, masked in cases:
        state = PipelineState(text=text, allocator=TokenAllocator())
        apply_institution_layer(state)
        check(name, ("INSTYTUCJA_" in state.text) == masked, f"tekst po: {state.text!r}")

    print(f"\nWynik: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    test_institution_layer()
