# Brief — LYNX-OCR-PARITY / krok 1: diagnostyka „silnik czy OCR”

STATUS: BRIEF_ONLY po PASS PREIMPLEMENTATION Codexa (`8444503786d673d89662d446888bb481d39d6871`) i recenzji CC z BOARD.md (19.10). Korekta TASK_SCOPE po tej recenzji: wąski re-check zmienionego zakresu przez Codexa, następnie zgoda OWNERA na rozmiar przed implementacją. Bez merge.
PRODUCT_TRUTH: `arch/spec.md` S1/S3/S5 oraz `AGENTS.md` (PRIVACY, BRIEF_ONLY, DEFECT_GATE). Źródło celu: `BOARD.md` sekcja TERAZ i wiersz `LYNX-OCR-PARITY` (19.10.2026), `ARCHITECT_START_HERE.md` §3–4. OWNER uzgodnił rozdzielenie diagnostyki od zmian silnika: ten krok nie wymaga pełnego E2E produktu.
Źródło reguł porównawczych: `paweltpietraszko-ship-it/LynxMask/app/src/androidTest/java/com/lynxmask/app/BenchmarkInstrumentedTest.kt` (metody `classifyMiss`, `fuzzyMatch`, `classifyExtraToken`). Portuj zasadę, nie cały tester Androida.

## Cel i znany szew

Na dokładnie tym samym, zamrożonym zbiorze syntetycznych obrazów odróżnić: (A) gold nadal czytelny w tekście oddanym silnikowi, ale niezamaskowany; (B) wartość zniekształconą przez OCR; (C) wartość nieodnalezioną w OCR. Osobno zaklasyfikować nadmiarowe tokeny, bez traktowania każdego tokenu spoza gold jako błędu. To miarka zmian w kolejnych Taskach, nie ocena bezpieczeństwa produkcyjnego na wszystkich dokumentach.

Istniejący punkt integracji: `backend/benchmark.py`, szczególnie `analyze`, `run_benchmark`, `build_report`. Ze względu na ratchet `gate.py` (plik `benchmark.py` ma 987 l. i nie może rosnąć) właściwa logika klasyfikacji i zapisu `ocr_diagnostics.json` należy do nowego modułu `backend/benchmark_ocr_diagnostics.py`; w `benchmark.py` wyłącznie minimalne wywołanie, bez wzrostu liczby linii (dopuszczalne skrócenie changelogu w docstringu, bez refaktoru). **Ważne odkrycie z punktowego odczytu kodu:** `backend/pseudominizer_api.py` zwraca w poprawnej odpowiedzi `/preview` pole `original_text` — tekst po OCR i ekstrakcji, przed `pseudonymize_document`. Benchmark obecnie go nie odczytuje. Nie uruchamiać ponownie Tesseracta i nie zmieniać endpointu. `ocr` w odpowiedzi zawiera tylko metadane jakości.

## Kontrakt diagnostyczny

1. Dla dokumentów zaakceptowanych przez HTTP/OCR odczytać `resp["original_text"]` tylko w pamięci procesu. Każdemu **już pominiętemu przez dotychczasowe `analyze`** wystąpieniu gold nadać jedną etykietę:
   - `BUG_SILNIKA`: gold występuje w `original_text` bez merytorycznej zmiany znaków, z tolerancją istniejących różnic białych znaków i formatowania; znaczy **kandydat do sprawdzenia szwu silnik–normalizacja–metryka**, NIE potwierdzony defekt na exact SHA.
   - `OCR_ZNIEKSZTAŁCONY`: nie ma dopasowania poprzedniego, ale jest wiarygodny bliski odpowiednik. Zastosować ograniczoną odległość Levenshteina jak Mobile: minimum 9 znaków, dopuszczalna odległość 1 (9–14), 2 (15–23), 3 (24+). Uwzględnić e-mail (m.in. `@`→`Q`) i numery ze spacją w środku. Porównywać lokalne kandydackie fragmenty, nie sklejać całego OCR w sztuczny ciąg; nie przypisywać wyniku do przypadkowo podobnego obcego słowa.
   - `BRAK_W_OCR`: brak dopasowania dokładnego i wiarygodnego przybliżonego. To **brak wykrytego odpowiednika**, nie dowód, że żaden znak encji nie pozostał na obrazie.
   Jeśli `original_text` jest niedostępny, pusty z przyczyn technicznych lub nie da się uczciwie sklasyfikować: `NOT_MEASURED` / `REVIEW` z powodem, **nigdy domyślnie `BRAK_W_OCR` ani `BUG_SILNIKA`**. Nie utożsamiać tekstu z `original_text` z surowymi pikselami/skanem.
