# Brief — LYNX-T02-CORS-EXPRESS
Status: propozycja kontraktu do prechecku Codexa; bez implementacji.
PRODUCT_TRUTH: `arch/spec.md` S1, S5, S6; `arch/FINDING_2026-10_AUDYT.md` BUG-EXPRESS-TOKEN-SCOPE + CORS wildcard.
OWNER_DECISION: brak; nie zmieniać tego, czy tryb Express może wypuścić niezamaskowaną osobę (osobne pytanie OWNERA).
Cel: obca witryna nie może przez przeglądarkę odczytać słownika i archiwum lokalnego backendu.
Zachowanie: token Express nadal dostępny dla uprawnionego lokalnego interfejsu Express, ale uprawnia wyłącznie do `/preview-express`; wszystkie inne prywatne endpointy przy tym tokenie zwracają 401. Żądania z niedozwolonego Origin nie dostają nagłówka umożliwiającego odczyt. Pełny token API zachowuje uprawnienia. Nieautoryzowana odmowa bez PII w odpowiedzi i bez nowych danych na dysku.
Existing owner: `backend/pseudominizer_api.py`, istniejące middleware uwierzytelniania i CORS. Nie dodawać sesji, nowych tokenów ani równoległego proxy.
TASK_SCOPE:
- backend/pseudominizer_api.py
- backend/tests/test_audyt_2026_10.py
OUT_OF_SCOPE: output Guard, zmiany pipeline Express, UI, TOKEN_RE, nowe ekrany logowania, rozszerzenie zakresu API.
Test celowany: `test_express_token_nie_otwiera_profilu`, `test_cors_nie_wpuszcza_obcego_origin`, `test_pusty_token_nie_przepuszcza` z `backend/tests/test_audyt_2026_10.py`: XPASS, następnie zdjąć te xfail. Konieczny test pozytywny żądania Express z prawidłowym tokenem i prawidłowego pełnego tokenu; żaden z trzech znanych failów NER nie jest własnością T02, więc nie wolno obiecywać ich zazielenienia.
PASS: brak dostępu do `/profile/entities`, `/archive` i eksportu przy tokenie Express; niedozwolony Origin nie odczytuje `/express/token`; pusty token nie działa, także przed lifespan; uprawniony Express działa. Nie wystarcza samo usunięcie CORS wildcard (curl nadal omija CORS).
UWAGA PRECHECK: sprawdzić faktyczny Origin/Tauri i połączenie UI Express przed wybraniem ograniczonej listy originów; jeśli obecne UI wymaga pochodzenia niemożliwego do zweryfikowania, zwrócić jako brak kontraktu, nie wprowadzać wildcard.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pseudominizer_api.py --symbol _require_api_token
- REASON: zmiana uprawnień istniejącego middleware i konfiguracji CORS.
Gate: max 2 nowe pliki, >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI; nie powiększać starego pliku bez konieczności.
