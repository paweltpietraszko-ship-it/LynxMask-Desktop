# LYNX-STARTUP-COMPONENTS — start tylko wtedy, gdy każdy element ochrony naprawdę działa

STATUS: cc_proposal pełniący rolę briefu, **obieg skrócony na polecenie Pawła**: CC → Codex precheck (przed kodem) → CC implementacja → Codex audyt exact-SHA → merge na słowo Pawła. Architekt dostaje informację w BOARD.
POCHODZENIE: BOARD `LYNX-STARTUP-COMPONENTS` (finding CC 2026-10-18), diagnoza M1. Paweł: „Musimy naprawić Smoke test od razu, program nie może startować z fałszywym poczuciem, że wszystko działa, to podstawa podstaw systemu bezpieczeństwa dla programu operującego na danych wrażliwych.”
Odpowiedzi Pawła na pytania CC (2026-10-18): przy niepowodzeniu którejkolwiek próby — **zawsze blokada startu** (bez trybu „działa częściowo”); obieg skrócony; rozmiar ok. 220 linii zaakceptowany przed kodem.
**r2 (po prechecku Codexa `e6ff6a4`, C1–C2):** gotowość startu i zachowanie UI (C1) oraz izolowana próba profilu bez zapisów do profilu użytkownika (C2); GUARD odróżnia detekcję od GUARD_ERROR.
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
   - **GUARD**: `_GUARD_AVAILABLE`; `guard_output` na syntetyku z PESEL → `blocked=True`, `high_hit=True`, powód PESEL (detekcja, nie awaria); `guard_output_with_map(…, known_plain=[syntetyczne imię i nazwisko])` na tekście z tą wartością → `blocked=True` z `MAP_LEAK`, `error=False`. Blokada wyłącznie przez `GUARD_ERROR` = próba NIEUDANA;
   - **CRYPTO**: `crypto_selftest` zwrócił 0;
   - **NER**: model SpaCy ładowany przy starcie (nie leniwie), `detect_entities` na syntetycznym zdaniu zwraca osobę z syntetycznym imieniem i nazwiskiem;
   - **PROFIL**: (a) `state.anonymizer` istnieje — profil użytkownika odszyfrowany i wczytany przez `build_anonymizer` (to już jest odczyt; próba go nie powtarza i NIE woła na nim `load_trie`/`_rebuild_trie`/`add_entity`/`_save`); (b) próba funkcjonalna ścieżki właściciela na IZOLOWANYM profilu syntetycznym: `AnonymizerMap(<katalog tymczasowy>, state.morf_env)` (współdzielony obiekt Morfeusza — bez ponownego wykrywania i bez zapisu `hardware_profile.json`) → `add_entity(<syntetyczne imię i nazwisko>, "OSOBA")` → `Anonymizer(map)._layer1_trie` na syntetycznym zdaniu z ODMIENIONĄ formą (np. dopełniacz) → wynik zawiera token OSOBA i nie zawiera nazwiska; katalog tymczasowy (z własnym keystore) usuwany po próbie. Próba działa tak samo dla pustego i niepustego profilu użytkownika;
   - **MORFEUSZ**: tryb ≠ BLOCKED **oraz** `get_forms` dla syntetycznego nazwiska daje co najmniej jedną formę inną niż wejście (dowód, że odmiana działa, a nie tylko wpis w cache).
2. Którakolwiek próba nie przechodzi → **start zablokowany**: `startup_error.json` z kodem `STARTUP-COMPONENTS` i listą nazw elementów, które zawiodły (po polsku, bez treści wyjątków i bez danych — S5), `RuntimeError` (uvicorn kończy start, port nie jest otwierany), brak `api_token.txt` (pkt 3a).
3. Wszystkie próby przechodzą → start jak dziś; w logu jedna linia z listą sprawdzonych elementów.
3a. **Gotowość (C1).** Plik tokenu jest sygnałem gotowości: `_lifespan` na samym początku usuwa stary `api_token.txt` i stary `startup_error.json`, wykonuje wszystkie próby, a **dopiero po ich przejściu** zapisuje nowy `api_token.txt` (wartości `_API_TOKEN`/`_EXPRESS_TOKEN` mogą powstać wcześniej — liczy się moment zapisu pliku). Przy zamknięciu backendu (po `yield`) plik tokenu jest usuwany, więc zatrzymany backend nie zostawia „gotowości”. Port HTTP (w tym `/health`) otwiera się dopiero po zakończeniu startowej części `_lifespan` (istniejące zachowanie uvicorn).
3b. **UI (C1; istniejący szew: efekt ładowania tokenu po odblokowaniu w `App.tsx`).** Zamiast jednej ponownej próby po 4 s: pętla co 1 s, maks. 60 s, z rozróżnialnymi stanami:
   - **gotowe** = token odczytany przez `read_api_token` **i** `GET /health` odpowiada 200 (stary token przy niedziałającym backendzie nie daje gotowości) → normalny ekran;
   - **awaria** = `read_startup_error` zwraca plik → `CrashScreen` z kodem i listą elementów;
   - **jeszcze startuje** = żadne z powyższych → ekran „Uruchamianie silnika…”, pętla trwa;
   - **brak odpowiedzi** = 60 s bez gotowości i bez pliku awarii → istniejący `STARTUP-NO-RESPONSE`.
   Bez zmian w Tauri (`read_api_token`, `read_startup_error` już istnieją) i bez nowego protokołu.
   Znane ograniczenia (nienaprawiane): `find_token_file` w Tauri przeszukuje też inne katalogi (zmienna środowiskowa, katalog exe, ścieżki dev/legacy) — stary token stamtąd nie da gotowości dzięki warunkowi `/health`, ale nie jest usuwany. Plik awarii z poprzedniego startu jest widoczny, dopóki nowy backend nie wystartuje i go nie usunie (3a) — wtedy CrashScreen pokazuje poprzednią awarię z przyciskiem restartu.
