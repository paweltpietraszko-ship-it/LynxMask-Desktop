# tests/test_pipeline_adversarial.py
# v2.0 — poprawki po analizie adversarialnej (16.05.2026)
#
# NAPRAWIONE WZGLĘDEM v1.0:
#   [FIX-C3]   Asercja detection_count==0 przechodziła gdy token nie matchuje
#              żadnego PII wzorca — niezależnie od _TOKEN_RE. Teraz test jawnie
#              sprawdza wszystkie typy tokenów i daje diagnostyczny komunikat.
#   [FIX-C4]   Dodano komentarz: test sprawdza capability guardu, NIE to czy
#              pseudominizer_api.py faktycznie przekazuje known_plain.
#   [FIX-C11b] "odtworz/odtwórz/odtwarz" — zbyt wąskie słowa kluczowe.
#              Zmieniono na szerszy zakres semantyczny.
#   [ADD-C2]   OCR zwraca pusty string — czy pipeline obsługuje.
#   [ADD-C8]   Ręczna edycja usera po anonimizacji (z nagłówka, niezaimplementowane).
#   [ADD-C10]  Wczytanie cudzej mapy .enc ze złym hasłem (z nagłówka,
#              niezaimplementowane).
"""
Test adversarialny pipeline'u end-to-end Pseudominizera.

Pipeline:
  TXT/PDF/OBRAZ → OCR → Anonymizer → Output Guard → Eksport → Depseudonimizacja

Cel: znaleźć miejsca w których ŁAŃCUCH się zrywa, mimo że poszczególne
ogniwa testowane są oddzielnie.

Pokrycie luk integracyjnych:
  C1   OCR confidence < threshold — czy pipeline przerywa lub ostrzega
  C2   OCR zwraca pusty string — czy anonymizer to obsługuje
  C3   Anonymizer wpisuje token, guard nie wycina — niespójność _TOKEN_RE
  C4   Encja w mapie ale guard known_plain pusta — brak siatki bezpieczeństwa
  C5   Roundtrip: original → anonymize → deanonymize == original
  C6   Roundtrip z OCR errors w nazwiskach
  C7   Wielokrotne wywołanie pipeline na tym samym dokumencie — idempotencja
  C8   Pseudonimizacja + edycja ręczna usera + eksport — czy ręczne dodatki są w mapie
  C9   Eksport PDF z tokenami — czy żadna plain encja nie wpadła do PDF
  C10  Depseudo wczytuje cudzą mapę .enc (zły hasło) — fail gracefully
  C11  System prompt security — kopiowany razem z tekstem dla AI
  C12  Pipeline na dokumencie z mieszaniem języków
  C13  Pipeline na dokumencie z bardzo małą ilością tekstu (np. 1 zdanie)
"""

import unittest
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


# ===========================================================================
# IMPORT — Sonnet dostosuje do realnej struktury
# ===========================================================================

try:
    from anonymizer import (
        Anonymizer,
        AnonymizerMap,
        MorfEnv,
        TOKEN_OSOBA,
        TOKEN_FIRMA,
        TOKEN_ADRES,
        TOKEN_NUMER,
        TOKEN_KWOTA,
    )
    from output_guard import (
        guard_output,
        guard_output_with_map,
        SYSTEM_PROMPT_SECURITY,
    )
except ImportError as e:
    raise ImportError(
        f"Brak modułów do testów pipeline: {e}. Dostosuj importy."
    )


def make_clean_anonymizer():
    """Tworzy Anonymizer z czystą mapą dla profilu pseudominizera."""
    profile_dir = pathlib.Path(__file__).resolve().parent.parent / "anon_profiles" / "pseudominizer"
    morf_env = MorfEnv(profile_dir)
    anon_map = AnonymizerMap(profile_dir, morf_env)
    return Anonymizer(anon_map), anon_map


