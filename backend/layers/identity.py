"""
layers/identity.py  v1.5
Warstwa identity — PESEL, NIP, REGON, dowod osobisty, paszport.
v1.4: [BUG-UR-DOB] Wzorzec ur. DD.MM.RRRR nie trafiał do _IDENTITY_PATTERNS.
  _IDENTITY_SOURCES miał literalne ZŁŚŹĆŃ, anonymizer_init.py ma ŁŚ...
  — inne bajty, pat.pattern in frozenset zwracał False.
  Fix: zmieniono klucz w _IDENTITY_SOURCES na zapis \\u zgodny z anonymizer_init.py.
v1.5: [BUG-NIP-DOUBLE-SEP] NIP z separatorem " -" (spacja+myslnik): "873 -000 -51-39".
  _NIP_RE_OCR zmieniony z [-\s.]? na [-\s.]{0,3} — lapie 0, 1 lub 2 znaki separatora.
v1.3: [BUG-PASSPORT-SPACE] Paszport ze spacją OCR: [A-Z]{2}[ \t]?\d{7}.
v1.2: [NUMER-RECALL-OCR] OCR-tolerancyjne wzorce PESEL/NIP/REGON.
  OCR czesto wstawia spacje w srodku liczb (85041 23 4567 zamiast 85041234567).
  _DIGITS_WITH_SPACES_RE: lapiemy grupy cyfr przedzielone spacjami,
  filtrujemy post-match po lacznej liczbie cyfr (11=PESEL, 10=NIP, 9=REGON).
  Wartosc kanoniczna w reverse_map = cyfry bez spacji.
"""
from __future__ import annotations

import os
import re
import sys

# Pozwala uruchamiać plik bezpośrednio (python layers/identity.py)
# oraz jako moduł (python -m layers.identity) z katalogu projektu.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer_init import STRUCTURAL_PATTERNS
from pipeline_core import PipelineState, TokenAllocator

# Klucze do filtrowania STRUCTURAL_PATTERNS — muszą dokładnie pasować do pat.pattern
_IDENTITY_SOURCES: frozenset[str] = frozenset({
    r"(?<!\d)\d{11}(?!\d)",                                    # PESEL
    r"(?<!\d)\d{14}(?!\d)",                                    # REGON 14
    r"(?<!\d)\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}(?!\d)",  # NIP format 3-3-2-2 (lookup)
    r"(?<!\d)\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3}(?!\d)",  # NIP format 3-2-2-3 [BUG-NIP-LEAK]
    r"\bPL\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b",          # NIP z PL
    r"(?<!\d)\d{9}(?!\d)",                                     # REGON 9
    r"(?<![A-Za-z])[A-Z]{3}\s?\d{6}(?!\d)",                   # Dowód osobisty
    r"(?<![A-Z])\b[A-Z]{2}[ \t]?\d{7}\b",                     # Paszport (ze spacją OCR lub bez)
    r"\bur\.\s*\d{1,2}\.\d{1,2}\.\d{4}(?:\s+w\s+[A-Z\u0141\u015a\u0179\u0106\u0143][\w\-]{1,30})?",  # ur. DD.MM.RRRR
})

# Wzorzec NIP z rozszerzonym separatorem: OCR czasem zastepuje myslnik kropka
# (np. "766-444-75.06"). STRUCTURAL_PATTERNS ma stary [-\s]? — podmieniamy lokalnie.
_NIP_PATTERN_ORIG = r"(?<!\d)\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}(?!\d)"
_NIP_RE_OCR = re.compile(r"(?<!\d)\d{3}[-\s.]{0,3}\d{3}[-\s.]{0,3}\d{2}[-\s.]{0,3}\d{2}(?!\d)")

_IDENTITY_PATTERNS: list[tuple[str, re.Pattern]] = [
    (tok, _NIP_RE_OCR if pat.pattern == _NIP_PATTERN_ORIG else pat)
    for tok, pat in STRUCTURAL_PATTERNS
    if pat.pattern in _IDENTITY_SOURCES
]

# [NUMER-RECALL-OCR] OCR wstawia spacje w srodek liczb.
# Lapiemy: grupy cyfr przedzielone spacjami/tabami, min 2 grupy.
# Post-match: filtrujemy po lacznej liczbie cyfr.
_DIGITS_WITH_SPACES_RE = re.compile(r"(?<!\d)\d+(?:[ \t]\d+)+(?!\d)")
_OCR_DIGIT_COUNTS: frozenset[int] = frozenset({11, 10})  # PESEL, NIP — 9 (REGON) zbyt ryzykowne (= telefon)
_OCR_DIGIT_TOKEN: dict[int, str] = {11: "NUMER", 10: "NUMER", 9: "NUMER"}


