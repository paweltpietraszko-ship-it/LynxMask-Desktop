"""
layers/contact.py  v1.2
Warstwa contact — email i telefon.
v1.2: [NUMER-RECALL-EMAIL] OCR-tolerancyjne wykrywanie emaila:
  - spacja/newline wokol @ (OCR rozrywa wiersz w miejscu @)
  - © jako @ (OCR myli znak)
  - przecinek jako kropka w TLD (gmail,com)
  - wartość kanoniczna w reverse_map = email po normalizacji (bez smieci OCR)
  Wzorzec _EMAIL_OCR_RE stosowany PRZED standardowym — lapiemy rozbite emaile.
v1.1: [NUMER-RECALL] Dodano _PHONE_CONTEXT_RE — telefon po slowie kluczowym
  (tel./kom./mob./fax/phone) wykrywany osobno, z wyzszym priorytetem niz REGON.
  Rozwiazuje kolizje: 9-cyfrowy numer komorkowy bez separatorow = REGON w identity.
  Nowy wzorzec akceptuje tez separatory kropkowe (501.234.567) i nawias (22)123-45-67.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer_init import STRUCTURAL_PATTERNS, TOKEN_EMAIL, TOKEN_NUMER
from pipeline_core import PipelineState, TokenAllocator

_CONTACT_EMAIL_PATTERNS: list[tuple[str, re.Pattern]] = [
    (tok, pat) for tok, pat in STRUCTURAL_PATTERNS if tok == TOKEN_EMAIL
]

_CONTACT_PHONE_PATTERNS: list[tuple[str, re.Pattern]] = [
    (tok, pat) for tok, pat in STRUCTURAL_PATTERNS
    if tok == TOKEN_NUMER and r"\+?48" in pat.pattern
]

_CONTACT_PATTERNS = _CONTACT_EMAIL_PATTERNS + _CONTACT_PHONE_PATTERNS

# [NUMER-RECALL] Telefon po slowie kluczowym — wyzszy priorytet niz REGON.
_PHONE_CONTEXT_RE = re.compile(
    r"(?:tel\.?|fax\.?|kom\.?|mob\.?|phone|Tel\.?|Fax\.?|Kom\.?|Mob\.?)"
    r"[\s:]*"
    r"(?:\+?48[\s\-.]?)?"
    r"\(?\d{2,3}\)?[\s\-.]?\d{3}[\s\-.]?\d{2}[\s\-.]?\d{2}"
    r"|"
    r"(?:tel\.?|fax\.?|kom\.?|mob\.?|phone|Tel\.?|Fax\.?|Kom\.?|Mob\.?)"
    r"[\s:]*"
    r"(?:\+?48[\s\-.]?)?"
    r"\d{3}[\s\-.]?\d{3}[\s\-.]?\d{3}",
    re.IGNORECASE,
)

# [NUMER-RECALL-EMAIL] OCR-tolerancyjny email:
# - czesc lokalna: normalne znaki emaila
# - wokol @: do 2 znakow bialych (spacja/tab/newline) lub © zamiast @
# - domena: normalna, ale z opcjonalna bialymi spacjami
# - TLD: przecinek lub kropka jako separator, 2-6 liter
_EMAIL_OCR_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]{2,}"       # czesc lokalna
    r"[ \t\n]{0,2}"                 # OCR: spacja/newline przed @
    r"[@©]"                    # @ lub © (OCR mylka)
    r"[ \t\n]{0,2}"                 # OCR: spacja/newline po @
    r"[a-zA-Z0-9.\-]{2,}"          # domena
    r"[ \t]{0,1}[.,][ \t]{0,1}"    # TLD separator — kropka lub przecinek
    r"[a-zA-Z]{2,6}",              # TLD
    re.IGNORECASE,
)

# Normalizacja emaila po OCR: usun biale znaki wokol @, © -> @, przecinek -> kropka w TLD
_AT_NOISE_RE   = re.compile(r"[ \t\n]{0,2}[@©][ \t\n]{0,2}")
_TLD_COMMA_RE  = re.compile(r"[ \t]{0,1},[ \t]{0,1}([a-zA-Z]{2,6})$", re.IGNORECASE)
_TLD_SPACE_RE  = re.compile(r"[ \t]{0,1}\.[ \t]{0,1}([a-zA-Z]{2,6})$", re.IGNORECASE)


def _normalize_email(raw: str) -> str:
    """Zwraca kanoniczna forme emaila — usuwa smieci OCR."""
    result = _AT_NOISE_RE.sub("@", raw, count=1)
    result = _TLD_COMMA_RE.sub(r".\1", result)
    result = _TLD_SPACE_RE.sub(r".\1", result)
    return result.strip()


def apply_contact_layer(state: PipelineState) -> None:
    """Stosuje wzorce email i telefon na state.text."""
    hits: list[tuple[int, int, str, str]] = []

    # OCR-tolerancyjny email — najpierw, by zajac span (szerszy) przed standardowym
    for m in _EMAIL_OCR_RE.finditer(state.text):
        canonical = _normalize_email(m.group(0))
        if "@" in canonical:   # odrzuc jesli normalizacja nie dala poprawnego emaila
            hits.append((m.start(), m.end(), canonical, TOKEN_EMAIL))

    # [NUMER-RECALL] Context-aware telefon — przed REGON
    for m in _PHONE_CONTEXT_RE.finditer(state.text):
        hits.append((m.start(), m.end(), m.group(0), TOKEN_NUMER))

    for token_type, pat in _CONTACT_PATTERNS:
        for m in pat.finditer(state.text):
            hits.append((m.start(), m.end(), m.group(0), token_type))

    # Wiekszy span wygrywa (tak jak w address.py v1.8)
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

def test_contact_layer() -> bool:
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

    print("=== test_contact_layer ===\n")

    print("1. Komorkowy + stacjonarny + email (podstawowy):")
    state = PipelineState(
        text="tel. +48 600 123 456, fax 22 123 45 67, jan@firma.pl",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state)
    check("Telefon komorkowy usuniety", "600 123 456" not in state.text)
    check("Telefon stacjonarny usuniety", "22 123 45 67" not in state.text)
    check("Email usuniety", "jan@firma.pl" not in state.text)
    rm = state.allocator.reverse_map
    check("EMAIL_NNN w reverse_map", any(k.startswith("EMAIL_") for k in rm))
    check("NUMER_NNN w reverse_map", any(k.startswith("NUMER_") for k in rm))

    print("\n2. OCR-rozbity email — spacja przed @:")
    state2 = PipelineState(
        text="kontakt: jan.kowalski @gmail.com",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state2)
    check("Email z SPacja przed @ usuniety", "jan.kowalski" not in state2.text,
          f"text={state2.text!r}")
    rm2 = state2.allocator.reverse_map
    check("Kanoniczny email w reverse_map",
          any("@" in v for v in rm2.values()),
          f"values={list(rm2.values())}")

    print("\n3. OCR-rozbity email — spacja po @:")
    state3 = PipelineState(
        text="e-mail: jan.kowalski@ gmail.com",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state3)
    check("Email z SPacja po @ usuniety", "gmail.com" not in state3.text,
          f"text={state3.text!r}")

    print("\n4. OCR-rozbity email — (c) zamiast @:")
    state4 = PipelineState(
        text="kontakt jan.kowalski©gmail.com",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state4)
    check("Email z (c) zamiast @ usuniety", "gmail.com" not in state4.text,
          f"text={state4.text!r}")
    rm4 = state4.allocator.reverse_map
    check("Kanoniczny @ w wartosci tokenu",
          any("@" in v for v in rm4.values()),
          f"values={list(rm4.values())}")

    print("\n5. OCR-rozbity email — newline przed @:")
    state5 = PipelineState(
        text="jan.kowalski\n@gmail.com",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state5)
    check("Email z newline przed @ usuniety", "gmail.com" not in state5.text,
          f"text={state5.text!r}")

    print("\n6. OCR-rozbity email — przecinek jako kropka w TLD:")
    state6 = PipelineState(
        text="e-mail: jan.kowalski@gmail,com",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state6)
    check("Email z przecinkiem w TLD usuniety", "gmail,com" not in state6.text,
          f"text={state6.text!r}")

    print("\n7. Deduplication — ten sam email dwa razy:")
    state7 = PipelineState(
        text="kontakt: jan@firma.pl lub jan@firma.pl",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state7)
    check("Email usuniety", "jan@firma.pl" not in state7.text)
    rm7 = state7.allocator.reverse_map
    check("Jeden token EMAIL (dedup)", len(rm7) == 1, f"reverse_map={rm7}")

    print("\n8. Brak dopasowania — tekst niezmieniony:")
    original = "Zwykly tekst bez kontaktow."
    state8 = PipelineState(text=original, allocator=TokenAllocator())
    apply_contact_layer(state8)
    check("Tekst niezmieniony", state8.text == original)
    check("reverse_map pusty", len(state8.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_contact_layer() else 1)
