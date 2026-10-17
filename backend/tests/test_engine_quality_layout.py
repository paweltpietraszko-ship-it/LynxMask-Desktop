# tests/test_engine_quality_layout.py — LYNX-PUBLIC-DATA-TESTS etap 1: wiarygodność trybu layout runnera audyt/engine_quality.py
"""Uruchamiać jawnie: cd backend && py -3 -m pytest tests/test_engine_quality_layout.py -q
Pliki tworzone w katalogu tymczasowym, dane wyłącznie syntetyczne. Produkcyjny _extract_text + produkcyjny pipeline."""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(ROOT, "backend"), os.path.join(ROOT, "audyt")]

import engine_quality as eq  # noqa: E402

EMAIL, CELL, PDF_EMAIL = "k.zalewska@example.pl", "m.nowicka@example.pl", "p.wrona@example.pl"


@pytest.fixture(scope="module")
def run():
    ok, why = eq._engine_available()
    if not ok:
        pytest.skip(f"NER/Morfeusz niedostępny: {why}")
    import pipeline
    import tempfile
    tmp = tempfile.TemporaryDirectory(prefix="lynx_layout_test_")
    st = eq.build_state(tmp.name)
    yield lambda t: pipeline.pseudonymize_document(t, st)
    st = None
    import gc
    gc.collect()
    tmp.cleanup()


def _docx(path):
    import docx
    d = docx.Document()
    d.add_paragraph(f"Adres do korespondencji: {EMAIL}")
    d.add_table(rows=1, cols=2).rows[0].cells[1].text = CELL
    d.save(path)


def _pdf(path):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path)
    c.drawString(72, 700, f"Kontakt: {PDF_EMAIL}")
    c.save()


def _manifest(tmp_path, entries):
    (tmp_path / "manifest.json").write_text(json.dumps(entries), encoding="utf-8")


def test_komorka_tabeli_to_brak_ekstrakcji_nie_maskowanie(tmp_path, run):
    _docx(str(tmp_path / "a.docx"))
    _pdf(str(tmp_path / "b.pdf"))
    _manifest(tmp_path, [
        {"file": "a.docx", "type": "docx", "fields": [{"category": "EMAIL", "value": EMAIL}, {"category": "EMAIL", "value": CELL, "in_table": True}]},
        {"file": "b.pdf", "type": "pdf", "fields": [{"category": "EMAIL", "value": PDF_EMAIL}]},
    ])
    rep = eq.measure_layout(str(tmp_path), run)
    by = rep["by_type_location"]
    assert by["docx/tabela"] == {"EXTRACTION_MISSING": 1}, by  # dzisiejszy extractor nie czyta tabel DOCX
    assert by["docx/tekst"] == {"masked": 1} and by["pdf/tekst"] == {"masked": 1}, by  # klasyfikacja po prawdziwym pipeline
    assert rep["status"] == "OK" and rep["fields_measured"] == 3 and all(d["status"] == "MEASURED" for d in rep["docs"])
    dump = json.dumps(rep, ensure_ascii=False)
    assert not any(s in dump for s in (EMAIL, CELL, PDF_EMAIL, "a.docx", "b.pdf", "korespondencji")), "raport zawiera dane/nazwy"


def test_brak_manifestu_i_pliku_to_not_run(tmp_path, run):
    assert eq.measure_layout(str(tmp_path), run)["status"] == "NOT_RUN"
    _manifest(tmp_path, [{"file": "nie_ma.docx", "type": "docx", "fields": [{"category": "EMAIL", "value": EMAIL}]}])
    rep = eq.measure_layout(str(tmp_path), run)
    assert rep["status"] == "NO_FIELDS_MEASURED" and rep["fields_not_run"] == 1 and rep["docs"][0]["status"] == "NOT_RUN", rep


def test_zmieniony_zapis_to_extraction_changed(tmp_path, run):
    _pdf(str(tmp_path / "b.pdf"))
    spaced = PDF_EMAIL.replace("@", " @ ")  # klucz w innym zapisie niż tekst z pliku
    _manifest(tmp_path, [{"file": "b.pdf", "type": "pdf", "fields": [{"category": "EMAIL", "value": spaced}]}])
    assert eq.measure_layout(str(tmp_path), run)["by_type_location"] == {"pdf/tekst": {"EXTRACTION_CHANGED": 1}}


# Codex r2 F1: ta sama wartość w akapicie i w nieodczytanej komórce — żadne z pól nie może dostać „masked”.
def test_powtorzona_wartosc_bez_dowodu_wystapienia(tmp_path, run):
    import docx
    d = docx.Document()
    d.add_paragraph(f"Adres do korespondencji: {EMAIL}")
    d.add_table(rows=1, cols=2).rows[0].cells[1].text = EMAIL
    d.save(str(tmp_path / "a.docx"))
    fields = [{"category": "EMAIL", "value": EMAIL}, {"category": "EMAIL", "value": EMAIL, "in_table": True}]
    _manifest(tmp_path, [{"file": "a.docx", "type": "docx", "fields": fields}])
    by = eq.measure_layout(str(tmp_path), run)["by_type_location"]
    assert by == {"docx/tekst": {"EXTRACTION_UNVERIFIED": 1}, "docx/tabela": {"EXTRACTION_UNVERIFIED": 1}}, by
