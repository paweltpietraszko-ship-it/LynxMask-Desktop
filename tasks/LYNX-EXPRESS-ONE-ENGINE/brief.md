# LYNX-EXPRESS-ONE-ENGINE — Express to ten sam silnik; usunięcie martwej ścieżki „bez NER”

STATUS: brief CC, **obieg skrócony na polecenie Pawła**: CC → Codex precheck (przed kodem) → CC implementacja → Codex audyt exact-SHA → merge na słowo Pawła. Architekt: informacja w BOARD.
POCHODZENIE: `tasks/LYNX-EXPRESS-ONE-ENGINE/cc_proposal.md` (ustalenia i pomiary). Paweł: „Ekspress Mode … miała być tylko pozbawiona biblioteki i depseudonimizacji … To miał być ten sam silnik.” Odpowiedzi Pawła na pytania z propozycji (2026-10-18): (1) baner zmienić — „tak”; (2) „to nie PII” w Express — „ukryty”; (3) obieg — „skrócony”.
PRODUCT_TRUTH: S1, S3, S6. Bez zmian S2/S4, TOKEN_RE, logiki silnika.

## Kontrakt
1. **Jedna ścieżka maskowania.** Tryb Express maskuje wyłącznie przez `POST /preview` (pełny pipeline: NER, Guard, profil). Nie istnieje żaden endpoint ani funkcja pipeline'u maskująca z pominięciem NER/Guarda:
   - `POST /preview-express` → 404 (endpoint usunięty);
   - `run_pipeline_express` usunięta;
   - `_EXPRESS_PATHS` = tylko `("POST", "/preview")`.
2. **Token Express** (LYNX-T02) bez zmian zakresu: tylko `POST /preview`. Archiwum, profil, allowlista i pozostałe → 401.
3. **Wynik Express = wynik pełny** dla tego samego dokumentu (ten sam silnik, ten sam profil).
4. **UI Express** (`MainLayout` przekazuje `expressMode` do `Pseudonimizuj`):
   - w trybie Express niewidoczne są przyciski wymagające logowania: zapis do archiwum, dodanie encji do profilu, „to nie PII” (allowlista);
   - ostrzeżenie Guarda, blokada i wyłączone „Kopiuj” przy blokadzie działają bez zmian;
   - baner w panelu: „⚡ Tryb Express — bez logowania” + „Biblioteka i odmaskowanie dostępne po zalogowaniu.” zamiast „Tryb demonstracyjny”.
5. **Sprzątanie:** usunięty nieużywany `ExpressModeScreen.tsx`. Docstringi i komentarze opisujące Express jako „bez SpaCy/NER” poprawione (`pipeline_new.py`, nagłówek `pseudominizer_api.py`, `LockScreen.tsx`).
6. Tryb pełny (zalogowany) bez zmian zachowania.

## Testy i falsyfikacja
- Nowy `backend/tests/test_express_one_engine.py` (TestClient, prawdziwy silnik jak `test_failclosed`):
  - `/preview-express` → 404;
  - ten sam syntetyczny dokument z osobą, firmą i PESEL przez `/preview` z tokenem Express i z tokenem pełnym → identyczne `anonymized_preview` i `tokens`, osoba zamaskowana;
  - token Express na `/archive` i `/profile/add-entity` → 401.
- Istniejące testy używające martwej ścieżki:
  - `test_failclosed.py`: przypadki `/preview-express` przenieść na `/preview` z tokenem Express;
  - `test_layers.py`, `test_map_fidelity.py`, `test_audyt_2026_10.py`: parametryzacja `express` / `run_pipeline_express` usunięta. Przypadek pełny pozostaje.
  - Reproduktor `BUG-EXPRESS-FAIL-OPEN` (zamknięty w FAILCLOSED) dotyczył usuwanej funkcji, więc usunąć go z komentarzem „ścieżka usunięta w LYNX-EXPRESS-ONE-ENGINE”.
  - Testy `api_client` dla `/preview-express` przenieść na `/preview`.
- `audyt/rota_leak_test.py`: tryb `express` usunięty (skrypt pomiarowy, nie produkt).
- Pomiar: 178 dok. `dataset_real_public` przez działający `/preview` z profilem Pawła:
  - token Express vs pełny → 0 różnic;
  - wynik pełny vs main przed zmianą → 0 różnic;
  - `/preview-express` → 404.
- `tsc --noEmit` 0. Suita `tests/` na backendzie gałęzi. Regresje: `test_failclosed`, `test_startup_check`, `test_layers`, `test_map_fidelity`, `test_audyt_2026_10`.
- UI: ocena okiem Pawła po `npm run tauri build`. Express wygląda jak Pseudonimizuj, bez przycisków wymagających logowania, z nowym banerem.

TASK_SCOPE:
- backend/pseudominizer_api.py
- backend/pipeline_new.py
- frontend/src/screens/ExpressModeScreen.tsx
- frontend/src/screens/LockScreen.tsx
- frontend/src/screens/MainLayout.tsx
- frontend/src/screens/Pseudonimizuj.tsx
- backend/tests/test_express_one_engine.py
- backend/tests/test_failclosed.py
- backend/tests/test_layers.py
- backend/tests/test_map_fidelity.py
- backend/tests/test_audyt_2026_10.py
- audyt/rota_leak_test.py

DELETED: `frontend/src/screens/ExpressModeScreen.tsx` (zadeklarowany w TASK_SCOPE).
OUT_OF_SCOPE: silnik i warstwy (poza usunięciem `run_pipeline_express`), Guard, `/express/token` (bez zmian), Tauri, Biblioteka/Odmaskuj, LYNX-APP-LAUNCHER.

## Rozmiar (szacunek CC; Paweł 2026-10-18 przed kodem: „Akceptuję rozmiar”)
Usunięcia ok. 800 linii (ekran 621, endpoint ok. 65, funkcja ok. 40, parametryzacje testów i docstringi). Dodane ok. 110 (nowy test ok. 60, UI ok. 25, przeniesienia testów). Plik API (legacy) zmniejsza się o ok. 70 linii. Gate zgłosi TOTAL > 150 z powodu usunięć.
