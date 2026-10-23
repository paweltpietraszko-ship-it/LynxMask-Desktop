# LYNX-OSOBA-LAYOUT — osoba z układu pisma w silniku; Guard pyta tylko o słowa nieopisane

23.10.2026, CC. Poprawka bez Architekta (reguły wykrywania + filtr Guarda), na polecenie Pawła 23.10 („działaj dalej, jeśli trzeba merge i push — rób”).
Kolejność wyjątkowo: kod powstał na prototypach (scratchpad CC, wersje v6–v10) przed briefem — Codex robi precheck briefu i audyt kodu w jednym kroku.

## Problem (stan main `b50655a`)
- Guard był drugim silnikiem: R1 zgadywał osoby w całym tekście (słownik/końcówki/kanał `released`) → śmieci w pytaniach („Góra”, „Data”, „Dział”).
- Silnik nie rozpoznawał osób oczywistych z układu pisma: „Imię i nazwisko:\nZoryana Fortuńska”, „NABYWCA:\nRakesh Kiljanek”,
  wiersz z nazwiskiem nad „PESEL:”, oraz reszty osoby za tokenem imienia („OSOBA_001 Kiljanek” — imię zakryte, nazwisko jawne).
- Pomiar main (zbiór Pawła `testset_owner`, stress 300 dok.): osoby widoczne w wyniku 21 cicho + 34 z pytaniem / 412.

## Model (uzgodniony z Pawłem 23.10 słowami; CC ocenił i zmierzył)
- Silnik decyduje, co zakryte. Guard nie analizuje osób w całym tekście.
- Guard pyta o słowo z wielkiej litery tylko gdy:
  (a) słownik (Morfeusz) zna je **wyłącznie** jako imię/nazwisko, a silnik go nie zakrył („Kasprzak”), albo
  (b) nikt go nie opisał: Morfeusz nie zna (ign), nie jest imieniem, nie ma go na białej liście (316 słów, zatwierdzona 23.10)
      ani wśród skrótów z pism, i nie jest zwykłym słowem zniekształconym przez OCR (brak ogonków; jedna typowa pomyłka znaku).
- Słowa obce zostają pytaniem — użytkownik decyduje („Zawsze jawne”). Słowa ze zwykłym znaczeniem („Kawa”, „Termin”) są dla Guarda niewidzialne.
- R2–R5, wzorce HIGH/MEDIUM i MAP_LEAK bez zmian.

## Zmiany
1. **`backend/guard_residue.py` — nowe R1** `_unknown(text, analyse)`; `_only_person_name`, `_ocr_common`, `_ABBR`,
   biała lista jako stała `_WHITELIST` (316 słów z `tasks/LYNX-OSOBA-REDESIGN/evidence_2026-10-23/biala_lista_pesel_zatwierdzona.csv`, gałąź `task/LYNX-OSOBA-REDESIGN`).
   Błąd Morfeusza → pytanie. (Po gate r1: bez osobnego modułu i pliku JSON — limit nowych plików 2.)
2. **`backend/guard_residue.py`**: usunięte stare R1 (`_person_word`, `_r1`, `_released` i ich stałe), `collect_warnings` bez parametru
   `released_words`, źródło R1 = `_unknown`. Plik 270 → ~277 l. (stare R1 −80, nowe R1 z listą +87).
3. **`backend/pipeline.py`**: 2 linie — `collect_warnings(text, guard_values, _allowlist)`; import tylko `start_run`.
   Rejestr `osoba_not_person.released()` zostaje (Guard go nie czyta) — usunięcie martwego kanału = osobna drobna sprawa.
4. **Nowy `backend/person_layout.py`** (silnik, `apply_person_layout(text, allocator, sub_whole)`), wołany na końcu
   `ner_adapter._apply_dictionary_names` (import + zmiana linii `return`; `apply_ner_layer` bez wzrostu). Reguły:
   - wiersz z 2–3 słów z wielkiej litery po etykiecie osoby („Imię i nazwisko:”, „NABYWCA:”, „Wnioskodawca:”, „pomiędzy:”…) albo nad
     wierszem „PESEL”/„zamieszkały”/„data urodzenia”; ta sama etykieta z nazwą w jednym wierszu;
   - znane imię + słowo z wielkiej litery (C3), poza ulicą/patronem („im.”), miejscowością wieloczłonową (`in_city_name`) i gdy pierwsze
     słowo ma zwykłe znaczenie („Rady Miejskiej”, „Danych Osobowych”);
   - słowo tuż za tokenem osoby w tym samym wierszu: gdy Morfeusz zna je jako nazwisko, albo gdy token zakrył samo imię, a słowo
     zamyka nazwę („Sheila Osoba”); słowo nieznane („GmbH”) zostaje — pyta Guard;
   - „Pan/Pani/P./dr/mgr/mec. + słowo” → osoba, poza funkcją także w odmianie (lemat Morfeusza: „Panie Ministrze”, „Pani Radnej”)
     i czasownikiem/przymiotnikiem; małe „p.” (= punkt) nie jest tytułem.

## Czego NIE ma (świadomie)
- Słownik nazwisk PESEL jako dowód bez kotwicy — prototyp v5–v8 wymagał rosnącej listy wyjątków (miasta, „Dział IV”, „w Świerku”,
  złamania linii); wyłączony w v9, nie wchodzi do repo.
- Gałąź `task/LYNX-GUARD-R1-FILTERS` (filtry starego R1) staje się zbędna — do zamknięcia po merge tego Tasku.
- Ciche FIRMA (GOLD dev 20 / test 52) — bez zmian, następny temat.

TASK_SCOPE:
- backend/person_layout.py
- backend/guard_residue.py
- backend/pipeline.py
- backend/layers/ner_adapter.py
- backend/tests/test_osoba_layout.py
- backend/tests/test_guard_residue.py
- backend/tests/test_osoba_handoff.py
- backend/tests/test_guard_allowlist_s5.py
- backend/tests/test_map_fidelity.py
- backend/tests/test_osoba_pack4.py
- tasks/LYNX-OSOBA-LAYOUT/brief.md
- tasks/LYNX-OSOBA-LAYOUT/repo_before.hash
- tasks/LYNX-OSOBA-LAYOUT/round_01/implementation/DELIVERY.md

Szacunek: kod ~230 l. nowych, ~90 l. usuniętych; testy ~130 l. (Paweł 23.10: bez szacunku, każdy plik ≤600 l.).

## Odbiór
- `tests/test_osoba_layout.py` (nowy): osoby z układu, reszta za tokenem, Pan + słowo, funkcje w odmianie, przypadki „nie osoba”,
  Guard pyta / nie pyta, biała lista, pusta lista nie wycisza, awaria Morfeusza.
- Zaktualizowane testy starego R1 (`test_guard_residue`, `test_osoba_handoff`, `test_guard_allowlist_s5`, `test_osoba_pack4`, `test_map_fidelity`): przypadki zależne od
  zgadywania R1 („Kawa”, „Pan Rogalik”, kanał released) przeniesione na nowy model — opis zmian w DELIVERY.
- Regresja: te same pliki testów na main i na gałęzi — bez nowych faili.
- Pomiar (powtarzalny, patrz DELIVERY): GOLD dev/test (`%TEMP%\lynx_cc_review\gold\human_view.py`, lokalnie), `testset_owner/run_testset.py`,
  ślepy zbiór 600 nowych dokumentów (generator Mobile, ziarno 2026, nikt nie oglądał błędów przed pomiarem).
