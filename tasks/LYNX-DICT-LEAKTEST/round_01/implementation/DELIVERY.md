# LYNX-DICT-LEAKTEST etap 1 — DELIVERY round_01

BEFORE_SHA: `e5e2e7f5e5d835d79d6745f23003cb2f8c262fc1` · IMPLEMENTATION_SHA: `e102fd87dd105caaa57baae5145ed4a017c00c9f`
Pliki (TASK_SCOPE): nowy `audyt/engine_quality.py` (269 l.), `backend/tests/test_audyt_2026_10.py` (+5 testów). Kod produkcyjny bez zmian. Rozszerzenia CC: brak (wykryte wady to inne klasy i brief zabrania napraw).

## Ocena briefu
Zgodny z kodem; przyjęty. `pipeline.pseudonymize_document` zwraca `PipelineResult(text, reverse_map, guard_blocked, guard_reasons, error)`; przy wyjątku `error` + oryginalny tekst → runner liczy `error`, nigdy sukces. `unmask_sim.unmask` sortuje tokeny po typie, a `Depseudonimizuj.tsx::restoreText` iteruje `Object.keys(map)` w kolejności wstawiania — runner liczy obie i raportuje `order_divergence`. Z góry zaznaczone: runner >150 linii → gate WYMAGA_DECYZJI (brief zabrania osłabiania M1–M3 dla gate).

## Runner
`py -3 audyt/engine_quality.py --seed 2026 --out <poza repo>/quality.json [--holdout <JSON nazwisk>]`
- **M1**: 4 typy pism (urzędowe, umowa, faktura, korespondencja) × 12 wariantów (OSOBA: pełne, odmiana, tytuł, CAPS, inicjał; FIRMA; ADRES; NIP, PESEL, IBAN, telefon; e-mail), każdy z jawnym spanem i kategorią. Statusy: `masked`, `leak`, `leak_partial` (słowo ≥3 znaki ze spanu jawne), `partial_mask` (token pokrywa tylko część wartości), `wrong_category`, `no_mapping`, `blocked`, `error`, `assumption` (span nie występuje w wejściu). Porównanie wartości po usunięciu spacji/interpunkcji.
- **HOLDOUT**: nazwiska z `--holdout`; odrzucone, jeśli baza LUB którakolwiek forma ∈ `_PERSON_FORMS` (surnames_top1000 + names_inflected) albo słowa szablonów M1; próbka 40 przez `random.Random(seed)`; kontrola `overlap_in_sample` (≠0 → `SEPARATION_FAILED`, wyniki nieliczone). Brak pliku → `NOT_MEASURED`.
- **M2**: 8 pułapek (piątek, zapłata, „w Radomiu”, ZUS/GUS, nagłówek CAPS, akronimy, „ul. Kowalskiego 7”, kwota) z jawnie dozwolonymi kategoriami kontraktu (INSTYTUCJA, ADRES, KWOTA) → `fp` / `contract` / `clean` / `blocked` / `error`.
- **M3**: każdy odblokowany przypadek: przywrócenie symulatorem i porównanie znak po znaku z oryginałem; `diff_ops`, `diff_outside_spans`, `missing_map` (token w wyniku bez wpisu w mapie), `order_divergence`. `blocked`/`error` → `blocked_or_error` (nie przechodzą).
- Raport JSON: `git_sha`, data, seed, `input_digest` (sha256 przypadków), `pipeline`, `n_cases`, `assumption_failures`, `holdout_info`, sumy M1/HOLDOUT/M2/M3 per kategoria, ID przypadków ze statusami. **Bez tekstów i wartości encji.** `--out` w repo → odmowa. Brak spaCy/Morfeusza → `status: NOT_RUN`, kod 2 (bez atrapy NER).
- Profil: `build_anonymizer` w `TemporaryDirectory("lynx_quality_")`, sprzątany w `finally` (z `gc.collect()` — SQLite na Windows). Bez HTTP, bez seeda (stan produkcyjny), bez monkeypatchy silnika.

