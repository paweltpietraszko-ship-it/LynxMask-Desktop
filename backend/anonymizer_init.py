"""
anonymizer_init.py  v1.8
Inicjalizacja warstw opcjonalnych (postal, stdnum, phonenumbers),
stałe tokenów, STRUCTURAL_PATTERNS.

v1.8 — [FIX-ID-CARD-BOUNDARY] Wzorzec dowodu osobistego: \b[A-Z]{3} → (?<![A-Za-z])[A-Z]{3}
       i \b na końcu → (?!\d). \b nie działa gdy dowód stoi przy literze (\w+\w).
       Naprawia pominięcia JHS681545, YTZ143919, DBF379230, RWU996331 z benchmarku.
v1.7 — [FIX-DOB-PASSPORT] Dodano wzorzec daty urodzenia DD.MM.YYYY/DD-MM-YYYY oraz
       paszportu polskiego (2 litery + 7 cyfr). Oba wstawione przed fallback \d{8,}.
v1.6 — [FIX-TEL-LANDLINE] Wzorzec telefonu rozszerzony o format stacjonarny 2+3+2+2
       (np. "22 123 45 67", "22-123-45-67"). Poprzedni wzorzec 3+3+3 pomijał numery
       warszawskie i inne stacjonarne. Dwa alternatywy w jednym re.compile.
       \b zastąpione (?<!\d)/(?!\d) spójnie z v1.5.
v1.5 — [FIX-WORD-BOUNDARY] \b zastąpione (?<!\d)/(?!\d) w 7 wzorcach cyfrowych
       STRUCTURAL_PATTERNS: \d{24}, \d{11}, \d{14}, NIP, \d{9}, \d{3}-\d{2}-\d{2}, \d{8,}.
       Poprzedni \b nie matchował PII klejonego z etykietą (PESEL85010112345, NIP8550193123)
       bo między literą a cyfrą brak granicy \b — oba są \w.
       Wzorce z prefiksem literowym (PL, KRS, [A-Z]{3}, ur\.) oraz EMAIL/ADRES/KWOTA
       pozostają bez zmian — tam \b działa poprawnie.
v1.4 — [FIX-LOGGER] Wszystkie getLogger("triangulum.anonymizer") zmienione
       na getLogger("lynxmask.anonymizer"). 6 miejsc w funkcjach inicjalizacyjnych
       (_init_postal_patterns, _init_stdnum_validators, _init_phonenumbers).
       Spójność z output_guard.py który miał już "lynxmask.output_guard".
v1.3 — [AUD-04] KWOTA_RE rozszerzony o kwoty 4-6 cyfrowe bez separatora tysięcy.
       Poprzedni wzorzec \\d{1,3}(?:[\\s]\\d{3})? nie matchował "19096 PLN", "36525 PLN"
       itp. — brakujące maski kwot potwierdzone przez benchmark (doc_00001, doc_00010,
       doc_00023, doc_00049). Nowy wzorzec: alternatyw \\d{4,6} obok istniejącego
       \\d{1,3}(?:[\\s]\\d{3}){0,2}. Górna granica 6 cyfr (999999) bez separatora —
       7+ cyfr bez separatora bardziej przypomina numer dokumentu.
v1.2 — [AUD-03] TOKEN_RE i TOKEN_SPAN_RE rozszerzone o INSTYTUCJA (linie 192-193).
       Poprzednio token INSTYTUCJA_NNN nie był chroniony przed re-tokenizacją przez
       warstwy anonymizer. Spójność z TOKEN_RE w pipeline.py i pseudominizer_api.py.
v1.1 — BUG-6: dodano TOKEN_EMAIL = "EMAIL". Wzorzec email w STRUCTURAL_PATTERNS
       zmieniony z TOKEN_NUMER na TOKEN_EMAIL. TOKEN_RE i TOKEN_SPAN_RE rozszerzone
       o EMAIL. TOKEN_EMAIL dodany do _STRUCTURAL_TOKEN_TYPES.
       Dotknięte linie: stałe tokenów (~195), TOKEN_RE (~200), TOKEN_SPAN_RE (~201),
       wpis email w STRUCTURAL_PATTERNS (~ok. 245), _STRUCTURAL_TOKEN_TYPES (ostatnia linia).

Wydzielone z anonymizer.py v4.19 — logika warstw w anonymizer.py.
Import: from anonymizer_init import (
    _POSTAL_PATTERNS, _POSTAL_CONTEXT_BEFORE, _POSTAL_CONTEXT_AFTER,
    _STDNUM_VALIDATORS, _STDNUM_CANDIDATE_RE,
    _PHONENUMBERS_AVAILABLE,
    _crypto, _CRYPTO_AVAILABLE,
    TOKEN_FIRMA, TOKEN_OSOBA, TOKEN_NUMER, TOKEN_KWOTA, TOKEN_ADRES, TOKEN_EMAIL,
    TOKEN_RE, TOKEN_SPAN_RE,
    INPUT_LIMIT_BYTES, MAX_TOKENS_PER_REQUEST,
    STRUCTURAL_PATTERNS, _STRUCTURAL_TOKEN_TYPES,
)
"""

