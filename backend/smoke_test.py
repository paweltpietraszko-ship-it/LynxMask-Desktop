"""
smoke_test.py  v1.0
Weryfikacja poprawnosci silnika pseudonimizacji przed pierwszym maskowaniem.

Uruchamiany automatycznie w _lifespan() pseudominizer_api.py.
Jesli ktorykolwiek test nie przejdzie — start jest blokowany z czytelnym komunikatem.

Zasada: syntetyczny tekst z min. jednym przykladem kazdej krytycznej kategorii PII.
Sprawdzamy czy pipeline strukturalny (bez NER/SpaCy) zamaskuje wszystkie encje.
NER nie jest testowany — jego niedostepnosc jest jawnie logowana przy starcie.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("lynxmask.smoke_test")

# Syntetyczny dokument — kazda kategoria PII musi byc zamaskowana
_SMOKE_TEXT = (
    "PESEL: 85010112345, "
    "NIP: 855-019-31-23, "
    "IBAN: PL61 1090 1014 0000 0712 1981 2874, "
    "e-mail: jan.kowalski@firma.pl, "
    "paszport: ZX1234567, "
    "dowod: AOK171495, "
    "adres: ul. Kwiatowa 12, 30-001 Krakow"
)

# Co musi zniknac z tekstu po pseudonimizacji
_MUST_MASK: list[tuple[str, str]] = [
    ("85010112345",           "PESEL"),
    ("855-019-31-23",         "NIP"),
    ("PL61 1090 1014",        "IBAN PL"),
    ("jan.kowalski@firma.pl", "EMAIL"),
    ("ZX1234567",             "PASZPORT"),
    ("AOK171495",             "DOWOD"),
    ("ul. Kwiatowa",          "ADRES"),
]


def run_smoke_test() -> tuple[bool, list[str]]:
    """
    Uruchamia pipeline strukturalny na syntetycznym tekscie.
    Zwraca (ok: bool, bledy: list[str]).
    """
    errors: list[str] = []

    try:
        from pipeline_core import PipelineState, TokenAllocator
        from layers.identity import apply_identity_layer
        from layers.financial import apply_financial_layer
        from layers.contact import apply_contact_layer
        from layers.address import apply_address_layer
    except ImportError as e:
        return False, [f"[SMOKE] Import warstwy nie powiodl sie: {e}"]

    try:
        state = PipelineState(text=_SMOKE_TEXT, allocator=TokenAllocator())
        apply_identity_layer(state)
        apply_financial_layer(state)
        apply_contact_layer(state)
        apply_address_layer(state)
        result = state.text
    except Exception as e:
        return False, [f"[SMOKE] Pipeline crash: {e}"]

    for fragment, label in _MUST_MASK:
        if fragment in result:
            errors.append(f"[SMOKE] Wyciek {label}: '{fragment}' nadal widoczny w wyniku")

    return len(errors) == 0, errors


def assert_smoke_test() -> None:
    """
    Wywolaj w _lifespan(). Rzuca RuntimeError jesli smoke test nie przejdzie.
    Blokuje start aplikacji — fail-closed.
    """
    ok, errors = run_smoke_test()
    if ok:
        logger.info("[SMOKE] Smoke test OK — wszystkie kategorie PII zamaskowane")
    else:
        for err in errors:
            logger.critical(err)
        raise RuntimeError(
            "Smoke test nie przeszedl — silnik pseudonimizacji nie dziala poprawnie. "
            "Aplikacja nie zostanie uruchomiona. Szczegoly powyzej w logach."
        )


if __name__ == "__main__":
    import sys
    ok, errors = run_smoke_test()
    if ok:
        print("[SMOKE] OK — wszystkie kategorie PII zamaskowane")
        sys.exit(0)
    else:
        for e in errors:
            print(e)
        sys.exit(1)
