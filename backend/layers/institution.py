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

# Lustrzana kopia _INSTITUTION_RE z pipeline.py.
# Nie importujemy pipeline.py bezpośrednio — jego import ładuje ner_layer,
# verbal_amounts i ner_blocklist ze skutkami ubocznymi.
_INSTITUTION_RE = re.compile(
    r"(?:"
    r"(?:Sąd|Sądu|Sądowi)\s+(?:Rejonowy|Rejonowego|Rejonowemu|Okręgowy|Okręgowego|Okręgowemu|Apelacyjny|Apelacyjnego|Administracyjny|Administracyjnego|Najwyższy|Najwyższego)"
    r"|(?:Naczelny|Naczelnego)\s+(?:Sąd|Sądu)\s+Administracyjny(?:ego)?"
    r"|(?:Wojewódzki|Wojewódzkiego)\s+(?:Sąd|Sądu)\s+Administracyjny(?:ego)?"
    r"|(?:Urząd|Urzędu|Urzędowi)\s+(?:Skarbowy|Skarbowego|Celno-Skarbowy|Celno-Skarbowego|Pracy|Ochrony\s+Danych\s+Osobowych)"
    r"|(?:Prokuratura|Prokuratury|Prokuraturze)\s+(?:Rejonowa|Rejonowej|Okręgowa|Okręgowej|Apelacyjna|Apelacyjnej|Krajowa|Krajowej)"
    r"|(?:Powiatowy|Powiatowego|Wojewódzki|Wojewódzkiego)\s+(?:Urząd|Urzędu)\s+Pracy"
    r"|(?:Zakład|Zakładu|Zakładowi)\s+Ubezpieczeń\s+Społecznych"
    r"|Wydział[ \t]+(?:[IVX]+|[0-9]+)[ \t]+[\wÀ-ž][\w \t\-À-ž]{0,30}"
    r"|(?:Komisja|Komisji|Komisję)\s+Nadzoru\s+Finansowego"
    r"|(?:Rzecznik|Rzecznika|Rzecznikowi)\s+Praw\s+Obywatelskich"
    r"|(?:Trybunał|Trybunału|Trybunałowi)\s+Konstytucyjn(?:y|ego|emu)"
    r"|(?:Państwowa|Państwowej)\s+Inspekcja\s+Pracy|Państwowej\s+Inspekcji\s+Pracy"
    r"|(?:Pracownicze|Pracowniczych|Pracowniczymi)\s+Plan(?:y|ów|ami)\s+Kapitałow(?:e|ych|ymi)"
    r"|\bPPK\b|\bKNF\b|\bRPO\b|\bTK\b|\bPIP\b|\bGUS\b|\bNIK\b|\bUOKiK\b"
    r")",
    re.IGNORECASE | re.UNICODE,
)

_INSTITUTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("INSTYTUCJA", _INSTITUTION_RE),
]


def apply_institution_layer(state: PipelineState) -> None:
    """Stosuje wzorce polskich instytucji publicznych na state.text."""
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

    cases = [
        ("ZUS", "Sprawa dotyczy Zakładu Ubezpieczeń Społecznych.", "INSTYTUCJA"),
        ("Sąd Rejonowy", "Zgodnie z orzeczeniem Sąd Rejonowy strony zawarły ugodę.", "INSTYTUCJA"),
        ("Urząd Skarbowy", "Pismo od Urzędu Skarbowego.", "INSTYTUCJA"),
        ("Prokuratura Okręgowa", "Prokuratura Okręgowa wszczęła dochodzenie.", "INSTYTUCJA"),
        ("Trybunał Konstytucyjny", "Wyrok Trybunału Konstytucyjnego.", "INSTYTUCJA"),
        ("KNF skrót", "Decyzja KNF z dnia 01.01.2024.", "INSTYTUCJA"),
        ("RPO skrót", "Wniosek do RPO.", "INSTYTUCJA"),
    ]

    for name, text, expected_type in cases:
        state = PipelineState(text=text, allocator=TokenAllocator())
        apply_institution_layer(state)
        found = expected_type + "_" in state.text
        check(name, found, f"tekst po: {state.text!r}")

    print(f"\nWynik: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    test_institution_layer()
