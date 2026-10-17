# LYNX-T12-ARCHIVE-TESTS — izolacja testów archiwum po T02

STATUS: BRIEF_ONLY — wyłącznie testy, bez modyfikacji produktu.
PRODUCT_TRUTH: `arch/spec.md` S3 (brak obejścia blokady), S5 (bezpieczne składowanie danych) i S6 (każde prywatne API wymaga tokenu); kontrakt T02 po merge (weryfikacja `Host` + pełnego tokenu).
FINDING: `BOARD.md` — `LYNX-T12-ARCHIVE-TESTS`; niezależny audyt T02 `tasks/LYNX-T02-CORS-EXPRESS/round_01/tests/tests_r4.txt`: 7/7 testów D1,D5,D6,D8,D8b,D10,D12 przeszło z prawidłowym testowym Host/tokenem, bez zmian kodu. Obecny test tworzy `TestClient(app)` i używa produkcyjnej ścieżki archiwum; `pseudominizer_api.py` inicjalizuje `ARCHIVE_DIR`, `MAPS_DIR`, `DB_PATH` oraz `db_store.init()` już przy imporcie.
CEL: przywrócić znaczenie 7 testów i zagwarantować, że test archiwum nie czyta, nie nadpisuje ani nie usuwa prawdziwych sesji użytkownika.

## Zachowanie
- Testy pozytywne wykonują prawdziwe endpointy archiwum na syntetycznym zaszyfrowanym blobie i tymczasowym katalogu SQLite/.enc; poprawne `Host: 127.0.0.1:8765` i pełny syntetyczny `X-Api-Token` są częścią testowego klienta.
- Testy negatywne PSE, base64 i token_count nadal weryfikują walidację wejścia przez endpoint. Nie mogą przechodzić tylko dlatego, że żądanie zwróciło 400 za błędny Host lub 401 za brak tokenu.
- Po zakończeniu nie zostaje plik testowy ani zmodyfikowany globalny stan auth, lokalizacji archiwum i ścieżki bazy. Błąd testu też uruchamia sprzątanie.
- UI, backend i dane realnego profilu bez zmian.

## Owner / minimalny szew
Istniejący właściciel fixture: `backend/tests/test_archive_adversarial.py` (unittest `setUpClass`/klient). Zastosować jeden wspólny minimalny setup/teardown dla klas testowych, bez dopisywania równoległego API lub osobnego subsystemu.
Istotne: obecne `_init_db()` w API to pusty alias, a `db_store` przechowuje aktywną `_DB_PATH` w module. Sam `TemporaryDirectory` lub `ARCHIVE_DIR` ustawiony **po** imporcie nie izoluje archiwum. Fixture musi przed pierwszym importem API w tym module wybrać tymczasowe `ARCHIVE_DIR`; jeżeli `pseudominizer_api` jest już w `sys.modules` podczas uruchomienia pełnej suity, musi dodatkowo podmienić jego `MAPS_DIR`/`DB_PATH` oraz skierować `db_store.init` na bazę tymczasową **przed pierwszym żądaniem**. Zachować i przywrócić stare wartości po teście (także `db_store._DB_PATH` i `_API_TOKEN`); nigdy nie inicjalizować ani nie czyścić produkcyjnej bazy w setup/teardown. Testowe bloby tylko syntetyczne. Jeśli nie da się zagwarantować izolacji, fail setup i zero operacji na realnym archiwum.
Używać `TestClient` z `base_url` zawierającym dozwolony Host i pełnym testowym tokenem; nie dodawać `testserver` do produkcyjnej allowlisty. Nie uruchamiać produkcyjnego lifespan ani realnego serwera.

TASK_SCOPE:
- backend/tests/test_archive_adversarial.py

OUT_OF_SCOPE: `pseudominizer_api.py`, `db_store.py`, `pytest.ini`, produkcyjna konfiguracja Host/CORS/auth, Guard, format PSE i tokenów, zmiana błędów endpointów dla wygody testów, globalne przepisanie całej suity lub refaktor archiwum.

## Test i kryteria PASS
1. `cd backend && python -m pytest tests/test_archive_adversarial.py -q -o log_file=NUL` (na Windows) — wszystkie istniejące przypadki, w tym siedem dawnych FAIL, zielone. Na Linux użyć `-o log_file=/dev/null` albo wyłączyć log_file w parametrach testowego uruchomienia.
2. Powtórzyć moduł w tym samym procesie testowym co pozostałe testy korzystające z `pseudominizer_api`; dowód, że import API wcześniej nie kieruje T12 do prawdziwego archiwum. Ponowne uruchomienie tego samego modułu ma być idempotentne.
3. Negatywny dowód: bez pełnego tokenu → 401; z obcym Host → 400; po podaniu prawidłowego Host/tokena rzeczywiste D1/D5/D6/D8/D8b/D10/D12 dochodzą do własnych asercji i przechodzą.
4. Dowód izolacji: ścieżka SQLite i .enc w `TemporaryDirectory` poza `backend/archive/`, pozostająca tam tylko przez test; po cleanup brak plików; żaden plik/sygnatura w uprzednio istniejącym `backend/archive/` nie zmieniła się. Można użyć sentinela syntetycznego, ale nie dotykać danych rzeczywistych.
5. Cała suita ma najwyżej dotychczasowy niezależny FAIL `IBAN-RECEPTA` (nie należy go ukrywać ani modyfikować); brak nowych failów. Nie modyfikować `xfail` niepowiązanych z archiwum.

PASS PREIMPLEMENTATION: zakres mieści się w istniejącym teście; poprawka naprawia wyłącznie fixture, nie produkt. PASS po implementacji: testy odtworzone na exact SHA, auth/Host pozostają fail-closed, izolacja dysku i stanu globalnego udowodniona.
WHERE_MAP:
- MODE: OPTIONAL
- TARGETS: backend/tests/test_archive_adversarial.py
- REASON: zmiana wyłącznie fixture testowej, bez modyfikacji produkcyjnego ownera.
GATE: brak nowych plików; >150 zmienionych linii lub ratio >5:1 oznacza WYMAGA_DECYZJI; nie powiększać testu bez konieczności.
