# ODLOZONE.md — rzeczy zauważone, świadomie odłożone

Backlog spraw zauważonych przez CC lub Codexa, które NIE trafiają do BOARD.md ani pamięci CC, żeby nie odżywały same w każdej rozmowie. Czytany tylko wtedy, gdy Paweł chce wrócić do tematu. Jeden wpis = jedna sprawa.

Format wpisu:

```
## [data] Tytuł

Krótki opis (2-4 zdania). Dlaczego odłożone. Gdzie szukać kontekstu.
```

---

## 2026-10-16 Integracja z Elnath Rota (mask/unmask dla pytań koordynatora)

Rota potrzebuje bezstanowego `mask(text, known_people) -> {masked_text, mapping}` i `unmask(text, mapping)` działającego na Linuksie bez Tauri/UI. Odłożone decyzją Pawła: najpierw testy LynxMask na dokumentach. Pełny opis: GitHub `paweltpietraszko-ship-it/LynxMask` (gałąź master), plik `MASTER_LynxMask_Desktop.md` §9; strona Roty: GitHub `paweltpietraszko-ship-it/elnath-rota`, plik `BOARD.md`, wiersz ROTA-SERVICE-ONBOARDING.

## 2026-10-17 Douczanie modelu NER spaCy (fine-tuning)

Pomysł z `MASTER_LynxMask_Desktop.md` („Fine-tuning (nie przed stabilizacją)”); OWNER 2026-10-17: „to ważne”, pamięta
też pomysł poprzednika na „sprytną drogę na skróty” — źródła NIE znaleziono (przeszukane MASTER Desktop/Mobile, TODO, docs,
pamięć sesji Mobile/pseudominizer). Znane skróty, które pasują do opisu (do rozpoznania przez OWNERA):
(a) **EntityRuler** — wzorce/słownik wpięte w potok spaCy jako dodatkowy rozpoznawacz, bez treningu;
(b) **etykiety „za darmo” (weak supervision)** — zdania oznaczone automatycznie przez nasz silnik + słownik + ground truth
generatora, użyte jako dane treningowe (ryzyko: model uczy się generatora i naszych błędów);
(c) **etykietowanie przez LLM** na danych syntetycznych (por. `llm_classifier.py` w MASTER Desktop), potem trening lokalny.
Kolejność wg CC: pomiar M1/M2 (LYNX-DICT-LEAKTEST) → reguły kontekstowe (LYNX-CONTEXT-ANCHORS) → douczenie tylko jeśli M1
pokaże istotną grupę wycieków bez kotwicy. Dane treningowe: syntetyczne, z nazwiskami rozłącznymi ze słownikiem; ocena na
zbiorze rozłącznym; mierzyć „zapominanie” (FIRMA/miejsca) przed/po. Bez realnych dokumentów w zbiorze treningowym (RODO).

## 2026-10-16 Redakcja wizualna obrazu (blur twarzy, prostokąty na pikselach)

Istnieje tylko w Mobile. W `PROJEKT_KONTEKST.md` oznaczone jako „wymaga osobnej sesji". Nie ruszane do czasu ustabilizowania silnika tekstowego.

## 2026-10-16 AUD-13/14 PBKDF2 — zmiana iteracji/soli

Zmiana parametrów KDF unieważnia istniejące `mapy.enc`. Wymaga planu migracji przed dystrybucją; nie ruszać bez osobnego Tasku. Źródło: `PROJEKT_KONTEKST.md` → Bezpieczeństwo.
