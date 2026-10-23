# DELIVERY — LYNX-OSOBA-PACK4, CC 22.10.2026

Gałąź `task/LYNX-OSOBA-PACK4`, baza main `fa1c375` (po scaleniu FIX1), kod `3edcab5`.
Brief: `tasks/LYNX-OSOBA-PACK4/brief.md` (Codex PASS PREIMPLEMENTATION `31a1259`, sekcja ROZSZERZENIE CC 1–4).

## gate.py (dosłownie, `round_01/gate_r3.txt`)
```
STATUS: WYMAGA_DECYZJI
WYMAGA_DECYZJI:
  - RATIO: 328/16 = 20.5:1 (threshold 5:1)
  - TOTAL_LINES: 344 lines changed (threshold 150)
```
- Rozmiar mieści się w zgodzie OWNERA (~350 l.).
- r1 FAIL SIZE_FUNC: `_process_ner` +1, `_merge_adjacent_entities` +2. Poprawione w r2: helper `drop_street_osoba`, połączony warunek `break`.

## Zmiany
- `osoba_not_person.py`:
  - CAPS-etykieta (1);
  - `inside_street_name`, `drop_street_osoba`, `in_city_name` (3);
  - krok 2: `single_osoba_evidence`, `filter_single_osoba`, rejestr `start_run`/`released` (ContextVar).
- `spacy_ner._merge_adjacent_entities`: OSOBA tylko przez spację/łącznik (2).
- `ner_layer._process_ner`: jedna linia — ulice, instytucje, krok 2.
- `ner_adapter`:
  - imię + nazwisko = jeden token (4, S4);
  - ścieżka słownikowa: ulica, miasto, krok 2.
- `herbert_net`: krok 2 dla pojedynczego PER (przy włączonym HerBERT).
- `pipeline`: `start_run()` na początku dokumentu, `released()` → `collect_warnings`.
- `guard_residue`:
  - kandydaci bez dowodu (z odmianami) jako R1;
  - R1 pomija człony miast;
  - R3 „Miejscowość obok zakrytego adresu”.

## Testy
- `test_osoba_pack4.py` 11 passed.
- `test_guard_residue.py` 50 passed.
- Bez zmian: `test_ner_multiline.py` 21 (warunek wstępny poprawiony zgodnie z briefem), `test_failclosed` 23, `test_osoba_not_person` 25, `test_names_dict_clean` 22, `test_map_fidelity` 29, `test_pipeline_v2` 41, `test_addr_email_leaks` 22, `test_express_one_engine` 6, `test_herbert_net` 7 (+1 skip), `test_amounts_numbers` 20, `test_formats_pack2` 20.
- `test_audyt_2026_10.py`: `test_kont0_nie_jest_osoba` XPASS → marker zdjęty.
  - Pozostaje 1 fail jak na main (Komornik Sądowy).
  - „ul. Kowalskiego 7” przechodzi (wcześniej fail na main).
- `test_layers.py`: 2 faile identyczne jak na main (TestFirmaBounds, S.A.).

## Pomiar
### 1. „Widok człowieka” na LYNX-GOLD-SET
Narzędzie: `tasks/LYNX-GOLD-SET/measure/human_view.py`; dane lokalnie: `backend/dataset_gold_20261022`. Część test — tylko agregaty.

| | main `6264290` (dev / test) | PACK4 (dev / test) |
|---|---|---|
| pozycje zakryte | 933 / 1864 | 933 / 1864 |
| **ciche wycieki** | 164 / 335 | **142 / 297** |
| wycieki z ostrzeżeniem | 55 / 102 | 77 / 140 |
| zbędne zakrycia not_pii | 93/440 / 201/880 | **69/440 / 152/880** |
| ostrzeżeń / dok. | 3,27 / 3,17 | **2,62 / 2,23** |

- OSOBA: dev 325 zakryte / 9 z ostrzeżeniem / 1 cichy, test 657 / 13 / 0 — bez zmian względem main.
- Mniej cichych wycieków głównie dzięki R3 „miejscowość po ADRES”.

### 2. Osoby gold (pomocnik CC; skrypty `%TEMP%\lynx_cc_review\osoba_pack4\measure_final\run.py`, `an.py`)

| | main | PACK4 |
|---|---|---|
| fresh+0627 (365 słów) | 357 zakryte / 0 z ostrz. / 8 ciche | 355 / 2 / **8** |
| KPWr (428 słów) | 403 / 13 / 12 | 370 / 47 / **11** |

- **Regresje ciche: 0.** Pierwszy pomiar wykazał „Maciolusa” — poprawione (ROZSZERZENIE CC 4).
- Wszystkie 36 słów zakrytych na main, a jawnych w PACK4, są „jawne z ostrzeżeniem”, np. Hamleta, Habermasa, Juan, Mikołaj, Jarek, „Pana Tomanz Zając” (OCR).
- Ostrzeżeń/dok.: fresh 0,17 → 0,56, KPWr 1,85 → 3,87 (proza).

## Uwagi
- Na prozie Guard pyta częściej. To skutek decyzji OWNERA: kandydat bez dowodu nie jest zakrywany, tylko pokazywany człowiekowi.
- Na pismach biurowych (GOLD) pytań jest mniej niż na main.

## Runda 2 — Codex r3 F1/F2 (`bf754d1`)
- **F1:** `guard_residue._released` porównuje bez wielkości liter („MALINA” po zwolnionym „Malina” jest pytaniem).
- **F2:** końcówkę odmiany obcinamy także w krótkich słowach, o ile rdzeń ma ≥3 litery („Róża” → „Róż” + końcówka: „Róży”, „Różę”). „Różowy” i „Kawałek” bez pytania.
- Testy: `test_guard_residue.py` +1, `test_osoba_pack4.py` +1 (pełny pipeline, MALINA). Razem 63 passed.
- Reproduktor Codexa `round_01/tests/repro_r3.py`: F1 ok, F2 ok, controls PASS, exit 0.
- GOLD bez zmian: ciche 142/297, zbędne 69/152, pytania 2,62/2,23.

## Runda 3 — Codex r4 F2 (`c1f0c6c`)
- Wcześniej obcinanie końcówki rozróżniało wielkość liter, więc kandydat „RÓŻA” nie obejmował „RÓŻY”. Teraz `_INFLECTION_RE` działa bez względu na wielkość liter.
- Test: parametryzacja Róża / RÓŻA / RÓŻY → ostrzeżenia na RÓŻA i RÓŻY. Testy: 66 passed.
- Reproduktory Codexa: `repro_r3.py` exit 0, `repro_r4.py` exit 0.
