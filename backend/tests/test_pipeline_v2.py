# test_pipeline_v2.py v1.3
"""
Testy integracyjne dla pseudonymizer pipeline v2.

Zmiany v1.1:
  [FIX-MOCK] _make_state: state.spacy_ner_mod zamiast state.nlp,
             detect_entities() zamiast nlp(), ent.label zamiast ent.label_
  [FIX-LABEL] T03: etykiety PERSNAME -> OSOBA (konwencja ner_layer.py)
  [FIX-TOKEN] T04c/T04d: IBAN_* -> NUMER_* + skip dla trybu zdegradowanego
  [FIX-T04b]  T04b: bez anonymizera IBAN jest znormalizowany ale nie tokenizowany —
              guard musi zablokować (guard_blocked=True), nie asertujemy brak w tekście

Założenia kontraktowe (dostosuj jeśli interfejs się różni):
  - pseudonymize_document(text: str, state: AppState) -> PipelineResult
  - PipelineResult.text          — tekst po pseudonimizacji
  - PipelineResult.reverse_map  — dict {token: oryginalna_wartość}
  - PipelineResult.guard_blocked — bool, True jeśli output_guard zablokował

Nie używają hardware_profile.json.
Anonymizer może być None (tryb zdegradowany).
SpaCy mockowany jako MagicMock — pipeline logic pozostaje realna.
"""

import re
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Ścieżka projektu — dostosuj jeśli testy są w podkatalogu tests/
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline import AppState, PipelineResult, pseudonymize_document  # noqa: E402


# ---------------------------------------------------------------------------
# Helpery
# ---------------------------------------------------------------------------

def _make_state(spacy_ents: list[tuple[str, str]] | None = None) -> AppState:
    """
    Zwraca AppState bez hardware_profile.json.
    anonymizer = None (tryb zdegradowany — warstwa anonymizer pomijana).
    spacy_ner_mod mockowany przez detect_entities(text) → lista encji.

    Etykiety muszą być 'OSOBA' lub 'FIRMA' (konwencja ner_layer.py,
    nie natywne etykiety SpaCy — tłumaczenie robi spacy_ner.py w produkcji).

    # v1.1 — fix: state.spacy_ner_mod zamiast state.nlp,
    #         detect_entities() zamiast nlp(),
    #         ent.label zamiast ent.label_
    """
    state = AppState()
    state.anonymizer = None  # tryb zdegradowany — brak hardware profilu

    if spacy_ents:
        ents = []
        for text, label in spacy_ents:
            ent = MagicMock()
            ent.text = text
            ent.label = label   # ner_layer.py czyta .label (bez podkreślnika)
            ent.start = 0
            ent.end = len(text)
            ents.append(ent)

        mock_mod = MagicMock()
        mock_mod.detect_entities.return_value = ents
        state.spacy_ner_mod = mock_mod
    else:
        state.spacy_ner_mod = None  # brak NER — pipeline degraduje

    return state


def _extract_tokens(text: str, prefix: str) -> list[str]:
    """Zwraca listę unikalnych tokenów pasujących do PREFIX_NNN w tekście."""
    pattern = rf"\b{re.escape(prefix)}_\d{{3}}\b"
    return list(set(re.findall(pattern, text)))


def _all_tokens_in_text(text: str) -> list[str]:
    """Zwraca wszystkie tokeny postaci WIELKIE_001 z tekstu."""
    return list(set(re.findall(r"\b[A-Z_]{3,}_\d{3}\b", text)))




# ---------------------------------------------------------------------------
# T02 — Adres patronimiczny
# ---------------------------------------------------------------------------

