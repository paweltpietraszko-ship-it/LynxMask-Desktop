# Brief — LYNX-OCR-CASCADE / C1: druga opinia OCR, eksperyment porównania przestrzennego

STATUS: BRIEF_ONLY → Codex PREIMPLEMENTATION → CC recenzja → CC implementuje C1 → Codex audytuje exact SHA → OWNER decyduje o dalszym etapie. Bez merge bez polecenia OWNERA.
PRODUCT_TRUTH: `arch/spec.md` S1 (lokalnie), S3 (fail-closed), S5 (brak danych użytkownika w logach); `AGENTS.md`; `BOARD.md` → TERAZ i wiersz `LYNX-OCR-PARITY` (20.10). To osobny Task po zmergowaniu B1 `5f048a1`, Codex PASS `ff56544`.

## Kontekst i wybór architekta

B1 dała `NO_SAFE_GATE`: confidence PP-OCRv6 nie wykrywa wszystkich błędów. W syntetyku `doc_00004` NIP jest zniekształcony przy wysokim score linii; w `doc_00012` PP pomija linię IBAN, choć inne linie są rozpoznane pewnie. PP odczytuje zwykle więcej danych (93–94% vs Tesseract ~72% w dotychczasowych porównaniach), ale żadne progi confidence nie uzasadniają wydania wyników `/preview`.

OWNER zaakceptował kierunek **kaskady**: PP-OCRv6 jako pierwszy odczyt, Tesseract jako niezależna druga opinia o pokryciu obrazu, potem istniejący silnik maskowania, a w kolejnych oddzielnych Taskach ewentualnie HerBERT i Guard pokazujący pozostałości. Opinia dwóch OCR nie gwarantuje kompletności: oba mogą pominąć ten sam fragment albo popełnić zgodny błąd. Nie wpisywać do raportu „100% pokrycia” na podstawie ich zgody.

**Rekomendacja architekta:** zamiast od razu sklejać dwa teksty w produkcie, najpierw sprawdzić **czy da się jednoznacznie skojarzyć odczyty na tych samych obszarach obrazu** i rozróżnić trzy działania. C1 to minimalny, falsyfikowalny pion diagnostyczny na istniejących prawdziwych silnikach OCR (bez atrap wyniku), a nie kolejna kalibracja confidence. Dopuszczenie automatycznej podmiany/uzupełnienia tekstu to dopiero C2 po dowodach C1.

## Cel C1: rozłączne klasy porównania

Przetworzyć *ten sam* lokalny syntetyczny obraz przez PP i Tesseract, z oryginalnymi współrzędnymi regionów tekstu, i przypisać spornemu obszarowi najwyżej jeden status:
- `BOTH_AGREE` — zgodny tekst/identyfikator w odpowiadającym sobie regionie; **nie jest** dowodem poprawności, nie uzasadnia `quality=ok`.
- `PP_DISTORTED_TESS_VALID` — PP odczytuje w danym obszarze inny, niepełny lub uszkodzony identyfikator, a Tesseract w *tym samym regionie* daje kandydata o **poprawnej sumie kontrolnej** i poprawnym kształcie (PESEL, NIP, REGON, IBAN). Tylko **kandydat** przyszłego zakrycia fragmentu PP, nie automatyczna zamiana na treść z Tesseracta.
- `PP_MISSING_TESS_PRESENT` — PP nie ma regionu w położeniu, gdzie Tesseract rozpoznaje tekst, także identyfikator (np. IBAN); **kandydat** przyszłego uzupełnienia brakującej linii, ale teraz żadnej wstawki. Puste/niezidentyfikowane pole to strata treści, nie automatycznie wyciek danych tekstowych.
- `CONFLICT_REVIEW` — istnieją oba regiony, ale odczyty się różnią, suma kontrolna nie rozstrzyga lub wartości są ze sobą przestrzennie niejednoznaczne.
- `PP_ONLY` / `TESS_ONLY_UNCERTAIN` — pojedynczy odczyt bez wiarygodnego sparowania lub zbyt niską jakością; nie promować automatycznie do „poprawnego”.
- `UNMEASURABLE` — brak geometrii, różne orientacje, brak modelu, awaria OCR albo inna niemożność porównania; z powodem. Wymaga jawnych liczników, nie ukrywać w `BOTH_AGREE`.

Dopuszczalne scalanie segmentów Tesseracta **tylko wewnątrz udowodnionego regionu jednej linii** (TSV: `block_num/par_num/line_num` + rzeczywiste położenie); nie sklejać słów z innych kolumn, sąsiednich pól, tabel ani różnych linii. PP zwraca `boxes/txts/scores`; Tesseract `image_to_data` z `left/top/width/height` i metadanymi linii. Oba odczyty muszą odnosić się do tych samych pikseli i orientacji; obrót, różna skala, różne strony → `UNMEASURABLE`, chyba że transformacja jest jawna i testowana. Porównywać regiony za pomocą mierzalnej geometrii (nakładanie w pionie i poziomie), nie samej zbieżności ciągów; wątpliwe przyporządkowania trafiają do REVIEW. Dwie identyczne wartości w odrębnych obszarach nie mogą zostać pomylone.

