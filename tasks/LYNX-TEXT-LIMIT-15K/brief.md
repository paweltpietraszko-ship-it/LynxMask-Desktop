# LYNX-TEXT-LIMIT-15K — cały dokument zamiast cichego obcięcia do 15 000 znaków

STATUS: BRIEF_ONLY → Codex precheck → CC implementacja → Codex audyt exact SHA → merge wyłącznie na polecenie OWNERA.
AUTOR BRIEFU: CC (Paweł 2026-10-18: „możemy pisać briefy”). Krok **K0** z `arch/DIAGNOZA_2026-10-18.md` r2 (`4f6c380`, Codex AKCEPTUJĘ `9c4db4e`), klasa A7 (utrata treści).
PRODUCT_TRUTH: arch/spec.md S1, S2 (wierność: wynik odpowiada całemu dokumentowi), S3 (fail-closed: błąd jawny, nie cichy), S4 (Guard bez zmian), S5.
Źródło: BOARD `LYNX-TEXT-LIMIT-15K` (finding z przeglądu metody Codexa M3).

## Defekt (potwierdzony)

- `backend/pseudominizer_api.py`: `MAX_TEXT_CHARS = 15_000` (l. 129); `/preview` (l. ~369) i `/preview-express` (l. ~904): `text = text.strip()[:MAX_TEXT_CHARS]`. Reszta dokumentu nie jest maskowana ani zwracana, a użytkownik nie dostaje żadnej informacji. Odpowiedź API ma `original_text` = obcięty tekst, więc UI też nie wie o obcięciu.
- Skala (lokalny `backend/dataset_real_public`, wszystkie partie, `59c98cf`): **54 ze 178 dokumentów (30%) ma więcej niż 15 000 znaków**; KIO_uzp_15777: 63 507 → 15 000 (~76% poza przetwarzaniem).
- Wydajność silnika bez limitu (pełny tryb, prawdziwy SpaCy, pusty profil, CPU Pawła): 52–63 tys. znaków 1,8–2,6 s; 76–114 tys. 2,7–4,0 s; 186 tys. 11,2 s, 162 unikalne tokeny (limit `MAX_TOKENS_PER_REQUEST` = 500). Limit wydajnościowy 15 tys. nie jest dziś potrzebny.
- Istniejące twarde limity niżej w łańcuchu: `MAX_FILE_BYTES` 5 MB (plik), `anonymizer_init.INPUT_LIMIT_BYTES` 500 000 B (ValueError w `anonymize`), `MAX_TOKENS_PER_REQUEST` 500 (ValueError); oba ValueError dają dziś w `pipeline.py` blokadę prewencyjną („anonymizer blad … BLOKADA”) — jawną, ale bez czytelnego powodu dla użytkownika. `MAX_BLOB_BYTES` 512 KB dotyczy archiwum.

## Wymagane zachowanie

Paweł 2026-10-18: „Limit musi być zdjęty, od ciebie zależy kiedy”. CC: **teraz, w K0, przed zmianą S4** — ciche obcięcie to ukryta utrata treści (gorsza niż jawna blokada), a pomiar K1 wymaga całych dokumentów; wzrost blokad mierzony przed/po jako materiał dla LYNX-SPEC-S4-GUARD-WARN.

1. `/preview` i `/preview-express` przetwarzają **cały** wyekstrahowany tekst. Brak cichego obcięcia w jakimkolwiek miejscu.
2. Jedna górna granica długości, egzekwowana **jawnie przed pipeline**: tekst powyżej granicy → odpowiedź z czytelnym błędem dla użytkownika (np. „Dokument jest za długi (N znaków, limit M). Podziel go na części.”), `blocked`/kod HTTP spójny z istniejącymi błędami wejścia, bez częściowego wyniku. Wartość M = istniejący `INPUT_LIMIT_BYTES` przeliczony na znaki albo stała w API — do ustalenia w precheck; nie wolno wprowadzić wartości niższej niż najdłuższy dokument zbioru (186 tys.) bez uzasadnienia pomiarem.
3. Przekroczenie `MAX_TOKENS_PER_REQUEST` w długim dokumencie: zachowanie fail-closed bez zmian (S3), ale powód musi być rozróżnialny w odpowiedzi/logu od awarii (bez wartości PII). Nie podnosić limitu tokenów w tym Tasku bez pomiaru.
4. Archiwum: zapis (`/archive`) wyniku najdłuższego dokumentu zbioru nie może się po cichu nie udać przez `MAX_BLOB_BYTES`; jeśli przekracza — jawny błąd (pomiar w precheck/DELIVERY; zmiana limitu blobu tylko jeśli konieczna i uzasadniona).
5. Bez zmiany pipeline, warstw, Guarda i formatu tokenów. Bez przetwarzania w kawałkach (niepotrzebne przy zmierzonej wydajności; kawałkowanie łamałoby spójność mapy).

