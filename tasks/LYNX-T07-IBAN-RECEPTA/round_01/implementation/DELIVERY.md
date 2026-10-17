# LYNX-T07-IBAN-RECEPTA — DELIVERY round_01

BEFORE_SHA: `7c6475e579ea9306eab2968520a19abf534b3d1f` · IMPLEMENTATION_SHA: `2e34d1d3dec6478f5a39747dd1c23d1c2437fdce` (kod `6f52033`, rozszerzenie E1 w briefie `8012116`, E2 w briefie `94fd23d`, kod E2 `2e34d1d`)
Pliki: TASK_SCOPE (`credential_patterns.json`, `layers/fallback.py`, `pipeline_new.py`, `tests/test_audyt_2026_10.py`) + ROZSZERZENIE CC: `layers/contact.py` (E1), `layers/credentials.py` (E2). `tests/test_pipeline_v2.py` bez zmian (jego dotychczasowy FAIL `TestIbanWithSpace::test_iban_reverse_map_entry` przechodzi sam).

## Ocena briefu
Zgodny z kodem; przyjęty. `where.py` (REQUIRED) przejrzane: fallback wywoływany tylko w `run_pipeline_new` (dotąd PRZED `validation`); `_load_patterns` kompiluje każdy wzorzec osobno — nowy wzorzec recepty się kompiluje (autotest credentials 13/13). Uwaga z kodu: gdyby IBAN z prefiksem kraju nie został rozpoznany przez `financial`, sam regex cyfr zostawiłby „PL61” jawne — dlatego reguła 15+ obejmuje przyklejony prefiks `[A-Z]{2}` jako część jednej wartości.

## Co zrobione
- **Recepta** (`credential_patterns.json`): etykieta wymagana (`recepta [nr|numer]`, `nr/numer recepty`, opcjonalny dwukropek) i granice całej 22-cyfrowej wartości (`(?<![\d-])…(?![\d-])`). Bez etykiety 22 cyfry → nie credentials, tylko fallback. Inne wzorce JSON bez zmian.
- **Fallback** (`layers/fallback.py`): `_LONG_NUMBER_RE` — ≥15 cyfr z pojedynczymi spacjami/tabami/myślnikami (opcjonalny prefiks kraju), `(?<!\w)…(?!\w)`: nie przechodzi przez newline, interpunkcję, wyraz ani token (cyfry tokenu poprzedzone `_`). `apply_fallback_layer(state, full=True)`: najpierw 15+, potem (tylko full) dotychczasowe 8+ kolejnych cyfr. Jeden `NUMER_NNN` na całą resztkę, wartość w mapie = dokładny span.
- **Kolejność** (`pipeline_new.py`): full — fallback po `validation` (ostatnia warstwa); Express — `apply_fallback_layer(state, False)` na końcu (tylko 15+, bez 8–14).
- **ROZSZERZENIE CC E1** (`contact.py`) i **E2** (`credentials.py`) — ta sama klasa „warstwa maskuje fragment dłuższego numeru”, wpisane do briefu przed kodem: wspólna reguła w `fallback.py` `long_number_runs()` + `cuts_long_number()` — trafienie, które przecina ciąg ≥15 cyfr, ale nie obejmuje go całego, jest pomijane; całość bierze fallback. E1: telefon „123 456 789” z „123 456 789 012 345”; E2: tablica rejestracyjna „PL6110” z „PL6110 9010 1400 000”. Oba przeciekały także przed T07. Recepta z etykietą obejmuje cały ciąg — nadal rozpoznawana; e-mail nie podlega regule (tylko NUMER w contact).

