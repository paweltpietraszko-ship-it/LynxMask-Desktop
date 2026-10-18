# LYNX-FAILCLOSED-S3 — DELIVERY r1 (CC)

Gałąź `task/LYNX-FAILCLOSED-S3`: brief architekta `f3528d1` (PASS PREIMPLEMENTATION `84d8cc0`), zsynchronizowana z main (`d32bc27`). Kod: `5d989b8`.

## Decyzje Pawła (dosłownie)
- **OWNER_ACCEPTED przed kodem** (po szacunku CC: ~250–270 linii, ~200 test; niewielki wzrost `pseudominizer_api.py`, `Pseudonimizuj.tsx`, `ExpressModeScreen.tsx`): „Jedno zadanie, akceptuję rozmiar”. Rzeczywisty rozmiar 313 linii (145 test) — powyżej szacunku, do potwierdzenia (niżej).
- **Konflikt briefu z UI, rozstrzygnięty przez Pawła** (punkt 4 briefu: powód dla UI bez pełnego PII; przycisk „to nie PII” w `Pseudonimizuj.tsx` wyciągał wartość z treści powodu `'…'`): „Chyba 1, ale uściślę: ma się pojawiać ostrzeżenie, a naciśnięcie przycisku przenosi słowo do białej listy”. Realizacja: powody i logi bez wartości (S5); wartości naruszeń w osobnym polu `guard_values` odpowiedzi `/preview`, pokazywane lokalnie w ostrzeżeniu i używane przez przycisk allowlisty. Podgląd zablokowanego wyniku pozostaje bez tych wartości, kopiowanie wyłączone.

## Zmiany
**(A) awaria → odmowa bez danych (F1, F1b, F2)**
- `pipeline_new.run_pipeline_express`: wyjątek → `(text, {}, True)` (było `False`); logi obu pipeline tylko `type(e).__name__`.
- `pipeline.py`: `S3_FAILURE` (jeden komunikat) i `_s3_failure(reason)` → `PipelineResult(text="", guard_blocked=True, error=…)`; użyte w `pseudonymize_document` (wyjątek), `_apply_guard` (force_block z NER/warstwy oraz wyjątek Guarda). Logi bez treści wyjątku.
- `pseudominizer_api.py`: `/preview` — `result.error` → HTTP 500 `S3_FAILURE` bez `anonymized_preview`/`tokens`/`original_text`; `/preview-express` — `force_block` → HTTP 500 jw. (wcześniej ignorowany). Nieoczekiwany wyjątek na poziomie endpointu: domyślna odpowiedź 500 FastAPI bez danych.
- `spacy_ner.detect_entities`, `ner_layer.process_ner`: wyjątek modelu/algorytmu nie zamienia się w „zero encji” — `RuntimeError` z samą nazwą typu wyjątku (S5), adapter ustawia `state.ner_error` → force_block. Poprawne zero encji bez zmian.
**(B) Guard (F3, F4, S5)**
- `output_guard.guard_output`: powody HIGH/MEDIUM bez wartości (`«…»` usunięte) — także w logach.
- `guard_output_with_map`: naruszenia jako (rodzaj, wartość); wartość z `check_blacklist_context` czytana dokładnym wzorcem formatu generowanego przez nasz kod (`[RODZAJ] Plain text '…'`), format nierozpoznany → wartość nieznana (bez zgadywania); allowlista = równość z całą wartością (casefold, strip), `GUARD_ERROR` i wartości nieznane nigdy wyciszane; powody/logi `MAP_LEAK: [RODZAJ] encja z mapy obecna w tekście`; `redacted_text`/`safe_text` = tekst z zamazaniami HIGH z `guard_output` + wartości naruszeń zamienione na `[REDACTED]`, a przy wartości nieznanej — pusty (bez treści); `GuardResult.values` → `PipelineResult.guard_values` → `guard_values` w API.
**(C) token po OCR (F5)**: `/preview` i `/preview-express` odrzucają (422, jak dotąd) także tekst, w którym token powstaje dopiero po `normalize_ocr` („OSOBA_0O1”, „FIRMA_1l2”) — przed pipeline, alokatorem i trie; reguły OCR i `TOKEN_RE` bez zmian.
**(D) UI**: `Pseudonimizuj.tsx` — „Kopiuj tekst” wyłączone przy blokadzie Guarda; ostrzeżenie pokazuje powody (bez wartości) i wykryte wartości z `guard_values`; przycisk allowlisty używa `guard_values` (zamiast wycinać `'…'` z powodu). Plik 920 → 913 linii. `ExpressModeScreen.tsx` bez zmian: Express nie ma Guarda, a 500 trafia do istniejącej ścieżki błędu (brak wyniku).

