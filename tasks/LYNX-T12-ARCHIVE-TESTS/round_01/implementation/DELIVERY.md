# LYNX-T12-ARCHIVE-TESTS — DELIVERY round_01

BEFORE_SHA: `0da298d4802306694065cab464583916fcacd571` · IMPLEMENTATION_SHA: `c96199b00028f7ce7b06ba1c77d51834a3242fec`
Zmieniony plik (TASK_SCOPE): `backend/tests/test_archive_adversarial.py`. Produkt bez zmian.

## Ocena briefu
Brief zgodny z kodem: `pseudominizer_api` przy imporcie robi `MAPS_DIR.mkdir` + `db_store.init(DB_PATH)` z `ARCHIVE_DIR` (env lub `./archive`), `_init_db()` to pusty alias, `db_store._DB_PATH` jest globalem modułu. Przyjęty bez uwag.
Potwierdzenie problemu: lokalne `backend/archive/` zawierało wyłącznie pozostałości dawnych przebiegów tego testu (`PSE-2026-9001/9010/9030.enc`, bloby 51–52 B = `FAKE_ENCRYPTED_DATA_…`) — stary test pisał do archiwum użytkownika. Nie sprzątałem (poza zakresem).

## Co zrobione
- Pierwszy import API w module: tylko jeśli `pseudominizer_api` nie ma w `sys.modules`, `ARCHIVE_DIR` w env → `TemporaryDirectory("lynx_t12_import_")` na czas importu, env odtworzony (także poprzednia wartość). Katalog żyje do końca procesu (finalizer), więc odtworzone globale nie wskazują na usunięty katalog.
- `setUpModule` (każde uruchomienie, niezależnie od kolejności importu): zapis `api.ARCHIVE_DIR/MAPS_DIR/DB_PATH/_API_TOKEN` i `db_store._DB_PATH`; nowy `TemporaryDirectory("lynx_t12_")`; `db_store.init()` tylko na bazie tymczasowej; syntetyczny token 64 znaki; sprawdzenie, że MAPS_DIR/DB_PATH/`db_store._DB_PATH` leżą w katalogu tymczasowym — inaczej `RuntimeError` i zero żądań. Błąd setupu → `_restore()` przed ponownym rzuceniem.
- `tearDownModule` → `_restore()`: odtworzenie globali (dla `db_store` tylko atrybut, nigdy `init()` na produkcji), `gc.collect()` + `cleanup()`. `gc.collect()` jest konieczny: `db_store` używa `with sqlite3.connect()` bez `close()`, Windows trzyma `rejestr.db` → bez tego `PermissionError [WinError 32]` w teardown (zaobserwowane w pierwszej wersji).
- `make_client()`: `TestClient(base_url="http://127.0.0.1:8765", headers={"X-Api-Token": …})` bez `with` (lifespan nie startuje). Allowlista Host bez zmian.
- 4 klasy: `_init_db()` + `TestClient(app)` → `make_client()`. Treść testów D1–D12 bez zmian.
- Nowa klasa `TestArchiveAuthGate` (kryterium 3): brak tokenu → 401, `Host: evil.example:8765` → 400.

## Dowody
1. Moduł sam (`py -3 -m pytest tests/test_archive_adversarial.py -q -o log_file=NUL`): `19 passed` (17 dawnych + 2 nowe; dawne 7 FAIL D1,D5,D6,D8,D8b,D10,D12 zielone).
2. Ten sam proces, API zaimportowane wcześniej przez `test_pipeline_adversarial`, moduł T12 2× (`implementation/t12_same_process.py`, uruchomić z `backend/`):
   ```
   API imported first: True | DB_PATH before: archive\rejestr.db
   T12 import-time tmp used: False
   run 1: tests=19 fail=0 err=0 skip=0 | db under TEMP: True | db exists after: False | maps exists after: False
   run 2: tests=19 fail=0 err=0 skip=0 | db under TEMP: True | db exists after: False | maps exists after: False
   globals restored: True | leftover lynx_t12_ dirs: 0
   ```
   (pytest deduplikuje powtórzoną ścieżkę pliku, dlatego powtórka przez `unittest` w jednym procesie.)
3. Log z (2): bez tokenu `401`, obcy Host `400`; D2/D3/D4/D4b/D7/D11b dostają `400` z walidacji endpointu przy poprawnym Host/tokenie, D11 `500` z rollbacku reencrypt (jak przed T02).
4. Izolacja dysku: sygnatura `backend/archive/` (nazwa, rozmiar, mtime_ns, sha256 — `implementation/archsig.py`) identyczna przed i po każdym przebiegu (moduł sam, przebieg (2), pełna suita): `ARCHIVE_UNCHANGED`. Po przebiegach 0 katalogów `lynx_t12_*` w `%TEMP%`.
5. Pełna suita (`py -3 -m pytest tests/ -q -o log_file=NUL`, profil tymczasowy przez env): `1 failed, 126 passed, 40 skipped, 1 xfailed` — jedyny FAIL `test_pipeline_v2.py::TestIbanWithSpace::test_iban_reverse_map_entry` (IBAN-RECEPTA, nietknięty). Przed: 8 failed. `test_audyt_2026_10.py`: `40 passed, 15 xfailed`.

## gate.py (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: c96199b00028f7ce7b06ba1c77d51834a3242fec
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 81/12 = 6.8:1 (threshold 5:1)
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-T12-ARCHIVE-TESTS/round_01/tests/tests_r1.txt
```
Uzasadnienie RATIO: zmiana z natury addytywna — brief każe zachować istniejące przypadki, więc usuwane są tylko 4× `_init_db()`/`TestClient(app)` i stary import; dodana jest fixture (izolacja przy imporcie + setup/teardown z odtwarzaniem 5 globali + strażnik ścieżek) i 2 testy bramy z kryterium 3. Bez testów bramy: ok. 71/12, nadal >5:1. Do rozstrzygnięcia przez Codexa/architekta; mogę usunąć `TestArchiveAuthGate`, jeśli dowód w DELIVERY wystarczy.

## Zgłoszenia (nie wykonane)
- Import `pseudominizer_api` przez inne moduły testów (`test_pipeline_adversarial`, `test_pseudominizer`) nadal robi `db_store.init()` na `./archive/rejestr.db` przy kolekcji (sygnatura pliku się nie zmienia — tylko `CREATE TABLE IF NOT EXISTS`). Poza zakresem T12.
- Lokalne `backend/archive/` ma 3 syntetyczne pozostałości po starym teście — do usunięcia ręcznie przez Pawła, jeśli chce.
