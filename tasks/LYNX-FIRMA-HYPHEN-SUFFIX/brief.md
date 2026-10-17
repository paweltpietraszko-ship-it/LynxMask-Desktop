# LYNX-FIRMA-HYPHEN-SUFFIX — pełna nazwa firmy z myślnikiem i formą prawną

STATUS: BRIEF_ONLY → Codex precheck → CC niezależna ocena → CC implementacja → Codex audyt exact SHA → merge wyłącznie OWNER.
PRODUCT_TRUTH: arch/spec.md S1–S5; BOARD.md LYNX-LAYOUT-SAMPLES i LYNX-LAYOUT-FINDINGS; próbka lokalna 20 dokumentów / 70 pól syntetycznych; audyt/engine_quality.py --layout. OWNER_INPUT 2026-10-17: po MERGED ZUS-BOXED-IDS wybrać kolejne findings (COMB-OTHER-FIELDS, FIRMA, ADRES, FP nagłówka). OCENA ARCHITEKTA: najpierw FIRMA, ponieważ próbka już wykazuje **3 jawne i 2 częściowe** wartości firmy; COMB-OTHER-FIELDS ma potwierdzoną stratę formatu, lecz nie potwierdzony wynik maskowania nazwisk po scaleniu. Nie łączyć klas w jednej dostawie.

## Wada i szew
W prawdziwych układach dokumentów wypełnionych syntetyką nazwy firm z łącznikiem i formą prawną, np. rodziny «Nazwa-A Sp.k.», «Nazwa-X S.A.», «Nazwa-Y Sp. z o.o.», są w 3 przypadkach jawne, a w 2 zamaskowane tylko częściowo (np. sama forma prawna). Dane źródłowe są wyłącznie lokalne. Nie ma jeszcze potwierdzonego pojedynczego miejsca utraty. Podejrzane już istniejące ownery: backend/ner_layer.py (granice encji, _TRUNC_ENDINGS / _SUFFIX_COMPLETION_RE, forma prawna) i backend/layers/ner_adapter.py (warianty i _FIRMA_CLEANUP_RE). backend/ner_blocklist.py dostarcza istniejącą listę sufiksów; nie rozszerzać jej bez wskazania konieczności. backend/layers/institution.py obsługuje instytucje publiczne i NIE jest właścicielem FIRMA.

## Krok 0: diagnoza przed kodem (Codex precheck / CC)
Dla reprezentatywnego syntetycznego tekstu z łącznikiem/sufiksem i dla pięciu lokalnych wystąpień (jeśli nadal dostępne) zebrać **tylko statusy i liczności** na granicach:
- pełny tekst wejściowy → wyniki detektora SpaCy (span/etykieta) → process_ner reverse_map/variants → ner_adapter/allocator → finalny tekst + mapa → symulacja Przywróć;
- ustalić, czy problem to *brak kandydata*, *ucięta granica*, *zła klasyfikacja*, czy *utrata formy prawnej przez cleanup*. Nie zmieniać regexu „na ślepo” ani produkcyjnych filtrów NER bez reproduktora RED;
- gdy SpaCy w ogóle nie daje przydatnego fragmentu i obecny szew nie wystarcza: STOP z dowodem do Architekta, nie dodawać nowej warstwy FIRMA ani globalnego regexu łapiącego wszystkie słowa przed Sp.k.

## Oczekiwane zachowanie
Jeśli w tekście jest rozpoznawalna nazwa przedsiębiorstwa z łącznikiem i rzeczywistą formą prawną, Zamaskuj (Full z aktywnym prawdziwym NER) zastępuje **całą nazwę wraz z formą** jednym FIRMA_NNN. Ani nazwa, ani końcówka prawna nie zostają jawne; reverse_map ma kompletną wartość źródłową, bez tokenu wewnątrz tokenu. Przywróć odtwarza cały wejściowy tekst 1:1 dla reproduktorów bez wcześniejszej modyfikacji OCR. Nie może powstać samodzielne FIRMA_NNN na «Sp.k.» przy pozostawieniu nazwy.

