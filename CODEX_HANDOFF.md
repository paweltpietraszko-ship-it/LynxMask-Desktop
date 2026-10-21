# Stan po kompaktowaniu — LynxMask, 2026-10-19

## STAN 21.10.2026 — czytaj najpierw (sekcje niżej z datami wcześniejszymi to historia; bieżąca kolejka: `BOARD.md` → TERAZ)
- **Zmergowane:** zdjęcia — PP-OCRv6 z prostowaniem (`PP-LCNet_x1_0_doc_ori`) **domyślnie**, Tesseract tylko zapas (`LYNX-PHOTO-CHAIN`
  `7dfe261`); odkrywanie pojedynczego tokenu w UI jak Mobile (`LYNX-MANUAL-REVEAL` v5 `c426211`); własne środowisko `.venv` +
  `backend/requirements.txt`, aktualizacje bezpieczeństwa, Morfeusz 1.99.15 (`LYNX-DEPS-UPDATE`); siatka HerBERT przed Guardem
  `LYNX_HERBERT=off|PER|ORG|PER,ORG`, **domyślnie off** do decyzji po pomiarze (`LYNX-HERBERT-NET` `dcaa3e1`); FIRMA — forma prawna
  nigdy sama, lista prefiksów tylko ze słów wyłącznie własnych, urzędy nigdy FIRMA (`LYNX-FIRMA-FILTER-FIX` `325b031`).
- **Proces (Paweł 21.10):** poprawki (błędy, filtry, listy, zależności) idą **bez Architekta** — CC pisze `brief.md`, Codex precheck
  i audyt; Architekt projektuje zmiany programu (nowe funkcje, architektura, kontrakt). Pomiary robi pomocnik CC; miarka = wycieki
  i fałszywe alarmy na końcu łańcucha, wiele zbiorów naraz.
- **Uruchamianie:** `LynxMask.vbs` startuje silnik z `.venv` (zapas: `py -3`); modele w `backend/models/{ocr,herbert}` (poza git,
  SHA w kodzie; na komputery klientów dostarczy `LYNX-INSTALLER`).


Przeczytaj także początek CODEX_START_HERE.md. To przekazanie pracy, nie specyfikacja.
Najpierw odśwież właściwy wiersz BOARD z origin/main; nie uruchamiaj audytów historycznych.

## Najważniejszy sposób pracy

- Paweł oszczędza limit. Audyty WĄSKIE I PROPORCJONALNE, nie pokaz możliwości.
- Rola: niezależny tester; bez zmian produktu, projektowania za Architekta i subagentów.
- Mała poprawka: aktualny wiersz BOARD + zmieniony fragment kontraktu + diff od
  poprzedniego badanego SHA + zachowany reproduktor + potrzebny test ownera. STOP przy dowodzie.
- BRIEF_ONLY: żadnych testów, modeli, benchmarków, reproduktorów ani diffu implementacji.
  Kod tylko punktowo, aby potwierdzić istniejący szew. Jedna zamknięta lista braków.
- Nie ponawiaj pełnych suit i 178 dokumentów przy mikrofixie. Poszerzenie musi mieć
  konkretny powód lub wynikać z kontraktu. Podaj ten powód przed poszerzeniem.
- FAIL tylko TRACE + OWNERSHIP + niezależny REPRO exact SHA. Niejasność ≠ FAIL.
- Mechanika eksperymentu może mieć PASS, a jego hipoteza być nietrafna. Nie poprawiaj
  gold pod wynik; nie dopisuj wyjątków pod kolejne ataki; nie udawaj certyfikacji produktu.
- Raporty nowe, nigdy nadpisywane: tasks/<id>/round_01/tests/tests_r<n>.txt.
  Publikacja na gałęzi Tasku, tylko jego wiersz BOARD na main. Jest stała zgoda na
  publikację raportów/BOARD i ff-only main; merge kodu wyłącznie na polecenie Pawła.
- Zachowuj równoległą pracę CC. Bez force-push i przepisywania main. W razie konfliktu
  publikacji zachowaj obie notatki; nie scalaj przy okazji kodu zadania.
- Zgoda na rozmiar jednego etapu nie jest automatycznie zgodą na każdy następny.
  GATE raportuj proporcjonalnie, nie myl z defektem i nie blokuj samego odczytu/audytu.

## Bieżące zadanie i następny ruch

LYNX-ARENA-SIGNALS-PILOT: BRIEF_ONLY zakończony PASS PREIMPLEMENTATION.
Brief/source: 2ebdf1e2e871945022fafcebad08be6ba2ce6f73.
Raport: 4c75236, tasks/LYNX-ARENA-SIGNALS-PILOT/round_01/tests/tests_r1.txt.
Gałąź: task/LYNX-ARENA-SIGNALS-PILOT. BOARD wpis audytu: 90202d3.
Następny ruch CC: review, szacunek i implementacja według GATE. Nie ma jeszcze
opublikowanej implementacji w sprawdzonej zdalnej gałęzi. Po dostawie nowy audyt r2+;
nie powtarzać prechecku. Kod lokalnego worktree CC nie jest automatycznie dostawą.

Pilot: 10–12 syntetycznych czystych tekstów, rzeczywiste identity/contact/address
i spacy_ner.detect_entities, ten sam candidate set do zamrożonych R1/R2; tylko dwa
nowe pliki arena_signal_probe.py i tests/test_arena_signal_probe.py. Bez OCR, profilu,
API, nowych arbitrów, generatora i 178 dokumentów. Po dostawie własne 3 nowe syntetyki.

