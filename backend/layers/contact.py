"""
layers/contact.py  v1.1
Warstwa contact — email i telefon.
v1.1: [NUMER-RECALL] Dodano _PHONE_CONTEXT_RE — telefon po słowie kluczowym
  (tel./kom./mob./fax/phone) wykrywany osobno, z wyższym priorytetem niż REGON.
  Rozwiązuje kolizję: 9-cyfrowy numer komórkowy bez separatorów = REGON w identity.
  Nowy wzorzec akceptuje też separatory kropkowe (501.234.567) i nawias (22)123-45-67.
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

# [NUMER-RECALL] Telefon po słowie kluczowym — wyższy priorytet niż REGON.
# Stosowany PRZED _CONTACT_PATTERNS żeby 9-cyfrowy numer zarejestrować zanim
# identity layer (warstwa 1) zmatchuje go jako REGON.
# Separatory: spacja, myślnik, kropka. Nawiasy przy kierunkowym opcjonalne.
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


def apply_contact_layer(state: PipelineState) -> None:
    """Stosuje wzorce email i telefon na state.text."""
    hits: list[tuple[int, int, str, str]] = []
    # [NUMER-RECALL] Context-aware telefon — najpierw, by zająć span przed REGON
    for m in _PHONE_CONTEXT_RE.finditer(state.text):
        hits.append((m.start(), m.end(), m.group(0), TOKEN_NUMER))
    for token_type, pat in _CONTACT_PATTERNS:
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

    # ── Test podstawowy: telefon komórkowy + stacjonarny + email ─────────────
    print("1. Komórkowy + stacjonarny + email:")
    state = PipelineState(
        text="tel. +48 600 123 456, fax 22 123 45 67, jan@firma.pl",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state)
    check("Telefon komórkowy usunięty", "600 123 456" not in state.text,
          f"text={state.text!r}")
    check("Telefon stacjonarny usunięty", "22 123 45 67" not in state.text,
          f"text={state.text!r}")
    check("Email usunięty", "jan@firma.pl" not in state.text,
          f"text={state.text!r}")
    rm = state.allocator.reverse_map
    check("EMAIL_NNN w reverse_map",
          any(k.startswith("EMAIL_") for k in rm),
          f"keys={list(rm)}")
    check("NUMER_NNN w reverse_map",
          any(k.startswith("NUMER_") for k in rm),
          f"keys={list(rm)}")

    # ── Test deduplikacji emaila ──────────────────────────────────────────────
    print("\n2. Deduplication — ten sam email dwa razy:")
    state2 = PipelineState(
        text="kontakt: jan@firma.pl lub jan@firma.pl",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state2)
    check("Email usunięty", "jan@firma.pl" not in state2.text)
    rm2 = state2.allocator.reverse_map
    check("Jeden token EMAIL (dedup)", len(rm2) == 1,
          f"reverse_map={rm2}")

    # ── Test numeru bez prefiksu krajowego ────────────────────────────────────
    print("\n3. Numer bez prefiksu +48:")
    state3 = PipelineState(
        text="Zadzwoń: 512 345 678",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state3)
    check("Telefon bez +48 usunięty", "512 345 678" not in state3.text,
          f"text={state3.text!r}")

    # ── Test ochrony spanu — email i telefon nie nakładają się ───────────────
    print("\n4. Ochrona spanu — email i telefon nie nakładają się:")
    state4 = PipelineState(
        text="info@firma.pl, tel. 600 123 456",
        allocator=TokenAllocator(),
    )
    apply_contact_layer(state4)
    rm4 = state4.allocator.reverse_map
    check("Dwa osobne tokeny", len(rm4) == 2,
          f"reverse_map={rm4}")

    # ── Test brak dopasowań ───────────────────────────────────────────────────
    print("\n5. Brak dopasowań — tekst niezmieniony:")
    original = "Zwykły tekst bez kontaktów."
    state5 = PipelineState(text=original, allocator=TokenAllocator())
    apply_contact_layer(state5)
    check("Tekst niezmieniony", state5.text == original)
    check("reverse_map pusty", len(state5.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_contact_layer() else 1)
