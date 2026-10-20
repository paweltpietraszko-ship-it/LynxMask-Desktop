# LYNX-OCR-PARITY — krok 2, faza B: kalibracja PP-OCRv6 i bramka dopuszczenia

STATUS: BRIEF_ONLY. **W tej rewizji kodujemy tylko B1 (narzędzie kalibracyjne), nie aktywujemy PP-OCRv6 w `/preview`.** Po pomiarze B1 Architekt zamraża osobny, liczbowy kontrakt B2; Codex robi jego wąski precheck przed zmianą zachowania. Brak merge bez polecenia OWNERA.

PRODUCT_TRUTH: `arch/spec.md` S1 (offline), S3 (fail-closed), S5 (brak PII w logach), S6 (istniejący UI); `BOARD.md` → TERAZ / `LYNX-OCR-PARITY`, 20.10.2026; kontrakt A w `tasks/LYNX-OCR-PARITY-STEP2/brief.md`. Dokładny zmergowany punkt odniesienia fazy A: main `570995e`; Codex PASS r3 `fe035b6`. Domyślny Tesseract pozostaje bez zmian.

## 1. Powód fazy B i aktualny dowód

Na 50 znanych obrazach PP-OCRv6 small zachowuje 321/342 (93,9%) wartości gold, Tesseract 245/342 (71,6%). Na 100 **nieużytych do strojenia** obrazach `dataset_20261016_fresh`: PP 578/619 (93,4%), Tesseract 443/619 (71,6%). To dane CC z bezpośredniego OCR, nie audyt pełnego maskowania; różna jest też liczba dokumentów odrzuconych przez bramkę jakości. Nie wolno z tych dwóch odsetków wywnioskować bezpieczeństwa `/preview` ani kalibrować progów na kontrolnych 100 obrazach.

Faza A ma `ocr_rapid.extract_rapid` zwracające `quality="reject"`, `confidence=0.0` jako **sentinel braku kalibracji**. Tego zachowania nie zmieniać w B1. `ocr_rapid.recognize` obecnie zwraca wyłącznie tekst, ale wynik RapidOCR zawiera `boxes`, `txts` i `scores` rozpoznawania per linia (sprawdzić na zainstalowanym 3.10.0). Nie używać wynikowej średniej jako automatycznie skalibrowanego prawdopodobieństwa kompletności skanu. W szczególności model może pominąć całą linię z wysoką pewnością pozostałych linii; filtr `Global.text_score` może usuwać niskie wyniki przed raportem — uwzględnić to przy analizie.

**Rozstrzygnięcie architekta:** B musi mieć dwa gates. B1 najpierw *mierzy* rozdzielczość progów i błędy pewne siebie, bez zmiany produktu. B2 po zapisaniu liczbowych progów i kontrprób pozwoli uruchomić PP przez `/preview` w trybie jawnym. Gdy B1 nie potwierdza sensownej bramki, pozostajemy przy odmowie PP; nie obniżamy bezpieczeństwa dla poprawienia procentów.

## 2. B1 — kontrakt zamknięty, narzędzie offline

Wąski skrypt `tasks/LYNX-OCR-PARITY-STEP2/measure/pp_quality.py`, używający aktualnego `ocr_rapid._get_engine()`, `build_text` i istniejącego formatu datasetu; nie kopiować inferencji ani nie pisać nowego OCR. Tylko lokalne obrazy syntetyczne i jawna ścieżka wejścia, żadnego HTTP, profilu użytkownika, zapisu do repo ani pobierania modeli. Przed pomiarem potwierdzić wersję RapidOCR/onnxruntime i SHA256 3 lokalnych modeli z DELIVERY fazy A. Przy braku modeli: `NOT_RUN`, nie „PASS”.

