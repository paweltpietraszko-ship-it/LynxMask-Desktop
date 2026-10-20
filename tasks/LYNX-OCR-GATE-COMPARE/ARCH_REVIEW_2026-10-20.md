# Recenzja Architekta — LYNX-OCR-GATE-COMPARE v2 (20.10.2026)

ADRESAT: Claude Code (autor briefu), potem Codex BRIEF_ONLY.
ODCZYT: `tasks/LYNX-OCR-GATE-COMPARE/brief.md` z gałęzi `task/LYNX-OCR-GATE-COMPARE` (v2 `637f203`), `BOARD.md → TERAZ`, `arch/spec.md` S1/S2/S3/S5, obecny szew `pseudominizer_api.py::preview`.

WERDYKT: **KIERUNEK AKCEPTUJĘ, BRIEF JESZCZE WYMAGA CZTERECH DOPRECYZOWAŃ PRZED CODEXEM.** Nie wracamy do kaskady dwóch OCR ani do arbitralnego progu pewności. Doceniam zmianę celu: mierzymy końcowy łańcuch, nie atrakcyjny procent samego OCR. Nie piszę konkurencyjnego briefu. Proszę poprawić Twój i skierować do Codexa, gdy kontrakt będzie zamknięty.

## C1 — Nieporównywalne „czysty tekst vs zdjęcie”

`dataset_clean` Mobile zawiera **inne dokumenty** niż 50+100 obrazów; nie odtwarzamy czystego tekstu dokładnie tych samych dokumentów. Wynik „0 dziur / ~4 pytania” jest **zewnętrznym punktem orientacyjnym**, nie sparowanym oracle, a zatem kryterium `mediana pytań ≤2 × czysty tekst` na innym korpusie nie dowodzi zbliżonego zachowania na zdjęciach. Niech odbiór dzieli: (a) zdjęcia 50+100, w tym L0, liczone po dokumentach/poziomach; (b) osobny `dataset_clean` bez bezpośredniej relacji procentowej. Zamiast „to samo co na czystym tekście”, wynik może brzmieć „wynik zdjęć w akceptowalnym zakresie według wcześniej zapisanych kryteriów” — nie ogłaszać parytetu bez sparowanych dokumentów.

## C2 — Symulowane Guard i HerBERT ≠ działający bezpieczny produkt

`Guard-reszta` i HerBERT nie są zaimplementowaną częścią ścieżki wydawania wyniku przez `/preview`. Zliczenia po hipotetycznym zadaniu pytania nie dowodzą, że użytkownik **zobaczy** to pytanie ani że wyjście jest **zablokowane do jego decyzji**. `blocked` dzisiejszego Output Guarda oraz hipotetyczne `would_ask` raportuj osobno. Jeżeli bieżące `/preview` ma `guard_blocked=true`, nie traktuj jego podglądu jako wyniku dopuszczonego do skopiowania ani jako potwierdzenia maskowania. Model HerBERT działający **po** `/preview` może „zakryć” tekst w symulacji, ale nie dodaje tokenu do zaszyfrowanej mapy `token → original` (S1/S2). To może mierzyć **potencjał odzysku recall**, nie gotowość produktu ani działającą depseudonimizację. Raport koniecznie rozdziela **REAL_PIPELINE** i **HYPOTHETICAL_GUARD/HERBERT**, a kryterium zakończenia ma dawać `READY_FOR_PRODUCT_BRIEF` (gotowość do napisania briefu implementacji), **nie** „bezpieczny / gotowy do wydania”.

Metryka `≥4` znaków fragmentu gold jest użyteczna, ale dla OCR który zmienił wszystkie kluczowe znaki lub porozdzielał cyfry fragmentami nie wykryje wszystkich niebezpiecznych pozostałości. Takie przypadki mają jawny `UNKNOWN/REVIEW` (odrębny od `NO_GAP`), z testem na uszkodzonym NIP, IBAN i telefonie w grupach, bez arbitralnego zaliczania do sukcesów. Wskazać, kto ogląda te przypadki przed werdyktem.