class TestAddrPatronymic:
    """v1.1 — przepisana na run_pipeline_new + mock process_ner."""

    def _run(self, text: str) -> tuple[str, dict]:
        import layers.ner_adapter as _ner_mod
        from pipeline_new import run_pipeline_new
        with patch.object(_ner_mod, "process_ner", return_value=({}, {})):
            return run_pipeline_new(text, anon_map={})

    def test_addr_patronymic_contains_adres_token(self):
        """
        ADDR regex: 'ul. Jana Kowalskiego 5, 00-001 Warszawa' → wynik zawiera ADRES_*.
        # v1.1
        """
        result_text, reverse_map = self._run(
            "Siedziba: ul. Jana Kowalskiego 5, 00-001 Warszawa."
        )
        adres_tokens = [k for k in reverse_map if k.startswith("ADRES_")]
        assert adres_tokens, (
            f"[T02a] Brak tokenu ADRES_* w wyniku.\n"
            f"  Wejście: 'ul. Jana Kowalskiego 5, 00-001 Warszawa'\n"
            f"  Wynik:   {result_text!r}"
        )

    def test_addr_patronymic_name_absent_from_output(self):
        """
        ADDR regex: 'Jana Kowalskiego' nie wycieka do wyjścia.
        # v1.1
        """
        result_text, _ = self._run(
            "Siedziba: ul. Jana Kowalskiego 5, 00-001 Warszawa."
        )
        assert "Jana Kowalskiego" not in result_text, (
            f"[T02b] Imię i nazwisko z adresu nadal w wyjściu.\n"
            f"  Wynik: {result_text!r}"
        )

    def test_addr_patronymic_reverse_map_contains_name(self):
        """
        ADDR regex: reverse_map[ADRES_*] zawiera 'Jana Kowalskiego'.
        # v1.1
        """
        result_text, reverse_map = self._run(
            "Siedziba: ul. Jana Kowalskiego 5, 00-001 Warszawa."
        )
        adres_tokens = [k for k in reverse_map if k.startswith("ADRES_")]
        assert adres_tokens, "[T02c-pre] Brak ADRES_* — test zależny od T02a"
        token = adres_tokens[0]
        original = reverse_map[token]
        assert "Kowalskiego" in original, (
            f"[T02c] reverse_map[{token!r}] = {original!r} — brak 'Kowalskiego'."
        )


# ---------------------------------------------------------------------------
# T03 — FIX-NER-GLOBAL: priorytet ADRES nad OSOBA
# ---------------------------------------------------------------------------

class TestFixNerGlobalPriority:

    def test_addr_wins_over_ner_person(self):
        """
        FIX-NER-GLOBAL: SpaCy widzi 'Jana Kowalskiego' jako PERSON,
        ale ADRES regex ma wyższy priorytet → token ADRES, nie OSOBA.
        # v1.0
        """
        # SpaCy zwraca Jana Kowalskiego jako osobę
        state = _make_state(spacy_ents=[("Jana Kowalskiego", "OSOBA")])

        result: PipelineResult = pseudonymize_document(
            "Siedziba: ul. Jana Kowalskiego 5, 00-001 Warszawa.", state
        )

        adres_tokens = _extract_tokens(result.text, "ADRES")
        osoba_tokens = _extract_tokens(result.text, "OSOBA")

        assert adres_tokens, (
            f"[T03a] Brak ADRES_* — ADDR regex nie wygrał z NER.\n"
            f"  Wynik: {result.text!r}"
        )

        # OSOBA_* nie powinno istnieć dla fragmentu będącego częścią adresu
        assert not osoba_tokens, (
            f"[T03b] Obecny token OSOBA_* mimo że name jest częścią adresu.\n"
            f"  Wynik: {result.text!r}\n"
            f"  OSOBA tokens: {osoba_tokens}"
        )

    def test_standalone_person_still_gets_osoba_token(self):
        """
        Imię/nazwisko poza adresem → token OSOBA_* w nowym pipeline.
        # v1.1 — przepisany na run_pipeline_new + mock process_ner
        """
        import layers.ner_adapter as _ner_mod
        from pipeline_new import run_pipeline_new

        with patch.object(_ner_mod, "process_ner",
                          return_value=({"OSOBA_001": "Jan Kowalski"}, {})):
            result_text, reverse_map = run_pipeline_new(
                "Zleceniodawca: Jan Kowalski.", anon_map={}
            )

        assert any(k.startswith("OSOBA_") for k in reverse_map), (
            f"[T03c] Brak tokenu OSOBA_* dla 'Jan Kowalski' bez kontekstu adresu.\n"
            f"  Wynik: {result_text!r}"
        )
        assert "Jan Kowalski" not in result_text, (
            f"[T03d] Imię i nazwisko nadal widoczne w wyjściu.\n"
            f"  Wynik: {result_text!r}"
        )


