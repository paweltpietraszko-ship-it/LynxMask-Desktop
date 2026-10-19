# ARCHITECT_START_HERE — handoff dla następnej instancji Architekta

LynxMask Desktop, 19.10.2026. Ten dokument to **migawka operacyjna, NIE PRODUCT_TRUTH**. Repo: paweltpietraszko-ship-it/LynxMask-Desktop. Przed podjęciem zadania odśwież origin/main, nagłówek i sekcję TERAZ w BOARD.md oraz WŁAŚCIWY wiersz. Nie zakładaj, że wskazany tutaj SHA nadal jest HEAD.

## 1. NAJWAŻNIEJSZA ZMIANA KIERUNKU

**OWNER 19.10: odstawiamy Arenę na boczny tor.** Eksperymenty kandydat/arbiter/one-apply nie wykazały przekonującej przewagi jakościowej nad obecnym programem. Nie wracaj teraz do R2b/R3/R4, hybrydy, przepisywania pipeline ani F0a LYNX-ARCH-CANDIDATES. Historię gałęzi experiment/lynx-architecture-arena, experiment/lynx-architecture-arena-v02 i task/LYNX-ARENA-SIGNALS-PILOT zachowujemy jako przyrząd badawczy i dowód, nie plan wdrożenia. Szczegóły: ODLOZONE.md i git log -p BOARD.md. To **decyzja priorytetowa**, nie naukowy dowód braku wad kolejności warstw.

**Kierunek na teraz: doskonalenie działającego LynxMask, szczególnie rozpoznawania OSOBA/FIRMA i mapy Przywróć.** Cel produktu jest samodzielny: lokalnie zamaskować dokument i dać człowiekowi możliwość bezpiecznego użycia AI. Integracja z Elnath Rota odłożona.

**Lekcja Areny:** najpierw mały eksperyment uruchomiony na prawdziwym kodzie i uczciwy wynik, dopiero architektura. Poprzedni Architekt dwa razy zaprojektował nieskuteczną regułę arbitra: globalne STOP było nadmiernie konserwatywne, a R2 ze sprawdzaniem samego sufiksu firmy łączyło dwie encje i prozę (Codex H1). Unikaj dopieszczania hipotez na papierze; używaj niezależnego gold i jawnego kryterium porzucenia. Nie maskuj kosztów FN przez ogólne STOP ani nie licz samego roundtrip jako semantycznej poprawności.

## 2. ROLE I ZASADY WSPÓŁPRACY

- OWNER (Paweł): zna użytkowanie, przedstawia cele; rozstrzyga decyzje produktowe po ocenie modeli, autoryzuje merge. Zwykłe wypowiedzi techniczne/produktowe to OWNER_PROPOSAL, nie automatyczne decyzje. Polecenia operacyjne wykonywać literalnie. Szczegóły AGENTS.md, OWNER_INPUT_IS_A_PROPOSAL.
- ChatGPT — Architekt / kontroler: zewnętrzny koordynator, falsyfikator i recenzent; domyślnie **nie implementuje**. Dobiera istniejącego ownera kodu, pisze minimalny kontrakt, nadzoruje spójność i status. Nie zamienia PASS Codexa w decyzję produktu.
- Claude Code (CC): implementer i merytoryczny recenzent briefu. Może odesłać brief mimo PASS prechecku. Implementuje dokładny TASK_SCOPE; jeśli wykryje błąd TEJ SAMEJ KLASY w szwie, przed kodem wpisuje ROZSZERZENIE CC i poszerza TASK_SCOPE. Inne tematy zgłasza, nie naprawia przy okazji.
- Codex: niezależny audytor testujący exact SHA; ma lokalny backend i zbiory. W prechecku BRIEF_ONLY **nie uruchamia kodu**; w audycie implementacji robi najmniejszy reproduktor i testy zmienionego ownera. Nie czyta całego repo ani nie ponawia 178 dokumentów, modeli i pełnych suit bez konkretnego powodu. Czytaj CODEX_START_HERE.md oraz CODEX_HANDOFF.md.
- Właściciel ma zatwierdzać realne zachowanie dla człowieka; nie zasypuj go nazwami funkcji. Wyjaśnij po polsku: kiedy, co zobaczy, co stanie się z danymi, co przy błędzie i jak wróci do pracy.

**Workflow:** OWNER/zgłoszenie → Architekt: minimalny brief i zakres → Codex BRIEF_ONLY → CC recenzja → CC implementacja i gate.py → Codex independent exact-SHA audit → OWNER akceptuje zachowanie/merge. Codex PASS ≠ zgoda OWNERA. Żaden merge bez jawnego polecenia. Aktualizacje i raporty muszą znaleźć się w GitHub, nie tylko w czacie.

## 3. NAJWAŻNIEJSZY AKTYWNY TEMAT — K1 OSOBY/FIRMY

BOARD TERAZ wskazuje LYNX-K1-PERSONS-FIRMS; gotowa **propozycja** CC (nie brief): https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/task/LYNX-K1-PERSONS-FIRMS/tasks/LYNX-K1-PERSONS-FIRMS/cc_proposal.md — commit 9e99b87b2d961b49fad5e6c066f645f75abd1f2e. Źródło: arch/DIAGNOZA_2026-10-18.md na task/LYNX-DIAGNOZA-2026-10-18, tekst zaakceptowany przez Codexa na SHA 4f6c38064f86e5aa93015f2abddef7527c811993; audyt: https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/9c4db4ef78b24a842077aff61ff0de9dbe231be7/tasks/LYNX-DIAGNOZA-2026-10-18/codex_review_r2.md.

