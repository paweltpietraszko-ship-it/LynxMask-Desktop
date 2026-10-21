# LYNX-DEPS-UPDATE — DELIVERY etap A (CC, 2026-10-21)

Zakres `d6a416084da4f0399320b2b58d63be6ee7e7322a` (BEFORE), HEAD `0219ffd01bf3823a2ca7b57154541d8907608c6c`. Wykonanie i pomiary:
pomocnik CC (Sonnet) wg zlecenia; ocena wyniku i decyzje — CC.

## Gate (dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 0219ffd01bf3823a2ca7b57154541d8907608c6c
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 52/8 = 6.5:1 (threshold 5:1)
```
Proporcja wynika z nowego pliku listy zależności (41 l., nie ma czego usuwać); +52/−8 łącznie.

## Zmiany
- `backend/requirements.txt` (nowy): wszystkie importy produkcyjne backendu (analiza `ast` backend/*.py + layers), wersje `==`.
  Podniesione (bezpieczeństwo): Pillow 12.2.0→13.0.0, cryptography 46.0.7→50.0.2, fastapi 0.135.3→0.156.4, starlette 1.0.0→1.9.0,
  python-multipart 0.0.26→0.0.32, urllib3 2.6.3→2.8.0 (sekcja dev, przez requests). Reszta = wersje dotychczasowe (morfeusz2 1.99.12,
  słownik sgjp-2025.11.10 bez zmian; spacy 3.8.13 + pl_core_news_lg 3.8.0 z URL wheel; onnxruntime 1.25.0; rapidocr 3.10.0 …);
  dopisany brakujący dotąd `pyahocorasick` (import leniwy w `anonymizer.py`). Sekcja dev: pytest, requests.
- `.venv/` w katalogu głównym (w `.gitignore`); `LynxMask.vbs` uruchamia silnik `.venv\Scripts\python.exe`, gdy istnieje, inaczej `py -3`.
- `frontend/src-tauri/Cargo.lock`: anyhow 1.0.102→1.0.104, rustls 0.23.41→0.23.46, rustls-webpki 0.103.13→0.103.16; `cargo check` OK.

## Odbiór (ten sam kod; globalny `py -3` = stary zestaw vs `.venv` = nowy)
- Instalacja `.venv`: 87 s, 1,2 GB, `pip check` OK.
- pytest `tests/`: zestawy FAILED identyczne (30 — testy HTTP do działającego silnika 8765 bez tokenu w katalogu roboczym; bez
  serwera stary zestaw: 129 passed / 40 skipped / 0 failed). `test_photo_chain.py` + `test_ocr_rapid.py`: 32/32 w obu.
- `crypto_selftest`: 22/22 w obu. **Szyfrogramy mapy (.enc) zgodne w obu kierunkach** (stary→nowy, nowy→stary; MAC OK; polskie znaki).
- `/preview` w procesie (TestClient, izolowany profil): 10 obrazów benchmarku + 20 tekstów `dataset_clean` — `anonymized_preview`
  **identyczne bajt w bajt 30/30**, kody HTTP, liczby tokenów, `engine=rapid` takie same; 1 obraz odrzucony w obu; 3 obrazy JPEG
  (dekoder Pillow 13) identyczne. Wartości gold jawne: 0/66 w obu. Czas mediana 1,32 s vs 1,38 s.
- Poprawki kodu pod nowe wersje: **brak potrzebnych**.
- NOT_CHECKED: `benchmark.py` (wymaga portu 8765 = silnik właściciela) — zastąpione porównaniem 30 dokumentów bajt w bajt;
  pełny build release Tauri (tylko `cargo check`) — zostanie zbudowany przy merge.

## Uwagi
- Zależności tranzytywne nie są przypięte (tylko bezpośrednie + starlette/pydantic/urllib3) — pełny lock (freeze) proponuję w
  `LYNX-INSTALLER` (powtarzalny instalator offline). Instalacja dziś wymaga PyPI i GitHuba (wheel modelu spaCy).
- Testy HTTP pomocnika wysłały syntetyczne teksty do silnika deweloperskiego OWNERA (8765) — możliwe wpisy w jego rejestrze PSE
  (dane testowe, dev). Odnotowane.
- Etap B (słownik Morfeusza) — następny w tym Tasku.
