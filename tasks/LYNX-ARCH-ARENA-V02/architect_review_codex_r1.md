# LynxMask Arena v0.2 — ocena Architekta po niezależnym audycie Codexa r1

DATA: 2026-10-19.
STATUS: ARCHITECT_REVIEW / BEZ ZMIAN KODU I GOLD / BEZ MERGE.
ŹRÓDŁA: `tasks/LYNX-ARCH-ARENA-V02/round_01/tests/tests_r1.txt` i niezależny `repro_r1.py` Codexa, audytowane exact SHA `f3e547a0e233a72b4856de1a40bdedb87249a15c`. Kod nowej R2 w `backend/arena_v02.py`; R1 w niezmienionym `backend/arena_sim.py`.

## Ustalenia potwierdzone przez Codexa
- MECHANICS_PASS w badanym zakresie: 40 oryginalnych + 5 nowych testów; strict byte-identical z oryginalną Areną na 42/42; structured niezależne od kolejności kandydatów 42/42; bez naruszeń N1–N4 i odwracalności na zrenderowanych przypadkach.
- Na 35 znanych syntetykach STOP spadły z 9 do 5; poprawnie RENDERED wzrosły z 14 do 18. Nie jest to realna częstość odmów ani produkcyjny pomiar bezpieczeństwa.
- Niezależny atak O2 / H1: tekst `Odbiorca: Jan Kowalski; wzór: Alfa Sp. z o.o.`; kandydaci BASE: OSOBA dla Jan Kowalski i fałszywie szeroka FIRMA obejmująca `Jan Kowalski; wzór: Alfa Sp. z o.o.`. Gold: OSOBA `Jan Kowalski` i FIRMA `Alfa Sp. z o.o.`. R1 STOP; R2 akceptuje fałszywie szeroką FIRMA, zwracając `Odbiorca: FIRMA_001`. To obala trafność hipotezy granic w R2. Poprawny roundtrip NIE ratuje semantycznej poprawności.
- 233 nowe linie kodu i testów >150 = GATE WYMAGA_DECYZJI. Raport r1 pozostaje dowodem i nie wolno go nadpisywać.

## Moje rozstrzygnięcie
1. PRZYJMUJĘ werdykt Codexa: implementacja wierna badanemu kontraktowi, ale R2 w aktualnej formie NIE kwalifikuje się jako bezpieczna polityka arbitra w LynxMask.
2. ODRZUCAM regułę, według której sam sufiks `Sp. z o.o.`, sama końcówka adresu lub sama składnia domeny dowodzą początku i całego zasięgu szerszego spanu. Dowód musi obejmować **typ, lewą granicę, prawą granicę oraz zasadę łączącą wszystkie objęte człony**. Odróżniamy **walidację własności kandydata** od **weryfikacji prawidłowego zasięgu**; pozytywne dowody bez granic nie uprawniają do usuwania innych kandydatów.
3. ODRZUCAM szybki hotfix typu `if ";" in FIRMA: STOP` jako odpowiedź na H1. H1 ma reprezentować całą klasę połykania tekstu, a nie konkretny separator. Doklejanie zakazów na nowe znaki odtworzyłoby dawną walkę regexów.
4. NIE ODRZUCAM idei arbitra z selektywną regułą zawierania. Zmniejszenie liczby odmów na znanych próbach jest mierzalne, ale wariant trzeba badać z niezależnym dowodem ZASIĘGU. Wstępna hipoteza do następnej gry: rozszerzenie FIRMA ponad OSOBA można dopuścić tylko, jeśli istniejący, niezależnie uruchamiany detektor potrafi uwiarygodnić dokładnie [start,end) całej FIRMA, a nie tylko deklarowany sufiks albo pochodzenie `evidence`. Nie jest to jeszcze zaimplementowany kontrakt, ani automatyczne pierwszeństwo FIRMA nad OSOBA.
5. Nie odchodzić od fail-closed produktu: odmowa ograniczona do fragmentu nie oznacza, że wolno wypuścić pozostałe niezamaskowane PII. STOP dokumentu w Arenie jest nadal bezpiecznym punktem odniesienia, chociaż bywa niepraktyczny.

## Dalsze próby, mały kontrolowany etap
A. Zachować R1/R2 v0.2 oraz kod/raport Codexa BEZ ZMIAN. Przekazać CC zamrożony SHA do nowych ataków przeciw **granicom encji**, np. osoby/firmy rozdzielone dwukropkiem, przecinkiem, nową linią, wyrażeniem łączącym; z kontrpróbami prawdziwych nazw z interpunkcją. Atakujący ustala gold przed uruchomieniem.
B. Następny osobny moduł pomiarowy zasila te same arbitry rzeczywistymi candidate spans obecnych detektorów — najpierw syntetyczny tekst z generatorem i gold offsetami, bez OCR. Nie zakładać, że istniejące warstwy można naiwnie uruchomić na oryginale: adapter potwierdza mapowanie albo zwraca ADAPTER_UNSUPPORTED/mapping_error. Następnie niezależne wejścia po OCR (raportowane OSOBNO), na końcu dokumenty bez gold do statystyk konfliktów, a nie jako dowód recall.
C. Dopiero przy identycznych kandydatach badać R2b: **dodatni dowód obu granic** zamiast sufiksowego przyzwolenia. W raporcie: R1/R2/R2b na tym samym gold, STOP, FN, FP/overmask, utrata N1–N4, długość fragmentu przyjętego wobec rozpoznanej struktury. Bez jednoczesnego strojenia Anchor, HerBERT, słowników i arbitra.

## Niezamknięte ryzyka
- Detektor sam może fałszywie wskazać początek i koniec; dwa różne regexy z tą samą heurystyką nie są niezależnymi dowodami. Potrzebna falsyfikacja dowodów, nie tylko liczba głosów.
- `evidence` we współczesnej Arenie jest metadanymi od wejścia. R2 nie może przyjąć tego za dowód, że pełny span został empirycznie sprawdzony.
- Producent syntetycznego gold musi wyznaczać offsety przy generowaniu, a nie wyszukiwać je później po wartości (kolizje nazw w firmach i adresach).
- Wymagana jawna decyzja o progu GATE (>150 l.) przed dalszą rozbudową kodu; wynik MECHANICS_PASS nie stanowi automatycznego przyjęcia zakresu.

WNIOSEK: Arena zrealizowała cel falsyfikacyjny. Codex znalazł przeciwny przykład obalający moje kryterium dowodu FIRMA. Zatrzymujemy R2 jako **celowo obalony wariant porównawczy** i przechodzimy do eksperymentu nad dowodami granic na prawdziwych kandydatach, bez zmiany produkcyjnego LynxMask.