**K1a (do rozstrzygnięcia i krótkiego briefu):** test/integracja HerBERT legal-NER jako drugiego źródła kandydatów obok SpaCy. CC proponuje szew ner_layer._process_ner, osobny minimalny backend/herbert_ner.py, istniejące filtry i fail-closed S3. OWNER zgodził się **tylko na większy rozmiar K1a**, nie na całą logikę. Przed briefem oceń: połączenie dwóch źródeł bez połykania list osób i FP na słowach/instytucjach; pokrycie CAŁEGO dokumentu przy limitach 512 tokenów; czas CPU na długim dokumencie i słabszym komputerze; brak modelu = jawna awaria; zgodność licencji/atrybucja (CC podaje CC BY 4.0, zweryfikuj przy dystrybucji). Stary probe HerBERT miał błąd: „both_source” ukrywa DETECTOR_ERROR i długa pojedyncza linia bywała obcięta; Codex udokumentował to w SIGNALS-PILOT r2. Nie nazywaj pilota potwierdzeniem zysku HerBERT, inferencja HerBERT była NOT_CHECKED przez Codexa.

**K1b później, osobno:** słownik nazwisk z Mobile; historia: surowe 39 tys. podniosło FP, późniejsze ograniczenia częstotliwości i kontekst poprawiły jakość. Nie importuj całego słownika bez filtra, kontekstu i pomiaru.
**K1c osobno:** „z o.o.” bez rdzenia firmy, A4, smoke test zasobów i martwy seed. Możliwe wąskie niezależne prace; nie rozlewaj K1a o te tematy.

**Inne otwarte wejścia** tylko na życzenie OWNERA / po priorytetyzacji BOARD: LYNX-FIRMA-BARE-REPEAT (Codex C1: „goła→goła” bez pełnej nazwy to kontrola regresji, nie obowiązek maskowania), FIRMA-NO-CANDIDATE, K1-INPUTS-MULTILINE, K2-INPUTS-ULTRAREVIEW (literalna wartość mapy), ADRES-POSTAL, NUMER-SIGNATURES, SHADOW-NORMALIZE/TEXT-FIDELITY, comb PDF, GUI/launcher, API-SIZE oraz bezpieczeństwo wydania. Zmiana wg obszaru zachowania; minimalny diff, regresja całego obszaru i E2E zamiast 12 mikrotasków bez wspólnego sprawdzianu.

## 4. DOWODY PRODUKTOWE — NIE MYL Z ZIELONYMI TESTAMI

Pomiar przez działający /preview: https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/task/LYNX-PUBLIC-REAL-DOCS/tasks/LYNX-PUBLIC-REAL-DOCS/REPORT.md (17.10, pomiar 3, historyczny main 2046805).
- 93 kwalifikowane dokumenty robocze, 38 kontrolnych; gold CC dla 72 dokumentów/601 pól (w części KIO słabszy; **nie niezależny**).
- Full: OSOBA 72%, FIRMA 29%, ADRES 44%, NUMER 39% pełnych zamaskowanych **wystąpień**; Guard 17/93 dokumentów zablokowanych; dokładne Przywróć 27/76 niezablokowanych.
- Część wcześniejszych próbek anonimizowanych już u źródła unieważnia starszą tabelę 23/50 blokad. **Nie cytuj jako aktualnego baseline'u; nie myl z pomiarem 3**. Miary są z konkretnego starego SHA, wymagają refresh dla nowego odbioru.
- Test funkcji nie wystarcza: dla zmian semantyki sprawdzaj typowy dokument przez działający backend /preview → Guard → maskowany tekst → mapę/Przywróć. Baza main i branch na tych samych wejściach; DEV do poprawek, HOLDOUT dopiero do odbioru, gold negatywny również, żeby nie wygrywać przez maskowanie wszystkiego.
- Generator backend/generator.py v1.2 daje wartości, lecz nie zawsze kompletne firmy ani gold offsety; nie jest automatycznym sędzią. Przy nowych syntetykach ustalaj dokładne spany w trakcie budowy; nie zgaduj przez szukanie powtarzającej się wartości. Czytaj czysty tekst lvl0/1 oddzielnie od degradacji OCR lvl2/3.
- Dwa rodzaje strat: **wyciek / niepełny span** i **zła wartość Przywróć / dopisany obcy tekst**. Odmieniona postać wartości nie jest automatycznie tym samym co dopisanie cudzej osoby. Pomiar per wystąpienie, per dokument i status Guard podawaj osobno.
- Bez surowych danych klientów w repo, raportach, diffach, logs czy skrótach. Repo zawiera kod i zagregowane wyniki; lokalne profile, mapy i prywatne dokumenty są poza repo. Jawny dokument z rejestru także nie daje dowolności obchodzenia tej zasady.

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

**Pierwsza praca:** odśwież BOARD TERAZ, przeczytaj cc_proposal K1 i diagnozę r2, zrób mały preimplementacyjny plan K1a (HerBERT + SpaCy) sprawdzający rzeczywisty zysk vs baseline, FP, awarie i czas. Nie uruchamiaj implementacji, dopóki nie ma uzgodnionego zakresu oraz krótkiego briefu po prechecku Codexa. Rozważ równolegle wyłącznie mechaniczny, mały Task K1c po oddzielnym zleceniu; K1b dopiero po pomiarach K1a.

**Nie odziedzicz bezkrytycznie moich hipotez.** Pytanie nie brzmi „jak napisać piękny silnik?”, tylko „jaki minimalny zabieg daje mierzalnie lepszą ochronę i Przywróć na dokumentach użytkownika?”. Jeżeli OWNER zmieni priorytet — reaguj na aktualne polecenie, nie na tę migawkę.
