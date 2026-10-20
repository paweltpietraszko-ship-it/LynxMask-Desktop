# LYNX-PHOTO-CHAIN — brief Architekta: orientacja + PP-OCRv6 w działającym Desktopie

DATA: 2026-10-20
STATUS: ARCHITECT BRIEF_ONLY → Codex PREIMPLEMENTATION → recenzja/szacowanie CC → zgoda OWNERA na rozmiar i zachowanie widoczne dla użytkownika → CC implementuje pod flagą → Codex audyt exact SHA → OWNER decyduje o aktywacji/merge. **Nie implementować na podstawie samego PASS Codexa.**
SOURCE: `arch/spec.md` S1, S2, S3, S4 (bez zmian), S5, S6; `AGENTS.md`; aktualny `BOARD.md → TERAZ`; propozycja CC `tasks/LYNX-PHOTO-CHAIN/cc_proposal.md` @ `4569d1da41ff5dd178230d8c2d67e27606b48449`; `LYNX-OCR-GATE-COMPARE` (main `9d45115`, DELIVERY etapu 1 i audyt r3). Zgoda OWNERA z 20.10 dotyczy **kierunku**, a nie automatycznego zatwierdzenia progów, instalatora ani nowej polityki bezpieczeństwa.

## 1. Cel, kolejność i dowody

Doprowadzić do produkcyjnie testowalnej ścieżki **obrazu** (JPG/PNG itd.): dedykowany model orientacji → obrót pikseli → PP-OCRv6 small → *obecny*, niezmieniony silnik maskowania i Output Guard → wynik albo jedna odmowa z konkretną alternatywą. Tesseract tylko zapas w razie **awarii technicznej** PP, nie arbiter tekstu i nie jego miara jakości. Zachować dotychczasową ścieżkę Tesseracta bez flagi; wdrożenie nie oznacza włączenia dla wszystkich.

Uzasadnienie: PP zachował ~93–94% gold wobec ~72% Tesseracta na dwóch syntetycznych zbiorach, ale to **wierność OCR, nie gwarancja prywatności**. Eksperyment C1 wykazał, że druga opinia Tesseracta nie naprawia straconych wartości PP. Samo wybieranie obrotu liczbą słów Morfeusza (P1) było wolne i mylne. CC raportuje model `PP-LCNet_x1_0_doc_ori`: 600/600 syntetycznych obrotów i 7/8 zdjęć realnych (jedna słaba fotografia z confidence 0,35); dowody modelu i agregaty na zdjęciach OWNERA **nie były niezależnie odtworzone przez Codexa**. Poprzedni pomiar łańcucha po poprawkach nie ukończył obu zbiorów 50/100 z przyczyn RAM/izolacji, a 17 `UNKNOWN_REVIEW` na `dataset_clean` nie zostało zamkniętych. Nie przedstawiać go jako finalnego PASS.

**Kolejność:** ten Task pierwszy; po nim `LYNX-OSOBA-REDESIGN`, z HerBERT jako ostatnią warstwą, w osobnym kontrakcie. Bez równoległych zmian silnika OSOBA, tokenów lub S4, aby przypisać regresje do OCR.

## 2. Zachowanie i właściciele kodu

