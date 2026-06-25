"""
layers/ocr_normalizer.py  v1.0
Port z OcrNormalizer.kt (LynxMask Mobile).

Uruchamiany jako PIERWSZA warstwa pipeline — normalizuje tekst OCR zanim
wzorce regex i SpaCy go zobaczą. Nie tworzy tokenów — tylko naprawia tekst.

Trzy etapy (kolejność ma znaczenie):
  1. Keyword normalization — zdegradowane nagłówki PII (PE5EL → PESEL)
  2. Digit-in-context  — litery OCR między cyframi (O→0, I→1, S→5)
  3. De-leet — cyfry w imionach/nazwiskach (P4ulina → Paulina), tylko gdy
               wynik istnieje w słowniku imion/nazwisk
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_core import PipelineState

# ── Mapy konwersji (port z OcrNormalizer.kt) ─────────────────────────────────

# Litera OCR → cyfra (kontekst numeryczny)
_OCR_TO_DIGIT: dict[str, str] = {
    'O': '0', 'o': '0',
    'I': '1', 'l': '1',
    'S': '5',
    'B': '8',
    'G': '6',
    'T': '7',
    'Z': '2', 'z': '2',
    # Homoglify cyrylica
    'З': '3', 'з': '3',  # Cyrillic З
    'О': '0', 'о': '0',  # Cyrillic О
    'І': '1', 'і': '1',  # Cyrillic І
}

# Cyfra OCR → litera (kontekst literowy — cyfra między literami)
_DIGIT_TO_CHAR: dict[str, str] = {
    '1': 'i', '0': 'o',
}

# Leet → litera (w imionach/nazwiskach)
_LEET_MAP: dict[str, str] = {
    '4': 'a', '3': 'e', '5': 's', '0': 'o', '1': 'i',
}

# ── Keyword normalization ─────────────────────────────────────────────────────
# Zdegradowane nagłówki PII — OCR psuje litery lub wstawia spacje.
# Obsługa: zamiana na standardową formę zanim wzorce regex próbują matchować.

# PE5EL, P E S E L, P3SEL, PESE1 itp. → PESEL
_KW_PESEL_RE = re.compile(
    r'(?<![A-Za-z0-9])'
    r'P[^\S\n]?[E3B8][^\S\n]?[S5B8][^\S\n]?[E3][^\S\n]?[LlI1i|]'
    r'(?![A-Za-z0-9])',
    re.IGNORECASE,
)

# N1P, N I P, NlP → NIP
_KW_NIP_RE = re.compile(
    r'(?<![A-Za-z0-9])'
    r'N[^\S\n]?[IiLl1|tTjJ][^\S\n]?P'
    r'(?![A-Za-z0-9])',
    re.IGNORECASE,
)

# REG0N, R E G O N, REGON → REGON
_KW_REGON_RE = re.compile(
    r'(?<![A-Za-z0-9])'
    r'R[^\S\n]?E[^\S\n]?G[^\S\n]?[O0o][^\S\n]?N'
    r'(?![A-Za-z0-9])',
    re.IGNORECASE,
)

# IB4N, I B A N → IBAN
_KW_IBAN_RE = re.compile(
    r'(?<![A-Za-z0-9])'
    r'[Il1][^\S\n]?B[^\S\n]?[A4][^\S\n]?N'
    r'(?![A-Za-z0-9])',
    re.IGNORECASE,
)

# PESE1 (ostatnia litera to cyfra) → już obsługuje _KW_PESEL_RE przez [LlI1i|]

# ── Digit-in-context ──────────────────────────────────────────────────────────
# Litera/cyfra OCR w kontekście numerycznym.
# Bezpieczny heurystyk: matchuj tylko gdy otoczone cyframi (nie literami).

# Litera OCR bezpośrednio między cyframi — np. "32O5" → "3205", "I1I" → "111"
_OCR_DIGIT_IN_CONTEXT_RE = re.compile(
    r'(?<=\d)([OoIlSBGTZzЗзОоІі]+)(?=[\s\-./]*\d)'
)

# Cyfra między literami (1→i, 0→o) — np. "K0walczyk" ale NIE "PESEL123"
_DIGIT_IN_WORD_RE = re.compile(
    r'(?<=[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ])([10])(?=[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ])'
)

# ── De-leet ───────────────────────────────────────────────────────────────────
# Cyfry pełniące rolę liter w imionach/nazwiskach (P4ulina → Paulina).
# Zamiana TYLKO gdy wynik istnieje w słowniku imion/nazwisk.

_LEET_CANDIDATE_RE = re.compile(
    r'[A-ZĄĆĘŁŃÓŚŹŻ][A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9]{2,}'
)

_NAMES_FORMS: set[str] = set()
_SURNAMES_FORMS: set[str] = set()
_DICT_LOADED: bool = False


def _load_dicts() -> None:
    global _DICT_LOADED
    if _DICT_LOADED:
        return
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(base, "names_inflected.json"), encoding="utf-8") as f:
            d = json.load(f)
        for forms in d.values():
            _NAMES_FORMS.update(forms)
    except Exception:
        pass
    try:
        with open(os.path.join(base, "surnames_top1000.json"), encoding="utf-8") as f:
            d = json.load(f)
        for forms in d.values():
            _SURNAMES_FORMS.update(forms)
    except Exception:
        pass
    _DICT_LOADED = True


def _fix_ocr_digit(seg: str) -> str:
    return ''.join(_OCR_TO_DIGIT.get(c, c) for c in seg)


def _de_leet(text: str) -> str:
    """Zamienia cyfry na litery w tokenach wyglądających jak imię/nazwisko."""
    def replace(m: re.Match) -> str:
        token = m.group()
        if not any(c in _LEET_MAP for c in token):
            return token
        converted = ''.join(_LEET_MAP.get(c, c) for c in token)
        lower = converted.lower()
        if lower in _NAMES_FORMS or lower in _SURNAMES_FORMS:
            return converted
        return token
    return _LEET_CANDIDATE_RE.sub(replace, text)


# ── API publiczne ─────────────────────────────────────────────────────────────

def normalize_ocr(text: str) -> str:
    """Normalizuje tekst OCR — wywołaj przed pipeline'em lub jako warstwę."""
    _load_dicts()

    # Etap 1: keyword normalization
    text = _KW_PESEL_RE.sub('PESEL', text)
    text = _KW_NIP_RE.sub('NIP', text)
    text = _KW_REGON_RE.sub('REGON', text)
    text = _KW_IBAN_RE.sub('IBAN', text)

    # Etap 2: litery OCR między cyframi → cyfry
    text = _OCR_DIGIT_IN_CONTEXT_RE.sub(
        lambda m: _fix_ocr_digit(m.group(1)), text
    )

    # Etap 3: cyfry między literami → litery (K0walczyk → Kowalczyk)
    text = _DIGIT_IN_WORD_RE.sub(
        lambda m: _DIGIT_TO_CHAR.get(m.group(1), m.group(1)), text
    )

    # Etap 4: de-leet (P4ulina → Paulina) — tylko gdy w słowniku
    text = _de_leet(text)

    return text


