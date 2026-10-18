# LYNX-EXPRESS-ONE-ENGINE — Express to ten sam silnik; usunięcie martwej ścieżki „bez NER”

STATUS: cc_proposal (CC) → Architekt lub obieg skrócony (decyzja Pawła) → Codex precheck → CC implementacja → Codex audyt → merge na słowo Pawła.
POCHODZENIE: Paweł 2026-10-18: „nigdy nie mówiłem, że Express Mode to uboższa wersja pod względem maskowania. Ona miała być tylko pozbawiona biblioteki i depseudonimizacji. … To miał być ten sam silnik.”
PRODUCT_TRUTH: S1 (żadne PII nie wychodzi), S3 (fail-closed), S6 (UI). Bez zmian S2/S4.

## Ustalenia (CC, 2026-10-18, main `63f2658`)
1. **Express w aplikacji JUŻ używa pełnego silnika.**
   - Ekran blokady → „Express Mode — bez logowania” → `App.tsx` pobiera token z `GET /express/token` → `MainLayout` z ekranem `Pseudonimizuj` → `POST /preview` z tokenem Express. Ścieżka ta obejmuje pełny pipeline z NER i Guardem.
   - Biblioteka i Odmaskuj są wyszarzone, a w panelu bocznym jest baner „Tryb demonstracyjny”.
   - **Pomiar na 178 dok. `dataset_real_public` przez działający `/preview`:** token pełny i token Express dają **0 różnic** (wynik, tokeny, blokady), w obu przypadkach 811 tokenów OSOBA.
2. **Obok żyje martwa, uboższa ścieżka z pierwszej wersji (27.06, commity `6eeef00`, `207c4f1`).** Commit `ec0fc60` („Express Mode: pełny pipeline”) z tego samego dnia zastąpił ją pełnym pipeline'em, ale starych elementów nie usunął:
   - `frontend/src/screens/ExpressModeScreen.tsx` — nigdzie nieimportowany (`git grep`). Ma etykietę „⚡ Express · bez NER” i woła `/preview-express`;
   - `POST /preview-express` w `pseudominizer_api.py` — **działa i jest dostępny z tokenem Express** (`_EXPRESS_PATHS`). Woła `run_pipeline_express` bez NER, profilu w zakresie walidacji, Guarda i inicjałów. Pomiar na tych samych 178 dok.: **0 tokenów OSOBA i 0 FIRMA**;
   - `pipeline_new.run_pipeline_express` oraz docstringi („Express Mode — pipeline bez SpaCy/NER”).
3. **Skutek:** każdy model i audytor czytający kod (w tym CC w ocenie planu bezpieczeństwa i w FAILCLOSED, raporty Codexa, testy `test_failclosed`, `test_audyt_2026_10`, `test_layers`, `test_map_fidelity`) uznawał tę martwą ścieżkę za „tryb Express”. Do tego otwarty endpoint, który nie maskuje osób, to niepotrzebna powierzchnia ryzyka (S1). Każdy klient z tokenem Express może go wywołać.
4. **Usterka UI w Express:** `Pseudonimizuj.tsx` nie wie, że działa w trybie Express. Zapis do archiwum, dodanie encji do profilu i „to nie PII” (allowlista) dostają 401, bo token Express obejmuje tylko `/preview` (LYNX-T02). Użytkownik widzi przyciski, które nie działają.

## Propozycja zakresu
A. **Jedna ścieżka maskowania.** Usunąć:
   - `POST /preview-express`;
   - `run_pipeline_express`;
   - `ExpressModeScreen.tsx`;
   - wpis `/preview-express` w `_EXPRESS_PATHS`.
   Poprawić docstringi i komentarze (`pipeline_new.py`, nagłówek API, `LockScreen.tsx`). Token Express pozostaje ograniczony do `POST /preview`.
B. **Testy:** przypadki z `/preview-express` i `run_pipeline_express` w `test_failclosed.py`, `test_layers.py`, `test_map_fidelity.py` i `test_audyt_2026_10.py` przenieść na `/preview` z tokenem Express (to jest prawdziwy tryb Express) albo usunąć, gdy dublują Full. Reproduktor BUG-EXPRESS-FAIL-OPEN zostaje zamknięty przez usunięcie ścieżki, a nie przez naprawę. Nowy test: `/preview-express` → 404; token Express na `/preview` daje ten sam wynik co pełny token; token Express na `/archive`, `/profile/*` → 401.
C. **UI Express:** w `Pseudonimizuj` przyciski wymagające logowania (zapis do archiwum, dodanie do profilu, „to nie PII”) w trybie Express są ukryte albo wyłączone z dopiskiem „dostępne po zalogowaniu”. Ostrzeżenie Guarda i blokada działają bez zmian.
D. **Pomiar:** 178 dok. przez `/preview`: token pełny vs token Express daje 0 różnic. Wynik trybu pełnego jest identyczny jak przed zmianą.

## Pytania do Pawła (przed briefem)
1. Baner „⚡ Tryb demonstracyjny” sugeruje wersję pokazową. Czy ma brzmieć np. „Tryb Express — bez logowania; Biblioteka i odmaskowanie po zalogowaniu”?
2. „To nie PII” (allowlista) w Express: przycisk ukryty, czy działa tylko na tę sesję, bez zapisu do profilu biura? Rekomendacja CC: ukryty. Allowlista to zmiana profilu biura, a ta wymaga zalogowania.
3. Obieg: skrócony (CC → Codex), jak przy STARTUP-COMPONENTS, czy przez architekta?

## Szacunek rozmiaru
Głównie usuwanie: `ExpressModeScreen.tsx` −621, API około −50, `pipeline_new` około −40, testy ±60. UI Express (C) około +30. Netto wyraźnie ujemne, ale gate zgłosi TOTAL > 150 z powodu usunięć — do potwierdzenia przez Pawła przed kodem.

## Testy odbioru
`/preview-express` → 404. Token Express na `/preview` = wynik pełny (178 dok., 0 różnic). Token Express na zapis i profil → 401, a w UI brak martwych przycisków. Wynik pełny bez zmian względem main. Ocena okiem Pawła: Express na ekranie wygląda jak Pseudonimizuj, bez przycisków wymagających logowania.
