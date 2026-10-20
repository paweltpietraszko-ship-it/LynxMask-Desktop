# [LYNX-PHOTO-CHAIN] Łańcuch zdjęcia: orientacja → obrót → PP → przyjęcie/odmowa; zapas Tesseract tylko przy awarii.
# Atrapy modeli sprawdzają logikę, nie jakość OCR. Test na prawdziwych modelach skipuje się bez plików w backend/models/ocr.
# Uruchamiać jawnie: py -3 -m pytest tests/test_photo_chain.py -q (plik spoza pytest.ini python_files).
import io
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import document_processor  # noqa: E402
import ocr_engine  # noqa: E402
import ocr_rapid  # noqa: E402
import photo_chain  # noqa: E402
import startup_check  # noqa: E402

GOOD = "Umowa najmu lokalu mieszkalnego zawarta pomiędzy stronami w dniu dzisiejszym"
JUNK = "Xqzt wrrpl Umowa kkjhq zzvbn ppqrt najmu"
SYNTH = Path(os.environ.get("LYNX_SYNTH_DIR", BACKEND / "dataset_20260627_095419"))   # syntetyki, lokalnie


class FakeEngine:
    def __init__(self, text="", delay=0.0, exc=None):
        self.text, self.delay, self.exc, self.calls, self.images = text, delay, exc, 0, []

    def __call__(self, image):
        self.calls += 1
        self.images.append(image)
        if self.delay:
            time.sleep(self.delay)
        if self.exc:
            raise self.exc
        words = self.text.split()
        boxes = [[[10 + 60 * i, 10], [60 + 60 * i, 10], [60 + 60 * i, 30], [10 + 60 * i, 30]] for i in range(len(words))]
        return SimpleNamespace(boxes=boxes or None, txts=words)


def png(w=40, h=20):
    img = np.zeros((h, w, 3), np.uint8)
    img[:5, :10] = 255   # asymetria: biały róg lewy-górny
    return cv2.imencode(".png", img)[1].tobytes(), img


@pytest.fixture
def chain(monkeypatch):
    monkeypatch.setenv("LYNX_OCR_ENGINE", "rapid")
    monkeypatch.setattr(ocr_rapid, "_unavailable", None)
    monkeypatch.setattr(ocr_engine, "_tesseract_available", lambda: True)
    tess = ocr_engine.OCRResult(text="T", confidence=90.0, quality="ok", warning_msg="", engine="tesseract", word_count=1)
    calls = []
    monkeypatch.setattr(ocr_engine, "_run_tesseract", lambda b, f: calls.append(1) or tess)

    def use(engine, angle=0, conf=0.95):
        monkeypatch.setattr(ocr_rapid, "_engine", engine)
        monkeypatch.setattr(photo_chain, "classify", lambda bgr: (angle, conf))
        return engine
    return SimpleNamespace(use=use, tess=tess, tess_calls=calls)


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
def test_each_orientation_is_turned_upright_once(chain, angle):
    _, img = png()
    turned = {0: img, 90: cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE), 180: cv2.rotate(img, cv2.ROTATE_180),
              270: cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)}[angle]
    eng = chain.use(FakeEngine(GOOD), angle=angle)
    r = ocr_engine.extract_text_from_image(cv2.imencode(".png", turned)[1].tobytes(), "x.png")
    assert (r.quality, r.engine, r.reason) == ("ok", "rapid", "ok") and r.text == GOOD
    assert eng.calls == 1 and np.array_equal(eng.images[0], img)   # PP czyta raz, wyprostowany obraz


