# Brief — LYNX-T02-CORS-EXPRESS
Status: propozycja kontraktu do prechecku Codexa; bez implementacji.
PRODUCT_TRUTH: `arch/spec.md` S1, S5, S6; `arch/FINDING_2026-10_AUDYT.md` BUG-EXPRESS-TOKEN-SCOPE + CORS wildcard.
OWNER_DECISION: brak; nie zmieniać tego, czy tryb Express może wypuścić niezamaskowaną osobę (osobne pytanie OWNERA).
Cel: obca witryna nie może przez przeglądarkę odczytać słownika i archiwum lokalnego backendu.
Zachowanie: token Express nadal dostępny dla lokalnego UI i uprawnia WYŁĄCZNIE do `POST /preview` (rzeczywiście używany przez Express: `App.tsx` → `MainLayout.tsx` → `Pseudonimizuj.tsx`) oraz `POST /preview-express` (istniejący endpoint niepodłączonego `ExpressModeScreen.tsx`). Każdy inny endpoint, w tym profil, eksport i archiwum, przy tym tokenie zwraca 401. Zachowanie aktualnego UI Express pozostaje bez zmian; nie przełączać go teraz na inny pipeline. CORS dla UI Windows Tauri 2: w dev dozwolony dokładnie `http://localhost:1420` (konfiguracja `devUrl`), w wydaniu Windows oczekiwany `http://tauri.localhost` (Tauri 2, domyślny schemat, bez `useHttpsScheme`). Nie dopuszczać `*`, `null`, obcych domen, portów ani wzorca `localhost:*`. Żądania bez `Origin` nie otrzymują nagłówka `Access-Control-Allow-Origin`, ale nadal przechodzą zwykłe sprawdzenie tokenu; sam brak `Origin` nie daje dostępu. Przed PASS implementacji trzeba potwierdzić nagłówek Origin z uruchomionego wydania Windows; przy odmiennym Origin zatrzymać dostawę i wrócić do Architekta, nie poszerzać listy bez dowodu. Pełny token API zachowuje uprawnienia. Nieautoryzowana odmowa bez PII w odpowiedzi i bez nowych danych na dysku.
Existing owner: `backend/pseudominizer_api.py`, istniejące middleware uwierzytelniania i CORS. Nie dodawać sesji, nowych tokenów ani równoległego proxy.
TASK_SCOPE:
- backend/pseudominizer_api.py
- backend/tests/test_audyt_2026_10.py
OUT_OF_SCOPE: Output Guard, zmiany pipeline Express, UI, TOKEN_RE, nowe ekrany logowania, rozszerzenie zakresu API; nie przenosić Express na niepodłączony `ExpressModeScreen` w tym Tasku.
Test celowany: `test_express_token_nie_otwiera_profilu`, `test_cors_nie_wpuszcza_obcego_origin`, `test_pusty_token_nie_przepuszcza` z `backend/tests/test_audyt_2026_10.py`: XPASS, następnie zdjąć te xfail. Konieczny test pozytywny `POST /preview` z tokenem Express oraz pełnym tokenem, zachowanie `POST /preview-express` i test negatywny GET `/profile/entities`, eksport, archiwum z tokenem Express; żaden z trzech znanych failów NER nie jest własnością T02, więc nie wolno obiecywać ich zazielenienia.
PASS: brak dostępu do `/profile/entities`, `/archive` i eksportu przy tokenie Express; niedozwolony Origin nie odczytuje `/express/token`; pusty token nie działa, także przed lifespan; uprawniony Express nadal działa przez `POST /preview`, bez wymuszania zmiany UI. Nie wystarcza samo usunięcie CORS wildcard (curl nadal omija CORS).
DOWÓD GRANIC: `frontend/src/App.tsx` pobiera `/express/token`; `MainLayout.tsx` renderuje `Pseudonimizuj.tsx` wysyłający `/preview`. `frontend/src-tauri/tauri.conf.json` ma devUrl `http://localhost:1420`; Tauri 2 na Windows domyślnie korzysta z `http://tauri.localhost`. To ostatnie to oczekiwany Origin z dokumentacji, NIE pomiar z wydania: test na rzeczywistym buildzie jest warunkiem PASS dostawy.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pseudominizer_api.py --symbol _require_api_token
- REASON: zmiana uprawnień istniejącego middleware i konfiguracji CORS.
KOREKTA r2: tylko dwa braki Codexa z `round_01/tests/tests_r1.txt`: rzeczywista ścieżka Express i dozwolone Originy. Precheck r2 ograniczyć do nich.
Gate: max 2 nowe pliki, >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI; nie powiększać starego pliku bez konieczności.
