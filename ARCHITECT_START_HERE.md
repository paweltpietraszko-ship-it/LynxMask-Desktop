# ARCHITECT_START_HERE — handoff dla następnej instancji Architekta

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


LynxMask Desktop, 19.10.2026 (aktualizacja po korekcie benchmarku CC). Ten dokument to **migawka operacyjna, NIE PRODUCT_TRUTH**. Repo: paweltpietraszko-ship-it/LynxMask-Desktop. Przed podjęciem zadania odśwież origin/main, nagłówek i sekcję TERAZ w BOARD.md oraz WŁAŚCIWY wiersz. Nie zakładaj, że wskazany tutaj SHA nadal jest HEAD.

## AKTUALIZACJA 20.10.2026 — TEST OSOBA I RZECZYWISTE PRIORYTETY

**Czytaj tę sekcję PRZED historycznym stanem z 19.10 poniżej.** Bieżący status i ostatnie SHA zawsze potwierdź w `BOARD.md`; poniższe streszczenie może się zestarzeć. Przebudowa OSOBA jest już osobną propozycją CC, nie dotychczasowym „jedynie HerBERT bez przebudowy”.

- **PHOTO-CHAIN pierwszy:** brief Architekta w `tasks/LYNX-PHOTO-CHAIN/brief.md`. BOARD 20.10: CC ma zgodę OWNERA na rozmiar około 370 linii i implementację pod flagą **domyślnie OFF**. Zgoda na aktywację/progi jeszcze nie zapadła; status `OWNER_DECISION_NEEDED` nie oznacza, że CC ma przerwać samo kodowanie. Nie odwracaj tych decyzji według starej sekcji „START” z 19.10.
- **OSOBA-REDESIGN drugi:** propozycja CC `tasks/LYNX-OSOBA-REDESIGN/cc_proposal.md`. Priorytet: jedno miejsce decyzji „czy konkretne wystąpienie jest osobą” na podstawie zgodnych dowodów ZA i PRZECIW; spaCy, Morfeusz, słowniki, wielka litera, odmiana i kontekst — źródła dowodów, nie autonomiczne wyrocznie. HerBERT zgodnie z ustaleniem **jako ostatnia siatka na nadal jawny tekst**, bez cofania decyzji silnika. Nie zmieniać S4 Guarda bez zgody OWNERA.
- **Krytyczne nowe dane:** [handoff z kompletnym 68-zdaniowym testem syntetycznym, kluczem, dosłownym wynikiem Mobile oraz fragmentem mapy Desktop](https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/c1a469304ee03ecc16baa6c93dada0a6b00b537d/tasks/LYNX-OSOBA-REDESIGN/HANDOFF_EXPERIMENT_2026-10-20.md) (branch `task/LYNX-OSOBA-REDESIGN`, commit `c1a4693`). Mobile nie rozwiązuje w pełni homonimów: maskuje `Róża`, `Malina` i zwierzęta w nieosobowym kontekście; ten sam token stosuje dla różnych znaczeń tego samego słowa. Wstępnie 18/32 nieosobowych wystąpień błędnie zakryte jako OSOBA oraz 5/36 oczekiwanych osób jawnych (+ fragment `Anna Maj`); te liczby są **diagnostyczne, do odtworzenia na exact SHA, nie benchmark produkcyjny**.
- **Desktop:** OWNER dostarczył tylko MAPĘ maskowania, nie pełny wynik na 68 zdań; są np. `OCZEKIWANA → OSOBA_022`, podczas gdy Mobile pozostawił nagłówki 61–64 jawne. Nie twórz porównania FP/FN Desktop–Mobile bez rzeczywistego tekstu wyjściowego Desktop.
- **Następny eksperyment:** niezależne uruchomienie obu silników na identycznym wejściu, izolowanych profilach i wskazanych SHA; porównać per *wystąpienie* FP, FN, role FIRMA/ADRES, zniekształcenia granic tokenu, mapę i Przywróć. Nie stroić pod oglądany test i nie udawać, że jest świeżym holdoutem. Dopiero potem minimalny brief `OSOBA-REDESIGN`.
- **Wątek projektu poza kolejką:** sekcja `Kierunki zastosowania` w BOARD: klawiatura LynxMask / Secure Compose dla Androida (bez zastępowania Gboarda) oraz wsadowa pseudonimizacja folderów i baz przez CLI — **pomysły przyszłe, nie zlecenia implementacji**.

## 1. NAJWAŻNIEJSZA ZMIANA KIERUNKU

