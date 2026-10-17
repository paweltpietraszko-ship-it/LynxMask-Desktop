# CC — ocena merytoryczna briefu LYNX-T02-CORS-EXPRESS (r1)

Brief na `42c11750d8a41b93a9ea4ac6cdf482ccf1a189e1` (po korekcie r2, precheck Codexa: PASS PREIMPLEMENTATION).
Werdykt CC: **ZWROT DO KOREKTY** — dwa konkretne braki, jedna runda. Reszta briefu przyjęta bez uwag.

## Braki

### B1. Sam CORS nie spełnia celu briefu — brak kontroli nagłówka Host (DNS rebinding)

Cel briefu: „obca witryna nie może przez przeglądarkę odczytać słownika i archiwum". CORS chroni tylko
żądania cross-origin. Przy DNS rebinding strona `http://evil.example:8765` po zmianie rekordu DNS na
`127.0.0.1` jest dla przeglądarki **tym samym originem** co backend: `GET /express/token` idzie bez
nagłówka `Origin` (same-origin GET), a brief wprost mówi, że żądania bez `Origin` „przechodzą zwykłe
sprawdzenie tokenu" — `/express/token` nie wymaga tokenu, więc strona dostaje token Express.
Po T02 ten token otwiera już tylko `POST /preview` — szkoda mniejsza, ale cel z briefu nie jest spełniony,
a pełny token nadal byłby bezpieczny tylko dlatego, że nie ma endpointu, który go zwraca.

Dowód z kodu (`main@a96a847`): `backend/pseudominizer_api.py` nie sprawdza nagłówka `Host`
(brak `TrustedHostMiddleware`, grep `Host`: 0 trafień). Mechanizm DNS rebinding to standardowa klasa
ataku na usługi na localhost [nie odtworzone w tym repo — wymaga kontrolowanego DNS]; nowsze Chrome
częściowo łagodzą to przez Private Network Access, Firefox nie.

Proponowana korekta (ten sam owner, ten sam plik, kilka linii): odrzucać żądania, których `Host` nie jest
dokładnie `127.0.0.1:8765` ani `localhost:8765` (np. `starlette.middleware.trustedhost.TrustedHostMiddleware`
z `allowed_hosts=["127.0.0.1", "localhost"]`). Test: żądanie z `Host: evil.example:8765` → 400.
Do sprawdzenia przez Architekta: jaki `Host` wysyła Tauri przy wywołaniu `http://127.0.0.1:8765`
(oczekiwany `127.0.0.1:8765`; ten sam pomiar co Origin).

### B2. Warunek PASS niewykonalny przed LYNX-T10 (build)

Brief wymaga przed PASS pomiaru `Origin` „z uruchomionego wydania Windows". Według audytu
(BUILD-TSC, [S]) `npm run build` kończy się 31 błędami TS, a `tauri build` uruchamia go jako
`beforeBuildCommand` — wydania nie da się dziś zbudować, więc T02 utknie na PASS.

Proponowane rozstrzygnięcie (wybór Architekta, jedno z):
(a) przenieść naprawę typów z LYNX-T10 (tylko część TS, bez ikon) przed dostawę T02; albo
(b) PASS T02 na podstawie testów + dokumentacji Tauri 2 (`http://tauri.localhost`), a pomiar Origin/Host
z wydania jako osobny, obowiązkowy punkt w T10 z prawem do cofnięcia, jeśli Origin będzie inny.
CC rekomenduje (a) — fałszywie zbyt wąski CORS w wydaniu zepsułby aplikację u użytkownika.

## Przyjęte bez uwag

Zakres plików, zachowanie ścieżki Express przez `POST /preview`, odrzucenie `*`/`null`/`localhost:*`,
pusty token także przed lifespan, OUT_OF_SCOPE i zakaz obiecywania zazielenienia faili NER.