# ---------------------------------------------------------------------------
# T04 — IBAN ze spacją
# ---------------------------------------------------------------------------

class TestIbanWithSpace:
    """v1.1 — przepisana na run_pipeline_new + mock process_ner."""

    def _run(self, text: str) -> tuple[str, dict]:
        import layers.ner_adapter as _ner_mod
        from pipeline_new import run_pipeline_new
        with patch.object(_ner_mod, "process_ner", return_value=({}, {})):
            return run_pipeline_new(text, anon_map={})

    def test_iban_with_spaces_masked(self):
        """
        IBAN ze spacjami: 'PL61 1090 1014 0000 0712 1981 2874' nie wycieka.
        # v1.1
        """
        iban = "PL61 1090 1014 0000 0712 1981 2874"
        result_text, _ = self._run(f"Przelew na konto: {iban}.")
        assert iban not in result_text, (
            f"[T04a] IBAN ze spacjami nie zamaskowany.\n"
            f"  Wynik: {result_text!r}"
        )

    def test_iban_with_spaces_token_in_output(self):
        """
        IBAN ze spacjami: wynik zawiera token NUMER_*.
        # v1.1
        """
        iban = "PL61 1090 1014 0000 0712 1981 2874"
        result_text, reverse_map = self._run(f"Przelew na konto: {iban}.")
        numer_tokens = [k for k in reverse_map if k.startswith("NUMER_")]
        assert numer_tokens, (
            f"[T04b] Brak tokenu NUMER_* w reverse_map.\n"
            f"  reverse_map: {reverse_map}"
        )

    def test_iban_reverse_map_entry(self):
        """
        IBAN ze spacjami: token NUMER_* ma wpis w reverse_map z wartością IBAN.
        # v1.1
        """
        iban = "PL61 1090 1014 0000 0712 1981 2874"
        result_text, reverse_map = self._run(f"Przelew na konto: {iban}.")
        numer_tokens = [k for k in reverse_map if k.startswith("NUMER_")]
        assert numer_tokens, "[T04d-pre] Brak NUMER_* — test zależny od T04b"
        token = numer_tokens[0]
        original = reverse_map[token]
        assert "PL" in original or "61" in original, (
            f"[T04d] reverse_map[{token!r}] = {original!r} — nie przypomina IBANu."
        )


# ---------------------------------------------------------------------------
# T05 — Idempotentność
# ---------------------------------------------------------------------------

