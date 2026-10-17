# LYNX-IBAN-FOREIGN-ALNUM — DELIVERY round_01

BEFORE_SHA (gate): `23a103e` (synchronizacja gałęzi z main na starcie — brief `10c215e` + późniejsze wpisy BOARD z main; liczenie od `10c215e` daje fałszywy DIFF_SCOPE na `BOARD.md`) · IMPLEMENTATION_SHA: `a7809540efe254b12eac9b657b3d795664689d57`
Pliki: TASK_SCOPE (`layers/ocr_normalizer.py`, `layers/financial.py`, `tests/test_layers.py`, `tests/test_pipeline_adversarial.py`) + ROZSZERZENIE CC E1 `layers/identity.py` (w briefie `46e1671` przed kodem); E2 w `financial.py` (w briefie `6c41a7d` przed kodem).

## Ocena briefu i diagnoza
Brief zgodny z kodem; przyjęty. `where.py`: `_fix_iban_digits` wywoływane tylko w kroku 8d `normalize_ocr`. Reproduktor przed zmianą (full = Express): „Konto: GB82 WEST 1234 5698 7654 32. Dalej.” → normalizator: „6882 WE57 …” (G→6, B→8, S→5, T→7) → „Konto: 6882 NUMER_001. Dalej.”, mapa „WE57 1234 5698 7654 32” — jawny uszkodzony prefiks. Drugi, osobny mechanizm (E1): „GB82WEST12345698765432” (compact) — normalizator go nie zmienia, ale `identity` (przed `financial`) zabiera 14 końcowych cyfr → „GB82WESTNUMER_001”. `financial._IBAN_FOREIGN_RE` dopasowuje oba warianty w całości — sam w izolacji był zielony.

## Co zrobione
- `ocr_normalizer._fix_iban_digits`: gdy wartość po etykiecie zaczyna się jak obcy IBAN (`(?!PL)[A-Z]{2}\d{2}` + znak BBAN), zostaje bez zmian. Naprawa OCR polskich/cyfrowych rachunków po etykiecie bez zmian. Plik 696 linii (jak przed Taskiem).
- **E1** `identity.apply_identity_layer`: trafienie przecinające pełny zagraniczny IBAN (`financial._IBAN_FOREIGN_RE`, ≥15 znaków) bez objęcia całości pomijane — reguła T07 przez `fallback.cuts_long_number` (`fallback.py` bez zmian); całość bierze `financial`.
- **E2** `financial._IBAN_PL_OCR_RE`: dopasowanie kończy się cyfrą (wcześniej `[\d\s]{20,55}` połykało spację/nową linię ZA numerem: „…2874 dziś” → „NUMER_001dziś”, „…2874\nKolejna” → „NUMER_001Kolejna” — także przed Taskiem).

## Dowody
- Przed/po (NER wyłączony, full = Express): GB ze spacjami po „Konto:” i „IBAN:”, GB compact po etykiecie → jeden `NUMER_NNN`, mapa = cały IBAN z literami i separatorami, Przywróć 1:1, `force_block=False`; „Konto: GB82 WEST.” bez tokenu; DE, FR (litera w BBAN), PL (spacje, OCR „1O9O…”, „0J12”), e-mail localpart — bez zmian względem bazy.
- Testy: `test_layers.py::TestForeignIbanLayers` (normalizator nie zmienia obcego IBAN ×3, nadal naprawia OCR PL po etykiecie, identity+financial pełny numer ×2), `test_pipeline_adversarial.py::TestForeignIbanWhole` (4 przypadki × full/Express: jeden token, tekst przed/po bez zmian, cała wartość; negatyw „GB82 WEST”). Na `0dd4bdc`: 11 FAIL (w tym subtesty), teraz zielone. Celowane (`test_layers`, `test_pipeline_adversarial`, `test_audyt`, `test_pipeline_v2`): `268 passed, 1 skipped, 10 xfailed, 8 subtests passed`; pełna suita `129 passed, 40 skipped, 1 xfailed` (0 failed); autotesty: ocr_normalizer 40/40, identity 15/15, financial 12/12.
- **Przegląd** `implementation/iban_sweep.py` (z `backend/`, baza w worktree): 7 IBAN (GB, NL, IT, FR z literami; DE, CH, PL cyfrowe) × spacje/compact × 5 etykiet × 3 konteksty po × 2 tryby = 420. **Regresje 0, naprawione 117, wyciek 0, zmieniony tekst po numerze 0** (przed E2: 40 — wszystkie PL). Przegląd T07 `number_sweep.py` nadal 0 regresji.
- Pomiar `engine_quality --seed 2026` + holdout, ten sam digest: 0 zmian statusu, M3 84/96 (zestaw nie ma obcych IBAN z literami — to nie dowód naprawy).

## gate.py (stdout dosłownie, base `23a103e`)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: a7809540efe254b12eac9b657b3d795664689d57
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 66/6 = 11.0:1 (threshold 5:1)
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\docs_variants.py
  - backend\ner_layer.py
  - backend\pipeline_new.py
  - backend\smoke_test.py
  - tasks\LYNX-T12-ARCHIVE-TESTS\round_01\implementation\t12_same_process.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\implementation\phone_sweep.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r4_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r5_repro.py
  - backend\tests\test_audyt_2026_10.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-IBAN-FOREIGN-ALNUM/round_01/implementation/iban_sweep.py
  - tasks/LYNX-IBAN-FOREIGN-ALNUM/brief.md
```
WYMAGA_DECYZJI tylko RATIO 66/6: zmiana addytywna — kod produkcyjny ~12 linii netto (3 pliki), reszta to testy wymagane briefem. Bez samodzielnego poszerzania (brief).

## Znane ograniczenia / poza zakresem
- PL IBAN: wartość w mapie bez spacji (normalizacja `financial`) — Przywróć nie oddaje oryginalnych odstępów (F3).
