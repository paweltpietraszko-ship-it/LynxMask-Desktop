"""
export_pdf.py  v1.0
Generowanie czystego PDF z pseudonimizowanego tekstu.

Historia zmian:
  v1.0 — [FIX-PDF-META] Nowy moduł. Zastępuje druk przeglądarki do PDF.
          Przyczyna: "Microsoft: Print To PDF" dokłada Author/Creator z konta
          Windows — imię i nazwisko użytkownika w metadanych "zanonimizowanego"
          dokumentu to wyciek RODO. PyMuPDF generuje PDF server-side z pustymi
          metadanymi niezależnie od systemu operacyjnego klienta.

API publiczne:
  generate_pdf(text, filename) -> bytes
    Zwraca bajty PDF gotowe do wysłania jako application/pdf.
    Przy błędzie rzuca RuntimeError z opisem.

Zależności: PyMuPDF (fitz) — już wymagany przez _extract_text w pseudominizer_api.
"""

import logging
import re

logger = logging.getLogger("pseudominizer.export_pdf")

# Szerokość i marginesy strony A4 w punktach (1 punkt = 1/72 cala)
_PAGE_WIDTH  = 595   # A4 szerokość
_PAGE_HEIGHT = 842   # A4 wysokość
_MARGIN_X    = 60
_MARGIN_Y    = 60
_FONT_SIZE   = 10
_LINE_HEIGHT = 14    # interlinia
_TEXT_WIDTH  = _PAGE_WIDTH - 2 * _MARGIN_X


def generate_pdf(text: str, filename: str = "dokument") -> bytes:
    """
    Generuje PDF z tekstu z czystymi metadanymi.

    Metadane wyjściowe:
      title    = filename (bez rozszerzenia, bez ścieżki)
      author   = ""       ← kluczowe: brak nazwiska użytkownika
      creator  = ""
      producer = "Pseudominizer"
      keywords = ""
      subject  = ""

    [FIX-PDF-META] author="" zamiast automatycznego Author z konta Windows.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError(
            "PyMuPDF niedostępny. Zainstaluj: pip install pymupdf"
        )

    # Wyczyść nazwę pliku do tytułu — bez ścieżki i rozszerzenia
    safe_title = re.sub(r"[^\w\s\-]", "", filename.rsplit(".", 1)[0])[:80] or "Dokument"

    doc = fitz.open()

    # Ustaw metadane — wszystkie pola jawnie puste lub generyczne
    # [FIX-PDF-META] Każde pole musi być jawnie ustawione — PyMuPDF
    # wypełnia brakujące pola wartościami systemowymi (author = login użytkownika).
    doc.set_metadata({
        "title":    safe_title,
        "author":   "",          # ← nie Windows login
        "subject":  "",
        "keywords": "",
        "creator":  "",          # ← nie nazwa aplikacji
        "producer": "Pseudominizer",
        "creationDate": "",      # ← nie ujawniamy czasu
        "modDate":  "",
    })

    # Podziel tekst na linie i rozłóż na strony
    lines = _wrap_text(text, max_chars=_max_chars_per_line())
    lines_per_page = (_PAGE_HEIGHT - 2 * _MARGIN_Y) // _LINE_HEIGHT

    page = None
    y = _MARGIN_Y

    for i, line in enumerate(lines):
        if page is None or y + _LINE_HEIGHT > _PAGE_HEIGHT - _MARGIN_Y:
            page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
            y = _MARGIN_Y

        if line.strip():
            page.insert_text(
                (float(_MARGIN_X), float(y)),
                line,
                fontsize=_FONT_SIZE,
                fontname="helv",
                color=(0, 0, 0),
            )
        y += _LINE_HEIGHT

    if len(doc) == 0:
        doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)

    pdf_bytes = doc.tobytes(
        garbage=4,      # usuń nieużywane obiekty
        deflate=True,   # kompresja
        clean=True,     # wyczyść strumienie
    )
    doc.close()

    logger.info(
        "[EXPORT-PDF] Wygenerowano PDF: %d stron, %d bajtów, title=%r",
        (len(lines) // int(lines_per_page) + 1),
        len(pdf_bytes),
        safe_title,
    )
    return pdf_bytes


def _max_chars_per_line() -> int:
    """Przybliżona liczba znaków na linię dla czcionki Helvetica 10pt."""
    # Helvetica 10pt: ~5.5pt na znak → (~535pt szerokości) / 5.5 ≈ 97 znaków
    return int(_TEXT_WIDTH / 5.5)


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """
    Dzieli tekst na linie z zawijaniem długich wierszy.
    Zachowuje oryginalne podziały linii z dokumentu.
    """
    result = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            result.append("")
            continue
        # Zawijaj długie linie po słowach
        words = paragraph.split(" ")
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= max_chars:
                current = (current + " " + word).lstrip()
            else:
                if current:
                    result.append(current)
                # Jeśli słowo dłuższe niż linia — przytnij twardo
                while len(word) > max_chars:
                    result.append(word[:max_chars])
                    word = word[max_chars:]
                current = word
        if current:
            result.append(current)
    return result
