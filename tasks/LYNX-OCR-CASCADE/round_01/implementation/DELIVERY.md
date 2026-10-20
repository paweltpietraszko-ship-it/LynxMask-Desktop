# DELIVERY — LYNX-OCR-CASCADE C1 (CC, 2026-10-20)

Brief `d2664e3`, precheck Codexa PASS `e164352`, recenzja CC `439aad8` (`tasks/LYNX-OCR-CASCADE/cc_review_c1.md`).
Zgoda Pawła na rozmiar: ~470 l. (20.10). Rzeczywisty rozmiar: **550 l.** (`paired_ocr.py` 393, testy 157) — o ~17% ponad szacunek;
zgłoszone Pawłowi w raporcie końcowym. Kod produkcyjny bez zmian (diff tylko w dwóch plikach TASK_SCOPE + artefakty `tasks/`).
Reguły parowania zamrożone commitem `aff284c` przed pierwszym uruchomieniem na holdoucie.

## Wynik (jedno pełne uruchomienie na `aff284c`, raport JSON poza repo)
Modele = faza A (SHA256 zgodne), rapidocr 3.10.0, onnxruntime 1.25.0; digest gold: znany `b2e580ae…`, holdout `d01b11c4…`.

| | znany (50) | holdout (100) |
|---|---|---|
| niemierzalne dokumenty | 0 | 0 |
| regiony: BOTH_AGREE / CONFLICT_REVIEW / PP_ONLY | 489 / 460 / 88 | 852 / 945 / 78 |
| PP_MISSING_TESS_PRESENT / TESS_ONLY_UNCERTAIN | 16 / 10 | 22 / 30 |
| PP_DISTORTED_TESS_VALID | 1 (wartość spoza gold) | 0 |
| gold: PP nienaruszone / zniekształcone / brak | 310 / 20 / 12 | 562 / 30 / 27 |
| krytyczne stracone przez PP | 2 | 0 |
| — wskazane konkretnym alarmem | 1 (doc_00004 NIP: `pp_invalid_id`) | — |
| kandydaci naprawy sumą kontrolną (wszystkie / krytyczne) | 0 / 0 | 0 / 0 |
| PP_MISSING_TESS_PRESENT zawierające wartość gold | 0 / 16 | 1 / 22 |
| alarmy na dokument bez krytycznej straty: wszystkie / konkretne | 9,29 / 1,21 | 9,67 / 1,03 |
| czas na stronę PP / Tesseract TSV | 1,70 s / 0,72 s | 1,64 s / 0,73 s |
RAM procesu na końcu: 197 MB.

Werdykt mechaniczny (reguła w `verdict()`): **naprawa sumą kontrolną `NOT_FEASIBLE`** na obu zbiorach;
**alarm pokrycia `PARTIAL`** (znany: 1 z 2 krytycznych strat), holdout bez krytycznych strat PP (`NO_LOSSES`).

## doc_00004 i doc_00012 (wymóg briefu)
- **doc_00004 NIP** (PP gubi cyfrę): region `CONFLICT_REVIEW / pp_invalid_id`; Tesseract w tym polu nie ma wartości gold
  (`MISSING`). Druga opinia nie naprawia; wykrywa go sam zły kształt identyfikatora w odczycie PP.
- **doc_00012 IBAN** (PP pomija linię): `NOT_LOCATED` — Tesseract ma w tym miejscu linię, ale nieczytelną i z medianą
  pewności < 30, więc zamrożona reguła dała `TESS_ONLY_UNCERTAIN:low_conf`, nie alarm. Bez trafienia; nie dostrajano.

## Obserwacje dla Architekta (bez nowych reguł w C1)
1. Tesseract na tych samych zdegradowanych fragmentach jest słabszy niż PP: 0 przypadków, w których poprawnie odczytał
   wartość zniekształconą lub pominiętą przez PP (150 obrazów, 961 wartości gold). Kierunek „Tesseract poprawia cyfry PP”
   nie ma podstaw w danych.
