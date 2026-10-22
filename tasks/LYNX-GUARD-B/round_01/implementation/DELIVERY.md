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