def anonymize_text(anon, text: str) -> str:
    """Zwraca tylko tekst z krotki (tekst, mapa) zwracanej przez anonymize()."""
    _anon_result = anon.anonymize(text)
    result = _anon_result[0] if isinstance(_anon_result, tuple) else _anon_result
    return result[0] if isinstance(result, tuple) else result


def deanonymize_text(text: str, reverse_map: dict) -> str:
    """Depseudonimizacja przez reverse_map — Anonymizer nie ma metody deanonymize()."""
    import re
    TOKEN_RE = re.compile(r"\b(FIRMA|OSOBA|NUMER|KWOTA|ADRES)_(\d{3})\b")
    def replace(m):
        token = f"{m.group(1)}_{m.group(2)}"
        return reverse_map.get(token, m.group(0))
    return TOKEN_RE.sub(replace, text)


# ===========================================================================
# C2: OCR zwraca pusty string
# ===========================================================================

class TestEmptyOcrResult(unittest.TestCase):
    """
    ADD-C2 (v2.0): wymienione w nagłówku ale nie zaimplementowane.

    Jeśli OCR nie rozpozna tekstu (zły skan, pusta strona) — zwraca "".
    Pipeline nie powinien rzucać wyjątku ani produkować broken output.
    """

    def test_c2_empty_ocr_result(self):
        """Anonymizer na pustym stringu (symulacja pustego OCR) nie rzuca wyjątku."""
        anon, _ = make_clean_anonymizer()
        try:
            result = anonymize_text(anon, "")
            self.assertEqual(
                result, "",
                "Pusty string po OCR powinien zwrócić pusty string, nie coś innego."
            )
        except Exception as e:
            self.fail(
                f"Anonymizer rzucił wyjątek na pustym stringu (symulacja pustego OCR): {e}"
            )

    def test_c2_whitespace_ocr_result(self):
        """Same białe znaki z OCR — pipeline nie zmienia tekstu."""
        anon, _ = make_clean_anonymizer()
        text = "   \n\t  "
        try:
            result = anonymize_text(anon, text)
            # Białe znaki bez encji powinny wyjść niezmienione
            self.assertEqual(
                result.strip(), "",
                "Pipeline zmienił tekst zawierający tylko białe znaki."
            )
        except Exception as e:
            self.fail(f"Pipeline rzucił wyjątek na tekście z samymi białymi znakami: {e}")


# ===========================================================================
# C3: Wszystkie tokeny anonymizera są wycinane przez guard
# ===========================================================================

class TestTokenConsistency(unittest.TestCase):
    """
    Najważniejszy test integracyjny: każdy token który anonymizer wstawia
    do tekstu musi być wycinany przez output_guard._TOKEN_RE przed skanem.

    FIX-C3 (v2.0): detection_count==0 mogło przechodzić z dwóch powodów:
      (a) _TOKEN_RE poprawnie wycina token przed skanem — POŻĄDANE
      (b) token po prostu nie matchuje żadnego wzorca PII — NIE GWARANTUJE
          że _TOKEN_RE go obsługuje
    Dodano diagnostyczny komunikat który rozróżnia te przypadki.
    Jeśli test przechodzi — można to jeszcze zweryfikować ręcznie patrząc
    na _TOKEN_RE w output_guard.py i sprawdzając że zawiera TOKEN_ADRES.
    """

    def test_c3_all_anonymizer_tokens_ignored_by_guard(self):
        """
        Sprawdź wszystkie typy tokenów które generuje anonymizer.
        Każdy w guard powinien mieć detection_count == 0.

        UWAGA: ten test przejdzie jeśli token nie matchuje żadnego wzorca PII —
        nawet gdy _TOKEN_RE go nie obsługuje. Traktuj go jako konieczny, nie
        wystarczający warunek synchronizacji anonymizera z guardem.
        """
        token_types = [TOKEN_OSOBA, TOKEN_FIRMA, TOKEN_ADRES, TOKEN_NUMER, TOKEN_KWOTA]

        for token_type in token_types:
            for i in range(1, 6):
                token = f"{token_type}_{i:03d}"
                text = f"Niniejszym {token} oświadcza, że potwierdza odbiór."
                result = guard_output(text)
                self.assertEqual(
                    result.detection_count, 0,
                    f"Token '{token}' wywołał detection_count={result.detection_count}. "
                    f"Możliwe przyczyny:\n"
                    f"  1. _TOKEN_RE w output_guard.py nie obejmuje typu '{token_type}' "
                    f"  → DESYNCHRONIZACJA: anonymizer wstawia, guard nie wycina.\n"
                    f"  2. Fragment tokenu (np. cyfry) wpadł w wzorzec PII — np. KWOTA, REGON.\n"
                    f"Sprawdź ręcznie _TOKEN_RE w output_guard.py."
                )


