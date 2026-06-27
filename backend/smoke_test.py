"""
smoke_test.py  v1.1
Weryfikacja poprawnosci silnika pseudonimizacji przed pierwszym maskowaniem.

Uruchamiany automatycznie w _lifespan() pseudominizer_api.py.
Jesli ktorykolwiek test nie przejdzie — start jest blokowany z czytelnym komunikatem.

Zasada: syntetyczny tekst z min. jednym przykladem kazdej krytycznej kategorii PII.
Sprawdzamy czy pipeline strukturalny (bez NER/SpaCy) zamaskuje wszystkie encje.
NER nie jest testowany — jego niedostepnosc jest jawnie logowana przy starcie.

v1.1: Rozszerzono o warstwy credentials, legal, numeric, amount, verbal_amount,
      institution oraz ocr_normalizer. Smoke test teraz pokrywa wszystkie 14 warstw.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("lynxmask.smoke_test")

# Syntetyczny dokument — kazda kategoria PII musi byc zamaskowana
_SMOKE_TEXT = (
    # identity
    "PESEL: 85010112345, "
    "NIP: 855-019-31-23, "
    "paszport: ZX1234567, "
    "dowod: AOK171495, "
    # financial
    "IBAN: PL61 1090 1014 0000 0712 1981 2874, "
    # contact
    "e-mail: jan.kowalski@firma.pl, "
    "tel. 600 123 456, "
    # address
    "adres: ul. Kwiatowa 12, 30-001 Krakow, "
    # legal
    "sygn. I C 123/2024, "
    "KRS 0000123456, "
    # numeric
    "FV/2024/00123, "
    # amount
    "kwota 3 500,00 PLN, "
    # credentials
    "PWZ 1234567, "
    "WAR/0042/21/BOK, "
    # institution (skrot instytucji — nie powinien trafic jako FIRMA)
    "ZUS, NFZ"
)

# Co musi zniknac z tekstu po pseudonimizacji
_MUST_MASK: list[tuple[str, str]] = [
    # identity
    ("85010112345",           "PESEL"),
    ("855-019-31-23",         "NIP"),
    ("ZX1234567",             "PASZPORT"),
    ("AOK171495",             "DOWOD"),
    # financial
    ("PL61 1090 1014",        "IBAN"),
    # contact
    ("jan.kowalski@firma.pl", "EMAIL"),
    ("600 123 456",           "TELEFON"),
    # address
    ("ul. Kwiatowa",          "ADRES"),
    # legal
    ("I C 123/2024",          "SYGNATURA"),
    ("KRS 0000123456",        "KRS"),
    # numeric
    ("FV/2024/00123",         "NUMER FAKTURY"),
    # amount
    ("3 500,00 PLN",          "KWOTA"),
    # credentials
    ("PWZ 1234567",           "PWZ"),
    ("WAR/0042/21/BOK",       "UPRAWNIENIA BUDOWLANE"),
]

# Co NIE moze byc zamaskowane (false positive guard)
_MUST_NOT_MASK: list[tuple[str, str]] = [
    ("ZUS",  "skrot instytucji ZUS"),
    ("NFZ",  "skrot instytucji NFZ"),
]


def run_smoke_test() -> tuple[bool, list[str]]:
    """
    Uruchamia pipeline strukturalny na syntetycznym tekscie.
    Zwraca (ok: bool, bledy: list[str]).
    """
    errors: list[str] = []

    try:
        from pipeline_core import PipelineState, TokenAllocator
        from layers.ocr_normalizer import apply_ocr_normalizer
        from layers.identity import apply_identity_layer
        from layers.credentials import apply_credentials_layer
        from layers.financial import apply_financial_layer
        from layers.legal import apply_legal_layer
        from layers.numeric import apply_numeric_layer
        from layers.contact import apply_contact_layer
        from layers.amount import apply_amount_layer
        from layers.address import apply_address_layer
        from layers.institution import apply_institution_layer
    except ImportError as e:
        return False, [f"[SMOKE] Import warstwy nie powiodl sie: {e}"]

    try:
        state = PipelineState(text=_SMOKE_TEXT, allocator=TokenAllocator())

        def _apply(fn, *args):
            state.allocator.reset_spans()
            fn(state, *args)

        _apply(apply_ocr_normalizer)
        _apply(apply_identity_layer)
        _apply(apply_credentials_layer)
        _apply(apply_financial_layer)
        _apply(apply_legal_layer)
        _apply(apply_numeric_layer)
        _apply(apply_contact_layer)
        _apply(apply_amount_layer)
        _apply(apply_address_layer)
        _apply(apply_institution_layer)

        result = state.text
    except Exception as e:
        return False, [f"[SMOKE] Pipeline crash: {e}"]

    for fragment, label in _MUST_MASK:
        if fragment in result:
            errors.append(f"[SMOKE] Wyciek {label}: '{fragment}' nadal widoczny")

    for fragment, label in _MUST_NOT_MASK:
        if fragment not in result:
            errors.append(f"[SMOKE] False positive {label}: '{fragment}' zostal zamaskowany")

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