class TestIdempotency:

    def test_second_pass_no_new_tokens(self):
        """
        Idempotentność: tekst z tokenami przepuszczony ponownie nie tworzy nowych tokenów.
        # v1.0
        """
        state = _make_state()
        first: PipelineResult = pseudonymize_document(
            "Faktura na kwotę sto dwadzieścia złotych 00/100. "
            "Siedziba: ul. Jana Kowalskiego 5, 00-001 Warszawa.",
            state,
        )

        tokens_after_first = _all_tokens_in_text(first.text)

        # Drugi przebieg na już pseudonimizowanym tekście
        second: PipelineResult = pseudonymize_document(first.text, state)
        tokens_after_second = _all_tokens_in_text(second.text)

        new_tokens = set(tokens_after_second) - set(tokens_after_first)
        assert not new_tokens, (
            f"[T05a] Drugi przebieg wygenerował nowe tokeny: {new_tokens}\n"
            f"  Po 1. przebiegu: {tokens_after_first}\n"
            f"  Po 2. przebiegu: {tokens_after_second}"
        )

    def test_second_pass_same_token_count(self):
        """
        Idempotentność: liczba tokenów nie rośnie przy kolejnym przebiegu.
        # v1.0
        """
        state = _make_state()
        first: PipelineResult = pseudonymize_document(
            "Przelew na PL 61 1234 5678 9012 3456 7890 1234 od Jan Nowak.",
            state,
        )

        count_first = len(_all_tokens_in_text(first.text))
        second: PipelineResult = pseudonymize_document(first.text, state)
        count_second = len(_all_tokens_in_text(second.text))

        assert count_second <= count_first, (
            f"[T05b] Liczba tokenów wzrosła przy 2. przebiegu: "
            f"{count_first} → {count_second}\n"
            f"  Po 1.: {first.text!r}\n"
            f"  Po 2.: {second.text!r}"
        )


# ---------------------------------------------------------------------------
# T06 — Depseudonimizacja (completeness reverse_map)
# ---------------------------------------------------------------------------

class TestDepseudonymization:

    def test_every_token_has_reverse_map_entry(self):
        """
        Depseudonimizacja: każdy token w wyjściu ma niepusty wpis w reverse_map.
        # v1.0
        """
        state = _make_state(spacy_ents=[("Jan Kowalski", "OSOBA")])

        result: PipelineResult = pseudonymize_document(
            "Zleceniodawca Jan Kowalski, ul. Lipowa 3, 00-001 Warszawa, "
            "konto PL 61 1234 5678 9012 3456 7890 1234, "
            "kwota: sto pięćdziesiąt złotych 00/100.",
            state,
        )

        tokens_in_text = _all_tokens_in_text(result.text)
        assert tokens_in_text, (
            f"[T06-pre] Brak jakichkolwiek tokenów w wyjściu — pipeline nie działa.\n"
            f"  Wynik: {result.text!r}"
        )

        missing = []
        empty = []
        for token in tokens_in_text:
            if token not in result.reverse_map:
                missing.append(token)
            elif not result.reverse_map[token].strip():
                empty.append(token)

        assert not missing, (
            f"[T06a] Tokeny bez wpisu w reverse_map: {missing}\n"
            f"  reverse_map keys: {list(result.reverse_map.keys())}"
        )
        assert not empty, (
            f"[T06b] Tokeny z pustym wpisem w reverse_map: {empty}"
        )

    def test_reverse_map_allows_full_reconstruction(self):
        """
        Depseudonimizacja: podmiana tokenów z reverse_map odtwarza oryginalne fragmenty.
        # v1.0
        """
        original = (
            "Kwota: sto złotych 00/100. Adres: ul. Lipowa 3, 00-001 Warszawa."
        )
        state = _make_state()

        result: PipelineResult = pseudonymize_document(original, state)

        reconstructed = result.text
        for token, value in result.reverse_map.items():
            reconstructed = reconstructed.replace(token, value)

        # Po podmianie tokenów żaden token nie powinien zostać
        leftover_tokens = _all_tokens_in_text(reconstructed)
        assert not leftover_tokens, (
            f"[T06c] Po depseudonimizacji pozostały tokeny: {leftover_tokens}\n"
            f"  Zrekonstruowany tekst: {reconstructed!r}"
        )


# ---------------------------------------------------------------------------
# T07 — Guard nie blokuje czystego tekstu
# ---------------------------------------------------------------------------

