"""
ocr_rapid.py — LYNX-OCR-PARITY krok 2, faza A: PP-OCRv6 small (RapidOCR + onnxruntime, CPU) jako OCR testowy.

Włączany wyłącznie jawnie: LYNX_OCR_ENGINE=rapid (domyślnie Tesseract w ocr_engine.py).
Faza A (kontrakt C1 briefu): ocena jakości PP nie jest skalibrowana, więc wynik zawsze
quality="reject", confidence=0.0 (techniczny znacznik „brak skalibrowanej oceny”, nie zmierzone 0%),
stały polski komunikat, engine="rapid" → /preview odmawia (HTTP 422) bez treści, mapy i tokenów.
Tekst zostaje wewnątrz procesu wyłącznie do lokalnej diagnostyki (bezpośrednie wywołanie adaptera).

Modele tylko lokalne, przygotowane przed startem (bez pobierania w trakcie pracy):
  LYNX_OCR_MODEL_DIR (domyślnie ~/lynx_models/ppocrv6_small) z plikami MODEL_FILES.
Awaria techniczna (brak pakietu/modelu, wyjątek, przekroczony czas) → None: ocr_engine wraca do
Tesseracta z jego własną bramką jakości. Niski wynik PP NIE jest powodem powrotu do Tesseracta.
Logi bez treści dokumentu: tylko rodzaj błędu.
"""
from __future__ import annotations

import logging
import os
import statistics
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("lynxmask.ocr_rapid")

ENGINE_ID = "rapid"
C1_WARNING = ("Nowy OCR jest w trybie testowym. Ocena jakości odczytu nie została zweryfikowana; "
              "wynik nie może być udostępniony.")
MODEL_FILES = {"det": "PP-OCRv6_det_small.onnx", "rec": "PP-OCRv6_rec_small.onnx",
               "cls": "ch_ppocr_mobile_v2.0_cls_mobile.onnx"}
TIMEOUT_S = float(os.environ.get("LYNX_OCR_RAPID_TIMEOUT", "60"))
COLUMN_GAP = "    "   # duża przerwa w linii = osobne pole/kolumna, nie jeden wyraz

_engine: Any = None
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ocr_rapid")


def model_dir() -> Path:
    return Path(os.environ.get("LYNX_OCR_MODEL_DIR", Path.home() / "lynx_models" / "ppocrv6_small"))


def _get_engine() -> Any:
    """Silnik RapidOCR tworzony najwyżej raz na proces; tylko z lokalnych plików modeli."""
    global _engine
    if _engine is None:
        paths = {k: model_dir() / f for k, f in MODEL_FILES.items()}
        missing = [k for k, p in paths.items() if not p.is_file()]
        if missing:
            raise FileNotFoundError("brak modeli PP-OCR: " + ",".join(missing))
        from rapidocr import ModelType, OCRVersion, RapidOCR
        _engine = RapidOCR(params={
            "Global.log_level": "error",
            "Det.ocr_version": OCRVersion.PPOCRV6, "Det.model_type": ModelType.SMALL, "Det.model_path": str(paths["det"]),
            "Rec.ocr_version": OCRVersion.PPOCRV6, "Rec.model_type": ModelType.SMALL, "Rec.model_path": str(paths["rec"]),
            "Cls.model_path": str(paths["cls"]),
        })
    return _engine


def _center_y(box) -> float:
    return sum(p[1] for p in box) / len(box)


def _height(box) -> float:
    ys = [p[1] for p in box]
    return max(ys) - min(ys) or 1.0


def build_text(boxes, txts) -> str:
    """Kolejność odczytu: wiersze wg środka pionowego, w wierszu od lewej; duża przerwa → COLUMN_GAP."""
    items = sorted(zip(boxes, txts), key=lambda b: (_center_y(b[0]), b[0][0][0]))
    rows: list[list] = []
    for box, txt in items:
        if rows and abs(_center_y(box) - _center_y(rows[-1][0][0])) <= 0.5 * max(_height(box), _height(rows[-1][0][0])):
            rows[-1].append((box, txt))
        else:
            rows.append([(box, txt)])
    lines = []
    for row in rows:
        row.sort(key=lambda b: b[0][0][0])
        h = statistics.median(_height(b) for b, _ in row)
        parts = [row[0][1]]
        for (pbox, _), (box, txt) in zip(row, row[1:]):
            gap = box[0][0] - max(p[0] for p in pbox)
            parts.append((COLUMN_GAP if gap > 2.0 * h else " ") + txt)
        lines.append("".join(parts))
    return "\n".join(lines)


def recognize(image_bytes: bytes, timeout: float) -> str:
    """Tekst z obrazu; wyjątek przy awarii technicznej lub przekroczeniu czasu."""
    engine = _get_engine()
    res = _pool.submit(engine, image_bytes).result(timeout=timeout)
    if res is None or res.boxes is None:
        return ""
    return build_text(res.boxes, res.txts)


def extract_rapid(image_bytes: bytes, result_cls: Callable[..., Any]) -> Any | None:
    """OCRResult fazy A (C1) albo None przy awarii technicznej (wtedy Tesseract)."""
    try:
        text = recognize(image_bytes, TIMEOUT_S)
    except FutureTimeout:
        logger.error("[OCR-RAPID] przekroczony czas %.0f s — powrót do Tesseracta", TIMEOUT_S)
        return None
    except Exception as e:  # noqa: BLE001 — bez treści wyjątku (S5)
        logger.error("[OCR-RAPID] awaria %s — powrót do Tesseracta", type(e).__name__)
        return None
    return result_cls(text=text, confidence=0.0, quality="reject", warning_msg=C1_WARNING,
                      engine=ENGINE_ID, word_count=len(text.split()))
