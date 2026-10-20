# DELIVERY — LYNX-OCR-PARITY krok 2, faza A (CC, runda 1)

Gałąź `task/LYNX-OCR-PARITY-STEP2`, kod `869a70d2d9e1b46f314439b9c4bdc0bd3007e189` (baza: precheck PASS `ec9c664`). **Domyślny OCR bez zmian (Tesseract). Faza B (kalibracja, aktywacja) NIE jest częścią tej dostawy.** Bez merge.

## Recenzja briefu (CC)
Przyjęty bez uwag merytorycznych. Szacunek ~300 l.; **zgoda OWNERA na rozmiar ~300 l. przed kodem (20.10)**. Uwaga techniczna: brief ma nagłówek `## TASK_SCOPE`, a `gate.py` szuka linii `TASK_SCOPE:` — gate uruchomiony na kopii briefu z tą jedną linią zmienioną (`sed 's/^## TASK_SCOPE$/TASK_SCOPE:/'`), lista plików identyczna. Prośba do Architekta: w kolejnych briefach format `TASK_SCOPE:`.

## Gate (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 869a70d2d9e1b46f314439b9c4bdc0bd3007e189
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 241 lines changed (threshold 150)
IMPORTERS_FOR_REVIEW:
  - backend\document_processor.py
  - tasks\LYNX-SEC-DISK-PII\round_01\tests\repro_r2.py
EXCLUDED_ARTIFACTS: NONE
```
241 l. (< 300 zaakceptowanych). `ocr_engine.py` +5 l. (478→483, `extract_text_from_image` 33→38 l.), ruff bez nowych błędów.

## Co zmieniono
- `backend/ocr_rapid.py` (nowy, 112 l.): RapidOCR 3.10 + onnxruntime CPU, PP-OCRv6 small (det/rec small + cls mobile) **wyłącznie z lokalnych plików** (`LYNX_OCR_MODEL_DIR`, domyślnie `~/lynx_models/ppocrv6_small`); brak pliku → `FileNotFoundError` przed importem `rapidocr` (żadnego pobierania). Silnik tworzony raz na proces. Limit czasu (`LYNX_OCR_RAPID_TIMEOUT`, 60 s) przez jednowątkową pulę. Składanie tekstu: wiersze wg środka pionowego, w wierszu od lewej, przerwa > 2× wysokość wiersza → 4 spacje (osobne pole/kolumna), mniejsza → jedna spacja. **C1:** wynik zawsze `quality="reject"`, `confidence=0.0`, stały komunikat, `engine="rapid"`, `word_count` = liczba słów; awaria techniczna (brak pakietu/modelu, wyjątek, limit czasu) → `None`.
- `backend/ocr_engine.py`: na początku `extract_text_from_image` — tylko przy `LYNX_OCR_ENGINE=rapid` import adaptera; `None` → dotychczasowa ścieżka Tesseracta z jego bramką. Niski wynik PP nie powoduje powrotu do Tesseracta (w fazie A każdy wynik PP to odmowa). Bez flagi `ocr_rapid`/`rapidocr` nie są importowane (test).
- `backend/tests/test_ocr_rapid.py` (nowy, 9 testów): C1 dokładnie; pusty odczyt; wyjątek i limit czasu → Tesseract, bez treści w logach; brak modeli → Tesseract, nic nie pobrane; domyślnie Tesseract i brak importu; składanie wierszy/kolumn/polskich liter; jedna wartość z małą przerwą nie rozbita.
- `README.md`: instalacja offline, zmienne, licencje (Apache-2.0, atrybucja Baidu/PaddleOCR).

## Dowody
```
cd backend && py -3 -m pytest tests/test_ocr_rapid.py tests/test_benchmark_ocr_diagnostics.py -q  → 37 passed
ruff ocr_rapid.py tests/test_ocr_rapid.py → All checks passed!
```
**/preview na żywo (backend z gałęzi, `LYNX_OCR_ENGINE=rapid`, kopia profilu):** obraz syntetyczny → HTTP 422, klucze `blocked, error, ocr, ocr_rejected`, `ocr = {quality: reject, confidence: 0.0, engine: rapid, word_count: 73}`, **bez** `original_text` i `tokens`; log zawiera tylko „odmowa OCR: conf=0.0%” (0 trafień cyfr PESEL/„@”).

**Lokalne badanie adaptera (bezpośrednie wywołanie, syntetyki, nic w repo)** — wartości gold nienaruszone po OCR (normalizacja i Levenshtein jak Mobile):

| Zbiór | Tesseract (dziś) | PP-OCRv6 small (adapter) |
|---|---|---|
| `dataset_20260627_095419` (50, znany) | 245/342 (71,6%), utracone 43, odrzuca 7/50 | 321/342 (93,9%), utracone 3 |
| `dataset_20261016_fresh` (100, **kontrolny — nic na nim nie strojono**) | 443/619 (71,6%), utracone 64, odrzuca 16/100 | 578/619 (93,4%), utracone 10 |

Poziomy degradacji (zbiór kontrolny, Tesseract → PP): lvl0 143→158/161, lvl1 111→130/141, lvl2 80→142/159, lvl3 109→148/158. Przewaga potwierdzona na danych spoza znanego zbioru (uwaga OWNERA o „nauczeniu się” stałego zbioru).

## Zasoby / wersje
rapidocr 3.10.0, onnxruntime 1.25.0 (Python 3.14 OWNERA). Modele (Apache-2.0):
- `PP-OCRv6_det_small.onnx` sha256 `090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f`
- `PP-OCRv6_rec_small.onnx` sha256 `6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884`
- `ch_ppocr_mobile_v2.0_cls_mobile.onnx` sha256 `e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c`
RAM procesu +136 MB po pierwszym odczycie; pierwsza strona 2,45 s (z ładowaniem modeli), kolejna 1,8 s; Tesseract ~1,3 s/str. na tej maszynie (PP wolniejszy o ~0,6 s/str.). Pakiet `rapidocr` instaluje modele w `site-packages/rapidocr/models/`; adapter używa jawnych ścieżek, więc nie zależy od tego katalogu.

## Ograniczenia i następny krok
- Limit czasu porzuca, ale nie przerywa wątku (Python) — kolejny dokument czeka, aż poprzednie rozpoznanie się zakończy; w fazie A bez znaczenia (każdy wynik PP to odmowa), do rozważenia w B.
- `IMPORTERS_FOR_REVIEW`: `document_processor.py` (wywołuje `extract_text_from_image` bez zmian sygnatury).
- **Faza B (osobno):** propozycja reguły jakości PP (pewności per linia z RapidOCR) — kalibracja na `dataset_20260627_095419`, sprawdzenie na `dataset_20261016_fresh`, plus `dataset_real_public` jako kontrola braku regresji (głównie PDF/TXT, OCR ich nie dotyczy), potem prawdziwe skany OWNERA okiem. Do tego czasu PP = odmowa.
