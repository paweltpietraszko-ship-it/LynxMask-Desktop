# LYNX-ONE-LAUNCHER — jedna ikona do uruchamiania + porządek w starych starterach

STATUS: brief CC na polecenie Pawła („Tak, zrób jedną ikonę i posprzątaj, całe repo wygląda jak pokój trzylatka”). Narzędzie uruchomieniowe, nie silnik. Obieg: CC implementacja → Codex audyt exact-SHA → merge na słowo Pawła. Precheck pominięty — zgłoszone Pawłowi.
POCHODZENIE: 19.10 Paweł nie mógł uruchomić programu:
- `backend/uruchom.vbs` otwiera przeglądarkę na stary interfejs HTML, który od LYNX-T02 wymaga tokenu → `{"error":"Unauthorized"}`; Python ma wpisany na sztywno;
- `dev.bat` woła `python`, którego na maszynie nie ma;
- aplikacja `pseudominizer.exe` leży w `frontend/src-tauri/target/release` i nie uruchamia silnika;
- skrót „LynxMask” w menu Start prowadzi do katalogu projektu Mobile.

Stałe rozwiązanie (aplikacja sama zarządza silnikiem) to `LYNX-APP-LAUNCHER` — poza zakresem.
PRODUCT_TRUTH: S5 (logi bez zapisu na dysk), S6 (port 8765, token API). Bez zmian w silniku i aplikacji.

## Kontrakt
1. `LynxMask.vbs` w katalogu głównym repo (WScript, bez okna konsoli):
   - silnik odpowiada na `GET http://127.0.0.1:8765/health` 200 i w `backend/` jest `api_token.txt` → tylko otwiera aplikację;
   - w przeciwnym razie uruchamia `py -3 pseudominizer_api.py` w `backend/` bez okna (wtedy log trafia donikąd, zgodnie z S5), czeka do 120 s na gotowość (health 200 + token), przerywa wcześniej, gdy pojawi się `startup_error.json` (aplikacja pokaże wtedy ekran awarii), i otwiera aplikację;
   - brak zbudowanej aplikacji → komunikat „uruchom build.bat”; brak `py` → komunikat. Bez ścieżek wpisanych na sztywno.
2. Skrót „LynxMask” na pulpicie Pawła → `wscript.exe <repo>\LynxMask.vbs`, ikona z `pseudominizer.exe`. To zmiana lokalna, nie w repo.
3. Usunięte nieaktualne startery i stary interfejs webowy: `dev.bat`, `dev.sh`, `build.sh`, `backend/uruchom.vbs`, `backend/zatrzymaj.vbs`, `backend/init_profile.bat`, `backend/run_*.bat` (6), `backend/pseudominizer.html`, `backend/index.html`. Zostaje `build.bat` (budowanie aplikacji). `GET /` po usunięciu HTML zwraca istniejące 404 JSON.
4. `test_disk_pii.py::test_f3_launcher_bez_zapisu_logu_na_dysk` sprawdza `LynxMask.vbs`: brak `>>` i brak pliku logu.
5. README: sekcja „Uruchomienie” — ikona `LynxMask.vbs` i `build.bat`.

TASK_SCOPE:
- LynxMask.vbs
- README.md
- dev.bat
- dev.sh
- build.sh
- backend/uruchom.vbs
- backend/zatrzymaj.vbs
- backend/init_profile.bat
- backend/run_benchmark.bat
- backend/run_benchmark_real.bat
- backend/run_dict_auto.bat
- backend/run_preview_real.bat
- backend/run_smoke_e2e.bat
- backend/run_tests.bat
- backend/pseudominizer.html
- backend/index.html
- backend/tests/test_disk_pii.py

OUT_OF_SCOPE: silnik, UI aplikacji, Tauri (`main.rs`), narzędzia procesu w katalogu głównym (`gate.py`, `guard.py`, `where.py`, `task_init.py`, `session_log.py` — używane przez CC i Codexa), dokumenty w `backend/*.md`, zbiory danych.

## Porządki lokalne (bez commitu, zasada „sprzątanie dozwolone”)
- `archive/` w katalogu głównym: testowy `rejestr.db` i dwa syntetyki z 18.10 (artefakt testu uruchomionego z katalogu głównego);
- `audit_ui_limit_0zsrog48/`: zakończony audyt TEXT-LIMIT.

`.audit_startup_af8833b/` to migawka Codexa z 19.10 — zostawiam, prośba do Codexa w BOARD o sprzątnięcie i trzymanie migawek poza repo.

## Falsyfikacja
- Silnik działa → skrypt otwiera aplikację bez drugiego silnika (port 8765 zajęty tylko raz).
- Silnik nie działa → skrypt go uruchamia, aplikacja dostaje token i działa (test ręczny CC + Paweł).
- `startup_error.json` → aplikacja pokazuje ekran awarii.
- `tests/` i `test_disk_pii` przechodzą.
