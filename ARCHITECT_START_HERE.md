# ARCHITECT_START_HERE — handoff dla następnej instancji Architekta

LynxMask Desktop, 19.10.2026 (aktualizacja po korekcie benchmarku CC). Ten dokument to **migawka operacyjna, NIE PRODUCT_TRUTH**. Repo: paweltpietraszko-ship-it/LynxMask-Desktop. Przed podjęciem zadania odśwież origin/main, nagłówek i sekcję TERAZ w BOARD.md oraz WŁAŚCIWY wiersz. Nie zakładaj, że wskazany tutaj SHA nadal jest HEAD.

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

## 3. AKTUALNA KOLEJNOŚĆ — TRZY BRIEFY (uzgodnione z OWNEREM 19.10, BOARD TERAZ `e1a4a22`)

Briefy w tej kolejności; 2 i 3 mogą powstawać równolegle po 1. Szczegóły, ścieżki kodu Mobile i dowody: BOARD.md sekcja TERAZ oraz wiersze `LYNX-OCR-PARITY` i `LYNX-K1-PERSONS-FIRMS`.

1. **`LYNX-OCR-PARITY` krok 1 — benchmark mówi „silnik czy OCR”.** Do `backend/benchmark.py` klasyfikacja przegapień jak Mobile (`BenchmarkInstrumentedTest.kt`): BUG_SILNIKA / OCR_ZNIEKSZTAŁCONY / BRAK_W_OCR oraz klasy tokenów spoza gold. Tylko narzędzie. To miarka dla 2 i 3 i strażnik regresji po każdej zmianie. Mały.
2. **`LYNX-OCR-PARITY` krok 2 — e-mail na skanie.** Port reguł e-mail z Mobile `OcrNormalizer.kt` (`OCR_EMAIL_AT_Q`, spacje). Jedyny zmierzony powtarzalny wyciek: 8/8 e-maili na skanach jawnych (OCR czyta „@” jako „Q”, także bez spacji przed Q). Decyzja w briefie: poprawka w miejscu czy widok wyszukiwania z mapą offsetów (`LYNX-SHADOW-NORMALIZE`; CC rekomenduje widok — tekst użytkownika bez zmian). Mały.
3. **`LYNX-K1-PERSONS-FIRMS` K1a — HerBERT jako siatka na resztki.** OWNER 19.10 (po `edb7100`): HerBERT to dodatkowe zabezpieczenie, w testach pomagał i nie szkodził; sztuka to miejsce, w którym nie przeszkadza. Wariant: ostatni krok `run_pipeline_new` (po fallback, przed Guardem), tylko na fragmentach wciąż jawnych, te same filtry co NER + potwierdzenie jednowyrazowej OSOBY słownikiem; niczego zakrytego nie zmienia; efekt = lista dołożonych tokenów do oceny okiem OWNERA. Decyzje w briefie: budżet czasu (diagnoza: ~40 s przy 63 tys. znaków), ORG→instytucje, brak modelu (S3) i uznanie autorstwa (CC BY 4.0). **Zgoda OWNERA na rozmiar ~350 l. udzielona** (dotyczy rozmiaru, nie zastępuje briefu). [Propozycja](https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/d6acbb4/tasks/LYNX-K1-PERSONS-FIRMS/cc_proposal.md). Uwagi Codexa SIGNALS-PILOT r2 do skryptów pomiaru HerBERT poprawione; inferencja nadal do niezależnego sprawdzenia przy audycie.

**Na później, tylko po dowodach:** reguły OCR dla telefonów/numerów (wg klasyfikacji z kroku 1); K1b słownik nazwisk i K1c — tylko jeśli OWNER zobaczy okiem przecieki osób/firm (lekcja Mobile: duży słownik bez progu częstości dał lawinę FP); Guard ostrzega zamiast blokować (`LYNX-SPEC-S4-GUARD-WARN`, decyzja OWNERA).

**Pozostałe wątki** (Przywróć, FIRMA-BARE-REPEAT, NO-CANDIDATE, pliki PDF i UI) to backlog/FINDINGi. Nie utożsamiaj ich historycznych statystyk z oceną dzisiejszego silnika i nie otwieraj automatycznie. `LYNX-POLIGON` i F0a odłożone.

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

**Pierwsza praca:** odśwież `BOARD.md` (sekcja TERAZ) i wiersz `LYNX-OCR-PARITY`; odtwórz benchmark (`cd backend && py -3 benchmark.py --dataset dataset_20260627_095419 --no-generate`, oczekiwane 274/290, 0/107 kryt.) i przygotuj **brief 1** (klasyfikacja silnik/OCR w benchmarku). Następnie briefy 2 (e-mail OCR) i 3 (HerBERT jako siatka na resztki) — mogą iść równolegle. Kryterium odbioru każdej zmiany silnika umów z OWNEREM prostym językiem; strażnik regresji po każdej zmianie. Ewentualne poprawki mapy/Przywróć i UI mają osobne zadania i własne źródła prawdy.

**Nie odziedzicz bezkrytycznie moich hipotez.** Pytanie nie brzmi „jak napisać piękny silnik?”, tylko „jaki minimalny zabieg daje mierzalnie lepszą ochronę i Przywróć na dokumentach użytkownika?”. Jeżeli OWNER zmieni priorytet — reaguj na aktualne polecenie, nie na tę migawkę.
