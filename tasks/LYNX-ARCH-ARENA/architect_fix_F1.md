# LYNX-ARCH-ARENA — rozstrzygnięcie Architekta po Codex r4 / F1

STATUS: ARCHITECT_FIX_GUIDANCE. Nie zmienia zamrożonej oceny v0.1 ani źródłowego kontraktu r2; implementacja tylko przez CC na gałęzi eksperymentu, nowy exact SHA i niezależny audyt Codexa. Nie jest zmianą produktu.
ŹRÓDŁA: Codex `tasks/LYNX-ARCH-ARENA/round_01/tests/tests_r4.txt` i `repro_r4.py` (dokładnie audytowany `4a1cbf093c3f489ef119ba2f0058358b01069da2`), `backend/arena_sim.py` na tym SHA; `tasks/LYNX-ARCH-ARENA/brief.md` N2, A–E.

## Ocena F1
Potwierdzam. `_base` waliduje liczby start/end i typ, ale nie sprawdza granicy wyrazu; `_apply` bez dodatkowej kontroli emituje token bezpośrednio w środku słowa. `Jan Kowalski`, `OSOBA [0,2)` daje `OSOBA_001n Kowalski`; `[1,3)` daje `JOSOBA_001 Kowalski`. To bezsporne naruszenie N2 i MECHANICS_FAIL, nie błąd gold ani tylko słaba heurystyka. Raport Codexa potwierdził je niezależnie od 38 zielonych testów CC.

## Minimalna poprawka tej samej klasy, bez przebudowy
1. Końcowy warunek dopuszczenia do ONE APPLY: dla każdego ZWYCIĘSKIEGO spanu sprawdź granice w oryginalnym Python str, przed jakąkolwiek podmianą. Jeśli początek lub koniec przecina ciąg znaków wyrazu, wynik STOP, `masked=null`, `tokens=[]`, bez ujawnienia źródła w trace/wyjątku. Bez dodawania spacji wokół tokenu — to niszczyłoby N1/Przywróć i jedynie ukrywało błąd.
2. Sprawdzenie granicy nie może zależeć od detektora ani rodzaju tokenu. Dla testu v0.1 ciąg znaków wyrazu obejmuje litery/cyfry Unicode, `_` i znaki łączące (`unicodedata.category(ch).startswith("M")`); unikać cięcia przed/po znaku łączącym (NFD). Sąsiednia interpunkcja, spacja i nowa linia są granicą. Nie domyślać się rozszerzenia OSOBA z samego `Ja`; nie uruchamiać prawdziwego NER.
3. Sprawdzaj **po arbitrażu**, nie tylko przy wejściu BASE. Ucięte `ala@fir` powinno móc zostać zastąpione pełnym kandydatem `ala@firma.pl` z AnchorEngine. Wczesne odrzucenie każdego błędnego BASE zabrałoby Anchorowi zadanie ratunkowe. Weryfikacja na finalnych spanach musi obejmować także sam Anchor, np. `ale\u0301x@firma.pl`: samo `x@firma.pl` nie jest bezpiecznym pełnym e-mailem. Jeśli taka propozycja przetrwa arbiter, STOP zamiast sklejonego tokenu. Nie twierdzić jednak, że STOP naprawił wyciek — to poprawność mechaniki, nie skuteczność ochrony.
4. Kod przyczyny: preferowane jawne `INVALID_BOUNDARY` (nowy techniczny `reason_code` Areny), ewentualnie `INVALID_INPUT` jeśli Codex w prechecku uzna zmianę kodów za zbędną; dla programu i sędziego zawsze deterministycznie i bez echa oryginału. Nie zmieniać `TOKEN_RE`, mapy ani API LynxMask.

## Minimalne próby odbioru CC i niezależne Codexa
- `Jan Kowalski` + OSOBA [0,2), [1,3), [0,3) osobno: dwa pierwsze STOP bez `masked`, trzeci RENDERED z bezstratnym Przywróć.
- Ten sam test przy prefiksie z emoji, polską literą, underscore i NFD/combining mark, obie krawędzie spanu; brak tokenów sklejononych z literami/znakami łączącymi.
- `Kontakt: ala@firma.pl` + niepełny BASE EMAIL obejmujący `ala@fir`: Anchor dołącza pełny zakres, arbiter go przyjmuje, render PRAWIDŁOWY; nie zatrzymywać przypadków, które może uratować Anchor.
- Regresja 16 jawnych CASES r2, 19 ataków CC, sześciu prób własnych Codexa; nie wymagać napraw wszystkich znanych FN/FP/UNEXPECTED_STOP przy F1. Zachować niezależny pomiar MECHANICS i PROTECTION oraz uczciwe liczenie nowego STOP.
- Bez cichej korekty oczekiwanych wartości pod wynik. Raport Codexa r5+ na NOWYM dokładnym SHA, weryfikacja F1 i brak regresji; r4 pozostaje nienaruszony.

TASK_SCOPE:
- backend/arena_sim.py
- backend/tests/test_arena_sim.py

OUT_OF_SCOPE: produkcyjny backend, nowa polityka overlap R2/R3, nowy OCR/NER, zmiana Anchor gramatyki, mapa K2, guard S4, CASES_V01 gold, przepinanie F0a, automatyczny merge.

Kierunek po F1: odrębny eksperyment z realnymi kandydatami z istniejących warstw, mapping_error/ADAPTER_UNSUPPORTED i stałym syntetycznym gold, potem porównanie arbitrów na identycznym wejściu. To nie jest zakres aktualnej poprawki.
