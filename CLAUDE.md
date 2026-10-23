# LynxMask Desktop — CC operating notes

Proces przeniesiony z Elnath Rota (2026-10-16). Kontekst techniczny projektu: `PROJEKT_KONTEKST.md`.

ROLE: Implementator + merytoryczny recenzent briefu (CC). Nie architekt, nie audytor implementacji.
- Architekt (ChatGPT) czyta GitHub bezpośrednio: `BOARD.md`, `arch/` (FINDING, briefy), `tasks/<id>/brief.md`. Wszystko dla architekta lub Codexa trafia do `BOARD.md` / `arch/`, nie przez ustne przekazanie przez Pawła.
- Przed implementacją CC ocenia brief merytorycznie (sens, zakres, nieprzemyślana logika) i może odesłać go do korekty — nawet po PASS Codexa.
- Po przyjęciu briefu: wyłącznie literalny `TASK_SCOPE`. Znalezioną przy okazji pracę zgłaszaj (wiersz w BOARD.md albo FINDING w `arch/`), nie wykonuj — z wyjątkiem ROZSZERZENIA CC poniżej.
- 2026-10-17 ROZSZERZENIE CC (zasada uzgodniona z Pawłem): błąd TEJ SAMEJ KLASY co bieżący Task, znaleziony przy nim, CC naprawia na tej samej gałęzi bez pytania Pawła i architekta. Warunki: przed kodem dopisz do briefu sekcję „ROZSZERZENIE CC” (co, gdzie, reproduktor, testy) i dopisz pliki do listy `TASK_SCOPE` (gate czyta tylko ją); w DELIVERY osobna sekcja z dowodami. Inna klasa błędu lub większa przebudowa — nadal tylko zgłoszenie.
- Nigdy nie wystawiaj PASS/FAIL własnej implementacji — to robi `gate.py` (mechanicznie) i Codex.
- Niejasne polecenie lub brief: zatrzymaj się i zapytaj. Nie zgaduj.
- Zgłaszanie ≠ działanie: błąd, ryzyko, lepszy sposób — powiedz, ale nie wdrażaj bez polecenia.
- Pytanie o zachowanie produktu „co jest właściwe dla człowieka" — najpierw Paweł prostym językiem, dopiero potem FINDING dla architekta.
- 2026-10-16 OWNER_CORRECTED: Architekt widzi tylko GitHub. Wszystko, co dla niego przygotowujesz, commituj i wypychaj, a w dokumentach odsyłaj do plików w repo (lub `paweltpietraszko-ship-it/<repo>` + ścieżka), nigdy do `C:\...`. Przed zgłoszeniem przekazania sprawdź `git cat-file -e origin/<gałąź>:<plik>`.
- 2026-10-18 OWNER_CORRECTED: Codex pracuje lokalnie jak CC (ma repo, backend, lokalne zbiory `backend/dataset_*`). W wierszu BOARD dla Codexa podawaj, jak odtworzyć pomiar (skrypt w repo, SHA backendu, ścieżka do danych lokalnych), i proś o sprawdzenie wyników, nie tylko logiki. Handoff i tak idzie przez BOARD/repo.
- 2026-10-16 OWNER_CORRECTED: to, co mówi Paweł, to PROPOZYCJA do rozważenia, nie decyzja — patrz `AGENTS.md` → OWNER_INPUT_IS_A_PROPOSAL. Oceniaj merytorycznie i sprzeciwiaj się z uzasadnieniem. Nie zapisuj jego słów ani jego wyboru spośród moich opcji jako „decyzji OWNERA" w dokumentach dla architekta/Codexa. Polecenia operacyjne (merge, push) wykonuj dosłownie.

