# Brief — LYNX-EMAIL-LOCALPART-OCR

STATUS: BRIEF_ONLY. Codex precheck → CC review → CC implementation → Codex audit exact SHA → OWNER merge.
PRODUCT_TRUTH: arch/spec.md S1–S5; BOARD.md LYNX-EMAIL-LOCALPART-OCR, LYNX-THREAT-MODEL; tasks/LYNX-T11-TEXT-FIDELITY/round_01/implementation/DELIVERY.md § Zgłoszenia. OWNER proponuje kolejność wycieki → PUBLIC-DATA-TESTS; wybór Architekta: najpierw ten przypadek, bez zgody na merge.

WADA: W pełnym trybie i Express rozbity przez OCR adres «anna. nowak@example.pl» jest wykrywany jedynie od «nowak@», a «anna.» pozostaje jawne. layers/ner_adapter.py naprawia lokalną część dopiero PO warstwie contact. To częściowy wyciek S1, którego zielona suita nie wykrywa.

CEL: cały adres z wewnętrzną spacją OCR w lokalnej części (po kropce) staje się JEDNYM EMAIL_NNN; reverse_map zawiera pełen surowy span potrzebny do Przywróć. Nie może zostać jawny prefiks ani zagnieżdżony token. Reszta wejścia, w tym kropka kończąca zdanie, odstępy i kolejna linia, pozostaje bez zmian.

OWNER / SZEW: istniejący backend/layers/contact.py i jego _EMAIL_OCR_RE / apply_contact_layer. Preferować punktowe dopasowanie kompletnego e-maila w contact. NIE przesuwać globalnie normalizatora lub warstw. Zachować regułę T07 (pełna encja albo brak dopasowania, fallback ostatni) oraz T11 (brak globalnego sklejania zdań).

TESTY MINIMALNE:
1. Reproduktor «Kontakt: anna. nowak@example.pl. Termin płatności.»: po contact i w obu pipeline'ach cały adres pod jednym EMAIL_NNN, pełny oryginalny zapis w reverse_map, «anna.» niejawne, brak tokenów w wartościach mapy. Symulowane Przywróć (audyt/unmask_sim.py) ma odtworzyć wejście znak w znak, o ile wcześniejsza normalizacja nie zmodyfikowała wejścia (osobne wskazanie, nie pozorne PASS).
2. Dodatnie: zwykły e-mail bez spacji, spacja przy @, spacja przy TLD. Ujemne: «Kontakt. jan@example.pl», «Podpisano. Jan@example.pl», «example.pl. Termin», kropka/nowa linia poza e-mailem. Nie pochłaniać sąsiedniego zdania.
3. Test T07: 15 cyfr w lokalnej części poprawnego e-maila pozostaje w EMAIL_NNN, niezależne 15 cyfr jest NUMER_NNN; brak zagnieżdżonej mapy. Testy regresyjne IBAN/NRB, recepty i Guard nadal poprawne.
4. Test warstwy w backend/tests/test_layers.py i pion w backend/tests/test_audyt_2026_10.py. Uruchomić jawnie oba pliki (test_layers.py nie jest zbierany przez domyślne pytest.ini) oraz standardową suitę. test_audyt blisko limitu 600 linii: nie rozbudowywać go bez potrzeby. Raport zawiera dokładne SHA, PASS/XFAIL i dowód przed/po.
5. Pomiar audyt/engine_quality.py tylko na identycznym digest, ale nie traktować braku tej próbki w M1 jako potwierdzenia naprawy. Bez rzeczywistych danych i bez logowania PII.

TASK_SCOPE:
- backend/layers/contact.py
- backend/tests/test_layers.py
- backend/tests/test_audyt_2026_10.py

OUT_OF_SCOPE: ner_adapter, ocr_normalizer, pipeline_new, fallback, financial/IBAN-O2, Guard, TOKEN_RE/S2, UI, nowe parsery, przebudowa kolejności warstw, profile, nowe pliki i dane rzeczywiste. Gdy kontaktowy owner nie wystarcza, Codex ma zgłosić wąski finding; nie poszerzać samowolnie TASK_SCOPE.

PASS: reproduktor pełnego e-maila bez jawnego fragmentu i z prawidłową mapą działa w full/Express; kontrola Przywróć, brak regresji T07/T11 i brak osłabienia S3/S4. Wynik z blokadą nie jest sukcesem maskowania.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/layers/contact.py --symbol _EMAIL_OCR_RE
- TARGETS: backend/layers/contact.py --symbol apply_contact_layer
- REASON: istniejący właściciel detekcji całych adresów.
GATE: zero nowych plików; >150 zmienionych linii lub ratio >5:1 → WYMAGA_DECYZJI. Precheck Codexa bez implementacji.

## Doprecyzowanie granic po audycie r2/r3 — PROPOZYCJA ARCHITEKTA, DO PRECHeckU
Źródła: `round_01/tests/tests_r2.txt` i `tests_r3.txt`; sprawdzana dostawa `fc75f1410c865acaa74e4ca2c9058aa81b16b5ed`. OWNER wybrał doprecyzowanie granic z Architektem, ale nie zaakceptował jeszcze nadmaskowania słowa ani limitów bieżącej dostawy. Ten rozdział zastępuje niezgodne z nim oczekiwania w pierwotnych TESTACH MINIMALNYCH pkt 2. NIE jest PASS dla `fc75f14`.