class TestOutputGuardCleanText:

    def test_clean_text_not_blocked(self):
        """
        output_guard: czysty tekst bez PII przechodzi bez guard_blocked=True.
        # v1.0
        """
        state = _make_state()

        result: PipelineResult = pseudonymize_document(
            "Proszę o wystawienie faktury za usługi doradcze w zakresie prawa podatkowego.",
            state,
        )

        assert result.guard_blocked is False, (
            f"[T07a] Guard zablokował czysty tekst (guard_blocked=True).\n"
            f"  Wynik: {result.text!r}"
        )

    def test_clean_text_no_tokens_generated(self):
        """
        output_guard: tekst bez PII nie generuje tokenów pseudonimizacji.
        # v1.0
        """
        state = _make_state()

        result: PipelineResult = pseudonymize_document(
            "Proszę o wystawienie faktury za usługi doradcze w zakresie prawa podatkowego.",
            state,
        )

        tokens = _all_tokens_in_text(result.text)
        assert not tokens, (
            f"[T07b] Wygenerowano tokeny dla tekstu bez PII: {tokens}\n"
            f"  Wynik: {result.text!r}"
        )

    def test_clean_text_output_close_to_input(self):
        """
        output_guard: tekst bez PII po pipeline jest semantycznie zbliżony do wejścia.
        Test heurystyczny: długość wyjścia > 80% długości wejścia.
        # v1.0
        """
        original = (
            "Proszę o wystawienie faktury za usługi doradcze w zakresie prawa podatkowego."
        )
        state = _make_state()

        result: PipelineResult = pseudonymize_document(original, state)

        ratio = len(result.text) / len(original)
        assert ratio > 0.8, (
            f"[T07c] Wyjście za krótkie: {len(result.text)} / {len(original)} = {ratio:.2f}.\n"
            f"  Wyjście: {result.text!r}"
        )


# ---------------------------------------------------------------------------
# T08 — Edge cases / regresja
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_text_no_crash(self):
        """
        Edge case: pusty string nie powoduje wyjątku, wynik jest prawidłowym PipelineResult.
        # v1.0
        """
        state = _make_state()
        result: PipelineResult = pseudonymize_document("", state)

        assert result is not None, "[T08a] pseudonymize_document('') zwróciło None."
        assert isinstance(result.text, str), (
            f"[T08a] result.text nie jest stringiem: {type(result.text)}"
        )
        assert isinstance(result.reverse_map, dict), (
            f"[T08a] result.reverse_map nie jest dict: {type(result.reverse_map)}"
        )

    def test_text_with_existing_token_pattern_not_doubled(self):
        """
        Edge case / regresja: tekst zawierający ciąg wyglądający jak token
        (np. FIRMA_001) nie powinien być pseudonimizowany ponownie.
        # v1.0
        """
        state = _make_state()
        text_with_token = "Kontrahent: FIRMA_001, ul. Zielona 1, 00-001 Kraków."

        result: PipelineResult = pseudonymize_document(text_with_token, state)

        # FIRMA_001 nie powinien dostać kolejnego nesting (FIRMA_002 za FIRMA_001)
        # Sprawdzamy, że nie ma tokenu który w reverse_map wskazuje na inny token
        nested = [
            (tok, val)
            for tok, val in result.reverse_map.items()
            if re.search(r"\b[A-Z_]{3,}_\d{3}\b", val)
        ]
        assert not nested, (
            f"[T08c] Zagnieżdżone tokeny w reverse_map (token→token): {nested}"
        )


# ---------------------------------------------------------------------------
# T09 — layers/numeric.py (numer_klienta, numer_faktury, numer_umowy)
# ---------------------------------------------------------------------------