## Ryzyko do zmierzenia (nie do naprawy tutaj)

Dłuższy tekst = więcej szans na `MAP_LEAK` Guarda: 6 najdłuższych dokumentów zbioru jest dziś blokowanych w pełnej długości. Dopóki S4 blokuje (LYNX-SPEC-S4-GUARD-WARN otwarte), część dokumentów, które dziś dają obcięty wynik, zacznie dawać blokadę. DELIVERY: liczba blokad przed/po na 54 długich dokumentach, bez wartości. To uczciwszy stan (brak ukrytej utraty treści); kolejność ustalona wyżej (najpierw limit, S4 osobno).

TASK_SCOPE:
- backend/pseudominizer_api.py
- backend/tests/test_audyt_2026_10.py
- backend/tests/test_pseudominizer.py

OUT_OF_SCOPE: pipeline.py, pipeline_new.py, warstwy, anonymizer.py/anonymizer_init.py (limity bajtów/tokenów bez zmian), output_guard.py, frontend (komunikat błędu wyświetlany istniejącą ścieżką błędu — jeśli UI go nie pokazuje, zgłosić finding, nie zmieniać), ekstrakcja (`document_processor.py`), HerBERT, NER-MULTILINE. Zmiana wymagająca innego ownera — STOP i finding.

## Minimalny test falsyfikujący

1. `test_audyt_2026_10.py` (wzorzec `TestClient` bez lifespanu, jak testy T02): syntetyczny TXT > 15 000 znaków z unikalnym syntetycznym PESEL i nazwiskiem **tylko w ostatnich 1 000 znaków**: oba tryby `/preview` i `/preview-express` — `original_text` ma pełną długość, w wyniku brak tego PESEL/nazwiska, token obecny, Przywróć (symulacja) = pełne wejście. Na `59c98cf` ten test musi FAILOWAĆ (dowód falsyfikacji).
2. Tekst powyżej granicy M: czytelny błąd, brak częściowego wyniku, brak wartości w logu.
3. `test_pseudominizer.py::test_dlugi_dokument_bez_wycieku` — komentarz o obcinaniu do 15 000 nieaktualny: zaktualizować komentarz/oczekiwanie tak, by test sprawdzał całość (nie osłabiać asercji).
4. Lokalnie (bez repo): 54 dokumenty > 15 000 znaków z `dataset_real_public` — przed/po: długość przetworzona = wyekstrahowana, czas (max/mediana), blokady Guarda przed/po, przekroczenia limitu tokenów (0 oczekiwane), zapis do archiwum najdłuższego. Raport tylko liczby.
5. Standardowa suita bez nowych FAIL; testy wymagające backendu — z działającym backendem z gałęzi.

PASS: brak cichego obcięcia w obu endpointach; jawny błąd powyżej granicy; reproduktor z PII w końcówce przechodzi z FAIL do PASS; czasy zmierzone; blokady przed/po raportowane. Ocena okiem Pawła: KIO_uzp_15777 w działającym programie (koniec orzeczenia obecny w wyniku albo jawna blokada Guarda z powodem).

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pseudominizer_api.py --symbol preview
- TARGETS: backend/pseudominizer_api.py --symbol MAX_TEXT_CHARS
- REASON: wszystkie miejsca obcięcia i istniejące ścieżki błędów wejścia; brak innych użyć stałej.
GATE: zero nowych plików produktu; `pseudominizer_api.py` powyżej limitu rozmiaru — reguła „nie pogarszaj” (netto nie rośnie albo uzasadnienie); >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI. Codex: BRIEF_ONLY precheck wykonalności i zakresu, bez implementacji.
