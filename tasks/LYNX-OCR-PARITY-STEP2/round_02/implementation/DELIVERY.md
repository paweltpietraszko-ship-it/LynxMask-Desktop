# DELIVERY — LYNX-OCR-PARITY krok 2, faza B1 (narzędzie kalibracji PP-OCRv6), CC runda 1

Gałąź `task/LYNX-OCR-PARITY-STEP2B`, kod `9e48593e66c9d0648db3509cae485488bcab4161` (baza: precheck B1 PASS `b695b2c`). Produkt bez zmian; PP dalej odmawia (C1), Tesseract domyślny. Bez merge.

## Werdykt pomiaru: **NO_SAFE_GATE** → zgodnie z §3 briefu **STOP B2**
Pewności per linia PP-OCRv6 nie odróżniają dokumentów z utratą/zniekształceniem danych od dokumentów bez strat; są pewne siebie błędy krytycznych identyfikatorów przepuszczane przez wszystkie reguły siatki.

## Recenzja / rozmiar / gate
Brief przyjęty bez uwag. Zgoda OWNERA na ~370 l. przed kodem (20.10); dostawa 337 l. (narzędzie 214, testy 123). Gate (stdout dosłownie):
```
STATUS: PASS
HEAD_SHA: 9e48593e66c9d0648db3509cae485488bcab4161
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-OCR-PARITY-STEP2/measure/pp_quality.py
```
Uwaga: `gate.py` traktuje `tasks/…/measure/pp_quality.py` jako artefakt (EXCLUDED) — limity sprawdzone ręcznie: ruff „All checks passed!”, najdłuższa funkcja < 40 l., plik 214 l.

## Narzędzie
`tasks/LYNX-OCR-PARITY-STEP2/measure/pp_quality.py`: preflight (wersje, SHA256 3 modeli = faza A, inaczej `NOT_RUN`, nic nie pobiera) → `ocr_rapid._get_engine()` wywołany raz na dokument z `text_score=0.0` (widać też linie, które produkcyjny filtr 0.5 usuwa) → walidacja powiązania `boxes/txts/scores` (rozbieżne długości, NaN/inf, poza [0,1] → brak podstaw → `reject`) → cechy: min, q10, średnia, udziały < 0.7/0.8/0.9, liczba linii odrzuconych filtrem, długość tekstu (pewność rozpoznania ≠ pokrycie obrazu) → tekst „produkcyjny” (`build_text` z linii ≥ 0.5) → każda wartość gold przez `classify_miss`: INTACT / DISTORTED / MISSING / REVIEW → siatka 10 reguł ustalona z góry (`min`/`q10` × progi ok/warn: 0.95/0.85, 0.9/0.8, 0.9/0.7, 0.85/0.7, 0.8/0.6) → wybór **tylko na zbiorze znanym** (0 nie-nienaruszonych krytycznych w dopuszczonych, potem najwięcej dopuszczonych) → jednorazowa falsyfikacja na holdoucie. Raport JSON do `--out` poza repo, bez wartości i tekstu OCR. Testy: 12 (walidacja scores, filtr produkcyjny, pusty wynik, liczenie ok/warn/reject i strat, wybór tylko z tabel znanego zbioru + NO_SAFE_GATE, raport bez wartości i deterministyczny, NOT_RUN bez modeli).

