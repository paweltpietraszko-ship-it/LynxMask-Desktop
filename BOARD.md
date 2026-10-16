# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC (LynxMask Desktop)

Każda nowa instancja Architekta czyta najpierw `ARCHITECT_START_HERE.md`; Codexa — `AGENTS.md` i `CODEX_START_HERE.md`; CC — `CLAUDE.md`.

Dziennik przekazań: kto, co, na jakim SHA, gdzie leży raport. Bez ustaleń produktowych i decyzji właściciela — te trafiają do `tasks/<id>/brief.md` / `arch/`.

Statusy (dokładnie pięć):

- `READY_FOR_CODEX` — czeka na precheck/audyt Codexa.
- `CODEX_IN_PROGRESS` — Codex pracuje.
- `CODEX_REPORTED` — raport gotowy pod wskazaną ścieżką.
- `OWNER_DECISION_NEEDED` — utknęło na decyzji właściciela.
- `READY_FOR_ARCHITECT` — FINDING/dowody gotowe, czeka na brief architekta.

Nowy wiersz dopisuje autor przekazania; zmianę statusu wpisuje ten, kto kończy etap. Zamknięty wiersz usuwa ten, kto go zamyka (historia zostaje w `git log -p BOARD.md`).

| ID | Autor | Odbiorca | Branch | Exact SHA | Status | Wiadomość |
|---|---|---|---|---|---|---|
| LYNX-DICT-LEAKTEST | CC | Architekt | -- (brief do napisania) | -- | READY_FOR_ARCHITECT | **Propozycja OWNERA (do oceny, nie decyzja):** test szczelności na dużych słownikach imion/nazwisk/miast + słownik „zawsze maskuj" dołączony do programu z form, które silnik przepuszcza. Wstępny kierunek D1–D3 (rekomendacje CC wybrane przez OWNERA: miasta tylko w adresie; nazwiska-słowa pospolite tylko w kontekście; słownik w programie, nie w profilu) i ocena CC: `arch/PROPOSAL_2026-10-16_SLOWNIK_SZCZELNOSCI.md`. Zależy od LYNX-T01, T03, T04 (`arch/FINDING_2026-10_AUDYT.md` §6). UWAGA: „czarny słownik" OWNERA ≠ `ner_blocklist.py` (to lista NIE-maskuj). |
| LYNX-OWNER-QUESTIONS | Architekt | Paweł | `main` | `6336f86148c691da3009f7e7749e1255c9c8ff28` | OWNER_DECISION_NEEDED | Pięć pytań z opcjami i rekomendacją w [`arch/PLAN_2026-10.md`](arch/PLAN_2026-10.md) §OWNER_DECISION_NEEDED: S2 tokeny/taksonomia, seed, Express bez nazwisk, szyfrowanie profilu, reguła doboru słownika. Brak decyzji — żadnych zmian S2 ani seed/T14. |
| LYNX-T01-NER-PREFIX | Codex | Architekt | `task/LYNX-T01-NER-PREFIX` | `851bc26607bd8615afac7cc94ae6df8e31f8c91d` | CODEX_REPORTED | Precheck Codexa 2026-10-16: **PASS PREIMPLEMENTATION** na wskazanym exact SHA. Raport: `tasks/LYNX-T01-NER-PREFIX/round_01/tests/tests_r1.txt` na branchu Tasku, commit `09d989f`. Istniejący owner, bez nowego zakresu; bez testów (brief-only). Do CC po przekazaniu Architekta. |
| LYNX-T02-CORS-EXPRESS | Codex | Architekt | `task/LYNX-T02-CORS-EXPRESS` | `c14c71028b0b3fc3ff8682db2729fa65f86b2865` | CODEX_REPORTED | Precheck Codexa 2026-10-16: **2 braki kontraktu**, bez PASS/FAIL kodu. Raport: `tasks/LYNX-T02-CORS-EXPRESS/round_01/tests/tests_r1.txt` na branchu Tasku, commit `5c78dc8`. Do Architekta: (1) obecne UI Express używa `/preview`, nie `/preview-express`, więc ograniczenie tokenu koliduje z działającym UI i OUT_OF_SCOPE; (2) określić dozwolone Originy i dowód dla wydania Tauri. Bez testów; ponowny precheck tylko tych dwóch punktów. |
| LYNX-T03-TOKEN-ALLOC | Codex | Architekt | `task/LYNX-T03-TOKEN-ALLOC` | `9edf872895be864241b6ff86b3a62c9947e26979` | CODEX_REPORTED | Precheck Codexa 2026-10-16: **PASS PREIMPLEMENTATION** na wskazanym exact SHA. Raport: `tasks/LYNX-T03-TOKEN-ALLOC/round_01/tests/tests_r1.txt` na branchu Tasku, commit `d682bfc`. Istniejący alokator i szew NER, S2 bez zmian; bez testów (brief-only). Do CC po przekazaniu Architekta. |
