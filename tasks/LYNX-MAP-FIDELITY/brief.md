# LYNX-MAP-FIDELITY — zgodność znaczenia tokenu, granic dopasowania i mapy

STATUS: ARCHITECT_BRIEF / BRIEF_ONLY → Codex precheck → CC niezależna ocena → CC implementacja → Codex exact-SHA audyt → merge tylko OWNER.
POCHODZENIE: tasks/LYNX-MAP-FIDELITY/cc_proposal.md, ultrareview F10/F7/F6, BOARD LYNX-CANONICAL-DEDUP i LYNX-REPLACE-BOUNDARY, zaakceptowane pomiary CC; właściciel poprosił o łączenie małych poprawek tam, gdzie dotyczą tej samej klasy.
PRODUCT_TRUTH: arch/spec.md S1–S5, szczególnie S1/S2/S3; wynik nie może podmienić kwoty/daty na inną wartość ani ujawnić fragmentu PII przez źle ulokowany token. Brak zmiany formatu kategorii, TOKEN_RE, Guarda/S4.

## Defekty i granice odpowiedzialności
D1 (F10): TokenAllocator._canonical usuwa separatory niezależnie od typu. Kwota 15.00 zł i 1 500 zł oraz daty 2.11.2023 i 21.1.2023 mogą otrzymać JEDEN token, choć oznaczają różne wartości. To cicha zmiana znaczenia także po Przywróć. Jednocześnie pomiar CC na 178 dokumentach: 86 tokenów obejmujących różne zapisy, ale zero z potwierdzoną różną WARTOŚCIĄ; prawidłowe łączenie 3 700 zł = 3700 zł, wariantów zapisów daty, IBAN/NIP ma przetrwać. Nie rozdzielać identycznej wartości tylko dla „łatwego” Przywróć.
D2 (F7): globalne replace() w layers/ner_adapter.py i początek _ADDR_RE bez lewej granicy pozwalają dopasować wnętrze dłuższego słowa lub przykleić token do litery: „SzpitADRES_002”, „OSOBA_001owska”, „FIRMA_013u”. Pomiar CC: 32 sklejone tokeny w 17/178 dokumentów.
D3 (F6): _process_ner normalizuje wielokrotne spacje/tab na pojedynczą spację w wartości encji, więc tekst typu „Jan  Kowalski” albo „Jan\tKowalski” nie jest literalnie znaleziony i pozostaje jawny. To dalszy przypadek po MERGED LYNX-NER-MULTILINE, nie powrót do tego Tasku.

## Kontrakt zachowania
1. ALLOCATION: Dwie różne wartości semantyczne nie mogą dzielić jednego tokenu. Dla danych rozpoznanych jednoznacznie: kwota = wartość liczby i waluta (użyć bezstratnej arytmetyki dziesiętnej, bez float), data = poprawna (dzień, miesiąc, rok), a identyfikatory korzystają z dotychczasowej kanonizacji. Gdy zapis jest niejednoznaczny, NIE wolno go scalić z inną liczbą/datą na podstawie samych skasowanych separatorów. Forma zapisu 3 700 zł / 3700 zł i 10-07-2024 / 10.07.2024 przy tej samej rzeczywistej wartości ma nadal ten sam token. Dodatkowej kategorii tokenu DATE nie tworzyć: obecne daty to NUMER. Minimalny punkt naprawy pipeline_core.TokenAllocator (assign/allocate/register muszą dawać spójny klucz); layers/amount.py tylko gdy potrzebna jest pewna informacja o typie, bez drugiego alokatora.
2. BOUNDARY: Podmiana NER/wariantów tylko dla całego, samodzielnego spanu zgodnego z tekstem, z granicami odpornymi na polskie litery i łącznik; nigdy wewnątrz innego słowa, istniejącego tokenu, emaila, nazwy czy pełnej firmy. Wyrazy sąsiednie i interpunkcja nie mogą być skasowane. Wzorce adresowe muszą mieć bezpieczną lewą granicę bez utraty zwykłych poprawnych adresów. Nie wystarczy samo użycie regex \b przy spanach kończących się znakiem nie-alfanumerycznym; najpierw wykazać zachowanie na kontrpróbach.
3. LITERAL SPAN: Dla każdego nowo zastąpionego JEDNEGO wystąpienia jego surowa wartość (spacje/tab) odpowiada wartości rejestrowanej przez alokator. Nadal dopuszczamy wcześniejsze zdefiniowane łączenie WIELU zapisów tej SAMEJ wartości pod jednym tokenem, więc takie warianty Przywróć mogą odtworzyć reprezentację mapy zamiast dokładnie każdego zapisu. To znane K2, jawnie NOT_FIXED; w tym Tasku wymagane jest przywrócenie znaczenia i brak pogorszenia wierności, a 1:1 sprawdzamy dla odrębnych literalnych wartości. Nie obiecywać równocześnie 1 tokenu na dwa różne zapisy i odtworzenia obu znak w znak bez nowego formatu mapy.
4. Brak regresji OSOBA/NER-MULTILINE, FIRMA-BARE-REPEAT, Newline-Crossing, Guard i fail-closed; nie zwiększać liczby nowych PII w niezamaskowanym tekście, zwłaszcza nie akceptować wyniku wyłącznie dlatego, że Guard go blokuje.

