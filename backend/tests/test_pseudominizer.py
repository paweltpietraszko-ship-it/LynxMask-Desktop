"""
test_pseudominizer.py  v1.4
===========================
Testy bezpieczeństwa Pseudominizera.

FILOZOFIA: testy pisane pod FAIL.
Każdy test ma szansę wykryć realny problem.
Zielony kolor jest wynikiem poprawności systemu — nie kompromisu w teście.

Uruchomienie (tryb HTTP — jedyny obsługiwany):
  python -m pytest tests/test_pseudominizer.py -v
  lub:
  python tests/test_pseudominizer.py

Backend musi być uruchomiony przed testami:
  uruchom_tauri_dev.vbs  lub  python pseudominizer_api.py

Zmiany v1.3 (06.06.2026):
  Usunięcie trybu lokalnego — był prowizorką generującą fałszywe wyniki.
  Testy działają wyłącznie przez HTTP na 127.0.0.1:8765 (port Pseudominizera).
  Jeśli backend nie odpowiada — skipTest zamiast crash.
  Dodano odczyt api_token.txt (ten sam mechanizm co test_pipeline.py).
  Poprawiono port: 8000 → 8765.
  TestBug1PublicInstitutions przepisany — odwrócenie logiki asercji:
    poprzednio: instytucja publiczna ma być JAWNA w wyjściu (nie tokenizowana)
    teraz: instytucja publiczna ma być ZAKRYTA tokenem INSTYTUCJA (nie FIRMA)
    _check_not_tokenized zastąpiona przez _check_tokenized_as_institution
  TestFilterFunction pozostaje bez zmian — importuje lokalnie, nie wymaga HTTP.

Zmiany v1.4 (07.06.2026):
  Naprawiono asercje fleksyjne w _check_tokenized_as_institution
  i test_osoba_i_instytucja_razem.
  Poprzedni warunek: "Sąd Najwyższy" in orig — zwracał False dla form
  fleksyjnych ("Sądu Najwyższego", "Sądu Najwyższego w Warszawie").
  Pipeline tokenizował poprawnie (audit: INSTYTUCJA_001) ale asercja failowała.
  Nowy warunek: assertRegex(anon, r"INSTYTUCJA_\\d{3}") — sprawdza obecność
  tokenu w wyjściu zamiast substring match na oryginalnej wartości.

Zmiany v1.2 (06.06.2026):
  _pseudonymize → pipeline.pseudonymize_document() (usunięte w v1.3)
  _filter_institutions → ner_layer._filter_institutions
  Dodano TestGuardBlocking.
"""

import os
import sys
import re
import json
import unittest

BASE_URL = "http://127.0.0.1:8765"
PREVIEW_URL = f"{BASE_URL}/preview"
HEALTH_URL  = f"{BASE_URL}/health"

TOKEN_RE = re.compile(r"\b(FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA)_\d{3}\b")