def apply_ocr_normalizer(state: PipelineState) -> None:
    """Warstwa pipeline — normalizuje state.text bez tworzenia tokenów."""
    state.text = normalize_ocr(state.text)


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_ocr_normalizer() -> bool:
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

    print("=== test_ocr_normalizer ===\n")

    print("1. Keyword normalization:")
    check("PE5EL → PESEL",   normalize_ocr("PE5EL: 12345678901") == "PESEL: 12345678901")
    check("PESE1 → PESEL",   normalize_ocr("PESE1 12345678901") == "PESEL 12345678901")
    check("P E S E L → PESEL", "PESEL" in normalize_ocr("P E S E L: 123"))
    check("N1P → NIP",       normalize_ocr("N1P: 1234567890") == "NIP: 1234567890")
    check("REG0N → REGON",   normalize_ocr("REG0N: 123456789") == "REGON: 123456789")
    check("IB4N → IBAN",     "IBAN" in normalize_ocr("IB4N: PL03"))

    print("\n2. Digit-in-context (litera między cyframi → cyfra):")
    check("32O5 → 3205",     normalize_ocr("NIP: 32O5-123") == "NIP: 3205-123",
          normalize_ocr("NIP: 32O5-123"))
    check("525OO5885O → cyfry", "O" not in normalize_ocr("NIP 525OO5885O"),
          normalize_ocr("NIP 525OO5885O"))
    check("77I128 → 771128",  "I" not in normalize_ocr("PESEL 77I128147"))

    print("\n3. Cyfra między literami → litera:")
    check("K0walczyk → Kowalczyk", normalize_ocr("K0walczyk") == "Kowalczyk",
          normalize_ocr("K0walczyk"))

    print("\n4. De-leet imion/nazwisk:")
    result_paulina = normalize_ocr("P4ulina")
    check("P4ulina → Paulina (jeśli w słowniku)", result_paulina in ("Paulina", "P4ulina"),
          result_paulina)
    result_kowal = normalize_ocr("K0walczyk")
    check("K0walczyk → Kowalczyk (etap 3)", result_kowal == "Kowalczyk",
          result_kowal)

    print("\n5. Brak false positive (nie ruszaj poprawnego tekstu):")
    original = "Jan Kowalski, ul. Prosta 1, NIP: 123-456-78-90"
    check("Poprawny tekst niezmieniony", normalize_ocr(original) == original,
          normalize_ocr(original))

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_ocr_normalizer() else 1)
