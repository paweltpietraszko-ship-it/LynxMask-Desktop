# LYNX-STARTUP-COMPONENTS — start tylko wtedy, gdy każdy element ochrony naprawdę działa

STATUS: cc_proposal pełniący rolę briefu, **obieg skrócony na polecenie Pawła**: CC → Codex precheck (przed kodem) → CC implementacja → Codex audyt exact-SHA → merge na słowo Pawła. Architekt dostaje informację w BOARD.
POCHODZENIE: BOARD `LYNX-STARTUP-COMPONENTS` (finding CC 2026-10-18), diagnoza M1. Paweł: „Musimy naprawić Smoke test od razu, program nie może startować z fałszywym poczuciem, że wszystko działa, to podstawa podstaw systemu bezpieczeństwa dla programu operującego na danych wrażliwych.”
Odpowiedzi Pawła na pytania CC (2026-10-18): przy niepowodzeniu którejkolwiek próby — **zawsze blokada startu** (bez trybu „działa częściowo”); obieg skrócony; rozmiar ok. 220 linii zaakceptowany przed kodem.
PRODUCT_TRUTH: `arch/spec.md` S3 (fail-closed), S5 (bez PII w logach). Brak zmian S2/S4.

## Stan dziś (main `4c2e57e`, `_lifespan` w `pseudominizer_api.py`)
Smoke test (`smoke_test.py`) sprawdza tylko warstwy regex na syntetyku. Pozostałe elementy przy błędzie dają **ostrzeżenie w logu, a start trwa dalej**:
| Element | Dziś przy awarii | Skutek dla użytkownika |
|---|---|---|
| SpaCy / NER | import modułu = „załadowany”; model ładowany leniwie przy 1. dokumencie | start „OK”, błąd dopiero przy dokumencie (od FAILCLOSED: odmowa S3) |
| Anonymizer / profil biura | `Anonymizer niedostępny` → `state.anonymizer=None` → warstwy `trie` i `validation` pomijane | słownik biura po cichu nie działa |
| pyahocorasick (trie) | `trie nie zbudowane` (ostrzeżenie) | jw. |
| Morfeusz | tryb czytany z cache `hardware_profile.json` bez sprawdzenia działania; BLOCKED → „tryb degraded” | odmiany nazw z profilu niewykrywane |
| Output Guard | brak importu → `_GUARD_AVAILABLE=False` → `_apply_guard` przepuszcza wynik bez sprawdzenia | **sprzeczne z S3** |
| crypto_selftest | FAIL → tylko log, `/health crypto_ok=false` | archiwum na niesprawdzonym szyfrowaniu |
Dodatkowo (ta sama klasa — fałszywy obraz stanu): `api_token.txt` jest zapisywany na początku `_lifespan`, PRZED smoke testem. Gdy smoke test przerwie start, plik z tokenem zostaje → aplikacja (`App.tsx`) odczytuje token i nie pokazuje `CrashScreen` (czyta `startup_error.json` tylko gdy tokenu brak). Ekran awarii praktycznie się nie pojawia.

## Kontrakt
1. Przy starcie backend wykonuje próbę FUNKCJONALNĄ (na syntetyku, nie sam import) każdego elementu:
   - **PIPELINE**: istniejący `smoke_test.run_smoke_test()` bez zmian;
   - **GUARD**: `_GUARD_AVAILABLE` i `guard_output_with_map` blokuje syntetyczny tekst z PESEL (`blocked=True`);
   - **CRYPTO**: `crypto_selftest` zwrócił 0;
   - **NER**: model SpaCy ładowany przy starcie (nie leniwie), `detect_entities` na syntetycznym zdaniu zwraca osobę z syntetycznym imieniem i nazwiskiem;
   - **PROFIL**: `state.anonymizer` istnieje, `ahocorasick` importowalne, a przy niepustym profilu `anon_map.load_trie()` zwraca automat;
   - **MORFEUSZ**: tryb ≠ BLOCKED **oraz** `get_forms` dla syntetycznego nazwiska daje co najmniej jedną formę inną niż wejście (dowód, że odmiana działa, a nie tylko wpis w cache).
2. Którakolwiek próba nie przechodzi → **start zablokowany**: `startup_error.json` z kodem `STARTUP-COMPONENTS` i listą nazw elementów, które zawiodły (po polsku, bez treści wyjątków i bez danych — S5), plik `api_token.txt` usunięty, `RuntimeError` (uvicorn kończy start). Aplikacja pokazuje istniejący `CrashScreen`.
3. Wszystkie próby przechodzą → start jak dziś; w logu jedna linia z listą sprawdzonych elementów.
4. Brak trybu „degraded”: żadnego elementu nie wolno pominąć ani zamienić na ostrzeżenie.
5. Profil biura użytkownika tylko odczytywany — próby nie dodają encji ani nie zapisują profilu.

## Szew
Nowy moduł `backend/startup_check.py`: funkcje prób zwracające listę niepowodzeń; `run(state, guard_available, crypto_ok) -> list[str]`. W `_lifespan` istniejący blok `smoke_test` zastąpiony jednym wywołaniem `startup_check` + obsługą niepowodzenia (unlink tokenu, `_write_startup_error`, raise). Bez zmian: `smoke_test.py`, warstwy, `anonymizer.py`, `spacy_ner.py`, UI (CrashScreen istnieje).

TASK_SCOPE:
- backend/startup_check.py
- backend/pseudominizer_api.py
- backend/tests/test_startup_check.py

OUT_OF_SCOPE: UI/Tauri, `smoke_test.py` (bez zmian treści), `anonymizer.py`/`MorfEnv` (cache trybu zostaje — próba funkcjonalna go weryfikuje), `seed_profile` (martwy, osobno M1), HerBERT/słownik nazwisk (dojdą w F2 LYNX-ARCH-CANDIDATES), S4.

## Minimalna falsyfikacja
1. Dla każdego z 6 elementów osobno: wymuszona awaria (brak modułu / wyjątek / BLOCKED / `get_forms` zwraca tylko wejście / Guard nie blokuje / crypto FAIL) → `run` zwraca niepowodzenie z nazwą elementu; `_lifespan` → `RuntimeError`, `startup_error.json` z `STARTUP-COMPONENTS`, brak `api_token.txt`; w pliku i logu brak treści wyjątku.
2. Wszystko sprawne (prawdziwe SpaCy, Morfeusz, Guard, crypto na tej maszynie, profil tymczasowy) → `run` zwraca `[]`, start przechodzi, token zapisany.
3. Prawdziwy start backendu z profilem Pawła: log z listą sprawdzonych elementów; czas startu przed/po (model SpaCy ładuje się teraz przy starcie — raportować).
4. Regresje: `tests/` z działającym backendem, `test_failclosed.py`.

GATE: 2 nowe pliki; `pseudominizer_api.py` (legacy >600) — przyrost minimalny, raportowany (szacunek ±5 linii, logika w nowym module); >150 linii → WYMAGA_DECYZJI (zgoda Pawła na ~220 udzielona przed kodem).