Walidacja sum kontrolnych jest dodatkowym dowodem wyłącznie dla wspieranych kategorii; użyć istniejącego `python-stdnum` lub minimalnego istniejącego walidatora produktu. Nie uznawać poprawnej sumy za gwarancję, że odczytane cyfry rzeczywiście były na skanie. Zwykłe nazwiska, adresy, e-maile, sygnatury nie mają sum kontrolnych; nie „naprawiać” ich automatycznie na podstawie różnicy silników.

## Implementacja C1 — pomiar offline, nie zmiana produktu

Jeden skrypt `tasks/LYNX-OCR-CASCADE/measure/paired_ocr.py` czyta `ground_truth.json` i obrazy **wyłącznie z jawnie wskazanej syntetycznej paczki**:
- PP: wykorzystać `backend/ocr_rapid._get_engine` (lokalne, identyczne hashe modeli) i obecny sposób składania tekstu; pobrać ramki i tekst na poziomie linii z jednym wywołaniem silnika na obraz, bez dodatkowych pobrań modelu.
- Tesseract: `pytesseract.image_to_data` z tym samym `--psm 3` i tym samym `lang` co w `ocr_engine.py`. Zbudować linie z TSV, zachować współrzędne i tekst oraz osobno wykryć niepewność; nie wywoływać `image_to_string` w drugim przebiegu bez konkretnej potrzeby. Zmierzyć rzeczywisty koszt drugiego OCR.
- Bez zmiany `backend/ocr_rapid.py`, `ocr_engine.py`, `/preview`, `OCRResult`, `quality`, Tesseractowych progów, Guarda i maskowania. PP w produkcie nadal `quality=reject/confidence=0`, Tesseract pozostaje domyślny.
- Raport wyłącznie do `--out` poza repo: SHA kodu, hashe modeli, digest paczki, liczność wszystkich obrazów i wartości gold, przypadki klasyfikacji `file ID + entity key + typ + status + powód`, rozkład per kategoria i degradacja, niepewne i niesparowane obszary, czas/RAM. Bez oryginalnych wartości, surowego OCR, bboxów zawierających PII jako obrazy, danych realnych, prywatnych ścieżek, nazw plików użytkownika, profilu. Szczegółowe lokalne wyniki wizualne mogą być oglądane przez OWNERA na jego komputerze, ale nie commitowane.
- Obecna diagnostyka `[OCR-DIAG]` i historyczna Tesseract baza służą do porównania, nie zastępować mianowników. Miary rozdzielają: (a) PP brak/zmiana **wartości gold**; (b) druga opinia znalazła ten sam rejon i poprawną wartość; (c) poprawność zakwalifikowania regionu; (d) fałszywe alarmy i nadmiarowe wstawki proponowane przez regułę; (e) koszt. Zgody obu OCR nie policzyć jako wartości zweryfikowanej bez ground truth.

C1 ma odnaleźć i opisać `doc_00004` i `doc_00012` na znanym `dataset_20260627_095419`. Przed otwarciem `dataset_20261016_fresh` zamrozić reguły parowania i etykietowania. Jedno kontrolne sprawdzenie na 100 obrazach (holdout używany już w A/B1 — nie „całkowicie niewidziany”), bez dobierania progów do niego. W wynikach koniecznie ujawnić, czy poprawne checksumy i geometria **rzeczywiście** umożliwiają naprawę tych dwóch przypadków; jeśli nie, zgłosić to bez udawania trafienia.

## Bezpieczeństwo i kontrpróby

Testy w `backend/tests/test_ocr_cascade_probe.py` na sztucznych geometrach i tekstach:
1. dwie kolumny, dwie podobne wartości w osobnych wierszach, liczba w tabeli blisko drugiej — brak łączenia obcych fragmentów;
2. PP błędne NIP + Tesseract poprawne NIP w *tym samym* polu → kandydat `PP_DISTORTED_TESS_VALID`; identyczna wartość Tesseracta w odległym miejscu nie może tego wywołać;
3. PP brak całej linii, Tesseract ma IBAN z poprawną sumą → `PP_MISSING_TESS_PRESENT`; bez autowstawienia;
4. PP i Tesseract różne, oba o poprawnej sumie; albo niepoprawna suma Tesseracta → `CONFLICT_REVIEW`; walidator nie rozstrzyga prawdy z dwóch poprawnych numerów;
5. tekst krótszy, bez checksumy, z polskimi znakami lub mieszanymi separatorami; brak ramki, obrót, nieprawidłowe/ujemne wymiary, duplikaty → status niepewności, zero domyślnego `BOTH_AGREE`;
6. awaria jednego OCR, timeout PP albo Tesseract, brak modelu: `UNMEASURABLE` lub `NOT_RUN`; nie ukrywać porażek w procentach. Bez wycieków do stdout/raportów/logów, bez internetu i dotykania profilu.
7. Dwa identyczne przebiegi na tym samym zbiorze i SHA: te same ID/statusy/liczności, tolerancja wyłącznie dla czasu/RAM.