def test_exif_rotation_is_not_doubled(chain, monkeypatch):
    seen = []
    pil = Image.new("RGB", (40, 20), "black")
    pil.paste((255, 255, 255), (0, 0, 10, 5))
    exif = pil.getexif()
    exif[0x0112] = 6   # EXIF: obróć 90° do wyświetlenia
    buf = io.BytesIO()
    pil.save(buf, "JPEG", exif=exif, quality=100)
    eng = chain.use(FakeEngine(GOOD))
    monkeypatch.setattr(photo_chain, "classify", lambda bgr: seen.append(bgr) or (0, 0.95))
    ocr_engine.extract_text_from_image(buf.getvalue(), "x.jpg")
    assert seen[0] is eng.images[0]   # model orientacji i PP widzą dokładnie te same piksele


@pytest.mark.parametrize("ori,known,total,decision", [
    (0.60, 4, 5, "ok"), (0.5999, 5, 5, "ORIENTATION_UNCERTAIN"), (0.95, 4, 4, "QUALITY_UNEVALUABLE"),
    (0.95, 0, 0, "QUALITY_UNEVALUABLE"), (0.95, 7, 10, "ok"), (0.95, 69, 100, "QUALITY_LOW")])   # próg OWNERA 0,70
def test_single_boundary_without_warning_band(ori, known, total, decision):
    assert photo_chain.accept(ori, known, total) == decision


def test_classifier_tie_is_deterministic_and_rejected(monkeypatch):
    monkeypatch.setattr(photo_chain, "_session", SimpleNamespace(run=lambda *_a, **_k: [np.full((1, 4), 0.25, np.float32)]))
    _, img = png()
    angle, conf = photo_chain.classify(img)
    assert (angle, round(conf, 2)) == (0, 0.25) and photo_chain.accept(conf, 10, 10) == "ORIENTATION_UNCERTAIN"


@pytest.mark.parametrize("text,reason", [(JUNK, "QUALITY_LOW"), ("Umowa najmu", "QUALITY_UNEVALUABLE"), ("", "QUALITY_UNEVALUABLE")])
def test_weak_read_is_refused_with_alternative_and_never_goes_to_tesseract(chain, text, reason):
    chain.use(FakeEngine(text))
    r = ocr_engine.extract_text_from_image(png()[0], "x.png")
    assert (r.quality, r.engine, r.reason, r.text, r.word_count) == ("reject", "rapid", reason, "", 0)
    assert r.warning_msg == photo_chain.REJECT_MSG and "wkleić tekst" in r.warning_msg
    assert not any(c.isdigit() for c in r.warning_msg) and "%" not in r.warning_msg
    assert chain.tess_calls == []


def test_uncertain_orientation_is_refused_without_reading(chain):
    eng = chain.use(FakeEngine(GOOD), conf=0.35)
    r = ocr_engine.extract_text_from_image(png()[0], "x.png")
    assert (r.quality, r.reason) == ("reject", "ORIENTATION_UNCERTAIN") and eng.calls == 0 and chain.tess_calls == []


def test_refusal_reaches_api_without_text_and_with_reject_meta(chain):
    chain.use(FakeEngine(JUNK))
    text, err, meta = document_processor._extract_text(png()[0], "x.png")
    assert text == "" and err == photo_chain.REJECT_MSG
    assert (meta["quality"], meta["engine"], meta["reason"]) == ("reject", "rapid", "QUALITY_LOW")


@pytest.mark.parametrize("exc", [RuntimeError("PESEL 44051401359"), FileNotFoundError("brak modelu")])
def test_technical_failure_uses_tesseract_once_without_content_in_logs(chain, caplog, exc):
    chain.use(FakeEngine(exc=exc))
    with caplog.at_level(logging.INFO):
        r = ocr_engine.extract_text_from_image(png()[0], "tajne_nazwisko.png")
    assert r is chain.tess and r.reason == "PP_FAILURE" and chain.tess_calls == [1]
    assert "44051401359" not in caplog.text and "tajne_nazwisko" not in caplog.text