Dla każdego dokumentu:
1. Wykonaj PP-OCRv6 raz, zbierz ID pliku, poziom degradacji, liczbę ramek i niepustych linii, `scores` z RapidOCR **powiązane z ramkami/tekstem**, oraz rozpoznany tekst wyłącznie w pamięci. Sprawdź spójność długości `boxes/txts/scores`; brak/NaN/inf/wynik nieprawidłowy → brak podstaw do uznania jakości; nie wpisuj fikcyjnych `0%` jako model score.
2. Oblicz bezpieczne, deterministyczne cechy dokumentu: min score, dolny kwantyl (np. 10%), udział linii poniżej zadanych progów, liczbę/udział pustych wierszy oraz sumę długości odczytu. W raporcie jawnie odróżnij `recognition_score` od **pokrycia obrazu tekstem**; sama pewność rozpoznanych wierszy nie mierzy tekstu pominiętego przez detektor. Nie dodawaj nowych danych do produkcyjnego `OCRResult`.
3. Przez istniejące reguły porównania gold/OCR policz dla **wszystkich** wartości gold: nienaruszone, bliskie/zniekształcone, niewidoczne, niejednoznaczne (`REVIEW`). Odrębnie typy krytyczne, e-mail/telefon/osoba/adres, per poziom degradacji. Nie zakładaj, że dopasowanie Levenshtein oznacza poprawny identyfikator. Lista wszystkich strat na lokalnym raporcie przez identyfikator pliku i klucz gold, bez dosłownych wartości w repo.
4. Dla z góry jawnej, małej siatki reguł kandydackich oblicz, ile dokumentów byłoby `ok`, `warn`, `reject` i ile **wartości gold byłoby zniekształconych lub pominiętych w dokumentach dopuszczonych**. Rozdziel wynik `ok` od `warn`; oba w obecnym API są udostępniane, więc oba należą do `accepted`. Reguła może używać min/kwantyla/odsetka słabych linii i ograniczenia przy pustym wyniku, ale NIE uczyć się na samych 100 obrazach kontrolnych. Nie dobierać skomplikowanego klasyfikatora/ML do 50 próbek.
5. Zapisz krótki raport lokalny do jawnie wskazanego `--out` poza repo: seed/dataset digest, SHA kodu i hash modeli, rozmiary i warunki wykluczeń, miary per typ i dla kandydatów, rozkład score, przypadki wysokiego score z błędną lub pominiętą wartością, koszt czasu/RAM. `stdout` bez PII. Niczego nie zapisywać w `backend/benchmark_results` ani katalogach produkcyjnego profilu. W repo tylko syntetyczne ID i agregaty bez pełnego OCR/dokumentów.

**Zbiory i uczciwość pomiaru:** `backend/dataset_20260627_095419` (50) do wyboru kandydatów progów. `backend/dataset_20261016_fresh` (100) to jednorazowy zamrożony **holdout**, użyty tylko do falsyfikacji *po* wybraniu kandydatów. W DELIVERY zapisać jawnie, że 100 obrazów było już użyte do wcześniejszego porównania adaptera, więc nie są całkowicie niezależnym niewidzianym zbiorem; żadnego wielokrotnego dopasowywania progów do tego holdoutu. `dataset_real_public` zawierający głównie PDF/TXT nie jest walidacją OCR obrazu; w B1 pomiń go jako nieadekwatny. Prawdziwe skany OWNERA nie trafiają do skryptu ani repo, będą osobną oceną lokalną przy B2.

**Wynik B1:** CC ma dostarczyć liczbową propozycję znaczenia `confidence` 0–100 (co mierzy, jak agreguje per-line score; NIE odsetek poprawnych znaków), deterministyczną tabelę progów `ok/warn/reject`, politykę braku/niepoprawnych scores i ryzykownego wysokiego score oraz liczbę strat błędnie dopuszczonych przez każdą propozycję; albo jednoznacznie `NO_SAFE_GATE`. Nie wolno uruchomić wyników PP z `/preview` wyłącznie na mocy tej propozycji.

## 3. Odbiór B1 i kryterium STOP

Codex na exact SHA ocenia: deterministykę (ten sam zestaw/model daje te same liczności/etykiety, z tolerancją czasu), odporność na brak/NaN/rozbieżne scores, brak dowolnego przyrostu kompletności, brak leakage do plików/logów, uczciwość mianowników i izolację holdoutu. Używa celowanych syntetycznych testów, bez automatycznego odpalania setek skanów po raz drugi. CC uruchamia jeden pomiar 50+100, jeżeli modele lokalnie dostępne; ujawnia błędy i odchylenia. Nie wymagamy sztucznie wymyślonego „progu 95%” ani 100% bezpieczeństwa.

**STOP B2** gdy: nie da się z scores odróżnić wartościowych od niekompletnych odczytów, istnieją pewne siebie pominięcia krytycznych identyfikatorów przepuszczane przez wszystkie praktyczne reguły, brakuje danych dla progów lub model nie działa stabilnie offline. `confidence` pojedynczych rozpoznanych linii nie może stać się domyślnym dowodem, że wszystkie ważne linie zostały znalezione. STOP nie oznacza regresji względem Tesseracta ani porażki B1 jako pomiaru.

