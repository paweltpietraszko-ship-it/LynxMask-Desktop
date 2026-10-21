# LYNX-MANUAL-REVEAL — DELIVERY r1 (CC, 2026-10-21)

Brief v5 `dc36d38c6721994affc563c83dd2f76cae5a174e` (+ TASK_SCOPE CC `f6e5671fbfb2e7efbc6166b6ab059566fa04e70c` = BEFORE dla gate),
precheck Codexa r4 `595a2f3`. HEAD implementacji: `a75e73cb0c7653b0caf7229bab98179bc03f5d59`.

## Gate (stdout dosłownie)
```
STATUS: PASS
HEAD_SHA: a75e73cb0c7653b0caf7229bab98179bc03f5d59
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
EXCLUDED_ARTIFACTS: NONE
```
Rozmiar: +119/−26 (`Pseudonimizuj.tsx` +30/−26 → 929→933 l.; `revealText.ts` 42; test 47).

## Co zrobione
- `frontend/src/screens/revealText.ts` (nowy, czyste funkcje): `segments` (tekst bazowy → zwykły tekst / tokeny z pozycją `at`),
  `finalText` (zawsze liczony od niezmiennej bazy `anonymized_preview` — bez kolejnych zamian i przesunięć offsetów), `toggleReveal`
  (przełącza jedno wystąpienie; bez wartości w mapie nie odkrywa). `TOKEN_RE` przeniesione bez zmian (S2).
- `Pseudonimizuj.tsx`: `HighlightedText` na `segments`; klik / Enter na tokenie = odkryj/cofnij **tylko to wystąpienie** (podpowiedź
  pokazuje całą wartość przed odkryciem; odkryte — czerwone podkreślenie jak Mobile); stan odkryć tylko w React; nowy wynik
  (`setResult`: nowy dokument, ponowne `/preview`, „Dodaj i zakryj”) czyści odkrycia (`useEffect` na `result`); **jedna wartość
  `shownText`** dla podglądu, „Kopiuj tekst” i zapisu do archiwum (`anonymized_preview` w zaszyfrowanym blobie). Przy `guardBlocked`
  tokeny nieklikalne, tekst pomocniczy ukryty, `shownText` = baza (także w „Zapisz mimo blokady”). Backend, Guard, API, mapa — bez zmian.
- Tekst pomocniczy (v5): „Jeśli LynxMask zakrył coś niepotrzebnie, kliknij token, żeby odkryć tylko to miejsce. Odkryta wartość
  znajdzie się także w kopiowanym i zapisanym tekście.”

## Testy
- `cd frontend && node --test tests/revealText.test.mjs` → **6 pass** (Node 24, bez nowych zależności): przykład „Róży” z nagłówkiem
  PSE (dokładny tekst z briefu), trzy wystąpienia + cofnięcie jednego, wielowyrazowy token w całości z zachowaniem innych tokenów
  i interpunkcji, brak wartości w mapie, baza bez odkryć = identyczna, token z cyfrą za numerem nie jest tokenem (S2).
- `npx tsc --noEmit -p frontend` → bez błędów.
- **NOT_CHECKED:** klikanie w działającym oknie aplikacji przed merge (okno pobiera token przez Tauri; wymagałoby pełnego buildu
  debug ~2 GB). Plan: po merge przebudowa release i ocena okiem OWNERA. Do oceny Codexa: podgląd = kopia = archiwum (jedna zmienna
  `shownText` — sprawdzalne w kodzie), reset przy nowym wyniku, brak odkrywania przy `guardBlocked`.

## Odstępstwo od briefu (za zgodą OWNERA 21.10)
Dwa nowe pliki zamiast „bez nowego modułu”: `Pseudonimizuj.tsx` ma >600 l. i nie może rosnąć (zasada OWNERA) → logika w `revealText.ts`;
front nie miał testów → `node --test`. S4/lock z gałęzi (Architekt, `e22866e`/`cc65fe5`) nietknięte przez CC.

## Poprawka F1 (Codex r5 `86cf82d`) — HEAD `777af057bc177a33b0c927f499bfa5531e32caad`
Klik odkryj/cofnij ustawia `saved=false` → po wcześniejszym zapisie znika „Zapisano”, wraca formularz zapisu i można zapisać
aktualny `shownText`. Ponowny zapis tego samego PSE nadpisuje `MAPS_DIR/<PSE>.enc` atomowo (`/archive`, zapis przez .tmp) —
bez zmian backendu. Gate (dosłownie): `STATUS: PASS`, `HEAD_SHA: 777af057bc177a33b0c927f499bfa5531e32caad`. `tsc` bez błędów, `node --test` 6 pass.
Recheck Codexa: scenariusz zapis → odkryj/cofnij → stan → ponowny zapis (`ui_harness_r5.cjs`).
