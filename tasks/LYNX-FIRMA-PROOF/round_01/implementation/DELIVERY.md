# DELIVERY — LYNX-FIRMA-PROOF (round 01)

Gałąź `task/LYNX-FIRMA-PROOF`, baza main `948c3bb`, kod `bff9b8a` (pomiary na `d2fd24d` — różnica `bff9b8a` to tylko przeniesienie
wywołań bez zmiany logiki: `firma_proof` w istniejącej linii `_process_ner`, propagacja na początku `apply_fallback_layer`
zamiast osobnej linii w `run_pipeline_new`; KIO 40 na żywym silniku z `bff9b8a`: wynik dokumentu KIO_230261 jak niżej).

## gate.py (dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: bff9b8ab7cf685096898b1a9ee024a17d2c5e88e
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 504 lines changed (threshold 150)
```
Rozkład: kod +218/−42 (nowy `firma_proof.py` 125 l.), testy +150/−94 (nowy `test_firma_proof.py` 116 l., klasa instytucji
w `test_pseudominizer.py` przepisana). Każdy plik < 600 l. (`ner_layer.py` 597 → 598). Zgoda Pawła na przekroczenie TOTAL_LINES — do uzyskania (pytanie w BOARD).

## Pomiar (ten sam kod, pusty profil, w procesie)
| miarka | main `948c3bb` | gałąź |
|---|---|---|
| KIO 40 (publiczne orzeczenia) — pozycje panelu Guarda | 272 (6,8/pismo) | **158 (4,0/pismo)** |
| — czerwone MAP_LEAK | 43 | **4** |
| — R4 „Numer lub data” | 113 | **42** |
| — R1 „Możliwe nazwisko” | 100 | 95 |
| — R5 / R3 | 11 / 5 | 12 / 5 |
| KIO — rdzenie firm z formą prawną jawne częściej niż na main | — | 2 (oba to śmieci-fragmenty: „Dróg”, „Nieruchomości”); częściej zakryte: 11 |
| GOLD dev — ciche wycieki / zbędne zakrycia / pytania na dok. | 0 / 69 z 440 / 0,53 | 0 / **18** / 0,53 |
| GOLD test (tylko agregaty) | 1 / 152 z 880 / 0,53 | 1 / **43** / 0,54 |
| GOLD FIRMA rodo / nierodo (test) | 160 zakryte / 158+1+1 | bez zmian |
| `testset_owner` stress — osoby widoczne (z pytaniem) | 8 (1) | 8 (1) |
| ślepy zbiór 600 (generator Mobile, ziarno 2026) stress — osoby | 3 (1) | 3 (2) |
| dokument z panelu Pawła KIO_230261 (żywy silnik, profil Pawła) | 12 pozycji (rejonu ×75, HONDA, AG-COMPLEX, komisji przetargowej, 86, 10, 153…) | **5** (Stihl, Sthil, Profihopper, Complex, Luxursus — słowa obce, R1) |

Agregaty KIO: `tasks/LYNX-FIRMA-PROOF/measure/kio_panel_base_vs_final.json`, pełny wydruk: `measure/wyniki_final.txt`.

## Jak odtworzyć (Codex lokalnie)
```
# kod gałęzi do katalogu (bez ruszania 8765):
git archive bff9b8a backend | tar -x -C <dir>
.venv\Scripts\python.exe tasks\LYNX-FIRMA-PROOF\measure\inproc.py <dir>\backend <out> backend\dataset_real_public\B_kio\docs\*.txt
.venv\Scripts\python.exe tasks\LYNX-FIRMA-PROOF\measure\firmleak.py <out_main> <out_galaz>     # firmy z formą jawne: main vs gałąź
py -3 tasks\LYNX-FIRMA-PROOF\measure\agg2.py <out> R4                                        # co zostało w panelu (+ konteksty R4)
# GOLD: tasks/LYNX-GOLD-SET/measure/human_view.py (gałąź task/LYNX-GOLD-SET) <dir>\backend backend\dataset_gold_20261022 all <out>
# testset_owner: testset_owner\run_testset.py <dir>\backend <wynik.json>
```

## Testy
- Nowy `tests/test_firma_proof.py`: 56 passed.
- Regresja: każdy plik `backend/tests/test_*.py` osobno (bez `test_pseudominizer.py`, który woła HTTP 8765) w pełnych worktree
  main `948c3bb` i gałęzi `bff9b8a`: main 23 linie FAILED/ERROR, gałąź 22; **nowych faili brak**. Różnice to tylko środowisko
  (worktree gałęzi ma token silnika i modele): `test_herbert_net` 7+1 skip → 8 passed, `test_smoke_e2e` 8 → 7 failed (401 na main).
  Wydruki: `measure/testy_main_948c3bb.txt`, `measure/testy_galaz_bff9b8a.txt`. Znane faile main bez zmian, m.in.
  `test_layers.py::TestFirmaBounds::test_osoba_i_fragment_formy`, `test_forma_prawna_nie_ginie_przy_przywroc[…S.A.]` (`LYNX-ENGINE-BACKLOG`).
- `tests/test_pseudominizer.py` na żywym silniku z gałęzi (8765, profil Pawła): 36 passed, 1 failed
  `TestEdgeCases::test_liczby_w_umowie_nie_sa_tokenizowane` — failuje tak samo na silniku main (sprawdzone w tej sesji).
- Zmienione istniejące testy (kontrakt się zmienił, nie łatanie wyniku):
  - `test_pseudominizer.py::TestBug1PublicInstitutions` — było „każda instytucja zakryta INSTYTUCJA”; jest: sama nazwa jawna i nie FIRMA,
    z miejscem/numerem/wydziałem zakryta (źródła w briefie). Usunięte przypadki PPK/PIP/RPO/TK/„Sąd Rejonowy” bez miejsca.
  - `test_map_fidelity.py` — fikstura „Beta Grupa (Polska)” → „Betanex Grupa (Polska)”: test sprawdza podmianę całych wyrazów; nazwa
    z samych polskich słów bez formy przestała być FIRMA (koszt z zasady 1), nazwa z dowodem zachowuje sens testu.

## Uwagi dla audytu
- Przy prototypie złapane i poprawione: `^` w `_ROLE_HEAD_RE` przy `match(text, pos)` nie kotwiczy w `pos` (słowo roli nie było
  zdejmowane); „J. S.C.” (inicjały) nie może przejść na FIRMA przez zdjęcie „J. ” jako numeracji; JDG z imieniem o znaczeniu
  pospolitym — dowód `is_jdg` (wcześniej 4 ciche FIRMA rodo w GOLD test na v7, teraz 0).
- `firma_proof` nie usuwa OSOBA; OSOBA z formą prawną i wyrazem ≥3 litery przechodzi na FIRMA (jak w `_process_ner`).
- Podmiana FIRMA bez wielkości liter dotyczy tylko tokenów FIRMA (`_whole(value, ci)`), OSOBA bez zmian.