## 4. B2 — warunki przyszłej rewizji kontraktu, NIE zakres implementacji B1

Gdy B1 przyniesie przekonującą propozycję, Architekt zamraża dokładny algorytm agregacji, progi, stany awaryjne i semantykę `confidence/quality/warning_msg` w kolejnej rewizji briefu. Codex robi wąski `BRIEF_ONLY`; dopiero po PASS CC zmienia `backend/ocr_rapid.py`, a także tylko konieczne testy, **wyłącznie pod jawną flagą `LYNX_OCR_ENGINE=rapid`**. Bramka `/preview` musi zachować istniejącą odpowiedź 422 dla `reject` i zgodność S3. Wciąż bez zmiany domyślnego silnika, UI, normalizacji, Guarda i Przywróć.

Przed dopuszczeniem PP domyślnie CC i Codex porównują na tej samej konfiguracji maskowania: oba OCR → `/preview` → `[OCR-DIAG]` na tych samych 50+100 syntetycznych obrazach. Liczyć osobno wszystkie wartości gold (również w odrzuconych dokumentach), liczbę dokumentów zaakceptowanych/odrzuconych, recall dla zaakceptowanych i **jawne krytyczne identyfikatory w wynikach dostępnych do skopiowania**; nie poprawiać statystyk przez zmianę mianownika. Wskazać każde pogorszenie względem Tesseracta wraz z ID syntetyka, bez zaliczania Guard-blocked do sukcesów maskowania. Wykonać punktowy test końca `/preview` i niezmienionych ścieżek TXT/DOCX/PDF; jeśli warunki nie spełnione, PP pozostaje testowy lub z odmową.

**Warunek techniczny przed B2:** w fazie A timeout kończy oczekiwanie, nie działający wątek, więc pojedynczy zawieszony OCR może blokować następne zadania w jednowątkowej puli. CC ma osobno zbadać dwa kolejne żądania po timeout; jeżeli drugie wpada w zator, zgłosić ograniczenie i rozwiązanie/oddzielny Task zamiast uznać gotowość do pracy. Nie dopisywać architektury procesowej na ślepo podczas B1.

Ostatecznie OWNER lokalnie ocenia niepublikowane realne skany: wydruk, fotografię, tabelę, polskie znaki i identyfikatory; brak kontroli właściciela = `NOT_CHECKED`, żadnej zmiany domyślnego OCR. Akceptacja B2 nie zmienia automatycznie domyślnego dostawcy.

TASK_SCOPE:
- tasks/LYNX-OCR-PARITY-STEP2/measure/pp_quality.py
- backend/tests/test_pp_ocr_calibration.py

OUT_OF_SCOPE: w B1 **jakakolwiek** zmiana `backend/ocr_rapid.py`, `ocr_engine.py`, `document_processor.py`, `pseudominizer_api.py`, `benchmark.py`, `arch/spec.md`, UI; uruchamianie `/preview` z PP w trybie oddającym dokument; zmiana progów Tesseracta; HerBERT, Guard-RESIDUE, instalator, zmiana domyślnego OCR, nowy dataset treningowy, strojenie na realnych danych.

TESTY / GATE: maks. dwa nowe pliki, nowy plik ≤600 l., funkcja ≤50 l.; >150 zmienionych linii lub ratio >5:1 → osobna zgoda OWNERA przed kodowaniem. Skrypt nie instaluje pakietów ani modeli, nie uruchamia backendu; wejścia/destynacja muszą być jawne. CC ocenia rozmiar podczas recenzji i nie dopisuje pozostałych pomysłów do B1. WHERE_MAP OPTIONAL: `backend/ocr_rapid.py::_get_engine`, `backend/ocr_rapid.py::build_text`, `backend/benchmark_ocr_diagnostics.py::classify_miss` (reuse, nie nowy owner). 

PRZEKAZANIE: Codex `BRIEF_ONLY` na tym briefie, raport `tasks/LYNX-OCR-PARITY-STEP2/round_02/tests/tests_r1.txt` na gałęzi B; bez kodu/modeli podczas prechecku. Potem CC merytoryczny review → B1 implementacja + gate.py + DELIVERY → Codex exact SHA audit → OWNER merge. Osobne rozstrzygnięcie B2 po pomiarze. Żadnego automatycznego „PP bezpieczny, więc włączamy”.