## Dowody
1. Testy runnera (bez spaCy, w `test_audyt_2026_10.py`): deterministyka przypadków i próbki holdout + odrzucenie formy ze słownika + `NOT_MEASURED`; `blocked`/`error`/wyjątek w `run` nie dają `masked`; `leak`, `leak_partial`, `partial_mask` (IBAN-RECEPTA), `wrong_category`; M2 `fp` vs `contract` vs `clean`; M3 wykrywa zgubioną spację (`diff_outside_spans=1`) i token bez mapy; `--out` w repo → odmowa; awaria `build_state` → katalog TEMP usunięty, 0 pozostałości; brak NER → kod 2 i `NOT_RUN`. Wynik: `test_audyt_2026_10.py` `58 passed, 15 xfailed`.
2. Dwa przebiegi z `--seed 2026` i tym samym holdoutem (Mobile `app/src/main/assets/surnames_extended.json`): raporty identyczne poza datą; `input_digest e089762029f7a27b`, `n_cases 96`, `assumption_failures 0`; holdout `pool 37118, sample 40, rejected_overlap 1665, overlap_in_sample 0`.
3. Pełna suita: `1 failed (IBAN-RECEPTA), 126 passed, 40 skipped, 1 xfailed`.

## Wynik bazowy na `e102fd8` (syntetyczny, NIE ocena szczelności)
- M1: OSOBA 20/20 `masked`, FIRMA 4/4, ADRES 4/4, EMAIL 4/4, NUMER 12 `masked` + **4 `partial_mask`** (IBAN — BUG-IBAN-RECEPTA, znany).
- HOLDOUT: 40/40 `masked` (szablon „Pan Jan {X}” — znane imię i tytuł pomagają spaCy; to nie dowód dla nazwisk bez kontekstu).
- M2: 5 `clean`, 3 `contract`, 0 `fp`.
- M3: **51/96 identycznych**, 45 z różnicą poza spanami encji, 0 brak mapy, 0 rozbieżności kolejności. Bez holdoutu: 11/56.

## Zgłoszenia z pomiaru (osobne findingi, nie naprawiane — brief)
- **F1 utrata spacji po kropce**: „Faktura nr 12/2026. Termin…” → „…12/2026.Termin…”, „Ala ma kota. Kot…” → „…kota.Kot…” — także bez encji w zdaniu; Przywróć nie odtwarza oryginału. Źródło 45/96 różnic M3.
- **F2 normalizacja OCR psuje tekst**: „tel. +48 512 987 654. Termin” → po przywróceniu „…654.7ermin” (T→7 po cyfrach).
- **F3 PESEL**: „PESEL 44051401359” → „PESEL: NUMER_001” (dopisany dwukropek); **telefon**: „+” zostaje poza tokenem, wartość w mapie bez spacji → po przywróceniu „+48512987654”.
- ~~F4~~ **wycofane** (korekta Pawła): „Ala ma kota.” → OSOBA to poprawne maskowanie — „Ala” jest imieniem w słowniku.

