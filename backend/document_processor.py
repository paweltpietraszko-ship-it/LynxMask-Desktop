"""
document_processor.py  v1.2
Wydzielone z pseudominizer_api.py v1.23-TAURI.

Historia zmian:
  v1.2 — [FIX-DOCX-IMPORT]: Rozdzielenie importu od użycia w branch PDF i DOCX.
          Poprzednio jeden blok try/except ImportError owijał zarówno import
          jak i wywołanie Document()/fitz.open() — błąd wewnętrzny biblioteki
          (np. uszkodzony plik, brakująca zależność) był mylnie raportowany
          jako "Biblioteka niedostępna" zamiast rzeczywistej przyczyny.
          Teraz ImportError łapie tylko faktyczny brak pakietu.
          Dotknięte linie: branch .pdf (~65-73), branch .docx (~75-84).
  v1.1 — BUG-12: PSE_REGISTRY zmieniony na sciezke bezwzgledna przez __file__.
          Linia dotknięta: ~14.
          Dlaczego bezpieczne: tylko zmiana defaultu sciezki, zmienna
          srodowiskowa PSE_REGISTRY nadal dziala jako override,
          logika _next_pse() niezmieniona.

Zawiera:
  _next_pse()    — sekwencyjny generator kodów PSE-RRRR-NNNN
  _extract_text() — ekstrakcja tekstu z PDF/DOCX/TXT/obraz
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("pseudominizer.document_processor")

# ── Rejestr PSE ──────────────────────────────────────────────────────────────

PSE_REGISTRY = Path(os.getenv("PSE_REGISTRY", str(Path(__file__).parent / "pse_registry.json")))

_pse_lock = threading.Lock()


def _next_pse() -> str:
    """
    Zwraca następny sekwencyjny kod PSE w formacie PSE-RRRR-NNNN.
    Rejestr przechowywany w pse_registry.json.
    Thread-safe: threading.Lock.
    """
    year = datetime.now().year
    with _pse_lock:
        try:
            if PSE_REGISTRY.exists():
                data = json.loads(PSE_REGISTRY.read_text(encoding="utf-8"))
            else:
                data = {"counter": 0, "year": year}
            if data.get("year") != year:
                data = {"counter": 0, "year": year}
            data["counter"] += 1
            PSE_REGISTRY.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8"
            )
            return f"PSE-{year}-{data['counter']:04d}"
        except Exception as e:
            logger.error(f"[PSE] Błąd rejestru: {e}")
            import time
            return f"PSE-{year}-{int(time.time()) % 10000:04d}"


# ── OCR ──────────────────────────────────────────────────────────────────────

try:
    from ocr_engine import extract_text_from_image, is_image
    _OCR_AVAILABLE = True
    logger.info("[STARTUP] OCR (Tesseract) dostepny")
except ImportError:
    _OCR_AVAILABLE = False
    is_image = lambda f: False
    logger.warning("[STARTUP] ocr_engine niedostepny")


# ── Ekstrakcja tekstu ─────────────────────────────────────────────────────────

def _docx_body_text(doc) -> str:
    """[LYNX-DOCX-TABLES] Akapity i zwykłe tabele treści DOCX w kolejności dokumentu. Każda komórka (także scalona,
    zwracana przez python-docx pod wieloma adresami) raz; akapity/komórki/wiersze rozdzielone nową linią, by wartości
    z sąsiednich komórek się nie skleiły. Poza zakresem: nagłówki/stopki, tabele zagnieżdżone, kształty, przypisy."""
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    parts: list[str] = []
    for el in doc.element.body.iterchildren():
        if el.tag == qn("w:p"):
            parts.append(Paragraph(el, doc).text)
        elif el.tag == qn("w:tbl"):
            seen: list = []
            for row in Table(el, doc).rows:
                for cell in row.cells:
                    if any(cell._tc is tc for tc in seen):
                        continue
                    seen.append(cell._tc)
                    parts += [p.text for p in cell.paragraphs]
    return "\n".join(t for t in parts if t.strip())


_PDF_COMB = 1 << 24  # flaga Ff „comb” pola tekstowego AcroForm: jeden znak na kratkę


def _pdf_page_text(page) -> str:
    """[LYNX-ZUS-BOXED-IDS] Tekst strony PDF. PESEL/NIP z pola kratkowego AcroForm get_text() podaje cyfrą na linię;
    taki ciąg zastępujemy wartością pola — granice wyłącznie z pola, nigdy z sąsiednich linii. Gdy wygląd pola
    nie daje dokładnie tych znaków albo ciąg występuje więcej razy niż pól z tą wartością — tekst bez zmian."""
    import re
    text = page.get_text()
    boxed: dict[str, int] = {}
    for w in page.widgets():
        value = w.field_value if isinstance(w.field_value, str) else ""
        if w.field_flags & _PDF_COMB and len(value) in (10, 11) and value.isascii() and value.isdigit():
            per_char = "\n".join(value) + "\n"
            if page.get_text(clip=w.rect) == per_char:
                boxed[per_char] = boxed.get(per_char, 0) + 1
    for per_char, n_fields in sorted(boxed.items(), key=lambda kv: -len(kv[0])):  # PESEL przed NIP-em, który może być jego początkiem
        pattern = re.compile(r"(?<![^\n])" + re.escape(per_char))  # od początku linii
        if len(pattern.findall(text)) == n_fields:
            text = pattern.sub(per_char.replace("\n", "") + "\n", text)
    return text


def _extract_text(content: bytes, filename: str) -> tuple[str, str | None, dict | None]:
    """
    Wyciąga tekst z pliku. Zwraca (tekst, błąd, ocr_meta).
    Obsługuje: PDF, DOCX, TXT, MD, PNG, JPG, TIFF, BMP, WEBP.
    """
    fname = filename.lower()

    if _OCR_AVAILABLE and is_image(fname):
        from ocr_engine import extract_text_from_image
        result = extract_text_from_image(content, filename)
        ocr_meta = {
            "confidence": result.confidence,
            "quality":    result.quality,
            "warning":    result.warning_msg,
            "engine":     result.engine,
            "word_count": result.word_count,
            "reason":     result.reason,  # [LYNX-PHOTO-CHAIN] kod bez treści
        }
        if not result.text:
            return "", result.warning_msg, ocr_meta
        return result.text, None, ocr_meta

    if not _OCR_AVAILABLE and is_image(fname):
        return "", (
            "OCR niedostępny. Zainstaluj Tesseract: "
            "https://github.com/UB-Mannheim/tesseract/wiki "
            "(zaznacz język Polish podczas instalacji)"
        ), None

    if fname.endswith(".pdf"):
        # [FIX-DOCX-IMPORT] Rozdzielenie importu od użycia — analogicznie jak DOCX.
        try:
            import fitz
        except ImportError:
            return "", "Biblioteka pymupdf niedostępna — zainstaluj: pip install pymupdf", None
        try:
            with fitz.open(stream=content, filetype="pdf") as doc:
                text = "\n".join(_pdf_page_text(page) for page in doc)
            return text, None, None
        except Exception as e:
            return "", f"Błąd odczytu PDF: {e}", None

    if fname.endswith(".docx"):
        # [FIX-DOCX-IMPORT] Rozdzielenie importu od użycia.
        # Poprzednio: jeden blok try/except ImportError owijał zarówno import
        # jak i Document() — błąd wewnątrz Document() (np. uszkodzony plik,
        # brakująca zależność docx) mógł być mylnie raportowany jako
        # "Biblioteka niedostępna" zamiast rzeczywistej przyczyny.
        try:
            import io
            from docx import Document
        except ImportError:
            return "", "Biblioteka python-docx niedostępna — zainstaluj: pip install python-docx", None
        try:
            doc = Document(io.BytesIO(content))
            return _docx_body_text(doc), None, None
        except Exception as e:
            return "", f"Błąd odczytu DOCX: {e}", None

    if fname.endswith((".txt", ".md")):
        return content.decode("utf-8", errors="replace"), None, None

    return "", "Nieobsługiwany format. Obsługiwane: PDF, DOCX, TXT, MD, PNG, JPG, TIFF", None
