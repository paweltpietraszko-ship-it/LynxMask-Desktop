# Adapter PP-OCRv6 (ocr_rapid): modele lokalne z SHA, odczyt i kolejność tekstu. [LYNX-PHOTO-CHAIN] wartownik C1 fazy A usunięty —
# decyzję o odczycie podejmuje photo_chain (tests/test_photo_chain.py).
# Stuby wyłącznie interfejsu RapidOCR (wynik z polami boxes/txts) — to nie jest dowód jakości OCR.
# Uruchamiać jawnie: py -3 -m pytest tests/test_ocr_rapid.py -q (plik spoza pytest.ini python_files).
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

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


def test_missing_model_fails_without_import_or_download(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_rapid, "_engine", None)
    monkeypatch.setenv("LYNX_OCR_MODEL_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        ocr_rapid._get_engine()
    assert list(tmp_path.iterdir()) == []


def test_recognize_reads_bytes(monkeypatch):
    eng = FakeEngine([box(10, 10, 200, 30), box(10, 50, 120, 70)], ["Jan Kowalski", "jan@poczta.pl"])
    monkeypatch.setattr(ocr_rapid, "_engine", eng)
    monkeypatch.setattr(ocr_rapid, "_unavailable", None)
    assert ocr_rapid.recognize(b"img", 5) == "Jan Kowalski\njan@poczta.pl"


def test_default_is_tesseract_and_rapid_not_imported():
    code = ("import sys; sys.path.insert(0, '.'); import ocr_engine; "
            "print('ocr_rapid' in sys.modules, 'rapidocr' in sys.modules)")
    env = {k: v for k, v in os.environ.items() if k != "LYNX_OCR_ENGINE"}
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, env=env)
    assert out.stdout.split() == ["False", "False"]


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


def test_threads_leave_cpu_for_the_user():
    assert 2 <= ocr_rapid.THREADS <= 6 or os.environ.get("LYNX_OCR_THREADS")
