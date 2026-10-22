# DELIVERY — LYNX-SILENT-PACK1 (round_01)

22.10.2026, CC. Brief: `tasks/LYNX-SILENT-PACK1/brief.md` (B1–B3, Codex BRIEF_ONLY r2 PASS `22c9fcb`).
Baza: `main` `bb0abbc3f4367cfbc3b3f3f52f983e6e12dc3c88`. Implementacja: `753b7afcac0ab5d6b7185c6a376035dbd137a381`.

## Zmiany (numstat względem bazy)
| plik | + | − | co |
|---|---|---|---|
| `backend/firma_context.py` | 57 | 2 | `_FORM_CHAIN_RE` w `_form_start` (klasa 1); `scan_legal_forms`: OSOBA zaczęta przed formą nie blokuje (klasa 1); `_TAIL_FORM_RE`, `_firma_core`, `_common_word`, `firma_core_variants` (klasa 2, B1–B3) |
| `backend/ner_layer.py` | 2 | 2 | import + `return` w `process_ner`; plik 597 l. (bez wzrostu), `_process_ner` bez zmian |
| `backend/layers/amount.py` | 18 | 0 | KWOTA `\d{4,6},\d{2}` / `\d{1,3}(\.\d{3})+,\d{2}` przy słowie kwotowym w zdaniu (klasa 3) |
| `backend/layers/numeric.py` | 6 | 1 | `_NUM_SPACED_RE` — numer rozbity spacjami po etykiecie (klasa 4b) |
| `backend/credential_patterns.json` | 2 | 2 | legitymacja radcy nie tnie dłuższego numeru `PO/2026/0329` (klasa 4a) |
| `backend/tests/test_silent_pack1.py` | 122 | 0 | nowe |

### B1–B3 w `firma_core_variants`
- B1: rdzeń jednej firmy → ten sam `FIRMA_NNN`, wartość w mapie = pełna nazwa z formą (Przywróć daje pełną nazwę).
- B2: rdzenie grupowane; gdy pod jednym rdzeniem są różne pełne wartości → nowy `FIRMA_(max+1)` z wartością rdzenia; OSOBA równa rdzeniowi przechodzi na ten token. Rdzeń nieobecny w tekście → bez zmian.
- B3: `_common_word` = `osoba_not_person._common_or_person(word)`; `common is not False` (True albo błąd Morfeusza `None`) → nie podmieniamy. Rdzeń ≥2 słów bez Morfeusza.

## Gate (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 753b7afcac0ab5d6b7185c6a376035dbd137a381
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 207/7 = 29.6:1 (threshold 5:1)
  - TOTAL_LINES: 214 lines changed (threshold 150)
