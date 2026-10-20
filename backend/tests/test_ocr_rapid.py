# LYNX-OCR-PARITY krok 2, faza A — adapter PP-OCRv6 (ocr_rapid) i wybór dostawcy w ocr_engine.
# Stuby wyłącznie interfejsu RapidOCR (wynik z polami boxes/txts) — to nie jest dowód jakości OCR.
# Uruchamiać jawnie: py -3 -m pytest tests/test_ocr_rapid.py -q (plik spoza pytest.ini python_files).
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import ocr_engine  # noqa: E402
import ocr_rapid  # noqa: E402


def box(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


class FakeEngine:
    def __init__(self, boxes=None, txts=None, exc=None, delay=0.0):
        self.res = SimpleNamespace(boxes=boxes, txts=txts)
        self.exc, self.delay = exc, delay

    def __call__(self, image):
        if self.delay:
            time.sleep(self.delay)
        if self.exc:
            raise self.exc
        return self.res


@pytest.fixture
def rapid(monkeypatch):
    monkeypatch.setenv("LYNX_OCR_ENGINE", "rapid")
    monkeypatch.setattr(ocr_engine, "_tesseract_available", lambda: True)
    tess = ocr_engine.OCRResult(text="T", confidence=90.0, quality="ok", warning_msg="", engine="tesseract", word_count=1)
    monkeypatch.setattr(ocr_engine, "_run_tesseract", lambda b, f: tess)

    def use(engine):
        monkeypatch.setattr(ocr_rapid, "_engine", engine)
    return use, tess


def test_c1_exact_contract(rapid):
    use, _ = rapid
    use(FakeEngine([box(10, 10, 200, 30), box(10, 50, 120, 70)], ["Jan Kowalski", "jan@poczta.pl"]))
    r = ocr_engine.extract_text_from_image(b"img", "x.png")
    assert (r.quality, r.confidence, r.engine, r.warning_msg) == ("reject", 0.0, "rapid", ocr_rapid.C1_WARNING)
    assert r.word_count == 3 and r.text == "Jan Kowalski\njan@poczta.pl"   # tekst tylko w procesie


def test_empty_recognition_is_still_c1_reject(rapid):
    use, _ = rapid
    use(FakeEngine(None, None))
    r = ocr_engine.extract_text_from_image(b"img", "x.png")
    assert (r.quality, r.engine, r.word_count, r.text) == ("reject", "rapid", 0, "")


@pytest.mark.parametrize("engine", [FakeEngine(exc=RuntimeError("PESEL 44051401359")), FakeEngine(delay=1.0)])
def test_technical_failure_falls_back_to_tesseract_without_content_in_logs(rapid, monkeypatch, caplog, engine):
    use, tess = rapid
    use(engine)
    monkeypatch.setattr(ocr_rapid, "TIMEOUT_S", 0.2)
    with caplog.at_level(logging.ERROR):
        assert ocr_engine.extract_text_from_image(b"img", "x.png") is tess
    assert "44051401359" not in caplog.text and "[OCR-RAPID]" in caplog.text


def test_missing_model_falls_back_without_import_or_download(rapid, monkeypatch, tmp_path):
    use, tess = rapid
    use(None)
    monkeypatch.setenv("LYNX_OCR_MODEL_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        ocr_rapid._get_engine()
    assert ocr_engine.extract_text_from_image(b"img", "x.png") is tess
    assert list(tmp_path.iterdir()) == []


def test_default_is_tesseract_and_rapid_not_imported():
    code = ("import sys; sys.path.insert(0, '.'); import ocr_engine; "
            "print('ocr_rapid' in sys.modules, 'rapidocr' in sys.modules)")
    env = {k: v for k, v in os.environ.items() if k != "LYNX_OCR_ENGINE"}
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, env=env)
    assert out.stdout.split() == ["False", "False"]


def test_default_engine_ignores_rapid_adapter(monkeypatch, rapid):
    use, tess = rapid
    use(FakeEngine([box(0, 0, 10, 10)], ["X"]))
    monkeypatch.delenv("LYNX_OCR_ENGINE")
    assert ocr_engine.extract_text_from_image(b"img", "x.png") is tess


def test_build_text_rows_columns_and_polish_letters():
    boxes = [box(400, 12, 600, 32), box(10, 10, 150, 30), box(160, 11, 300, 31),   # wiersz 1, nieposortowany
             box(10, 50, 200, 70), box(10, 90, 180, 110), box(500, 92, 700, 112)]   # wiersz 2; wiersz 3 = 2 kolumny
    txts = ["NIP: 5260001246", "Łukasz", "Wójcik-Żak", "ul. Źródlana 5", "PESEL 44051401359", "IBAN PL61109010140000071219812874"]
    assert ocr_rapid.build_text(boxes, txts) == (
        "Łukasz Wójcik-Żak    NIP: 5260001246\n"
        "ul. Źródlana 5\n"
        "PESEL 44051401359    IBAN PL61109010140000071219812874")


def test_build_text_keeps_one_value_together():
    # dwa fragmenty jednego numeru z małą przerwą → jedna spacja, nie separator kolumn
    assert ocr_rapid.build_text([box(10, 10, 100, 30), box(108, 10, 200, 30)], ["+48 605", "858 864"]) == "+48 605 858 864"
