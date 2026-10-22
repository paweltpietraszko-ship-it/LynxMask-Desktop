# DELIVERY — LYNX-GUARD-B (etap B Guarda: okno), CC 22.10.2026

Gałąź `task/LYNX-GUARD-B` na `task/LYNX-GUARD-A` (Codex PASS r2 `f47fdb9`), kod `21effb1`. Brief: `tasks/LYNX-GUARD-B/brief.md`.

## gate.py (dosłownie, `round_01/gate_r2.txt`)
```
STATUS: WYMAGA_DECYZJI
WYMAGA_DECYZJI:
  - TOTAL_LINES: 307 lines changed (threshold 150)
```
Rozmiar zatwierdzony przez OWNERA 22.10 (BOARD). r1: FAIL NEW_FILES 3 > 2 — testy decyzji przeniesione do istniejącego `revealText.test.mjs`.

## Zmiany
- `guardDecisions.ts` (67 l., logika bez UI):
  - `warningKey` = fragment + otoczenie ±24 znaki, numery tokenów pominięte;
  - `applyCovers`;
  - `coverWarning`: słowa ≥3 litery we wszystkich wystąpieniach (całe słowa), numery/resztki tylko w miejscu, wartość z mapy → jej token, inaczej kolejny wolny numer typu;
  - `pendingWarnings`.
- `GuardPanel.tsx` (62 l.): licznik „Pozostało N…” stale widoczny; lista przewijana w `maxHeight: 38vh`; przy pozycji kropka RED/YELLOW, kontekst z pogrubionym fragmentem, powód, Zakryj / Zostaw / „Zostawione — cofnij”.
- `Pseudonimizuj.tsx` (933 → 895 l.):
  - `locked = guardBlocked || pending.length > 0` blokuje Kopiuj tekst i Zapisz;
  - usunięte: zbiorczy „To nie PII — zapisz mimo to”, `handleSave(forceBypassGuard)`, stan `addingAllowlist` i zapis do `/profile/guard-allowlist` z okna;
  - zakrycia liczone z kluczy (`covered`), więc przeżywają „Dodaj i zakryj”; nowe tokeny dopisane do zapisanej listy (Przywróć w bibliotece);
  - Odkryj działa przy ostrzeżeniach (S4: decyzja użytkownika);
  - komunikat twardej blokady według briefu v2.

## Testy
- `node --test tests/revealText.test.mjs` (Node 24.15): **13 pass, 0 fail**: 6 dotychczasowych testów reveal i 7 nowych testów decyzji.
- `tsc --noEmit`: exit 0.
- Backend bez zmian względem A.

## Do sprawdzenia oglądowo
- Build release z gałęzi do osobnego katalogu (bez nadpisania aplikacji OWNERA).
- Silnik z gałęzi do testu oczami. Wynik oglądu OWNERA dopiszę.

## Uwagi
- Zakryj działa tylko w bieżącym dokumencie i nie dopisuje do słownika biura. Do tego służy istniejące „Dodaj i zakryj”. Ewentualne automatyczne dopisywanie to decyzja OWNERA na później.
- Zostaw nie trafia na dysk ani do allowlisty (S5).
- Endpointy `/profile/guard-allowlist` w backendzie zostają (poza zakresem B). Okno ich już nie wywołuje.

## ROZSZERZENIE CC (kod `f7f4e03`)
Sonda `/preview` silnika z gałęzi przed oglądem OWNERA: R5 z roli brał początek następnego zdania („Biuro Rachunkowe RACHMISTRZ. Wczoraj”).
Poprawka w `backend/guard_residue.py` `_r5` (`_SENTENCE_END_RE`); forma prawna z kropką („GAMMA S.A.”) zostaje. Sekcja w briefie + TASK_SCOPE.
`test_guard_residue.py` 41 passed (+2), `test_failclosed.py` 23 passed, ruff czysto, pomiar `rerun_cc.py` bez zmian (25 / 150 dok.).
Sonda po restarcie silnika: `Biuro Rachunkowe RACHMISTRZ` (R5), `Śludkowskiego` (R1), `128/7` (R4); pozycje zgodne z `anonymized_preview`.
gate r3 (`round_01/gate_r3.txt`): `STATUS: WYMAGA_DECYZJI` — tylko rozmiar.

## Runda 1b — Zakryj → słownik biura (OWNER 22.10), kod `58d2872`
- Przełącznik „Zapamiętaj zakryte w słowniku biura” jest nad listą, domyślnie zaznaczony. Wyjaśnienie jest pod „?” (`title`).
- Zakryj woła `/profile/add-entity` (typy OSOBA/FIRMA/NUMER/ADRES) tylko dla `rememberable`: słowa ≥3 litery albo identyfikatory ≥5 znaków z cyfrą, z wyjątkiem samego roku.
- Gdy endpoint odmówi (np. słowo pospolite), pojawia się komunikat, a zakrycie w dokumencie zostaje.
- Express: bez przełącznika.
- Zostaw i Odkryj dotyczą tylko bieżącego dokumentu (S4). Trwałe „nie zakrywaj” to osobne zadanie z szyfrowaną allowlistą.
- `node --test tests/revealText.test.mjs`: 14 pass. `tsc`: 0. `Pseudonimizuj.tsx`: 912 l. (baza 933).
- gate r4: `STATUS: WYMAGA_DECYZJI` — tylko rozmiar.

## Runda 2 — poprawki F1–F3 (Codex r1 `40c4b25`), kod `0f3f855`
- **F1 (pozycje Python → JS):** API zostaje bez zmian (punkty kodowe).
  - `guardDecisions.ts` `at16`: gdy pozycja nie wskazuje fragmentu, przelicza punkty kodowe na UTF-16 i przyjmuje wynik tylko wtedy, gdy wskazuje dokładnie fragment. Gdy pozycja jest już poprawna, nic nie zmienia.
  - Używane w środku `coverWarning`, `pendingWarnings` i `warningKey`, więc bezpieczne także przy wywołaniu bez przeliczenia, jak w reproduktorze. Ekran dodatkowo raz woła `toUtf16`.
  - Format tokenów bez zmian.
- **F2 (częściowe zakrycie):**
  - `pendingWarnings`: ostrzeżenie jest rozstrzygnięte tylko wtedy, gdy każda litera i cyfra w jego zakresie jest zakryta.
  - `coverWarning`: zakrycia leżące w środku wskazanego miejsca zastępuje jeden token całej wartości („Rogalik i KOWALCZYK sp. k.” → `FIRMA_001`).
- **F3 (granica słowa):** `[\p{L}\p{N}_]` zamiast `\w`; „Kawałek” zostaje w całości.
- **Testy:**
  - reproduktor Codexa `node tasks/LYNX-GUARD-B/round_01/tests/repro_r1.mjs`: `failures=0` (7/7);
  - `node --test tests/revealText.test.mjs`: 17 pass, w tym 3 nowe (F1 emoji, F2 Rogalik/KOWALCZYK, F3 Kawałek);
  - `tsc`: 0;
  - `Pseudonimizuj.tsx` 914 l. (baza 933).
- **gate r6:** `STATUS: WYMAGA_DECYZJI` — tylko rozmiar.
