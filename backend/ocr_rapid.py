"""
ocr_rapid.py — PP-OCRv6 small (RapidOCR + onnxruntime, CPU): wykonawca odczytu dla łańcucha zdjęć (photo_chain.py).

Domyślny czytnik zdjęć (OWNER 20.10); LYNX_OCR_ENGINE=tesseract wymusza dawną ścieżkę Tesseracta. [LYNX-PHOTO-CHAIN] Ten moduł tylko czyta;
o przyjęciu/odmowie odczytu decyduje photo_chain (pewność PP nie jest miarą jakości — B1 NO_SAFE_GATE).

Modele tylko lokalne, bez pobierania w trakcie pracy: katalog model_dir() (domyślnie backend/models/ocr — miejsce dla instalatora;
LYNX_OCR_MODEL_DIR nadpisuje) z plikami MODEL_FILES o sumach MODEL_SHA256. Brak pliku / zły hash → PP niedostępny.
Przekroczony czas: wątek PP nie daje się przerwać, więc PP zostaje wyłączony do restartu (bez kolejkowania kolejnych zadań
do zawieszonego wykonawcy). Logi bez treści dokumentu: tylko rodzaj błędu.
"""
from __future__ import annotations

import logging
import hashlib
import os
import statistics
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any

logger = logging.getLogger("lynxmask.ocr_rapid")

ENGINE_ID = "rapid"
MODEL_FILES = {"det": "PP-OCRv6_det_small.onnx", "rec": "PP-OCRv6_rec_small.onnx",
               "cls": "ch_ppocr_mobile_v2.0_cls_mobile.onnx"}
MODEL_SHA256 = {
    "PP-OCRv6_det_small.onnx": "090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f",
    "PP-OCRv6_rec_small.onnx": "6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx": "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c",
}
TIMEOUT_S = float(os.environ.get("LYNX_OCR_RAPID_TIMEOUT", "60"))
# Wątki ONNX: więcej ≠ szybciej (pomiar 20.10, 24 wątki logiczne: wszystkie 1,7–2,2 s/str. i ~84% CPU; 6 wątków 1,0–1,4 s
# i ~47% CPU) — użytkownik pracuje obok, więc PP nie zajmuje całego procesora. Ocena sprzętu: LYNX-INSTALLER.
THREADS = int(os.environ.get("LYNX_OCR_THREADS", 0)) or min(6, max(2, (os.cpu_count() or 8) // 4))
COLUMN_GAP = "    "   # duża przerwa w linii = osobne pole/kolumna, nie jeden wyraz

_engine: Any = None
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ocr_rapid")
_unavailable: str | None = None   # kod przyczyny; ustawiony po przekroczeniu czasu → PP wyłączony do restartu


class PPUnavailable(RuntimeError):
    """PP wyłączony do restartu procesu (zawieszony wątek po przekroczeniu czasu)."""


def model_dir() -> Path:
    return Path(os.environ.get("LYNX_OCR_MODEL_DIR", Path(__file__).resolve().parent / "models" / "ocr"))


def verified_model(name: str, sha256: str) -> Path:
    """Ścieżka lokalnego pliku modelu po sprawdzeniu SHA256; brak/niezgodność → wyjątek (nigdy niezweryfikowane wagi)."""
    path = model_dir() / name
    if not path.is_file():
        raise FileNotFoundError("brak modelu")
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
        raise ValueError("niezgodny SHA256 modelu")
    return path


def disable_onnx_telemetry() -> None:
    import onnxruntime
    if hasattr(onnxruntime, "disable_telemetry_events"):
        onnxruntime.disable_telemetry_events()


def _get_engine() -> Any:
    """Silnik RapidOCR tworzony najwyżej raz na proces; tylko z lokalnych, zweryfikowanych plików modeli."""
    global _engine
    if _engine is None:
        paths = {k: verified_model(f, MODEL_SHA256[f]) for k, f in MODEL_FILES.items()}
        disable_onnx_telemetry()
        from rapidocr import ModelType, OCRVersion, RapidOCR
        _engine = RapidOCR(params={
            "Global.log_level": "error",
            "Det.ocr_version": OCRVersion.PPOCRV6, "Det.model_type": ModelType.SMALL, "Det.model_path": str(paths["det"]),
            "Rec.ocr_version": OCRVersion.PPOCRV6, "Rec.model_type": ModelType.SMALL, "Rec.model_path": str(paths["rec"]),
            "Cls.model_path": str(paths["cls"]), "EngineConfig.onnxruntime.intra_op_num_threads": THREADS,
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


def recognize(image: Any, timeout: float) -> str:
    """Tekst z obrazu (bajty albo tablica BGR); wyjątek przy awarii technicznej lub przekroczeniu czasu."""
    global _unavailable
    if _unavailable:
        raise PPUnavailable(_unavailable)
    engine = _get_engine()
    try:
        res = _pool.submit(engine, image).result(timeout=timeout)
    except FutureTimeout:
        _unavailable = "PP_TIMEOUT"   # wątek nadal pracuje — nie dokładamy zadań do zawieszonego wykonawcy
        raise
    if res is None or res.boxes is None:
        return ""
    return build_text(res.boxes, res.txts)
