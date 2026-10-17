# LYNX-DOCX-TABLES — odczyt pól tabel DOCX przed maskowaniem

STATUS: BRIEF_ONLY → precheck Codexa → CC review/implementacja → audyt Codexa exact SHA → merge tylko OWNER.
PRODUCT_TRUTH: `arch/spec.md` S1/S2/S3/S4/S5; `BOARD.md` LYNX-PUBLIC-DATA-TESTS (MERGED) i finding LYNX-DOCX-TABLES; `tasks/LYNX-PUBLIC-DATA-TESTS/round_01/implementation/DELIVERY.md` (etap 1, próbka gov.pl: DOCX/tabela 3/3 EXTRACTION_MISSING, akapit 1 masked, PDF/tekst 3 masked); `backend/document_processor.py::_extract_text`; `audyt/engine_quality.py --layout` i `backend/tests/test_engine_quality_layout.py`.
OWNER_PROPOSAL 2026-10-17: po merge etapu 1 naprawić pomijanie tabel DOCX. OCENA ARCHITEKTA: kolejność zasadna — dane w pominiętych tabelach nie są przekazywane do silnika. To nie jest dowód, że dziś eksportuje się je jawnie do AI; przy przyszłej funkcji zachowania układu dokumentu byłoby to ryzyko. Bez automatycznej zgody na merge.

## Cel i minimalny szew
`document_processor._extract_text(bytes, filename)` w gałęzi `.docx` czyta tylko `doc.paragraphs`. Naprawić **jeden istniejący owner odczytu**: zebrać akapity i tekst z komórek zwykłych tabel w głównej treści DOCX, w **kolejności dokumentu** (akapit → tabela → akapit), bez gubienia i duplikowania treści. W tabeli zachować rozdzielenie akapitów/komórek/wierszy tak, by odrębne identyfikatory nie sklejały się w jedną wartość, ani słowo z końca jednej komórki z początkiem drugiej. Puste komórki mogą nie tworzyć treści. Nie wolno dwukrotnie wypisać zawartości komórek scalonych, jeśli API DOCX zwraca ją przez wiele adresów komórek. Zamknięty zakres pierwszego kroku to tabele w body oraz akapity bezpośrednio w komórkach; gdy zagnieżdżone tabele występują w próbce, wskazać wynik i zgłosić finding zamiast obiecywać ich pełną obsługę.

Nie zmieniać kontraktu `_extract_text` — nadal `(text: str, error: str | None, ocr_meta: dict | None)`. Rozpoznawanie formatu, ścieżki PDF/TXT/obrazy, zachowanie błędów importu/otwarcia DOCX i OCR bez zmian. Maskowanie wykonuje istniejący pipeline **po** ekstrakcji; nie podłączać osobnego skanera PII do czytnika DOCX.

