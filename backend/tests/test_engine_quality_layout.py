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
    assert by["docx/tabela"] == {"masked": 1}, by  # LYNX-DOCX-TABLES: komórka czytana i maskowana (wcześniej EXTRACTION_MISSING)
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


def _docx_with_unread(path, para, unread):
    """Akapit (czytany) + nagłówek strony (nieczytany przez _extract_text — poza zakresem LYNX-DOCX-TABLES)."""
    import docx
    d = docx.Document()
    d.add_paragraph(f"Dane: {para}")
    d.sections[0].header.paragraphs[0].text = unread
    d.save(path)


# Codex r2 F1: ta sama wartość w akapicie i w nieodczytanym miejscu — żadne z pól nie może dostać „masked”.
# Po LYNX-DOCX-TABLES komórki są czytane, więc nieodczytanym miejscem jest nagłówek strony.
def test_powtorzona_wartosc_bez_dowodu_wystapienia(tmp_path, run):
    _docx_with_unread(str(tmp_path / "a.docx"), EMAIL, EMAIL)
    _manifest(tmp_path, [{"file": "a.docx", "type": "docx", "fields": [{"category": "EMAIL", "value": EMAIL}] * 2}])
    assert eq.measure_layout(str(tmp_path), run)["by_type_location"] == {"docx/tekst": {"EXTRACTION_UNVERIFIED": 2}}


# LYNX-DOCX-TABLES: ta sama wartość w akapicie i w komórce to teraz dwa rzeczywiste wystąpienia — oba maskowane.
def test_powtorzona_wartosc_akapit_i_tabela_obie_odczytane(tmp_path, run):
    import docx
    from document_processor import _extract_text
    d = docx.Document()
    d.add_paragraph(f"Adres do korespondencji: {EMAIL}")
    d.add_table(rows=1, cols=2).rows[0].cells[1].text = EMAIL
    d.save(str(tmp_path / "a.docx"))
    fields = [{"category": "EMAIL", "value": EMAIL}, {"category": "EMAIL", "value": EMAIL, "in_table": True}]
    _manifest(tmp_path, [{"file": "a.docx", "type": "docx", "fields": fields}])
    assert eq.measure_layout(str(tmp_path), run)["by_type_location"] == {"docx/tekst": {"masked": 1}, "docx/tabela": {"masked": 1}}
    text = _extract_text((tmp_path / "a.docx").read_bytes(), "a.docx")[0]
    res = run(text)
    assert text.count(EMAIL) == 2 and EMAIL not in res.text and list(res.reverse_map.values()) == [EMAIL], (res.text, res.reverse_map)


# Codex r3 F1 i rodzina: wartość nieodczytanej komórki występuje w tekście tylko jako fragment innej wartości.
@pytest.mark.parametrize("para,cell,cat", [
    ("anna.k.zalewska@example.pl", "k.zalewska@example.pl", "EMAIL"),   # sufiks dłuższego e-maila (r3)
    ("Jan Kowalski", "Kowalski", "OSOBA"),                               # nazwisko wewnątrz pełnego imienia i nazwiska
    ("526-000-12-467", "526-000-12-46", "NUMER"),                        # prefiks dłuższego numeru
])
def test_wartosc_tylko_jako_fragment_innej(tmp_path, run, para, cell, cat):
    _docx_with_unread(str(tmp_path / "a.docx"), para, cell)  # krótsza wartość tylko w nieczytanym nagłówku
    _manifest(tmp_path, [{"file": "a.docx", "type": "docx", "fields": [{"category": cat, "value": para}, {"category": cat, "value": cell}]}])
    by = eq.measure_layout(str(tmp_path), run)["by_type_location"]
    assert by["docx/tekst"].get("masked", 0) <= 1 and sum(by["docx/tekst"].values()) == 2, by  # nieodczytane pole nigdy „masked”


# LYNX-DOCX-TABLES: produkcyjny extractor — akapity i tabele w kolejności dokumentu, każda komórka raz, bez sklejania.
def test_docx_tabele_w_kolejnosci_bez_duplikatow():
    import io
    import docx
    from document_processor import _extract_text
    d = docx.Document()
    t0 = d.add_table(rows=1, cols=2)
    t0.rows[0].cells[0].text, t0.rows[0].cells[1].text = "T0A", "T0B"  # tabela przed pierwszym akapitem
    d.add_paragraph("PA")
    t = d.add_table(rows=3, cols=3)
    t.cell(0, 0).text = EMAIL
    t.cell(0, 1).merge(t.cell(0, 2)).text = "MERGEH"
    t.cell(1, 0).merge(t.cell(2, 0)).text = "MERGEV"
    c = t.cell(1, 1)
    c.text = "L1"
    c.add_paragraph("L2")  # komórka wieloakapitowa; (1,2) pusta
    t.cell(2, 2).text = "526-000-12-46"
    d.add_paragraph("PB")
    d.add_table(rows=1, cols=1).rows[0].cells[0].text = "T2"
    d.add_paragraph("PC")
    buf = io.BytesIO()
    d.save(buf)
    text, err, meta = _extract_text(buf.getvalue(), "x.docx")
    assert err is None and meta is None
    assert text.split("\n") == ["T0A", "T0B", "PA", EMAIL, "MERGEH", "MERGEV", "L1", "L2", "526-000-12-46", "PB", "T2", "PC"], text


def test_obie_wartosci_odczytane_osobno(tmp_path, run):  # kontrola: dwa osobne wystąpienia → oba zmierzone przez pipeline
    import docx
    d = docx.Document()
    d.add_paragraph(f"Dane: {EMAIL}")
    d.add_paragraph(f"Kopia: {EMAIL}")
    d.save(str(tmp_path / "a.docx"))
    _manifest(tmp_path, [{"file": "a.docx", "type": "docx", "fields": [{"category": "EMAIL", "value": EMAIL}] * 2}])
    assert eq.measure_layout(str(tmp_path), run)["by_type_location"] == {"docx/tekst": {"masked": 2}}