## Dowody
- Testy: zdjęty `xfail` z `test_iban_pl_bez_jawnej_resztki` — teraz: dokładnie jeden `NUMER_NNN`, wynik = tekst z całym spanem zastąpionym tokenem, wartość = cały numer (bez spacji — normalizacja `financial`, klasa F3), `force_block=False`. Nowe: `test_credentials_recepta_cala_wartosc` ×5 (seam credentials), `test_fallback_dlugie_numery_w_calosci` ×7×2 tryby (22 bez etykiety, 15 ciągłe/spacje/myślniki, PL-prefiks E2, wiersz+newline, K1 e-mail z cyframi + liczba; wynik znak w znak z tokenami, brak tokenów w wartościach mapy), `test_fallback_8_14_tylko_pelny_tryb`. Na `7c6475e`: 13 z nowych/odblokowanych FAIL.
- `test_audyt_2026_10.py` + `test_pipeline_v2.py` + `test_layers.py`: `220 passed, 10 xfailed`. **Pełna suita: `127 passed, 40 skipped, 1 xfailed` — 0 failed** (pierwszy raz: znany FAIL IBAN-RECEPTA w `test_pipeline_v2` przechodzi). Autotesty: contact 16/16, credentials 13/13, fallback 9/9, pipeline_new 11/11.
- **Przegląd rodziny** `implementation/number_sweep.py` (z `backend/`; stary kod w tymczasowym worktree na `7c6475e`): 300 przypadków = długości 8/11/15/22/26 × zapis ciągły/spacje/myślniki × etykiety (brak, Konto, Nr, tel., numer recepty) × prefiks PL/brak × full/Express. **Regresje 0, naprawione 150, zmieniony tekst po numerze 0.** Pozostałe 70 jawnych to wyłącznie numery <15 cyfr: Express 8/11 cyfr (brief: Express bez 8–14) i full 8/11 cyfr z separatorami (brief zachowuje tylko 8+ kolejnych). Żaden ciąg ≥15 cyfr nie przecieka w żadnym trybie.
- Pomiar `audyt/engine_quality.py --seed 2026` + holdout, ten sam `input_digest e089762029f7a27b`: **M1 NUMER 12 masked + 4 partial_mask → 16 masked** (4× IBAN), pozostałe statusy bez zmian; HOLDOUT, M2 (5 clean + 3 contract, 0 FP) bez zmian; M3 84/96 bez zmian (IBAN nadal różni się po Przywróć — wartość bez spacji, klasa F3).

## gate.py (stdout dosłownie, finalny SHA)
```
STATUS: PASS
HEAD_SHA: 2e34d1d3dec6478f5a39747dd1c23d1c2437fdce
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\docs_variants.py
  - audyt\rota_leak_test.py
  - audyt\trace_layers.py
  - backend\pseudominizer_api.py
  - backend\smoke_test.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r4_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r5_repro.py
  - tasks\LYNX-T07-IBAN-RECEPTA\round_01\implementation\number_sweep.py
  - tasks\LYNX-T03-TOKEN-ALLOC\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\implementation\holdout_measure.py
  - tasks\LYNX-NER-GEO-EXACT\round_01\implementation\geo_measure.py
  - tasks\LYNX-NER-GEO-EXACT\round_01\implementation\geo_vertical.py
  - tasks\LYNX-NER-GEO-EXACT\round_01\tests\tests_r3_repro.py
  - backend\tests\test_layers.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-T07-IBAN-RECEPTA/round_01/implementation/number_sweep.py
  - tasks/LYNX-T07-IBAN-RECEPTA/round_01/tests/tests_r2.txt
  - tasks/LYNX-T07-IBAN-RECEPTA/brief.md
```

## Zgłoszenia (poza zakresem — nie wykonane)
- **Numery 8–14 cyfr z separatorami** (np. „6110 9010”, 11 cyfr w grupach) — jawne w obu trybach; w Express także 8–14 ciągłe. Brief świadomie zachowuje dotychczasowe zasady; do decyzji, czy rozszerzyć fallback pełnego trybu na 8–14 z separatorami (ryzyko FP: daty, kwoty, kody).
- **F3 / wartość mapy**: IBAN „PL61 1090 …” i 15 cyfr ze spacjami mają w mapie wartość znormalizowaną (bez spacji / z myślnikami przy deduplikacji alokatora), więc Przywróć nie oddaje oryginalnego zapisu. Wierność, nie wyciek — istniejący LYNX-TEXT-FIDELITY-F3.
- „(+48) 606 …” w nawiasie nie łapane przez wzorzec telefonu po słowie kluczowym (z T11) — bez zmian.
