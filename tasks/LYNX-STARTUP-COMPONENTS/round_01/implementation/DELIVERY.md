# LYNX-STARTUP-COMPONENTS — DELIVERY r1 (CC)

Kod: `4dd79a4` na brief r2 `7fe637d` (Codex PASS PREIMPLEMENTATION `f39e4f5`), gałąź zsynchronizowana z main (`40fed32`).

## Zmiany
- **`backend/startup_check.py` (nowy, 102 linie):** sześć prób funkcjonalnych na syntetyku. `run(state, guard_available, crypto_ok) -> list[str]` zwraca nazwy elementów, które nie przeszły. Wyjątek w próbie oznacza porażkę; do logu trafia tylko nazwa elementu i typ wyjątku (S5).
  - **maskowanie numerów i adresów:** istniejący `smoke_test.run_smoke_test()`;
  - **Output Guard:** `guard_available`, potem `guard_output` na syntetycznym PESEL (`blocked` i `high_hit`, bez `GUARD_ERROR`) oraz `guard_output_with_map` z `known_plain` (`MAP_LEAK`, `error=False`);
  - **szyfrowanie:** wynik `crypto_selftest`;
  - **rozpoznawanie osób (SpaCy):** `detect_entities` znajduje OSOBA „Jan Kowalski”; model ładuje się teraz przy starcie, a nie przy 1. dokumencie;
  - **odmiana nazw (Morfeusz):** tryb native/wsl2 i `get_forms("Kowalski")` zawiera „Kowalskiego”;
  - **profil biura:** `state.anonymizer` istnieje (profil użytkownika wczytany przez `build_anonymizer`, próba niczego na nim nie wywołuje). Na izolowanym profilu tymczasowym `AnonymizerMap(tmp, state.morf_env)` → `add_entity` → `_layer1_trie` zakrywa „Jana Kowalskiego”. Katalog próby jest usuwany w `finally`.
- **`pseudominizer_api.py` (+16/−17, plik 1147 → 1146):** w `_lifespan`:
  - na początku usuwane są stare `startup_error.json` i `api_token.txt`;
  - blok `smoke_test` zastępuje `startup_check.run`;
  - przy porażce: `startup_error.json` (`STARTUP-COMPONENTS`, „Nie przeszły próby startowe: …”) i `RuntimeError`;
  - `api_token.txt` jest zapisywany dopiero po próbach i usuwany po `yield`.
- **`frontend/src/App.tsx`:** zamiast jednej ponownej próby po 4 s jest pętla co 1 s, do 60 prób:
  - **gotowe:** `read_api_token` i `/health` 200 (timeout 2 s);
  - **awaria:** `read_startup_error`, wtedy CrashScreen;
  - **jeszcze startuje:** ekran „Uruchamianie silnika…” (wcześniej „Ładowanie sesji…”);
  - **po 60 próbach:** `STARTUP-NO-RESPONSE`.
  Efekt jest anulowany przy odmontowaniu lub wylogowaniu (`cancelled`). Tauri bez zmian.

## Testy
- **`tests/test_startup_check.py` (nowy, uruchamiany jawnie, poza pytest.ini): 17 passed.**
  - Wszystko sprawne daje `[]`.
  - Każdy element osobno daje porażkę z jego nazwą:
    - smoke zwraca False;
    - wyjątek `guard_output`;
    - Guard blokujący tylko przez `GUARD_ERROR`;
    - SpaCy bez osoby oraz SpaCy z wyjątkiem;
    - Morfeusz zwracający tylko formę podstawową oraz Morfeusz BLOCKED;
    - automat bez dopasowania odmienionej formy;
    - brak modułu SpaCy, anonymizera lub Morfeusza;
    - Guard niezaładowany oraz crypto FAIL.
    Treść wyjątku nie trafia do logu.
  - Profil użytkownika pusty i niepusty: SHA256, rozmiar i mtime wszystkich plików profilu i `hardware_profile.json` przed i po są identyczne, a katalog próby jest usunięty.
  - `_lifespan` przy porażce: `RuntimeError`, `startup_error.json` z `STARTUP-COMPONENTS`, brak `api_token.txt` (stary też usunięty).
  - `_lifespan` przy sukcesie: tokenu nie ma w trakcie prób, po starcie jest nowy, po zamknięciu go nie ma.
- **RED:** testy `_lifespan` na starym `pseudominizer_api.py` dają **2 failed**: „DID NOT RAISE” (start przechodzi mimo nieudanej próby Guarda) oraz token istniejący w trakcie prób.
- **Regresje:** backend z gałęzi na 8765 z profilem Pawła.

  | Zestaw | Wynik |
  |---|---|
  | `tests/` | **167 passed, 2 skipped, 1 xfailed** |
  | `test_startup_check` + `test_failclosed` + `test_layers` + `test_output_guard_adversarial` | **192 passed** |
  | `ruff` | 0 |
  | `tsc --noEmit` | 0 błędów |

- **Prawdziwy start z profilem Pawła** (`ANONYMIZER_PROFILE_DIR`, `HARDWARE_PROFILE` jak w jego uruchomieniu):
  - log: „[STARTUP] próby OK: maskowanie numerów i adresów, Output Guard, szyfrowanie, rozpoznawanie osób (SpaCy), odmiana nazw (Morfeusz), profil biura”;
  - **pliki profilu (`mapa.enc`, `triangulum_keystore.bin`, `trie.pkl`) i `hardware_profile.json` identyczne przed i po dwóch startach** (SHA256, rozmiar, mtime);
  - **czas do `/health` 200: przed 3,1 s → po 15,9 s.** Różnica to wczytanie modelu SpaCy (12,6 s w logu). Wcześniej ten czas przypadał na pierwszy dokument, teraz na start, równolegle z ekranem logowania.
- **UI — scenariusze ręczne (b)–(d) z briefu: NOT_RUN.** Wymagają przebudowy Tauri (`npm run tauri build`), do odbioru okiem Pawła. Scenariusz (a) „start >4 s” zachodzi przy każdym starcie (16 s).

## Ograniczenia
- Usunięcie tokenu po `yield` działa tylko przy łagodnym zamknięciu (Ctrl+C). Twarde zabicie procesu (TaskKill, awaria) zostawia plik. Aplikacja nie uzna go jednak za gotowość, bo wymaga `/health` 200, a nowy start i tak go usuwa.
- Express (`/express/token` z ekranu blokady) pomija pętlę gotowości, jak dotąd. Do czasu przejścia prób port jest zamknięty, więc Express dostaje błąd połączenia, a nie wynik.
- `seed_profile` nadal jest wołany na profilu użytkownika i nadal martwy (`NameError: MAX_ONBOARD_BATCH`), więc niczego nie zapisuje. Poza zakresem (M1).
- Pozostałe ograniczenia jak w briefie (3b): tokeny w innych katalogach wyszukiwania Tauri; stary plik awarii przed startem nowego backendu.

## Gate (dosłownie, bez listy IMPORTERS_FOR_REVIEW)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 4dd79a416f6c4fc1447da743a05766b99378397f
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 294/42 = 7.0:1 (threshold 5:1)
  - TOTAL_LINES: 336 lines changed (threshold 150)
```
Dodanych linii jest 294, zgodnie ze zgodą Pawła („Akceptuję 290”); TOTAL 336 obejmuje 42 usunięte. Plik API zmniejszył się o 1 linię.
