# Brief — LYNX-NER-GEO-EXACT
Status: BRIEF_ONLY / precheck Codexa. Bez implementacji i bez merge.
Źródło PRODUCT_TRUTH: `arch/spec.md` S1 (brak wycieków PII), S2 (zamrożony token), S3 (fail-closed), S4 (Guard), S5 (bez PII w logach); `arch/FINDING_2026-10_AUDYT.md` i `tasks/LYNX-T01-NER-PREFIX/round_01/implementation/DELIVERY.md` („BUG-NER-GEO-EXACT”); wiersz `LYNX-NER-GEO-EXACT` w `BOARD.md`.
OWNER_INPUT: „ok, pisz” — zgoda na przygotowanie briefu poprawki wykazanego wycieku, nie upoważnienie do merge. Wcześniejszy kierunek D1/D2: miasta wyłącznie w adresie, dwuznaczne nazwiska/słowa pospolite wyłącznie w kontekście. Nie rozszerzać tego zadania o ogólną warstwę kontekstową.

## Cel i odtwarzalny defekt
Forma nazwiska wykryta przez NER jako `OSOBA` jest odrzucana tylko dlatego, że występuje też w nazwie **ulicy**. Audyt T01: 1008/10080 form z `surnames_top1000` pokrywa się z geo, np. „Kowalskiego”, „Nowaka”, „Adamczyka”. Ta liczba to pomiar przecięcia list, NIE udowodniony odsetek wycieków w dokumentach.
Szew 1: `backend/ner_blocklist.py` buduje `_GEO_WORDS` z miast, ulic i placówek medycznych, po czym dodaje całość do `_NER_BLOCKLIST` (exact).
Szew 2: `backend/ner_layer.py::_filter_institutions` odrzuca `name_lower in _NER_BLOCKLIST` jeszcze **przed** sprawdzeniem osoby; `_is_person_word(strict=True)` także odrzuca każde `low in _GEO_WORDS`. Poprawienie jednego szwu bez drugiego nie usuwa wycieku.

## Zachowanie (istniejący UI, bez nowej funkcji)
Przy „Zamaskuj” rozpoznane przez spaCy jednowyrazowe nazwisko/odmiana z istniejącego słownika osób nie ginie wskutek pokrycia z nazwą ulicy, jeżeli nie jest także nazwą miasta/placówki ani świadomie blokowanym słowem pospolitym. Wynik: token OSOBA i poprawna mapa do „Przywróć” w dotychczasowym formacie. Przy braku rozpoznania osoby przez spaCy nie wymyślać encji ani nie uruchamiać nowego wyszukiwania; osobna praca nad kotwicami i pomiarem M1.
Adres („ul. Kowalskiego 7”) nadal rozpoznaje właściciel ADRES; samo miasto poza adresem („pracuje w Radomiu”) nie dostaje tokenu OSOBA. Nazwiska będące również słowami pospolitymi (np. „Piątek”, „Zając”, „Mazur”) nie stają się bezwarunkową listą „zawsze maskuj” — wymagają kontekstu, poza tym Taskiem. `FIRMA`, instytucje, kody, tokeny i filtry przymiotników pozostają chronione. Wyjątek NER/pipeline nadal blokuje wynik wg S3; przy błędzie nie pokazuj oryginału jako bezpiecznego.

## Minimalny szew / odpowiedzialność
Istniejący owner: `backend/ner_blocklist.py::_load_geo_words` i `backend/ner_layer.py::_filter_institutions`/`_is_person_word`. Oddziel pochodzenie wpisów geo (miasto vs ulica vs placówka) w ramach istniejącego ładowania danych, zachowując dotychczasową całościową ochronę geo dla reszty systemu. Bypass exact **wyłącznie** dla `OSOBA`, gdy forma należy do istniejącego `_PERSON_FORMS` (konkretny słownik, nie dowolne rozstrzygnięcie Morfeusza), kolizja pochodzi tylko z ulicy, a reguły miasta/placówki i istniejąca ręczna blocklista/słowa pospolite nie wskazują odrzucenia. Musi przejść także `strict` w T01; nie usuwać globalnie `_GEO_WORDS` z blocklisty.
Zachować możliwość odrzucenia słowa, które jest jednocześnie miastem, ulicą i nazwiskiem; samo `_PERSON_FORMS` nie wystarcza do podważenia świadomego odrzucenia. Nie wprowadzać kolejnego NER, nowych danych JSON, nowego pipeline ani trwałego stanu.

TASK_SCOPE:
- backend/ner_blocklist.py
- backend/ner_layer.py
- backend/tests/test_audyt_2026_10.py
- backend/layers/ner_adapter.py
- backend/pseudominizer_api.py

OUT_OF_SCOPE: T01 ponownie, kontekstowy AnchorEngine/P05, dodawanie nieznanych nazwisk, seed/T04, profile/trie, TokenAllocator/T03, OCR, firmy w cudzysłowach (T20/FIX-QUOTES), nazwy miast poza adresem, format TOKEN_RE/taksonomia/.lynxdict (S2), Output Guard/fail-closed (S3/S4), GUI, generowanie „zawsze maskuj” i zmiana zestawów benchmarku.