def _digit_count(s: str) -> int:
    return sum(1 for c in s if c.isdigit())


def apply_identity_layer(state: PipelineState) -> None:
    """Stosuje wzorce identity (PESEL/NIP/REGON/dowod/paszport) na state.text."""
    hits: list[tuple[int, int, str, str]] = []

    # [NUMER-RECALL-OCR] Najpierw OCR-tolerancyjne liczby z spacjami
    for m in _DIGITS_WITH_SPACES_RE.finditer(state.text):
        dc = _digit_count(m.group(0))
        if dc in _OCR_DIGIT_COUNTS:
            canonical = m.group(0).replace(" ", "").replace("\t", "")
            hits.append((m.start(), m.end(), canonical, _OCR_DIGIT_TOKEN[dc]))

    for token_type, pat in _IDENTITY_PATTERNS:
        for m in pat.finditer(state.text):
            hits.append((m.start(), m.end(), m.group(0), token_type))

    # Wiekszy span wygrywa
    hits.sort(key=lambda x: (-(x[1] - x[0]), -x[0]))
    valid: list[tuple[int, int, str]] = []
    for start, end, value, token_type in hits:
        if state.allocator.is_occupied(start, end):
            continue
        tid = state.allocator.allocate(token_type, value, start, end)
        if tid is None:
            continue
        valid.append((start, end, tid))

    valid.sort(key=lambda x: x[0], reverse=True)
    text = state.text
    for start, end, tid in valid:
        text = text[:start] + tid + text[end:]
    state.text = text


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_identity_layer() -> bool:
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

    print("=== test_identity_layer ===\n")

    print("1. PESEL + dowód + paszport:")
    state = PipelineState(
        text="PESEL: 85010112345, dowód: AOK171495, paszport: ZX1234567",
        allocator=TokenAllocator(),
    )
    apply_identity_layer(state)
    check("PESEL usunięty",    "85010112345" not in state.text,
          f"text={state.text!r}")
    check("Dowód usunięty",    "AOK171495"   not in state.text,
          f"text={state.text!r}")
    check("Paszport usunięty", "ZX1234567"   not in state.text,
          f"text={state.text!r}")
    check("3 wpisy w reverse_map", len(state.allocator.reverse_map) == 3,
          f"reverse_map={state.allocator.reverse_map}")

    print("\n2. NIP + REGON 9 + REGON 14:")
    state2 = PipelineState(
        text="NIP: 855-019-31-23, REGON: 123456789, REGON14: 12345678901234",
        allocator=TokenAllocator(),
    )
    apply_identity_layer(state2)
    check("NIP usunięty",      "855-019-31-23" not in state2.text)
    check("REGON 9 usunięty",  "123456789"      not in state2.text,
          f"text={state2.text!r}")
    check("REGON 14 usunięty", "12345678901234" not in state2.text)

    print("\n3. Ochrona spanu — ten sam PESEL dwa razy:")
    state3 = PipelineState(
        text="85010112345 i znowu 85010112345",
        allocator=TokenAllocator(),
    )
    apply_identity_layer(state3)
    check("Oba PESEL zastąpione", "85010112345" not in state3.text)
    rm3 = state3.allocator.reverse_map
    check("Jeden token (deduplication)", len(rm3) == 1,
          f"reverse_map={rm3}")
    check("Token poprawny", list(rm3.values()) == ["85010112345"],
          f"values={list(rm3.values())}")

    print("\n4. OCR-rozbity PESEL — spacja w srodku:")
    state4a = PipelineState(
        text="PESEL: 8504123 4567",
        allocator=TokenAllocator(),
    )
    apply_identity_layer(state4a)
    check("PESEL z OCR-spacja usuniety", "8504123 4567" not in state4a.text,
          f"text={state4a.text!r}")
    rm4a = state4a.allocator.reverse_map
    check("Kanoniczny PESEL (bez spacji)",
          any(v == "85041234567" for v in rm4a.values()),
          f"values={list(rm4a.values())}")

    print("\n5. OCR-rozbity PESEL — dwa podzialy:")
    state4b = PipelineState(
        text="nr: 850 412 34567",
        allocator=TokenAllocator(),
    )
    apply_identity_layer(state4b)
    check("PESEL 850 412 34567 usuniety", "850 412 34567" not in state4b.text,
          f"text={state4b.text!r}")

    print("\n6. Brak dopasowania — tekst niezmieniony:")
    original = "Zwykły tekst bez PII: data 2024-01-15."
    state4 = PipelineState(text=original, allocator=TokenAllocator())
    apply_identity_layer(state4)
    check("Tekst niezmieniony", state4.text == original,
          f"text={state4.text!r}")
    check("reverse_map pusty", len(state4.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if test_identity_layer() else 1)
