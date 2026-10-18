# LYNX-FAILCLOSED-S3 — awaria/obejście nie może zwrócić surowych danych jako wyniku maskowania

STATUS: ARCHITECT_BRIEF / BRIEF_ONLY → Codex precheck → CC niezależna ocena → CC implementacja → Codex audyt exact SHA → merge wyłącznie OWNER.
POCHODZENIE: tasks/LYNX-FAILCLOSED-S3/cc_proposal.md, ultrareview F1/F1b/F2/F3/F4/F5, stary niewykonany LYNX-T06-GUARD-BLOCK, BOARD; wszystkie reproduktory syntetyczne CC. OWNER_INPUT: łączyć małe poprawki, jeśli ta sama klasa. OCENA ARCHITEKTA: spójny temat granicy zaufania S3, ale wieloownerowy; Codex ma rygorystycznie ocenić zakres i kolejność przed implementacją.
PRODUCT_TRUTH: arch/spec.md S1, S3, S5; S2 bez zmiany formatów; S4 jest wciąż FROZEN i oddzielny projekt LYNX-SPEC-S4-GUARD-WARN. Ten Task NIE zmienia polityki ostrzeżeń/blokad Guarda. Gdy S4 kiedyś się zmieni, S3 awarii nadal blokuje.

## Ustalone przypadki
F1: pipeline_new.run_pipeline_express przy wyjątku zwraca (oryginalny tekst, {}, False), /preview-express ignoruje trzecią wartość i mówi blocked=False.
F1b: pipeline.pseudonymize_document przy nieoczekiwanym wyjątku zwraca PipelineResult(text=oryginał, error=...), a Full API/UI może potraktować pole text jako wynik do skopiowania.
F2: spacy_ner.detect_entities i ner_layer.process_ner pochłaniają wyjątki i zamieniają je na „brak encji”, co nie ustawia ner_error/force_block.
F3: output_guard.guard_output_with_map przy MAP_LEAK zwraca redacted_text=text, przywracając w podglądzie wartości HIGH już zamazane przez guard_output. Dodatkowo teksty naruszeń i logów mogą zawierać jawne wartości — to też S5.
F4: allowlista sprawdza substring całego komunikatu naruszenia, a nie konkretną pełną wartość; wpis „Jan” może uciszyć „Janina”, wpis „encja”/„mapy” może uciszyć naruszenie, GUARD_ERROR nigdy nie może podlegać allowliście.
F5: przed OCR normalizer API odrzuca tylko poprawne tokeny; „OSOBA_0O1” po zmianach OCR może stać się ważnym OSOBA_001 i zderzyć się z tokenem alokatora. Potrzebna druga kontrola na granicy wejścia do tokenizacji, w Full i Express.

