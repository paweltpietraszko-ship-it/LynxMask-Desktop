# LYNX-ARCH-CANDIDATES — F0a: bezpieczny rdzeń kandydatów (bez integracji)

STATUS: BRIEF_ONLY / Architect → Codex precheck → CC review → implementacja po ocenie i zgodzie na rozmiar → Codex audyt exact SHA → merge tylko OWNER.
PRODUCT_TRUTH: arch/spec.md S1–S5, BOARD LYNX-ARCH-CANDIDATES, tasks/LYNX-ARCH-CANDIDATES/cc_proposal.md, tasks/LYNX-ARCH-CANDIDATES/architect_assessment.md (obowiązkowa lektura). Propozycja docelowej architektury CC NIE jest jeszcze przyjęta do produkcji. Akceptujemy jedynie izolowany dowód mechaniki F0a. OWNER zaakceptował wstępnie Q1 (jeden token/kanoniczna forma do odpowiedzi AI), lecz nowy format mapy nie jest tu autoryzowany.

## Cel i wyzwalacz
Na wywołanie WYŁĄCZNIE z syntetycznego testu/programu audytowego, F0a przyjmuje oryginalny Python str i listę kandydatów wykrytą poza modułem. Zwraca deterministyczną reprezentację zaakceptowanych rozłącznych spanów albo jawne AMBIGUOUS/INVALID — bez cichego upuszczenia danych. Dla rozłącznych i jednoznacznych kandydatów wykonuje JEDNĄ podmianę od końca na tym oryginale, wykorzystując istniejący TokenAllocator. Nie uruchamia żadnego produkcyjnego detektora.

Candidate (data-only): start/end półotwarte w oryginalnym str, typ zgodny z aktualną taksonomią S2, value = oryginał[start:end], engine_id (źródło), evidence jako niepusta kolekcja zamkniętych nazw rodzajów dowodów; w F0a dowód ma tylko pochodzenie, bez wag/oceny siły. Żadnych surowych fragmentów w logach. Nie zakładać indeksów w bajtach UTF-8 ani UTF-16 JS. Należy zwrócić jawny wynik przy poprawnym braku kandydatów; przy nierozstrzygniętym konflikcie nigdy nie emitować rzekomo bezpiecznego tekstu.

Reguły F0a:
- Walidacja: 0 ≤ start < end ≤ len(original), value == original[start:end]; znane typy S2, niepusta lista dowodów, żaden candidate nie obejmuje tokenu wniesionego przez użytkownika. Dla niepoprawnych spanów INVALID/STOP, bez tekstu do kopiowania.
- Ten sam span i ten sam typ od kilku silników: jeden kandydat z zachowaniem zbioru rodzajów dowodów; wielokrotne dowody tego samego rodzaju nie zwiększają siły.
- Częściowe nakładanie i identyczny span o sprzecznych typach: AMBIGUOUS/STOP z maszynowym kodem, bez arbitralnej przewagi długości, kolejności silnika lub punktów. To świadomie NIE jest gotowy arbiter produkcyjny. Przyszłą tabelę wag/wet Codex ma wymagać jako osobny, uprzednio zamrożony kontrakt.
- Test granicy podciągu: nie akceptować spanu wewnątrz dłuższego słowa lub identyfikatora (w tym łączniki / polskie litery). Jeśli realny typ strukturalny wymaga granicy innej niż słowo, dopiero F1 rozstrzyga jego politykę; F0a nie zgaduje.
- Render przyjętych rozłącznych spanów od prawej do lewej na oryginalnym tekście, bez przepisywania reszty. Użyć aktualnego TokenAllocator tylko do przydziału tokenów, bez zmiany jego zachowania, formatu ani mapy. Jeśli allocator połączy RÓŻNE dosłowne wartości pod jednym tokenem, F0a nie może obiecać roundtrip źródła: oznaczyć UNSUPPORTED_LITERAL_COLLISION/STOP (to K2/Q1, późniejsza faza), a nie ukrywać błąd. Identyczna dosłowna wartość powtórzona w dwóch miejscach może korzystać z jednego tokenu.
- W syntetykach bez kolizji canonical zachodzi Przywróć = original znak w znak, jednoprzebiegowo; źródłowy tekst poza spanami jest identyczny (porównywać UTF-8 po rekonstrukcji), a wynik nie zawiera częściowo przyklejonych tokenów.

