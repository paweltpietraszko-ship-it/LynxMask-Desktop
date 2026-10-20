# LYNX-PHOTO-CHAIN — propozycja CC: wdrożenie łańcucha zdjęć w produkcie (2026-10-20)

STATUS: cc_proposal → Architekt (brief) → Codex precheck → szacunek CC / zgoda OWNERA → implementacja → audyt → merge na słowo OWNERA.
OWNER 20.10: „Tak, bo nam przepadnie, jeśli twoje badania wykazały, że usunięcie Tesseract jest sensowne, a wstawienie PP z obracaniem
przynosi efekty.” Jeden blok (OWNER: mniej szwów): prostowanie + PP-OCRv6 jako czytnik + reguła odmowy z komunikatem + pakowanie modeli.

## Dowody (wszystkie w repo albo w DELIVERY; bez danych realnych)
1. **PP-OCRv6 czyta lepiej niż Tesseract:** wartości nienaruszone 93,9% (znany) / 93,4% (kontrolny 100) vs Tesseract 71,6%; e-maile
   10/10 vs 0/10 (`LYNX-OCR-PARITY`, faza A `570995e`).
2. **Tesseract nie poprawia PP i nie jest dobrą miarką jakości:** C1 (`78648f7`) — 0/150 przypadków, w których Tesseract odzyskał wartość
   zgubioną przez PP; na realnym zdjęciu OWNERA pewność Tesseracta 0–12% przy odczycie PP ocenionym okiem OWNERA jako czytelny.
3. **Łańcuch na końcu (dziury + pytania Guarda), holdout 100** (`LYNX-OCR-GATE-COMPARE`, DELIVERY `392a433`): PP + silnik — 0 odmów,
   0 dziur krytycznych, 3 prawdziwe niekrytyczne (po przeglądzie, naprawione w ETAPIE 2), mediana pytań 9; dziś (Tesseract, bramka 70) —
   16 odmów OCR, więcej dziur, mediana pytań 11. Najsłabszy element pomiaru był P1 (obrót słownikowy) — zastąpiony niżej.
4. **Prostowanie:** `PP-LCNet_x1_0_doc_ori` (Apache-2.0, ~7 MB ONNX) — 600/600 na syntetykach obróconych 0/90/180/270, 2–5 ms/str.;
   dwie niezależne konwersje ONNX dają identyczne predykcje; realne zdjęcia OWNERA: 7/8 poprawnie (oko OWNERA), błąd wyłącznie na
   zdjęciu złym, przy pewności 0,35 (pozostałe 0,83–0,93; syntetyki min 0,76). Obecny produkt nie prostuje wcale — 4 z 9 realnych
   zdjęć odrzucane wyłącznie z powodu obrotu.

## Zakres proponowany
1. **Nowy moduł** (np. `backend/photo_chain.py`; w `ocr_engine.py` tylko wywołanie zastępujące istniejącą gałąź `LYNX_OCR_ENGINE=rapid` —
   plik nie rośnie): obraz → (EXIF tylko jako wskazówka, nie prawda) → model orientacji na kopii 224 px → obrót korygujący →
   PP-OCRv6 (`ocr_rapid`, te same modele co faza A, SHA w kodzie) → tekst do istniejącego `/preview` (bez zmian silnika).
2. **Reguła odmowy (jedna jasna granica, bez pasma „przetwarzaj z ostrzeżeniem” — OWNER 20.10):** odmowa gdy (a) pewność modelu orientacji
   < próg (propozycja 0,6 — margines względem min 0,76 na syntetykach i 0,35 na złym zdjęciu) albo (b) odczyt PP jest „śmieciowy” wg
   miarki niezależnej od pewności PP (B1: `NO_SAFE_GATE` — pewności PP NIE używać): kandydaci (do wyboru w briefie, na zbiorze znanym):
   odsetek słów znanych Morfeuszowi (zmierzone: syntetyki min 0,53, złe zdjęcie realne 0,33, pozostałe 0,79–0,91) albo liczba pytań
   Guard-reszty na stronę. Komunikat (OWNER): **„Popraw ujęcie: skorzystaj ze skanera, ustaw lepsze światło i kąt aparatu.”** + droga
   zastępcza „albo wklej tekst dokumentu”; bez procentów. Dzisiejszy komunikat fazy A („wynik nie może być udostępniony”) — usunięty.
3. **Tesseract:** przestaje być czytnikiem i miarką; zostaje wyłącznie jako zapas przy **awarii technicznej** PP (brak modelu, wyjątek,
   przekroczony czas) — wtedy dzisiejsza ścieżka Tesseracta z jej bramką, jawnie oznaczona w odpowiedzi. Usunięcie całkowite — osobna
   decyzja OWNERA po okresie próbnym.
4. **Warunki z wcześniejszych ustaleń (zachowane):** timeout PP nie zatrzymuje wątku (faza A, CASCADE brief) — przed wdrożeniem drugi
   request po timeout musi wrócić do pracy (test); offline (`LYNX-OFFLINE-GUARANTEE`): modele tylko z dysku, bez pobierania,
   `onnxruntime` telemetria wyłączona; S3 fail-closed, S5 bez treści w logach; Guard bez zmian (S4 osobno); atrybucja licencji
   (PP-OCRv6/RapidOCR, PP-LCNet — Apache-2.0) w aplikacji; Mobile ma osobny próg (ML Kit) — bez zmian.
5. **Pakowanie:** modele PP (det/rec/cls) i orientacji w katalogu modeli aplikacji z SHA256 weryfikowanym przy starcie
   (`startup_check.py`); brak/niezgodność → zapas Tesseract + komunikat w logu bez treści.
6. **Front:** obsługa nowej odmowy w istniejącej ścieżce `ocr_rejected` (`frontend/src/screens/Pseudonimizuj.tsx`) — tekst komunikatu i
   przycisk „Wklej tekst”; bez nowego ekranu.

## Pomiar odbioru (ta sama miarka co GATE-COMPARE, kod produktu zamiast symulacji)
- Syntetyki 50 + 100 (także obrócone w pamięci) przez **prawdziwy** `/preview` z obrazem (E2E): odmowy, dziury (krytyczne osobno),
  pytania Guarda, czas na stronę; porównanie z dzisiejszym produktem na tych samych plikach.
- Realne zdjęcia OWNERA lokalnie: plik porównawczy do oceny okiem (wyprostowanie, odczyt, odmowa tak/nie) — bez danych w repo.
- Strażnik `benchmark.py` (dziś przez Tesseract): po zmianie zmienia się czytnik, więc punkt odniesienia = ta sama miarka na main vs
  gałąź, a `[OCR-DIAG]` raportowany osobno; nie wolno wnioskować o silniku z różnicy OCR.
- Czas: cel ≤ 3 s/str. na maszynie OWNERA (PP ~1,7–4 s na dużych zdjęciach — do zmierzenia; ewentualnie zmniejszanie obrazu przed PP
  do ustalonej rozdzielczości, mierzone wpływem na dziury).

## Szacunek CC
Moduł ~150–200 l., testy ~120 l., front ~20 l., `startup_check` ~20 l. — razem ~300–350 l. → zgoda OWNERA przed kodem.

## Do rozstrzygnięcia przez Architekta
Miarka „śmieciowego odczytu” (słownikowa vs pytania Guarda) i jej próg; próg pewności orientacji; czy zmniejszać obraz przed PP; okres
próbny z Tesseractem jako zapasem; kolejność względem `LYNX-OSOBA-REDESIGN` (niezależne — proponuję równolegle).