**Reguła kosztu niejednoznaczności.** Dla zapisu `<słowo>.[1–3 spacje/taby]<reszta-localpart>@<domena>` przyjąć priorytet ochrony PII: objąć jednym `EMAIL_NNN` również słowo przed kropką, jeżeli nie da się odróżnić OCR-localpart od końca zdania wyłącznie w tym lokalnym szwie. Dotyczy liter małych, WIELKICH i mieszanych w tym jednym słowie; zakres wzorca pozostaje ograniczony do istniejącej składni adresów ASCII. Akceptowany koszt: **nadmaskowanie najwyżej tego jednego sąsiadującego słowa i kropki**, np. `Prosimy o kontakt. jan@example.pl` może dać `Prosimy o EMAIL_001` z mapą `EMAIL_001 → kontakt. jan@example.pl`. To nie jest utrata tekstu: Przywróć musi oddać wejście znak w znak. Ochrona przed częściowym wyciekiem ma pierwszeństwo przed zachowaniem tego jednego słowa w tekście przekazanym AI.

**Bezwzględne granice (K1 Codexa r4):** nowa heurystyka `słowo.[1–3 spacje/taby]localpart@...` może dołączyć **najwyżej jedno słowo przed kropką WYŁĄCZNIE W TYM SAMYM WIERSZU**. Nie może połączyć słowa z poprzedniego wiersza przez `\n`/`\r`, pochłonąć słów lub kropki **po** pełnym adresie ani modyfikować zdań bez e-maila po prawej stronie. **To nie jest zakaz istniejącego OCR-newline WEWNĄTRZ e-maila przy samym `@`:** obowiązujące rozpoznanie `jan@\nexample.pl` oraz `jan\n@example.pl` (jak dotąd, do 2 białych znaków przy `@`) pozostaje działające i daje jeden `EMAIL_NNN`; nie wolno go usunąć w ramach rozszerzenia localpart. Wartość w mapie dla takich *wcześniej obsługiwanych* przypadków przy `@` może pozostać kanoniczna, zgodnie ze znanym F3 — nie udawać nowej gwarancji odtworzenia OCR-newline 1:1. Dla nowej heurystyki z odstępem po kropce nadal wymagać pełnego surowego spanu i Przywróć 1:1 w izolowanym przypadku. Żadnych zagnieżdżonych tokenów ani globalnego sklejania/normalizacji. Przypadki z 4+ odstępami lub kilkoma rozbiciami lokalnej części NIE są w tym wąskim zadaniu naprawione automatycznie: jeśli pozostaje fragment jawny, zgłosić jawne ograniczenie i osobny finding, nie przedstawiać jako PASS całej klasy OCR.

**Minimalna zmiana testów po nowym rozstrzygnięciu:**
- Pozytywy full + Express: `anna. nowak@example.pl` (1 spacja), `ANNA. NOWAK@example.pl` (CAPS, 1–2), `Anna. Nowak@example.pl` (mixed), `anna.   nowak@example.pl` (3 spacje), zwykły adres bez OCR. Wszystkie: jeden `EMAIL_NNN`, pełny surowy span w mapie, brak jawnego prefiksu, wierne Przywróć w izolowanym przypadku.
- Kontrolowane nadmaskowanie: `Prosimy o kontakt. jan@example.pl` oraz `Podpisano. Jan@example.pl` — dopuszczony token na jedno poprzedzające słowo+kropkę i pełen e-mail, mapa dokładna, Przywróć 1:1; **nie oczekiwać już zachowania tych słów jawnie**. Porównać wyniki przed/po na exact SHA.
- **K1 — osobne przypadki newline:** `Kontakt.\njan@example.pl` nie łączy poprzedniego słowa z adresem; **pozytywna regresja** `jan@\nexample.pl` i `jan\n@example.pl` zachowuje rozpoznawanie całego e-maila jednym `EMAIL_NNN` w full i Express (mapa może zachować dotychczasowy kanoniczny zapis przy `@`, patrz F3). Pozostałe negatywy: `Kontakt. nie podano adresu` bez e-maila nienaruszone; `jan@example.pl. Termin płatności` nie wciąga `Termin`. OCR przy TLD, 15-cyfrowa część lokalna i T07 fallback bez regresji.
- W `backend/tests/test_audyt_2026_10.py` obecnie obowiązuje limit 600 linii — testy dodatkowych wariantów preferować w istniejącym `backend/tests/test_layers.py`, bez sztucznego usuwania innych testów. Produkcja nadal wyłącznie `layers/contact.py`. S3/S4 bez zmian, brak akceptacji „blocked” jako prawidłowego maskowania.

**Przekazanie:** Codex robi precheck WYŁĄCZNIE nowych granic (czy jeden regex/istniejący owner pozwala osiągnąć te warunki bez nowych strat), a po jego ocenie CC wąsko koryguje `fc75f14` i Codex audytuje nowe exact SHA. Jeśli zawężenie do jednego słowa i 1–3 odstępów nie jest realizowalne bez większego kosztu, STOP i krótka decyzja OWNERA; bez nowego subsystemu. Merge nieautoryzowany.

**KOREKTA K1 Codexa r4** (`round_01/tests/tests_r4.txt`, poprzedni brief SHA `ec49f3fb38a33e6d8b27f72f3fa26bb9d029bc7b`): rozdzielono zakaz dołączania słowa przez newline od zachowania istniejących rozpoznań OCR-newline przy `@`. To korekta zakresu, nie PASS dostawy `fc75f14` ani decyzja OWNERA o zaakceptowaniu dokładnego kosztu nadmaskowania i wyłączenia 4+ odstępów. Codex: wąski recheck wyłącznie K1, bez ponownego audytu całego briefu.
