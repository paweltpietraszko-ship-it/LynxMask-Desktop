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

4. **Zakryj → słownik biura (OWNER 22.10: „jeśli zakryte encje nie będą budowały słownika biura, to jest bez sensu”):**
   - przełącznik „Zapamiętaj zakryte w słowniku biura” nad listą, domyślnie zaznaczony;
   - wyjaśnienie pod znakiem „?” (podpowiedź po najechaniu);
   - przy zaznaczonym Zakryj woła istniejące `/profile/add-entity` (szyfrowany profil, S5) dla słów/nazw ≥3 litery i identyfikatorów ≥5 znaków
     (nie: pojedyncza cyfra, inicjał, rok);
   - błąd zapisu słownika → komunikat, zakrycie w dokumencie zostaje;
   - Express bez przełącznika (brak profilu).
   Zostaw i Odkryj — zawsze tylko bieżący dokument; trwałe „nie zakrywaj w przyszłości” dopiero z szyfrowaną allowlistą (osobne zadanie, S4/S5).

Poza zakresem: szyfrowana allowlista / „zapamiętaj” (S5, osobno),
rejestr decyzji (`LYNX-GUARD-DECISION-LOG`), zmiany backendu.

TASK_SCOPE:
- frontend/src/screens/guardDecisions.ts
- frontend/src/screens/GuardPanel.tsx
- frontend/src/screens/Pseudonimizuj.tsx
- frontend/tests/revealText.test.mjs
- tasks/LYNX-GUARD-B/brief.md
- tasks/LYNX-GUARD-B/repo_before.hash
- backend/guard_residue.py
- backend/tests/test_guard_residue.py

Wzrost powyżej 150 linii: zgoda OWNERA na koszt etapu B (~200–250 l. + testy) udzielona 22.10 (BOARD).

## ROZSZERZENIE CC (22.10, ta sama klasa — zakres ostrzeżenia R5 z etapu A)
Co: R5 z roli kontrahenta brał też początek następnego zdania. Wykryte sondą `/preview` silnika z gałęzi przed oglądem OWNERA.
Gdzie: `backend/guard_residue.py` `_r5` (`_SENTENCE_END_RE`).
Reproduktor: „Sprzedawca: Biuro Rachunkowe RACHMISTRZ. Wczoraj …” → fragment „Biuro Rachunkowe RACHMISTRZ. Wczoraj”.
Poprawka: cięcie na końcu zdania (kropka + słowo z wielkiej litery), forma prawna z kropką („S.A.”) zostaje.
Testy: 2 przypadki w `backend/tests/test_guard_residue.py`.

## Odbiór
- `node --test tests/revealText.test.mjs` (testy decyzji dopisane do istniejącego pliku — limit nowych plików gate) (Node 24): blokada do decyzji przy każdej pozycji, Zostaw tylko wskazanego
  wystąpienia, Zakryj wszystkich wystąpień słowa jednym tokenem, MAP_LEAK → token z mapy i Przywróć, resztka numeru tylko w miejscu, klucz
  Zostaw odporny na przenumerowanie tokenów.
- `tsc --noEmit` czysto.
- Oglądowo w aplikacji (OWNER/CC): dokument z kilkoma ostrzeżeniami — przed decyzjami i po części brak zapisu/kopii, po wszystkich dostępne;
  długa lista przewija się.