import re
import logging

# ============================================================
# Warstwa 3 — kody pocztowe jako kotwice adresowe [FIX-POSTAL-LIB]
# Używa biblioteki postal-codes-tools (ECB) dla 26 krajów EU.
# Opcjonalna — brak biblioteki = fallback do warstwy 2 regex.
# ============================================================

_POSTAL_PATTERNS: dict = {}   # country_code → compiled regex
_POSTAL_CONTEXT_BEFORE = 60   # znaki tekstu przed kodem pocztowym
_POSTAL_CONTEXT_AFTER  = 30   # znaki tekstu po kodzie pocztowym

def _init_postal_patterns() -> None:
    """
    Ładuje regex kodów pocztowych z postal-codes-tools (ECB).
    Wywoływane raz przy imporcie modułu.
    Filtruje kraje których pattern jest zbyt ogólny (brak wymogu cyfr).
    """
    try:
        from postal_codes_tools.postal_codes import get_postal_code_regex
        # [FIX-POSTAL-SAFELIST] v4.18 — biała lista zamiast wszystkich 26 krajów EU.
        # Kraje wykluczone mają kody 4-cyfrowe lub format NNN-NN które zbiegają się
        # z danymi finansowymi i datami w dokumentach biurowych:
        #   - AT, CH, BE, DK, NO, HU (4 cyfry): 2020, 2024, 1234, 5000 → daty, kwoty
        #   - CZ, SK (NNN NN): 500 00, 600 00 → kwoty z separatorem tysięcy
        #   - SE, FI, LU, RO, BG, HR, SI, EE, LV, LT, PT: format zbyt krótki lub
        #     pokrywający się z numerami w polskich dokumentach biurowych
        # Zostawione:
        #   PL (\d{2}-\d{3}) — myślnik czyni kod unikalnym
        #   DE (\d{5})        — 5 cyfr bez separatora, rzadkie false positives
        #   FR (\d{5})        — jak DE
        #   IT (\d{5})        — jak DE
        #   ES (\d{5})        — jak DE
        #   NL (\d{4} [A-Z]{2}) — cyfry + litery, bardzo unikalne
        #   GB ([A-Z]{1,2}\d... ) — alfanumeryczne, praktycznie bez false positives
        # Dokumenty zagraniczne z kodami innych krajów: człowiek weryfikuje.
        EU_COUNTRIES = ['PL', 'DE', 'FR', 'IT', 'ES', 'NL', 'GB', 'UA']
        # UA dodane v4.18 — polskie firmy często handlują z Ukrainą.
        # Ukraiński kod pocztowy to 5 cyfr (\d{5}), ten sam bezpieczny
        # format co DE/FR/IT/ES — nie zbiega się z datami ani kwotami.
        for country in EU_COUNTRIES:
            raw = get_postal_code_regex(country)
            stripped = raw.lstrip('^').rstrip('$')
            # Pomiń patterny bez wymogu cyfr — za ogólne
            if r'\d' not in stripped and '[0-9]' not in stripped:
                continue
            try:
                pat = re.compile(stripped)
                # Pomiń patterny matchujące pojedyncze znaki
                if pat.match('1'):
                    continue
                _POSTAL_PATTERNS[country] = pat
            except re.error:
                pass
        logging.getLogger("lynxmask.anonymizer").debug(
            f"postal-codes-tools: załadowano {len(_POSTAL_PATTERNS)} krajów"
        )
    except ImportError:
        logging.getLogger("lynxmask.anonymizer").info(
            "postal-codes-tools niedostępne — warstwa 3 adresów wyłączona. "
            "Zainstaluj: pip install postal-codes-tools"
        )

