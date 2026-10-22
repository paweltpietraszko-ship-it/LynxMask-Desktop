# LYNX-PDF-CRASH — silnik pada po pierwszym PDF (PyMuPDF + Morfeusz w jednym procesie)

22.10.2026, CC. Poprawka krytyczna bez Architekta. Wykryte w przeglądzie zbiorów (`%TEMP%\lynx_cc_review\status_2210\raport.md`). Brief i kod
w jednej dostawie (awaria całego procesu silnika); Codex: precheck briefu + audyt kodu razem.

## Problem (odtworzony na kopii main `70fa6be`, syntetyczny PDF `backend/dataset_layout/filled/zawiadomienie_syn.pdf`)
- `document_processor._extract_text` importuje PyMuPDF (`fitz`) w procesie silnika.
- Potem `morfeusz2.analyse()` (Guard R1 `guard_residue._morf_interps`, krok 2 OSOBA) kończy się **Windows fatal exception: access violation**. Pada cały proces.
- Ślad stosu: `morfeusz2.py:179 analyse` → `pymupdf/mupdf.py:99 __next__`.
- Przyczyna:
  - oba moduły SWIG dzielą rejestr typów; iterator wyników Morfeusza zostaje owinięty klasą `SwigPyIterator` z PyMuPDF;
  - rozgrzanie Morfeusza przed PDF nie pomaga (sprawdzone);
  - eksport `/export-pdf` (`export_pdf.generate_pdf`) też ładuje PyMuPDF do procesu.
- Skala w przeglądzie: 12/12 PDF `dataset_layout`, 12/18 PDF BIP. Od scalenia Guarda (R1 woła Morfeusza przy każdym dokumencie) pierwszy wgrany PDF kładzie silnik.

## Zmiana
- Nowy `backend/pdf_worker.py`: odczyt (`extract_text`) i eksport (`export_pdf`) PDF w **osobnym krótkotrwałym procesie** (`sys.executable pdf_worker.py extract|export`).
  - Treść tylko przez stdin/stdout (bez plików — S5).
  - stderr: tylko typ błędu.
  - Timeout 120 s.
  - `_pdf_page_text` (pola kratkowe PESEL/NIP, LYNX-ZUS-BOXED-IDS) przeniesione bez zmian.
  - Moduł importowany przez silnik nie importuje PyMuPDF.
- `document_processor._extract_text`: gałąź PDF woła `pdf_worker.extract_text`; błąd → „Błąd odczytu PDF: …” jak dotąd. Import `_PDF_COMB`, `_pdf_page_text` z `pdf_worker` (zgodność).
- `pseudominizer_api.py`: jedna linia — `from pdf_worker import export_pdf as _generate_pdf` (plik nie rośnie).

TASK_SCOPE:
- backend/pdf_worker.py
- backend/document_processor.py
- backend/pseudominizer_api.py
- backend/tests/test_pdf_worker.py
- tasks/LYNX-PDF-CRASH/brief.md
- tasks/LYNX-PDF-CRASH/repo_before.hash
- tasks/LYNX-PDF-CRASH/round_01/implementation/DELIVERY.md

## Odbiór
- `tests/test_pdf_worker.py` (proces potomny):
  - eksport → odczyt przez silnik;
  - `fitz`/`pymupdf` nieobecne w `sys.modules`;
  - Guard `collect_warnings` + `single_osoba_evidence` (Morfeusz) bez awarii, kod wyjścia 0;
  - niepoprawny PDF → „Błąd odczytu PDF”, bez treści.
- Reproduktor `pdf_crash.py` (CC, lokalnie): wszystkie 13 PDF `dataset_layout/filled` × 2 powtórzenia bez awarii (na main: access violation przy pierwszym).
