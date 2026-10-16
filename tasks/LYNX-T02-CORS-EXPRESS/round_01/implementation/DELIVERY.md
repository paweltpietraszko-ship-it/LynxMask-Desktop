# DELIVERY — LYNX-T02-CORS-EXPRESS (CC, runda 1)

Brief: `tasks/LYNX-T02-CORS-EXPRESS/brief.md` (`3cff4f5`, precheck Codexa r3 PASS `286b964` = BEFORE_SHA).
Ocena CC korekty: B1 (Host/DNS rebinding) i B2 (pomiar wydania po T10-BUILD-TS) zamknięte — brief przyjęty.
CC nie wystawia werdyktu własnej implementacji.

## Zmiana (`backend/pseudominizer_api.py`, istniejący middleware `_require_api_token` + CORS)

- `_ALLOWED_HOSTS = {"127.0.0.1:8765", "localhost:8765"}` — sprawdzane jako PIERWSZE w middleware, dla każdej ścieżki
  (także `/health`, `/express/token`, `OPTIONS`); inny `Host` → 400 `{"error": "Invalid host"}`. Ścisły port w tym samym
  ownerze (wbudowany `TrustedHostMiddleware` nie sprawdza portu — nie użyty). Frontend (`MainLayout.tsx`, `App.tsx`,
  `Biblioteka.tsx`, …) i Rust (`main.rs`) łączą się wyłącznie z `http://127.0.0.1:8765` → Host `127.0.0.1:8765`.
- CORS: `allow_origins = ["http://localhost:1420", "http://tauri.localhost"]` zamiast `*` (dev `devUrl` + oczekiwany Origin
  wydania Windows Tauri 2 — DO POTWIERDZENIA pomiarem po T10-BUILD-TS, warunek końcowego PASS wg briefu).
- Token Express ważny wyłącznie dla `POST /preview` i `POST /preview-express`; każda inna ścieżka z tym tokenem → 401.
- Pusty token serwera (przed lifespanem) nigdy nie pasuje (`bool(_API_TOKEN) and compare_digest(...)`).
- Brak nowych plików, sesji, tokenów, proxy; UI bez zmian.

## Testy (`backend/tests/test_audyt_2026_10.py`)

- Zdjęte `xfail`: `test_express_token_nie_otwiera_profilu`, `test_cors_nie_wpuszcza_obcego_origin`, `test_pusty_token_nie_przepuszcza`.
- Klient testowy z jawnym `base_url="http://127.0.0.1:8765"` (bez wyjątku `testserver` w produkcji).
- Nowe: token Express → 401 na `/profile/entities`, `/profile/export-dict`, `/archive`, `/version` (pełny token ≠ 401);
  `POST /preview` i `/preview-express` przechodzą auth z tokenem Express i pełnym; `Host: evil.example:8765` → 400 na
  `/express/token` (bez tokenu w odpowiedzi) i na `/profile/entities` z pełnym tokenem, bez `Origin`;
  `127.0.0.1:8765` / `localhost:8765` → 200; Origin UI Tauri (dev, wydanie) dostaje `Access-Control-Allow-Origin`.
- Wynik: 16/16 testów T02 zielonych.

## Pełna suita na gałęzi (bez backendu) — UWAGA, poza TASK_SCOPE

| | BEFORE `286b964` | po T02 |
|---|---|---|
| failed | 3 (filtr NER ×2 — naprawione w T01 na main; IBAN-RECEPTA) | **10** = te 3 + **7 × `tests/test_archive_adversarial.py`** |

7 testów archiwum (`test_d1_valid_save`, `test_d5`, `test_d6`, `test_d8`, `test_d8b`, `test_d10`, `test_d12`) dostaje teraz
400: używają `TestClient(app)` (Host `testserver`) i NIE wysyłają tokenu — przechodziły wyłącznie dzięki BUG-AUTH-BYPASS
(audyt §2b, „Istniejące test_archive_adversarial.py działa właśnie dzięki temu”). To przewidywalny skutek kontraktu T02,
nie regresja produktu. Plik nie jest w TASK_SCOPE — **nie zmieniono go**. Minimalna naprawa testu (do decyzji Architekta:
dopisanie do TASK_SCOPE T02 albo w LYNX-T12-TEST-ISOLATION): `TestClient(app, base_url="http://127.0.0.1:8765")` +
nagłówek `X-Api-Token` z podstawionym `_API_TOKEN` (jak fixture `api_client`). Uwaga z audytu: te testy piszą też do
produkcyjnego `backend/archive/` — temat T12.
