# LYNX-ARENA-SIGNALS-PILOT — pierwszy pomiar z prawdziwych detektorów

STATUS: BRIEF_ONLY. Architekt → Codex PRECHECK → CC ocena i implementacja → Codex audyt exact SHA. Zadanie eksperymentalne, bez merge i bez zmian produktu.
BRANCH: task/LYNX-ARENA-SIGNALS-PILOT (baza: experiment/lynx-architecture-arena-v02, R1 i R2 NIEZMIENIONE).
MOTYW: Codex r2 dla Areny v0.2 wskazał, że projektowanie R2b bez znajomości realnych błędów detekcji przenosi problem granic do kolejnego silnika. OWNER chce uruchamiać i falsyfikować nawet niedojrzałe pomysły, nie pisać kolejnej teoretycznej architektury.
PRODUCT_TRUTH/GRANICE: arch/spec.md S1–S5; ARCHITECT_START_HERE.md; AGENTS.md; tasks/LYNX-ARCH-ARENA-V02/round_01/tests/tests_r2.txt; LYNX-ARCH-ARENA/architect_review_r1.md. Żadna hipoteza Areny nie jest zatwierdzeniem nowego pipeline.

## Cel jednej próby
Sprawdzić na 10–12 krótkich **syntetycznych czystych tekstach** (BEZ OCR), jakie **rzeczywiste spany** przekazują dziś 4 istniejące detektory: layers.identity, layers.contact, layers.address oraz spacy_ner.detect_entities (OSOBA/FIRMA). Te same, niezmienne kandydatury zasilić w pamięci obie zamrożone Areny: R1=strict i R2=structured. Odróżnić błąd detekcji od decyzji arbitra. Nie proponować R3/R4/R2b w tym Tasku.

## Realny szew (zweryfikowany w kodzie main)
- identity/contact/address mają apply_*_layer(state: PipelineState). Każdą warstwę uruchom OSOBNO na nowym PipelineState z ORYGINALNYM str i świeżym TokenAllocator; bez normalizera, pipeline_new, API, profilu, Guard lub wzajemnej kolejności warstw.
- TokenAllocator.allocate(type, value, start, end) otrzymuje offsety przed podmianą przez te warstwy. W pilocie można zastosować wyłącznie **lokalny obiekt instrumentujący/subklasę alokatora**, zapisujący udane przydziały [start,end), kind i source. Nie przenosić kodu warstw ani nie rekonstruować spanu przez wyszukiwanie wartości/tokenów w już zmienionym tekście.
- Spacy: użyj bezpośrednio spacy_ner.detect_entities(original), które zwraca start/end/label. To NIE pełna logika layers.ner_adapter z propagacją i poprawianiem OCR; jawnie nazywaj źródło SPAСY_DIRECT (ASCII w kodzie: SPACY_DIRECT). Jeżeli model pl_core_news_lg jest niedostępny albo detektor rzuci wyjątek: jawny MODEL_UNAVAILABLE/DETECTOR_ERROR, żadnego „zero trafień = PASS”.
- Dla każdego źródła waliduj 0 <= start < end <= len(original), typ z taksonomii i raw literal = original[start:end]. Jeśli warstwa zmieniła fragment POZA tokenizowanymi spanami, zwróciła przesunięte współrzędne, użyła innego mechanizmu bez pochodzenia albo nie da się potwierdzić offsetu: ADAPTER_UNSUPPORTED / MAPPING_ERROR dla źródła/próby, nie NO_CANDIDATE. Niczego nie „naprawiaj” difflibem ani zgadywaniem.
- Zapis candidate dla Areny: start, end, kind, source, evidence=["OBSERVED_DETECTOR"]; ten rodzaj dowodu to tylko informacja o pochodzeniu, NIE potwierdzenie semantyki. Kolejność i lista źródeł deterministyczna. Utrzymaj identyczną listę wejściową do R1/R2.

