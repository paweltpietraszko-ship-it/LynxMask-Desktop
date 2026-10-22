# LYNX-GUARD-B — etap B Guarda: panel decyzji Zakryj/Zostaw i blokada zapisu/kopii

22.10.2026, CC. Etap B zatwierdzonego kontraktu `LYNX-GUARD-RESIDUE` brief v2 (`52d8358`, Codex PASS r4, zgoda OWNERA 22.10) i S4 (`94a7954`).
Gałąź na etapie A (`task/LYNX-GUARD-A`, Codex PASS r2 `f47fdb9`). Uwagi CC U1–U5 i zgoda OWNERA na koszt: BOARD, wiersz LYNX-GUARD-RESIDUE.

## Zakres B (okno)
1. `frontend/src/screens/guardDecisions.ts` (nowy, czysta logika):
   - Zostaw = klucz z fragmentu i otoczenia (numery tokenów pominięte), tylko w pamięci bieżącego dokumentu (U2). Bez allowlisty i bez dysku.
   - Zakryj = token wstawiony w tekst bazowy:
     - słowo lub nazwa (≥3 litery) we wszystkich wystąpieniach w dokumencie, całe słowa;
     - numer albo krótka resztka tylko we wskazanym miejscu;
     - wartość obecna w mapie dostaje jej token (jedna wartość = jeden token; Przywróć daje postać z mapy — zaakceptowane przez OWNERA);
     - nowa wartość dostaje kolejny wolny numer typu (R5 FIRMA, R1/R2 OSOBA, kod pocztowy ADRES, reszta NUMER).
   - Ostrzeżenie bez decyzji = niezostawione i niezakryte.
2. `frontend/src/screens/GuardPanel.tsx` (nowy): lista ostrzeżeń, przy każdej pozycji fragment w kontekście, powód, Zakryj i Zostaw
   („Zostawione — cofnij”). Komunikat „Pozostało N ostrzeżeń…” stale widoczny, lista przewijana w stałej wysokości (U5).
3. `frontend/src/screens/Pseudonimizuj.tsx` (bez wzrostu):
   - `locked` = twarda blokada lub co najmniej jedno ostrzeżenie bez decyzji → Zapisz do biblioteki i Kopiuj tekst niedostępne (S4).
   - Usunięte: zbiorczy „To nie PII — zapisz mimo to”, `handleSave(forceBypassGuard)` i dopisywanie do jawnej `guard_allowlist.json` z okna.
   - Zakryte tokeny trafiają do zapisanej listy tokenów (Przywróć w bibliotece).
   - Decyzje Zakryj/Zostaw przeżywają „Dodaj i zakryj” (ponowne przeliczenie).
   - Odkryj działa przy ostrzeżeniach; odkrycie to decyzja użytkownika dla tego miejsca (S4/U1), Guard go nie ocenia.
   - Tryb Express: ten sam panel (Zakryj lokalnie, bez profilu); kopia też zablokowana do rozstrzygnięcia.

Poza zakresem: dopisywanie Zakryj do słownika biura (istnieje osobne „Dodaj i zakryj”), szyfrowana allowlista / „zapamiętaj” (S5, osobno),
rejestr decyzji (`LYNX-GUARD-DECISION-LOG`), zmiany backendu.

TASK_SCOPE:
- frontend/src/screens/guardDecisions.ts
- frontend/src/screens/GuardPanel.tsx
- frontend/src/screens/Pseudonimizuj.tsx
- frontend/tests/guardDecisions.test.mjs
- tasks/LYNX-GUARD-B/brief.md
- tasks/LYNX-GUARD-B/repo_before.hash

Wzrost powyżej 150 linii: zgoda OWNERA na koszt etapu B (~200–250 l. + testy) udzielona 22.10 (BOARD).

## Odbiór
- `node --test tests/guardDecisions.test.mjs tests/revealText.test.mjs` (Node 24): blokada do decyzji przy każdej pozycji, Zostaw tylko wskazanego
  wystąpienia, Zakryj wszystkich wystąpień słowa jednym tokenem, MAP_LEAK → token z mapy i Przywróć, resztka numeru tylko w miejscu, klucz
  Zostaw odporny na przenumerowanie tokenów.
- `tsc --noEmit` czysto.
- Oglądowo w aplikacji (OWNER/CC): dokument z kilkoma ostrzeżeniami — przed decyzjami i po części brak zapisu/kopii, po wszystkich dostępne;
  długa lista przewija się.
