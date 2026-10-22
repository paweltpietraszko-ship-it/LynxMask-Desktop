# DELIVERY — LYNX-PDF-CRASH, CC 22.10.2026

Gałąź `task/LYNX-PDF-CRASH`, baza main `70fa6be`, kod `133cefd`. Brief: `tasks/LYNX-PDF-CRASH/brief.md`.

## gate.py (`round_01/gate_r1.txt`)
```
STATUS: WYMAGA_DECYZJI
WYMAGA_DECYZJI:
  - TOTAL_LINES: 156 lines changed (threshold 150)
```
Około 40 linii to `_pdf_page_text` przeniesione bez zmian (liczone jako usunięte i dodane). Zgoda OWNERA na +6 ponad próg — w BOARD.

## Dowody
- **Reproduktor** `round_01/tests/repro_pdf_crash.py` (pipeline w procesie po `_extract_text`):
  - main `70fa6be`: `Windows fatal exception: access violation` (`morfeusz2.py:179 analyse` → `pymupdf/mupdf.py:99 __next__`) przy pierwszym PDF;
  - dostawa: 13/13 PDF `dataset_layout/filled` × 2 przebiegi → „KONIEC BEZ AWARII”.
- **Próba „rozgrzania” Morfeusza przed PDF** (wywołanie przed importem PyMuPDF): nadal awaria. Stąd osobny proces, a nie kolejność importów.
- **`tests/test_pdf_worker.py`: 2 passed.**
  - Proces potomny: eksport → odczyt przez silnik; brak `fitz`/`pymupdf` w `sys.modules`; Guard + krok 2 OSOBA z Morfeuszem bez awarii.
  - Zły PDF → „Błąd odczytu PDF”.
- **Bez zmian:** `test_disk_pii` 6, `test_photo_chain` 25 (+1 skip), `test_failclosed` 23, `test_express_one_engine` 6, `test_smoke_e2e` 9 skip (wymaga 8765).
- **`test_engine_quality_layout.py`: 7 failed / 8 passed — tak samo na main.**
  - Przyczyna: w `.venv` brak bibliotek testowych `pypdf` (5) i `reportlab` (2) — `ModuleNotFoundError`, nie produkt.
  - Test pól kratkowych (przeniesione `_pdf_page_text`) nie uruchamia się bez `reportlab`. Funkcja przeniesiona bez zmian treści.
- Ruff: `pdf_worker.py` i test czysto; `document_processor.py` 2 → 2 (F401, E731 — były na main).

## Uwagi
- Koszt: jeden proces Pythona na PDF (import PyMuPDF), rzędu sekundy; brak wpływu na TXT/DOCX/obrazy.
- Do backlogu: `pypdf` i `reportlab` jako zależności testowe (np. `requirements-dev.txt`), żeby `test_engine_quality_layout` dało się uruchomić.
