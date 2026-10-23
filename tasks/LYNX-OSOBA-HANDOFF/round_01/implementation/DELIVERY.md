# DELIVERY — LYNX-OSOBA-HANDOFF (round_01)

23.10.2026, CC. Brief `tasks/LYNX-OSOBA-HANDOFF/brief.md` (Codex BRIEF_ONLY r2 PASS PREIMPLEMENTATION `95f5ddd`).
Baza: `main` `edc28684413793866f3e71eaa4fa4809b61ffd97`. Implementacja: `9f8a07e5eb8f0500c872ac1478c597036b1f80e3`.

## Zmiany (numstat względem bazy)
| plik | + | − | co |
|---|---|---|---|
| `backend/osoba_not_person.py` | 23 | 0 | `_NAME_SHAPE_RE`, `_VOWEL_RE`, `_surname_forms()` (lista ładowana raz; brak/uszkodzony plik → pusty zbiór); w `single_osoba_evidence` przed `_RELEASED.append`: **B** nie-nazwa → bez przekazania; **A (granica z sekcji „Granica (zastępuje pkt 1.A)”)** `common and not person and low not in person_forms and _surname_forms() and low not in _surname_forms()` → bez przekazania |
| `backend/guard_residue.py` | 2 | 1 | `_released`: pomija wystąpienia w całości małymi literami; CAPS i wielka litera bez zmian |
| `backend/surnames_extended.json` | 1 | 0 | nowy: Mobile `app/src/main/assets/surnames_extended.json` (38 783 hasła) oczyszczony `tasks/LYNX-NAMES-DICT-CLEAN/clean_names.py` (bez `--closed`; −16 808 form innych słów), zapis zwarty w 1 linii, 4,5 MB |
| `backend/tests/test_osoba_handoff.py` | 74 | 0 | nowy, 17 testów |
| `tasks/.../r1_diag.py`, `c1_evidence.py` | — | — | narzędzia pomiaru/dowodu (ruff czysty) |

## Gate (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 9f8a07e5eb8f0500c872ac1478c597036b1f80e3
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 100/1 = 100.0:1 (threshold 5:1)
```
RATIO — sam dopisany kod (filtr), nic nie usuwano. TOTAL_LINES < 150 (bez zgody).

## Testy (`.venv`, cwd = `backend/` worktree, plik po pliku)
- `tests/test_osoba_handoff.py`: **17 passed**. Na kodzie z bazy (`osoba_not_person.py` + `guard_residue.py` z `edc2868`, ta sama lista): **14 failed / 3 passed** — przechodzą tylko 3 testy „możliwe nazwisko nadal do Guarda” (zachowanie bazowe).
  Klasy odbioru: rola spoza listy ×4 (Przystępującego, Powódka, Odwołującemu, Protokolant) → brak przekazania; Kawa/Malina/Maciolus → przekazane;
  **C1:** Holub, Prokopenko (test sprawdza `common=True, person=False` i obecność na liście) → przekazane; kandydat w `person_forms` spoza listy → przekazany;
  brak pliku listy → A wyłączona (Powódka przekazana jak na main); nie-nazwy ×4 („……”, Pzp, Cz, G) → brak; małe „kawa” bez R1, „KAWA” z R1; reproduktor „i/a” → brak ostrzeżeń.
- Regresja: `test_guard_residue` 54 passed, `test_osoba_pack4` 12, `test_osoba_not_person` 25, `test_guard_allowlist_s5` 13, `test_silent_pack1` 30, `test_map_fidelity` 29;
  `test_layers` 2 failed / 119, `test_audyt_2026_10` 1 failed / 122 / 2 xfailed — te same znane faile co na main.

## Pomiar na exact SHA `9f8a07e`
`round_01/implementation/r1_diag.py <backend> <jobs_realpub.json>,<jobs_pub.json> <out>` (zadania z `%TEMP%\lynx_cc_review\status_2210\`, tekst z cache ekstrakcji):
| | main `2ea3a12` | gałąź |
|---|---|---|
| pytania R1, 255 dok. | 7448 | **902** |
| — z `released()` | 6760 | 214 |
| KIO B_kio / dataset_public (R1/dok.) | 72,3 / 54,4 | 5,6 / 5,0 |
| dopasowania R1 do osób z gold (metryka zgrubna) | 3 | 4 |
Pozostałe w `released()`: Komornika 10, Sam 9, Brunnenstrasse 7, Komornik 7, Rady 5, Konieczne 5, Röttelnweiler 4, Mają 4, … (odczyt imię/nazwisko albo nieznane — poza regułą A, zgodnie z briefem).

GOLD `human_view.py all` (dataset lokalny `backend/dataset_gold_20261022`):
| | main | gałąź |
|---|---|---|
| dev: ciche / OSOBA ciche / OSOBA z ostrzeżeniem | 20 / 1 / 9 | 20 / 1 / 9 |
| test: ciche / OSOBA ciche / OSOBA z ostrzeżeniem | 52 / 0 / 13 | 52 / 0 / 13 |
| zbędne zakrycia dev / test | 69/440, 152/880 | 69/440, 152/880 |
| ostrzeżeń/dok. dev / test | 1,23 / 0,97 | 1,23 / 0,97 |
Odbiór briefu: R1 ≤ 950 ✓ (902); GOLD ciche razem i OSOBA nie większe niż main ✓; zbędne bez zmian ✓.
Wynik wariantu finalnego (z ochroną listą) praktycznie równy prototypowi bez listy (899 → 902; `released()` 211 → 214) — różnicy 3 pozycji nie rozbierałem.

## Odtworzenie (Codex)
```
git worktree add <wt> 9f8a07e5eb8f0500c872ac1478c597036b1f80e3
cd <wt>/backend && <repo>/.venv/Scripts/python.exe -m pytest tests/test_osoba_handoff.py -q -p no:cacheprovider --rootdir .
<repo>/.venv/Scripts/python.exe <wt>/tasks/LYNX-OSOBA-HANDOFF/round_01/implementation/r1_diag.py <wt>/backend %TEMP%\lynx_cc_review\status_2210\jobs_realpub.json,%TEMP%\lynx_cc_review\status_2210\jobs_pub.json <out>
```
(`r1_diag.py` używa `%TEMP%\lynx_cc_review\status_2210\extract_one.py` do ekstrakcji PDF w osobnym procesie i własnego cache tekstu.)

## Granice (jak w briefie / Codex r2)
- Nazwisko spoza listy 39k i `person_forms`, tylko-pospolite w Morfeuszu, bez dowodu w zdaniu — nie dostanie pytania z `released()` (może z `_r1`). Rozmiar klasy niezmierzony.
- Oko Pawła: pismo KIO na silniku z gałęzi — do zrobienia po audycie Codexa albo na prośbę Pawła.