LEAK_PATTERNS = [
    ("PESEL",   re.compile(r"\b\d{11}\b")),
    ("NIP",     re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b")),
    ("IBAN",    re.compile(r"\bPL\d{2}(?:\s?\d{4}){6}\b", re.IGNORECASE)),
    ("EMAIL",   re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")),
    ("TELEFON", re.compile(r"\b(?:\+?48[-\s]?)?\d{3}[-\s]?\d{3}[-\s]?\d{3}\b")),
]


def _load_api_token() -> str:
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "api_token.txt")
    try:
        with open(token_path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

_API_TOKEN    = _load_api_token()
_AUTH_HEADERS = {"x-api-token": _API_TOKEN} if _API_TOKEN else {}


def _check_backend() -> bool:
    """Zwraca True jeśli backend odpowiada na /health."""
    try:
        import urllib.request
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def pseudonymize(text: str) -> dict:
    """Wysyła tekst do backendu i zwraca odpowiedź /preview."""
    import urllib.request
    boundary = "----PseudoBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"{text}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    req = urllib.request.Request(
        PREVIEW_URL,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            **_AUTH_HEADERS,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # 400 itp. — zwróć body jako dict jeśli JSON, inaczej error string
        try:
            body_bytes = e.read()
            return json.loads(body_bytes)
        except Exception:
            return {"error": f"HTTP {e.code}", "blocked": False, "tokens": [],
                    "anonymized_preview": text, "original_text": text}
    except Exception as e:
        return {"error": str(e), "blocked": False, "tokens": [],
                "anonymized_preview": text, "original_text": text}


def get_anon(text): return pseudonymize(text).get("anonymized_preview", text)
def get_tokens(text): return pseudonymize(text).get("tokens", [])


class _BackendRequired(unittest.TestCase):
    """Klasa bazowa — skipuje cały test jeśli backend niedostępny."""

    @classmethod
    def setUpClass(cls):
        if not _check_backend():
            raise unittest.SkipTest(
                "Backend niedostępny — uruchom pseudominizer_api.py przed testami "
                f"(oczekiwany adres: {BASE_URL})"
            )


# ── [LEAK] ────────────────────────────────────────────────────────────────────

class TestLeakPrevention(_BackendRequired):

    def _no_raw(self, anon, value, label):
        self.assertNotIn(value, anon, f"[LEAK] {label}: '{value}' w eksporcie")
        stripped = re.sub(r"[\s\-]", "", value)
        if stripped != value:
            self.assertNotIn(stripped, re.sub(r"[\s\-]", "", anon),
                f"[LEAK] {label}: '{stripped}' (bez sep.) w eksporcie")

    def _no_patterns(self, anon, label):
        clean = TOKEN_RE.sub("__TOKEN__", anon)
        for name, pat in LEAK_PATTERNS:
            hits = pat.findall(clean)
            self.assertEqual(len(hits), 0,
                f"[LEAK] {label}: {name} w eksporcie: {hits[:3]}")

    def test_pesel(self):
        self._no_raw(get_anon("Pracownik Jan Kowalski, PESEL 85010112345."),
                     "85010112345", "PESEL")

    def test_pesel_bez_etykiety(self):
        """PESEL bez słowa PESEL w tekście — trudniejszy przypadek."""
        self._no_raw(get_anon("Urodzony 01.01.1985, nr 85010112345, zam. Gdańsk."),
                     "85010112345", "PESEL_bez_etykiety")

    def test_nip_z_myslnikami(self):
        anon = get_anon("NIP pracodawcy: 123-456-78-90.")
        self._no_raw(anon, "123-456-78-90", "NIP_myslniki")
        self._no_raw(anon, "1234567890", "NIP_cyfry")

    def test_nip_ze_spacjami(self):
        self._no_patterns(get_anon("NIP: 123 456 78 90."), "NIP_spacje")

    def test_iban(self):
        anon = get_anon("Konto: PL61109010140000071219812874.")
        self._no_raw(anon, "PL61109010140000071219812874", "IBAN")
        self._no_patterns(anon, "IBAN")

    def test_email(self):
        anon = get_anon("Kontakt: jan.kowalski@kancelaria.pl")
        self._no_raw(anon, "jan.kowalski@kancelaria.pl", "EMAIL")

    def test_telefon_z_prefiksem(self):
        self._no_patterns(get_anon("Tel: +48 601 234 567."), "TELEFON_+48")

    def test_telefon_bez_prefiksu(self):
        self._no_patterns(get_anon("Tel: 601 234 567."), "TELEFON_bez_prefiksu")

    def test_pesel_izolowany_bez_kontekstu(self):
        """Sam PESEL — najsłabszy przypadek dla NER, regex musi go wyłapać."""
        self._no_raw(get_anon("85010112345"), "85010112345", "PESEL_izolowany")

    def test_kombinowana_umowa_o_prace(self):
        text = """UMOWA O PRACĘ
Pracodawca: XYZ Sp. z o.o., NIP 987-654-32-10.
Pracownik: Anna Wiśniewska, PESEL 90050567891.
E-mail: anna.wisniewska@gmail.com, tel. 507 890 123.
Konto: PL27114020040000300201355387."""
        anon = get_anon(text)
        self._no_raw(anon, "90050567891", "PESEL_umowa")
        self._no_raw(anon, "987-654-32-10", "NIP_umowa")
        self._no_raw(anon, "anna.wisniewska@gmail.com", "EMAIL_umowa")
        self._no_raw(anon, "PL27114020040000300201355387", "IBAN_umowa")
        self._no_patterns(anon, "umowa_kombinowana")
        self.assertTrue(TOKEN_RE.search(anon),
            "[LEAK] Brak tokenów w eksporcie — pseudonimizacja nie zadziałała")

    def test_pesel_w_tabeli(self):
        self._no_raw(get_anon("Imię\tNazwisko\tPESEL\nJan\tKowalski\t85010112345"),
                     "85010112345", "PESEL_tabela")


# ── [BUG-1] ───────────────────────────────────────────────────────────────────

class TestBug1PublicInstitutions(_BackendRequired):
    """
    Instytucje publiczne muszą być zakryte tokenem INSTYTUCJA — nie FIRMA.
    Pipeline używa _INSTITUTION_RE (regex) który tokenizuje je jako INSTYTUCJA_NNN.
    Testy sprawdzają że:
      1. Fraza nie jest widoczna jawnie w wyjściu (zakryta).
      2. Token jest typu INSTYTUCJA, nie FIRMA.
    """

    def _check_tokenized_as_institution(self, institution, variant=None):
        """Instytucja musi być zakryta i mieć token INSTYTUCJA, nie FIRMA."""
        phrase = variant or institution
        text = f"Zgodnie z orzeczeniem {phrase} strony ustaliły warunki umowy."
        result = pseudonymize(text)
        anon   = result.get("anonymized_preview", "")
        tokens = result.get("tokens", [])

        all_originals       = [t["original"] for t in tokens]
        instytucja_originals = [t["original"] for t in tokens if t["type"] == "INSTYTUCJA"]
        firma_originals      = [t["original"] for t in tokens if t["type"] == "FIRMA"]

        # Fraza nie może być widoczna jawnie w wyjściu
        self.assertNotIn(phrase, anon,
            f"[BUG-1] '{phrase}' widoczny jawnie w eksporcie — nie zakryty")

        # Musi być zakryta jako INSTYTUCJA, nie jako FIRMA
        self.assertNotIn(institution, firma_originals,
            f"[BUG-1] '{institution}' trafił jako FIRMA zamiast INSTYTUCJA: {firma_originals}")

        # Sprawdź że w wyjściu jest token INSTYTUCJA_NNN — pipeline zakrył encję.
        # Nie porównujemy mianownika z formą fleksyjną (substring match nie obsługuje
        # fleksji: "Sąd Najwyższy" not in "Sądu Najwyższego"). Wystarczy że
        # wyjście zawiera jakikolwiek token INSTYTUCJA i fraza nie jest jawna.
        import re as _re
        has_instytucja_token = bool(_re.search(r"\bINSTYTUCJA_\d{3}\b", anon))
        self.assertTrue(has_instytucja_token,
            f"[BUG-1] '{institution}' nie zakryty tokenem INSTYTUCJA — "
            f"instytucja_originals={instytucja_originals}, all={all_originals}")

    def test_sad_najwyzszy(self):
        self._check_tokenized_as_institution("Sąd Najwyższy")

    def test_sad_najwyzszy_dopelniacz(self):
        self._check_tokenized_as_institution("Sąd Najwyższy", "Sądu Najwyższego")

    def test_sad_rejonowy(self):
        self._check_tokenized_as_institution("Sąd Rejonowy")

    def test_sad_okregowy(self):
        self._check_tokenized_as_institution("Sąd Okręgowy")

    def test_zus(self):
        self._check_tokenized_as_institution("Zakład Ubezpieczeń Społecznych")

    def test_zus_dopelniacz(self):
        self._check_tokenized_as_institution("Zakład Ubezpieczeń Społecznych",
                                              "Zakładu Ubezpieczeń Społecznych")

    def test_ppk(self):
        self._check_tokenized_as_institution("Pracownicze Plany Kapitałowe")

    def test_pip(self):
        self._check_tokenized_as_institution("Państwowa Inspekcja Pracy")

    def test_trybunal_konstytucyjny(self):
        self._check_tokenized_as_institution("Trybunał Konstytucyjny")

    def test_urzad_skarbowy(self):
        self._check_tokenized_as_institution("Urząd Skarbowy")

    def test_knf(self):
        self._check_tokenized_as_institution("Komisja Nadzoru Finansowego")

    def test_rzecznik_praw_obywatelskich(self):
        self._check_tokenized_as_institution("Rzecznik Praw Obywatelskich")

    def test_osoba_i_instytucja_razem(self):
        """
        Kluczowy test: osoba i instytucja w tym samym zdaniu.
        Osoba musi dostać token OSOBA, instytucja token INSTYTUCJA.
        Żadne z nich nie może być widoczne jawnie.
        """
        text = "Anna Kowalska złożyła skargę do Sądu Najwyższego w Warszawie."
        result = pseudonymize(text)
        anon   = result.get("anonymized_preview", "")
        tokens = result.get("tokens", [])

        instytucja_originals = [t["original"] for t in tokens if t["type"] == "INSTYTUCJA"]
        osoby                = [t for t in tokens if t["type"] == "OSOBA"]

        self.assertNotIn("Anna Kowalska", anon,
            "[BUG-1] 'Anna Kowalska' nie zastąpiona tokenem")
        self.assertTrue(len(osoby) > 0,
            "[BUG-1] Anna Kowalska nie wykryta jako OSOBA")

        self.assertNotIn("Sądu Najwyższego", anon,
            "[BUG-1] 'Sądu Najwyższego' widoczny jawnie — nie zakryty jako INSTYTUCJA")
        import re as _re
        has_instytucja_token = bool(_re.search(r"\bINSTYTUCJA_\d{3}\b", anon))
        self.assertTrue(has_instytucja_token,
            f"[BUG-1] 'Sąd Najwyższy' nie zakryty tokenem INSTYTUCJA — "
            f"instytucja_originals={instytucja_originals}")

    def test_wiele_instytucji(self):
        """Wiele instytucji w jednym tekście — każda zakryta jako INSTYTUCJA, nie FIRMA."""
        text = """Składki ZUS odprowadza pracodawca.
PPK obsługuje podmiot zarządzający.
Spory rozstrzyga Sąd Rejonowy.
Kontrolę przeprowadza Państwowa Inspekcja Pracy."""
        result = pseudonymize(text)
        anon   = result.get("anonymized_preview", "")
        tokens = result.get("tokens", [])
        firma_originals = [t["original"] for t in tokens if t["type"] == "FIRMA"]
        for inst in ["Sąd Rejonowy", "Państwowa Inspekcja Pracy"]:
            self.assertNotIn(inst, anon,
                f"[BUG-1] '{inst}' widoczny jawnie w eksporcie")
            self.assertNotIn(inst, firma_originals,
                f"[BUG-1] '{inst}' trafił jako FIRMA zamiast INSTYTUCJA")


# ── [NER] ─────────────────────────────────────────────────────────────────────

class TestNERDetection(_BackendRequired):

    def test_osoba_wykryta(self):
        result = pseudonymize("Zleceniobiorca Jan Kowalski zobowiązuje się do usługi.")
        tokens = result.get("tokens", [])
        osoby = [t for t in tokens if t["type"] == "OSOBA"]
        wykryte = [t["original"] for t in osoby if "Kowalski" in t["original"]]
        self.assertTrue(len(wykryte) > 0,
            f"[NER] Jan Kowalski nie wykryty. Tokeny OSOBA: {osoby}")

    def test_osoba_nie_w_eksporcie(self):
        text = "Zleceniobiorca Jan Kowalski zobowiązuje się do usługi."
        result = pseudonymize(text)
        anon = result.get("anonymized_preview", "")
        tokens = result.get("tokens", [])
        osoby = [t for t in tokens if t["type"] == "OSOBA"]
        if osoby:
            self.assertNotIn("Jan Kowalski", anon,
                "[NER] Jan Kowalski w mapie ale nadal widoczny w eksporcie")

    def test_firma_prywatna_wykryta(self):
        result = pseudonymize("Firma: Kowalski i Partnerzy Sp. z o.o., Kraków.")
        tokens = result.get("tokens", [])
        firmy = [t for t in tokens if t["type"] == "FIRMA"]
        # SpaCy może wykryć pełną nazwę lub fragment z "Sp. z o.o." —
        # ważne że jakakolwiek firma jest wykryta i nie jest instytucją publiczną
        self.assertTrue(len(firmy) > 0,
            f"[NER] Żadna firma nie wykryta w tekście. Tokens: {tokens}")
        # Firma musi zawierać co najmniej fragment nazwy prywatnej
        private_detected = any(
            any(w in t["original"] for w in ["Kowalski", "Partnerzy", "Sp."])
            for t in firmy
        )
        self.assertTrue(private_detected,
            f"[NER] Wykryta firma nie zawiera fragmentu nazwy prywatnej: {firmy}")

    def test_firma_nie_w_eksporcie(self):
        text = "Firma: Kowalski i Partnerzy Sp. z o.o."
        result = pseudonymize(text)
        anon = result.get("anonymized_preview", "")
        tokens = result.get("tokens", [])
        for f in [t for t in tokens if t["type"] == "FIRMA"]:
            self.assertNotIn(f["original"], anon,
                f"[NER] Firma '{f['original']}' nadal widoczna w eksporcie")

    def test_pesel_tokenizowany(self):
        result = pseudonymize("PESEL: 85010112345.")
        tokens = result.get("tokens", [])
        numery = [t for t in tokens if t["type"] == "NUMER"]
        self.assertTrue(len(numery) > 0,
            f"[NER] PESEL nie tokenizowany: {tokens}")

    def test_iban_tokenizowany(self):
        result = pseudonymize("Konto: PL61109010140000071219812874.")
        tokens = result.get("tokens", [])
        numery = [t for t in tokens if t["type"] == "NUMER"]
        self.assertTrue(len(numery) > 0,
            f"[NER] IBAN nie tokenizowany: {tokens}")


# ── [GUARD] ───────────────────────────────────────────────────────────────────

class TestGuardBlocking(_BackendRequired):

    def test_guard_blokuje_niezanonimizowane_pii(self):
        """Guard musi zwrócić blocked=True gdy PII przeszło przez pipeline."""
        # Tekst który celowo zawiera PII które POWINNO zostać zakryte
        # ale symulujemy scenariusz gdzie guard widzi plaintext
        text = "Jan Kowalski, PESEL 85010112345, ul. Zielona 1."
        result = pseudonymize(text)
        anon = result.get("anonymized_preview", "")
        # Jeśli PESEL nadal widoczny w wyjściu — Guard powinien był zablokować
        if "85010112345" in anon:
            blocked = result.get("blocked", False) or result.get("guard_blocked", False)
            self.assertTrue(blocked,
                "[GUARD] PESEL widoczny w wyjściu ale Guard nie zablokował (blocked=False)")
        else:
            # PESEL zakryty — Guard nie musiał blokować, to jest poprawne
            pass


# ── [CONS] ────────────────────────────────────────────────────────────────────

class TestConsistency(_BackendRequired):

    def test_ta_sama_osoba_jeden_token(self):
        """Trzy wystąpienia tej samej osoby — jeden token, użyty trzy razy."""
        text = "Jan Kowalski podpisał umowę. Jan Kowalski zobowiązał się. Podpis: Jan Kowalski."
        result = pseudonymize(text)
        tokens = result.get("tokens", [])
        anon = result.get("anonymized_preview", "")
        kowalski = [t for t in tokens if t["type"] == "OSOBA"
                    and "Kowalski" in t.get("original", "")]
        # Najpierw sprawdź że "Jan Kowalski" w ogóle nie wycieka
        self.assertNotIn("Jan Kowalski", anon,
            "[CONS] 'Jan Kowalski' widoczny jawnie w eksporcie")
        # Następnie sprawdź deduplikację — jeden token dla tej samej osoby
        self.assertEqual(len(kowalski), 1,
            f"[CONS] Jan Kowalski: {len(kowalski)} tokenów zamiast 1 — "
            f"bug deduplikacji w ner_layer.py: {kowalski}")

    def test_rozne_osoby_rozne_tokeny(self):
        text = "Anna Nowak podpisała umowę. Kontrahentem był Piotr Wiśniewski."
        result = pseudonymize(text)
        tokens = result.get("tokens", [])
        osoby = [t["token"] for t in tokens if t["type"] == "OSOBA"]
        self.assertEqual(len(set(osoby)), len(osoby),
            f"[CONS] Dwie osoby mają ten sam token: {osoby}")


# ── [EDGE] ────────────────────────────────────────────────────────────────────

class TestEdgeCases(_BackendRequired):

    def test_liczby_w_umowie_nie_sa_tokenizowane(self):
        """
        Numer umowy i rok nie mogą być tokenizowane jako NUMER.
        Poprzednia wersja używała zdania bez żadnych liczb — za proste.
        """
        text = "Umowa nr 1/2026 zawarta w Warszawie dnia 1 stycznia 2026 r."
        result = pseudonymize(text)
        tokens = result.get("tokens", [])
        numery = [t for t in tokens if t["type"] == "NUMER"]
        self.assertEqual(len(numery), 0,
            f"[EDGE] Numer umowy/rok tokenizowany jako NUMER: {numery}")

    def test_pusty_tekst_nie_crashuje(self):
        """Backend zwraca 400 dla pustego tekstu — to jest poprawne, nie crash."""
        result = pseudonymize("   ")
        # 400 z error to poprawna odpowiedź — sprawdzamy tylko że nie ma Traceback
        self.assertNotIn("Traceback", str(result.get("error", "")),
            "[EDGE] Backend crashuje na pustym tekście (Traceback w error)")

    def test_tokeny_w_tekscie_nie_sa_zmieniane(self):
        """Istniejące tokeny w dokumencie nie mogą być podwójnie tokenizowane."""
        text = "OSOBA_001 FIRMA_002 — te tokeny są już w dokumencie."
        anon = get_anon(text)
        self.assertIn("OSOBA_001", anon,
            "[EDGE] Istniejący token OSOBA_001 zmieniony")
        self.assertIn("FIRMA_002", anon,
            "[EDGE] Istniejący token FIRMA_002 zmieniony")

    def test_dlugi_dokument_bez_wycieku(self):
        pesel = "85010112345"
        # 300 powtórzeń * ~55 znaków = ~16500 — backend tnie do MAX_TEXT_CHARS=15000
        text = ("Jan Kowalski, PESEL " + pesel + ", zawarł umowę. ") * 300
        anon = get_anon(text)
        self.assertNotIn(pesel, anon,
            "[EDGE] PESEL wyciekł w długim dokumencie")


# ── [FILT] ────────────────────────────────────────────────────────────────────
# TestFilterFunction nie wymaga backendu — importuje lokalnie z ner_layer/spacy_ner.

class TestFilterFunction(unittest.TestCase):

    def _get(self):
        try:
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if cwd not in sys.path:
                sys.path.insert(0, cwd)
            # v1.2: _filter_institutions przeniesiona do ner_layer po refaktoryzacji
            from ner_layer import _filter_institutions
            from spacy_ner import NERResult
            return _filter_institutions, NERResult
        except ImportError:
            self.skipTest("Import ner_layer/spacy_ner niedostępny")

    def test_instytucje_odfiltrowane(self):
        f, R = self._get()
        results = [
            R("Jan Kowalski", "OSOBA", 0.9, 0, 12),
            R("Sąd Najwyższy", "FIRMA", 0.8, 14, 27),
            R("Zakład Ubezpieczeń Społecznych", "FIRMA", 0.9, 28, 58),
            R("ABC Sp. z o.o.", "FIRMA", 0.85, 60, 75),
        ]
        filtered = f(results)
        names = [r.text for r in filtered]
        self.assertIn("Jan Kowalski", names)
        self.assertIn("ABC Sp. z o.o.", names)
        self.assertNotIn("Sąd Najwyższy", names, "[FILT] SN nie odfiltrowany")
        self.assertNotIn("Zakład Ubezpieczeń Społecznych", names, "[FILT] ZUS nie odfiltrowany")

    def test_odmiany_odfiltrowane(self):
        f, R = self._get()
        results = [
            R("Sądu Najwyższego", "FIRMA", 0.8, 0, 16),
            R("Sądowi Najwyższemu", "FIRMA", 0.8, 20, 38),
            R("Zakładu Ubezpieczeń Społecznych", "FIRMA", 0.85, 40, 70),
        ]
        filtered = f(results)
        self.assertEqual(len(filtered), 0,
            f"[FILT] Odmiany nie odfiltrowane: {[r.text for r in filtered]}")

    def test_prywatna_firma_nie_odfiltrowana(self):
        f, R = self._get()
        results = [R("Kowalski i Partnerzy Sp. z o.o.", "FIRMA", 0.85, 0, 30)]
        filtered = f(results)
        self.assertEqual(len(filtered), 1,
            "[FILT] Prywatna firma błędnie odfiltrowana przez blocklist")

    def test_prefix_nie_uderza_w_podobne_nazwy(self):
        """
        'Sadowski i Wspólnicy' zaczyna się podobnie do 'Sąd' ale
        nie jest instytucją — nie może być odfiltrowany.
        """
        f, R = self._get()
        results = [R("Sadowski i Wspólnicy", "FIRMA", 0.8, 0, 20)]
        filtered = f(results)
        self.assertEqual(len(filtered), 1,
            "[FILT] 'Sadowski i Wspólnicy' błędnie odfiltrowany przez prefix 'sąd'")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  Pseudominizer — testy  v1.4  [HTTP]")
    print(f"  Backend: {BASE_URL}")
    print(f"  FAIL = problem w systemie, nie w teście")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2)