## Kontrakt (jedna zasada przez wszystkie warstwy)
1. **Każda AWARIA pipeline/NER/Guarda, a także wykryte wstrzyknięcie tokenu przed lub po OCR, kończy się kontrolowaną odmową.** Brak tekstu wejściowego i niepełnego wyniku w anonymized_preview, tokenach, mapie, polu original_text przekazywanym w odpowiedzi błędu albo w danych do kopiowania. blocked=True / error z krótkim komunikatem bez wartości; dla token injection zachować HTTP 422, dla nieoczekiwanej awarii użyć istniejącej ścieżki błędu (precheck ma ustalić właściwy status HTTP). Nie wysyłać wyjątku str(e) zawierającego tekst użytkownika do UI ani do zwykłych logów.
2. **Express MUSI respektować force_block** zwrócony przez run_pipeline_express; samo True w trzecim polu nie wystarczy, gdy API nadal pokazuje text. Podobnie Full z błędem nie może wystawić kopii oryginału. Widoczny UI i kopiowanie/zapis: wynik nie istnieje przy S3 error; użytkownik dostaje komunikat i może poprawić wejście/ponowić. Działa także przy nieoczekiwanym wyjątku na poziomie endpointu.
3. **NER:** poprawne zero encji jest normalnym wynikiem; wyjątek środowiska/modelu/algorytmu nie jest zerem encji. Propagować do istniejącej ścieżki state.ner_error → force_block. Zapewnić, że jeśli preekstrakcja i fallback oba failują, nie ma możliwości wypuszczenia częściowego wyniku.
4. **Guard MAP_LEAK:** zablokowany wynik nie może pokazywać surowych wartości (HIGH ani known_plain), także gdy wykrycie pochodzi wyłącznie z mapy. Nie opierać bezpieczeństwa na pojedynczej podmianie tekstu, która przepuszcza nazwiska (nie HIGH); bezpieczniej ukryć treść zablokowanej odpowiedzi niż udawać kompletne redaction. Zakazane jest używanie redacted_text=text w drodze do podglądu i umieszczanie dosłownych wartości w powodach/logach. Powód dla UI = klasa, lokalizacja lub liczba, bez pełnego PII.
5. **Allowlista:** porównywać równość z całą, rzeczywistą encją, bez względu na wielkość liter, po niezbędnym istniejącym oczyszczeniu brzegów; nie porównywać z językiem komunikatu naruszenia. GUARD_ERROR i awarie S3 nigdy nie podlegają wyciszeniu. Przy braku wiarygodnego spanu encji nie zgadywać — pozostawić blokadę i finding zamiast substring allowlist.
6. **OCR token injection:** po normalizacji OCR, zanim jakikolwiek allocator/trie/nadanie identyfikatora może potraktować powstały token jako prawdziwy, wykryć TOKEN_RE na znormalizowanej postaci i zablokować. Bez zmiany samej normalizacji ani TOKEN_RE/S2. Sprawdzić, że zwykła korekta OCR cyfr w numerze nie generuje fałszywego token injection.
7. Poprawny przebieg bez wyjątku pozostaje zachowany, w tym istniejąca polityka S4 i odmowy dla tokenów wejściowych. Bez ukrywania błędów w return False lub pomijania Guarda w Full. Blokada z powodu S4 także nie może udostępnić przycisku „Kopiuj”; ewentualny przyszły tryb ostrzegania to osobny kontrakt.

## Minimalny szew i sekwencja
Codex przed implementacją identyfikuje najkrótszy łańcuch: od wyjątku z NER/warstwy/OCR przez force_block/result, endpoint JSON aż do ekranów Tauri, plus osobno Guard MAP_LEAK/allowlist. Nie budować nowego frameworka błędów, nie zmieniać podziału Full/Express. Prace sugerowane w jednym Tasku, ale na jednej gałęzi z checkpointami: (A) F1/F1b/F2/force_block, (B) F3/F4/Guard, (C) F5/OCR token injection, (D) minimalne UI, jeśli API samo nie usuwa możliwości skopiowania. Każdy checkpoint audytowany łącznie na finalnym SHA; jeśli zakres przekracza GATE, STOP/WYMAGA_DECYZJI PRZED implementacją, a nie „PASS” po przekroczeniu.

TASK_SCOPE:
- backend/pipeline_new.py
- backend/pipeline.py
- backend/pseudominizer_api.py
- backend/ner_layer.py
- backend/spacy_ner.py
- backend/output_guard.py
- frontend/src/screens/Pseudonimizuj.tsx
- frontend/src/screens/ExpressModeScreen.tsx
- backend/tests/test_failclosed.py

OUT_OF_SCOPE: backend/tests/test_audyt_2026_10.py (601 linii, istniejące 3 xfail mają pozostać dowodem; nie trzeba usunąć markera dla PASS, ale po fixie je uruchomić i raportować XPASS), zmiana S4/arch/spec.md i frozen lock, TOKEN_RE/taksonomia, OCR reguły i warstwy normalizacji, alokacja oraz MAP-FIDELITY, repo logowanie do plików, profil/archiwum, nowe UI flow poza blokadą Kopiuj/Zapisz, produkcyjne backend deploy. Jeśli potrzebna korekta existing xfail markerów, osobne zatwierdzenie rozszerzenia TASK_SCOPE — nie modyfikować ich wbrew gate.