## C3 — `/preview` modyfikuje stan; wymagane odizolowanie pomiaru

W bieżącym `pseudominizer_api.py::preview` każde wywołanie `_next_pse()` zwiększa licznik w `pse_registry.json`, a `record_preview()` rejestruje przebieg. Praca na istniejącym, działającym backendzie/profile OWNERA z `.txt` byłaby ingerencją w jego stan i zakłóciłaby porównanie wariantów, potencjalnie również przez stan słowników i tokenów. Kontrakt musi wymagać **osobnego procesu/izolowanego testowego środowiska** z tym samym exact SHA, pustym albo sklonowanym *testowym* stanem oraz oddzielnymi ścieżkami profilu, PSE, bazy, logów i archiwum. Dla każdego wariantu odtwarzamy identyczny stan początkowy. Nie podłączać się do produkcyjnego backendu na 8765. Jeżeli pełnej izolacji nie uda się wykazać → `NOT_RUN`, nie „PASS”. Nie wprowadzać do scope refaktoru API, jeżeli wystarczą konfiguracja/test harness; ograniczenie opisać przed kodem.

## C4 — Kryterium N i „0 dziur” może nagradzać odrzucanie dokumentów

Próg pytań `N` wybierany z 15/20/30/40 „na znanym zbiorze” nie ma jawnej **funkcji wyboru**, więc wynik będzie zależał od implementera. Ustal przed implementacją: jak traktować `guard_blocked`, `UNKNOWN`, błędy i odmowy; jak wybrać N deterministycznie tylko z 50 znanych; co zrobić, jeśli żadna reguła nie przechodzi. Odbiór zawsze raportuje pełny mianownik 50/100, zaakceptowane/odrzucone i gold obecne/nieobecne w OCR, a `0 dziur` nie może być osiągnięte po prostu odrzuceniem większości danych. `L0=0 odmów` jest konieczne, ale nie wystarcza dla pozostałych poziomów. Kryteria jakości muszą odróżniać bezpieczeństwo wyniku dostępnego człowiekowi od kompletności i uciążliwości systemu.

## Uwagi niefatalne (do decyzji CC, bez nowej architektury)

- P1: obrót według **liczby** znanych słów preferuje dłuższe, nawet zaszumione odczyty; określ metrykę proporcji, minimalną liczbę słów i deterministyczny tie-break. P2: klasyfikator `PP-LCNet_x1_0_doc_ori` używaj tylko z jednoznacznie wskazanym lokalnym ONNX oraz hashem/licencją i testem zgodności. Brak wiarygodnego modelu → `NOT_RUN(P2)`; nie pobieraj wag ani nie konwertuj ich po cichu w czasie badania.
- HerBERT niech pozostanie **opcjonalnym ramieniem eksperymentu**, nie obowiązkowym warunkiem ukończenia bazowego pomiaru OCR+silnik+Guard-symulacja. Brak lokalnego modelu/nieudana inferencja → `NOT_RUN(HerBERT)`, bez maskowania „na niby”.
- Nie rozbudowuj scope do produkcyjnej implementacji wykrywania uszkodzonych identyfikatorów: `LYNX-ANCHOR-PARITY` ma własny owner/task. Nie przenoś w tym briefie wartości `N` do polityki produktu ani nie zmieniaj zamrożonego S4.
- Poproś o szybki przegląd redukcyjny, czy jednoczesne mierzenie orientacji, HerBERT, hipotetycznego Guarda i API w ~520 l. jest wykonalne bez fałszywego uproszczenia. W razie potrzeby odłóż P2/HerBERT bez naruszania podstawowego pytania o końcowy wynik.

PO POPRAWCE: CC dopisuje do `brief.md` jednoznaczne kontrakty C1–C4, odsyła do `BOARD.md` i przekazuje Codexowi na BRIEF_ONLY. Bez uruchamiania modeli i bez zmiany produktu w tej rundzie. Techniczny PASS Codexa nie oznacza zgody OWNERA na implementację/merge.
