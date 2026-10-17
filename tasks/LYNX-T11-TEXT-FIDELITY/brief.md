# LYNX-T11-TEXT-FIDELITY — poprawka F1/F2: tekst poza encjami pozostaje bez zmian

STATUS: BRIEF_ONLY; adresat prechecku: Codex. Kod produkcyjny nietknięty, bez zgody na merge.
PRODUCT_TRUTH: `arch/spec.md` S1 (Zamaskuj/Przywróć), S2 (zakaz globalnego sklejania spacji), S3 (fail-closed), S5 (brak PII w logach). Dowód: `BOARD.md` → `LYNX-TEXT-FIDELITY`; `arch/FINDING_2026-10_AUDYT.md` (BUG-GLOBAL-SPACE-GLUE, BUG-OCR-NORMALIZER-WORDS, BUG-UNMASK-FIDELITY); `tasks/LYNX-DICT-LEAKTEST/round_01/implementation/DELIVERY.md` → M3/F1/F2/F3.
OWNER_PROPOSAL: zacząć naprawę TEXT-FIDELITY po scaleniu pomiaru jakości. Zakres F1/F2 to naprawa udokumentowanych odstępstw od istniejącego kontraktu; nie ustanawia nowych kategorii danych ani zasad maskowania.

## Cel i granice
M3 na syntetycznym zbiorze `DICT-LEAKTEST` (seed 2026, 96 przypadków z holdoutem) wykazał 51/96 tekstów identycznych po symulowanym Przywróć; w 45 wystąpiła różnica poza spanami. Nie utożsamiać wszystkich różnic z jednym defektem.
- **F1** `backend/layers/ner_adapter.py::_fix_ocr_email` usuwa spacje po zwykłych kropkach nawet bez `@` („12/2026. Termin” → „12/2026.Termin”; łączy także zdania oddzielone nową linią). To zabroniona globalna modyfikacja tekstu (S2).
- **F2** `backend/layers/ocr_normalizer.py` krok 11, `_PHONE_AFTER_KW_RE` i zamiana `_OCR_TO_DIGIT`: po numerze telefonu obejmuje początek następnego słowa („654. Termin” → „654. 7ermin”); podobny zapis „…654) zglosil…” może być modyfikowany wewnątrz słowa. Normalizacja numeru NIE może objąć następującego zwykłego słowa.
- **F3 poza tym Taskiem**: „PESEL 44051401359” zyskuje dwukropek, telefon traci `+`/spacje po Przywróć. To kwestia oryginalnych spanów, wartości w reverse_map i/lub innych warstw. Wymaga odrębnego reproduktora i briefu, bez przypadkowej zmiany w T11; nie obiecywać 96/96 jako kryterium dla F1/F2.

## Kontrakt zachowania w istniejącej aplikacji
Wyzwalacz: wklejenie/załadowanie zwykłego tekstu do „Zamaskuj”, a także tekstu po OCR. Efekt: fragmenty nieobjęte tokenem (zdania, wielkość liter, spacje, końce wierszy, interpunkcja, zwykłe słowa po numerze) pozostają dokładnie takie jak wejście; zamaskowane PII nadal nie jest udostępniane, tokeny i ich kategorie bez zmian.
- **F1**: przed modyfikacją interpunkcji/spacji muszą istnieć wiarygodne granice *tego samego* adresu e-mail (np. lokalna część z `@`, nie sąsiednie zdania). `anna. nowak@wp.pl` → lokalna część może zostać sklejona do `anna.nowak@wp.pl` przed maskowaniem; `Wystawiono fakturę. Termin płatności`, `nieokreślony.\n2. Umowa`, `12/2026. Termin` — identyczne. Zachować poprawki OCR e-maila: spacje przed/po `@`, jeśli dotyczą prawdziwego adresu. Żadnych globalnych `replace` albo sklejania „na wszelki wypadek”.
- **F2**: wzorzec telefonu ma kończyć się na danych numeru, przed interpunkcją i następnym słowem; nie naprawiać zwykłych liter `Termin`, `zglosil` itp. Poziom rozpoznania cyfr OCR w *całym dopasowanym numerze* zachować (np. `Tel: +48 606 219 T2T` → wykrywalne 727). Jeśli rozstrzygnięcie granicy jest niepewne, nie poprawiać zwykłego słowa; nigdy nie osłabiać Guarda, aby przepuścić podejrzany numer.
- Błąd warstwy/NER/pipeline: dotychczasowa semantyka fail-closed S3, bez zwracania tekstu jawnego jako bezpiecznego. W UI brak nowych ustawień, komunikatów i danych. Nie zmieniać zawartości `reverse_map` w ramach F1/F2 poza istniejącym zachowaniem normalizatora dla wykrytych tokenów; problemy z rekonstrukcją oryginalnego zapisu tokenu zgłosić do F3.

## Minimalny szew i zakres
Istniejący owner F1: `_fix_ocr_email` w `backend/layers/ner_adapter.py`; istniejący owner F2: `_PHONE_AFTER_KW_RE` i jego użycie w `backend/layers/ocr_normalizer.py`. Bez drugiego normalizatora, nowej warstwy ani zmiany kolejności pipeline.