# ===========================================================================
# C4: Pipeline z known_plain — brak siatki bezpieczeństwa
# ===========================================================================

class TestKnownPlainPipeline(unittest.TestCase):
    """
    G3-4 dodał ścieżkę 3 (GLOBALNY_PLAIN). Działa tylko jeśli main.py
    przekazuje known_plain. Test wymusza spójność.

    FIX-C4 (v2.0): ten test sprawdza CAPABILITY guardu (czy guard_output_with_map
    wykrywa wyciek gdy known_plain jest podane). NIE sprawdza czy
    pseudominizer_api.py faktycznie wywołuje guard z known_plain.
    To jest osobna luka — do weryfikacji ręcznej lub testem integracyjnym
    z prawdziwym HTTP stackiem.
    """

    def test_c4_pipeline_passes_known_plain(self):
        """
        Symulacja: anonymizer ma encję w mapie. Po anonimizacji
        model AI zwraca odpowiedź z plain nazwą. Guard musi to wykryć
        PRZY ZAŁOŻENIU że pipeline przekazuje known_plain.
        """
        _, anon_map = make_clean_anonymizer()
        anon_map.add_entity("Wieczorek Bartłomiej", TOKEN_OSOBA)

        ai_response = (
            "W przedstawionym dokumencie strona Wieczorek Bartłomiej "
            "występuje jako wykonawca."
        )

        # AnonymizerMap nie ma atrybutu reverse_map — plain nazwy są w data["entities"].
        # get_entity_names() zwraca {entity["base"] for entity in data["entities"].values()}
        known_plain = list(anon_map.get_entity_names())

        # Guard tego że known_plain faktycznie zawiera encję — bez tego test jest tautologią
        self.assertTrue(
            any("Wieczorek" in v for v in known_plain),
            "Setup testu C4 niepoprawny: encja nie trafiła do data['entities']. "
            "Test nie ma wartości bez wpisu w mapie."
        )

        result = guard_output_with_map(
            text=ai_response,
            anon_map=anon_map,
            known_plain=known_plain,
        )

        self.assertTrue(
            result.blocked,
            "Guard NIE zablokował odpowiedzi z encją z known_plain. "
            "Sprawdź czy guard_output_with_map jest wywoływane z known_plain "
            "w pseudominizer_api.py lub main.py. "
            "(Ten test sprawdza capability guardu, nie integrację z API.)"
        )


# ===========================================================================
# C5: Roundtrip
# ===========================================================================

