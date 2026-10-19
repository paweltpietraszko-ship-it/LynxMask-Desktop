# LYNX-ONE-LAUNCHER — DELIVERY r1 (CC)

Kod: `335420b` na main `c884900`. Brief: `tasks/LYNX-ONE-LAUNCHER/brief.md` (polecenie Pawła 19.10; precheck pominięty, zgłoszone Pawłowi).

## Zmiany
- **Nowy `LynxMask.vbs`** w katalogu głównym, 47 linii:
  - silnik gotowy (`/health` 200 i `backend/api_token.txt`) → otwiera tylko aplikację;
  - w przeciwnym razie `py -3 pseudominizer_api.py` w `backend/` bez okna (styl 0, bez przekierowania do pliku — S5), czeka do 120 s albo do pojawienia się `startup_error.json`, potem otwiera aplikację;
  - brak zbudowanej aplikacji lub brak `py` → komunikat;
  - bez ścieżek wpisanych na sztywno, napisy w ASCII (WSH czyta ANSI), CRLF.
- **Usunięte (14 plików):**
  - `dev.bat` (woła `python`, którego nie ma), `dev.sh`, `build.sh`;
  - `backend/uruchom.vbs` (przeglądarka na stary interfejs → 401), `backend/zatrzymaj.vbs`, `backend/init_profile.bat`;
  - `backend/run_*.bat` ×6 (`python`, a `run_benchmark.bat` zabijał proces na 8765);
  - `backend/pseudominizer.html` i `backend/index.html` (stary interfejs webowy; `GET /` zwraca istniejące 404 JSON).

  Zostaje `build.bat`.
- `README.md`: sekcja „Running (Windows)”.
- `test_disk_pii.py::test_f3_launcher_bez_zapisu_logu_na_dysk` sprawdza `LynxMask.vbs`: brak `>` w poleceniu startu silnika, brak `.log`, `uruchom.vbs` nie istnieje.

## Dowody
- `test_disk_pii.py`: 6 passed.
- **Test na żywo, maszyna Pawła, 19.10 06:23:**
  - aplikacja przebudowana z main `c884900` (`npm run tauri build`, exit 0, `pseudominizer.exe` 06:23);
  - backend CC zatrzymany, port 8765 wolny;
  - kliknięcie skrótu („LynxMask” na pulpicie → `wscript.exe <repo>\LynxMask.vbs`) → `py -3 pseudominizer_api.py` bez okna (PID nasłuchu 8765);
  - `api_token.txt` zapisany 06:23:32;
  - aplikacja otwarta po 8 s;
  - `POST /preview` z tym tokenem → 200.
- Na czas testu kopia `LynxMask.vbs` leży w katalogu głównym repo Pawła jako plik nieśledzony. Przed merge zostanie usunięta.
- Skrót na pulpicie to zmiana lokalna, poza repo.

## Gate (dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 335420ba7a2d23d5e168f00e6e6b49c662d0538e
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 1974 lines changed (threshold 150)
```
TOTAL to prawie wyłącznie usunięcia: stary `pseudominizer.html` i startery. Dodane: 47 linii vbs, 6 linii README, test.

## Lokalne porządki (bez commitu)
- Usunięte śmieci testowe w katalogu głównym repo Pawła: `archive/` (testowy `rejestr.db` i 2 syntetyki z 18.10) oraz `audit_ui_limit_0zsrog48/` (zakończony audyt TEXT-LIMIT).
- `.audit_startup_af8833b/` (migawka Codexa) zostawiona — prośba w BOARD.

## Uwaga dla pracy CC
Po każdym restarcie silnika przez CC (testy gałęzi) aplikacja Pawła ma stary token. Wystarczy zamknąć aplikację i kliknąć ikonę ponownie — skrypt wykryje działający silnik i tylko otworzy aplikację. Stałe rozwiązanie: `LYNX-APP-LAUNCHER`.