Negatywy: «Sp. z o.o.» lub «S.A.» bez nazwy to nie wystarczający dowód firmy; zwykłe słowo z łącznikiem («biało-czerwony»), instytucje ZUS/KNF, nagłówki WERSALIKAMI i fragmenty adresów nie mają stać się nowymi FIRMA. Nie zmieniać świadomie polityki Express: w tym trybie brak NER, więc nie obiecywać pełnego wykrywania nieznanych firm; sprawdzić jedynie brak regresji/nowych przecieków spowodowanych zmianą. Guard blocked ani force_block nie jest PASS maskowania.

TASK_SCOPE:
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/tests/test_layers.py

OUT_OF_SCOPE: nowe regexowe warstwy firm/AnchorEngine, backend/ner_blocklist.py (tylko odczyt; rozszerzenie po dowodzie i nowym prechecku), spacy_ner.py i douczanie NER, layers/institution.py, pipeline_new.py, document_processor.py, output_guard.py, TOKEN_RE, audyt/engine_quality.py, UI, COMB-OTHER-FIELDS, ADRES m.8, SPRZECIW FP, KRS/KW, prawdziwe dane osobowe. Jeśli root cause wymaga innego ownera, STOP i punktowa korekta briefu przed zmianą implementacyjną.

## Testy i PASS
1. Minimalna rodzina RED→GREEN na sztucznych nazwach z myślnikiem i zakończeniem Sp.k., S.A., Sp. z o.o.; także wariant bez łącznika. W Full z prawdziwym NER sprawdzić cały FIRMA, poprawny reverse_map, Przywróć 1:1, tekst przed/po nienaruszony. Dodatkowa kontrola na poziomie process_ner i ner_adapter, aby ujawnić właściciela błędu. Nie zaliczać PASS na jednym sztucznie podstawionym mocku NER przy niedziałającym pionie rzeczywistym.
2. Zestaw kontrprób: forma prawna sama, przymiotnik z myślnikiem, zwykły nagłówek, nazwa instytucji, dwie różne firmy w jednym zdaniu, końcowa kropka i następne zdanie; brak fałszywego sklejenia i utraty sufiksu przy Przywróć. Stare testy firm, NER/Guard i NEWLINE-CROSSING bez regresji.
3. Opcjonalny lokalny recheck **tych samych pięciu** wartości na tym samym ignorowanym zbiorze 70 pól / hash plików z engine_quality --layout: 3 leak + 2 partial → 5 masked przy prawidłowym pełnym spanie i kategorii. Jeśli local manifest/dane nie są dostępne: NOT_RUN, a nie twierdzenie o zamknięciu rzeczywistej próbki. Nie zmieniać runnera, nie ujawniać wartości w raporcie.
4. Uruchomić jawnie testy w backend/tests/test_layers.py (poza domyślnym pytest.ini), standardową suitę i gate exact SHA. Sprawdzić rozmiar: ner_layer.py ma dziś ok. 542 l., ner_adapter ok. 452, test_layers ok. 506; nie przekroczyć 600 l. ani limitu funkcji bez WYMAGA_DECYZJI. Raporty tylko syntetyczne i bez treści realnych dokumentów.

PASS: naprawiona jedna mierzalna klasa częściowego/pełnego wycieku FIRMA z poprawną mapą, bez rozluźnienia filtrów NER lub S2–S5; niezależny audyt exact SHA. To nie zamyka COMB-OTHER-FIELDS, ADRES ani FP SPRZECIW.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/ner_layer.py --symbol _process_ner
- TARGETS: backend/layers/ner_adapter.py --symbol apply_ner_layer
- REASON: nie tworzyć równoległego detektora, najpierw określić miejsce ucięcia pełnej nazwy przez NER/adapter.
GATE: 0 nowych plików; >150 zmienionych linii lub ratio >5:1 → WYMAGA_DECYZJI. Codex BRIEF_ONLY: precheck wykonalności, minimalności, testowalności; implementacji NIE rozpoczynać przed oceną.