## Testy
`backend/tests/test_failclosed.py` (nowy, 145 linii, jawnie; TestClient API z prawdziwym silnikiem): **main 15 failed / 4 passed** (strażnicy: zero encji = normalny wynik, dokładna allowlista, zwykła korekta OCR ×2) → **gałąź 19 passed**. Zakres: wyjątek warstwy Express/Full i `_run_pipeline` → 500 bez PESEL/nazwiska w całym JSON; ValueError i MemoryError w SpaCy → 500; MAP_LEAK — podgląd, powody i log bez wartości (+ `guard_values`); allowlista „Jan”/słowa szablonu nie wyciszają, cała wartość wycisza; `GUARD_ERROR` nie do wyciszenia; „OSOBA_0O1”/„FIRMA_1l2” → 422 w obu trybach; zwykła korekta OCR cyfr → 200.
Trzy istniejące reproduktory audytu w `test_audyt_2026_10.py`: **XPASS(strict)** — BUG-EXPRESS-FAIL-OPEN, BUG-GUARD-MAPLEAK-UNREDACTED, BUG-ALLOWLIST-SUBSTRING (plik poza TASK_SCOPE — markerów nie zmieniano; pytest raportuje je jako „failed” z powodu strict, 131 passed, 7 xfailed). Do zdjęcia markerów w osobnym kroku.
Regresje: `test_output_guard_adversarial` + `test_layers` + `test_ner_multiline` + `test_text_limit_15k` + `test_map_fidelity` + nowy: 231 passed; `tests/` z działającym backendem z gałęzi: 167 passed, 2 skipped, 1 xfailed. TypeScript `tsc --noEmit`: 0 błędów. `ruff`: liczba uwag w każdym zmienionym pliku jak na main.