class TestNumericLayer:
    """Testy jednostkowe apply_numeric_layer — bez pełnego pipeline'u."""

    @pytest.fixture(autouse=True)
    def _state(self):
        from pipeline_core import PipelineState, TokenAllocator
        from layers.numeric import apply_numeric_layer
        self._make = lambda text: (
            lambda s: (apply_numeric_layer(s), s)[1]
        )(PipelineState(text=text, allocator=TokenAllocator()))
        self._apply = apply_numeric_layer
        self._PipelineState = PipelineState
        self._TokenAllocator = TokenAllocator

    def _run(self, text: str):
        from pipeline_core import PipelineState, TokenAllocator
        from layers.numeric import apply_numeric_layer
        s = PipelineState(text=text, allocator=TokenAllocator())
        apply_numeric_layer(s)
        return s

    # ── numer_klienta ────────────────────────────────────────────────────────

    def test_kl_5digit_masked(self):
        """KL-66634 (5 cyfr) → zamaskowane jako NUMER_xxx. [T09a]"""
        s = self._run("Klient: KL-66634")
        assert "KL-66634" not in s.text, f"Wyciek KL-66634: {s.text!r}"
        assert "NUMER_" in s.text, f"Brak tokenu NUMER_: {s.text!r}"

    def test_kl_5digit_b_masked(self):
        """KL-15884 (5 cyfr) → zamaskowane. [T09b]"""
        s = self._run("Numer klienta: KL-15884")
        assert "KL-15884" not in s.text, f"Wyciek KL-15884: {s.text!r}"

    def test_kl_3digit_not_masked(self):
        """KL-123 (3 cyfry — za krótki) → NIE zamaskowane. [T09c]"""
        s = self._run("Kod: KL-123")
        assert "KL-123" in s.text, f"Błędne maskowanie KL-123: {s.text!r}"
        assert len(s.allocator.reverse_map) == 0, \
            f"Niespodziewany token: {s.allocator.reverse_map}"

    # ── numer_faktury ────────────────────────────────────────────────────────

    def test_faktura_fv_format_masked(self):
        """FV-03422/04/2021 → zamaskowane. [T09d]"""
        s = self._run("Faktura: FV-03422/04/2021")
        assert "FV-03422/04/2021" not in s.text, \
            f"Wyciek FV-03422/04/2021: {s.text!r}"

    def test_faktura_vat_format_masked(self):
        """VAT/2021/0353 → zamaskowane. [T09e]"""
        s = self._run("Nr faktury: VAT/2021/0353")
        assert "VAT/2021/0353" not in s.text, \
            f"Wyciek VAT/2021/0353: {s.text!r}"

    def test_faktura_numeric_format_masked(self):
        """9276/10/2023 → zamaskowane. [T09f]"""
        s = self._run("Faktura nr 9276/10/2023")
        assert "9276/10/2023" not in s.text, \
            f"Wyciek 9276/10/2023: {s.text!r}"

    def test_date_not_masked(self):
        """12/03/2024 (data — pierwszy człon 2 cyfry) → NIE zamaskowane. [T09g]"""
        s = self._run("Termin: 12/03/2024")
        assert "12/03/2024" in s.text, \
            f"Błędne maskowanie daty 12/03/2024: {s.text!r}"
        assert len(s.allocator.reverse_map) == 0, \
            f"Niespodziewany token: {s.allocator.reverse_map}"

    # ── numer_umowy ──────────────────────────────────────────────────────────

    def test_umowa_826_masked(self):
        """UMW/2024/826 → zamaskowane. [T09h]"""
        s = self._run("Umowa: UMW/2024/826")
        assert "UMW/2024/826" not in s.text, \
            f"Wyciek UMW/2024/826: {s.text!r}"

    def test_umowa_325_masked(self):
        """UMW/2023/325 → zamaskowane. [T09i]"""
        s = self._run("Umowa nr UMW/2023/325")
        assert "UMW/2023/325" not in s.text, \
            f"Wyciek UMW/2023/325: {s.text!r}"

    # ── tekst mieszany ───────────────────────────────────────────────────────

    def test_mixed_no_collision(self):
        """KL-66634 + FV-03422/04/2021 w jednym tekście → oba zamaskowane, zero kolizji. [T09j]"""
        s = self._run("Klient KL-66634, faktura FV-03422/04/2021")
        assert "KL-66634" not in s.text, f"Wyciek KL-66634: {s.text!r}"
        assert "FV-03422/04/2021" not in s.text, \
            f"Wyciek FV-03422/04/2021: {s.text!r}"
        tokens = list(s.allocator.reverse_map.keys())
        assert len(tokens) == 2, \
            f"Oczekiwano 2 tokeny, jest {len(tokens)}: {s.allocator.reverse_map}"
        assert len(set(tokens)) == len(tokens), \
            f"Kolizja tokenów: {tokens}"


