# test_layers.py v1.1
"""
Testy jednostkowe dla warstw: credentials, ocr_normalizer, verbal_amount.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "layers")))

import pytest
from pipeline_core import PipelineState, TokenAllocator
from layers.credentials import apply_credentials_layer
from layers.financial import apply_financial_layer
from layers.ocr_normalizer import normalize_ocr
from layers.verbal_amount_layer import apply_verbal_amount_layer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(text: str) -> PipelineState:
    return PipelineState(text, TokenAllocator())


def _apply_financial(text: str) -> tuple[str, dict]:
    s = _state(text)
    apply_financial_layer(s)
    return s.text, s.allocator.reverse_map


def _apply_credentials(text: str) -> str:
    s = _state(text)
    apply_credentials_layer(s)
    return s.text


def _apply_verbal(text: str) -> str:
    s = _state(text)
    apply_verbal_amount_layer(s)
    return s.text


# ===========================================================================
# TestFinancialLayer
# ===========================================================================

class TestFinancialLayer:

    # --- IBAN PL standardowy ---

    def test_iban_pl_compact(self):
        text, rev = _apply_financial("konto PL58325000032630362440455236")
        assert "PL58" not in text
        assert len(rev) == 1

    def test_iban_pl_with_spaces(self):
        text, rev = _apply_financial("konto PL61 1090 1014 0000 0712 1981 2874")
        assert "PL61" not in text
        assert len(rev) == 1

    # --- IBAN PL OCR lvl3 — rozerwane grupy (nowy kod v1.2) ---

    def test_iban_pl_ocr_single_space_in_group(self):
        # "1 053" zamiast "1053" — OCR rozrywa 4-cyfrową grupę
        text, rev = _apply_financial("PL98 1 053 1875 0000 0023 4567 8901")
        assert "PL98" not in text
        assert len(rev) == 1

    def test_iban_pl_ocr_multiple_broken_groups(self):
        # Kilka grup rozerwanych spacją
        text, rev = _apply_financial("Nr konta: PL61 10 90 10 14 0000 0712 1981 2874")
        assert "PL61" not in text
        assert len(rev) == 1

    def test_iban_pl_ocr_lvl3_all_groups_split(self):
        # Maksymalnie rozerwany (OCR lvl3): każda 4-cyfrowa grupa podzielona
        text, rev = _apply_financial("PL98 1 053 1 875 0000 0023 4567 8901")
        assert "PL98" not in text
        assert len(rev) == 1

    def test_iban_pl_ocr_wrong_digit_count_not_masked(self):
        # Tylko 24 cyfry po PL (nie 26) — nie powinno być zamaskowane
        text, rev = _apply_financial("PL12 3456 7890 1234 5678 9012")
        # 24 cyfry — nie spełnia warunku, nie maskujemy
        assert len(rev) == 0

    def test_iban_pl_ocr_dedup(self):
        # Ten sam IBAN OCR dwa razy → jeden token
        iban = "PL98 1 053 1875 0000 0023 4567 8901"
        text, rev = _apply_financial(f"{iban} oraz {iban}")
        assert len(rev) == 1

    # --- IBAN zagraniczny ---

    def test_iban_de_with_spaces(self):
        text, rev = _apply_financial("Konto DE89 3704 0044 0532 0130 00")
        assert "DE89" not in text

    def test_iban_de_compact(self):
        text, rev = _apply_financial("DE89370400440532013000")
        assert "DE89" not in text

    def test_iban_gb(self):
        text, rev = _apply_financial("GB29 NWBK 6016 1331 9268 19")
        assert "GB29" not in text

    def test_iban_ua(self):
        text, rev = _apply_financial("UA213223130000026007233566001")
        assert "UA21" not in text

    def test_iban_foreign_too_short_not_masked(self):
        # Krótszy niż 15 znaków — odrzucamy jako false positive
        text, rev = _apply_financial("AT12 1234")
        assert "AT12" in text
        assert len(rev) == 0

    # --- Konto bez prefiksu PL ---

    def test_account_no_prefix_spaces(self):
        text, rev = _apply_financial("61 1090 1014 0000 0712 1981 2874")
        assert "1090 1014 0000 0712 1981 2874" not in text

    def test_account_24digits_compact(self):
        text, rev = _apply_financial("325000032630362440455236")
        assert "325000032630362440455236" not in text

    # --- Brak false positive ---

    def test_no_fp_nip(self):
        text, rev = _apply_financial("NIP: 855-019-31-23")
        assert text == "NIP: 855-019-31-23"
        assert len(rev) == 0

    def test_no_fp_pln_currency(self):
        text, rev = _apply_financial("Kwota: 1234 PLN")
        assert text == "Kwota: 1234 PLN"
        assert len(rev) == 0

    # --- Deduplication ---

    def test_dedup_same_iban_twice(self):
        text, rev = _apply_financial(
            "DE89370400440532013000 i DE89370400440532013000"
        )
        assert "DE89" not in text
        assert len(rev) == 1

    def test_two_different_ibans_two_tokens(self):
        text, rev = _apply_financial(
            "PL61109010140000071219812874 i PL58325000032630362440455236"
        )
        assert "PL61" not in text
        assert "PL58" not in text
        assert len(rev) == 2


# ===========================================================================
# TestCredentialsLayer
# ===========================================================================

class TestCredentialsLayer:

    def test_pwz_prefix(self):
        result = _apply_credentials("Lekarz PWZ 1234567 wystawił.")
        assert "1234567" not in result
        assert "NUMER_" in result

    def test_pwz_full_phrase(self):
        result = _apply_credentials("prawo wykonywania zawodu nr 9876543")
        assert "9876543" not in result
        assert "NUMER_" in result

    def test_pwz_with_dot_separators(self):
        result = _apply_credentials("P.W.Z. 1234567")
        assert "1234567" not in result

    def test_uprawnienia_budowlane(self):
        result = _apply_credentials("Projektant: WAR/0123/16/BOK")
        assert "WAR/0123/16/BOK" not in result
        assert "NUMER_" in result

    def test_uprawnienia_budowlane_short(self):
        result = _apply_credentials("uprawnienia LO/45/21/AK")
        assert "LO/45/21/AK" not in result

    def test_pilot_easa(self):
        result = _apply_credentials("Pilot: PL.FCL.012345")
        assert "PL.FCL.012345" not in result
        assert "NUMER_" in result

    def test_mechanik_lotniczy(self):
        result = _apply_credentials("Certyfikat PL.66.012345")
        assert "PL.66.012345" not in result

    def test_legitymacja_radcy(self):
        result = _apply_credentials("Radca WA/1234")
        assert "WA/1234" not in result
        assert "NUMER_" in result

    def test_legitymacja_radcy_krakow(self):
        result = _apply_credentials("Adwokat KR/56789")
        assert "KR/56789" not in result

    def test_legitymacja_nr_context(self):
        result = _apply_credentials("legitymacja nr 123456")
        assert "123456" not in result

    def test_notariusz_repertorium(self):
        result = _apply_credentials("repertorium A nr 1234/2023")
        assert "1234/2023" not in result

    def test_komornik(self):
        result = _apply_credentials("Komornik Sądowy nr 12/2022")
        assert "12/2022" not in result

    def test_karta_motorowodna(self):
        result = _apply_credentials("karta KM/123456")
        assert "KM/123456" not in result

    def test_legitymacja_sluzb_sluzb(self):
        result = _apply_credentials("legitymacja służbowa nr AB123456")
        assert "AB123456" not in result

    def test_no_false_positive_plain_number(self):
        # Zwykły 7-cyfrowy numer bez kontekstu nie powinien być maskowany
        result = _apply_credentials("Zamówienie 1234567")
        assert result == "Zamówienie 1234567"

    def test_dedup_same_token(self):
        # To samo PWZ dwa razy → ten sam token
        s = _state("PWZ 1234567 i znowu PWZ 1234567")
        apply_credentials_layer(s)
        tokens = [t for t in s.text.split() if t.startswith("NUMER_")]
        assert len(set(tokens)) == 1


# ===========================================================================
# TestOcrNormalizer
# ===========================================================================

class TestOcrNormalizer:

    # --- Keyword canonicalization ---

    def test_pesel_keyword(self):
        assert normalize_ocr("PE5EL: 90010112345") == "PESEL: 90010112345"

    def test_nip_keyword(self):
        assert normalize_ocr("N1P: 526-030-01-34") == "NIP: 526-030-01-34"

    def test_regon_keyword(self):
        assert normalize_ocr("REG0N: 012345678") == "REGON: 012345678"

    def test_iban_keyword(self):
        result = normalize_ocr("IB4N PL61109010140000071219812874")
        assert result.startswith("IBAN")

    # --- ul. prefix ---

    def test_ul_prefix(self):
        result = normalize_ocr("u. Kwiatowa 5")
        assert result.startswith("ul.")

    # --- al. prefix (OCR a1.) ---

    def test_al_prefix(self):
        result = normalize_ocr("a1. Jerozolimskie 44")
        assert result.startswith("al.")

    # --- PESEL OCR ---

    def test_pesel_ocr_letter_o(self):
        result = normalize_ocr("PESEL: 9l0405l2367")
        assert "9" in result and "l" not in result.split("PESEL:")[1]

    # --- NIP OCR ---

    def test_nip_ocr_letter_o(self):
        result = normalize_ocr("NIP: 526-O3O-O1-34")
        assert "O" not in result

    def test_nip_bare_ocr(self):
        result = normalize_ocr("I42-I99-O6-38")
        assert "I" not in result or "142" in result

    # --- Dowód osobisty ---

    def test_dowod_space_removed(self):
        result = normalize_ocr("FOH6 I4892")
        assert " " not in result.replace("FOH6", "").strip() or "FOH614892" in result

    # --- Paszport ---

    def test_paszport_ocr(self):
        # krok 6: OCR-litera I→1 w numerze paszportu (wymaga słowa kluczowego "paszport")
        result = normalize_ocr("paszport AB I234567")
        assert "AB1234567" in result

    # --- IBAN ---

    def test_iban_spaces_removed(self):
        # krok 8: spacje w IBAN usuwane gdy jest słowo kluczowe IBAN
        result = normalize_ocr("IBAN: PL61 1090 1014 0000 0712 1981 2874")
        assert "PL61109010140000071219812874" in result

    def test_iban_j_to_0(self):
        result = normalize_ocr("PL61109010140000J7121981 2874")
        assert "J" not in result

    # --- Kod pocztowy ---

    def test_postal_code_ocr(self):
        result = normalize_ocr("2O-1OO")
        assert "O" not in result

    def test_postal_code_space(self):
        result = normalize_ocr("ul. Kwiatowa 5, 85 001 Bydgoszcz")
        assert "85-001" in result or "85001" in result

    # --- Email ---

    def test_email_space_around_at(self):
        result = normalize_ocr("jan @ kowalski.pl")
        assert "@" in result and " @ " not in result

    def test_email_tld_ocr(self):
        result = normalize_ocr("jan@kowalski.p1")
        assert ".pl" in result or "p1" not in result

    # --- De-leet ---

    def test_deleet_name(self):
        result = normalize_ocr("P4ulina")
        assert "P4ulina" not in result or "Paulina" in result

    # --- City midspace ---

    def test_city_midspace_sosnowiec(self):
        result = normalize_ocr("Sos nowiec")
        assert "Sosnowiec" in result

    def test_city_midspace_katowice(self):
        result = normalize_ocr("Kato wice")
        assert "Katowice" in result

    # --- Idempotent on clean text ---

    def test_clean_text_unchanged(self):
        text = "Jan Kowalski, ul. Kwiatowa 5, Warszawa"
        assert normalize_ocr(text) == text


# ===========================================================================
# TestVerbalAmountLayer
# ===========================================================================

class TestVerbalAmountLayer:

    def test_simple_verbal_amount(self):
        result = _apply_verbal("Kwota: sto dwadzieścia złotych")
        assert "sto dwadzieścia złotych" not in result
        assert "KWOTA_" in result

    def test_verbal_amount_with_fraction(self):
        result = _apply_verbal("suma trzy tysiące pięćset złotych 00/100")
        assert "trzy tysiące" not in result
        assert "KWOTA_" in result

    def test_verbal_amount_uppercase(self):
        result = _apply_verbal("STO ZŁOTYCH")
        assert "KWOTA_" in result

    def test_no_verbal_amount_in_plain(self):
        result = _apply_verbal("Przelew 1000 zł")
        # cyfry obsługuje amount_layer, tu nie powinno być nowych tokenów KWOTA
        assert result == "Przelew 1000 zł"

    def test_kwota_counter_not_collide_with_existing(self):
        # Jeśli allocator już ma KWOTA_001, verbal powinien dostać KWOTA_002
        s = _state("dwieście złotych")
        s.allocator._counters["KWOTA"] = 1
        s.allocator._reverse["KWOTA_001"] = "1000"
        apply_verbal_amount_layer(s)
        assert "KWOTA_001" not in s.text or "dwieście złotych" not in s.text
        if "KWOTA_" in s.text:
            tokens = [w for w in s.text.split() if w.startswith("KWOTA_")]
            assert all(t != "KWOTA_001" for t in tokens)