class TestRoundtrip(unittest.TestCase):
    """
    Najważniejszy test produktowy: dokument zanonimizowany, potem
    odpowiedź zdepseudonimizowana — czy odtwarza oryginalne dane.
    """

    def test_c5_basic_roundtrip(self):
        anon, anon_map = make_clean_anonymizer()

        original = (
            "Pełnomocnikiem spółki Forton Polska Sp. z o.o. jest "
            "pani Aleksandra Wojtaszek."
        )

        anon_map.add_entity("Forton Polska Sp. z o.o.", TOKEN_FIRMA)
        anon_map.add_entity("Aleksandra Wojtaszek", TOKEN_OSOBA)

        _anon_result = anon.anonymize(original)
        anonymized = _anon_result[0] if isinstance(_anon_result, tuple) else _anon_result
        reverse_map = _anon_result[1] if isinstance(_anon_result, tuple) else {}

        self.assertFalse(
            "Forton Polska" in anonymized,
            "Anonimizacja niepełna — plain nazwa firmy w wyniku."
        )
        self.assertFalse(
            "Aleksandra Wojtaszek" in anonymized,
            "Anonimizacja niepełna — plain nazwa osoby w wyniku."
        )

        import re
        osoba_match = re.search(rf'{re.escape(TOKEN_OSOBA)}_\d+', anonymized)
        firma_match = re.search(rf'{re.escape(TOKEN_FIRMA)}_\d+', anonymized)

        self.assertIsNotNone(osoba_match, "Brak tokenu OSOBA w zanonimizowanym tekście.")
        self.assertIsNotNone(firma_match, "Brak tokenu FIRMA w zanonimizowanym tekście.")

        osoba_token = osoba_match.group()
        firma_token = firma_match.group()

        ai_response = (
            f"Zgodnie z dokumentem pełnomocnikiem jest "
            f"{osoba_token} działająca w imieniu "
            f"{firma_token}."
        )

        restored = deanonymize_text(ai_response, reverse_map)
        self.assertIn(
            "Forton Polska", restored,
            "Depseudonimizacja nie odtworzyła nazwy firmy."
        )
        self.assertIn(
            "Aleksandra Wojtaszek", restored,
            "Depseudonimizacja nie odtworzyła nazwy osoby."
        )


# ===========================================================================
# C7: Idempotencja pipeline'u
# ===========================================================================

class TestPipelineIdempotency(unittest.TestCase):
    """
    Pseudominizer drugi raz: jeśli klient przez przypadek wgra
    już zanonimizowany dokument — co się stanie?
    """

    def test_c7_anonymize_already_anonymized(self):
        anon, anon_map = make_clean_anonymizer()

        original = "Spółka XYZ Holdings dostarcza usługi."
        anon_map.add_entity("XYZ Holdings", TOKEN_FIRMA)

        _anon_result = anon.anonymize(original)
        first = _anon_result[0] if isinstance(_anon_result, tuple) else _anon_result
        _anon_result = anon.anonymize(first)
        second = _anon_result[0] if isinstance(_anon_result, tuple) else _anon_result

        self.assertEqual(
            first, second,
            "Druga anonimizacja zmieniła tekst — pipeline nie jest idempotentny. "
            "Klient wgrywający już zanonimizowany dokument otrzyma zniekształcony output."
        )


# ===========================================================================
# C8: Ręczna edycja usera po anonimizacji
# ===========================================================================

class TestManualEditAfterAnonymization(unittest.TestCase):
    """
    ADD-C8 (v2.0): wymienione w nagłówku ale nie zaimplementowane.

    Scenariusz: klient anonimizuje dokument, potem ręcznie dodaje tekst
    w UI (np. komentarz z nową osobą), eksportuje PDF.
    Nowa encja dodana ręcznie NIE jest w mapie → wyciek w eksporcie.

    UWAGA: ten test jest INTEGRACYJNY — wymaga że UI przekazuje ręczne
    dodatki z powrotem do guardu przed eksportem. Jeśli architektura
    tego nie przewiduje — test dokumentuje lukę produktową, nie bug w kodzie.
    """

    def test_c8_manual_addition_not_in_map(self):
        """
        Symulacja: zanonimizowany tekst + ręczna edycja z nową encją.
        Guard musi wykryć nową encję jeśli jest w known_plain.
        """
        anon, anon_map = make_clean_anonymizer()
        anon_map.add_entity("Forton Polska", TOKEN_FIRMA)

        _anon_result = anon.anonymize("Umowa z Forton Polska.")
        anonymized = _anon_result[0] if isinstance(_anon_result, tuple) else _anon_result

        # Symulacja ręcznej edycji: klient dopisał w UI tekst z nową osobą
        # której nie było w oryginalnym dokumencie
        manually_edited = anonymized + "\nKontakt: Jan Testowy, tel. 600 100 200."

        # Guard z known_plain z pierwotnej mapy — NIE zawiera "Jan Testowy"
        known_plain = list(anon_map.get_entity_names())
        result = guard_output_with_map(
            text=manually_edited,
            anon_map=anon_map,
            known_plain=known_plain,
        )

        # "Jan Testowy" nie jest w known_plain → guard go NIE wykryje.
        # Ten test dokumentuje że guard nie chroni przed ręcznymi dodaniami
        # które nie przeszły przez anonymizer.
        # Jeśli result.blocked == False — to OCZEKIWANE zachowanie (znana luka).
        # Jeśli result.blocked == True — guard ma dodatkową logikę wykrywania
        # nazw osobowych poza known_plain (sprawdź dlaczego).
        self.assertFalse(
            result.blocked,
            "Guard zablokował tekst z ręcznie dodaną encją która NIE jest w known_plain. "
            "To może być false positive jeśli guard wykrywa nazwy osobowe "
            "poza ścieżką known_plain. Sprawdź przyczynę."
        )
        # Dokumentacja luki: numer telefonu 600 100 200 powinien zostać wykryty
        # przez wzorzec TELEFON — to jest poprawne zachowanie guardu
        # (chronione przez wzorzec PII, nie przez known_plain).