```
Rozmiar: zgoda OWNERA na ~200 l. udzielona przed kodem (BOARD). 214 = 87 kodu + 122 testów + 5 linii zmienionych; nadwyżka ponad szacunek to B2 (grupowanie rdzeni) i test B2.

## Testy (`.venv`, cwd = `backend/` worktree, `PROFILE_DIR` pusty, plik po pliku)
- `tests/test_silent_pack1.py`: **24 passed** (12 pozytywnych + 11 negatywnych z briefu + `test_k2_dwie_firmy_ten_sam_rdzen` dla B2).
- Regresja: `test_firma_context` 14 passed; `test_layers` 2 failed / 119 passed; `test_amounts_numbers` 20 passed; `test_formats_pack2` 20 passed; `test_addr_email_leaks` 22 passed; `test_map_fidelity` 29 passed; `test_audyt_2026_10` 1 failed / 122 passed / 2 xfailed; `test_osoba_pack4` 12 passed; `test_addr_reversed` 23 passed.
- Faile identyczne na bazie (sprawdzone `git stash`): `test_layers::TestFirmaBounds::test_osoba_i_fragment_formy`, `test_layers::test_forma_prawna_nie_ginie_przy_przywroc[...S.A.]`, `test_audyt_2026_10::test_filtr_ner_nadal_odrzuca_nie_osoby[Komornik Sądowy-FIRMA]`.

## Pomiar „widok człowieka” GOLD (`tasks/LYNX-GOLD-SET/measure/human_view.py`, dataset lokalny `backend/dataset_gold_20261022`, split `all`)
| | baza dev | SP1 dev | baza test | SP1 test |
|---|---|---|---|---|
| ciche wycieki | 102 | **20** | 217 | **52** |
| wycieki z ostrzeżeniem | 37 | 35 | 60 | 60 |
| zbędne zakrycia | 69/440 | 69/440 | 152/880 | 152/880 |
| ostrzeżenia/dok (śr.) | 1,62 | 1,23 | 1,23 | 0,97 |

Wg typu (ciche, dev / test): FIRMA nierodo 33→5 / 70→12; FIRMA rodo 14→14 / 40→40 (poza zakresem: „s.c.”, opis JDG); KWOTA 36→0 / 71→0; NUMER 18→0 / 36→0; OSOBA 1→1 / 0→0; ADRES, EMAIL 0→0.
Wymagania briefu: 0 nowych zbędnych zakryć — spełnione; OSOBA/ADRES/EMAIL bez pogorszenia — spełnione.

## Odtworzenie (Codex)
```
git worktree add <wt> 753b7afcac0ab5d6b7185c6a376035dbd137a381
cd <wt>/backend
PROFILE_DIR=<pusty> <repo>/.venv/Scripts/python.exe -m pytest tests/test_silent_pack1.py -q -p no:cacheprovider --rootdir .
<repo>/.venv/Scripts/python.exe <repo-z-task/LYNX-GOLD-SET>/tasks/LYNX-GOLD-SET/measure/human_view.py <wt>/backend <repo>/backend/dataset_gold_20261022 all <out>
```
Baza do porównania: ten sam pomiar z `bb0abbc` (`git worktree add <wt0> bb0abbc`).

---
# ROUND r2 — poprawka F1 z Codex r3 (`0979c83`)
Implementacja: `6fcab2176def42881ccb3ec0f730eac209c55daa` (diff względem r1 `753b7af`: `layers/amount.py` +4/−2, `test_silent_pack1.py` +4).

## ROZSZERZENIE CC (opis w briefie, sekcja „ROZSZERZENIE CC”)
- Wspólna lista `_UNIT` dla `_AMOUNT_NOCUR_RE` (main) i `_AMOUNT_NOCUR_CTX_RE` (SP1): dodane mm, cm, dm, mg, m3/m³, ml, min, kWh, kW, MWh. Bez jednostek jednoliterowych mylących się z polskim słowem przy IGNORECASE („w”, „t”).
- Ta sama luka na main: „Wartość pomiaru 575,63 mm.” → KWOTA (stary wzorzec) — naprawiona tą samą listą.

## Dowody
- `repro_r3.py` (Codex) na `6fcab21`: exit 0 (8/8 ok).
- `test_silent_pack1.py`: 30 passed. Z `amount.py` z r1 (`753b7af`): 5 failed / 25 passed — nowe negatywne łapią błąd (3 przypadki Codexa, „575,63 mm”, „2 450,00 cm”). Pozytywny „Kwota 1234,56 w terminie 14 dni.” przechodzi.
- Regresja: `test_amounts_numbers` 20 passed, `test_formats_pack2` 20 passed, `test_map_fidelity` 29 passed, `test_layers` 2 failed / 119 passed (te same 2 znane).
- GOLD all na `6fcab21`: dev ciche 20, zbędne 69/440; test ciche 52, zbędne 152/880; KWOTA 120/120 i 240/240 zakryte — bez zmian względem r1.

## Gate (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 6fcab2176def42881ccb3ec0f730eac209c55daa
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 214/8 = 26.8:1 (threshold 5:1)
  - TOTAL_LINES: 222 lines changed (threshold 150)
```