# ---------------------------------------------------------------------------
# T10 — Testy integracyjne nowego pipeline (Coverage-Fix)
# ---------------------------------------------------------------------------

class TestNewPipelineIntegration:
    """
    Testy integracyjne run_pipeline_new() — przypadki odkryte w Coverage-Fix.

    Każdy test wywołuje run_pipeline_new() bezpośrednio (nie pseudonymize_document).
    process_ner w layers.ner_adapter jest mockowany — testy nie wymagają SpaCy.
    Dla przypadków z OSOBA: mock zwraca gotowy ner_reverse (jak w test_pipeline_new()).
    """

    def _run(
        self,
        text: str,
        ner_mock: dict | None = None,
    ) -> tuple[str, dict]:
        """Uruchamia run_pipeline_new z NER mockowanym.

        ner_mock — {token_id: value} przekazywane jako ner_reverse do process_ner.
        Bez ner_mock: process_ner zwraca ({}, {}) — brak encji NER.
        """
        import layers.ner_adapter as _ner_mod
        from pipeline_new import run_pipeline_new
        with patch.object(_ner_mod, "process_ner",
                          return_value=(ner_mock or {}, {})):
            return run_pipeline_new(text, anon_map={})

    # ── 1. NIP z separatorem OCR ──────────────────────────────────────────────

    def test_nip_ocr_dot_separator(self):
        """NIP 766-444-75.06 (OCR: myślnik→kropka) → zamaskowany. [TI-01]"""
        text, rev = self._run("NIP 766-444-75.06")
        assert "766-444-75.06" not in text, f"Wyciek NIP: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    # ── 2-4. Adresy ───────────────────────────────────────────────────────────

    def test_address_full_ul(self):
        """ul. Różana 3, 50-100 Wrocław → ADRES zamaskowany (prefix ul.). [TI-02]"""
        text, rev = self._run("Mieszka: ul. Różana 3, 50-100 Wrocław.")
        assert "Różana" not in text, f"Wyciek ulicy: {text!r}"
        assert "50-100" not in text, f"Wyciek kodu: {text!r}"
        assert any(k.startswith("ADRES_") for k in rev), \
            f"Brak tokenu ADRES w reverse_map: {rev}"

    def test_address_no_prefix(self):
        """Polna 196, 80-001 Kielce → ADRES zamaskowany (bez ul./al.). [TI-03]"""
        text, rev = self._run("Adres: Polna 196, 80-001 Kielce.")
        assert "Polna 196" not in text, f"Wyciek ulicy: {text!r}"
        assert "80-001" not in text, f"Wyciek kodu: {text!r}"
        assert any(k.startswith("ADRES_") for k in rev), \
            f"Brak tokenu ADRES w reverse_map: {rev}"

    def test_address_postal_only(self):
        """59-700 Bolesławiec → ADRES zamaskowany (sam kod + miasto). [TI-04]"""
        text, rev = self._run("Kod: 59-700 Bolesławiec")
        assert "59-700" not in text, f"Wyciek kodu: {text!r}"
        assert any(k.startswith("ADRES_") for k in rev), \
            f"Brak tokenu ADRES w reverse_map: {rev}"

    # ── 5-7. Warstwa numeric ──────────────────────────────────────────────────

    def test_numeric_kl(self):
        """KL-66634 → NUMER zamaskowany. [TI-05]"""
        text, rev = self._run("Klient: KL-66634")
        assert "KL-66634" not in text, f"Wyciek KL: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    def test_numeric_fv(self):
        """FV-03422/04/2021 → NUMER zamaskowany. [TI-06]"""
        text, rev = self._run("Faktura: FV-03422/04/2021")
        assert "FV-03422/04/2021" not in text, f"Wyciek FV: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    def test_numeric_umw(self):
        """UMW/2024/826 → NUMER zamaskowany. [TI-07]"""
        text, rev = self._run("Umowa: UMW/2024/826")
        assert "UMW/2024/826" not in text, f"Wyciek UMW: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    # ── 8-10. Warstwa legal ───────────────────────────────────────────────────

    def test_legal_case_sig(self):
        """I C 9170/2023 (sygnatura sądowa) → NUMER zamaskowany. [TI-08]"""
        text, rev = self._run("Sygn. akt I C 9170/2023")
        assert "I C 9170/2023" not in text, f"Wyciek sygnatury: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    def test_legal_km_sig(self):
        """Km 17224/2021 (sygnatura komornicza) → NUMER zamaskowany. [TI-09]"""
        text, rev = self._run("Sprawa Km 17224/2021")
        assert "Km 17224/2021" not in text, f"Wyciek Km: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    def test_legal_kw(self):
        """KA1K/00075119/1 (numer KW) → NUMER zamaskowany. [TI-10]"""
        text, rev = self._run("KW: KA1K/00075119/1")
        assert "KA1K/00075119/1" not in text, f"Wyciek KW: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    # ── 11. IBAN ──────────────────────────────────────────────────────────────

    def test_financial_iban(self):
        """PL61 1090 1014 0000 0712 1981 2874 → NUMER zamaskowany. [TI-11]"""
        iban_spaced  = "PL61 1090 1014 0000 0712 1981 2874"
        iban_compact = "PL61109010140000071219812874"
        text, rev = self._run(f"Konto: {iban_spaced}")
        assert iban_compact not in text, f"Wyciek IBAN (compact): {text!r}"
        assert iban_spaced not in text,  f"Wyciek IBAN (ze spacjami): {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    # ── 12-13. Dokumenty tożsamości ───────────────────────────────────────────

    def test_identity_passport(self):
        """AB1234567 (paszport: [A-Z]{2}\\d{7}) → NUMER zamaskowany. [TI-12]"""
        text, rev = self._run("Paszport: AB1234567")
        assert "AB1234567" not in text, f"Wyciek paszportu: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    def test_identity_id_card(self):
        """AOK171495 (dowód: [A-Z]{3}\\d{6}) → NUMER zamaskowany. [TI-13]"""
        text, rev = self._run("Dowód: AOK171495")
        assert "AOK171495" not in text, f"Wyciek dowodu: {text!r}"
        assert any(k.startswith("NUMER_") for k in rev), \
            f"Brak tokenu NUMER w reverse_map: {rev}"

    # ── 14. Tekst mieszany — zero kolizji ─────────────────────────────────────

    def test_mixed_no_token_collision(self):
        """
        Tekst mieszany (OSOBA + PESEL + adres + NIP + KL + FV) →
        wszystkie PII zamaskowane, wartości w reverse_map unikalne. [TI-14]
        """
        mixed = (
            "Jan Kowalski, PESEL 93102712345, ul. Różana 3, 50-100 Wrocław, "
            "NIP 766-444-75-06, KL-66634, FV-03422/04/2021"
        )
        text, rev = self._run(mixed, ner_mock={"OSOBA_001": "Jan Kowalski"})

        assert "Jan Kowalski"     not in text, f"Wyciek OSOBA: {text!r}"
        assert "93102712345"      not in text, f"Wyciek PESEL: {text!r}"
        assert "Różana"           not in text, f"Wyciek adresu: {text!r}"
        assert "766-444-75-06"    not in text, f"Wyciek NIP: {text!r}"
        assert "KL-66634"         not in text, f"Wyciek KL: {text!r}"
        assert "FV-03422/04/2021" not in text, f"Wyciek FV: {text!r}"

        values = list(rev.values())
        assert len(values) == len(set(values)), \
            f"Kolizja tokenów (nieunikalane wartości): {rev}"
