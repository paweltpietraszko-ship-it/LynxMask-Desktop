# LYNX-T10-BUILD-TS — minimalna naprawa buildu i pomiar dla T02

STATUS: BRIEF_ONLY; dla prechecku Codexa, bez implementacji. Branch `task/LYNX-T10-BUILD-TS`.
PRODUCT_TRUTH: `arch/spec.md` S3 (fail-closed), S6 (działający lokalny UI), decyzja OWNERA w `BOARD.md`: T02 czeka na T10 i końcowy pomiar Windows, bez wcześniejszego merge.
FINDING: `arch/FINDING_2026-10_AUDYT.md` §2c BUILD-TSC, BUG-S3-ARCHIVE-403-DEAD; reproduktor `audyt/logs/npm_build.txt` na `audyt/2026-10` (31 błędów TS w audycie). `BOARD.md` wiersze T10 i T02.
CEL: przywrócić kontrolowany build TypeScript/Vite i wydanie Windows Tauri 2, bez wyłączania kontroli typów i bez zmiany sposobu działania aplikacji; dostarczyć rzeczywisty pomiar `Origin` i `Host` potrzebny do dokończenia audytu T02.
OWNER_CONFIRMED: naprawa buildu samodzielnej aplikacji; T02 bez merge do zakończenia pomiaru. TECHNICAL_ONLY: błędy TS, niewykorzystane zmienne i poprawne typowanie callbacków.
ZACHOWANIE: użytkownik nadal otwiera te same ekrany, przełącza motyw, używa przycisków bezpieczeństwa i Zapisz. Przycisk Zapisz nigdy nie interpretuje obiektu zdarzenia kliknięcia jako `forceBypassGuard=true`; kiedy wynik jest zablokowany, zapisu nie uruchamia. Żadnych nowych danych w UI, nowych operacji sieciowych ani logowania PII. W razie nieudanego buildu/niezgodnego nagłówka — STOP, bez zmiany CORS na wildcard.

## Istniejący owner i najmniejszy szew
- `frontend/src/theme.ts`: `Theme` ma reprezentować te same klucze palety z wartościami typu `string`, nie literalne heksy `DARK as const`; `DARK`, `LIGHT`, `T` i kolory zostają. Bez globalnego `any` jako obejścia typowania.
- `frontend/src/App.tsx`: nieistniejący `T.muted` zastąpić istniejącym `T.textMuted` tylko w ekranie ładowania.
- `frontend/src/screens/MainLayout.tsx`: usunąć cztery nieużywane `logoBadgeBg`, `logoBadgeText`, `logoNameColor`, `logoVerColor`; nie zmieniać renderowania logo.
- `frontend/src/screens/Pseudonimizuj.tsx`: `onClick={() => handleSave()}` zamiast `onClick={handleSave}` — nie wolno przekazać `MouseEvent` do parametru pozwalającego obejść Guard. Bez zmian w `/archive` ani w zasadach backendowego blokowania zapisu (osobne T13).
- `frontend/src/screens/SecurityScreen.tsx`: `Btn` przyjmuje opcjonalny callback; bez callbacku pozostaje nieaktywny (`disabled`) — nie wykonywać nieistniejącej funkcji. Zachować obsługę ładowania, kolorów i dwóch aktualnych miejsc wywołania.
31 błędów = 23 theme, 4 MainLayout, 1 App, 1 Pseudonimizuj, 2 SecurityScreen według audytu; przeliczyć na exact SHA przed poprawką, nie zakładać że lista jest aktualna.

TASK_SCOPE:
- frontend/src/theme.ts
- frontend/src/App.tsx
- frontend/src/screens/MainLayout.tsx
- frontend/src/screens/Pseudonimizuj.tsx
- frontend/src/screens/SecurityScreen.tsx

OUT_OF_SCOPE: backend, implementacja T02, zmiana CORS/tokenów/protokołu, Guard/archiwum po stronie serwera (T13), logowanie nagłówków w produkcyjnym kodzie, nowe pakiety, modyfikacja tsconfig/skryptu build przez wyłączenie `tsc`, `@ts-ignore`/`@ts-nocheck`/`any` jako metoda naprawy, kosmetyczny redesign, poprawa ikon RGB/ICNS (osobny BUILD-ICONS), pełne refaktory i testy archiwum T12.

## Sprawdzenie i granica przekazania
1. Minimalny dowód kodowy: `cd frontend && npm ci && npm run build` = exit 0, TypeScript 0 błędów i Vite generuje `dist/`; nie zastępować przez samo `npx vite build`. Raport BEFORE/AFTER na exact SHA, bez danych klienta.
2. Jeden punktowy smoke UI na syntetycznych danych: motyw jasny/ciemny, ekran ładowania, oba przyciski list bezpieczeństwa w stanie ładowania, Zapisz z niezablokowanym wynikiem i blokada przy zablokowanym wyniku. Nie obiecywać naprawienia całego BUG-S3-ARCHIVE-403-DEAD: backendowe `guard_blocked` jest w T13.
3. Na Windows: `cd frontend && npm run tauri build` (Tauri 2, aktualna `beforeBuildCommand` uruchamia npm build). Uruchomić zbudowane wydanie i zmierzyć rzeczywiste nagłówki HTTP `Origin` i `Host` przy żądaniu UI do `http://127.0.0.1:8765`; używać wyłącznie syntetycznego testu, bez treści dokumentów i tokenów w logu. Oczekiwane wg Tauri 2: `Origin: http://tauri.localhost`, `Host: 127.0.0.1:8765`, ale dokumentacja/symulacja NIE stanowią dowodu.
4. T02 jest na osobnej, niepołączonej gałęzi. Pomiar integracyjny musi dotyczyć wydania T10 z backendem dokładnie z audytowanego T02 `dc498366368b0b4d4767a61e6c6d56c939630713`; użyć izolowanego worktree/tymczasowego zestawienia, bez merge i bez przepisywania plików. Zapisać oba SHA i rzeczywiste dwa nagłówki. Potwierdzić, że uprawniony UI Express i standardowy widok mogą wywoływać właściwe endpointy, bez otwierania obcego Host/Origin.
5. Jeśli brak środowiska Windows albo build blokuje inny niezależny błąd narzędzi/ikon, raport `PARTIAL / BLOCKER` (z dokładną przyczyną); nie wydawać końcowego PASS wydania ani T02 tylko na podstawie `npm run build`. Nie poszerzać samodzielnie TASK_SCOPE.

PASS: `npm run build` zielony, bez zmian kontraktów UI i osłabienia S3; poprawiony `onClick` nigdy nie wywołuje `handleSave` z obiektem event; build i uruchomienie Windows potwierdzone, rzeczywiste `Origin`/`Host` zgodne z kontrolami T02. Przekazać dokładne SHA, wynik budowy, dowód nagłówków i ewentualne ograniczenia Codexowi do niezależnego audytu.
TEST ARCHIWUM: 7 starych przypadków z `backend/tests/test_archive_adversarial.py` otrzymuje zadanie T12-TEST-ISOLATION (poprawa fixture zgodnie z Host+auth), NIE T02 i NIE T10; Codex już odtworzył ich 7/7 PASS po ustawieniu poprawnego klienta tylko w pamięci.
WHERE_MAP:
- MODE: OPTIONAL
- TARGETS: frontend/src/screens/Pseudonimizuj.tsx --symbol handleSave
- REASON: poprawka typowania istniejącego callbacku, bez przenoszenia właściciela.
LIMIT: `gate.py`: maks. 2 nowe pliki, starych dużych plików nie powiększać, >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI. Nie implementować nic poza TASK_SCOPE.