## Pomiar: 178 dokumentów przez działający `/preview` (profil Pawła; baza main `71bc525` vs gałąź)
- kody HTTP 200 ×178 obie strony; blokady 59 → 59 (0 zmian); **119 niezablokowanych: wynik identyczny znak w znak**;
- zablokowane (59): podgląd z jawną wartością z mapy — baza 59, gałąź 2 (obie: wartość-śmieć „M., ” — inicjał z przecinkiem jako OSOBA, nie PII); powody z wartością („'”, „«”) — 0/59; `guard_values` wypełnione — 59/59; podgląd zawierający wartość z `guard_values` — 0/59;
- log backendu z całego przebiegu (657 linii): 0 wystąpień „Plain text” / „«”.

## Gate (dosłownie)
```
STATUS: FAIL
HEAD_SHA: 5d989b81db45a18459c6aadc1725249d8bc721a2
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
REASON:
  - SIZE_FILE: backend/pseudominizer_api.py has 1135 lines (max 600, before 1129)
  - SIZE_FUNC: backend/pseudominizer_api.py:preview has 115 lines (max 50, before 112)
  - SIZE_FUNC: backend/pseudominizer_api.py:preview_express has 81 lines (max 50, before 79)
WYMAGA_DECYZJI:
  - TOTAL_LINES: 313 lines changed (threshold 150)
```
Wzrost API +6 (import `normalize_ocr`, dwa warunki S3 po 2 linie, pole `guard_values`) — w zakresie zaakceptowanym przed kodem („niewielki wzrost API”); 313 linii vs szacunek 250–270 — różnica z przebudowy zbierania naruszeń w Guardzie (+40/−33) i `guard_values` po decyzji Pawła. Do potwierdzenia przez Pawła.

## Ograniczenia / findingi
- `pipeline.py` ma w komentarzach i części komunikatów podwójnie zakodowane polskie znaki (np. „bĹ‚Ä…d”) — także dawny komunikat błędu widoczny w UI; nowe komunikaty poprawne, reszty pliku nie ruszano (finding).
- Przycisk „to nie PII” po dodaniu wartości zapisuje wynik z pominięciem Guarda (`handleSave(true)`) — zachowanie istniejące, bez zmian.
- Wartości-śmieci z NER (np. „M., ”) jako OSOBA — K1/C2.
- Markery xfail trzech reproduktorów audytu do zdjęcia (XPASS) — poza TASK_SCOPE.

---

# DELIVERY r2 (CC) — poprawka FAIL r3 Codexa (`93d15a4`)

Kod: `b0b5ff9` (na `93d15a4`). Diff względem dostawy r1 (`8194c0d`): `pseudominizer_api.py` +12, `tests/test_failclosed.py` +53; nic więcej w produkcie.

## Zmiana
`pseudominizer_api.py`: nowy zewnętrzny middleware `_s3_error_boundary` wokół `call_next`. Nieobsłużony wyjątek z dowolnego endpointu (np. `_extract_text` przed pipeline) → `JSONResponse(S3_FAILURE, 500)` dla `/preview` i `/preview-express`, a dla innych ścieżek `{"error": "Wewnętrzny błąd serwera."}` 500. Log: `logger.error(...)` z samą ścieżką i `type(e).__name__`, bez `str(e)` i bez tracebacku (S5). Wyjątek nie wraca do Starlette/uvicorn, więc `uvicorn.error` nie dostaje tracebacku. `@app.exception_handler(Exception)` odrzucony, bo Starlette po obsłudze i tak re-raisuje wyjątek do serwera, który loguje treść. Wyjątki spoza `Exception` (np. `KeyboardInterrupt`) przechodzą bez zmian.

## Testy
- `test_wyjatek_endpointu_json_s3_bez_tresci_w_logu[/preview, /preview-express]`: prawdziwy `uvicorn.Server` na porcie tymczasowym (jak reproduktor Codexa), `_extract_text` rzuca `ValueError` ze znacznikiem syntetycznym z PESEL. Handler logów jest na `root`, `uvicorn`, `uvicorn.error` i `pseudominizer`. Asercje: HTTP 500 i `json == S3_FAILURE`; w logu jest nazwa typu `ValueError`; w logu nie ma znacznika ani PESEL.
- RED→GREEN: na API z r1 (`8194c0d`) **2 failed**, na `b0b5ff9` cały plik **21 passed**.
- Reproduktor Codexa `tests_r3_server_repro.py` uruchomiony na kopii bez asercji SHA. Pada na swoim oczekiwaniu błędu, bo dostaje `(500, '{"error":"Nie udało się bezpiecznie zamaskować dokumentu…","blocked'…)` zamiast `Internal Server Error`.
- Regresje: `test_output_guard_adversarial` + `test_layers` + `test_ner_multiline` + `test_text_limit_15k` + `test_map_fidelity` + `test_failclosed` dały **233 passed**. `test_audyt_2026_10.py`: 131 passed, 7 xfailed, 3 „failed” = te same XPASS(strict) co w r1 (marker poza TASK_SCOPE).
- `tests/` (standardowa suita): 137 passed, 2 skipped, 1 xfailed, **30 failed**. Wszystkie 30 to testy live-HTTP na porcie 8765. Na tym porcie działa backend Pawła z main, a w worktree jest stary `api_token.txt`, więc każde wywołanie dostaje 401, co potwierdza curl. Te testy nie sprawdzały gałęzi i nie mogły tego zrobić, a backendu Pawła nie restartowano. Uruchomienie ich na backendzie z gałęzi: **NOT_RUN** w r2 (w r1 było 167 passed). Do odtworzenia: `cd backend && py -3 pseudominizer_api.py` z gałęzi, potem `py -3 -m pytest tests/ -q`.
- `ruff`: 0 uwag w obu plikach (baza API również 0).
- Pomiar 178 dokumentów: niepowtarzany. Zmiana działa wyłącznie przy wyjątku, który w r1 nie wystąpił na żadnym z 178 dokumentów (wszystkie odpowiedzi 200).

## Gate (dosłownie)
```
STATUS: FAIL
HEAD_SHA: b0b5ff9a2eabe754d21b6a41424769f3d1fac0c6
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
REASON:
  - SIZE_FILE: backend/pseudominizer_api.py has 1147 lines (max 600, before 1129)
  - SIZE_FUNC: backend/pseudominizer_api.py:preview has 115 lines (max 50, before 112)
  - SIZE_FUNC: backend/pseudominizer_api.py:preview_express has 81 lines (max 50, before 79)
WYMAGA_DECYZJI:
  - TOTAL_LINES: 380 lines changed (threshold 150)
```
Nowy wzrost względem zaakceptowanego r1 to API +12 (łącznie +18 względem bazy) i test +53. Powód: wymaganie FAIL r3 (granica błędu endpointu), nie nowy zakres. Funkcje `preview` i `preview_express` są bez zmian względem r1. Zgłaszam Pawłowi i nie zakładam zgody.