## Minimalne testy, weryfikacja, odbiór
1. **Red → green na produkcyjnym extractorze**: mały syntetyczny DOCX utworzony in-memory lub w katalogu tymczasowym: akapit A z unikalnym adresem, tabela 2×2 z dwoma różnymi kompletnymi EMAIL/NUMER, akapit B za tabelą. Przed zmianą oba pola tabelaryczne są pomijane; po zmianie każde występuje dokładnie raz; A i B pozostają w poprawnej kolejności, brak sklejania przez granice komórek i wierszy. Ten test musi FAIL na kodzie bazowym.
2. Dodatkowe kontrpróby na tym samym małym teście: tabela wieloakapitowa w jednej komórce, komórka pusta, tabela przed pierwszym akapitem, akapit między dwiema tabelami i komórka scalona — brak duplikatów, zamiany kolejności lub utraty zwykłych akapitów. Nie przebudowywać całego modelu Word; nietypowe struktury (nagłówki/stopki, tekst w kształtach, przypisy, komentarze, pola formularzy, tabele zagnieżdżone) są poza zakresem i wymagają osobnego findingu, jeśli pomiar je ujawni.
3. **Istniejący pomiar layout:** `backend/tests/test_engine_quality_layout.py::test_komorka_tabeli_to_brak_ekstrakcji_nie_maskowanie` ma dziś asercję `EXTRACTION_MISSING` — po rzeczywistej naprawie zaktualizować oczekiwanie na wynik z **produkcyjnego** pipeline i sprawdzić `docx/tabela` → `masked` (nie `blocked`, `EXTRACTION_UNVERIFIED`, `no_mapping`). Nie osłabiać istniejących regresji: przypadki tej samej wartości w akapicie i tabeli oraz krótszych wartości będących fragmentami dłuższych powinny po poprawie odzwierciedlać faktycznie dwa oddzielne wystąpienia; każda zmiana asercji wymaga sprawdzenia pełnej mapy/wyniku, nie automatycznej zamiany oczekiwanych statusów. `engine_quality.py` i jego `classify_m1` NIE zmieniać.
4. **Pion i realny układ, dane syntetyczne:** jeśli lokalna próbka `backend/dataset_layout/` z etapu 1 nadal istnieje, uruchomić `audyt/engine_quality.py --layout` i porównać tę samą manifestowaną próbkę / digest / hash wejść przed i po. Oczekiwane trzy `docx/tabela` przechodzą z `EXTRACTION_MISSING` do zmierzonych, a dalej prawidłowych `masked`; wynik nie może być uzyskany samą modyfikacją runnera. DOCX/akapit 1 i PDF 3 bez regresji. Jeśli próbki lokalnej brak, NIE udawać porównania: test syntetyczny i jawne `NOT_RUN` dla pomiaru gov.pl, plus instrukcja odtworzenia lokalnie bez publikowania pliku ani wartości.
5. Uruchomić jawnie `cd backend && py -3 -m pytest tests/test_engine_quality_layout.py -q -o log_file=NUL` (plik nie jest w standardowym `pytest.ini`); uzupełnić/uruchomić test ekstrakcji, standardową suite oraz gate dla exact SHA. Udokumentować zmianę liczby wyodrębnionych pól, wynik M1/M3 i zachowanie błędów. Nie zaliczać PASS przy zamaskowaniu tylko wartości w akapicie i pominięciu tych samych lub innych pól w tabelach.
6. Testy i raporty z syntetyki, bez realnych danych osobowych. Lokalne oryginalne wzory tylko w już ignorowanym `backend/dataset_layout/`; bez plików źródłowych, wartości i treści dokumentów w logach/raportach/repo. `--seed` bez `--layout` zachowuje poprzednie wyniki/digest.

TASK_SCOPE:
- backend/document_processor.py
- backend/tests/test_engine_quality_layout.py

OUT_OF_SCOPE: `audyt/engine_quality.py` (tylko odczyt i pomiar), `pipeline_new.py`, NER, normalizatory, Guard, tokeny, UI, PDF/obrazy/OCR, eksport/odtwarzanie układu DOCX, nagłówki/stopki/przypisy/kształty/pola formularzy, parser HTML, tabele zagnieżdżone, KRS/KW, prawdziwe dane osobowe, nowe zależności/nowy parser dokumentów. Gdy zwykła tabela body nie jest możliwa bez dodatkowego ownera: STOP + wąski finding, zamiast rozszerzenia po cichu.

PASS: kompletne, jednokrotne i uporządkowane wydobycie tekstu zwykłych tabel body DOCX z zachowaniem istniejących akapitów; liczbowy pomiar pól po produkcyjnym pipeline, bez udawania sukcesu przez zignorowanie tabel; żadna regresja PDF/Guard/starego runnera; niezależny audyt exact SHA. Nagłówki i stopki pozostają osobnym niezamkniętym ryzykiem ekstrakcji, nie deklarować „DOCX 100%”.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/document_processor.py --symbol _extract_text
- TARGETS: backend/tests/test_engine_quality_layout.py --symbol test_komorka_tabeli_to_brak_ekstrakcji_nie_maskowanie
- REASON: odczyt DOCX to jedyne produkcyjne źródło danych przed pipeline; poprzedni pomiar może być regresją RED→GREEN.
GATE: 0 nowych plików, >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI; nie kasować istotnych testów dla przejścia gate. Codex: BRIEF_ONLY precheck bez kodowania, ocenić minimalność i wykonalność testów.
