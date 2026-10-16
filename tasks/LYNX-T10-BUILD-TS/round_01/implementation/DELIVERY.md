# DELIVERY — LYNX-T10-BUILD-TS (CC, runda 1)

Brief: `tasks/LYNX-T10-BUILD-TS/brief.md` (`30b4061`, precheck Codexa PASS `b8fc461`); ocena CC `cc_review_r1.md` (`744c1de` = BEFORE_SHA).
Implementacja: **`5b874072cfe818e12f3f81714d9af8944c3b8f55`**. CC nie wystawia werdyktu własnej implementacji.

## 1. Build TypeScript/Vite

- BEFORE (`744c1de`): `tsc --noEmit` = **31 błędów** (theme 23, MainLayout 4, App 1, Pseudonimizuj 1, SecurityScreen 2) — `tsc_before.txt`; zgodne z audytem.
- Zmiany (5 plików z TASK_SCOPE, +5/−9 linii):
  - `theme.ts`: `Theme = { readonly [K in keyof typeof DARK]: string }` (te same klucze, wartości string; `DARK`/`LIGHT`/`T` bez zmian).
  - `App.tsx`: `T.muted` → `T.textMuted` (ekran ładowania).
  - `MainLayout.tsx`: usunięte 4 nieużywane stałe logo.
  - `Pseudonimizuj.tsx`: `onClick={() => handleSave()}` — MouseEvent nie trafia już do `forceBypassGuard`.
  - `SecurityScreen.tsx`: `Btn.onClick` opcjonalny, `disabled={disabled || !onClick}`. **Ukryty błąd** (zasłonięty przez błąd onClick):
    `<Btn … style={{ marginBottom: 14 }}>` — `Btn` nie przyjmuje `style`, więc odstęp NIGDY nie działał; usunięta martwa
    właściwość (wygląd bez zmian, zgodnie z zakazem redesignu). Ewentualne dodanie odstępu = osobna decyzja kosmetyczna.
- AFTER: `tsc` 0 błędów; `npm run build` exit 0, `dist/` wygenerowany (`npm_build_after.txt`). Bez `any`/`@ts-ignore`/zmian tsconfig.
- `gate.py` na `5b87407` (dosłownie): `STATUS: PASS`.

## 2. Wydanie Windows Tauri 2

- `npm run tauri build` w repo: FAIL niezależny od zmiany — stary cache `src-tauri/target/` wskazuje poprzednią lokalizację
  projektu (`Desktop\pseudominizer-tauri\…\app_hide.toml: System nie może odnaleźć określonej ścieżki`). Cache nieusuwany
  (są w nim instalatory z czerwca); build ponowiony z `CARGO_TARGET_DIR` w katalogu tymczasowym: **exit 0**,
  `pseudominizer.exe` + `LynxMask Desktop_1.0.0_x64_en-US.msi` + `LynxMask Desktop_1.0.0_x64-setup.exe` (NSIS).
  Rekomendacja (poza zakresem): `cargo clean` w `frontend/src-tauri` przed następnym buildem w repo.

## 3. Pomiar Origin/Host — wydanie T10 (`5b87407`) × backend T02 (`dc498366368b0b4d4767a61e6c6d56c939630713`)

Backend T02 z izolowanego worktree, uruchomiony przez `header_capture.py` (zewnętrzny wrapper ASGI, zapis: metoda, ścieżka,
Origin, Host, czy był token — bez wartości — status). Profil/archiwum tymczasowe. Interakcję w UI wykonał OWNER
(dane syntetyczne). Log: `naglowki_release_windows.jsonl`.

| | Wynik |
|---|---|
| `Origin` ze wszystkich żądań UI | **`http://tauri.localhost`** (zgodny z `_ALLOWED_ORIGINS` T02) |
| `Host` | **`127.0.0.1:8765`** (zgodny z `_ALLOWED_HOSTS` T02) |
| Tryb standardowy (pełny token) | `POST /preview` 200, `POST /archive` 200 (Zapisz), `GET /archive` 200, `GET /profile/entities` 200, `GET /profile/guard-allowlist` 200, preflighty `OPTIONS` 200 |
| Tryb Express (token Express) | `GET /express/token` 200, `POST /preview` 200 (maskowanie działa); `GET /archive` **401** (zamierzone w T02) |
| Obcy Host (`curl -H "Host: evil.example:8765" /express/token`) | **400** |

## 4. Smoke UI (OWNER, wydanie Windows, dane syntetyczne)

OWNER: „Wszystko działa” — logowanie, maskowanie, Zapisz (niezablokowany wynik → `POST /archive` 200), przełączanie motywu,
„Pokaż encje”, „Pokaż wyjątki”. NIE sprawdzono: Zapisz przy wyniku zablokowanym przez Guard (wymaga dokumentu wywołującego blokadę)
— warstwa NOT_CHECKED; poprawka `onClick` sprawdzona typem (TS2322 zniknął) i odczytem kodu.

## 5. Znaleziska z pomiaru (istniały przed T02/T10 — nie naprawiane, do Architekta)

1. **Express: „Zapisz” → „Błąd szyfrowania lub zapisu.”** `handleSave` szyfruje kluczem z hasła (`invoke("encrypt_data")`), którego
   w Express nie ma → wyjątek przed wysłaniem (w logu brak `POST /archive`). Zapis w Express jest z założenia niemożliwy
   (brak klucza; od T02 także 401 dla tokenu Express) — UI powinien to powiedzieć zamiast pokazywać błąd.
2. **`GET /version` bez tokenu → 401** (`MainLayout.tsx:154`): wersja w pasku nigdy się nie wyświetla; dodatkowo kod czyta
   `d.version`, a API zwraca `{"api": …}`.
3. **Brak przycisku „Wyjdź z programu”** (zgłoszenie OWNERA). Obserwacja CC: po zakończeniu testu proces `pseudominizer.exe`
   nadal działał (nie ustalono, czy okno było zamknięte, czy tylko zminimalizowane).