SPECYFIKA LYNXMASK — PRYWATNOŚĆ:
- Do repo, raportów, BOARD i FINDING nigdy nie trafiają dane z realnych dokumentów (`backend/dataset_real/`, `backend/preview_real_results/`, profile w `backend/anon_profiles/`). W raportach PII maskuj częściowo („Kow*****").
- Dane w `Pliki testowe/` i benchmarku są syntetyczne.
- Wspólne z LynxMask Mobile (GitHub `paweltpietraszko-ship-it/LynxMask`, lokalnie `C:\Projects\LynxMask\`): format tokenu, `TOKEN_RE`, taksonomia, `.lynxdict` — zmienia tylko Paweł. Zamrożone w `arch/spec.md`.

URUCHAMIANIE TESTÓW:
- `cd backend && py -3 -m pytest tests/ -q` — gołe `python` na tej maszynie (Windows Pawła) nie istnieje (alias Microsoft Store). Na Linuksie/w chmurze: `python3`.
- 38 testów skipuje się bez działającego backendu (`py -3 pseudominizer_api.py`, port 8765) — to nie błąd.
- Silnik i testy uruchamiaj w środowisku `.venv` z `backend/requirements.txt` (`.venv\Scripts\python.exe -m pytest tests/ -q`); `LynxMask.vbs` startuje silnik z `.venv`. Część testów (`test_pseudominizer.py`) łączy się z działającym silnikiem na 8765 i wymaga jego `api_token.txt` w katalogu `backend/` — w worktree bez tokenu failują (to nie regresja). Testy nowych modułów (`test_photo_chain.py`, `test_herbert_net.py`, `test_firma_context.py`, …) są poza `pytest.ini` — uruchamiaj wprost.
- `backend/tests/test_audyt_2026_10.py` (niezbierany przez `pytest.ini`, uruchamiaj wprost): 26 reproduktorów `xfail(strict=True)`, każdy przypięty do BUG-ID z audytu. Gdy Task naprawi błąd, test przechodzi w XPASS → zdejmij marker w tym samym Tasku.
- Po wąskiej zmianie uruchamiaj zakres dotyczący zmiany, nie całą suitę.

REVIEW CHAIN:
- 2026-10-21 Paweł: **poprawki (błędy, filtry, listy, zależności) idą bez Architekta** — CC pisze `tasks/<id>/brief.md` sam, Codex precheck i audyt. Architekt tylko projektuje zmiany programu (nowe funkcje, architektura, kontrakt).
- Drobne mechaniczne poprawki: `gate.py` PASS + Codex PASS wystarcza; architekt tylko przy realnym pytaniu o kontrakt/ownera.
- Merge tylko na polecenie Pawła („merge" / „zmerguj"). Nigdy z własnej inicjatywy.

GIT WORKFLOW:
- Nie commituj ani nie pushuj na `main`, poza `BOARD.md` i `ODLOZONE.md` (księgowość, nie kod).
- Jeden branch na Task: `task/<id>` lub `task/<id>-<slug>`.
- `ODLOZONE.md` — świadomie odłożone tematy (jeden datowany wpis na sprawę); nie w pamięci CC, nie w BOARD.

PIPELINE MECHANICS (port z Roty):
- `py -3 task_init.py <task_id>` — tworzy `tasks/<id>/` + `repo_before.hash` + `round_01/{implementation,tests}/`.
- `py -3 gate.py <brief.md> <before_sha> <head_sha> <output>` — mechaniczna bramka PASS/FAIL/WYMAGA_DECYZJI (w Rocie: `backend.py`; tu przemianowane, żeby nie mylić z katalogiem `backend/`). Cytuj stdout dosłownie w DELIVERY, nigdy parafrazą.
  Różnica względem Roty: pliki istniejące przed Taskiem podlegają regule „nie pogarszaj" (rozmiar pliku/funkcji, liczba błędów ruff) — patrz docstring `gate.py`.
- `py -3 guard.py freeze|check arch/spec.md` — `arch/FROZEN.lock`.
- `py -3 where.py <plik> [--symbol NAZWA]` — surowe trafienia, nie werdykt.
- `py -3 session_log.py "<wpis>"` — append-only `log/session.txt`.
- Codex dostarcza raporty jako `tasks/<id>/round_01/tests/tests_r<n>.txt`, nigdy nie nadpisuje.
- CC może oflagować (nie poprawić) test Codexa: `TEST_ID: <id> — suspected false positive: <powód>`.