TASK_SCOPE:
- backend/layers/ner_adapter.py
- backend/layers/ocr_normalizer.py
- backend/tests/test_audyt_2026_10.py
- backend/layers/contact.py

OUT_OF_SCOPE: F3 (PESEL/telefon — przywrócenie oryginalnych spanów); `layers/identity.py`, `layers/contact.py` (poza ROZSZERZENIEM CC E1 niżej), alokator, mapowanie tokenów, `Depseudonimizuj.tsx`, OCR engine/Tesseract, `pipeline_new.py`, zmiana Guard/fail-closed, seed/T04, słowniki, architektura AnchorEngine, szeroka refaktoryzacja normalizacji, poprawki regex dla IBAN (osobny T07), prawdziwe dokumenty klienta.

## Minimalne testy i dowody
1. Zdjąć `xfail(strict=True)` i doprowadzić do PASS istniejące `test_fix_ocr_email_nie_skleja_zdan` (dwie parametryzacje) i `test_ocr_normalizer_nie_psuje_slow` w `backend/tests/test_audyt_2026_10.py`. Dodać minimalne przypadki „12/2026. Termin”, „654. Termin” oraz dopasowanie `Tel: +48 606 219 T2T` i „anna. nowak@wp.pl”, bez duplikowania testów warstw.
2. Testy negatywne czystego tekstu i pozytywne OCR na jednym szwie: spacja po kropce w zdaniu i newline nienaruszone; następne słowo po numerze identyczne; zamaskowanie syntetycznego adresu e-mail i telefonu nadal działa. Regressions nie mogą być „zielone” tylko dlatego, że rozpoznawanie PII przestało działać — sprawdź wynik *i reverse_map* lub status blokady.
3. Uruchomić wskazane testy celowane (`cd backend && py -3 -m pytest tests/test_audyt_2026_10.py -q -o log_file=NUL` na Windows) i najmniejsze testy istniejących ownerów. Bez pełnej suity, chyba że ujawni się rzeczywisty szew regresji.
4. Uruchomić istniejący `audyt/engine_quality.py --seed 2026` na dokładnie tych samych wejściach przed/po, z raportem poza repo. Porównywać `input_digest` i każdą sekcję M1/M2/M3, osobno holdout, jeśli dostępny identyczny plik. Raportować wzrost liczby identycznych round-tripów lub wskazać bez zakłamań inne pozostałe źródła różnic; brak nowych M1 `leak`/`blocked` ani M2 `fp` w porównywalnej próbie. `F3` nie może być milcząco uznany za naprawiony.
5. Do dostawy: exact SHA, syntetyczne fragmenty reproduktorów, liczby M3 przed/po, jawne regresje i wynik gate. Raporty nie mogą zawierać danych z rzeczywistych dokumentów, profilu, archiwum.

PASS: F1 i F2 poprawione w dwóch istniejących warstwach; 3 poprzednie xfail przeszły na PASS; przykłady zwykłego tekstu są wierne znak po znaku; istniejące maskowanie rzeczywistych postaci danych syntetycznych nie pogorszyło się; pomiar M3 rzetelnie pokazuje stan po poprawce. Nie wymagamy 100% w M3 ani naprawy F3.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/layers/ner_adapter.py --symbol _fix_ocr_email
- TARGETS: backend/layers/ocr_normalizer.py --symbol _PHONE_AFTER_KW_RE
- REASON: zmiana dwóch istniejących reguł normalizacji; przed implementacją sprawdzić ich wywołania i odbiorców.
GATE: nowych plików 0, nie zwiększać niepotrzebnie dużych istniejących funkcji/plików; >150 zmienionych linii lub ratio >5:1 wymaga decyzji. Jeżeli CC odkryje inne F1/F2 w analogicznym mechanizmie, obowiązuje `ROZSZERZENIE CC` z jawnie dopisanym TASK_SCOPE, nie samowolna przebudowa pipeline.

## ROZSZERZENIE CC (2026-10-17, przed kodem rozszerzenia)
Ta sama klasa co F1 (kropka + spacja po adresie e-mail sklejana z następnym słowem), mechanizm analogiczny — klauzula GATE tego briefu. Plik dopisany do TASK_SCOPE.
- **E1** `backend/layers/contact.py::_EMAIL_OCR_RE`: separator TLD `[ \t]?[.,][ \t]?` + TLD `[a-zA-Z]{2,6}` z IGNORECASE łapie „nowak@example.pl. Termin” jako e-mail z TLD „Termin” → tekst traci słowo „Termin”, a reverse_map dostaje „nowak@example.pl.Termin” (Przywróć oddaje sklejony tekst). Reproduktor (bez spaCy): `run_pipeline_new("Kontakt: nowak@example.pl. Termin płatności 14 dni.")` → `"Kontakt: EMAIL_001 płatności 14 dni."`, `{EMAIL_001: "nowak@example.pl.Termin"}` — także przed T11.
- Poprawka: TLD po separatorze ze spacją OCR tylko małymi literami (`(?-i:[a-z]{2,6})`); „wp. pl”, „wp ,pl” itp. nadal łączone. Bez zmian w kanonizacji, telefonach i kolejności warstw.
- Test: pion z e-mailem przed „. Termin” — tekst wierny, wartość w mapie bez „Termin”; OCR „jan@wp. pl” nadal jeden e-mail.