## Minimalna falsyfikacja
1. RED→GREEN Full i Express przez prawdziwy TestClient API (tak jak aplikacja): wymuszony wyjątek warstwy / _run_pipeline / nlp (ValueError, MemoryError) — komunikat i blocked, brak oryginalnego tekstu/surowego PESEL/nazwiska w całym JSON, brak mapy i tokenów do kopiowania. Sprawdzić niewymyślone statusy w UI; nie wystarczy force_block=True na niskiej warstwie.
2. F2: syntetyczny wynik „zero encji” bez wyjątku daje nieblokowany normalny przebieg, wyjątek _get_nlp/nlp w Full daje blokadę, Express nadal bez NER; nie przestawiać wariantów SpaCy.
3. F3 i F4: MAP_LEAK z HIGH PESEL i z samym znanym nazwiskiem, log/guard_reasons/redacted_text/preview bez dosłownych wartości, blocked=True; allowlista „Jan” nie tłumi „Janina”; pełne „Janina Kowalska” może być allowlisted tylko jako ta konkretna encja, a GUARD_ERROR nigdy.
4. F5: OSOBA_0O1 i FIRMA_1l2 syntetycznie w wejściu, OCR normalizuje do poprawnego tokenu → odmowa Full/Express PRZED allocator; prawidłowe liczby OCR bez tokenowego prefiksu nadal maskowane.
5. Front: oba ekrany przy zablokowanej sesji/odmowie nie pokazują pola z danymi jako „wyniku zamaskowanego”, nie pozwalają go skopiować, zapisać ani przejąć jako wynik Przywróć. Nie wystarcza jedynie disable przycisku, jeśli tekst surowy nadal widnieje pod nagłówkiem bezpiecznego wyniku.
6. Uruchomić jawnie nowy test (poza pytest.ini), istniejące trzy xfail ultrareview (sprawdzić oczekiwany XPASS bez zmiany pliku), standardową suite, testy NER-MULTILINE/TEXT-LIMIT-15K/MAP-FIDELITY jeśli już zmergowane. Lokalny zestaw 17 dokumentów diagnozy: brak nowych blokad przy poprawnym silniku, zliczyć blokady/komunikaty bez wartości. Brak zbioru = NOT_RUN, nie pełny PASS pomiaru. Gate i audyt dokładnego SHA.
PASS: awaria żadnej warstwy nie wypuszcza surowej kopii, wyjątek NER nie staje się „brakiem encji”, MapLeak/allowlist nie osłabiają blokady ani nie przeciekają w podglądzie/logach, fałszywe tokeny OCR blokowane, oba ekrany nie kopiują błędu, zero regresji normalnego przebiegu. Ze względu na 9 plików i rozmiary legacy Codex może zwrócić WYMAGA_DECYZJI_PODZIAŁU; nie wdrażać części w ramach niezatwierdzonego rozszerzenia.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_new.py --symbol run_pipeline_express
- TARGETS: backend/pipeline.py --symbol pseudonymize_document
- TARGETS: backend/pseudominizer_api.py --symbol preview_express
- TARGETS: backend/ner_layer.py --symbol process_ner
- TARGETS: backend/spacy_ner.py --symbol detect_entities
- TARGETS: backend/output_guard.py --symbol guard_output_with_map
- REASON: S3 jest kontraktem całego łańcucha, a nie tylko wartości bool w pipeline.
GATE: 1 nowy test; istniejące ner_layer.py ~601 linii, API ~1130 linii, UI legacy >600; bez pogorszenia ratchet. >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI. Codex BRIEF_ONLY ma ocenić adekwatność dziewięciu plików do jednej dostawy oraz brak zmiany zachowania S4.
