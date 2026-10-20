# Recenzja Architekta — LYNX-OCR-GATE-COMPARE v3.1

DATA: 2026-10-20
PODSTAWA: brief CC `e8c004b50a064b8ac424efadf876f43d7dd49dcc` (blob `289ef69d`), BOARD → TERAZ, wcześniejszy review `5154057`, bieżące `AGENTS.md`, `gate.py`, `backend/pseudominizer_api.py::preview`, `document_processor._next_pse`, `audit_log.record_preview`.

WERDYKT: **KIERUNEK ZAAKCEPTOWANY; WĄSKA KOREKTA KONTRAKTU PRZED BRIEF_ONLY CODEXA.** C1–C4 z poprzedniej recenzji zostały w istotnej części zamknięte. Nie proponuję drugiej architektury ani rozbijania pracy na osobne Taski. Jeden Task może zawierać dwa etapy, ale musi mieć audytowalne granice.

## F1 — TASK_SCOPE zawiera 3 nowe pliki, GATE dopuszcza 2 (BLOCKER formalny)

Obecna lista:
- `tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py` (nowy)
- `backend/tests/test_ocr_chain_compare.py` (nowy)
- `backend/tests/test_ocr_chain_anchor_fixes.py` (nowy)
- `backend/layers/identity.py` oraz `backend/layers/numeric.py` (istniejące).

`gate.py` ma `MAX_NEW_FILES=2`. W briefie jednocześnie wpisano „dwa nowe pliki”, a lista podaje trzy. **Korekta minimalna:** testy etapu 2 dopisać do `backend/tests/test_ocr_chain_compare.py` (lub innego istniejącego testu) i usunąć z TASK_SCOPE nowy `test_ocr_chain_anchor_fixes.py`. Nie poszerzać limitu ani nie rozdzielać Tasku.

## F2 — etap 2 nie może zmienić znaczenia eksperymentu po obejrzeniu holdoutu

Ustalenie OWNERA „jeden blok zdjęcia” respektuję. W obrębie tej samej gałęzi potrzebna jest **bramka wewnętrzna**:
1. ETAP 1: zamrozić skrypt, reguły, N i raport 50/100 na exact SHA; zapisać werdykt, wszystkie `HOLE`/`UNKNOWN_REVIEW`, odrzucone obrazy i przyczyny. W raporcie uczciwie odróżnić wyniki przed poprawkami od wyników po nich.
2. ETAP 2: tylko reprodukowalne błędy klasy „kotwica + uszkodzona wartość” przypisane do istniejącego ownera, z testem padającym **przed** poprawką i PASS po poprawce. Nie poprawiać arbitralnie wszystkiego, co nazwano `UNKNOWN_REVIEW`; nie interpretować każdej `HOLE` jako błędu silnika, bo może to być błąd OCR, metryki lub hipotetycznego Guarda. Jeśli brak tego rodzaju potwierdzonych findingów, ETAP 2 = `NO_CHANGE`. Nie zmieniać N/definicji dziury po zobaczeniu wyników.
3. Po poprawce testy celowane + dotychczasowy benchmark regresyjny + ponowienie porównania. Ponowne 100 obrazów to **regresja na już obejrzanym zbiorze**, a nie nowy, nietknięty holdout dowodzący uogólnienia. Kryterium `READY_FOR_PRODUCT_BRIEF` przypisać jawnie do wyniku bazowego i po poprawkach, z ograniczeniem dowodowym.

To dwie rundy pracy **w jednym Tasku**. Codex może dostać końcowy exact SHA i oba zestawy dowodów; wcześniejszy stan etapu 1 musi zostać zapisany tak, by można było wykryć poprawianie miarki pod wynik.

## Dwie drobne uwagi do zamknięcia redakcyjnie

- Nazwa `REAL_PIPELINE`: `/preview` przyjmuje w eksperymencie **tekst .txt z osobno uruchomionego OCR**, a nie samo zdjęcie. To rzeczywisty silnik maskowania/aktualny Guard, lecz nie jest produkcyjnym E2E „obraz → /preview”. Proszę nazwać zakres dokładnie, np. `REAL_MASKING_PIPELINE`, a produkcyjne E2E wyraźnie pozostawić do briefu wdrożenia. `would_ask` nadal tylko symulacja, a nie dowód wstrzymania wysyłki.
- W P1 cztery odczyty PP oznaczają z natury ok. 4× czas jednego; warunek uruchomienia P2 `P1 > 4 × czas` może być spełniany niemal automatycznie przez overhead. Podać cel użytkowy/czas całkowity lub uczciwy limit względem jednego odczytu, żeby P2 nie stał się niejawnie obowiązkowy. Brak wiarygodnego ONNX → `NOT_RUN(P2)`.

## Podsumowanie

Akceptuję definicje `MASKED/ASKED/HOLE/UNKNOWN_REVIEW/NOT_IN_OCR`, izolację przez zmienne środowiskowe i katalog tymczasowy, rozdział hipotetycznego Guarda/HerBERT od realnego pipeline, regułę odmowy z pełnym mianownikiem oraz porównanie według z góry ustalonych kryteriów. `READY_FOR_PRODUCT_BRIEF` oznacza wyłącznie gotowość do napisania kontraktu wdrożenia, nie certyfikat bezpieczeństwa.

Po poprawce F1/F2 i dwóch uwag: **Codex BRIEF_ONLY**, następnie CC szacuje ostateczny rozmiar i uzyskuje zgodę OWNERA przed kodowaniem. Nie zmieniaj produktu w ramach samej recenzji.
