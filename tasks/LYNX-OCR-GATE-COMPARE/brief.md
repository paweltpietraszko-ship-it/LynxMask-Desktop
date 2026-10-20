# Brief — LYNX-OCR-GATE-COMPARE: orientacja + odczyt PP + kotwice zamiast globalnej bramki? Eksperyment porównawczy

STATUS: PROJEKT BRIEFU CC na prośbę OWNERA (20.10, „pisz brief”) → Architekt akceptuje lub poprawia → Codex PREIMPLEMENTATION →
zgoda OWNERA na rozmiar → CC implementuje → Codex audytuje exact SHA. Pomiar offline, produkt bez zmian. Bez merge bez polecenia OWNERA.
PRODUCT_TRUTH: `arch/spec.md` S1 (lokalnie), S3, S5; `BOARD.md` → wiersze `LYNX-OCR-QUALITY-GATE`, `LYNX-OCR-ORIENTATION`,
`LYNX-OCR-GATE-COMPARE`; wyniki C1 (`tasks/LYNX-OCR-CASCADE/round_01/implementation/DELIVERY.md`, merge `78648f7`).

## Skąd ten Task
1. C1: Tesseract nie naprawia odczytu PP-OCRv6; najsilniejszy sygnał to identyfikator o złym kształcie w odczycie PP.
2. Realne zdjęcia OWNERA: 4 z 9 odmów wynika wyłącznie z obrotu; pewność Tesseracta odrzuca zdjęcie, które PP czyta czytelnie
   (ocena oka OWNERA) → Tesseract to zła miarka jakości dla PP.
3. CC zmierzył miarkę zastępczą (odsetek słów odczytu PP znanych Morfeuszowi) — obiecująca, ale to globalna liczba dla dokumentu.
4. Alternatywa przekazana przez OWNERA: rozdzielić **orientację** (wyspecjalizowany klasyfikator), **błędne fragmenty**
   (kontekst + struktura: „NIP:” + zła liczba cyfr → zakryj cały fragment, bez zgadywania) i **kompletność** (pominięta linia
   to utrata treści, nie wyciek).
5. OWNER: „część problemów rozwiązałby AnchorEngine z Mobile — system kotwic, nie waliduje cyfr”. **Sprawdzenie CC (20.10,
   silnik Desktop przez `/preview`, teksty syntetyczne):** Desktop już dziś zakrywa uszkodzone identyfikatory po etykiecie bez
   sumy kontrolnej — `NIP: 742-333-75-90`, `NIP 7423375 90`, `PESEL: 5002245882`, `PESEL: 50O22458822`, IBAN 25-cyfrowy,
   `Nr rachunku: …`, `Sygn. akt Km 29O74/2025`, `tel. 6O1 234 5B7`, `Dowód osobisty: ABC 12345` → wszystkie zamaskowane.
   **Dziury względem AnchorEngine Mobile** (kotwica + klasa znaków cyfropodobnych `[0-9OolIiSsBbZz]`):
   - `ur. 12.O3.1985` → **niezamaskowane** (data urodzenia z literą zamiast cyfry; Mobile A.7/A.7b);
   - `NIP: 742-33-75-90 | PESEL: …` (dokładnie odczyt PP z `doc_00004`) → `NIP: NUMER_006-90` — **końcówka „-90” jawna**;
   - `ul. Zielona 2OO` → `ADRES_002O` — jawna litera po tokenie (kosmetyka, nie PII).
   Wniosek: reguła fragmentów z alternatywy w Desktop w większości istnieje (warstwy `identity`/`numeric`); brakuje parytetu
   kotwic z Mobile dla cyfr pomylonych z literami i granic. To **osobny Task naprawczy** (port reguł AnchorEngine A.5/A.7/A.7b
   z klasą D), nie część tego eksperymentu — patrz OUT_OF_SCOPE i wiersz BOARD.

## Cel: odpowiedź liczbami, którą drogą iść
Porównać na tych samych danych, **na końcu ścieżki** (tekst gotowy do udostępnienia po istniejącym silniku), trzy warianty:
- **A (CC):** orientacja = obrót o najwyższym odsetku słów Morfeusza (4 × PP) → PP → bramka słownikowa 0,8 → `/preview`.
- **B (alternatywa):** orientacja = klasyfikator `PP-LCNet_x1_0_doc_ori` → jeden PP → `/preview` (istniejące kotwice/warstwy),
  bez bramki dokumentu; pominięte linie raportowane osobno.
- **B+ (rekomendacja CC):** jak B + **niska** bramka słownikowa tylko na śmieci (próg wybrany na zbiorze znanym z siatki
  0,5/0,55/0,6/0,65, przed holdoutem).
Punkt odniesienia: **dziś** (Tesseract bez obrotu, bramka 70) — ten sam `/preview`.

## Dane
- `backend/dataset_20260627_095419` (50, znany — wybór progu B+), jego kopie obrócone o 90/180/270 (generowane w pamięci, bez zapisu),
  `backend/dataset_20261016_fresh` (100, holdout — tylko kontrola, raz, po zamrożeniu reguł commitem).