2. Zgoda dwóch OCR ≠ prawda: holdout `doc_00017` (adres) i `doc_00065` (osoba) — oba OCR zgodnie zniekształcone (`BOTH_AGREE`).
3. Zwykła różnica tekstu dotyczy ~40% sparowanych regionów (`text_close` + `text_differs`: 389/949 znany, 796/1797 holdout), więc arbiter „pokaż człowiekowi każdy spór”
   dałby ~9–10 pytań na dokument. Konkretne sygnały (zły kształt identyfikatora, linia tylko u Tesseracta, dwuznaczna
   geometria) to ~1 na dokument.
4. Z 38 linii „tylko Tesseract” z treścią tylko 1 zawierała wartość gold — to głównie tekst nie-PII, który PP pominął
   (strata treści, nie wyciek). Alarm pokrycia wymaga osobnej decyzji o progu (`TESS_LOW_CONF`), na nowych danych.
6. Arbiter: zasada z odrzuconej Areny (`experiment/lynx-architecture-arena-v02`, `arena_v02.proof`) — rozstrzygać tylko
   dowodem sprawdzalnym w samym fragmencie, nie zgodą/pewnością kandydatów, a dwuznaczność zatrzymywać — jest tu
   zachowana (suma kontrolna, kształt, geometria → REVIEW). W C2 zatrzymanie musi dawać użytkownikowi drogę dalej
   (np. zakrycie spornego fragmentu + „zrób wyraźniejsze zdjęcie albo wklej tekst”), nie samą odmowę.
5. Najmocniejszy sygnał bez drugiego OCR: `pp_invalid_id` (identyfikator o złej długości/sumie w odczycie PP) — 24 / 53 regiony.

## Uzupełnienie po uwadze Pawła: bramka jakości obrazu (20.10)
C1 mierzyło wszystkie obrazy, bez dzisiejszej bramki produktu (`ocr_engine._quality_from_confidence`: średnia pewność
Tesseracta < 70 → odmowa). Przekrój tych samych wyników wg tej pewności (`_run_tesseract(...).confidence` na każdym obrazie,
straty PP z raportu C1; „strata” = wartość gold nieodczytana wiernie, co nie oznacza wycieku — zniekształcone cyfry silnik nadal maskuje):

| próg | znany: dok. przyjęte / straty PP (kryt.) | holdout: dok. przyjęte / straty PP (kryt.) | odrzucone obrazy bez degradacji (L0) |
|---|---|---|---|
| 0 | 50 / 32 (2) | 100 / 57 (0) | 0 |
| 70 (dziś) | 43 / 21 (0) | 84 / 38 (0) | 0 |
| 75 | 38 / 16 (0) | 78 / 32 (0) | 0 |
| 80 | 29 / 13 (0) | 55 / 21 (0) | 5 z 38 |

- **doc_00004 (pewność 19,6) i doc_00012 (15,8) produkt już dziś odrzuca.** Oba „flagowe” przypadki B1/C1 leżą poniżej bramki;
  po bramce 70 PP nie traci żadnej wartości krytycznej na 127 przyjętych obrazach.
- Próg 80 odrzuca też część obrazów niezdegradowanych (pewność Tesseracta zależy od układu i czcionki, nie tylko od jakości
  zdjęcia); 75 nie odrzuca żadnego L0/L1 w holdoucie i 1 L1 w znanym.
- Wniosek CC: kaskada powinna używać Tesseracta przede wszystkim jako **miernika jakości obrazu** (bramka przed PP),
  a nie jako drugiego czytelnika. Zmiana progu to zmiana produktu — osobny kontrakt; syntetyczna degradacja nie wystarczy
  do wyboru 75 vs 80, potrzebne realne zdjęcia z telefonu (lokalnie u Pawła).

## Powtarzalność
Drugi identyczny przebieg na `aff284c` (te same zbiory i modele): raport JSON identyczny po usunięciu `rss_mb`, `secs_pp`, `secs_tess` (porównanie `==` całych słowników: True).

## Testy
`cd backend && py -3 -m pytest tests/test_ocr_cascade_probe.py -q` → `14 passed`. Testy wykryły błąd narzędzia w trakcie
pisania (słowa pod zdublowaną ramką PP liczone jako „brak w PP”) — poprawione przed zamrożeniem. `ruff`: All checks passed.
Strażnik regresji `benchmark.py` nieuruchamiany: diff nie dotyka kodu produktu.

