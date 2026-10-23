# DELIVERY — LYNX-OSOBA-LAYOUT (round 01)

Gałąź `task/LYNX-OSOBA-LAYOUT`, baza `b50655a8d3991add5313714f59f89bb3211e0afa`, kod `92168210ba31f813f4ea33c735ad34d36115e3df`.
Brief: `tasks/LYNX-OSOBA-LAYOUT/brief.md`. CC nie wystawia PASS/FAIL — ocena: gate (niżej) + Codex.

## gate.py (stdout dosłownie, pierwsze linie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 92168210ba31f813f4ea33c735ad34d36115e3df
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 509 lines changed (threshold 150)
```
TOTAL_LINES: zgoda Pawła 23.10 („bez szacunku, każdy plik ≤600 l.”). Gate r1 (`ae0e63b`) dał FAIL: 4 nowe pliki (max 2) i +1 linia w
`apply_ner_layer` — poprawione w `00347c6` (R1 Guarda w `guard_residue.py`, biała lista jako stała; wywołanie w `_apply_dictionary_names`).
Rozmiary: `guard_residue.py` 270 → 277, `person_layout.py` 127 (nowy), `ner_adapter.py` 513 → 514, `pipeline.py` 552 → 552.

## Commity
- `ae0e63b` — pierwsza wersja (person_layout, guard_unknown, testy).
- `00347c6` — po gate r1: scalenie R1 Guarda do `guard_residue.py`, bez pliku JSON.
- `9216821` — po kontroli „pytania main, których gałąź już nie zadaje” na 255 pismach: 3 prawdziwe osoby main tylko pytał, gałąź ani
  nie pytała, ani nie zakrywała (nazwisko w następnym wierszu PDF za tokenem samego imienia; inicjał przyklejony „P.Kapusta”).
  Dodane 2 reguły tej samej klasy (reszta osoby) + testy. Po zmianie: wszystkie 3 zakryte, 0 utraconych.

## Testy (cwd = backend, `.venv`), gałąź vs main `b50655a` — ten sam zestaw plików
| plik | main | gałąź |
|---|---|---|
| test_osoba_layout (nowy) | — | 43 passed |
| test_guard_residue | 54 passed (stara treść) | 50 passed |
| test_osoba_handoff | 17 passed (stara treść) | 16 passed |
| test_guard_allowlist_s5 | 13 passed | 13 passed |
| test_osoba_pack4 | 12 passed | 12 passed |
| test_map_fidelity | 29 passed | 29 passed |
| test_osoba_not_person / test_names_dict_clean | 25 / 22 passed | 25 / 22 passed |
| test_audyt_2026_10 | 1 failed, 122 passed, 2 xfailed | 1 failed, 122 passed, 2 xfailed |
| test_engine_quality_layout | 7 failed, 8 passed | 7 failed, 8 passed |
| test_layers | 2 failed, 119 passed | 2 failed, 119 passed |
| test_smoke_e2e | 8 failed, 1 passed (bez silnika 8765) | 8 failed, 1 passed |
| test_disk_pii | 1 failed, 5 passed | 1 failed, 5 passed |
| pozostałe: addr_email_leaks, addr_reversed, amounts_numbers, anonymizer_adversarial, express_one_engine, failclosed, firma_context, formats_pack2, ner_multiline, output_guard_adversarial, pipeline_adversarial, pipeline_v2, silent_pack1, text_limit_15k, token_re_spec | bez faili | bez faili (identycznie) |

Faile w tabeli są identyczne na main i gałęzi (znane). `test_pipeline`: 1 error przy zbieraniu na obu.

### Zmienione oczekiwania starych testów (nowy model, nie regresja)
- `test_guard_residue`: usunięte pozytywy R1 „Kawa” (zwykłe słowo → Guard nie pyta, test przeniesiony do `test_brak_alarmu`) i „Pan Rogalik”
  (zakrywa teraz silnik — `test_osoba_layout::test_pan_plus_slowo_to_osoba`); testy kanału `released_words` usunięte (parametr nie istnieje);
  „Maciolus/Maciolusa” — teraz jako słowo nieopisane (`test_nieznane_slowo_w_odmianie`); allowlista na słowie nieznanym („Śludkowski”).
- `test_osoba_handoff`: 2 testy `collect_warnings(..., released_words=)` → 1 test „Guard nie czyta rejestru”.
- `test_guard_allowlist_s5`: „Kawa” → „Śludkowski” (słowo, o które Guard nadal pyta).
- `test_osoba_pack4`: „Malina/Róża” bez kotwicy — dawniej pytanie przez released, teraz brak pytania (**świadomy koszt modelu**: nazwisko
  będące słowem pospolitym bez żadnej kotwicy przechodzi cicho; z kotwicą — Pani/imię/etykieta — zakryte, test bez zmian);
  wersaliki: oba wystąpienia traktowane tak samo.
- `test_map_fidelity`: „Anna Nowakowska” zakryta teraz regułą imię + słowo (całym wyrazem, bez doklejenia).

## Pomiar (main `b50655a` → gałąź `9216821`)
| zbiór | miara | main | gałąź |
|---|---|---|---|
| GOLD dev (40) / test (80) | pytania Guarda na dok. | 1,23 / 0,97 | **0,82 / 0,80** |
| GOLD | OSOBA cicho | 1 / 0 | **0 / 0** (test: 1 z pytaniem) |
| GOLD | zbędne zakrycia (not_pii) | 69/440 / 152/880 | 73/440 / 157/880 |
| GOLD | FIRMA cicho | 20 / 52 | 20 / 52 (bez zmian, poza zakresem) |
| `testset_owner` stress (300) | osoby widoczne: cicho (z pytaniem) / 412 | 21 (34) | **8 (1)** |
| `testset_owner` clean (300) | wycieki | 0 | 0 |
| ślepy zbiór (600, ziarno 2026) stress | osoby widoczne: cicho (z pytaniem) / 410 | 17 (39) | **3 (1)** |
| 255 pism (realne publiczne + Pliki testowe) | pytania R1 | 902 | **526** |
| 255 pism | nowe zakrycia OSOBA / utracone | — | 28 / **0** |

Nowe zakrycia OSOBA na 255 pismach (agregat, PII maskowane): ~10 prawdziwych osób (m.in. Kap\*\*\*\*, Ski\*\*, Zaj\*\*\* — dawniej tylko
pytanie; autorzy komentarzy: Cie\*\*\*, Zat\*\*\*\*\*\*, Kid\*\*\*; Cze\*\*\*\*\*\*\*), śmieci: „Apel” („S.Apel.”), „Polska”, „Podlaskim”,
„Trybunalskim”, „Nadbystrzycka”, „Prowadzisz” (za błędnym tokenem osoby / inicjałem). Pozostałe pytania R1 to głównie słowa obce
(„Avenue”, „Nanterre”, „Brunnenstrasse”, „Mozilla”) — zgodnie z modelem decyduje użytkownik.

Ograniczenia pomiaru: `testset_owner` stress był podglądany przy projektowaniu reguł (nie jest dowodem); ślepy zbiór = ten sam generator
(te same układy formularzy); GOLD test — tylko agregaty, mierzony kilkukrotnie (lekka selekcja). Klucz clean/stress mierzy tylko „musi zniknąć”.

## Odtworzenie (Codex, lokalnie)
- Środowisko: `.venv\Scripts\python.exe`, backend z gałęzi (`git worktree add <dir> task/LYNX-OSOBA-LAYOUT`), nigdy z cwd `Desktop\backend`.
- `testset_owner`: `.venv\Scripts\python.exe testset_owner\run_testset.py <worktree>\backend wynik.json` (main: ten sam skrypt na worktree `b50655a`).
- Ślepy zbiór: `py -3 C:\Projects\LynxMask\generator_stress.py --count 300 --output <dir>\gen_stress --seed 2026` oraz
  `generator_clean.py --count 300 --output <dir>\gen_clean --seed 2026`; skopiować do struktury `testset_owner` (corpus/ + gold_*.json + manifest.json;
  id = `<zbiór>__doc_NNNNN.txt`) i uruchomić `run_testset.py`. Gotowa kopia CC: `%TEMP%\claude\…\scratchpad\blind\ts\`.
- GOLD: `%TEMP%\lynx_cc_review\gold\human_view.py <backend> backend\dataset_gold_20261022 all <out>` (cwd = ten katalog, PROFILE_DIR = pusty tmp).
- 255 pism: `round_01`-owe skrypty CC lokalnie: `%TEMP%\claude\…\scratchpad\r1\r1_diag.py` (lista: `%TEMP%\lynx_cc_review\status_2210\jobs_realpub.json,jobs_pub.json`),
  `osoba_diff.py` (cache tekstów `scratchpad\r1\text_cache`). Realne pisma tylko lokalnie, do repo wyłącznie agregaty.

## Do decyzji / następne
- Merge po PASS Codexa (polecenie Pawła 23.10).
- Po merge: zamknąć `task/LYNX-GUARD-R1-FILTERS` (filtry starego R1 — zbędne) i usunąć martwy rejestr `osoba_not_person.released()` (drobna sprawa).
- Następny temat: ciche FIRMA (GOLD 20/52), potem zbędne zakrycia (~17% not_pii) — najpierw zasada słowami.