2. Dla tokenów uznanych przez dotychczasowy benchmark za `false_positives` (spoza dopasowania gold) dodać rozłączne etykiety, zgodnie z Mobile: `EXTRA_MASK_OK` (dodatkowe dopasowanie odpowiedniego typu do gold), `EXTRA_MASK_POLICY` (typ objęty obowiązującą polityką maskowania, np. `KWOTA`/`NUMER`), `UX_FP` (tylko potwierdzony negatywny przypadek, np. mała jawna lista zakazanych fraz z Mobile), `REVIEW` (pozostałe). Uwzględnić desktopowe mapowanie `FIRMA`/`INSTYTUCJA` → `ORGANIZACJA`. `REVIEW` nie liczy się automatycznie jako prawdziwy FP.
3. Oddzielnie zachować status `ocr_rejected`, błędy HTTP, `guard_blocked`. Odrzucone/błędne dokumenty **nie wchodzą do mianownika** etykiet ani starego recall. Guard-blocked nie oznacza automatycznie skutecznej pseudonimizacji i musi być widoczny osobno.
4. **Nie zmieniać** dotychczasowej logiki dopasowania gold–token, tabel wyników, liczników recall/critical/precision, struktury `report.json` i dotychczasowych plików `summary.txt`/`bugs.txt`. Klasyfikację i zapis raportu realizuje `backend/benchmark_ocr_diagnostics.py`; `backend/benchmark.py` jedynie wywołuje moduł bez przyrostu linii. Dopisać obok lokalny `ocr_diagnostics.json` dla przebiegu: ID pliku, klucz gold, etykieta, typ, status i ewentualny powód `REVIEW`/`NOT_MEASURED`; dodatkowo sumy per etykieta/typ oraz sumy `accepted/rejected/errors/guard_blocked`. Bez pełnych wartości, fragmentów OCR, tokenów API i surowych dokumentów. Jedna zwięzła linia sum diagnostyki na stdout. Pracować tylko na syntetycznym zbiorze `backend/dataset_20260627_095419`; żadnych prawdziwych dokumentów ani automatycznych commitów wyników.
5. Etykietowanie jest **dodatkowym widokiem**, nie nowym „procentem jakości silnika”. Liczba etykiet miss musi odpowiadać staremu `privacy_missed` na tych samych zaakceptowanych dokumentach, wraz z jawnym `NOT_MEASURED` (jeżeli wystąpi); analogicznie suma kategorii extra równa się dotychczasowej liczbie `false_positives`. Żadnego dobierania progów do historycznego podziału 0/10/6.

TASK_SCOPE:
- backend/benchmark_ocr_diagnostics.py
- backend/benchmark.py
- backend/tests/test_benchmark_ocr_diagnostics.py

Odpowiedzialność: nowy moduł = cała klasyfikacja pominięć i dodatkowych tokenów oraz zapis `ocr_diagnostics.json`; istniejący `benchmark.py` = tylko wywołanie nowego modułu, bez netto przyrostu liczby linii (np. poprzez skrócenie changelogu w docstringu); plik testowy = celowane testy nowej diagnostyki. Bez rozbudowy 987-liniowego `benchmark.py`.

OUT_OF_SCOPE: zmiany endpointów lub `original_text` w API, produkcyjny OCR/normalizer, pipeline, tokeny, Guard, Przywróć, UI, generowanie nowej paczki, HerBERT, port reguł e-mail, pełny E2E, poprawianie starych raportów publicznych i przesądzanie przyczyn każdego błędu.

