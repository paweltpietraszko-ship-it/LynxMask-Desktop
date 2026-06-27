"""
layers/financial.py  v1.2
Warstwa financial -- IBAN, numery kont bankowych.
v1.1: [BUG-4] Zagraniczne IBAN (DE, UA, GB, FR, NL...) maskowane przez pipeline.
  _IBAN_FOREIGN_RE: dwa wzorce -- ze spacjami (grupy po 4) i bez spacji (compact).
  Stosowany PO wzorcach PL (konto bez prefiksu PL mogloby podlapac prefiks obcego IBAN).
  Walidacja: min. 15 znakow lacznie (najkrotszy IBAN na swiecie = NO, 15 znakow).
v1.2: [OCR-IBAN-PL] Tolerancyjny wzorzec dla IBAN PL z rozerwanymi grupami (OCR lvl3).
  Zamiast sztywnych grup (?: d{4}){6} -- lacapcy dowolny uklad cyfr i spacji po "PL".
  Post-match: sprawdzamy dokladnie 26 cyfr po prefiksie PL (wymaganie normy ISO 13616).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer_init import STRUCTURAL_PATTERNS, TOKEN_NUMER
from pipeline_core import PipelineState, TokenAllocator

# Explicit set -- "PL" in pat.pattern zlapalby tez NIP-PL i PLN (waluta)
_FINANCIAL_SOURCES: frozenset[str] = frozenset({
    r"(?<!\d)\d{24}(?!\d)",           # 24-cyfrowy numer konta/przesylki
    r"\b\d{2}(?:\s\d{4}){5,6}\b",     # konto bez prefiksu PL (spacje)
    r"\b\d{2}-\d[\d\-]{20,28}\d\b",   # konto bez prefiksu PL (myslniki)
})

# [OCR-IBAN-PL] Tolerancyjny wzorzec dla PL IBAN z rozerwanymi grupami OCR.
# Lapiemy: PL + do 40 znakow (cyfry + spacje), post-match walidacja: dokladnie 26 cyfr.
# Przyklad OCR lvl3: "PL 98 1 053 1 875 0000 0023 4567 8901" -> 26 cyfr po PL.
_IBAN_PL_OCR_RE = re.compile(r"\bPL[\d\s]{20,45}(?=\D|$)", re.IGNORECASE)

_FINANCIAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    (tok, pat) for tok, pat in STRUCTURAL_PATTERNS
    if pat.pattern in _FINANCIAL_SOURCES
]

# [BUG-4] Zagraniczne IBAN -- DE, UA, GB, FR, NL i inne.
# Wzorzec 1: ze spacjami -- grupy po 4 znaki (A-Z0-9), ostatnia moze byc krotsza.
# Wzorzec 2: compact -- ciagle (bez spacji), min. 11 znakow BBAN po CC+DD.
# Min. 15 znakow lacznie = najkrotszy IBAN (Norwegia NO).
# Wykluczamy "PL" (obslugiwany przez _FINANCIAL_PATTERNS) i "UA" osobno nie trzeba.
_IBAN_FOREIGN_RE = re.compile(
    r"\b(?!PL)[A-Z]{2}\d{2}(?:[ \t]?[A-Z0-9]{4}){2,7}(?:[ \t]?[A-Z0-9]{1,4})?\b"
    r"|"
    r"\b(?!PL)[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"
)

# Minimalny IBAN ma 15 znakow -- odrzucamy krotsze dopasowania (FP-guard)
_IBAN_MIN_LEN = 15


def apply_financial_layer(state: PipelineState) -> None:
    """Stosuje wzorce IBAN i kont bankowych na state.text."""
    hits: list[tuple[int, int, str, str]] = []

    for token_type, pat in _FINANCIAL_PATTERNS:
        for m in pat.finditer(state.text):
            hits.append((m.start(), m.end(), m.group(0), token_type))

    # [OCR-IBAN-PL] PL IBAN z rozerwanymi grupami (OCR lvl3)
    for m in _IBAN_PL_OCR_RE.finditer(state.text):
        raw = m.group(0)
        digits_after_pl = re.sub(r"\D", "", raw[2:])
        if len(digits_after_pl) == 26:
            hits.append((m.start(), m.end(), raw, TOKEN_NUMER))

    # [BUG-4] Zagraniczne IBAN -- po wzorcach PL
    for m in _IBAN_FOREIGN_RE.finditer(state.text):
        raw = m.group(0)
        # Odrzuc jesli za krotkie (FP) lub juz objety wczesniejszym hitem PL
        if len(raw.replace(" ", "").replace("\t", "")) >= _IBAN_MIN_LEN:
            hits.append((m.start(), m.end(), raw, TOKEN_NUMER))

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


# -----------------------------------------------------------------------------
# Testy
# -----------------------------------------------------------------------------

def test_financial_layer() -> bool:
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}" + (f" -- {detail}" if detail else ""))
            failed += 1

    print("=== test_financial_layer ===\n")

    print("1. IBAN PL ze spacjami i bez:")
    state = PipelineState(
        text="konto: PL61 1090 1014 0000 0712 1981 2874, lub PL58325000032630362440455236",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state)
    check("PL61 usuniety", "PL61" not in state.text, f"text={state.text!r}")
    check("PL58 usuniety", "PL58" not in state.text, f"text={state.text!r}")
    check("Dwa tokeny", len(state.allocator.reverse_map) == 2,
          f"reverse_map={state.allocator.reverse_map}")

    print("\n2. IBAN DE -- ze spacjami i bez:")
    state2 = PipelineState(
        text="Konto DE: DE89 3704 0044 0532 0130 00 lub DE89370400440532013000",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state2)
    check("DE ze spacjami usuniety", "DE89 3704" not in state2.text,
          f"text={state2.text!r}")
    check("DE bez spacji usuniety", "DE89370400440532013000" not in state2.text,
          f"text={state2.text!r}")

    print("\n3. IBAN UA (Ukraina -- 29 znakow):")
    state3 = PipelineState(
        text="Odbiorca: UA213223130000026007233566001",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state3)
    check("UA usuniety", "UA21" not in state3.text, f"text={state3.text!r}")

    print("\n4. IBAN GB (z literami w BBAN):")
    state4 = PipelineState(
        text="Sort code: GB29 NWBK 6016 1331 9268 19",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state4)
    check("GB usuniety", "GB29" not in state4.text, f"text={state4.text!r}")

    print("\n5. Konto bez prefiksu PL (spacje):")
    state5 = PipelineState(
        text="Przelew na: 61 1090 1014 0000 0712 1981 2874",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state5)
    check("Konto bez PL usuniete",
          "1090 1014 0000 0712 1981 2874" not in state5.text,
          f"text={state5.text!r}")

    print("\n6. Deduplication -- ten sam IBAN dwa razy:")
    state6 = PipelineState(
        text="DE89370400440532013000 i DE89370400440532013000",
        allocator=TokenAllocator(),
    )
    apply_financial_layer(state6)
    check("Oba DE usuniete", "DE89" not in state6.text)
    check("Jeden token (dedup)", len(state6.allocator.reverse_map) == 1,
          f"reverse_map={state6.allocator.reverse_map}")

    print("\n7. Brak dopasowania -- tekst niezmieniony:")
    original = "Kwota: 1234 PLN, NIP: 855-019-31-23"
    state7 = PipelineState(text=original, allocator=TokenAllocator())
    apply_financial_layer(state7)
    check("Tekst niezmieniony", state7.text == original, f"text={state7.text!r}")
    check("reverse_map pusty", len(state7.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_financial_layer() else 1)