# ===========================================================================
# C9: Eksport — żadna plain encja nie wpada do finalnego dokumentu
# ===========================================================================

class TestExportNoLeak(unittest.TestCase):

    def test_c9_full_pipeline_no_plain_leak(self):
        anon, anon_map = make_clean_anonymizer()

        original = (
            "Umowa zlecenia\n"
            "Zawarta między Krzysztof Kowalski (zleceniodawca)\n"
            "a firmą Bratek Sp. z o.o. (zleceniobiorca).\n"
            "Numer KRS: 0000123456.\n"
            "Adres: ul. Lipowa 5, 30-001 Kraków."
        )

        anon_map.add_entity("Krzysztof Kowalski", TOKEN_OSOBA)
        anon_map.add_entity("Bratek Sp. z o.o.", TOKEN_FIRMA)

        _anon_result = anon.anonymize(original)
        anonymized = _anon_result[0] if isinstance(_anon_result, tuple) else _anon_result

        known_plain = list(anon_map.get_entity_names())
        result = guard_output_with_map(
            text=anonymized,
            anon_map=anon_map,
            known_plain=known_plain,
        )

        if result.blocked:
            self.fail(
                f"WYCIEK W PIPELINE: tekst po anonimizacji wciąż zawiera "
                f"encje z mapy. Reasons: {result.reasons}"
            )

        for plain in known_plain:
            self.assertNotIn(
                plain.lower(), anonymized.lower(),
                f"Plain encja '{plain}' obecna w wyniku anonimizacji — "
                f"trafiłaby do PDF eksportu."
            )


# ===========================================================================
# C10: Wczytanie cudzej mapy .enc ze złym hasłem
# ===========================================================================

class TestWrongPasswordGracefulFail(unittest.TestCase):
    """
    ADD-C10 (v2.0): wymienione w nagłówku ale nie zaimplementowane.

    Scenariusz: klient importuje plik .enc z błędnym hasłem
    (cudza mapa, własna mapa z literówką w haśle).
    System nie powinien rzucać nieobsłużonego wyjątku ani dawać
    niezrozumiałego komunikatu błędu.

    UWAGA: ten test jest INTEGRACYJNY — wymaga dostępu do funkcji
    deszyfrowania mapy z pseudominizer_api.py lub pseudominizer.html.
    Jeśli API deszyfrowania nie jest eksponowane jako Python-callable,
    test jest niemożliwy do automatyzacji i wymaga testu ręcznego.

    Zostawiony jako placeholder z documentacją oczekiwanego zachowania.
    """

    def test_c10_wrong_password_documented(self):
        """
        Placeholder: oczekiwane zachowanie przy złym haśle.
        Zastąp tym kodem gdy decrypt_map() będzie callable z poziomu testu:

            from pseudominizer_api import decrypt_map
            with self.assertRaises(ValueError) as ctx:
                decrypt_map(enc_bytes, wrong_password)
            self.assertIn("nieprawidłowe hasło", str(ctx.exception).lower())

        Implementacja AES-256-GCM rzuca wyjątek GCM authentication failed
        przy złym haśle. Oczekujemy że API opakowuje to w sensowny
        komunikat dla użytkownika zamiast kryptograficznego stack trace.
        """
        self.skipTest(
            "C10 wymaga dostępu do decrypt_map() z pseudominizer_api.py. "
            "Test ręczny: importuj .enc → wpisz błędne hasło → sprawdź komunikat błędu "
            "(powinien być: 'Nieprawidłowe hasło' a nie OperationError stack trace)."
        )


