"""
layers/credentials.py  v1.0
Warstwa credentials — prawa wykonywania zawodu, legitymacje, licencje.

Wzorce ładowane z backend/credential_patterns.json (plik JSON obok backendu).
Dodawanie nowych wzorców: edytuj JSON, nie ten plik.

Format JSON:
  [{"name": "...", "comment": "...", "pattern": "REGEX", "token": "NUMER"}, ...]
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_core import PipelineState, TokenAllocator

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATTERNS_FILE = os.path.join(_HERE, "credential_patterns.json")


def _load_patterns() -> list[tuple[str, re.Pattern]]:
    try:
        with open(_PATTERNS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        result = []
        for entry in data:
            try:
                pat = re.compile(entry["pattern"], re.UNICODE)
                result.append((entry["token"], pat))
            except re.error as e:
                import logging
                logging.getLogger("lynxmask.credentials").warning(
                    "Zły wzorzec '%s': %s", entry.get("name", "?"), e
                )
        return result
    except FileNotFoundError:
        return []
    except Exception as e:
        import logging
        logging.getLogger("lynxmask.credentials").error(
            "Nie można załadować credential_patterns.json: %s", e
        )
        return []


_CREDENTIAL_PATTERNS: list[tuple[str, re.Pattern]] = _load_patterns()


def apply_credentials_layer(state: PipelineState) -> None:
    """Maskuje numery praw wykonywania zawodu, licencji i legitymacji."""
    hits: list[tuple[int, int, str, str]] = []

    for token_type, pat in _CREDENTIAL_PATTERNS:
        for m in pat.finditer(state.text):
            hits.append((m.start(), m.end(), m.group(0), token_type))

    # Większy span wygrywa (jak w pozostałych warstwach)
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

def test_credentials_layer() -> bool:
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

    print("=== test_credentials_layer ===\n")

    cases = [
        ("PWZ skrót",           "PWZ 1234567",                                "1234567"),
        ("PWZ z kropkami",      "P.W.Z. nr 7654321",                          "7654321"),
        ("PWZ fraza",           "prawo wykonywania zawodu nr 1234567",         "1234567"),
        ("Uprawnienia budowl.", "WAR/0123/16/BOK",                            "WAR/0123/16/BOK"),
        ("Licencja ochrony",    "licencją pracownika ochrony nr 123456",       "123456"),
        ("Licencja detektywa",  "licencja detektywa 654321",                   "654321"),
        ("Pilot EASA",          "PL.FCL.012345",                              "PL.FCL.012345"),
        ("Mechanik EASA",       "PL.66.987654",                               "PL.66.987654"),
        ("Geodezja",            "numer 456.GiK.2",                            "456.GiK.2"),
        ("Legitymacja nr",      "legitymacja nr 12345",                       "12345"),
        ("Doradca pod.",        "doradcy podatkowego nr 98765",               "98765"),
    ]

    for name, text, expected_absent in cases:
        state = PipelineState(text=text, allocator=TokenAllocator())
        apply_credentials_layer(state)
        check(name, expected_absent not in state.text, f"text={state.text!r}")

    print("\nBrak dopasowania — tekst niezmieniony:")
    orig = "Zwykły tekst bez uprawnień."
    state = PipelineState(text=orig, allocator=TokenAllocator())
    apply_credentials_layer(state)
    check("Tekst niezmieniony", state.text == orig)
    check("reverse_map pusty", len(state.allocator.reverse_map) == 0)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    print()
    _sys.exit(0 if test_credentials_layer() else 1)
