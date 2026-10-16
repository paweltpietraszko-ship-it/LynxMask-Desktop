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
| LYNX-OWNER-QUESTIONS | Paweł (zapis CC) | Architekt | `main` | `6336f86` | OWNER_DECIDED | **OWNER_DECISION 2026-10-16** (po ocenie Architekta i CC, dosłownie: „Zgoda na rekomendacje”): pytania A–E z `arch/PLAN_2026-10.md` rozstrzygnięte zgodnie z rekomendacjami Architekta — A(1) zostaje działający format `KATEGORIA_NNN`, korekta opisu MASTER Mobile §9, lista kategorii i reguła TOKEN_RE do uzgodnienia w T08; B(2) osobny słownik programu, profil tylko dla danych użytkownika; C(2) Express bez pewnego rozpoznania osoby → brak wyniku do skopiowania; D(1) szyfrowanie profilu z migracją i kopią, osobny projekt; E(2) test + kuratorowana lista kontekstowa. **Priorytet OWNERA (ten sam dzień):** „nie naprawiamy LynxMask na tyle by pracował z Rotą, tylko naprawiamy go na ile się da, by był też samodzielnym programem” — kryterium wyboru i zakresu Tasków to jakość samodzielnej aplikacji; integracja z Rotą pozostaje odłożona (`ODLOZONE.md`). |
| LYNX-T01-NER-PREFIX | CC | Architekt / Codex (do wiadomości) | `task/LYNX-T01-NER-PREFIX` | `069df2f` | CC_ACCEPTED | Ocena CC: **PRZYJĘTY** z trzema doprecyzowaniami wykonania w obecnym TASK_SCOPE (Morfeusz jako główne potwierdzenie osoby; pomiar PASS na nazwiskach spoza słownika; przy braku Morfeusza nie odrzucać nierozstrzygniętej OSOBA): `tasks/LYNX-T01-NER-PREFIX/round_01/cc_review_r1.md`. Brak sprzeciwu Architekta/Codexa → CC implementuje. Precheck Codexa: PASS (`09d989f`). |
| LYNX-T02-CORS-EXPRESS | CC | Architekt | `task/LYNX-T02-CORS-EXPRESS` | `1dce4ff` | READY_FOR_ARCHITECT | Ocena CC: **ZWROT DO KOREKTY** (jedna runda): B1 — sam CORS nie spełnia celu, brak kontroli `Host` (DNS rebinding: same-origin GET `/express/token` bez `Origin`) → dodać allowlistę Host w tym samym pliku; B2 — PASS wymaga pomiaru Origin z wydania, a build release nie przechodzi (BUILD-TSC) → przenieść część TS z T10 przed T02 albo przenieść pomiar do T10. `tasks/LYNX-T02-CORS-EXPRESS/round_01/cc_review_r1.md`. Precheck Codexa r2: PASS (`5d4c5c5`). |
| LYNX-T03-TOKEN-ALLOC | CC | Architekt | `task/LYNX-T03-TOKEN-ALLOC` | `52b4010` | READY_FOR_ARCHITECT | Ocena CC: **ZWROT DO KOREKTY** (jedna runda): „token zajęty przez profil” — w dokumencie czy w całym profilu? Dziś trie rejestruje tylko tokeny obecne w dokumencie, więc `OSOBA_001` z profilu może dostać inna osoba. CC rekomenduje rezerwację całej przestrzeni profilu → wymaga `pipeline_new.py` lub `layers/trie_layer.py` w TASK_SCOPE + test. `tasks/LYNX-T03-TOKEN-ALLOC/round_01/cc_review_r1.md`. Precheck Codexa: PASS (`d682bfc`). |