**OWNER 19.10: odstawiamy Arenę na boczny tor.** Eksperymenty kandydat/arbiter/one-apply nie wykazały przekonującej przewagi jakościowej nad obecnym programem. Nie wracaj teraz do R2b/R3/R4, hybrydy, przepisywania pipeline ani F0a LYNX-ARCH-CANDIDATES. Historię gałęzi experiment/lynx-architecture-arena, experiment/lynx-architecture-arena-v02 i task/LYNX-ARENA-SIGNALS-PILOT zachowujemy jako przyrząd badawczy i dowód, nie plan wdrożenia. Szczegóły: ODLOZONE.md i git log -p BOARD.md. To **decyzja priorytetowa**, nie naukowy dowód braku wad kolejności warstw.

**Kierunek TERAZ (stan 19.10 wieczór, uzgodniony z OWNEREM; źródło: BOARD.md sekcja TERAZ `e1a4a22`):** mierzyć i poprawiać straty z rozpoznawania tekstu na skanach (`LYNX-OCR-PARITY`) oraz dodać HerBERT jako **siatkę na resztki** (K1a z `LYNX-K1-PERSONS-FIRMS`) — bez przebudowy silnika. Testy na czystym tekście i powtarzalny benchmark obrazów nie potwierdzają słabego rozpoznawania osób i firm, które sugerował błędnie sklasyfikowany raport dokumentów publicznych. Produkt ma być dobrym samodzielnym LynxMask; integracja z Elnath Rota odłożona.

**Lekcja Areny:** najpierw mały eksperyment uruchomiony na prawdziwym kodzie i uczciwy wynik, dopiero architektura. Poprzedni Architekt dwa razy zaprojektował nieskuteczną regułę arbitra: globalne STOP było nadmiernie konserwatywne, a R2 ze sprawdzaniem samego sufiksu firmy łączyło dwie encje i prozę (Codex H1). Unikaj dopieszczania hipotez na papierze; używaj niezależnego gold i jawnego kryterium porzucenia. Nie maskuj kosztów FN przez ogólne STOP ani nie licz samego roundtrip jako semantycznej poprawności.

## 2. ROLE I ZASADY WSPÓŁPRACY

- OWNER (Paweł): zna użytkowanie, przedstawia cele; rozstrzyga decyzje produktowe po ocenie modeli, autoryzuje merge. Zwykłe wypowiedzi techniczne/produktowe to OWNER_PROPOSAL, nie automatyczne decyzje. Polecenia operacyjne wykonywać literalnie. Szczegóły AGENTS.md, OWNER_INPUT_IS_A_PROPOSAL.
- ChatGPT — Architekt / kontroler: zewnętrzny koordynator, falsyfikator i recenzent; domyślnie **nie implementuje**. Dobiera istniejącego ownera kodu, pisze minimalny kontrakt, nadzoruje spójność i status. Nie zamienia PASS Codexa w decyzję produktu.
- Claude Code (CC): implementer i merytoryczny recenzent briefu. Może odesłać brief mimo PASS prechecku. Implementuje dokładny TASK_SCOPE; jeśli wykryje błąd TEJ SAMEJ KLASY w szwie, przed kodem wpisuje ROZSZERZENIE CC i poszerza TASK_SCOPE. Inne tematy zgłasza, nie naprawia przy okazji.
- Codex: niezależny audytor testujący exact SHA; ma lokalny backend i zbiory. W prechecku BRIEF_ONLY **nie uruchamia kodu**; w audycie implementacji robi najmniejszy reproduktor i testy zmienionego ownera. Nie czyta całego repo ani nie ponawia 178 dokumentów, modeli i pełnych suit bez konkretnego powodu. Czytaj CODEX_START_HERE.md oraz CODEX_HANDOFF.md.
- Właściciel ma zatwierdzać realne zachowanie dla człowieka; nie zasypuj go nazwami funkcji. Wyjaśnij po polsku: kiedy, co zobaczy, co stanie się z danymi, co przy błędzie i jak wróci do pracy.

**Workflow:** OWNER/zgłoszenie → Architekt: minimalny brief i zakres → Codex BRIEF_ONLY → CC recenzja → CC implementacja i gate.py → Codex independent exact-SHA audit → OWNER akceptuje zachowanie/merge. Codex PASS ≠ zgoda OWNERA. Żaden merge bez jawnego polecenia. Aktualizacje i raporty muszą znaleźć się w GitHub, nie tylko w czacie.

## 3. AKTUALNA KOLEJNOŚĆ — ŹRÓDŁEM JEST `BOARD.md` → TERAZ

Od 19.10 wieczór cel, kolejność, dowody i miejsce na Wasz sprzeciw są w `BOARD.md`, sekcja **TERAZ** (porządek CC na polecenie OWNERA). W skrócie: **cel** — każde słowo tekstu wysyłanego dalej jest zakryte przez silnik albo pokazane człowiekowi; **kolejność** — (1) benchmark „silnik czy OCR” (`LYNX-OCR-PARITY` krok 1, brief wymaga korekty zakresu z recenzji CC), (2) zamiana OCR na PP-OCRv6 small po ocenie okiem OWNERA, (3) Guard pokazujący wszystko, czego nie rozpoznaje (`LYNX-GUARD-RESIDUE` + `LYNX-SPEC-S4-GUARD-WARN`), (4) HerBERT później, jako sposób na mniej pytań. Jeśli się nie zgadzasz — wpisz zdanie w TERAZ → „Zdanie Architekta i Codexa”.