_init_postal_patterns()

# ============================================================
# Warstwa 4 — stdnum: walidacja numerów identyfikacyjnych [FIX-STDNUM]
# Używa python-stdnum dla PL, UA, EU VAT i innych.
# Opcjonalna — brak biblioteki = fallback do warstwy 2 regex.
# ============================================================

_STDNUM_VALIDATORS: list = []  # list of (name, validator_module, token_type)

def _init_stdnum_validators() -> None:
    """
    Ładuje walidatory stdnum. Każdy wpis: (nazwa, moduł, token_type).
    Kolejność ważna — bardziej specyficzne przed ogólnymi.
    """
    _log = logging.getLogger("lynxmask.anonymizer")
    try:
        from stdnum.pl import nip, pesel, regon
        from stdnum.ua import edrpou, rntrc
        from stdnum import iban as stdnum_iban

        # (etykieta, moduł z is_valid() i compact(), TOKEN_*)
        # Używamy string "NUMER" zamiast TOKEN_NUMER — stała zdefiniowana niżej w module
        validators = [
            ("IBAN",       stdnum_iban, "NUMER"),
            ("PESEL",      pesel,       "NUMER"),
            ("NIP-PL",     nip,         "NUMER"),
            ("REGON",      regon,       "NUMER"),
            ("EDRPOU-UA",  edrpou,      "NUMER"),
            ("RNTRC-UA",   rntrc,       "NUMER"),
        ]

        # EU VAT — obsługuje PL, DE, FR, AT, CZ i inne
        try:
            from stdnum.eu import vat as eu_vat
            validators.insert(0, ("VAT-EU", eu_vat, "NUMER"))
        except ImportError:
            pass

        _STDNUM_VALIDATORS.extend(validators)
        _log.debug(f"stdnum: załadowano {len(_STDNUM_VALIDATORS)} walidatorów")
    except ImportError:
        _log.info(
            "python-stdnum niedostępne — warstwa 4 wyłączona. "
            "Zainstaluj: pip install python-stdnum"
        )

_init_stdnum_validators()

# Regex do wyciągania kandydatów numerycznych z tekstu dla stdnum
# Pattern 1: liczby z separatorami (IBAN, PESEL, NIP, EDRPOU, telefon)
# Pattern 2: EU VAT format — 2 wielkie litery + cyfry (PL6551979313, DE815559897)
_STDNUM_CANDIDATE_RE = re.compile(
    r'(?<!\w)(?:\+?\d[\d\s\-]{4,30}\d)(?!\w)'
    r'|'
    r'(?<![A-Z])([A-Z]{2}\d[\d\s\-]{6,20}\d)(?!\w)',
)

# ============================================================
# Warstwa 5 — phonenumbers: wykrywanie telefonów globalnie [FIX-PHONENUMBERS]
# Używa phonenumbers (libphonenumber Google) — obsługuje 200+ krajów.
# Opcjonalna — brak biblioteki = fallback do warstwy 2 regex.
# ============================================================

_PHONENUMBERS_AVAILABLE = False

def _init_phonenumbers() -> None:
    global _PHONENUMBERS_AVAILABLE
    try:
        import phonenumbers as _ph_test
        _PHONENUMBERS_AVAILABLE = True
        logging.getLogger("lynxmask.anonymizer").debug(
            "phonenumbers: dostępne"
        )
    except ImportError:
        logging.getLogger("lynxmask.anonymizer").info(
            "phonenumbers niedostępne — warstwa 5 wyłączona. "
            "Zainstaluj: pip install phonenumbers"
        )

_init_phonenumbers()