**Wymóg falsyfikacji:** liczba `PP_MISSING_TESS_PRESENT` w danych z gold nie jest automatycznie liczbą brakujących encji uratowanych; niezależne dopasowanie po gold i przegląd rozjazdów wymagane. Jeśli dużo fałszywych sparowań, brak zgodności współrzędnych lub wysokie koszty, nie wdrażać automatycznych poprawek. C1 może zakończyć się `NOT_FEASIBLE` bez FAIL poprawnego narzędzia.

## Proponowana następna faza C2 — NIE implementować w C1

Dopiero po wynikach C1 osobny krótki kontrakt zachowania produktu:
- (A) pewny, jednoznacznie przestrzennie sparowany *uszkodzony* identyfikator PP → maskowanie **oryginalnego fragmentu PP**, bez zastępowania go cyframi z Tesseracta i bez nowego właściciela tokenów; jeśli nie ma bezpiecznego zakresu → do oceny, nie heurystyczna podmiana;
- (B) linia Tesseracta brakująca w PP → **nie wstawiać na ślepo**; konieczne dowody poprawnej pozycji, uniknięcia duplikatów i możliwości przejścia całej wstawki przez istniejący pipeline + Guard. Niepewność → dokument wymaga działania człowieka, bez udostępnienia niezweryfikowanego wyniku;
- (C) konflikt niejednoznaczny → blokada udostępnienia/ostrzeżenie do rozstrzygnięcia, zgodnie z obowiązującym S3/S4; istniejące S4 nie może być zmienione przy okazji. Użytkownik musi dostać rozwiązanie: **„Odczyt skanu jest niejednoznaczny. Wykonaj wyraźniejsze zdjęcie albo wklej tekst dokumentu.”** Wszelkie nowe interakcje UI wymagają osobnego kontraktu OWNERA.
- Test pełnego `/preview` z obu OCR, rzeczywistym maskowaniem i Guardem na tym samym profilu testowym, 50+100 obrazów, poprawność identyfikatorów i brak jawnych krytycznych fragmentów w wynikach dostępnych do skopiowania. Dokładne odróżnienie odmów i rzeczywistych wycieków. Timeout PP w fazie A nie zatrzymuje wątku: przed uruchomieniem kaskady produkcyjnie trzeba wyjaśnić drugi request po timeout i zagwarantować powrót do pracy, bez dowolnego dodawania nowego backendu.

Wdrożenie HerBERT, pełnego Guard-RESIDUE, wybór domyślnego PP i zmiana S4 są **oddzielnymi** zadaniami. Załączone dane B1 nie udzielają im automatycznego PASS.

TASK_SCOPE:
- tasks/LYNX-OCR-CASCADE/measure/paired_ocr.py
- backend/tests/test_ocr_cascade_probe.py

OUT_OF_SCOPE: modyfikacja jakiegokolwiek kodu produkcyjnego, zapis albo podmiana treści w `/preview`, dodanie Tesseracta do produkcyjnej ścieżki PP, wstawianie linii, maskowanie przez drugi OCR, aktywacja PP, UI, zmiana S3/S4, instalacja modeli/binariów, realne dokumenty w repo i pełna suita.

WHERE_MAP:
- MODE: OPTIONAL
- TARGETS: backend/ocr_rapid.py --symbol _get_engine
- TARGETS: backend/ocr_rapid.py --symbol build_text
- TARGETS: backend/ocr_engine.py --symbol _run_tesseract
- REASON: odczyt tych samych regionów z dwóch istniejących dostawców, bez poszerzania właściciela produktu.

GATE: maks. dwa nowe pliki, każdy ≤600 l., funkcje ≤50 l.; suma zmian >150 albo ratio >5:1 => `WYMAGA_DECYZJI` i szacunek CC / zgoda OWNERA przed kodowaniem (zgody z A/B1 nie przenoszą się). Nie powielać obecnego OCR, walidatorów i diagnostyki. Zapis danych wyjściowych tylko poza repo. Wymagana minimalna redukcja przedimplementacyjna; gdy po recenzji wynika, że dopasowanie przestrzenne nie zmieści się w rozsądnym narzędziu, CC zgłasza ograniczenie przed implementacją zamiast budować nowy framework.

PRZEKAZANIE: Codex teraz wyłącznie BRIEF_ONLY w `tasks/LYNX-OCR-CASCADE/round_01/tests/tests_r1.txt`, nie uruchamia modelu/testów. CC po PASS ocenia wykonalność geometrii, liczy rozmiar i implementuje tylko C1; potem Codex audyt exact SHA. Tesseract nadal domyślny; PP bez skalibrowanej bramki nadal odmawia. Wyniki C1/ewentualna decyzja C2 wracają do Architekta i OWNERA. Merge tylko na polecenie OWNERA.