## 4. JAKIE POMIARY SĄ WIARYGODNE, A JAKICH NIE WOLNO UŻYWAĆ

**NOWY, POWTARZALNY POMIAR (CC 19.10, `BOARD.md` wiersz `LYNX-OCR-PARITY`):** `backend/benchmark.py`, zbiór `backend/dataset_20260627_095419`, **50 syntetycznych obrazów** z gold generatora, silnik main `cfe8eb7`. Wynik: **0 z 107 identyfikatorów krytycznych pozostawionych jawnie według miary benchmarku; recall 94,5% (274/290 wystąpień); 16 pominiętych**. CC sklasyfikował 16 przypadków, porównując gold z tekstem rozpoznanym przez OCR (analogicznie do Mobile): **0 BUG_SILNIKA, 10 OCR_ZNIEKSZTAŁCONY** (7 EMAIL, 2 TELEFON, 1 NUMER), **6 BRAK_W_OCR**. Mechanizm był powtórzony na starym silniku `28cff45` i porównany z raportem 27.06, co potwierdza powtarzalność tej miarki; wynik nie oznacza niezależnego audytu całego produktu.

**Granice tego dowodu:** obejmuje konkretny zbiór obrazów, konkretne kategorie i metodę klasyfikacji, NIE wszystkie typy dokumentów, nie 100% bezpieczeństwa danych klientów ani pełną poprawność Przywróć/Guarda. Wnioski „silnik działa na czystym tekście; aktualne mierzone straty to OCR” dotyczą tego pomiaru oraz obserwacji testów Mobile na czystym tekście. Trzeba je dalej falsyfikować na reprezentatywnych dokumentach, zawsze rozróżniając: wartość nieobecna w OCR, zniekształcona przez OCR, wartość prawidłowa w OCR lecz przeoczona przez silnik. Nie przypisuj automatycznie każdego nowego wycieku OCR.

**STARY POMIAR `LYNX-REAL-DOCS-BENCHMARK` ZOSTAŁ ZAKWESTIONOWANY I WYCOFANY JAKO PODSTAWA DECYZJI.** Błędy wzorca/gold CC obejmowały m.in. traktowanie urzędowych sygnatur jako wycieków NUMER, miasta poza częściowo zamaskowanym adresem jako nieudanego ADRES oraz instytucji jako FIRMA. Jego dawne procenty skuteczności typów i miary blokad/Przywróć **NIE SĄ WIARYGODNYM BASELINE'EM**. Zostały **celowo usunięte z tego handoffu**; historyczny raport pozostaje w git jako materiał do audytu narzędzia, nie do oceniania produktu:
https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/task/LYNX-PUBLIC-REAL-DOCS/tasks/LYNX-PUBLIC-REAL-DOCS/REPORT.md.

**Co ma sprawdzić następca:** (1) porównanie oryginał→OCR i OCR→maskowany wynik, nie tylko gold→final; (2) poprawne źródło mianownika, warunki wykluczeń i uzasadnione FP; (3) odrębnie recall maskowania, OCR fidelity, Guard i Przywróć; (4) test regresji na identycznej, zamrożonej próbce, a dla zmian produktu /preview przez cały obieg. Zgoda na plan z `LYNX-PATH-CLEAN-DOCS` nie jest automatyczną zgodą na jego progi, ponieważ został sporządzony przed korektą miarki.

**Komenda odtworzenia (według CC):** przy backendzie na localhost:8765: `cd backend && py -3 benchmark.py --dataset dataset_20260627_095419 --no-generate`. Dane i próbki lokalne; nie commituj literalnych danych użytkownika, OCR z prawdziwych dokumentów ani profili do repo.

## 5. BEZPIECZEŃSTWO / PRODUCT_TRUTH

arch/spec.md jest FROZEN; weryfikuj arch/FROZEN.lock. S1: lokalna pseudonimizacja polskich dokumentów, mapa wyłącznie lokalna i szyfrowana. S2: KATEGORIA_NNN, TOKEN_RE z (?!\d), taksonomia, .lynxdict wspólne z Mobile — decyzje OWNERA. S3: awaria NER/pipeline/OutputGuard → fail-closed, token injection blokowane. S5: dane osobowe nie mogą znaleźć się w logach/nieszyfrowanych mapach; S6: lokalne API port 8765, polski UI „Zamaskuj/Przywróć”.

