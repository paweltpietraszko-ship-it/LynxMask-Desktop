"""
pipeline_new.py  v0.5
Nowy pipeline oparty na TokenAllocator — bez rozproszonych liczników.
Zmiany v0.5:
  - apply_ocr_normalizer jako pierwsza warstwa (krok 0) — OCR-błędy naprawiane
    zanim wzorce regex i SpaCy zobaczą tekst. Bez tego I→1/O→0 itp. nie były
    korygowane, IBAN/PESEL/NIP z błędami OCR trafiały do tekstu wyjściowego
    niesprawdzone (PSE-2026-0824).
Zmiany v0.4:
  - Pre-ekstrakcja NER przed apply_address_layer (extract_ner_results).
    SpaCy musi widzieć pełny adres żeby rozpoznać poprzedzające imię/nazwisko.
    Po zamaskowaniu adresu TracBack OSOBA_NNN nie pojawia się bo SpaCy traci
    kontekst ulicy (np. Krzysztof Adamczyk al. Niepodległości → SpaCy OK,
    ale Krzysztof Adamczyk ADRES_001 → SpaCy nie rozpoznaje).
    Rozwiązanie: extract_ner_results() przed adresem, apply_ner_layer() po.
Zmiany v0.3:
  - Dodano apply_numeric_layer (numer_klienta KL-, numer_faktury FV-/VAT/, numer_umowy UMW/)
    po apply_legal_layer
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pipeline_core import PipelineState, TokenAllocator
from layers.identity import apply_identity_layer
from layers.contact import apply_contact_layer
from layers.financial import apply_financial_layer
from layers.legal import apply_legal_layer
from layers.numeric import apply_numeric_layer
from layers.institution import apply_institution_layer
from layers.address import apply_address_layer
from layers.ocr_normalizer import apply_ocr_normalizer
from layers.ner_adapter import apply_ner_layer, extract_ner_results
from layers.fallback import apply_fallback_layer
from layers.validation import apply_validation_layer

if TYPE_CHECKING:
    from anonymizer import Anonymizer


def _apply(state: PipelineState, fn, *args) -> None:
    """Resetuje spany przed wywołaniem warstwy.
    Każda warstwa modyfikuje tekst — stare spany mają błędne współrzędne
    w nowym tekście i blokowałyby dopasowania kolejnej warstwy."""
    state.allocator.reset_spans()
    fn(state, *args)


def run_pipeline_new(
    text: str,
    anon_map: dict,
    anonymizer: "Anonymizer | None" = None,
) -> tuple[str, dict]:
    state = PipelineState(text=text, allocator=TokenAllocator())
    _apply(state, apply_ocr_normalizer)
    _apply(state, apply_identity_layer)
    _apply(state, apply_financial_layer)
    _apply(state, apply_legal_layer)
    _apply(state, apply_numeric_layer)
    _apply(state, apply_contact_layer)
    # [BUG-INSTITUTION-ORDER] institution musi działać PO NER — skróty instytucji
    # (KNF, RPO itp.) są w blocklist NER żeby SpaCy ich nie tokenizował jako FIRMA.
    # Gdyby institution działał przed NER, skrót stałby się już INSTYTUCJA_NNN
    # i był pomijany przez _filter_institutions (TOKEN_RE match). Kolejność:
    # NER → institution → fallback.
    extract_ner_results(state, anon_map)
    _apply(state, apply_address_layer)
    _apply(state, apply_ner_layer, anon_map)
    _apply(state, apply_institution_layer)
    _apply(state, apply_fallback_layer)
    if anonymizer is not None:
        _apply(state, apply_validation_layer, anonymizer)
    return state.text, state.allocator.reverse_map


# ─────────────────────────────────────────────────────────────────────────────
# Test integracyjny
# ─────────────────────────────────────────────────────────────────────────────

def test_pipeline_new() -> bool:
    from unittest.mock import patch
    import layers.ner_adapter as _ner_mod

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

    print("=== test_pipeline_new (integracyjny) ===\n")

    PII_VALUES = [
        "AOK171495",           # dowód osobisty
        "512 345 678",         # telefon (fragment wystarczy)
        "75082212345",         # PESEL
        "KA1K/00075119/1",     # KW
        "Km 17224/2021",       # sygnatura komornicza
        "jan.kowalski@firma.pl", # email
    ]

    text = (
        "Nr dowodu: AOK171495\n"
        "Tel.: +48 512 345 678\n"
        "PESEL: 75082212345\n"
        "KW: KA1K/00075119/1\n"
        "Sygn. komornicza: Km 17224/2021\n"
        "E-mail: jan.kowalski@firma.pl"
    )

    # NER nie zwraca nic dla tego tekstu (brak modelu w testach)
    with patch.object(_ner_mod, "process_ner", return_value=({}, {})):
        result_text, reverse_map = run_pipeline_new(text, anon_map={})

    print("Tekst po pseudonimizacji:")
    print(result_text)
    print()
    print("reverse_map:")
    for k, v in sorted(reverse_map.items()):
        print(f"  {k} → {v!r}")
    print()

    # ── 1. Żadna wartość PII nie pozostała w tekście ──────────────────────────
    print("1. Pokrycie PII:")
    for pii in PII_VALUES:
        check(f"{pii!r} usunięty", pii not in result_text,
              f"nadal w tekście")

    # ── 2. Każda wartość ma unikalny token ────────────────────────────────────
    print("\n2. Unikalność tokenów (token → jedna wartość):")
    check("reverse_map niepusty", len(reverse_map) > 0,
          f"len={len(reverse_map)}")
    values = list(reverse_map.values())
    check("Brak duplikatów wartości w reverse_map",
          len(values) == len(set(values)),
          f"duplikaty: {[v for v in values if values.count(v) > 1]}")

    # ── 3. Żaden token nie wskazuje na dwie wartości ──────────────────────────
    print("\n3. Integralność mapy (jeden token → jedna wartość):")
    check("Każdy token unikalny (dict nie może mieć duplikatów kluczy)",
          len(reverse_map) == len(set(reverse_map.keys())))

    # ── 4. Tokeny mają poprawny format TYPE_NNN ───────────────────────────────
    print("\n4. Format tokenów:")
    import re
    token_re = re.compile(r"^(NUMER|EMAIL|ADRES|OSOBA|FIRMA|KWOTA|INSTYTUCJA)_\d{3}$")
    bad = [k for k in reverse_map if not token_re.match(k)]
    check("Wszystkie tokeny w formacie TYPE_NNN", len(bad) == 0,
          f"niepoprawne: {bad}")

    # ── 5. Brak tokenów w tekście których nie ma w reverse_map ───────────────
    print("\n5. Spójność tekst ↔ reverse_map:")
    found_in_text = set(token_re.findall(result_text))
    # token_re.findall zwraca grupy — sprawdź pełne tokeny inaczej
    full_token_re = re.compile(
        r"\b(NUMER|EMAIL|ADRES|OSOBA|FIRMA|KWOTA|INSTYTUCJA)_\d{3}\b"
    )
    tokens_in_text = set(full_token_re.findall(result_text))
    # Zamień grupy capture na pełne tokeny
    full_tokens_in_text = {m for m in full_token_re.finditer(result_text)
                           for m in [m.group(0)]}
    orphaned = full_tokens_in_text - set(reverse_map.keys())
    check("Brak tokenów-sierot w tekście (bez wpisu w reverse_map)",
          len(orphaned) == 0, f"sieroty: {orphaned}")

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys
    print()
    sys.exit(0 if test_pipeline_new() else 1)
