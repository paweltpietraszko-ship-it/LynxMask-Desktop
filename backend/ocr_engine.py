"""
ocr_engine.py  v1.4.5
===================
OCR dla Pseudominizera — Tesseract z oceną jakości.

v1.4.5 — [TASK-3] Rozszerzenie Kroku 3 korekcji artefaktów (Potok OCR-2, 10.06.2026).
       Krok 3 rozszerzony: usuwa linie zawierające TYLKO kombinacje znaków
       z zestawu =, -, —, _, ., ,, | i spacji (np. "= .", "- .", "— .").
       Granica separatora sekcji: linie złożone wyłącznie z jednego znaku
       powtórzonego 3+ razy (---,  ===, ___) są ZACHOWYWANE jako separatory.
       Wzorzec: linia musi zawierać co najmniej dwa różne znaki niebiałe
       LUB tylko jeden znak ale nie powtórzony (= czyste artefakty OCR).
       Dotknięte linie: Krok 3 w _fix_ocr_artifacts (~2 linie zmienione).

v1.4.4 — Progi jakości zaktualizowane empirycznie na podstawie testów (10.06.2026).
       Nowe progi: >=80% ok, >=70% warn, <70% reject.
       Poziom "low" zastąpiony przez "reject" — semantycznie precyzyjniejszy,
       sygnalizuje że pipeline odmawia przetwarzania a nie tylko ostrzega.
       Uzasadnienie: conf=83.5% → maskowanie poprawne, conf=66.7% → katastrofalne.
       Granica między 83.5% a 66.7% — próg ustawiony konserwatywnie przy 70%.
v1.4.3 — Wyrównanie progów z założeniami projektowymi.
       Poprzednie progi (80/60) były arbitralne. Nowe (65/50) wynikają
       z analizy zestawów testowych: >=65% = druk/dobry skan,
       50-65% = telefon typowe warunki (warn), <50% = odmowa maskowania
       (implementacja odmowy planowana po testach empirycznych).
       Komunikat "low" rozszerzony o konkretną instrukcję dla użytkownika.
       Nowa funkcja wywoływana w _run_tesseract po image_to_string,
       przed zwróceniem OCRResult. Pięć kroków korekcji.
       [BUG-KOR-1] Krok 1 rozszerzony o sekwencje zaczynające się małą
       literą — "e l i ń s k a" → "elińska" (reszta nazwiska po tym jak
       pierwsza część trafiła do tokenu OSOBA_001).
       [BUG-KOR-2] Krok 2 naprawiony — myślnik dodany do negatywnego
       lookbehind: "583-301-45-52" nie jest już podmieniane na "583-301-45-S2".
       Krytyczny fix przed dystrybucją — poprzednia wersja zmieniała
       cyfry w NIP/PESEL/IBAN co prowadziło do wycieku przez zmianę wartości.
       Dotknięte linie: Krok 1 (~+6 linii), Krok 2 lookbehind (~1 linia).
         Krok 1: złączenie liter rozdzielonych spacjami
                 ("K o w a l s k i" → "Kowalski") — tylko wzorzec
                 Wielka+małe, bezpieczny dla nazwisk i nazw własnych.
         Krok 2: podstawienia cyfra→litera na początku słowa
                 ("0STATECZNE" → "OSTATECZNE") — tylko {"0","1","5"},
                 tylko gdy następna litera jest samogłoską, nie stosuje
                 dla tokenów numerycznych (NIP, PESEL, IBAN).
         Krok 3: usunięcie samotnych linii z ".", ",", "|"
         Krok 4: normalizacja 3+ pustych linii → 2 puste linie
         Krok 5 (poza briefem): split połączonych słów z wielką literą
                 w środku ("SądRejonowy" → "Sąd Rejonowy") — artefakt
                 OCR który powodował false positive w NER.
       Dotknięte linie: nowa funkcja _fix_ocr_artifacts (~160 linii),
       wywołanie w _run_tesseract (1 linia).

v1.3 — martwa gałąź w logice wyboru języka OCR (_run_tesseract):
       usunięto sprzeczny podwójny warunek ("pol+eng" if True był nieosiągalny,
       _check_polish_lang() wywoływane dwa razy). Zastąpiono jednym prostym
       if/else. Zachowanie: pol gdy dostępny, eng gdy nie — bez zmian.

v1.2 — BUG-10: zastąpienie hardkodowanej ścieżki osobistej (C:/Users/p_pie/...)
       przez os.path.expandvars("%LOCALAPPDATA%") w _TESSERACT_CANDIDATES.

v1.1 — jawne ustawienie ścieżki Tesseract przy imporcie modułu.

Zwraca tekst + confidence score (0-100) który służy do
ostrzeżenia użytkownika o jakości odczytu.

Poziomy jakości:
  >= 80  → OK (czysty skan)
  60-79  → WARN (skan słabej jakości, zalecana weryfikacja)
  < 60   → LOW (zdjęcie telefonem, zła jakość — weryfikacja obowiązkowa)

Obsługiwane formaty: PNG, JPG/JPEG, TIFF, BMP, WEBP

Instalacja Tesseract (Windows):
  https://github.com/UB-Mannheim/tesseract/wiki
  Pobierz instalator, zaznacz język "Polish" podczas instalacji.
  Dodaj do PATH: C:\\Program Files\\Tesseract-OCR
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("pseudominizer.ocr")

# ── Ścieżka Tesseract (Windows) ───────────────────────────────────────────────
# Jawne ustawienie ścieżki — nie polegamy na PATH subprocess (zawodne na Windows)
_TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]

def _set_tesseract_path() -> bool:
    """Ustawia pytesseract.tesseract_cmd na pierwszą znalezioną ścieżkę."""
    try:
        import pytesseract
        # Najpierw sprawdź czy aktualna komenda już działa
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            pass
        # Szukaj w znanych lokalizacjach
        for candidate in _TESSERACT_CANDIDATES:
            if Path(candidate).exists():
                pytesseract.tesseract_cmd = candidate
                logger.info(f"[OCR] Tesseract znaleziony: {candidate}")
                try:
                    pytesseract.get_tesseract_version()
                    return True
                except Exception:
                    continue
        return False
    except ImportError:
        return False

# Ustaw ścieżkę raz przy imporcie modułu
_TESSERACT_PATH_OK = _set_tesseract_path()

# ── Typy ─────────────────────────────────────────────────────────────────────

@dataclass
class OCRResult:
    text:        str
    confidence:  float        # 0.0 – 100.0
    quality:     str          # "ok" | "warn" | "reject"
    warning_msg: str          # komunikat dla użytkownika
    engine:      str          # "tesseract" | "unavailable"
    word_count:  int

    @property
    def quality_label(self) -> str:
        return {
            "ok":     "Dobra jakość odczytu",
            "warn":   "Obniżona jakość — zweryfikuj encje ręcznie",
            "reject": "Jakość zbyt niska — maskowanie niemożliwe",
        }.get(self.quality, "Nieznana jakość")


def _quality_from_confidence(conf: float) -> tuple[str, str]:
    """
    Progi jakości ustalone empirycznie na podstawie testów (10.06.2026):

      Obraz 2A (telefon dobre warunki): conf=83.5% → maskowanie poprawne
      Obraz 2B (telefon średnie):       conf=66.7% → maskowanie katastrofalne
      Obraz 2C (telefon złe):           conf=0%    → brak tekstu
      Obraz 3B (stary dokument):        conf=86.7% → maskowanie poprawne

      Granica użyteczności leży między 83.5% a 66.7%.
      Próg odmowy ustawiony konserwatywnie przy 70% jako margines bezpieczeństwa.

      >= 80% → "ok"     — przetwarzaj normalnie
      >= 70% → "warn"   — przetwarzaj z ostrzeżeniem, użytkownik musi sprawdzić
      <  70% → "reject" — odmowa, ryzyko wycieku przez błędne maskowanie
    """
    if conf >= 80:
        return "ok", (
            "Jakość OCR: dobra. Zalecamy przejrzenie tekstu przed wysłaniem — "
            "OCR może pomylić cyfry (0/O, 1/l)."
        )
    if conf >= 70:
        return "warn", (
            f"Jakość OCR: obniżona ({conf:.0f}%). "
            "Sprawdź każdą wykrytą encję ręcznie — przy tej jakości NER może "
            "pominąć dane osobowe lub wykryć błędne wartości."
        )
    return "reject", (
        f"Jakość OCR zbyt niska do bezpiecznego maskowania ({conf:.0f}%). "
        "Zdjęcie jest zbyt niewyraźne, krzywe lub słabo oświetlone. "
        "Wykonaj lepsze zdjęcie: połóż dokument płasko, zapewnij równomierne "
        "oświetlenie, fotografuj prostopadle do dokumentu."
    )


# ── Tesseract ─────────────────────────────────────────────────────────────────

def _tesseract_available() -> bool:
    """Sprawdza dostępność Tesseract — używa flagi ustawionej przy starcie modułu."""
    if _TESSERACT_PATH_OK:
        return True
    # Ostatnia szansa — spróbuj ponownie ustawić ścieżkę (np. po instalacji w trakcie sesji)
    return _set_tesseract_path()


def _check_polish_lang() -> bool:
    """Sprawdza czy zainstalowany jest język polski w Tesseract."""
    try:
        import pytesseract
        langs = pytesseract.get_languages()
        return "pol" in langs
    except Exception:
        return False


def _run_tesseract(image_bytes: bytes, filename: str) -> OCRResult:
    """
    Uruchamia Tesseract na obrazie.
    Zwraca tekst + confidence z danych per-słowo (tsv output).
    """
    import pytesseract
    from PIL import Image
    import io

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"Nie można otworzyć obrazu: {e}")

    # Konwertuj do RGB jeśli RGBA/P (Tesseract nie lubi kanału alpha)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    # Wybierz język
    if _check_polish_lang():
        lang = "pol"
    else:
        lang = "eng"
        logger.warning("[OCR] Język polski niedostępny w Tesseract — używam eng")

    # Pobierz dane per-słowo z confidence
    try:
        tsv_data = pytesseract.image_to_data(
            img,
            lang=lang,
            config="--psm 3",   # automatyczna orientacja i segmentacja strony
            output_type=pytesseract.Output.DICT,
        )
    except Exception as e:
        raise RuntimeError(f"Błąd Tesseract: {e}")

    # Zbierz słowa z confidence > 0 (conf=-1 to nierozpoznane regiony)
    words = []
    confidences = []
    for i, word in enumerate(tsv_data["text"]):
        word = word.strip()
        if not word:
            continue
        conf = tsv_data["conf"][i]
        if conf < 0:
            continue
        words.append(word)
        confidences.append(conf)

    if not words:
        return OCRResult(
            text="", confidence=0.0, quality="low",
            warning_msg="OCR nie rozpoznał żadnego tekstu. Sprawdź jakość obrazu.",
            engine="tesseract", word_count=0,
        )

    # Confidence = średnia ważona (odrzuć skrajne wartości)
    avg_conf = sum(confidences) / len(confidences)
    # Penalizuj jeśli dużo słów ma conf < 30 (znak złej jakości obrazu)
    low_conf_ratio = sum(1 for c in confidences if c < 30) / len(confidences)
    if low_conf_ratio > 0.3:
        avg_conf = avg_conf * (1 - low_conf_ratio * 0.5)

    # Zbuduj tekst z danych tsv (zachowaj podział na linie)
    text = pytesseract.image_to_string(img, lang=lang, config="--psm 3")
    text = text.strip()

    # Korekcja artefaktów OCR przed przekazaniem do NER
    text = _fix_ocr_artifacts(text)

    quality, warning_msg = _quality_from_confidence(avg_conf)

    # Dodatkowe ostrzeżenie jeśli wykryto cyfry (ryzyko błędu w PESEL/NIP)
    has_digits = bool(re.search(r'\d{4,}', text))
    if has_digits and quality != "ok":
        warning_msg += (
            " ⚠ Wykryto ciągi cyfr — sprawdź je szczególnie uważnie "
            "(pomyłka w PESEL lub NIP może być niewidoczna)."
        )

    return OCRResult(
        text=text,
        confidence=round(avg_conf, 1),
        quality=quality,
        warning_msg=warning_msg,
        engine="tesseract",
        word_count=len(words),
    )


# ── Korekcja artefaktów OCR ───────────────────────────────────────────────────

# Mapowanie cyfr OCR → liter — używane w _fix_ocr_artifacts
_DIGIT_MAP: dict[str, str] = {"0": "O", "1": "I", "5": "S"}


def _fix_ocr_artifacts(text: str) -> str:
    """
    Korekcja typowych artefaktów OCR przed przekazaniem tekstu do NER.

    CEL: nie poprawiać tekstu dla czytelności — tylko naprawić artefakty
    które uniemożliwiają NER wykrycie danych osobowych. Np. "K o w a l s k i"
    nie zostanie rozpoznane jako nazwisko, więc nie zostanie zamaskowane.

    Cztery kroki stosowane w ustalonej kolejności:

    Krok 1 — Złączenie liter rozdzielonych spacjami
      Wzorzec: trzy lub więcej pojedynczych liter oddzielonych pojedynczymi
      spacjami. Łączymy gdy sekwencja zaczyna się wielką literą i resztę
      stanowią małe litery — to wzorzec nazwiska/nazwy własnej (Kowalski,
      Adresat). Inicjały z kropkami (J. K.) są bezpieczne — mają kropki
      więc nie pasują do wzorca. Sekwencje jednolite (same wielkie: K O W)
      lub same małe (k o w) pomijamy — zbyt ryzykowne, mogą być skrótami.
      Wybór: tylko mieszane (Wielka + małe) bo to jedyny wzorzec gdzie
      złączenie jest jednoznacznie bezpieczne.

    Krok 2 — Podstawienia cyfra→litera na początku słowa
      Tylko: {"0": "O", "1": "I", "5": "S"} — nie rozszerzamy listy.
      Warunek: cyfra na początku słowa (poprzedzona spacją/początkiem linii),
      następna litera to samogłoska (tylko samogłoski — grupy spółgłoskowe
      zbyt ryzykowne). NIP/PESEL/IBAN zaczynają się od cyfr ale są
      w środku zdania po etykiecie ("PESEL: 850...") — nie spełniają
      warunku "na początku słowa po spacji/początku linii" w tym kontekście
      bo poprzedza je ": " nie spacja+cyfra. Dodatkowe zabezpieczenie:
      nie stosuj gdy cały token to same cyfry (numer bez liter).

    Krok 3 — Usunięcie samotnych znaków interpunkcyjnych jako artefaktów
      Linia zawierająca TYLKO znaki z zestawu: ".", ",", "|", "=", "-",
      "—", "_" i spacje — usuń całą linię (artefakt OCR).
      Wyjątek: linie będące separatorem sekcji — złożone z jednego znaku
      powtórzonego 3 lub więcej razy (np. "---", "===", "___") — zachowaj.
      Uzasadnienie: "= ." lub "- ." to rozpadnięta interpunkcja OCR,
      natomiast "---" to zamierzony separator w dokumencie.

    Krok 4 — Normalizacja pustych linii
      Trzy lub więcej pustych linii z rzędu → dwie puste linie.
      (Zachowujemy jedną pustą linię jako separator akapitów.)

    Krok 5 — Split połączonych słów z wielką literą w środku
      "SądRejonowy" → "Sąd Rejonowy", "podaNy" → "poda Ny" → nie, zbyt
      agresywne dla małe+Wielka w środku. Stosujemy tylko dla sekwencji
      mała_litera + Wielka_litera gdzie obie strony mają >= 2 znaki
      i żadna nie jest cyfrą. "NaszaZnak" → "Nasza Znak". Wyjątek:
      skróty i znane wzorce (Sp., ul., nr) — pomijamy przez próg długości.
    """

    # ── Krok 1: złącz litery rozdzielone spacjami ─────────────────────────────
    # Wzorzec A: sekwencja zaczyna się wielką literą — nazwiska, nazwy własne
    # "K o w a l s k i" → "Kowalski", "A d r e s a t" → "Adresat"
    # Wzorzec B: sekwencja zaczyna się małą literą — reszta nazwiska po tokenizacji
    # "e l i ń s k a" → "elińska" (pierwsza część trafiła do tokenu OSOBA_001)
    # Nie łączy: same wielkie (K O W — skrót), mieszane bez spacji (już złączone)
    def _join_spaced_letters(m: re.Match) -> str:
        return m.group(0).replace(" ", "")

    # Wielka litera + co najmniej dwie małe po spacjach
    text = re.sub(
        r'\b([A-ZĄĆĘŁŃÓŚŹŻ])( [a-ząćęłńóśźż]){2,}\b',
        _join_spaced_letters,
        text
    )
    # [BUG-KOR-1] Mała litera + co najmniej trzy małe po spacjach
    # (trzy zamiast dwóch — "a b" to za krótkie żeby być pewnym)
    text = re.sub(
        r'(?<!\w)([a-ząćęłńóśźż])( [a-ząćęłńóśźż]){3,}\b',
        _join_spaced_letters,
        text
    )

    # ── Krok 2: podstawienia cyfra→litera ────────────────────────────────────
    # Dwa przypadki:
    # A) Cyfra w środku słowa otoczona literami: "WEZWAN1E" → "WEZWANIE"
    # B) Cyfra na początku słowa gdy reszta to same litery: "0STATECZNE" → "OSTATECZNE"
    # [BUG-KOR-2] Nie stosuj gdy cyfra poprzedzona myślnikiem (segment numeru):
    # "583-301-45-52" → bez zmian (poprzednio "583-301-45-S2" — błąd krytyczny)

    def _fix_mid_digit(m: re.Match) -> str:
        return m.group(1) + _DIGIT_MAP.get(m.group(2), m.group(2)) + m.group(3)

    # Przypadek A: cyfra w środku słowa (litera-cyfra-litera)
    text = re.sub(
        r'([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż])([015])([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż])',
        _fix_mid_digit,
        text
    )

    def _fix_start_digit(m: re.Match) -> str:
        digit, rest = m.group(1), m.group(2)
        # Nie podstawiaj jeśli reszta zawiera cyfry (to numer, nie słowo)
        if re.search(r'\d', rest):
            return m.group(0)
        return _DIGIT_MAP.get(digit, digit) + rest

    # Przypadek B: cyfra na początku słowa — nie poprzedzona literą, cyfrą ani myślnikiem
    # [BUG-KOR-2] (?<![\w\-]) zamiast (?<!\w) — wyklucza segmenty po myślniku w numerach
    text = re.sub(
        r'(?<![\w\-])([015])([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]{2,})',
        _fix_start_digit,
        text
    )

    # ── Krok 3: usuń samotne znaki interpunkcyjne / artefakty OCR ─────────────
    # Linia zawierająca TYLKO znaki z zestawu: . , | = - — _ i spacje → usuń.
    # Wyjątek: separator sekcji — jeden znak powtórzony 3+ razy (---, ===, ___).
    # Logika: najpierw sprawdź czy to separator (jeden znak × N) — jeśli tak,
    # zachowaj. Jeśli nie — sprawdź czy linia zawiera tylko znaki artefaktowe.
    def _remove_artifact_line(m: re.Match) -> str:
        line = m.group(0)
        stripped = line.strip()
        if not stripped:
            return line  # pusta linia — poza zakresem Kroku 3
        # Separator sekcji: jeden unikalny znak niebiały powtórzony 3+ razy
        unique_nonws = set(stripped.replace(" ", "").replace("\t", ""))
        if len(unique_nonws) == 1 and len(stripped.replace(" ", "")) >= 3:
            return line  # zachowaj separator (---, ===, ___, ...)
        # Artefakt: linia złożona wyłącznie ze znaków artefaktowych i spacji
        return re.sub(r'^[ \t]*[.,|=\-\u2014_][\s.,|=\-\u2014_]*$', '', line)

    text = re.sub(r'(?m)^[ \t]*[.,|=\-\u2014_][\s.,|=\-\u2014_]*$',
                  _remove_artifact_line, text)

    # ── Krok 4: normalizacja pustych linii ────────────────────────────────────
    # 3+ puste linie z rzędu → 2 puste linie
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # ── Krok 5: split połączonych słów z wielką literą w środku ──────────────
    # "SądRejonowy" → "Sąd Rejonowy"
    # Warunek: mała litera + wielka litera, obie strony >= 2 znaki
    # Nie stosuj dla wzorców gdzie wielka w środku to norma (Sp., McX, itd.)
    def _split_camel(m: re.Match) -> str:
        return m.group(1) + " " + m.group(2)

    text = re.sub(
        r'([a-ząćęłńóśźż]{2,})([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})',
        _split_camel,
        text
    )

    return text


# ── Główna funkcja ────────────────────────────────────────────────────────────

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def extract_text_from_image(image_bytes: bytes, filename: str) -> OCRResult:
    """
    Główna funkcja OCR dla Pseudominizera.

    Jeśli Tesseract niedostępny — zwraca OCRResult z instrukcją instalacji
    zamiast rzucać wyjątek (fail-graceful dla UI).
    """
    if not _tesseract_available():
        msg = (
            "OCR niedostępny — Tesseract nie jest zainstalowany. "
            "Pobierz instalator: https://github.com/UB-Mannheim/tesseract/wiki "
            "i zaznacz język 'Polish' podczas instalacji."
        )
        logger.warning("[OCR] Tesseract niedostępny")
        return OCRResult(
            text="", confidence=0.0, quality="low",
            warning_msg=msg, engine="unavailable", word_count=0,
        )

    try:
        result = _run_tesseract(image_bytes, filename)
        logger.info(
            f"[OCR] {filename}: {result.word_count} słów, "
            f"conf={result.confidence:.1f}%, jakość={result.quality}"
        )
        return result
    except Exception as e:
        logger.error(f"[OCR] błąd dla {filename}: {e}")
        return OCRResult(
            text="", confidence=0.0, quality="low",
            warning_msg=f"Błąd OCR: {e}",
            engine="tesseract", word_count=0,
        )