## Pomiar (jeden przebieg 50 + 100; rapidocr 3.10.0, onnxruntime 1.25.0, modele = faza A)
`py -3 tasks/LYNX-OCR-PARITY-STEP2/measure/pp_quality.py --known backend/dataset_20260627_095419 --holdout backend/dataset_20261016_fresh --out <poza repo>`
stdout: `[PP-QUALITY] NO_SAFE_GATE; reguła (zbiór znany): —`
- Gold po OCR (produkcyjny filtr): znany 310 INTACT / 20 DISTORTED / 12 MISSING (z 342); holdout 562 / 30 / 27 (z 619). 0 nieważnych wyników; filtr 0.5 usunął 4 i 6 linii. ~1,95 s/str.
- **Dwa krytyczne identyfikatory na zbiorze znanym przechodzą przez wszystkie reguły z dopuszczonym dokumentem:** `doc_00004` NIP zniekształcony (OCR zgubił cyfrę; linia score 0,95; min dokumentu 0,81 — odrzucany tylko przez najostrzejszą regułę) i `doc_00012` IBAN **pominięty przez detektor** (linii nie ma wcale, pozostałe linie pewne — min dokumentu 0,89, przechodzi każdą regułę). To dokładnie ryzyko z briefu: pewność rozpoznanych linii nie mówi o liniach niewykrytych.
- Rozdzielczość: min dokumentu dla dokumentów ze stratami nakłada się z dokumentami bez strat (znany: DISTORTED 0,55–0,95, MISSING 0,55–0,96, bez strat mediana 0,96; holdout podobnie). Błędy przy min ≥ 0,9: znany 12, holdout 31 (głównie ADRES, też OSOBA, NUMER, 1 EMAIL).
- Koszt bezpieczeństwa reguł opartych na min: np. `min 0.95/0.85` odrzuca 13/50 i 32/100 dokumentów (Tesseract dziś 7/50 i 16/100) i nadal dopuszcza krytyczne straty na znanym zbiorze.
- Holdout pokazuje 0 krytycznych nie-nienaruszonych w dopuszczonych dla wszystkich reguł, ale reguła nie została wybrana (znany zbiór już ją obala) — nie dobierano progów do holdoutu.

## Ograniczenia
- `dataset_20261016_fresh` był wcześniej użyty do porównania adaptera (faza A), więc nie jest całkowicie niewidziany; progi nie były do niego dobierane.
- ADRES: część MISSING/DISTORTED to adres rozłożony w OCR na kilka linii bez przecinka — `classify_miss` (granice wartości, fuzzy w obrębie linii) nie składa linii; etykiety ADRES zawyżają straty. Wniosek nie opiera się na ADRES (krytyczne identyfikatory jw.).
- MISSING (wartości nieodczytanej) nie ma w tekście, więc nie wycieka przez tekst — to strata treści dla AI, nie prywatności; DISTORTED może wyciec, jeśli silnik nie rozpozna zniekształconej wartości. Brief liczy obie jako straty; podział dla decyzji Architekta.
- `dataset_real_public` pominięty zgodnie z briefem (PDF/TXT). Prawdziwe skany OWNERA — nie w B1.

## Rekomendacja CC (decyzja Architekta/OWNERA)
Bramka jakości dla PP oparta wyłącznie na pewności linii nie spełnia kontraktu → STOP B2 w tej postaci. Przewaga PP w odczycie (93–94% vs 72% danych nienaruszonych) pozostaje faktem; możliwe dalsze drogi do rozważenia osobno, nie w tym Tasku: (a) PP bez własnej bramki, ale z **obowiązkowym Guardem pokazującym resztę** (`LYNX-GUARD-RESIDUE`) — zniekształcone wartości trafiają do oceny człowieka; (b) sygnał pokrycia (np. zgodność liczby linii/obszaru z detekcją Tesseracta) zamiast pewności; (c) zostać przy Tesseracie dla skanów.

---

# Runda 2 — F1 z audytu Codexa B1 r2 (`35dfba5`)
Kod `40d6673a2ad8b3a357b73b29f97440a92218383c` (diff od `a954766`: `pp_quality.py` +3/−2, testy +11). **Przyjęte:** niezgodność SHA256 modeli z fazą A zatrzymuje preflight przed silnikiem i pomiarem — `NOT_RUN` (powód: „modele PP-OCRv6 inne niż w fazie A (SHA256)”), exit 2, bez raportu.
```
pytest tests/test_pp_ocr_calibration.py -q → 13 passed (nowy test: inne modele → exit 2, silnik niewywołany, brak raportu)
ruff → All checks passed!
repro_r2.py Codexa (kopia bez asercji HEAD): F1_HASH_0 / F1_HASH_1 → exit_code 2, engine_called false, report_written false → F1_CLOSED
```
Pomiar 50+100 nie powtarzany (zmiana nie dotyka pomiaru; modele użyte w pomiarze r1 miały SHA256 zgodne z fazą A — `models_match_phase_a: true` w raporcie). Werdykt NO_SAFE_GATE bez zmian. Gate r2: `STATUS: PASS`.