- Zakres wejścia: **tylko obrazy** obsługiwane obecnie przez `ocr_engine.extract_text_from_image`. PDF-y ze skanami, maskowanie oryginalnych pikseli, layout i eksport PDF nie stają się obsługiwane przez to zadanie.
- Routing: `ocr_engine.extract_text_from_image` wybiera ścieżkę zgodnie z flagą; nowy wąski owner `backend/photo_chain.py` odpowiada tylko za orientację, obrót i decyzję o przyjęciu odczytu PP. `ocr_rapid.py` pozostaje jedynym wykonawcą PP, `_run_tesseract` zachowuje swoją implementację. **Bez kopiowania dostawców, Guardów, normalizatorów i tokenizacji**.
- Orientacja: wyłącznie lokalny `PP-LCNet_x1_0_doc_ori` z jawną licencją, SHA256 wag, preprocessingiem i mapą klas zweryfikowaną przez powtórzenie co najmniej prób 0/90/180/270. Operacja na kopii obrazu: miniatura do klasyfikacji, obrót **pełnej rozdzielczości** do PP. Uwzględnić EXIF i fizyczną orientację bajtów bez podwójnego obrotu; EXIF nie jest arbitrem. Nigdy nie wywoływać PP cztery razy jako ukryty fallback P1.
- Wybór jakości głównej ścieżki **proponowany do pomiaru i decyzji OWNERA**, nie arbitralna deklaracja bezpieczeństwa: (A) confidence **klasyfikatora orientacji** ≥ 0,60 (to NIE pewność OCR), (B) udział słów ≥3-literowych rozpoznanych przez Morfeusza w tekście PP ≥ 0,80; minimum 5 słów kwalifikujących się, inaczej `QUALITY_UNEVALUABLE` → odmowa z alternatywą. Wynik przyjęty tylko po spełnieniu **obu** warunków; brak osobnego pasma WARN. Liczyć stabilnie przy identycznym SHA i słowniku, jawny licznik mianownika i wynik `NOT_EVALUABLE`. **Progi 0,60/0,80 oraz minimum 5 to kandydaci**, oparte na małych wcześniejszych pomiarach, nie zatwierdzone uniwersalne wartości. Codex ocenia testowalność reguły, CC mierzy na znanym zbiorze i realnych zdjęciach; OWNER ma zatwierdzić wartości przed jakąkolwiek aktywacją dla użytkownika. Jeśli danych nie starczy do uzasadnienia, `NOT_READY`, pozostaje Tesseract. Nie dostrajać pod późniejszy holdout.
- `ocr_result.quality`: wyłącznie `ok` albo `reject` na nowej ścieżce; odmowa nie podaje tekstu, mapy ani tokenów (S3). **Nie wolno wyświetlić miary słownikowej jako „pewności OCR”.** `OCRResult.confidence=0.0` z fazy A też nie oznacza rzeczywistego 0% — zmienić prezentację `frontend/src/screens/Pseudonimizuj.tsx`: dla PP/OCR nowej ścieżki nie wyświetlać procentu pewności odczytu; meta może wskazać nazwę dostawcy i status; metryka wewnętrzna odrębna od Tesseract `confidence`. `document_processor.py` pozostaje miejscem przekazania metadanych do API, bez zmiany maskowania.
- Użytkownik przy odmowie otrzymuje komunikat: **„Popraw ujęcie: skorzystaj ze skanera dokumentów, ustaw lepsze światło i kąt aparatu. Możesz też wkleić tekst dokumentu.”** UI wykorzystuje istniejący `ocr_rejected`, a przycisk/odnośnik przełącza na już dostępne pole wklejania. Nie pokazywać liczb/progów. Brak nowego ekranu.
- Awaria modelu/PP, brak plików, błąd inferencji albo timeout PP → **jednorazowe** uruchomienie istniejącej ścieżki Tesseracta i jej dzisiejszej bramki jakości; w metadanych `engine="tesseract"` i beztreściowy kod przyczyny technicznej. **Nie przełączać na Tesseract przy słabym, ale wykonanym odczycie PP**; taki wynik podlega odmowie. Jeżeli Tesseract też nie działa, zwrócić odmowę, nie surowy OCR. Fallback nie może omijać zamrożonego S3/S4.
- Błąd timeout w obecnym `ThreadPoolExecutor(max_workers=1)` nie zabija pracy wątku. Minimalny bezpiecznik do wyboru i przetestowania przez CC: po pierwszym timeout oznaczyć PP jako `UNAVAILABLE_UNTIL_RESTART`, **nie dodawać dalszych zadań do kolejki zawieszonego executora**; następne zapytanie ma wrócić ścieżką Tesseract albo bezpieczną odmową, bez zawieszenia. Przed wdrożeniem reproduktor: dwa lub więcej kolejnych requestów po zasymulowanym zacięciu, ograniczony czas odpowiedzi, brak nowych wiszących zadań i brak wycieku. Jeśli model jest nieprzerywalny i nie da się zapewnić bezpieczeństwa pamięci/wyłączenia procesu, CC zgłasza `NOT_READY`, nie przebudowuje backendu bez nowego briefu.
- Offline: modele weryfikowane SHA i używane wyłącznie z lokalnych ścieżek, bez automatycznych downloadów, telemetria ONNX wyłączona, test ruchu wychodzącego na starcie i w obu wariantach. Logi wyłącznie kody/typy błędów, żadnych tekstów OCR, nazw plików użytkownika ani prywatnych ścieżek. Atrybucje licencji i pakowanie modeli potrzebne do wydania. Nie zakładać, że domyślna ścieżka `~/lynx_models` działa na komputerze klienta: pakiet musi zawierać/udostępniać modele i jednoznacznie ustawiać katalog modeli; naruszenie hasha = PP niedostępny, nigdy ciche użycie niezweryfikowanych wag.

