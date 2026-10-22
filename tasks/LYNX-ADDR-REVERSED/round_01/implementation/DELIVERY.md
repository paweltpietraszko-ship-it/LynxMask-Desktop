# DELIVERY — LYNX-ADDR-REVERSED, CC 22.10.2026

Gałąź `task/LYNX-ADDR-REVERSED`, baza main `3ad472b`, kod `39c9239`. Brief: `tasks/LYNX-ADDR-REVERSED/brief.md` (przypadki z diagnozy Qwen 3.8; sekcja „Korekta odbioru i wykonawca”).
Kod WIP Qwena (`7ee92c5`) wycofany commitem `f410b67`, więc baza to main. Zapis próby: `round_01/qwen_trial.md`.

## gate.py (dosłownie, `round_01/gate_r1.txt`)
```
STATUS: WYMAGA_DECYZJI
WYMAGA_DECYZJI:
  - RATIO: 102/1 = 102.0:1 (threshold 5:1)
```
Zmiana ma 102 linie (<150). `apply_address_layer` nie rośnie: podmieniona jedna linia wywołania.

## Zmiana (`backend/layers/address.py`)
Nowa faza 3 `_with_neighbours(text, all_hits)` na zebranych trafieniach, przed wspólnym `_apply_hits`. Uzupełnia każde trafienie o:
- **ucięty kod pocztowy:** trafienie kończy się dwiema cyframi, a dalej jest `-NNN` → doklejamy całość („… 15 31” + „-001”);
- **miasto przed adresem:** 1–2 słowa z SIMC (`_CITY_FORMS` / ASCII), odstęp albo przecinek, ta sama linia;
- **ulicę bez prefiksu po „kod + miasto”:** „, Twarda 18”;
- **miasto po adresie, tylko po przecinku:** `_match_city`.

Dodatkowo kod pocztowy spoza trafień z miastem tuż przed nim daje trafienie „Miasto, NN-NNN”.

Samo miasto bez sąsiedztwa adresu zostaje jawne.

## Testy
- `backend/tests/test_addr_reversed.py`: **15 passed**.
  - 9 przypadków zakrycia z kontrolą sklejeń (`GLUED`) i Przywróć 1:1.
  - 6 przypadków „samo miasto jawne, bez ADRES”.
- Bez zmian względem main:
  - przechodzą: `test_addr_email_leaks` 22, `test_map_fidelity` 29, `test_pipeline_v2` 41, `test_osoba_pack4` 12, `test_guard_residue` 54, `test_failclosed` 23, `test_formats_pack2` 20, `test_amounts_numbers` 20, `test_express_one_engine` 6;
  - znane faile jak na main: `test_layers` 2, `test_audyt_2026_10` 1 (Komornik).
- Ruff czysto.

## Pomiar „widok człowieka” LYNX-GOLD-SET (`tasks/LYNX-GOLD-SET/measure/human_view.py`, dev / test, część test tylko agregaty)

| | main `3ad472b` | ADDR-REVERSED |
|---|---|---|
| ADRES zakryte | 40/120 · 80/240 | **120/120 · 240/240** |
| ciche wycieki (wszystkie typy) | 142 · 297 | **102 · 217** |
| wycieki z ostrzeżeniem | 77 · 140 | 37 · 60 |
| zbędne zakrycia not_pii | 69/440 · 152/880 | 69/440 · 152/880 (bez zmian, w tym „city_only”) |
| pytania Guarda / dok. | 2,62 · 2,23 | **1,62 · 1,23** |

## Granice
- Miasto po adresie: przecinek albo odstęp (r2), zawsze potwierdzone w SIMC, ta sama linia.

## Runda 2 — Codex r1/r2 F1–F2 (`0826de1`), kod `249c72f`
- **F1:** miasto po ulicy także po samym odstępie (spacja/tab), dwuwyrazowe i ASCII: „ul. Polna 5 Radom” → jeden ADRES.
- **F2 (S4, OWNER_CORRECTED):** `_city_before` nie zabiera słowa, które jest:
  - słowem osoby rozpoznanej przed warstwą adresu (`state.ner_results`, przekazane do `_with_neighbours`);
  - słowem tuż po imieniu (`names_inflected`) albo po „Pan/Pani/p.”.
  - „Pan Jan Kalisz, ul. Polna 5” → „Pan OSOBA_001, ADRES_001” (OSOBA = Jan Kalisz). Usunięte zdanie z „Granic” o akceptacji tego nadmaskowania.
- Testy:
  - `test_addr_reversed.py`: 21 passed (+4 separator, +2 nazwisko);
  - regresja bez zmian: addr_email 22, map_fidelity 29, pipeline_v2 41, osoba_pack4 12, failclosed 23, formats_pack2 20;
  - reproduktor Codexa `repro_r1.py`: space → ADRES całość, person → OSOBA=Jan Kalisz + ADRES=ul. Polna 5.
- GOLD bez zmian względem r1: ADRES 120/120 · 240/240, ciche 102 · 217, pytania 1,62 · 1,23, OSOBA jak main.
- gate r2: STATUS: WYMAGA_DECYZJI —   - RATIO: 131/1 = 131.0:1 (threshold 5:1) 

## Runda 3 — Codex r3 F3–F4 (`85197dc`), kod `de4185e`
- **F3 (regresja r2):** ochrona nazwiska działała globalnie (słowa osób z całego dokumentu). Teraz `_city_before` pomija miasto tylko wtedy, gdy tekst w TYM miejscu kończy się pełną rozpoznaną osobą („Jan Kalisz”), albo słowo stoi po imieniu / „Pan/Pani”. „Podpis: Jan Kalisz. Adres doręczenia: Kalisz, ul. Polna 5.” → „Podpis: OSOBA_001. Adres doręczenia: ADRES_001.”
- **F4 (wcześniejszy, ta sama klasa):** nachodzące trafienia adresu („26-600 Radom” i „Radom, ul. Polna 5”) łączymy w jedno w `_with_neighbours`. Wcześniej `_apply_hits` odrzucał mniejsze i kod zostawał jawny. „Adres: 26-600 Radom, ul. Polna 5” → „Adres: ADRES_001”.
- Testy:
  - `test_addr_reversed.py` 23 passed (+2 F4);
  - reproduktor Codexa `repro_r3.py`: F1, F2, city-control, F3, F4 ok, exit 0;
  - regresja bez zmian: addr_email 22, map_fidelity 29, pipeline_v2 41, osoba_pack4 12, failclosed 23, formats_pack2 20.
- GOLD bez zmian: ADRES 120/120 · 240/240, ciche 102 · 217, pytania 1,62 · 1,23.
- gate r3: STATUS: WYMAGA_DECYZJI 