## Prywatność
Tylko syntetyki (`dataset_20260627_095419`, `dataset_20261016_fresh`); narzędzie odmawia ścieżek `dataset_real` i `--out`
w repo; raport bez wartości, tekstu OCR i współrzędnych (test `test_deterministic_and_value_free_summary`).

## GATE
`py -3 gate.py tasks/LYNX-OCR-CASCADE/brief.md e164352 a8b70bd …/gate.txt`, stdout dosłownie:
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: a8b70bdb9dc6ae4f306c1608209b0481c3931037
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 157 lines changed (threshold 150)
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-OCR-CASCADE/cc_review_c1.md
  - tasks/LYNX-OCR-CASCADE/measure/paired_ocr.py
  - tasks/LYNX-OCR-CASCADE/round_01/implementation/DELIVERY.md
```
TOTAL_LINES: zgoda Pawła na ~470 l. (20.10) przed kodem; faktycznie 550 l. (w tym 393 w artefakcie `tasks/`, który gate pomija) — przekroczenie zgłoszone Pawłowi. Limity artefaktu sprawdzone ręcznie: `paired_ocr.py` 393 l. ≤600, najdłuższa funkcja ≤35 l. ≤50.

## Runda 2 — poprawki po audycie Codexa r2 (`tests_r2.txt`, FAIL F1/F2 na `359fca8`)
- **F1 (sklejanie kolumn w pozostałości Tesseracta):** `_segments` dzieli niewykorzystane słowa jednej linii TSV na pola przy
  przerwie > 2 × wysokość słowa (ta sama reguła co `ocr_rapid.build_text`). Test `test_tess_rest_split_by_column_gap` (blisko → 1
  identyfikator, 650 px → 2 osobne pola bez sumy kontrolnej).
- **F2 (zła ramka przerywała pomiar):** tekst PP składany tylko z ramek o poprawnej geometrii; błąd składania dokumentu →
  `unmeasurable="assemble_<Typ>"`, bez przerwania zbioru. Test `test_bad_box_in_full_doc_is_status_not_crash`.
- Oba nowe testy padają na kodzie `359fca8` i przechodzą po poprawce; `repro_r2.py` Codexa (z podmienionym SHA) →
  `F1_reproduced: false, F2_reproduced: false`, exit 0. `pytest tests/test_ocr_cascade_probe.py` → `17 passed`; ruff czysty.
- **Ponowny pełny pomiar (50 + 100) po poprawce:** werdykty bez zmian (`NOT_FEASIBLE` / `PARTIAL`, holdout `NO_LOSSES`), lista
  przypadków gold identyczna. Zmienia się tylko podział linii „tylko Tesseract”: znany TESS_ONLY_UNCERTAIN 10→18; holdout
  PP_MISSING_TESS_PRESENT 22→23 (dodatkowe bez wartości gold), TESS_ONLY_UNCERTAIN 30→38; konkretne alarmy/dok. holdout 1,03→1,04.
  Reguł nie dostrajano do liczb (holdout był już otwarty — poprawka wynika wyłącznie z F1/F2).
- Rozmiar po rundzie 2: 584 l. (zgoda Pawła ~470) — przekroczenie zgłoszone Pawłowi.
- GATE r2 (`gate.py … e164352 1accad3 …/gate_r2.txt`), stdout dosłownie:
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 1accad32fec47bd9f7f0fee0311bdc41cdb94e67
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 174 lines changed (threshold 150)
IMPORTERS_FOR_REVIEW:
  - tasks\LYNX-OCR-CASCADE\round_01\tests\repro_r2.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-OCR-CASCADE/cc_review_c1.md
  - tasks/LYNX-OCR-CASCADE/measure/paired_ocr.py
  - tasks/LYNX-OCR-CASCADE/round_01/implementation/DELIVERY.md
  - tasks/LYNX-OCR-CASCADE/round_01/implementation/gate.txt
  - tasks/LYNX-OCR-CASCADE/round_01/tests/repro_r2.py
  - tasks/LYNX-OCR-CASCADE/round_01/tests/tests_r2.txt
```