**KONFLIKT S4:** zamrożony spec aktualnie nakazuje Guard HIGH → **blokadę wyniku**. OWNER wyjaśnił intencję: Guard miał **ostrzegać** i umożliwiać człowiekowi poprawkę/domaskowanie, nie zastępować silnika i nie odbierać całego dokumentu (jak Mobile). CC zgłosił propozycję zmiany BOARD LYNX-SPEC-S4-GUARD-WARN. **Intencja nie zastępuje zamrożonego S4.** Zanim zmienisz API/UI: jasne rozstrzygnięcie OWNERA, osobny Task/spec i guard.py freeze --recompute, test bezpieczeństwa kopiowania do AI. Nie zakładaj, że każda flaga Guarda jest dowodem PII, ale nie osłabiaj S3.

Security review Codexa: F1–F3 (jawny trie profilu, reset nieusuwający całości, ścieżki/logi) wymaga osobnych zadań przed wydaniem; zob. BOARD LYNX-SECURITY-REVIEW. Uważaj na PDF copy/metadata, szyfrowanie archiwum i uruchamianie frontend + backend; nie dodawaj tego do K1.

## 6. PROCEDURA ARCHITEKTA

1. Odczytaj aktualny BOARD.md **TERAZ** i tylko odpowiedni wiersz + źródłowy raport/brief. Dopiero potem punktowy kod i exact SHA. PROJEKT_KONTEKST.md to migawka techniczna z **27.06.2026**, nie aktualne benchmarki października.
2. Skrytykuj propozycję, poszukaj najmniejszego falsyfikującego eksperymentu na kodzie, ustal co jest obserwacją, a co hipotezą. Przy materialnej zmianie zachowania zapytaj OWNERA raz, prostym językiem z rekomendacją.
3. Wskaż istniejącego ownera (layers/*, ner_layer, ner_adapter, TokenAllocator, output_guard, API, UI); używaj where.py celowo, nie czytaj repo w całości. Preferuj istniejącą logikę bez równoległej walidacji/nowego stanu.
4. Brief na gałęzi task/<id>: PRODUCT_TRUTH i decyzje; cel/wejście/wyjście; minimalny owner i szew; literalny TASK_SCOPE: z listą "- relative/path"; OUT_OF_SCOPE; kontrpróby; odbiór przez test jednostkowy ORAZ E2E gdy dotyczy; GATE i ewentualny WHERE_MAP. Nie wdrażaj nowego zachowania produktu bez zgody.
5. Codex BRIEF_ONLY → CC merytoryczny review → CC kod + gate.py → Codex audyt exact SHA → OWNER wydaje merge. Raport Codexa nowy, nie nadpisywany: tasks/<id>/round_01/tests/tests_r<n>.txt. BOARD na main: branch, SHA, odbiorca, status, krótki link. Zapis w samym czacie nie przekazuje pracy.
6. **Minimalny budżet**: max 2 nowe pliki, plik ≤600 l., funkcja ≤50 l., >150 nowych/zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI przed implementacją; istniejący plik nie powinien rosnąć w dług architektury. Zgoda na rozmiar jednego Tasku nie dotyczy automatycznie drugiego.
7. Lokalnie Windows: cd backend && py -3 ...; celowane pytest: py -3 -m pytest tests/<plik> -q. Python przez samo python może odpalać Microsoft Store. Pominięcie 38 testów integracyjnych bez serwera nie oznacza PASS E2E. Uruchomienie backendu: py -3 pseudominizer_api.py, lokalny port 8765.
8. Nie rób merge bez explicit OWNER; nie zapisuj PII, nie force-push, nie rozszerzaj diffu pod pozorem „dobrych praktyk”. Weryfikuj SHA zarówno kodu, jak i raportów/źródeł. Rozróżniaj CODEX PASS techniczny i OWNER ACCEPTED.

## 7. START PO OTWARCIU NOWEGO OKNA

**Pierwsza praca (aktualizacja 20.10):** przeczytaj `BOARD.md` → TERAZ i bieżące wiersze PHOTO-CHAIN / OSOBA-REDESIGN; przeglądnij wskazany wyżej nowy handoff z testem 68 przypadków. Poprzednie zadania OCR-PARITY krok 1 i GATE-COMPARE są historyczne, nie pisać ich briefów ponownie. Wszelkie nowe decyzje wymagają aktualnego kontekstu, nie tej migawki.

**Nie odziedzicz bezkrytycznie moich hipotez.** Pytanie nie brzmi „jak napisać piękny silnik?”, tylko „jaki minimalny zabieg daje mierzalnie lepszą ochronę i Przywróć na dokumentach użytkownika?”. Jeżeli OWNER zmieni priorytet — reaguj na aktualne polecenie, nie na tę migawkę.
