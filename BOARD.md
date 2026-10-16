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
| LYNX-T01-NER-PREFIX | Architekt | Codex | `task/LYNX-T01-NER-PREFIX` | `851bc26607bd8615afac7cc94ae6df8e31f8c91d` | READY_FOR_CODEX | Precheck [`brief`](https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/task/LYNX-T01-NER-PREFIX/tasks/LYNX-T01-NER-PREFIX/brief.md): słownik przed filtrem OSOBA, minimalny scope, reproduktory prefiksu i przymiotnika; zależność planu. |
| LYNX-T02-CORS-EXPRESS | Architekt | Codex | `task/LYNX-T02-CORS-EXPRESS` | `c14c71028b0b3fc3ff8682db2729fa65f86b2865` | READY_FOR_CODEX | Precheck [`brief`](https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/task/LYNX-T02-CORS-EXPRESS/tasks/LYNX-T02-CORS-EXPRESS/brief.md): ograniczenie Express do endpointu, CORS, brak pustego tokenu; potwierdzić Origin interfejsu. |
| LYNX-T03-TOKEN-ALLOC | Architekt | Codex | `task/LYNX-T03-TOKEN-ALLOC` | `9edf872895be864241b6ff86b3a62c9947e26979` | READY_FOR_CODEX | Precheck [`brief`](https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/task/LYNX-T03-TOKEN-ALLOC/tasks/LYNX-T03-TOKEN-ALLOC/brief.md): jedyny alokator i brak kolizji mapy, bez zmian S2. |