## Sędzia i dane
- Stwórz 10–12 własnych krótkich syntetyków we współdzielonym teście (minimum: pełny/ucięty e-mail, PESEL, firma z nazwiskiem, adres z nazwiskiem, nazwiska w wyliczeniu, powtórzenia wartości, Unicode/NFD, H1 fałszywie szeroka firma z prozą i druga rzeczywista firma, tekst bez PII). Ustal niezależny gold [start,end,kind] przy SKŁADANIU tekstu z bloków, NIE przez późniejszy .find(value) na całym dokumencie; odnotuj zagnieżdżenie OSOBA wewnątrz FIRMA/ADRES i nie licz go automatycznie jako FP przy zakryciu całego poprawnego zewnętrznego zakresu. Nie zapisuj fikcyjnych wykryć jako rzeczywistych.
- Nie modyfikuj generator.py: jego obecny ground_truth.json jest oparty o wartości, a firmy nie zawsze są kompletne w gold. Osobne poszerzenie generatora z offsetami dopiero po wynikach tego pilota. Codex dokłada co najmniej 3 NOWE dokumenty poza fixture CC.
- Dla każdego gold raportuj oddzielnie NO_CANDIDATE, BAD_SPAN, WRONG_KIND, EXACT_CANDIDATE oraz (tylko gdy exact istniał) ARBITER_STOP/ARBITER_DISCARDED; można mieć kilka obserwacji dla jednego tekstu, NIE redukuj wszystkiego do jednego FAIL. Dla RENDERED osobno FN, FP/OVERMASK, N1–N4/roundtrip. STOP liczyć jako STOP, nigdy jako udane maskowanie. Mierz liczbę konfliktów i czas na źródło oraz na wariant. Osobno przypadki ADAPTER_UNSUPPORTED, MAPPING_ERROR, MODEL_UNAVAILABLE — nie uwzględniaj ich w mianowniku recall dla brakującego detektora.
- Raport do repo: tylko agregaty, nazwy klas i identyfikatory syntetyków. **Żadnych surowych danych klientów, literalnych wykryć ani źródłowych spanów dokumentów rzeczywistych** w stdout, trace, logach, wynikach w repo; wyniki szczegółowe na syntetykach mogą być w lokalnym teście. Nie uruchamiaj na 178 dokumentach w tej fazie.
- Porównanie jest **testem czystego tekstu**. Utrata danych w OCR, projekcja offsetów OCR oraz wydajność po OCR to odrębny późniejszy tor; nie nazywać ich błędami detekcji bez kontroli.

## Minimalny interfejs i kryteria odbioru
- Read-only moduł offline, wejście w testach jako synthetic text + niezależny gold; wyjście techniczne jako spany i statusy źródeł. Wykonanie R1/R2 w tym samym procesie, bez sieci i bez logowania tekstu. Brak produkcyjnego endpointu/trybu ENGINE.
- Najmniejszy reproduktor: jeden tekst z PESEL + e-mail → rzeczywiste trafienia identity/contact wraz z pozycjami; tekst z osobą i firmą → wywołanie realnego SpaCy (albo jawny błąd modelu); konflikt OSOBA⊂FIRMA → ten sam candidate set dla strict i structured; przypadek fałszywego zakresu H1 pozostaje falsyfikacją R2.
- Testy weryfikują zarówno 1:1 offsety, jak i to, że nieprawidłowy adapter NIE emituje poprawnie wyglądających spadków recall. R1/R2, ich kod i dotychczasowy gold pozostają byte-for-byte niezmienione.
- Wynik DELIVERY: dokładny SHA, polecenia, testy, status dostępności SpaCy, tabela liczników i 2–3 największe *zaobserwowane* źródła strat, bez nowej architektury.

TASK_SCOPE:
- backend/arena_signal_probe.py
- backend/tests/test_arena_signal_probe.py

OUT_OF_SCOPE: generator.py, arch/spec.md, backend/arena_sim.py, backend/arena_v02.py, istniejące backend/layers/* i spacy_ner.py, pipeline_new.py, TokenAllocator produkcyjny, profil/trie, HerBERT, OCR, API/UI, .lynxdict, realny dataset, nowy arbiter/score, produkcyjny Guard, merge. Nie tworzyć trzeciego pliku bez osobnej decyzji.
GATE: max 2 nowe pliki, <=600 l./plik i <=50 l./funkcję; próg >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI OWNERA przed implementacją. CC ma oszacować i zwrócić STOP do decyzji, jeśli nie mieści się w progu; nie opierać się na starej zgodzie dla v0.1/v0.2.
PRECHECK CODEX BRIEF_ONLY: czy 4 źródła da się rzeczywiście odczytać bez zmiany pipeline; czy intercept allocate i bezpośrednie SpaCy udowadniają original offsets; czy gold pełny i niezależny; czy dwa pliki są minimalne. Jeśli część warstwy nie wspiera takiego podsłuchu, zgłosić dokładnie nieobsługiwaną ścieżkę i odciąć ją jako osobny etap, NIE pisać nowego adaptera produkcyjnego. Precheck tylko kontrakt; po pracy CC audyt exact SHA i nieznane wcześniej syntetyki Codexa. Raport tests_r1.txt w tasks/LYNX-ARENA-SIGNALS-PILOT/round_01/tests/. Bez merge bez polecenia OWNERA.