## gate.py (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: e102fd87dd105caaa57baae5145ed4a017c00c9f
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 347 lines changed (threshold 150)
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r1.txt
```
Uzasadnienie: brief przewiduje WYMAGA_DECYZJI >150 i zabrania osłabiania M1–M3 dla gate. Runner 269 l. (wszystkie funkcje ≤50, ruff czysto), testy 78 l.

## Runda 2 — poprawki po FAIL Codexa r2 (`tests_r2.txt`, `a212f05`)
IMPLEMENTATION_SHA: `ec0c505205c7bb6511626818ee23cc3c13e4f640`. Wszystkie trzy zarzuty trafne.
- **R1** `classify_m1`: liczą się wyłącznie tokeny **obecne w wyniku** i mające wpis w mapie (`_output_tokens`); jeśli którykolwiek token pokrywający span ma inną kategorię → `wrong_category` (wcześniej wystarczył jeden zgodny); wpis w mapie bez tokenu w tekście → `no_mapping`. Przy okazji `TOKEN_RE` bez `` na początku — token sklejony z cyframi („PL6110NUMER_001”) był niewidoczny (wyszło przy teście IBAN po zawężeniu do tokenów z wyniku).
- **R2** `M2_CASES`: kontrakt to `{kategoria: [oczekiwane wartości]}` (ZUS/GUS, „ul. Kowalskiego 7”, „1 250,00 zł”); token dozwolonej kategorii na innym słowie → `fp`. Brane pod uwagę tylko tokeny obecne w wyniku.
- **R3** `_out_path`: porównanie `normcase(realpath)` — ta sama ścieżka repo inną wielkością liter odrzucana.
- Testy: scenariusze z `tests_r2_repro.py` przeniesione jako asercje regresyjne (R1 ×3, R2 ×1, R3 na Windows) obok istniejących granic (masked, blocked, error, leak, partial_mask, fp/contract/clean). `test_audyt_2026_10.py`: `58 passed, 15 xfailed`.
- Realny runner po poprawkach (seed 2026): dwa przebiegi z holdoutem identyczne (`e089762029f7a27b`, 96 przypadków); bez holdoutu digest `ac6a7ca1e033b862`, 56, `NOT_MEASURED` — zgodny z niezależnym przebiegiem Codexa. Wynik bazowy bez zmian (M1 jak wyżej, M2 5 clean + 3 contract, M3 51/96) — zaostrzony klasyfikator nie zmienił oceny realnego silnika na tym zestawie.
- Pełna suita: `1 failed (IBAN-RECEPTA), 126 passed, 40 skipped, 1 xfailed`.

gate.py (stdout dosłownie):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: ec0c505205c7bb6511626818ee23cc3c13e4f640
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 370 lines changed (threshold 150)
IMPORTERS_FOR_REVIEW:
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r2_repro.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-DICT-LEAKTEST/round_01/implementation/DELIVERY.md
  - tasks/LYNX-DICT-LEAKTEST/round_01/implementation/gate.txt
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r1.txt
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r2.txt
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r2_repro.py
```

## Runda 3 — R2 po recheck r3 (`tests_r3.txt`, `9f80d17`)
IMPLEMENTATION_SHA: `528856b9b4c07d4fac2d623d0dab23c709c6c4ee`. Zarzut trafny: kontrakt M2 dalej opierał się na zawieraniu się liter po `_norm`, więc „w” lub „kowal” zamaskowane jako ADRES obok nietkniętego „ul. Kowalskiego 7” dawały `contract`.
- `classify_m2`: token dozwolonej kategorii jest kontraktem tylko gdy jego wartość po `_norm` **równa się całej** oczekiwanej wartości i ta wartość **nie występuje już w wyniku**; inaczej `fp`. M1 (`_overlaps`) bez zmian — R1 zamknięte.
- Testy regresyjne: oba warianty z `tests_r3_repro.py` („w” → ADRES, „kowal” → ADRES przy jawnym adresie) → `fp`; granice dodatnie: cały adres → `contract`, prawdziwa kwota → `contract`, „zapłaty” → KWOTA → `fp`. Przez `measure → report`: wstrzyknięte FP raportowane jako `{'fp': 1}`.
- `test_audyt_2026_10.py`: `58 passed, 15 xfailed`. Realny runner seed 2026 z holdoutem: dwa przebiegi identyczne (`e089762029f7a27b`), wynik bazowy bez zmian (M2 5 clean + 3 contract).

gate.py (stdout dosłownie):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 528856b9b4c07d4fac2d623d0dab23c709c6c4ee
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 377 lines changed (threshold 150)
IMPORTERS_FOR_REVIEW:
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r3_repro.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-DICT-LEAKTEST/round_01/implementation/DELIVERY.md
  - tasks/LYNX-DICT-LEAKTEST/round_01/implementation/gate.txt
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r1.txt
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r2.txt
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r2_repro.py
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r3.txt
  - tasks/LYNX-DICT-LEAKTEST/round_01/tests/tests_r3_repro.py
```