try:
    import anonymizer_crypto as _crypto
    _CRYPTO_AVAILABLE = True
except ImportError:
    _crypto = None
    _CRYPTO_AVAILABLE = False
    logging.getLogger("lynxmask.anonymizer").warning(
        "anonymizer_crypto niedostępny — mapa przechowywana jako plain JSON. "
        "Zainstaluj: pip install cryptography"
    )

# ============================================================
# Stałe
# ============================================================
TOKEN_FIRMA  = "FIRMA"
TOKEN_OSOBA  = "OSOBA"
TOKEN_NUMER  = "NUMER"
TOKEN_KWOTA  = "KWOTA"
TOKEN_ADRES  = "ADRES"
TOKEN_EMAIL  = "EMAIL"  # BUG-6: adresy e-mail tokenizowane jako NUMER — nowy typ

TOKEN_RE      = re.compile(r"\b(FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_(\d{3})\b")
TOKEN_SPAN_RE = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}\b")

INPUT_LIMIT_BYTES      = 500_000
MAX_TOKENS_PER_REQUEST = 500      # unikalne tokeny [V4-3]
MAX_ONBOARD_BATCH      = 100

# ============================================================
# Regex warstwa 2 — dane strukturalne
# UWAGA: nie zmieniać kolejności — bardziej specyficzne przed ogólnymi
# IBAN przed NIP, PESEL przed REGON/NIP, KRS z prefiksem przed cyframi
# ============================================================
STRUCTURAL_PATTERNS = [
    # [FIX-TRACKING] Numer przesyłki kurierskiej — dokładnie 24 cyfry.
    # InPost, DHL, DPD i inne używają tego formatu. Numer identyfikuje
    # nadawcę, odbiorcę i adres dostawy — PII.
    # Umieszczony przed PESEL/REGON — word boundary i tak wyklucza cross-matching,
    # ale kolejność jawna dla przejrzystości.
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)\d{24}(?!\d)"
    )),
    # IBAN PL (PL + 26 cyfr, opcjonalne spacje co 4)
    (TOKEN_NUMER, re.compile(
        r"\bPL\s?\d{2}(?:\s?\d{4}){6}\b", re.IGNORECASE
    )),
    # [FIX-IBAN-PL] Konto bankowe bez prefiksu PL — format powszechny na polskich fakturach.
    # Standardowy IBAN PL ma 26 cyfr; na fakturach zapisywany jako:
    #   "07 1240 6973 1111 0011 3718 3341" (spacje, grupy 2+4+4+4+4+4+4)
    #   "61-12403347-1111001124737720"      (myślniki, grupy 2+8+16 lub inne)
    # Wzorzec 1: spacje — grupy 2+4+4+4+4+4+4
    # Wzorzec 2: myślniki — dowolne grupy cyfr oddzielone myślnikiem, łącznie 26 cyfr
    (TOKEN_NUMER, re.compile(
        r"\b\d{2}(?:\s\d{4}){5,6}\b"
    )),
    (TOKEN_NUMER, re.compile(
        r"\b\d{2}-\d[\d\-]{20,28}\d\b"
    )),
    # KRS (10 cyfr z prefiksem — przed cyframi bez prefiksu)
    (TOKEN_NUMER, re.compile(
        r"\bKRS\s*\d{10}\b", re.IGNORECASE
    )),
    # PESEL (11 cyfr — przed REGON 9-cyfrowym)
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)\d{11}(?!\d)"
    )),
    # REGON 14-cyfrowy
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)\d{14}(?!\d)"
    )),
    # NIP (10 cyfr, opcjonalne separatory)
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}(?!\d)"
    )),
    # [FIX-NIP-PL] NIP z prefiksem PL — format używany na fakturach dla firm
    # unijnych (np. "NIP: PL6551979313"). Poprzedni wzorzec wymagał samych cyfr.
    (TOKEN_NUMER, re.compile(
        r"\bPL\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b", re.IGNORECASE
    )),
    # REGON 9-cyfrowy
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)\d{9}(?!\d)"
    )),
    # Data urodzenia — "ur. DD.MM.RRRR" lub "ur. DD.MM.RRRR w Miasto"
    # [FIX-BIRTHDATE] Niezamaskowana w umowie o pracę — pole "ur. 12.04.1990 w Gdansku".
    # Miejsce urodzenia tez PII w polaczeniu z data.
    (TOKEN_NUMER, re.compile(
        r"\bur\.\s*\d{1,2}\.\d{1,2}\.\d{4}(?:\s+w\s+[A-Z\u0141\u015a\u0179\u0106\u0143][\w\-]{1,30})?",
        re.IGNORECASE | re.UNICODE
    )),
    # Nr dowodu osobistego — format ABC 123456 lub ABC123456
    # [FIX-ID-CARD] Trafial jako ADRES zamiast NUMER — regex strukturalny ma priorytet.
    (TOKEN_NUMER, re.compile(
        r"(?<![A-Za-z])[A-Z]{3}\s?\d{6}(?!\d)"
    )),
    # Email — BUG-6: poprzednio przypisany do TOKEN_NUMER, teraz TOKEN_EMAIL
    # Umieszczony przed telefonem — @ jest unikalnym separatorem, zero false positives.
    (TOKEN_EMAIL, re.compile(
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
    )),
    # Email OCR-broken — local part na jednej linii, @domain na następnej
    (TOKEN_EMAIL, re.compile(
        r"\b[a-zA-Z0-9._%+\-]+[ \t]*\n[ \t]*@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    )),
    # Telefon — dwa formaty:
    # format stacjonarny 2+3+2+2 (np. "22 123 45 67", "22-123-45-67")
    # format komórkowy  3+3+3   (np. "600 123 456", "+48 600 123 456")
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)(?:\+?48[-\s]?)?\d{2}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}(?!\d)"
        r"|"
        r"(?<!\d)(?:\+?48[-\s]?)?\d{3}[-\s]?\d{3}[-\s]?\d{3}(?!\d)"
    )),
    # Kwota (liczba + waluta)
    # [FIX-KWOTA-YEAR] Poprzedni wzorzec \d[\d\s]* łapał "2025 78,69 PLN" jako jedną kwotę.
    # Poprawka: liczba przed walutą to max 3 grupy cyfr (do 999 999 999,99) bez spacji
    # między tysiącami — spacja jest separatorem w IBAN, nie w kwocie.
    # Akceptujemy: "78,69 PLN", "1 234,56 PLN" (spacja jako separator tysięcy max 1x)
    # [AUD-04] Rozszerzony o kwoty 4-6 cyfrowe bez separatora tysięcy.
    # "19096 PLN", "36525 PLN", "44408 PLN" nie pasowały bo wzorzec wymagał max 3 cyfry
    # lub 3+spacja+3. Nowy alternatyw \d{4,6} obejmuje kwoty 1000-999999 bez separatora.
    # Górna granica 6 cyfr (999999) bez separatora — 7+ cyfr bez separatora to anomalia
    # (bardziej numer dokumentu niż kwota) i obsługiwana przez \d{1,3}[\s]\d{3}[\s]\d{3}.
    (TOKEN_KWOTA, re.compile(
        r"\b(?:\d{1,3}(?:[\s]\d{3}){0,2}|\d{4,6})(?:[.,]\d{1,2})?\s*(?:zł|PLN|EUR|USD|GBP)\b",
        re.IGNORECASE
    )),
    # Sygnatura akt ukośnikowa — co najmniej 3 segmenty z co najmniej jedną literą.
    # [FIX-B6b] wzorzec wymieniony w v4.6 ale nie dodany do kodu.
    # Pasuje:   15/2Pm/P/JAG3/2024/EO,  I/ACa/123/2024
    # Nie pasuje: 1/2/2024 (same cyfry — data),  Sokola 4/6 (2 segmenty)
    (TOKEN_NUMER, re.compile(
        r"(?<!\w)"
        r"(?=[0-9A-Za-z/]*[A-Za-z])"   # co najmniej jedna litera w całym dopasowaniu
        r"[A-Z0-9]{1,8}"               # pierwszy segment (max 8 znaków)
        r"(?:/[A-Z0-9]{1,8}){2,}"      # co najmniej 2 kolejne segmenty /XXX
        r"(?!\w)",
        re.IGNORECASE
    )),
    # Adres bez prefiksu — pełny: ulica + numer \n kod_pocztowy + miasto
    # [FIX-B10] wzorzec dodany — był tylko w pseudominizer_api, nie w anonymizer.
    # [FIX-B10-NUM] Numer musi zaczynać się od cyfry (nie dowolne słowo).
    # [FIX-ADDR-SEP] Separator kod/miasto: spacja LUB przecinek LUB przecinek+spacja.
    (TOKEN_ADRES, re.compile(
        r"\b\w{2,30}[ \t]+\d[\w/\-]{0,9}"   # ulica + numer zaczynający się od cyfry
        r"\n"
        r"\d{2}-\d{3}[,\s]+"              # kod pocztowy PL + dowolny separator
        r"\w[\w ]{2,40}\b"                # miasto (min. 3 znaki)
    )),
    # Adres — sam kod pocztowy + miasto (fallback gdy ulica niedostępna)
    # [FIX-ADDR-SEP] separator: spacja, przecinek, przecinek+spacja
    (TOKEN_ADRES, re.compile(
        r"\b\d{2}-\d{3}[,\s]+\w[\w ]{2,40}\b"
    )),
    # [FIX-ADDR-NOPREFIX] USUNIĘTY v4.17 — generował false positives na numerach
    # faktur, kodach produktów, datach ("Faktura VAT 141/05", "PLN 369", "VAT 23").
    # "Sokola 4/6" bez kodu pocztowego nie jest PII.
    # Pokrycie zapewniają: FIX-ADDR-FULL, warstwa postal, _ADDR_RE w pipeline.py.
    # [FIX-ADDR-FULL] Pełny adres jednoliniowy z kodem pocztowym jako kotwicą.
    # Separator elastyczny: spacja, przecinek, przecinek+spacja.
    (TOKEN_ADRES, re.compile(
        r"\b[A-ZŁŚŹĆŃĄĘÓŻ]\w{1,29}"
        r"(?:\s+[A-ZŁŚŹĆŃĄĘÓŻ]\w{1,29})?"
        r"\s+\d{1,4}[A-Za-z]?(?:/\d{1,4}[A-Za-z]?)?"
        r"[,\s]+"
        r"\d{2}-\d{3}"
        r"[,\s]+\w[\w ,]{2,40}\b"
    )),
    # Numer wewnętrzny/skrócony — 7 cyfr w formacie 3-2-2 (np. "322 19 27")
    # UWAGA: wzorzec celowo ostatni — akceptujemy false positives na krótkich liczbach.
    # Decyzja produktowa: lepiej zasłonić za dużo niż za mało (oryginał w sejfie).
    # False positive: "str. 12 poz. 45" może dać NUMER jeśli OCR złączy cyfry.
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)\d{3}[\s\-]\d{2}[\s\-]\d{2}(?!\d)"
    )),
    # [FIX-DIGITS-CATCHALL] Siatka bezpieczeństwa — wszystkie ciągi cyfr 8+.
    # Łapie formaty których nie przewidziano: kody EAN, CN, numery zamówień,
    # Data urodzenia — format DD.MM.YYYY i DD-MM-YYYY
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)\d{2}[.\-]\d{2}[.\-]\d{4}(?!\d)"
    )),
    # Paszport polski — 2 litery + 7 cyfr (np. ZX1234567)
    (TOKEN_NUMER, re.compile(
        r"(?<![A-Z])\b[A-Z]{2}\d{7}\b"
    )),
    # identyfikatory systemowe itp. False positives (EAN, CN) akceptowalne —
    # oryginał w sejfie, AI nie potrzebuje surowych kodów produktów.
    # Umieszczony ostatni — specyficzne wzorce wyżej mają priorytet.
    (TOKEN_NUMER, re.compile(
        r"(?<!\d)\d{8,}(?!\d)"
    )),
]

# Typy tokenów dla których normalizacja strukturalna usuwa separatory [V4-2]
_STRUCTURAL_TOKEN_TYPES = {TOKEN_NUMER, TOKEN_EMAIL}