## 3. Plan falsyfikacji i odbiór

**Przed wdrożeniem i zmianą domyślnego OCR** zamrozić SHA implementacji, modele/hash, słownik Morfeusza, regułę bramki i mianowniki. Oddzielić:
1. Testy jednostkowe na atrapach modeli (nie służą za dowód jakości): wszystkie 4 orientacje, remisy i progi graniczne, EXIF/double rotation, brak/zmieniony hash, tryb domyślny Tesseract, PP technicznie awaryjny/timeout i kolejny request, PP słaby jakościowo (bez fallbacku), pusty/krótki OCR, brak network/download, brak PII w logach, jakość meta i UI, bez zmian tokenów.
2. Integracja na **prawdziwym** `/preview` z obrazem i **prawdziwym** aktualnym silnikiem/Guardem, w izolowanym profilu i backendzie jak GATE-COMPARE; nie podawać `.txt` zamiast obrazu i nie używać prywatnego profilu OWNERA. Podzielić dane na znany 50 i historycznie użyty kontrolny 100; 100 nie jest świeżym, nietkniętym holdoutem. Osobno na skanach obróconych, poziomach degradacji L0–L3 i typach encji.
3. Raportować na **pełnym mianowniku**: przyjęte/odrzucone/awarie/Tesseract fallback i L0 odrzucone; `MASKED/ASKED` (ASKED tylko **hipotetycznie** do czasu wdrożenia GUARD-RESIDUE)/`HOLE/UNKNOWN_REVIEW/NOT_IN_OCR`, krytyczne osobno; liczbę pytań tylko jako `would_ask`, nie obiecywać, że UI realnie chroni w ten sposób. Obecny Output Guard i rzeczywista blokada wyników osobno. Czas mediana/p95 i RAM, dodatkowo cold start, drugi request po timeout. Nie ogłaszać bezpieczeństwa na podstawie 0 krytycznych przy dużej liczbie odmów.
4. Każdy `UNKNOWN_REVIEW` na porównywanych syntetykach oraz **17 wcześniejszych** z `dataset_clean` ma zostać wyjaśniony przez CC jako błąd miarki/nieidentyfikujący fragment/rzeczywista dziura, z dowodem syntetycznym bez wartości w raporcie. Jeśli nie da się rozstrzygnąć — `NOT_READY`, nie „zero dziur”. Wyniki GATE-COMPARE po ETAPIE 2/2b niedomknięte — nie uzupełniać ich domysłami.
5. Porównanie gałąź vs bieżący `main` na tych samych obrazach, bez mieszania różnic OCR z jakością warstw. Strażnik `benchmark.py`, `[OCR-DIAG]` i test Przywróć token→oryginał. Testy nazwisk, skrótów i mapy OSOBA mają wykluczyć regresję przed osobnym `OSOBA-REDESIGN`. Przyjmowany wynik do użytkownika nadal podlega obecnemu Guardowi; żadne nowe „pytania” z symulacji go nie zastępują.
6. Realne zdjęcia OWNERA tylko lokalnie i z oceną wzrokową OWNERA: poprawny obrót, czytelność, przykłady niebezpiecznych resztek, odmowa/akcja naprawcza, brak zapisów realnych danych w repo. Wymagany test instalacyjny bez zewnętrznych modeli na ścieżkach deweloperskich. Limit czasu **cel** ≤ 3 s/str.; pomiary większych zdjęć mogą wykazać niespełnienie, wtedy `NOT_READY_PERFORMANCE` i jawne rozstrzygnięcie zamiast cichego zmniejszania obrazu. Skalowania wejścia do PP nie zmieniać bez testów utraty małych znaków/identyfikatorów.