4. Brak trybu „degraded”: żadnego elementu nie wolno pominąć ani zamienić na ostrzeżenie.
5. Profil biura użytkownika: próby nie dodają encji i nie zapisują niczego w katalogu profilu (`mapa.json`/`.enc`, `trie.pkl`, keystore) ani w `hardware_profile.json` — sprawdzalne porównaniem plików (rozmiar, mtime, SHA256) przed i po próbach.

## Szew
Nowy moduł `backend/startup_check.py`: funkcje prób zwracające listę niepowodzeń; `run(state, guard_available, crypto_ok) -> list[str]`. W `_lifespan`: usunięcie starych plików na początku, istniejący blok `smoke_test` zastąpiony jednym wywołaniem `startup_check` + obsługą niepowodzenia (`_write_startup_error`, raise), zapis `api_token.txt` przeniesiony za próby, usunięcie tokenu po `yield`. UI: pętla gotowości w `App.tsx` (3b). Bez zmian: `smoke_test.py`, warstwy, `anonymizer.py`, `spacy_ner.py`, `CrashScreen.tsx`, Tauri.

TASK_SCOPE:
- backend/startup_check.py
- backend/pseudominizer_api.py
- backend/tests/test_startup_check.py
- frontend/src/App.tsx

OUT_OF_SCOPE: Tauri (`main.rs`), `CrashScreen.tsx`, pozostałe UI, `smoke_test.py` (bez zmian treści), `anonymizer.py`/`MorfEnv` (cache trybu zostaje — próba funkcjonalna go weryfikuje), `seed_profile` (martwy, osobno M1), HerBERT/słownik nazwisk (dojdą w F2 LYNX-ARCH-CANDIDATES), S4.

## Minimalna falsyfikacja
1. Dla każdego z 6 elementów osobno: wymuszona awaria (brak modułu / wyjątek / BLOCKED / `get_forms` zwraca tylko wejście / Guard nie blokuje / Guard blokuje wyłącznie przez `GUARD_ERROR` / crypto FAIL / **automat istnieje, ale nie dopasowuje odmienionej formy**) → `run` zwraca niepowodzenie z nazwą elementu; `_lifespan` → `RuntimeError`, `startup_error.json` z `STARTUP-COMPONENTS`, **brak `api_token.txt`**; w pliku i logu brak treści wyjątku.
2. Wszystko sprawne (prawdziwe SpaCy, Morfeusz, Guard, crypto, profil tymczasowy) → `run` zwraca `[]`, token zapisany dopiero po próbach; po wyjściu z `_lifespan` token usunięty.
3. **Brak zapisów do profilu użytkownika:** profil tymczasowy niepusty (z encją) i pusty — SHA256/rozmiar/mtime wszystkich plików katalogu profilu i `hardware_profile.json` przed i po `run` identyczne; katalog tymczasowy próby usunięty.
4. Prawdziwy start backendu z profilem Pawła: porównanie plików profilu przed/po (jak pkt 3), log z listą sprawdzonych elementów, czas startu przed/po.
5. UI: `tsc --noEmit` 0 błędów; scenariusze ręczne w działającej aplikacji, opisane w DELIVERY: (a) backend startuje >4 s → „Uruchamianie silnika…”, potem normalny ekran; (b) próba nie przechodzi (np. `ANONYMIZER_PROFILE_DIR` wskazuje plik zamiast katalogu) → CrashScreen z nazwą elementu; (c) backend nieuruchomiony → po 60 s `STARTUP-NO-RESPONSE`; (d) stary `api_token.txt` bez działającego backendu → brak „gotowe”. Ocena okiem Pawła po przebudowie Tauri.
6. Regresje: `tests/` z działającym backendem, `test_failclosed.py`.

## Pomiar czasu prób (CC, 2026-10-18, komputer Pawła, przed kodem)
SpaCy — wczytanie modelu 4,5 s (dziś i tak następuje, tylko później: przy pierwszym dokumencie), rozpoznanie zdania 0,01 s; Morfeusz `native` 0,08 s; izolowany profil (`add_entity` + `_layer1_trie`) 0,05 s; crypto 0,01 s; smoke regex 0,18 s. Razem ok. 5 s; na maszynie biurowej (2–4× wolniej) szacunkowo 10–20 s. Backend startuje równolegle z ekranem logowania aplikacji, a pętla gotowości (3b) rusza dopiero po odblokowaniu — przy zwykłym starcie użytkownik nie powinien jej widzieć. Limit 60 s (zmniejszony z 180 s na uwagę Pawła: „trzy minuty na odpalenie programu to było w latach 90.”) to wyłącznie granica, po której program zgłasza brak odpowiedzi.
Uwaga do prób: syntetyczne nazwisko musi być znane Morfeuszowi (nazwa nieznana, np. zmyślona, daje tylko formę podstawową — sprawdzone: wymyślone nazwisko 1 forma, „Kowalski” 8+ form), inaczej próba MORFEUSZ/PROFIL fałszywie nie przejdzie. Użyć pospolitego wzorca imienia i nazwiska (np. „Jan Kowalski” → „Jana Kowalskiego”).

GATE: 2 nowe pliki; `pseudominizer_api.py` (legacy >600) — przyrost minimalny, raportowany (szacunek ±8 linii, logika w nowym module); `App.tsx` ok. +25 linii; >150 linii → WYMAGA_DECYZJI. Zgoda Pawła na ~220 udzielona przed kodem; po r2 (UI + izolowana próba profilu) szacunek ~290 (startup_check ~140, API ~8, App ~25, testy ~120) — zgłoszone Pawłowi przed kodem.
