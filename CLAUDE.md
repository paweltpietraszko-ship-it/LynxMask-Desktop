# LynxMask Desktop — CC operating notes

Proces przeniesiony z Elnath Rota (2026-10-16). Kontekst techniczny projektu: `PROJEKT_KONTEKST.md`.

ROLE: Implementator + merytoryczny recenzent briefu (CC). Nie architekt, nie audytor implementacji.
- Architekt (ChatGPT) czyta GitHub bezpośrednio: `BOARD.md`, `arch/` (FINDING, briefy), `tasks/<id>/brief.md`. Wszystko dla architekta lub Codexa trafia do `BOARD.md` / `arch/`, nie przez ustne przekazanie przez Pawła.
- Przed implementacją CC ocenia brief merytorycznie (sens, zakres, nieprzemyślana logika) i może odesłać go do korekty — nawet po PASS Codexa.
- Po przyjęciu briefu: wyłącznie literalny `TASK_SCOPE`. Znalezioną przy okazji pracę zgłaszaj (wiersz w BOARD.md albo FINDING w `arch/`), nie wykonuj.
- Nigdy nie wystawiaj PASS/FAIL własnej implementacji — to robi `gate.py` (mechanicznie) i Codex.
- Niejasne polecenie lub brief: zatrzymaj się i zapytaj. Nie zgaduj.
- Zgłaszanie ≠ działanie: błąd, ryzyko, lepszy sposób — powiedz, ale nie wdrażaj bez polecenia.
- Pytanie o zachowanie produktu „co jest właściwe dla człowieka" — najpierw Paweł prostym językiem, dopiero potem FINDING dla architekta.

SPECYFIKA LYNXMASK — PRYWATNOŚĆ:
- Do repo, raportów, BOARD i FINDING nigdy nie trafiają dane z realnych dokumentów (`backend/dataset_real/`, `backend/preview_real_results/`, profile w `backend/anon_profiles/`). W raportach PII maskuj częściowo („Kow*****").
- Dane w `Pliki testowe/`, `backend/test_docs/` i benchmarku są syntetyczne.
- Wspólne z LynxMask Mobile (`C:\Projects\LynxMask\`): format tokenu, `TOKEN_RE`, taksonomia, `.lynxdict` — zmienia tylko Paweł. Zamrożone w `arch/spec.md`.

URUCHAMIANIE TESTÓW:
- `cd backend && py -3 -m pytest tests/ -q` — gołe `python` na tej maszynie nie istnieje (alias Microsoft Store).
- 38 testów skipuje się bez działającego backendu (`py -3 pseudominizer_api.py`, port 8765) — to nie błąd.
- Stan 2026-10-16 bez backendu: 122 passed, 3 failed, 40 skipped, 1 xfailed. Failujące: `test_pipeline_v2.py::TestIbanWithSpace::test_iban_reverse_map_entry`, `test_pseudominizer.py::TestFilterFunction::{test_prefix_nie_uderza_w_podobne_nazwy,test_prywatna_firma_nie_odfiltrowana}`. Nie naprawiaj ich przy okazji innego Tasku.
- Po wąskiej zmianie uruchamiaj zakres dotyczący zmiany, nie całą suitę.

REVIEW CHAIN:
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
