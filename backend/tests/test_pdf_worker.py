"""[LYNX-PDF-CRASH] PyMuPDF poza procesem silnika: po odczycie PDF Morfeusz (Guard R1, krok 2 OSOBA) działa bez
„access violation”. Awarię sprawdzamy w osobnym procesie (wywrotka procesu = kod wyjścia ≠ 0, nie wyjątek)."""
import os
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHILD = r'''
import os, sys, tempfile
os.environ["PROFILE_DIR"] = tempfile.mkdtemp(prefix="pdfw_")
sys.path.insert(0, ".")
from pdf_worker import export_pdf
from document_processor import _extract_text
pdf = export_pdf("Umowa z dnia 21.10.2026. Wykonawca: Jan Kowalski. Kawa zlecił wysłanie paczki do Przychodni.", "test")
text, err, _ = _extract_text(pdf, "test.pdf")
assert err is None and "Kowalski" in text, (err, text[:80])
assert "fitz" not in sys.modules and "pymupdf" not in sys.modules, "PyMuPDF w procesie silnika"
from guard_residue import collect_warnings
from osoba_not_person import single_osoba_evidence
ws = collect_warnings(text)
single_osoba_evidence(text, text.index("Kawa"), text.index("Kawa") + 4)
print("OK", len(ws))
'''


def test_pdf_i_morfeusz_bez_awarii_procesu():
    pytest.importorskip("fitz")
    r = subprocess.run([sys.executable, "-c", CHILD], cwd=BACKEND, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "OK" in r.stdout, (r.returncode, r.stdout[-300:], r.stderr[-600:])


def test_blad_odczytu_pdf_bez_tresci_i_bez_awarii():
    import document_processor
    text, err, _ = document_processor._extract_text(b"%PDF-1.4 to nie jest poprawny plik", "zly.pdf")
    assert text == "" and err and err.startswith("Błąd odczytu PDF"), (text, err)