## Kontrpróby / odbiór

- Testy jednostkowe na syntetycznym `gt`, `resp` i starym wyniku `analyze`: dokładny tekst bez tokenu → `BUG_SILNIKA`; e-mail z `Q` zamiast `@` i 1–3 zmianami stosownie do długości → `OCR_ZNIEKSZTAŁCONY`; ciąg nieobecny → `BRAK_W_OCR`; brak pola OCR → `NOT_MEASURED`; zbliżone niezwiązane wartości nie mogą dać pozornego trafienia. Osobno numery z wtrąconymi spacjami, granice długości 9/15/24 i brak fałszywego sklejenia obcych wyrazów.
- Jeden przypadek dla każdej z czterech etykiet extra; ich suma równa liczbie legacy `false_positives`. `REVIEW` nie jest automatycznie `UX_FP`.
- HTTP error/OCR reject: brak klasyfikacji i wykluczenie z mianownika; `guard_blocked` pozostaje widoczny.
- Dwa identyczne uruchomienia na tej samej paczce (poza timestampem i ścieżką runu): te same ID/etykiety/liczności. W `report.json`, `summary.txt`, `bugs.txt` te same dotychczasowe dane metryczne/struktury. W nowym pliku żadnego surowego `original_text`. Brak odczytu/wysyłki danych zewnętrznych poza istniejącym lokalnym `/preview`.
- Dopiero po przejściu prechecku, CC uruchamia celowane `cd backend && py -3 -m pytest tests/test_benchmark_ocr_diagnostics.py -q`, potem **jeden** pełny odczyt zamrożonych 50 obrazów przez istniejący lokalny backend na porównywalnym exact SHA: `cd backend && py -3 benchmark.py --dataset dataset_20260627_095419 --no-generate`. Oczekiwane historycznie 274/290 recall i 0/107 critical w **starej miarce**, ale nie kodować tych liczb jako wymogu nowej klasyfikacji. Jeśli nie ma lokalnego backendu lub datasetu, oznacz `NOT_RUN`; nie nazywaj PASS. To nie jest E2E produktu ani pełna suita.
- Jeśli wyniki nie zgadzają się z ręczną diagnozą 19.10 (0/10/6), podać przypadki i przyczynę rozjazdu; nie zmieniać progów tylko po to, by odzyskać 0/10/6.
- Audyt Codexa na **exact SHA**, mały niezależny reproduktor + te same testy celowane; osobne zgłoszenia findingów narzędzia i silnika, bez automatycznej naprawy silnika.

WHERE_MAP:
- MODE: OPTIONAL
- TARGETS: backend/benchmark.py --symbol analyze
- TARGETS: backend/pseudominizer_api.py --symbol preview
- REASON: narzędzie korzysta z istniejącego pola `original_text`; nie zmieniamy właściciela produkcyjnego.

GATE: maks. dwa nowe pliki (moduł + test), nowy plik ≤600 l., funkcja ≤50 l.; `backend/benchmark.py` ma 987 l. i z powodu ratchet `gate.py` nie może urosnąć. CC szacuje ~220 linii łącznie z testami; **wymagana jawna zgoda OWNERA na rozmiar przed kodem** (>150 nowych/zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI). Korekta TASK_SCOPE sama w sobie nie jest taką zgodą. W pierwszym kroku żaden nowy endpoint, biblioteka OCR ani refaktor benchmarku; jeśli założenie o polu `original_text` okaże się fałszywe w bieżącym trybie, CC zgłasza problem zamiast rozszerzać zakres.

PRZEKAZANIE: Codex zakończył BRIEF_ONLY PASS w raporcie r1 (`8444503`), a CC zaakceptował brief merytorycznie pod warunkiem korekty zakresu (BOARD.md, 19.10). Po niniejszej korekcie: Codex ewentualnie wąski re-check samego TASK_SCOPE, następnie jawna zgoda OWNERA na rozmiar ~220 l. → CC implementacja → Codex exact-SHA audit → OWNER ocena/merge. PASS techniczny nie jest zgodą na merge.