**Warunek oddania do OWNERA pod decyzję o aktywacji:** 0 potwierdzonych krytycznych dziur w dostępnych do skopiowania wynikach testowych, brak nieprzejrzanych `UNKNOWN`, brak regresji S3/S4/Przywróć i 0 odmów bez instrukcji naprawy; liczby akceptacji, fałszywych odmów (w szczególności L0), kompletność tekstu, czas i stabilność pokazane uczciwie, bez deklaracji 100% ochrony. Jeśli słownikowa bramka wyklucza poprawne krótkie dokumenty lub zbyt wiele dokumentów realnych, wynik **NOT_READY** — bez „podnoszenia” wyniku przez odrzucanie. Obowiązuje jawna aprobata progów i zachowania przez OWNERA. **Codex PASS na kodzie ≠ zgoda produktowa.**

## 4. Scope, redukcja, workflow

TASK_SCOPE:
- backend/photo_chain.py
- backend/ocr_engine.py
- backend/ocr_rapid.py
- backend/document_processor.py
- backend/startup_check.py
- backend/tests/test_photo_chain.py
- backend/tests/test_ocr_rapid.py
- frontend/src/screens/Pseudonimizuj.tsx
- frontend/src-tauri/tauri.conf.json
- README.md

OUT_OF_SCOPE: zmiany `backend/layers/*`, silnika OSOBA/FIRMA, HerBERT, Output Guarda, S4, formatu tokenów/.lynxdict, eksportu i redakcji obrazów/PDF, nowych ekranów, drugiej opinii Tesseracta, naprawy niezwiązanych findingów security review. Zmiana `arch/spec.md` wymaga osobnej decyzji OWNERA. Nie tworzyć dodatkowego managera OCR, schedulera, frameworku modeli ani nowego stanu użytkownika.

**SOURCE → NECESSITY (redukcja):** `photo_chain.py`: jedyna nowa odpowiedzialność — obrót i bramka PP (potrzebne wobec C1/ETAP 1); `ocr_engine.py`: istniejący wybór OCR; `ocr_rapid.py`: istniejący dostawca i timeout; `document_processor.py`: tylko metadane statusu; `startup_check.py`: kontrola dostępności modeli; `Pseudonimizuj.tsx`: komunikat i brak fałszywego procentu; `tauri.conf.json`: istniejący właściciel zasobów instalatora. Testy mają korzystać z istniejących fake engine i `/preview`, bez kopiowania całej miarki C1.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/ocr_engine.py --symbol extract_text_from_image
- TARGETS: backend/ocr_rapid.py --symbol extract_rapid
- TARGETS: backend/document_processor.py --symbol _extract_text
- TARGETS: backend/startup_check.py --symbol run
- REASON: nowe wywołanie i reguła bramki zastępują C1 bez równoległego ownera; sprawdzić rzeczywistych importerów i granice przed edycją.

GATE: maksimum **2 nowe pliki**, plik ≤600 l., funkcje ≤50 l.; suma zmian >150 l. albo ratio >5:1 = `WYMAGA_DECYZJI` i zgoda OWNERA **przed kodowaniem**. Szacunek CC w propozycji ~300–350 l. (bez potwierdzenia pakowania); wymagany przegląd rozmiaru i minimalna redukcja przed implementacją. Jeśli rzeczywiste pakowanie wymaga innego istniejącego pliku, CC zgłasza jego nazwę i aktualizuje TASK_SCOPE **przed** pracą, nie dodaje go po cichu.

PRECHECK: Codex wyłącznie BRIEF_ONLY na exact SHA briefu, bez uruchamiania modeli, testów ani pisania kodu; raport `tasks/LYNX-PHOTO-CHAIN/round_01/tests/tests_r1.txt`. Potem CC ocenia kontrakt (może go zawrócić), podaje rozmiar, OWNER podejmuje decyzję. Dopiero wtedy implementacja pod flagą, exact-SHA audyt Codexa, OWNER wydaje polecenie merge/aktywacji. Następny Task: `LYNX-OSOBA-REDESIGN`, HerBERT jako siatka po maskowaniu; nie równolegle z aktywacją PHOTO-CHAIN.
