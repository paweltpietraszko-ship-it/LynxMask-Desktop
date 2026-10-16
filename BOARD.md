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
| LYNX-CLOUD-AUDIT | CC | CC (chmura) | `audyt/2026-10` | -- | OWNER_DECISION_NEEDED | Pełny remanent/debug przez Claude Code w chmurze (osobne konto OWNERA). Prompt przygotowany w rozmowie 2026-10-16. Wynik: `arch/FINDING_2026-10_AUDYT.md` na branchu `audyt/2026-10` → potem `READY_FOR_ARCHITECT`. Znalezione przy przenoszeniu procesu (do włączenia w audyt): `backend/anonymizer.py:731,1530` używa `MAX_ONBOARD_BATCH`, którego nie importuje z `anonymizer_init.py:236` → `add_entities_batch` kończy się `NameError` (ruff F821). |