TASK_SCOPE:
- backend/engine/core.py
- backend/tests/test_arch_candidates_f0a.py

OUT_OF_SCOPE: backend/engine/__init__.py, modyfikacje istniejących pipeline/warstw/TokenAllocator/Guard/API/endpointów, tryb ENGINE, UI, archive, .lynxdict, mapy wystąpień K2, realny NER, OCR i mapowanie pozycji, fallback/Anchor, arbitralna punktacja dowodów, wszystkie dane osobowe. Import w dev z backend/engine/core.py jako namespace package — sprawdzić w prechecku kompatybilność Python i ścieżek testowych, bez dodawania trzeciego pliku; jeśli trzeci plik konieczny, STOP i nowy brief/zgoda.

## Test falsyfikujący
1. Dwa syntetyczne niepokrywające się fragmenty OSOBA/NUMER w krótkim tekście + prefiks/sufiks i CRLF: dokładne offsety, tokeny, mapa i Przywróć 1:1, identyczny tekst poza podmianą. Dwa identyczne wystąpienia tej samej wartości bez utraty dosłownej formy.
2. Jeden span OSOBA z dwoma silnikami dowodu → jedna zaakceptowana encja; odwrócenie kolejności kandydatów/duplikat dowodu nie zmienia rezultatu. Deterministyczność numeracji niezależnie od kolejności wejściowej listy (kolejność tekstowa w oryginale).
3. Kontrpróby INVALID/STOP: błędne offsety, wartość różna od oryginalnego wycinka, token injection w wejściu, nieznany typ, kandydat pusty, OSOBA Nowak jako środek Nowakowska, dwóch różnych kandydatów ze wspólnymi znakami. AMBIGUOUS na tym samym spanie OSOBA i INSTYTUCJA oraz na częściowym overlap, nawet gdy dłuższy jest mniej trafny. STOP nie może wyświetlać oryginalnego tekstu jako bezpiecznie zamaskowanego.
4. Unicode: polskie litery, łącznik, emoji przed spanem, combining mark, CRLF, powtarzające się frazy; dokładne cięcie w oryginalnym Python str i brak „odjazdu” indeksów. Wartości semantycznie wspólne, lecz różnie zapisane, które dzisiejszy TokenAllocator scala → UNSUPPORTED_LITERAL_COLLISION zamiast złego Przywróć.
5. Przebieg jawnie uruchomionego nowego testu oraz dostępnych testów pipeline_core; zero modyfikacji i zero regresji starego backendu. PASS dotyczy WYŁĄCZNIE weryfikowalności mechaniki, nie 178 dokumentów i nie jakości detekcji. Nie podawać A/B bez silników.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_core.py --symbol TokenAllocator
- TARGETS: backend/pipeline_core.py --symbol ConflictResolver
- REASON: pożyczyć jedynie alokator numerów; obecny ConflictResolver to inna semantyka i nie stanowi gotowej polityki punktowej.

GATE: maks. 2 nowe pliki w produkcji/testach łącznie; core.py i test_arch_candidates_f0a.py każdy <300 linii, funkcje ≤50; >150 zmienionych linii lub ratio >5:1 → WYMAGA_DECYZJI właściciela PRZED implementacją. Codex BRIEF_ONLY sprawdza, czy taka izolacja i dwa pliki wystarczają; nie implementuje. F0b (widok OCR i bezpieczna projekcja) to osobny brief dopiero po F0a; F1 i A/B nie są teraz autoryzowane.
