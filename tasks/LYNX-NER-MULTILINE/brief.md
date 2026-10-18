# LYNX-NER-MULTILINE — wielowierszowy kandydat NER nie może zniknąć w podmianie

STATUS: BRIEF_ONLY / ARCHITECT_APPROVED_FOR_CODEX_PRECHECK → Codex → ocena CC → implementacja CC → audyt Codexa exact SHA → merge wyłącznie OWNER.
ŹRÓDŁO: CC, tasks/LYNX-NER-MULTILINE/cc_proposal.md; zaakceptowana diagnoza arch/DIAGNOZA_2026-10-18.md r2, A1/A2 (ocena Codexa 9c4db4e). Architekt zweryfikował propozycję i oddzielił zachowanie Full od Express, zmienił rozmieszczenie testów oraz kryterium pomiaru. PRODUCT_TRUTH: arch/spec.md S1–S5, bez zmiany S4.
OWNER_INPUT: polecenie przygotowania obu zadań przez Architekta, po korekcie obiegu przez CC. To nie jest zgoda na merge.

## Problem i jedyny preferowany szew
W Full SpaCy wykrywa niektóre osoby/firmy jako jeden span zawierający znak końca wiersza. ner_layer._process_ner zamienia wszystkie białe znaki na pojedynczą spację, a layers/ner_adapter._remap_ner_ids i apply_ner_layer szukają dosłownej wartości w oryginalnym tekście. Znormalizowana wartość nie występuje — encja i dane pozostają jawne.

Naprawić lokalnie w ner_layer.py, zanim końce wiersza znikną z wartości: zachować oryginalne granice i z wielowierszowego spanu przygotować kandydatów zgodnych z rzeczywistymi liniami wejścia. Każda niepusta część przechodzi istniejące filtry osób/firm i kwalifikację; nie maskować automatycznie całego wiersza tylko dlatego, że był częścią spanu. Dotychczasowe encje jednowierszowe mają się zachować bez zmian. Adapter poprawiać wyłącznie po dowodzie, że ten szew nie wystarcza.

Skutek: dwie osoby w osobnych wierszach nie są jednym tokenem; osoba + stanowisko nie powoduje z definicji tokenizacji stanowiska; jedna osoba rozbita wierszem może mieć dwa tokeny, jeśli oba fragmenty rzeczywiście przechodzą filtry. W wyniku pozostają separatory wierszy w tej samej liczbie/kolejności, ale nie te same absolutne offsety (tokeny zmieniają długość). Mapa przechowuje dokładny podmieniony fragment, nie wersję z wymyśloną spacją. Przywróć jednoprzejściowy odtwarza wejście 1:1 na kontrolowanych przypadkach bez wcześniejszej, niezależnej zmiany OCR. Nie robić tokenów zagnieżdżonych ani wycinać zwykłego tekstu.

**EXPRESS NIE URUCHAMIA NER.** Bez wymogu maskowania nazwisk/firm przez Express; test Express sprawdza wyłącznie brak regresji istniejących reguł/telefonów/numerów i działania API. Nie dodawać NER do Express. Nie naprawiać tu nowych modeli HerBERT, fałszywych FIRMA z „z o.o.”, osób sklejonych w jednym wierszu (K3), scalania jednej osoby ponad newline (K5), FIRMA-BARE-REPEAT, globalnego OCR lub S4.

TASK_SCOPE:
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/tests/test_ner_multiline.py

OUT_OF_SCOPE: backend/tests/test_layers.py (584 linie), backend/tests/test_audyt_2026_10.py (601), spacy_ner.py, pipeline_new.py, pipeline_core.py, output_guard.py, pseudominizer_api.py, frontend, profil/seed, nowe modele, wspólny format tokenów. Jeden niewielki nowy plik testowy jest lepszy od dopisywania do plików przy limicie 600.

## Test falsyfikujący i PASS
1. RED→GREEN: syntetyczne wyniki SpaCy/NERResult z dokładnymi offsetami oraz spanem zawierającym newline: dwie osoby, osoba+rola, osoba przecięta w połowie, firma przecięta, trailing newline. Test musi przechodzić prawdziwą logikę ner_layer + adapter, a nie podawać już ręcznie poprawionej reverse_map. Sprawdzić maskowany tekst, tokeny, pełne wartości mapy, jednoprzejściowe Przywróć i linie.
2. Prawdziwy SpaCy i Full pipeline/Guard: co najmniej jeden syntetyczny tekst, na którym detect_entities faktycznie zwraca span z newline (obowiązkowa asercja); wcześniej jawny rozpoznany identyfikator po naprawie nie jest jawny ani nie jest zastąpiony błędną wartością. Jeśli model nie daje takiego spanu, to NOT_CHECKED i dobrać poprawny syntetyk — same mocki nie dają końcowego PASS.
3. Negatywy: sam „Protokolant” i „Al.” nie otrzymują nowego tokenu bez istniejącej podstawy kwalifikacji; kompletne identyfikatory z dwóch różnych wierszy nie sklejają się (NEWLINE-CROSSING); zwykłe NER/FIRMA i forma prawna nie tracą wierności; przy nowych FP — finding do K1, nie zwiększać list w tym Tasku. Express tylko smoke/regresja bez obietnic nowego NER.
4. Lokalna próbka diagnozy: plik Mobile oraz dokumenty A1/A2 na tych samych SHA i tej samej wersji backendu przed/po; raport ilości poprawionych ujawnień, FP, blokad i błędów Przywróć. Baseline 85/102 jawnych linii i 36/49 całych nazw są różnymi licznikami, starsze 36/102 pochodzi z innego commitu — nie ustanawiać arbitralnego progu „poniżej 36/102”. Wymagane poprawienie konkretnych A1/A2; niedostępne próbki => NOT_RUN, nie PASS.
5. Jawne uruchomienie nowego testu i istniejących test_layers + standardowych testów; przy dostępności działający backend /preview z syntetycznym TXT. Bez publikowania danych osobowych. PASS oznacza działający rzeczywisty pipeline, dokładną mapę/Przywróć i brak nowych wycieków/Guarda, nie „100% nazwisk” ani nowe pokrycie Express.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/ner_layer.py --symbol _process_ner
- TARGETS: backend/layers/ner_adapter.py --symbol _remap_ner_ids
- REASON: porównać surowy span, wartość po normalizacji i literalną podmianę.
GATE: 1 nowy plik testowy, ner_layer.py jest blisko 600 linii; bez przekraczania limitów bez zgody, >150 linii zmienionych lub ratio >5:1 => WYMAGA_DECYZJI. Codex: tylko BRIEF_ONLY precheck, bez implementacji.