- Realne zdjęcia OWNERA `backend/dataset_real/images/*.jpg` (lokalne, bez gold): tylko orientacja wybrana przez A i B,
  przyjęcie/odmowa, czas — **agregaty bez nazw plików i tekstu**; ocena poprawności = oko OWNERA na lokalnym pliku (nie w repo).

## Miary (każda osobno, bez jednej sumy)
1. **Pozostałość:** wartości gold widoczne w tekście do udostępnienia (`anonymized_preview`) — jawne całe, jawne fragmenty
   ≥ 4 cyfry/litery identyfikatora (np. „-90” się nie liczy, „75-90” tak — reguła zapisana w kodzie przed pomiarem), per typ, krytyczne osobno.
2. **Przyjęte / odrzucone dokumenty**, w tym odrzucone obrazy bez degradacji (L0).
3. **Fałszywe alarmy:** tokeny na tekście nie-PII ponad punkt odniesienia (`classify_extra` z `benchmark_ocr_diagnostics`).
4. **Kompletność (osobno, nie wyciek):** wartości gold nieobecne w odczycie PP (`classify_miss` = `BRAK_W_OCR`).
5. **Orientacja:** trafność na obróconych kopiach (A vs B), czas na stronę, RAM.
Zgoda wariantów ≠ prawda; procent bez odtworzenia punktu odniesienia (dziś = wynik `benchmark.py` 274/290, krytyczne 0/107
dla Tesseracta bez obrotu) jest nieważny — narzędzie najpierw odtwarza ten punkt.

## Model orientacji (bez zgadywania o pochodzeniu)
Oficjalny `PaddlePaddle/PP-LCNet_x1_0_doc_ori` (Apache-2.0) jest w formacie Paddle. W eksperymencie dopuszczalne:
(a) konwersja własna `paddle2onnx` w osobnym tymczasowym środowisku, albo (b) gotowy plik ONNX z jawnym źródłem i SHA256 w raporcie.
Model leży poza repo (`~/lynx_models/doc_ori/`), brak pobierania w trakcie pomiaru; brak pliku → NOT_RUN wariantu B z powodem.
Trafność modelu jest **mierzona** na obróconych syntetykach, nie przyjmowana z karty modelu (99,06% producenta to nie nasz wynik).
Decyzja produkcyjna o źródle modelu — poza tym Taskiem.

## Implementacja — pomiar, nie produkt
Jeden skrypt `tasks/LYNX-OCR-GATE-COMPARE/measure/compare_gate.py`:
- reużywa `ocr_rapid._get_engine/build_text`, `pp_quality.MODEL_SHA256`/`pp_quality.preflight`, `benchmark_ocr_diagnostics`,
  `benchmark` (token, `_CRITICAL_KEYS`) przez import — bez kopiowania;
- `/preview` z tekstem PP jako plik `.txt` na działającym silniku (SHA backendu w raporcie; silnik musi odpowiadać kodowi main —
  sprawdzić i zapisać); bez zmian `/preview`, OCR, warstw, Guarda;
- raport JSON tylko do `--out` poza repo: ID syntetyków, klucze/typy gold, liczby, czasy, SHA modeli/kodu/danych;
  zero wartości, tekstu OCR i nazw plików realnych.
Testy `backend/tests/test_ocr_gate_compare.py` na sztucznych danych (bez modeli): reguła fragmentu ≥ 4 znaków, liczenie pozostałości
z tokenami obok wartości, NOT_RUN przy braku modelu, odmowa ścieżek `dataset_real` dla trybu gold i `--out` w repo, determinizm
dwóch przebiegów (poza czasem), wybór progu B+ tylko ze zbioru znanego.

TASK_SCOPE:
- tasks/LYNX-OCR-GATE-COMPARE/measure/compare_gate.py
- backend/tests/test_ocr_gate_compare.py

OUT_OF_SCOPE: zmiany produkcyjne (OCR, `/preview`, warstwy, kotwice, Guard, progi), port reguł AnchorEngine (osobny Task po tym
pomiarze — dziury opisane wyżej idą do BOARD), aktywacja PP, instalacja modeli w aplikacji, UI/onboarding, zmiana S3/S4,
realne dane w repo, pełna suita.

GATE: dwa nowe pliki, każdy ≤ 600 l., funkcje ≤ 50 l. Szacunek CC: skrypt ~330 l. + testy ~130 l. ≈ 460 l. (> 150) → zgoda OWNERA
na rozmiar przed kodem.

KRYTERIUM WYNIKU (zapisane przed pomiarem): wariant wygrywa, jeśli na holdoucie ma **nie więcej** krytycznych pozostałości niż
punkt odniesienia i najmniej odrzuconych obrazów L0; przy remisie — mniej fałszywych alarmów, potem krótszy czas. Gdy żaden
wariant nie spełnia warunku krytycznego, wynik = `NO_WINNER` i nic nie idzie do produktu.

PRZEKAZANIE: Architekt → decyzja o briefie (akceptacja/poprawki) w tym pliku albo wierszu BOARD; Codex → precheck
`tasks/LYNX-OCR-GATE-COMPARE/round_01/tests/tests_r1.txt`; CC po PASS i zgodzie OWNERA implementuje. Merge tylko na polecenie OWNERA.