## Minimalny szew
W pierwszej kolejności zreprodukować D1/D2/D3 na HEAD main i ustalić ich pierwszego właściciela. D1: pipeline_core.py, opcjonalnie amount.py. D2: ner_adapter.py i address.py. D3: ner_layer.py, bez globalnego whitespace rewrite. Wykorzystać istniejący alokator i mechanizmy span/NER; NIE dodawać drugiego procesu anonimizacji. ner_layer.py ma już ok. 601 linii, więc ratchet: bez przyrostu albo STOP i decyzja właściciela, nie obcinać testów na siłę.

TASK_SCOPE:
- backend/pipeline_core.py
- backend/layers/amount.py
- backend/layers/ner_adapter.py
- backend/ner_layer.py
- backend/layers/address.py
- backend/tests/test_map_fidelity.py

OUT_OF_SCOPE: backend/pipeline_new.py, backend/output_guard.py, API/UI, warstwy OCR/normalizacja (osobny SHADOW-NORMALIZE), profil/trie poza istniejącą semantyką alokatora, zmiana TokenAllocator API publicznego bez prechecku, K2 osobne literalne warianty tej samej wartości, fail-closed S3 (odrębny brief), nowy parser dat/kwot dla całej aplikacji, nowe modele i prawdziwe PII. Jeśli utrzymanie bezpiecznego rozróżnienia D1 wymaga osobnego rodzaju/źródła w kolejnym ownerze, Codex: STOP i minimalny aneks TASK_SCOPE przed implementacją, bez obejścia testu.

## Testy falsyfikujące / odbiór
- RED→GREEN D1: 15.00 zł vs 1 500 zł → inne tokeny i poprawne wartości, 3 700 zł vs 3700 zł → jeden; 2.11.2023 vs 21.1.2023 → różne, 10-07-2024 vs 10.07.2024 → jeden; NIP z i bez myślników zachowuje dedup. Testy na allocator.assign oraz Full/Express tam, gdzie warstwa rzeczywiście działa; kontrola register() i konfliktu tokenów, żadnej zmiany wartości po Przywróć w dwóch RÓŻNYCH wartościach.
- RED→GREEN D2: Nowak/Nowakowska, Sąd/Sądu, prefix „Szpitala ... al.”, token blisko cudzysłowu i końcowej kropki, pełna FIRMA + rdzeń, zdanie z drugim tokenem. Zero tokenu wewnątrz wyrazu, zero jawnego ogona PII, prawidłowy token parsowalny przez aktualny TOKEN_RE i mapa nie zawierająca części innej encji.
- RED→GREEN D3: kontrolowany prawdziwy span NER z podwójną spacją/tab w osobie; podmiana pełnego literalnego tekstu, mapa zachowuje jego postać, Przywróć 1:1 dla pojedynczego zapisu. Dodatkowy test prawdziwego Full z NER, bez maskowania nowych osób w Express na siłę.
- Regresje: existing test_ner_multiline.py, test_layers.py, test_text_limit_15k.py, standardowa suite; również lokalne porównanie 178 dokumentów przez DZIAŁAJĄCY /preview na identycznym zbiorze/hashach: 32 sklejone → 0, semantyczne kolizje 0 → 0, prawidłowy dedup nie zanika, Guard/FP/Przywróć przed i po. Brak dostępu do zbioru = NOT_RUN, a nie zgłoszony PASS pomiaru. Jawnie uruchomić nowy test (poza pytest.ini).
- Odbiór wymaga D1+D2+D3 + niepogorszenia wcześniejszych poprawnych przypadków i audytu dokładnego SHA. Jeśli punkt D3 wymaga naruszenia limitów, STOP przed rozszerzeniem. Raport tylko agregaty i syntetyki, bez danych klientów.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_core.py --symbol _canonical
- TARGETS: backend/layers/amount.py --symbol apply_amount_layer
- TARGETS: backend/layers/ner_adapter.py --symbol apply_ner_layer
- TARGETS: backend/ner_layer.py --symbol _process_ner
- TARGETS: backend/layers/address.py --symbol _ADDR_RE
- REASON: dwie rodziny błędów — kolizja wartości w alokatorze oraz błędny span/literalne podmiany.
GATE: maksymalnie jeden nowy plik testowy; >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI; pliki historycznie ponad limitem nie mogą rosnąć. Codex najpierw BRIEF_ONLY precheck: ocenić semantyczne daty w NUMER, ryzyko wyjątków/niejednoznaczności, spójny register/assign oraz realność D3 w 601-liniowym ner_layer.py.
