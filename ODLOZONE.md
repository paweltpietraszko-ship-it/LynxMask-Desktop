# ODLOZONE.md — rzeczy zauważone, świadomie odłożone

Backlog spraw zauważonych przez CC lub Codexa, które NIE trafiają do BOARD.md ani pamięci CC, żeby nie odżywały same w każdej rozmowie. Czytany tylko wtedy, gdy Paweł chce wrócić do tematu. Jeden wpis = jedna sprawa.

Format wpisu:

```
## [data] Tytuł

Krótki opis (2-4 zdania). Dlaczego odłożone. Gdzie szukać kontekstu.
```

---

## 2026-10-16 Integracja z Elnath Rota (mask/unmask dla pytań koordynatora)

Rota potrzebuje bezstanowego `mask(text, known_people) -> {masked_text, mapping}` i `unmask(text, mapping)` działającego na Linuksie bez Tauri/UI. Odłożone decyzją Pawła: najpierw testy LynxMask na dokumentach. Pełny opis: `C:\Projects\LynxMask\MASTER_LynxMask_Desktop.md` §9; strona Roty: `C:\Projects\Elnath Rota\BOARD.md`, ROTA-SERVICE-ONBOARDING.

## 2026-10-16 Redakcja wizualna obrazu (blur twarzy, prostokąty na pikselach)

Istnieje tylko w Mobile. W `PROJEKT_KONTEKST.md` oznaczone jako „wymaga osobnej sesji". Nie ruszane do czasu ustabilizowania silnika tekstowego.

## 2026-10-16 AUD-13/14 PBKDF2 — zmiana iteracji/soli

Zmiana parametrów KDF unieważnia istniejące `mapy.enc`. Wymaga planu migracji przed dystrybucją; nie ruszać bez osobnego Tasku. Źródło: `PROJEKT_KONTEKST.md` → Bezpieczeństwo.
