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
| LYNX-CLOUD-AUDIT | CC (chmura) | Architekt | `audyt/2026-10` | `ecb20f2e1cdb3077181e743637f378e9466e8de7` (audyt), `05077c7d96146e205be4f5ddb413007bde469fd7` (port Mobile) | READY_FOR_ARCHITECT | Raport: `arch/FINDING_2026-10_AUDYT.md` (gałąź `audyt/2026-10`; dowody `audyt/logs/`, 23 reproduktory xfail w `backend/tests/test_audyt_2026_10.py`). Top 3 ryzyka: (1) **BUG-NER-PREFIX-FILTER** — filtr prefiksów blocklisty (ulice/miejscowości) odrzuca osoby wykryte przez spaCy: 20/21 pominiętych OSOBA w benchmarku, 30% form nazwisk jawnie w zdaniach koordynatora; (2) **BUG-EXPRESS-TOKEN-SCOPE + CORS `*`** — strona WWW może pobrać `/express/token` i odczytać słownik encji/archiwum; (3) **BUG-TOKEN-COLLISION** — encja w profilu + NER = dwie osoby pod jednym tokenem, Przywracanie wstawia złą osobę. Też: BUG-ONBOARD-BATCH potwierdzony (seed słownika martwy). 3 „znane faile” to realne błędy, nie nieaktualne testy. Lista kandydatów na Taski w §6 raportu. **2026-10-16 — drugi raport:** `arch/FINDING_2026-10_MOBILE_PORT.md` (analiza portu Mobile→Desktop, prototyp AnchorEngine w `audyt/`). Najwięcej daje zasada Mobile „słownik imion/nazwisk przed filtrem” (benchmark OSOBA 85→105/106, recall 88,2→92,1%, 0 nowych FP; Rota 30%→5% form jawnie), potem IBAN_EARLY (3/3 krytyczne IBAN, CLR 7,7→6,1% w pakiecie) i zakotwiczona normalizacja OCR; sam AnchorEngine +1 encja/+31 FP — portować wybiórczo, Rundy 2 nie odtwarzać. Skorygowano BUG-TOKEN-RE-SPEC w pierwszym raporcie. OWNER_DECISION: rozjazd kontraktu tokenu/taksonomii (MASTER Mobile §9 vs kod Mobile vs spec S2). |
| LYNX-DICT-LEAKTEST | CC | Architekt | -- (brief do napisania) | -- | READY_FOR_ARCHITECT | **Propozycja OWNERA (do oceny, nie decyzja):** test szczelności na dużych słownikach imion/nazwisk/miast + słownik „zawsze maskuj" dołączony do programu z form, które silnik przepuszcza. Wstępny kierunek D1–D3 (rekomendacje CC wybrane przez OWNERA: miasta tylko w adresie; nazwiska-słowa pospolite tylko w kontekście; słownik w programie, nie w profilu) i ocena CC: `arch/PROPOSAL_2026-10-16_SLOWNIK_SZCZELNOSCI.md`. Zależy od LYNX-T01, T03, T04 (`arch/FINDING_2026-10_AUDYT.md` §6). UWAGA: „czarny słownik" OWNERA ≠ `ner_blocklist.py` (to lista NIE-maskuj). |