## Najmniejsze testy (wyłącznie syntetyczne; `backend/tests/`)
1. Reproduktor `_filter_institutions` z encją `_NER(..., "OSOBA")` dla „Kowalskiego”, „Nowaka”, „Adamczyka”: sprawdzić, że wybrane formy są jednocześnie w słowniku osób i w danych ulic, a **nie** w zbiorze nazw miast/placówek ani ręcznych wykluczeń; wtedy muszą przejść exact i strict. Jeśli konkretna forma ma inne pochodzenie geo, wymienić ją na udokumentowany bezsporny przykład z przecięcia — bez warunku `if` pomijającego asercję.
2. Negatywy regresyjne na tej samej funkcji: miasto „Radom”, forma miejscowa „Warszawie”, dwuznaczne „Piątek”/„Zając”, adres „ul. Kowalskiego 7”, instytucja „ZUS” i `FIRMA` z nieuprawnioną nazwą geo — mają zachować dotychczasowe odrzucenie w ustalonych kontekstach. Nie dopuścić do nowego przepuszczenia jednowyrazowej nazwy tylko dlatego, że jest na obu listach. **„Zapłata” jest znanym bazowym fałszywym trafieniem (BUG-NER-FP) przepuszczanym przed T01 i po T01**: może służyć jako obserwacja baseline, ale nie wymagać odrzucenia ani zaliczać jej jako nowej regresji GEO-EXACT; naprawa poza zakresem.
3. Jeden syntetyczny pion przez istniejącą ścieżkę NER/adapter/pipeline z kontrolowaną detekcją spaCy: „Wniosek Kowalskiego” → nazwisko zamaskowane w wyniku, poprawny `reverse_map`; „ul. Kowalskiego 7” nie staje się osobą. Wystarczy minimum, bez pełnej macierzy.
4. `cd backend && py -3 -m pytest tests/test_audyt_2026_10.py -q -o log_file=NUL` (Windows) + celowane regresje filtra T01; na Linux bez Windowsowego `NUL`. Pełna suita/benchmark tylko jeśli niezależny audyt wykaże rzeczywisty szew albo za zgodą OWNERA. Znany `IBAN-RECEPTA` nie jest częścią tego Tasku.
5. Nie kopiować pełnych wartości osób do logów/dostawy. Dla wykazania regresji raportować liczbę FN/FP na identycznych, rozłącznych zdaniach syntetycznych oraz SHA; żadnych deklaracji „100% szczelności” na podstawie kilku testów.

PASS: (a) naprawione oba szwy exact/strict dla jednoznacznych nazwisk-odmian pochodzących wyłącznie z ulic; (b) zachowane **istniejące** odrzucanie miast, placówek, objętych dotychczasowym filtrem słów pospolitych i instytucji; bez wymogu naprawiania bazowego FP „Zapłata”;  (c) brak nowej kolizji/zmiany tokenu; (d) S3/S4/S5 nietknięte; (e) brak nowych nieuzasadnionych FP w testach celowanych. Przez błędną klasyfikację NER nie zastępować ręcznie wyniku pozytywnego — zgłosić jako inny finding.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/ner_blocklist.py --symbol _load_geo_words
- TARGETS: backend/ner_layer.py --symbol _filter_institutions
- REASON: zmiana dokładnej reguły odrzucania encji i pochodzenia geo; przed implementacją sprawdzić istniejących odbiorców tych zbiorów.
KOREKTA B1 po prechecku Codexa `round_01/tests/tests_r1.txt`: oddzielono bazowy FP „Zapłata” od negatywów regresyjnych; powtórny precheck wyłącznie B1, bez otwierania pozostałych granic.
GATE: max 2 nowe pliki (cel: 0), plik ≤600 i funkcja ≤50 linii dla nowych elementów, dla starszych nie pogarszać; >150 linii zmienionych lub ratio >5:1 = WYMAGA_DECYZJI. Każdy zmieniony plik musi znajdować się w TASK_SCOPE.

## ROZSZERZENIE CC (2026-10-17, przed audytem implementacji)
Zasada z polecenia Pawła 2026-10-17: ta sama klasa błędu znaleziona przy Tasku jest naprawiana na tej samej gałęzi, z jawnym rozszerzeniem briefu przed implementacją; Codex audytuje rozszerzenie razem z Taskiem.
Klasa: forma nazwiska kolidująca wyłącznie z nazwą ulicy odrzucana przez exact `_NER_BLOCKLIST` (zawiera `_GEO_WORDS`). Ten sam zbiór `_STREET_ONLY_PERSON_FORMS`, bez nowych danych.
- E1 `backend/layers/ner_adapter.py::_apply_initials` (l.178): „K. Kowalskiego” — warstwa inicjałów (zapas, gdy spaCy nie rozpozna osoby) pomija nazwisko z blocklisty → jawne. Reproduktor: `run_pipeline_new` z `process_ner` → `({}, {})`: „Zgoda K. Nowaka na zabieg.” zostaje bez zmian. Poprawka: nie pomijać, gdy nazwisko ∈ `_STREET_ONLY_PERSON_FORMS`.
- E2 `backend/pseudominizer_api.py::profile_add_entity` (l.762): ręczne dodanie „Kowalskiego” jako OSOBA odrzucane jako „słowo pospolite” → użytkownik nie może sam uszczelnić profilu. Poprawka: dopuścić tylko dla `token_type == "OSOBA"` i formy ∈ `_STREET_ONLY_PERSON_FORMS`; miasta, placówki, ręczna blocklista, stop-words i inne typy bez zmian.
Testy (w `test_audyt_2026_10.py`): E1 pozytyw z wyłączonym spaCy; E2 pozytyw OSOBA + negatywy „Radom”/OSOBA i „Kowalskiego”/FIRMA (400).

Rozszerzenie zakresu: `backend/layers/ner_adapter.py` (E1) i `backend/pseudominizer_api.py` (E2) dopisane do listy TASK_SCOPE powyżej (gate czyta tylko tę listę).
