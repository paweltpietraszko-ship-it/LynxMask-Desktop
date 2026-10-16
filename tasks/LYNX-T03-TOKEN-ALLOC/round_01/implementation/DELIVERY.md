# DELIVERY — LYNX-T03-TOKEN-ALLOC (CC, runda 1)

Brief: `tasks/LYNX-T03-TOKEN-ALLOC/brief.md` (`bc7f4f7`, precheck Codexa r2 PASS `f33bd62` = BEFORE_SHA).
Ocena CC korekty: B1 (rezerwacja całej przestrzeni profilu, `trie_layer.py` w TASK_SCOPE) zamknięte — brief przyjęty.
CC nie wystawia werdyktu własnej implementacji.

## Zmiana

- `pipeline_core.py` (`TokenAllocator`, istniejący owner):
  - `assign(token_type, value)` — przydział ID bez sprawdzania spanu (dedup po canonical, nowy numer z licznika);
    `allocate()` korzysta z niego po sprawdzeniu spanu (zachowanie `allocate` bez zmian).
  - `reserve(token_id)` — podnosi licznik typu bez wpisu wartości ani spanu.
  - `register()` — na początku: jeśli `token_id` wskazuje już INNĄ wartość kanoniczną → `ValueError("[TOKEN-COLLISION] …")`
    (bez PII w komunikacie); wyjątek przechwytuje istniejące WYS-2 w `run_pipeline_new` → `force_block=True` (S3).
- `layers/trie_layer.py`: przed seedowaniem — `reserve()` dla KAŻDEGO token_id z `anonymizer.anon_map.data["entities"]`
  (także encji nieobecnych w dokumencie). Bez profilu — bez zmian.
- `layers/ner_adapter.py`: lokalne numery `process_ner` (licznik od 001 w `ner_layer`) przemapowane przez
  `_remap_ner_ids()` → `allocator.assign()`; numer dostaje tylko wartość obecna w tekście, odmiany (`ner_variants`) —
  leniwie, gdy są w tekście (zachowany kontrakt autotestu „find=-1 → nie rejestruje”). Usunięte bezwarunkowe `register()`
  numerów NER. `ner_layer.py` bez zmian (numeracja lokalna nieszkodliwa po przemapowaniu).

## Testy

- `test_dwie_osoby_dwa_tokeny` — xfail zdjęty.
- Nowe: `test_token_profilu_zarezerwowany_miedzy_dokumentami` (profil `OSOBA_001 = Jan K.`; dokument bez Jana → inna osoba
  ≠ `OSOBA_001`, `OSOBA_001` NIE w mapie dokumentu; drugi dokument z Janem → `OSOBA_001`),
  `test_formy_osoby_z_profilu_jeden_token` (dwie formy Jana → jeden token profilu), `test_alokator_odrzuca_…`
  (konflikt w `register` → wyjątek; `reserve` + `assign` → numer powyżej rezerwacji; dedup).
- Na BEFORE: `test_dwie_osoby_dwa_tokeny` i `test_token_profilu_zarezerwowany…` FAIL; `test_formy_osoby…` PASS (pilnuje
  zachowania, które brief każe utrzymać).
- Autotesty modułów: `ner_adapter` 19/19, `pipeline_new` 11/11, `pipeline_core` 10/10 (pierwsza wersja zmiany łamała
  autotest `ner_adapter` — rejestrowała wartość nieobecną w tekście; poprawione przed commitem końcowym).
- `pytest tests/` (bez backendu): 3 failed / 122 passed — te same 3 co na BEFORE (filtr NER ×2 naprawione w T01 na main;
  IBAN-RECEPTA).

## Benchmark przed/po (`audyt/bench_offline.py --variants base`, wspólny cache OCR)

| Zbiór | `f33bd62` | `51ff976` |
|---|---|---|
| stały `dataset_20260627_095419` (50 obr., 43 przyjęte) | R 90,0%, FP 164, OSOBA 41/54, CLR 0% | identycznie |
| świeży `dataset_20261016_fresh` (100 obr., 84 przyjęte) | R 89,9%, FP 353, OSOBA 85/112, CLR 0,6% | identycznie |

Oczekiwane: benchmark działa na pustym profilu, więc T03 zmienia tylko numerację, nie zakres maskowania — brak regresji.

## Exact SHA i bramka

- Implementacja: `7b71d90` → **`51ff9760bb71265026d212956ccff0ffac442429`** (końcowa). `7b71d90`: `gate.py` FAIL
  `SIZE_FUNC apply_ner_layer 92 (before 89)`; w `51ff976` przemapowanie wydzielone do `_remap_ner_ids` (86 linii).
- `gate.py` na `51ff976` (dosłownie): `STATUS: PASS` (`gate_r1.txt`).

## Uwaga do merge

Gałęzie T02 i T03 wyszły z `main` sprzed merge T01. Pliki się nie pokrywają z T01 (T01: `ner_layer.py`, `ner_blocklist.py`;
T03: `pipeline_core.py`, `ner_adapter.py`, `trie_layer.py`), wspólny jest tylko `backend/tests/test_audyt_2026_10.py`
(różne sekcje) — przy merge możliwy prosty konflikt w tym pliku testów.