Punktowo potwierdzone ograniczenia szwu (nie odkrywaj od nowa):
- allocate widzi udane przydziały po wewnętrznej selekcji warstwy, nie wszystkie hity regex;
- allocate.value bywa kanoniczne; raw literal to original[start:end], bez szukania po wartości;
- SPACY_DIRECT to wrapper: deduplikuje wartości; przy wielowierszowej OSOBA skraca text,
  ale pozostawia ent.end_char. Rozbieżność text/wycinek ma być MAPPING_ERROR lub
  ADAPTER_UNSUPPORTED, a nie zero trafień / zgadywanie offsetów. Nie naprawiać wrappera
  w pilocie. Model niedostępny lub błąd nie może udawać sukcesu.
- Pilot nie mierzy całej jakości obecnej aplikacji, wszystkich detektorów ani udziału OCR.

## Pytanie Pawła: silnik czy OCR?

Kalibracja silnika na CZYSTYM TEKŚCIE z niezależnym gold. Odporność na OCR osobno,
docelowo na tych samych dokumentach przed/po OCR, z oddzielnymi wynikami. Nie mieszać
błędów OCR do oceny wykrywania na czystym wejściu. Wiemy z wcześniejszych bezpośrednich
syntetyków, że nie wszystkie błędy pochodziły z OCR; nie znamy proporcji dla całej aplikacji.
Detektor proponuje typ i zakres; arbiter rozstrzyga między propozycjami. „Niezależny
detektor potwierdzi cały zakres” jest celem, nie gotowym mechanizmem ani dowodem.

## Zamknięte etapy — dowody do wykorzystania, nie powtarzania

- LYNX-ARCH-ARENA v0.1.2: F1 zamknięte na 897351c (kod dc149cd), raport r6 b03dfed;
  40 testów, zachowany repro Unicode M 7/7 STOP. Nie otwierać F1 ponownie bez nowego dowodu.
- V02: kod 6dae87d, testy 08c7a5b, kontrakt/snapshot f3e547a. MECHANICS_PASS;
  raport r1 43d4bf7 + repro, 45 passed. 35 wcześniejszych prób: STOP 9→5,
  poprawne RENDERED 14→18. Własny H1/O2 ujawnia FP/połknięcie osoby i prozy
  przez szeroką FIRMA z końcówką Sp. z o.o. To obalenie hipotezy, nie błąd implementacji.
- Architekt uznał H1 w 069dfcf. Opinia Codexa r2 c48c846: nie stroić kolejnego arbitra
  przed pomiarem rzeczywistych sygnałów. Stąd bieżący SIGNALS-PILOT.
- LYNX-ADDR-EMAIL-LEAKS: PASS zakresu na c9f1b54, kod 6ee688a; raport/repro r2 5843f01.
  Niezależny RED L1–L5, GREEN 12 pipeline/roundtrip +15 wzorców EMAIL +5 clean;
  22 testy i373 regresje/3 xfail. Pełne stare HTTP PARTIAL przez 401/token, nie nowy wyciek.
  178 dokumentów = pomocnicze agregaty CC, nie niezależna powtórka Codexa.
- LYNX-ONE-LAUNCHER: PASS techniczny/PARTIAL rzeczywisty GUI na c822c2b, kod335420b;
  raport/harness r1 4e78234. 6 prób WSH z atrapami +6 disk_pii. Native start to dowód CC.

## Najnowsza dodatkowa propozycja — nie kontrakt

main 4e715c2 dodał LYNX-ARCH-HYBRID od CC do Architekta. To propozycja łączenia obecnych
detektorów z arbitrem i jedną podmianą, później dodatkowych modeli/słowników i widoku OCR.
Nie audytowano jej ani nie przyjęto jako produktu. Szczególnie twierdzenia o zachowaniu
Guarda są propozycją do sprawdzenia ze spec/OWNER, nie nową PRODUCT_TRUTH. Nie wdrażaj
hybrydy podczas audytu pilota i nie uruchamiaj wszystkich klocków naraz.

## Środowisko i bezpieczeństwo

Repo: C:\Users\p_pie\Desktop\LynxMask-Desktop.
Własny czysty worktree Codexa: C:\Users\p_pie\AppData\Local\Temp\lynx-codex-audit-20261019,
ostatnio detached na 4c75236. Używaj tego worktree; nie twórz migawek wewnątrz repo.
Przed przełączeniem zawsze git status -sb. Pozostałe worktree Temp/claude należą do CC.
Python: C:\Users\p_pie\AppData\Local\Python\pythoncore-3.14-64\python.exe.
pytest.ini ogranicza zbierane pliki; test ownera trzeba wskazać jawnie.
Nie restartuj i nie podmieniaj backendu Pawła na 8765. Token zmienia się przy restarcie;
nie wypisuj go ani nie commituj. HTTP 401 nie jest dowodem wycieku. Własny serwer tylko
oddzielnie i gdy potrzebny; nie ma obecnie serwera uruchomionego przeze mnie.
Żadnych realnych danych, profili, surowych wyników lub nazw klientów w repo/raportach.
W pamięci wolno zapisywać tylko na wyraźne polecenie; to przekazanie zostało zamówione
przez Pawła przed kompaktowaniem, 2026-10-19.