def test_timeout_disables_pp_and_next_requests_return_quickly(chain, monkeypatch):
    monkeypatch.setattr(ocr_rapid, "TIMEOUT_S", 0.2)
    eng = chain.use(FakeEngine(GOOD, delay=1.5))
    assert ocr_engine.extract_text_from_image(png()[0], "x.png").reason == "PP_TIMEOUT"
    for _ in range(3):
        t0 = time.perf_counter()
        r = ocr_engine.extract_text_from_image(png()[0], "x.png")
        assert r is chain.tess and r.reason == "PP_TIMEOUT" and time.perf_counter() - t0 < 0.5
    assert eng.calls == 1   # nic nie dołożone do zawieszonego wykonawcy
    time.sleep(1.4)   # wątek atrapy kończy pracę przed następnym testem


def test_model_without_matching_hash_is_never_used(monkeypatch, tmp_path):
    monkeypatch.setenv("LYNX_OCR_MODEL_DIR", str(tmp_path))
    (tmp_path / photo_chain.ORI_MODEL).write_bytes(b"podmienione wagi")
    with pytest.raises(ValueError):
        ocr_rapid.verified_model(photo_chain.ORI_MODEL, photo_chain.ORI_SHA256)
    (tmp_path / photo_chain.ORI_MODEL).unlink()
    with pytest.raises(FileNotFoundError):
        ocr_rapid.verified_model(photo_chain.ORI_MODEL, photo_chain.ORI_SHA256)
    assert list(tmp_path.iterdir()) == []   # niczego nie pobrano


def test_default_dir_is_next_to_engine_not_home(monkeypatch):
    monkeypatch.delenv("LYNX_OCR_MODEL_DIR", raising=False)
    assert ocr_rapid.model_dir() == BACKEND / "models" / "ocr"


def test_default_is_tesseract_and_chain_not_imported():
    code = ("import sys; sys.path.insert(0, '.'); import ocr_engine; "
            "print(*(m in sys.modules for m in ('photo_chain', 'ocr_rapid', 'rapidocr', 'onnxruntime')))")
    env = {k: v for k, v in os.environ.items() if k != "LYNX_OCR_ENGINE"}
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, env=env)
    assert out.stdout.split() == ["False"] * 4


_HAVE_MODELS = all((BACKEND / "models" / "ocr" / f).is_file()
                   for f in (*ocr_rapid.MODEL_FILES.values(), photo_chain.ORI_MODEL))


@pytest.mark.skipif(not (_HAVE_MODELS and (SYNTH / "ground_truth.json").is_file()), reason="brak modeli lub syntetyków lokalnie")
def test_real_models_offline_class_map_and_reading(monkeypatch):
    monkeypatch.delenv("LYNX_OCR_MODEL_DIR", raising=False)
    monkeypatch.setattr(ocr_rapid, "_unavailable", None)
    real_connect = socket.socket.connect

    def guard(sock, addr):
        if isinstance(addr, tuple) and addr[0] not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError("połączenie wychodzące")
        return real_connect(sock, addr)
    monkeypatch.setattr(socket.socket, "connect", guard)
    img = cv2.imdecode(np.fromfile(str(sorted((SYNTH / "images").glob("*.png"))[0]), np.uint8), cv2.IMREAD_COLOR)
    for angle, rot in ((0, None), (90, cv2.ROTATE_90_CLOCKWISE), (180, cv2.ROTATE_180), (270, cv2.ROTATE_90_COUNTERCLOCKWISE)):
        assert photo_chain.classify(img if rot is None else cv2.rotate(img, rot))[0] == angle
    r = photo_chain.read_photo(cv2.imencode(".png", cv2.rotate(img, cv2.ROTATE_180))[1].tobytes(), ocr_engine.OCRResult)
    assert r.engine == "rapid" and r.reason in ("ok", "QUALITY_LOW")


def test_engine_process_opts_out_of_windows_background_throttling(monkeypatch):
    assert startup_check.keep_full_speed() is (sys.platform == "win32")
    monkeypatch.setattr(sys, "platform", "linux")
    assert startup_check.keep_full_speed() is False
