"""
photo_chain.py — [LYNX-PHOTO-CHAIN] łańcuch zdjęcia: orientacja → obrót → PP-OCRv6 → przyjęcie albo odmowa odczytu.

Włączany wyłącznie jawnie (LYNX_OCR_ENGINE=rapid w ocr_engine.py); domyślnie Tesseract bez zmian.
- Orientacja: lokalny model PP-LCNet_x1_0_doc_ori (Apache-2.0, ONNX, SHA256 w kodzie) na miniaturze 224 px; obrót pełnej
  rozdzielczości. Model i PP widzą te same piksele (dekodowanie z EXIF), więc obrót nie może się zdublować; EXIF nie jest arbitrem.
- Przyjęcie odczytu: pewność klasyfikatora ORIENTACJI ≥ ORI_MIN_CONF i udział słów ≥3-literowych znanych Morfeuszowi ≥ DICT_MIN_SHARE
  przy co najmniej MIN_WORDS słowach. Pewność PP NIE jest używana (B1 NO_SAFE_GATE). Progi to kandydaci do pomiaru i zgody OWNERA
  (nadpisywalne zmiennymi środowiska wyłącznie na potrzeby pomiaru).
- Słaby odczyt → odmowa z alternatywą (bez tekstu w odpowiedzi API). Awaria techniczna → kod przyczyny (str) → ocr_engine
  jednorazowo używa Tesseracta z jego bramką. Słaby, ale wykonany odczyt PP nigdy nie przechodzi do Tesseracta.
Logi bez treści dokumentu i nazw plików: tylko kody.
"""
from __future__ import annotations

import logging
import os
import re
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any, Callable

import ocr_rapid

logger = logging.getLogger("lynxmask.photo_chain")

ORI_MODEL = "PP-LCNet_x1_0_doc_ori.onnx"
ORI_SHA256 = "5dcaf4e3359c35af086f64445ceefab0b4461ad5de752ca89e1d2a0fbefd37f5"
ORI_ANGLES = (0, 90, 180, 270)            # klasa = obrót obrazu zgodnie z ruchem wskazówek (pomiar CC 20.10, 600/600)
ORI_MIN_CONF = float(os.environ.get("LYNX_PHOTO_ORI_MIN", "0.60"))
DICT_MIN_SHARE = float(os.environ.get("LYNX_PHOTO_DICT_MIN", "0.80"))
MIN_WORDS = 5
REJECT_MSG = ("Popraw ujęcie: skorzystaj ze skanera dokumentów, ustaw lepsze światło i kąt aparatu. "
              "Możesz też wkleić tekst dokumentu.")
_WORD = re.compile(r"[^\W\d_]{3,}")
_MEAN, _STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)

_session: Any = None
_morf: Any = None


def _ori_session() -> Any:
    global _session
    if _session is None:
        import onnxruntime as ort
        path = ocr_rapid.verified_model(ORI_MODEL, ORI_SHA256)
        ocr_rapid.disable_onnx_telemetry()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = ocr_rapid.THREADS
        _session = ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])
    return _session


def decode(image_bytes: bytes) -> Any:
    """Obraz BGR (tak jak go wyświetla system — z EXIF); wyjątek, gdy to nie obraz."""
    import cv2
    import numpy as np
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("nieczytelny obraz")
    return img


def classify(bgr: Any) -> tuple[int, float]:
    """(obrót zgodnie z ruchem wskazówek, pewność) — preprocessing jak oficjalny inference.yml modelu."""
    import cv2
    import numpy as np
    h, w = bgr.shape[:2]
    s = 256 / min(h, w)
    img = cv2.resize(bgr, (round(w * s), round(h * s)), interpolation=cv2.INTER_LINEAR)
    h, w = img.shape[:2]
    y, x = (h - 224) // 2, (w - 224) // 2
    img = cv2.cvtColor(img[y:y + 224, x:x + 224], cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x_in = ((img - np.array(_MEAN, np.float32)) / np.array(_STD, np.float32)).transpose(2, 0, 1)[None]
    p = _ori_session().run(None, {"x": x_in})[0][0].astype(np.float64)   # model zwraca już prawdopodobieństwa (softmax)
    p /= p.sum()
    k = int(np.argmax(p))
    return ORI_ANGLES[k], float(p[k])


def upright(bgr: Any, angle: int) -> Any:
    import cv2
    fix = {90: cv2.ROTATE_90_COUNTERCLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_CLOCKWISE}.get(angle)
    return bgr if fix is None else cv2.rotate(bgr, fix)


def dictionary_share(text: str) -> tuple[int, int]:
    """(słowa znane Morfeuszowi, słowa ≥3-literowe) — miarka niezależna od pewności PP."""
    global _morf
    words = _WORD.findall(text)
    if not words:
        return 0, 0
    if _morf is None:
        import morfeusz2
        _morf = morfeusz2.Morfeusz(generate=False)
    known = sum(1 for w in words if any(i[2][2] != "ign" for i in _morf.analyse(w)))
    return known, len(words)


def accept(ori_conf: float, known: int, total: int) -> str:
    """Kod decyzji: 'ok' albo przyczyna odmowy (jedna granica, bez pasma ostrzeżeń)."""
    if ori_conf < ORI_MIN_CONF:
        return "ORIENTATION_UNCERTAIN"
    if total < MIN_WORDS:
        return "QUALITY_UNEVALUABLE"
    if known / total < DICT_MIN_SHARE:
        return "QUALITY_LOW"
    return "ok"


def read_photo(image_bytes: bytes, result_cls: Callable[..., Any]) -> Any:
    """OCRResult (ok/reject, engine='rapid') albo str — kod awarii technicznej (wtedy Tesseract)."""
    try:
        bgr = decode(image_bytes)
        angle, ori_conf = classify(bgr)
        if ori_conf < ORI_MIN_CONF:   # nie czytamy obrazu, którego nie umiemy ustawić
            return _result(result_cls, "", accept(ori_conf, 0, 0))
        text = ocr_rapid.recognize(upright(bgr, angle), ocr_rapid.TIMEOUT_S)
        known, total = dictionary_share(text)
    except FutureTimeout:
        logger.error("[PHOTO] PP: przekroczony czas — PP wyłączony do restartu, zapas Tesseract")
        return "PP_TIMEOUT"
    except ocr_rapid.PPUnavailable as e:
        return str(e)
    except Exception as e:  # noqa: BLE001 — bez treści wyjątku (S5)
        logger.error("[PHOTO] awaria %s — zapas Tesseract", type(e).__name__)
        return "PP_FAILURE"
    decision = accept(ori_conf, known, total)
    logger.info("[PHOTO] obrót=%d pewność_orient=%.2f słowa=%d/%d decyzja=%s", angle, ori_conf, known, total, decision)
    return _result(result_cls, text, decision)


def _result(result_cls: Callable[..., Any], text: str, decision: str) -> Any:
    ok = decision == "ok"
    return result_cls(text=text if ok else "", confidence=0.0, quality="ok" if ok else "reject",
                      warning_msg="" if ok else REJECT_MSG, engine=ocr_rapid.ENGINE_ID,
                      word_count=len(text.split()) if ok else 0, reason=decision)