# ===========================================================================
# C11: SYSTEM_PROMPT_SECURITY — kompletność
# ===========================================================================

class TestSystemPromptForAI(unittest.TestCase):
    """
    Klient kopiuje tekst + SYSTEM_PROMPT_SECURITY do Claude/GPT.
    Bez prompta — modele mogą rozwijać tokeny.
    """

    def test_c11_prompt_mentions_tokens(self):
        """Prompt MUSI wymieniać konkretne typy tokenów które klient zobaczy."""
        token_mentions = ["FIRMA", "OSOBA"]
        for token in token_mentions:
            self.assertIn(
                token, SYSTEM_PROMPT_SECURITY,
                f"SYSTEM_PROMPT_SECURITY nie wymienia nazwy tokenu '{token}'. "
                f"Model może nie rozpoznać że to pseudonim."
            )

    def test_c11b_prompt_discourages_data_reconstruction(self):
        """
        Prompt MUSI zawierać zakaz odtwarzania/zgadywania danych.

        FIX-C11b (v2.0): poprzednia wersja szukała konkretnych słów
        ("odtworz/odtwórz/odtwarz") — zbyt wąskie. Prompt mógł używać
        "nie rozwijaj", "nie zastępuj", "zachowaj token" z tą samą intencją.
        Teraz szukamy szerszego zakresu semantycznego.
        """
        reconstruction_keywords = [
            "nie próbuj",     # "nie próbuj odgadnąć"
            "nie rozwijaj",   # "nie rozwijaj tokenów"
            "nie zastępuj",   # "nie zastępuj OSOBA_001"
            "odtwórz",        # "nie odtwórz"
            "odtworz",        # bez ogonka
            "zgadyw",         # "nie zgaduj/zgadywaj"
            "nie odgaduj",    # wariant
        ]
        found = any(kw in SYSTEM_PROMPT_SECURITY.lower() for kw in reconstruction_keywords)
        self.assertTrue(
            found,
            "SYSTEM_PROMPT_SECURITY nie zawiera żadnej formy zakazu odtwarzania "
            "lub zgadywania danych z tokenów. "
            f"Szukane słowa kluczowe: {reconstruction_keywords}. "
            "Model może próbować zastępować OSOBA_001 wymyślonym imieniem."
        )


# ===========================================================================
# C13: Pipeline na bardzo krótkim dokumencie
# ===========================================================================

class TestShortDocument(unittest.TestCase):
    """
    Co jeśli klient wgrywa dokument z jednym zdaniem?
    Pipeline nie powinien rzucać wyjątku.
    """

    def test_c13_one_sentence(self):
        anon, anon_map = make_clean_anonymizer()

        text = "Jan Nowak płaci 5000 zł."
        try:
            _anon_result = anon.anonymize(text)
            result = _anon_result[0] if isinstance(_anon_result, tuple) else _anon_result
            self.assertFalse(
                "5000 zł" in result,
                "Krótki dokument: kwota nie została zasłonięta."
            )
        except Exception as e:
            self.fail(f"Pipeline rzucił wyjątek na krótkim dokumencie: {e}")


# ===========================================================================
# Uruchomienie
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2, failfast=False)
