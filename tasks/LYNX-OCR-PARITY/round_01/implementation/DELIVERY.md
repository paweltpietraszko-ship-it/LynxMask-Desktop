# DELIVERY — LYNX-OCR-PARITY krok 1 (CC, runda 1)

Gałąź `task/LYNX-OCR-PARITY-STEP1`, kod `7aaa83b2cef41196caae143d7e720fdfeae553a1` (baza briefu `4bb7c84`). Bez zmian produktu, bez merge.

## Gate (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 7aaa83b2cef41196caae143d7e720fdfeae553a1
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 305/6 = 50.8:1 (threshold 5:1)
  - TOTAL_LINES: 311 lines changed (threshold 150)
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r3_repro.py
EXCLUDED_ARTIFACTS: NONE
```
**Rozmiar: 311 linii zmienionych wobec zgody OWNERA na ~220** (moduł 192 l., testy 109 l., `benchmark.py` +2/−4). Przekroczenie zgłoszone OWNEROWI. SIZE_FILE/SIZE_FUNC/RUFF bez pogorszenia: `benchmark.py` 987 → 985 l.; `run_benchmark` i `main` (już >50 l.) nie urosły — wywołanie przez opakowania `analyze_and_record` / `build_report_and_write`; ruff `benchmark.py` 12 → 12.

## Co zmieniono
- `backend/benchmark_ocr_diagnostics.py` (nowy): klasyfikacja pominięć (`BUG_SILNIKA` / `OCR_ZNIEKSZTAŁCONY` / `BRAK_W_OCR` / `NOT_MEASURED` / `REVIEW`) i tokenów spoza gold (`EXTRA_MASK_OK` / `EXTRA_MASK_POLICY` / `UX_FP` / `REVIEW`), zapis `ocr_diagnostics.json` (bez wartości, fragmentów OCR, tokenów API) + jedna linia sum na stdout. `original_text` z `/preview` tylko w pamięci wywołania. Normalizacja identyczna z `benchmark._norm` (test). Fuzzy: Levenshtein jak Mobile (≥9 znaków; 1 / 2 od 15 / 3 od 24) wyłącznie na ciągach kolejnych słów **jednej linii** (bez sklejania linii i bez dopasowania w środku słowa). `REVIEW` dla wartości <9 znaków bez dokładnego dopasowania; `NOT_MEASURED` przy braku/pustym `original_text`. Statusy dokumentów jak `build_report`: rejected/error bez klasyfikacji i poza mianownikiem; guard_blocked klasyfikowany, ale osobno widoczny (`miss_in_guard_blocked_docs`). Kontrola zgodności: liczba etykiet = legacy `privacy_missed` i `false_positives`.
- `backend/benchmark.py`: import + 2 wywołania (zamiast `analyze(...)` i `build_report(...)`), changelog v1.0–v1.1 skrócony do jednej linii. Logika dopasowania, liczniki, `report.json`, `summary.txt`, `bugs.txt` bez zmian.
- `backend/tests/test_benchmark_ocr_diagnostics.py` (nowy): 21 testów.

## Testy i przebieg
```
cd backend && py -3 -m pytest tests/test_benchmark_ocr_diagnostics.py -q   → 21 passed
py -3 -m ruff check benchmark_ocr_diagnostics.py tests/test_benchmark_ocr_diagnostics.py → All checks passed!
py -3 benchmark.py --dataset dataset_20260627_095419 --no-generate  (backend: main, katalog OWNERA)
```
Stara miarka bez zmian: Privacy Recall 94,5%, Critical Leakage 0,0%, Precision 62,3% (jak 19.10).
Nowa linia: `[OCR-DIAG] pominięte BUG_SILNIKA=0 OCR_ZNIEKSZTAŁCONY=13 BRAK_W_OCR=3 NOT_MEASURED=0 REVIEW=0 | spoza gold EXTRA_MASK_OK=33 EXTRA_MASK_POLICY=65 UX_FP=0 REVIEW=68 | dok. accepted=43 guard_blocked=0 rejected=7 error=0 | zgodność z legacy: OK`
Pominięcia wg typu: EMAIL 8 OCR_ZNIEKSZT.; TELEFON 2 OCR_ZNIEKSZT.; ADRES 1+1; NUMER 1 OCR_ZNIEKSZT. + 2 BRAK (numery KW); SYGNATURA 1 OCR_ZNIEKSZT.

## Rozjazd z ręczną diagnozą 19.10 (0/10/6 → 0/13/3), bez strojenia progów
Ręczny skrypt CC brał kandydatów fuzzy z okien regex ≤4 słów; moduł bierze dowolny ciąg kolejnych słów w obrębie linii. Trzy przypadki przeszły z BRAK_W_OCR do OCR_ZNIEKSZTAŁCONY: 1 e-mail (dłuższe okno), 1 adres i 1 sygnatura (wielowyrazowe). Progi odległości bez zmian.
**Obserwacja dla miarki:** 33 z 166 legacy „false_positives” to `EXTRA_MASK_OK` — tokeny będące zniekształconą przez OCR wersją wartości gold tego samego typu (zamaskowane poprawnie, a stara precyzja liczy je jako FP).

## Uwagi
- IMPORTERS_FOR_REVIEW: `audyt/bench_offline.py` importuje `benchmark` (analyze/build_report bez zmian; import nowego modułu z katalogu `backend`). Nie uruchamiano.
- Wyniki przebiegu lokalnie w worktree (`benchmark_results/`, ignorowane), nie w repo.
