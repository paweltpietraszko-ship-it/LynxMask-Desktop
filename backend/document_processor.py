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
                text = "\n".join(page.get_text() for page in doc)
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
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return text, None, None
        except Exception as e:
            return "", f"Błąd odczytu DOCX: {e}", None

    if fname.endswith((".txt", ".md")):
        return content.decode("utf-8", errors="replace"), None, None

    return "", "Nieobsługiwany format. Obsługiwane: PDF, DOCX, TXT, MD, PNG, JPG, TIFF", None
