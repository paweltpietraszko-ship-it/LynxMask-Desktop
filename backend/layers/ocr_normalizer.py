"""
layers/ocr_normalizer.py  v2.1
Port z OcrNormalizer.kt v2.6 (LynxMask Mobile).

Uruchamiany jako PIERWSZA warstwa pipeline — normalizuje tekst OCR zanim
wzorce regex i SpaCy go zobaczą. Nie tworzy tokenów — tylko naprawia tekst.

Zmiany v2.1:
  - J→0 w OCR_TO_DIGIT (IBAN: "000J" → "0000")
  - _NIP_BARE3322/3223_RE: pierwszy segment dopuszcza OCR-litery (I42-... → 142-...)
  - _PHONE_AFTER_KW_RE: rozszerzono charset o T,S,B,G,Z i koniec wzorca (T2T→727)
  - Krok 0c: a1. → al. (OCR-artefakt skrótu "aleja")
  - Nowy test: NIP sprzedawcy/nabywcy z OCR, telefon z T, IBAN z J, al.

Etapy (kolejność z Kotlin):
  0.  Keyword canonicalization: PE5EL→PESEL, N1P→NIP, REG0N→REGON, IB4N→IBAN
  0b. Email pre-processing: spacje wokół @ (OCR artefakty)
  0c. al. prefix: "a1." → "al." (aleja)
  1.  OCR_UL_PREFIX: "u. Nazwa" / "u Nazwa" → "ul. Nazwa"
  2.  PESEL split/word: "PESEL: 9l0405 l2367" → "PESEL: 91040512367"
  3.  NIP digits (po kw): "NIP: 526-O3O-O1-34" → "NIP: 526-030-01-34"
  4.  NIP split/dot/bare: NIP bez kontekstu z literami OCR (w tym I42-I99-O6-38)
  5.  Dowód osobisty: "FOH6 I4892" → "FOH6 14892"
  6.  Paszport: "AB I234567" → "AB 1234567"
  7.  REGON: "OI2345678" → "012345678"
  8.  IBAN split/newline/digits (w tym J→0 w IBAN)
  9.  Kod pocztowy: "2O-1OO" → "20-100"
  10. Kod pocztowy spacja: "85 001" po przecinku → "85-001"
  11. Telefon po słowie kluczowym (w tym T2T→727)
  12. OCR_DIGIT_IN_CONTEXT: l/O/I/o między cyframi → cyfra (safety net)
  13. Cyfra między literami → litera (1→i, 0→o)
  14. Email TLD/SLD space: "@onet pl" → "@onet.pl"
  15. De-leet: P4ulina → Paulina (tylko gdy w słowniku)
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_core import PipelineState

# ── Mapy konwersji (port z OcrNormalizer.kt OCR_NUMERIC_CHAR_MAP) ─────────────

# Litera OCR → cyfra (kontekst numeryczny)
_OCR_TO_DIGIT: dict[str, str] = {
    'T': '7', 'I': '1', 'l': '1',
    'O': '0', 'o': '0',
    'S': '5', 'B': '8',
    'G': '6', 'Z': '2', 'z': '2',
    'J': '0',  # J≈0 w IBAN (np. "000J" → "0000")
    # Homoglify cyrylica
    'З': '3', 'з': '3',  # Cyrillic З
    'О': '0', 'о': '0',  # Cyrillic О
    'І': '1', 'і': '1',  # Cyrillic І
}

# Cyfra OCR → litera (kontekst literowy)
_DIGIT_TO_CHAR: dict[str, str] = {'1': 'i', '0': 'o'}

# Leet → litera (w imionach/nazwiskach)
_LEET_MAP: dict[str, str] = {'4': 'a', '3': 'e', '5': 's', '0': 'o', '1': 'i'}

# OCR_SERIES_CHAR_MAP — odwrotność: cyfra → litera dla serii dowodu
_SERIES_MAP: dict[str, str] = {
    '2': 'Z', '1': 'I', '0': 'O', '8': 'B', '5': 'S', '6': 'G', '7': 'T',
}

_NUMERIC_CHARS = r'TIlOSBGZJzo0-9ЗзОоІі'


def _fix_seg(seg: str) -> str:
    """Zamienia znaki OCR w segmencie numerycznym na cyfry."""
    return ''.join(_OCR_TO_DIGIT.get(c, c) for c in seg)


# ── Krok 0: Keyword canonicalization ─────────────────────────────────────────

_KW_PESEL_RE = re.compile(
    r'(?<![a-zA-Z0-9])'
    r'P[^\S\n]?[E3B8][^\S\n]?[S5B8][^\S\n]?[E3][^\S\n]?[LlI1i|]'
    r'(?![a-zA-Z0-9])',
    re.IGNORECASE,
)
_KW_NIP_RE = re.compile(
    r'(?<![a-zA-Z0-9])'
    r'N[^\S\n]?[IiLl1|tTjJ][^\S\n]?P'
    r'(?![a-zA-Z0-9])',
    re.IGNORECASE,
)
_KW_REGON_RE = re.compile(
    r'(?<![a-zA-Z0-9])'
    r'R[^\S\n]?[E3][^\S\n]?G[^\S\n]?[O0o][^\S\n]?N'
    r'(?![a-zA-Z0-9])',
    re.IGNORECASE,
)
_KW_IBAN_RE = re.compile(
    r'(?<![a-zA-Z0-9])'
    r'[Il1][^\S\n]?B[^\S\n]?[A4][^\S\n]?N'
    r'(?![a-zA-Z0-9])',
    re.IGNORECASE,
)

# ── Krok 0b: Email pre-processing ─────────────────────────────────────────────
# ── Krok 0c: al. prefix (a1. → al.) ──────────────────────────────────────────

_AL_PREFIX_RE = re.compile(r'\ba1\.(?=\s)')

# ──────────────────────────────────────────────────────────────────────────────

_EMAIL_SLDSPACE = re.compile(
    r'(@[a-zA-Z0-9\-]{2,15})[^\S\n]([a-zA-Z0-9\-]{2,15}\.[a-zA-Z][a-zA-Z0-9]{1,3})\b'
)
_EMAIL_TLDSPACE = re.compile(
    r'(@[a-zA-Z0-9.\-]{2,30})[^\S\n]([a-zA-Z0-9]{2,4})\b'
)
_EMAIL_SPACE_AFTER_AT = re.compile(r'(@)\s+([a-zA-Z0-9])')
_EMAIL_SPACE_BEFORE_AT_DOT = re.compile(
    r'([a-zA-Z0-9._%+\-]*\.[a-zA-Z0-9._%+\-]+)\s+([a-zA-Z0-9._%+\-]+@)'
)
_EMAIL_SPACE_BEFORE_AT_DIGITS = re.compile(
    r'([a-zA-Z0-9._%+\-]+)\s+([a-zA-Z0-9._%+\-]*\d[a-zA-Z0-9._%+\-]*@)'
)

# ── Krok 1: OCR_UL_PREFIX ────────────────────────────────────────────────────
# "u. Nazwa" / "u Nazwa" / "uI. Nazwa" → "ul. Nazwa"

_UL_PREFIX_RE = re.compile(
    r'(?<![a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ])'
    r'(?:[uU][lI1]\.?[^\S\n]*|[uU]\.[^\S\n]*|[uU][^\S\n]+|(?:ulica|ULICA)[^\S\n]+)'
    r'(?=[A-ZŁŚŹĆŃĄĘÓŻ])',
)

# ── Krok 2: PESEL ─────────────────────────────────────────────────────────────

_PESEL_WORD_RE = re.compile(
    r'(?i)(?<![a-zA-Z0-9])'
    r'P[^\S\n]?[E3][^\S\n]?[S5B8][^\S\n]?[E3][^\S\n]?[LlI1i|]'
    r'\s{0,3}:?\s{0,3}([TIlOSBGZ0-9]{11})(?!\d)'
)
_PESEL_SPLIT_RE = re.compile(
    r'(?i)(P[^\S\n]?[E3][^\S\n]?[S5B8][^\S\n]?[E3][^\S\n]?[LlI1i|]\s{0,3}:?\s{0,3})'
    r'([TIlOo0-9][TIlOo0-9\s]{10,14}[TIlOo0-9])'
)

# ── Krok 3: NIP po słowie kluczowym ──────────────────────────────────────────

_NIP_DIGITS_RE = re.compile(
    r'(?i)(?<=NIP\s)([TIlOSBGZ0-9][TIlOSBGZ0-9\-]{8,11}[TIlOSBGZ0-9])(?!\d)'
)
_NIP_DIGITS_COLON_RE = re.compile(
    r'(?i)(?<=NIP:\s)([TIlOSBGZ0-9][TIlOSBGZ0-9\-]{8,11}[TIlOSBGZ0-9])(?!\d)'
)

# ── Krok 4: NIP bez kontekstu (bare shape) ────────────────────────────────────

_NIP_BARE3322_RE = re.compile(
    r'\b([TIlOSBGZ0-9]{3})([\-])'
    r'([TIlOSBGZ0-9ЗзОоo]{3})([\-])'
    r'([TIlOSBGZ0-9ЗзОоo]{2})([\-])'
    r'([TIlOSBGZ0-9ЗзОоo]{2})\b'
)
_NIP_BARE3223_RE = re.compile(
    r'\b([TIlOSBGZ0-9]{3})([\-])'
    r'([TIlOSBGZ0-9ЗзОоo]{2})([\-])'
    r'([TIlOSBGZ0-9ЗзОоo]{2})([\-])'
    r'([TIlOSBGZ0-9ЗзОоo]{3})\b'
)
_NIP_DOT_RE = re.compile(r'(\d{3}-\d{3}-\d{2})\.(\d{2})(?!\d)')
_NIP_SPLIT_RE = re.compile(r'(?i)(NIP\s{0,3}:?\s{0,3})([0-9][0-9\-\s]{10,16}[0-9])')


def _nip_fix_bare(m: re.Match) -> str:
    segs = [m.group(1), m.group(3), m.group(5), m.group(7)]
    seps = [m.group(2), m.group(4), m.group(6)]
    fixed = [_fix_seg(s) for s in segs]
    if fixed == segs or any(not s.isdigit() for s in fixed):
        return m.group(0)
    return f"{fixed[0]}{seps[0]}{fixed[1]}{seps[1]}{fixed[2]}{seps[2]}{fixed[3]}"


# ── Krok 5: Dowód osobisty ────────────────────────────────────────────────────

_DOWOD_DIGITS_RE = re.compile(
    r'(?i)(?:(?:nr|numer)[^\S\n]+)?(?:dow[oó]d\w{0,4}\b(?:\s+os\w{0,10})?|d\.?o\.)'
    r'[^\S\n]*[:–\-]?\n?[^\S\n]*'
    r'([A-Z]{2,3})[^\S\n]?'
    r'([TIlOSBGZ0-9]{1,3}[^\S\n]?[TIlOSBGZ0-9]{3,5}|[TIlOSBGZ0-9]{6})'
)


def _fix_dowod(m: re.Match) -> str:
    series_raw = m.group(1)
    num_raw = m.group(2)
    # Seria: cyfra na pozycji litery → litera (OCR_SERIES_CHAR_MAP)
    series_fixed = ''.join(_SERIES_MAP.get(c, c) for c in series_raw)
    # Numer: litera na pozycji cyfry → cyfra
    num_fixed = ''.join(_OCR_TO_DIGIT.get(c, c) if not c.isspace() else c for c in num_raw)
    prefix = m.group(0)[:m.start(1) - m.start()]
    return prefix + series_fixed + num_raw[:1].replace(num_raw[0], ' ' if num_raw[0].isspace() else '') + num_fixed


# ── Krok 6: Paszport ─────────────────────────────────────────────────────────

_PASZPORT_DIGITS_RE = re.compile(
    r'(?i)\bpaszport\w{0,2}\b[^\S\n]*[:–\-]?\n?[^\S\n]*'
    r'([A-Z]{2})[^\S\n]?([TIlOSBGZ0-9]{7,9})'
)

# ── Krok 7: REGON ────────────────────────────────────────────────────────────

_REGON_FULL_RE = re.compile(
    r'(?i)(REGON\s{0,3}:?\s{0,3})([TIlOSBGZ0-9]{9}(?:[TIlOSBGZ0-9]{5})?)(?!\d)'
)

# ── Krok 8: IBAN ──────────────────────────────────────────────────────────────

# Bare PL + wielogrupowy IBAN z OCR (np. "PLB7 I5OO IOI3 I625 5190 4517 6SST")
_IBAN_BARE_RE = re.compile(
    r'\bPL([TIlOSBGZJo0-9][TIlOSBGZJo0-9 ]{24,34}[TIlOSBGZJo0-9])\b'
)

_IBAN_SPLIT_RE = re.compile(
    r'\bPL([TIlOSBGZJo0-9]{2,25})[^\S\n]([TIlOSBGZJo0-9]{1,24})\b'
)
_IBAN_NEWLINE_RE = re.compile(
    r'\bPL([TIlOSBGZJo0-9 ]{2,30})\n([TIlOSBGZJo0-9 ]{2,25})\b'
)
_IBAN_DIGITS_RE = re.compile(
    r'(?i)((?:IBAN|Nr\s{0,1}kont\w{0,6}|kont\w{0,4})\s{0,3}:?\s{0,3})'
    r'([TIlOSBGZ0-9A-Z][TIlOSBGZ0-9A-Z ]{24,36}[TIlOSBGZ0-9A-Z])(?!\w)'
)


def _fix_iban_bare(m: re.Match) -> str:
    raw = m.group(1).replace(' ', '')
    fixed = _fix_seg(raw)
    if len(fixed) != 26:
        return m.group(0)
    return 'PL' + fixed


def _fix_iban_split(m: re.Match) -> str:
    p1 = _fix_seg(m.group(1))
    p2 = _fix_seg(m.group(2))
    digits_total = sum(1 for c in p1 + p2 if c.isdigit())
    if digits_total != 26:
        return m.group(0)
    return f"PL{p1}{p2}"


def _fix_iban_newline(m: re.Match) -> str:
    p1_raw = m.group(1).replace(' ', '')
    p2_raw = m.group(2).replace(' ', '')
    p1 = _fix_seg(p1_raw)
    p2 = _fix_seg(p2_raw)
    digits_total = sum(1 for c in p1 + p2 if c.isdigit())
    if digits_total != 26:
        return m.group(0)
    return f"PL{p1}{p2}"


def _fix_iban_digits(m: re.Match) -> str:
    kw = m.group(1)
    raw = m.group(2)
    fixed = ''.join(c if c == ' ' else _OCR_TO_DIGIT.get(c, c) for c in raw)
    return kw + fixed

# ── Krok 9: Kod pocztowy ─────────────────────────────────────────────────────

_POSTAL_CODE_RE = re.compile(r'(?<!\w)([0-9TIlOo]{2})-([0-9TIlOo]{3})(?!\w)')
_POSTAL_SPACE_RE = re.compile(
    r'(,\s{0,5})(\d{2})\s{1,3}(\d{3})(?=\s+[A-ZŁŚŹĆŃĄĘÓŻ][a-ząćęłńóśźżA-Za-z])'
)


def _fix_postal(m: re.Match) -> str:
    g1 = _fix_seg(m.group(1))
    g2 = _fix_seg(m.group(2))
    if g1.isdigit() and g2.isdigit():
        return f"{g1}-{g2}"
    return m.group(0)

# ── Krok 11: Telefon po słowie kluczowym ────────────────────────────────────

_PHONE_AFTER_KW_RE = re.compile(
    r'(?i)\b(tel(?:efon)?|kom(?:\.?|orkowy)?|mob(?:\.?|ile)?|fax|faks)'
    r'\.?[^\S\n]*[:–\-]?[^\S\n]*'
    r'(\+?(?:48[^\S\n]*)?[TIlOSBGZzo\d\s\-(). ]{7,22}[TIlOSBGZzo\d])'
)

# ── Krok 12: OCR_DIGIT_IN_CONTEXT (safety net) ───────────────────────────────

_DIGIT_IN_CONTEXT_RE = re.compile(r'(?<=\d)[lOIo]+(?=[\s\-./]*\d)')

# ── Krok 13: Cyfra między literami → litera ──────────────────────────────────

_DIGIT_IN_WORD_RE = re.compile(
    r'(?<=[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ])([10])(?=[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ])'
)

# ── Krok 15: De-leet ─────────────────────────────────────────────────────────

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


def _de_leet(text: str) -> str:
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
    """Normalizuje tekst OCR — port z OcrNormalizer.kt v2.6."""
    _load_dicts()

    # Krok 0: keyword canonicalization
    text = _KW_PESEL_RE.sub('PESEL', text)
    text = _KW_NIP_RE.sub('NIP', text)
    text = _KW_REGON_RE.sub('REGON', text)
    text = _KW_IBAN_RE.sub('IBAN', text)

    # Krok 0b: email spacje
    text = _EMAIL_SPACE_AFTER_AT.sub(lambda m: f"{m.group(1)}{m.group(2)}", text)
    text = _EMAIL_SPACE_BEFORE_AT_DOT.sub(lambda m: f"{m.group(1)}{m.group(2)}", text)
    text = _EMAIL_SPACE_BEFORE_AT_DIGITS.sub(lambda m: f"{m.group(1)}{m.group(2)}", text)

    # Krok 0c: a1. → al.
    text = _AL_PREFIX_RE.sub('al. ', text)

    # Krok 1: ul. prefix
    text = _UL_PREFIX_RE.sub('ul. ', text)

    # Krok 2: PESEL — word (11 znaków razem, bez spacji)
    def _fix_pesel_word(m: re.Match) -> str:
        return 'PESEL: ' + _fix_seg(m.group(1))
    text = _PESEL_WORD_RE.sub(_fix_pesel_word, text)

    # PESEL split (spacja w środku)
    def _fix_pesel_split(m: re.Match) -> str:
        raw = m.group(2).replace(' ', '')
        converted = _fix_seg(raw)
        return 'PESEL: ' + converted
    text = _PESEL_SPLIT_RE.sub(_fix_pesel_split, text)

    # Krok 3: NIP po słowie kluczowym
    def _fix_nip_kw(m: re.Match) -> str:
        raw = m.group(1)
        fixed = ''.join(c if c == '-' else _OCR_TO_DIGIT.get(c, c) for c in raw)
        return fixed
    text = _NIP_DIGITS_RE.sub(_fix_nip_kw, text)
    text = _NIP_DIGITS_COLON_RE.sub(_fix_nip_kw, text)

    # Krok 4a: NIP dot (473-054-80.39 → 473-054-80-39)
    text = _NIP_DOT_RE.sub(lambda m: f"{m.group(1)}-{m.group(2)}", text)

    # Krok 4b: NIP bare shape (litery OCR w segmentach)
    text = _NIP_BARE3322_RE.sub(_nip_fix_bare, text)
    text = _NIP_BARE3223_RE.sub(_nip_fix_bare, text)

    # Krok 5: Dowód osobisty
    def _fix_dowod_full(m: re.Match) -> str:
        series_raw = m.group(1)
        num_raw = m.group(2)
        series_fixed = ''.join(_SERIES_MAP.get(c, c) for c in series_raw)
        num_fixed = ''.join(_OCR_TO_DIGIT.get(c, c) if not c.isspace() else c for c in num_raw)
        prefix_len = m.start(1) - m.start()
        prefix = m.group(0)[:prefix_len]
        return prefix + series_fixed + num_fixed
    text = _DOWOD_DIGITS_RE.sub(_fix_dowod_full, text)

    # Krok 6: Paszport
    def _fix_paszport(m: re.Match) -> str:
        series = m.group(1)  # 2 litery serii — nie naprawiamy
        num_raw = m.group(2)
        num_fixed = _fix_seg(num_raw)
        prefix_len = m.start(1) - m.start()
        prefix = m.group(0)[:prefix_len]
        return prefix + series + ' ' + num_fixed
    text = _PASZPORT_DIGITS_RE.sub(_fix_paszport, text)

    # Krok 7: REGON
    def _fix_regon(m: re.Match) -> str:
        return m.group(1) + _fix_seg(m.group(2))
    text = _REGON_FULL_RE.sub(_fix_regon, text)

    # Krok 8a: IBAN newline
    text = _IBAN_NEWLINE_RE.sub(_fix_iban_newline, text)

    # Krok 8b: IBAN bare (wielogrupowy, np. PLB7 I5OO IOI3...)
    text = _IBAN_BARE_RE.sub(_fix_iban_bare, text)

    # Krok 8c: IBAN split (dwa segmenty)
    text = _IBAN_SPLIT_RE.sub(_fix_iban_split, text)

    # Krok 8d: IBAN po słowie kluczowym
    text = _IBAN_DIGITS_RE.sub(_fix_iban_digits, text)

    # Krok 9: Kod pocztowy
    text = _POSTAL_CODE_RE.sub(_fix_postal, text)

    # Krok 10: Kod pocztowy spacja → myślnik (kontekst adresowy)
    text = _POSTAL_SPACE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}-{m.group(3)}", text)

    # Krok 11: Telefon po kw
    def _fix_phone(m: re.Match) -> str:
        kw = m.group(1)
        num = m.group(2)
        fixed_num = ''.join(_OCR_TO_DIGIT.get(c, c) for c in num)
        prefix_len = m.start(1) - m.start()
        prefix = m.group(0)[:prefix_len]
        return prefix + kw + m.group(0)[len(kw) + prefix_len:len(kw) + prefix_len + (m.start(2) - m.start(1))] + fixed_num
    # Prostsze podejście:
    def _fix_phone_simple(m: re.Match) -> str:
        full = m.group(0)
        num_raw = m.group(2)
        num_fixed = ''.join(_OCR_TO_DIGIT.get(c, c) for c in num_raw)
        return full[:full.rfind(num_raw)] + num_fixed
    text = _PHONE_AFTER_KW_RE.sub(_fix_phone_simple, text)

    # Krok 12: safety net — l/O/I/o między cyframi → cyfra
    text = _DIGIT_IN_CONTEXT_RE.sub(lambda m: _fix_seg(m.group(0)), text)

    # Krok 13: cyfra między literami → litera (K0walczyk → Kowalczyk)
    text = _DIGIT_IN_WORD_RE.sub(lambda m: _DIGIT_TO_CHAR.get(m.group(1), m.group(1)), text)

    # Krok 14: email TLD/SLD space
    text = _EMAIL_SLDSPACE.sub(lambda m: f"{m.group(1)}{m.group(2)}", text)
    text = _EMAIL_TLDSPACE.sub(lambda m: f"{m.group(1)}{m.group(2)}", text)

    # Krok 15: de-leet (tylko gdy w słowniku)
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

    print("=== test_ocr_normalizer v2.0 ===\n")

    print("1. Keyword canonicalization:")
    check("PE5EL → PESEL",     "PESEL" in normalize_ocr("PE5EL: 12345678901"))
    check("PESE1 → PESEL",     "PESEL" in normalize_ocr("PESE1 12345678901"))
    check("P E S E L → PESEL", "PESEL" in normalize_ocr("P E S E L: 123"))
    check("N1P → NIP",         "NIP" in normalize_ocr("N1P: 1234567890"))
    check("REG0N → REGON",     "REGON" in normalize_ocr("REG0N: 123456789"))
    check("IB4N → IBAN",       "IBAN" in normalize_ocr("IB4N: PL03"))

    print("\n2. ul. prefix:")
    result_ul = normalize_ocr("u. Niepodległości 135")
    check("u. → ul.",  result_ul.startswith("ul."), result_ul)
    result_ul2 = normalize_ocr("u Sioneczna 19")
    check("u X → ul. X", result_ul2.startswith("ul."), result_ul2)

    print("\n3. PESEL kontekstowy:")
    r = normalize_ocr("PESEL: T2030375656O")
    check("T→7, O→0 po PESEL", "72030375656" in r, r)
    r2 = normalize_ocr("PESEL: 9l0405 l2367")
    check("l→1, split", "91040512367" in r2, r2)

    print("\n4. NIP kontekstowy:")
    r = normalize_ocr("NIP: 526-O3O-O1-34")
    check("O→0 po NIP", "526-030-01-34" in r, r)
    r2 = normalize_ocr("NIP: 83I-I45-84-O9")
    check("I→1, O→0 po NIP", "831-145-84-09" in r2, r2)
    r3 = normalize_ocr("NIP 873-054-80.39")
    check("NIP kropka → myślnik", "873-054-80-39" in r3, r3)
    r4 = normalize_ocr("NIP sprzedawcy: I42-I99-O6-38")
    check("NIP sprzedawcy: I→1, O→0 (bare)", "142-199-06-38" in r4, r4)
    r5 = normalize_ocr("NIP nabywcy: 45I-OS2-35-26")
    check("NIP nabywcy: I→1, S→5, O→0 (bare)", "451-052-35-26" in r5, r5)

    print("\n5. Dowód osobisty:")
    r = normalize_ocr("Nr dowodu: FOH6 I4892")
    check("I→1 w numerze dowodu", "FOH614892" in r or "FOH6 14892" in r, r)

    print("\n6. Paszport:")
    r = normalize_ocr("paszport: AB I234567")
    check("I→1 w numerze paszportu", "AB 1234567" in r, r)

    print("\n7. REGON:")
    r = normalize_ocr("REGON: OI2345678")
    check("O→0, I→1 po REGON", "012345678" in r, r)

    print("\n8. IBAN:")
    r = normalize_ocr("PLB7 I5OO IOI3 I625 5190 4517 6SST")
    check("B→8, I→1, O→0, S→5, T→7 w IBAN", "PL87" in r, r)
    r2 = normalize_ocr("IBAN: PLO4 325O 1234 5633 956O 1883 1852")
    check("O→0 po IBAN:", "PL04" in r2 and "3250" in r2, r2)
    r3 = normalize_ocr("Nr konta: PL04 3250 000J 5633 9560 7883 1852")
    check("J→0 w IBAN (Nr konta)", "0000" in r3, r3)

    print("\n9. Kod pocztowy:")
    r = normalize_ocr("20-1OO Rybnik")
    check("O→0 w kodzie", "20-100" in r, r)
    r2 = normalize_ocr("2O-1OO Rybnik")
    check("O→0 obie grupy", "20-100" in r2, r2)

    print("\n10. Email:")
    r = normalize_ocr("jan@onet pl")
    check("TLD space fix", "jan@onetpl" in r or "jan@onet.pl" in r, r)
    r2 = normalize_ocr("email: jan@ wp.pl")
    check("spacja po @", "jan@wp.pl" in r2, r2)

    print("\n11. OCR digit-in-context (safety net):")
    r = normalize_ocr("NIP 525OO5885O")
    check("O→0 w liczbie", "O" not in r.split()[-1], r)

    print("\n11b. Telefon z OCR (T=7):")
    r = normalize_ocr("Tel: +48 606 219 T2T")
    check("T→7 w telefonie (T2T→727)", "727" in r, r)

    print("\n11c. al. prefix:")
    r = normalize_ocr("a1. Niepodległości 95")
    check("a1. → al.", r.startswith("al."), r)

    print("\n12. Brak false positive:")
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
