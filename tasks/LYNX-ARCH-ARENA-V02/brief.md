# LYNX-ARCH-ARENA-V02 — dwie polityki arbitra na jednym wejściu

STATUS: EKSPERYMENTALNA IMPLEMENTACJA AUTORSTWA CHATGPT; NIE produkt / NIE MERGE / NIE AUDYTOWANE PRZEZ CODEX.
BRANCH: experiment/lynx-architecture-arena-v02. Bazą jest zaakceptowana przez Codexa Arena v0.1.2 z zamkniętym F1, na osobnej gałęzi. NIE MODYFIKUJEMY starych plików, testów ani wyników CC.

## Co nowego
- Nowy backend/arena_v02.py importuje niezmienione arena_sim.py. Nie duplikuje lub nie stroi Anchor/Guard/detektorów. Używa dokładnie tych samych base_candidates; nie korzysta z gold w runtime.
- Wejście JSONL: {"text":"...","base_candidates":[...],"mode":"full","policy":"both"}.
- policy: "strict" uruchamia niezmienioną v0.1.2, "structured" — testową politykę R2, "both" porównuje te dwie decyzje. "both" zwraca pola strict, structured i changed; porównanie NIE jest werdyktem o bezpieczeństwie.
- R2 dopuszcza całkowite zawieranie OSOBA przez FIRMA wyłącznie gdy większy span kończy się dosłowną rozpoznaną formą prawną; przez ADRES z literalnym "ul." i końcowym członem wyglądającym na numer budynku; przez EMAIL z literalnym @ i częścią domeny z kropką lub przecinkiem. To są **hipotezy dowodów**, a nie prawdziwa walidacja bycia firmą, adresem czy e-mailem. Wszystkie inne różnotypowe konflikty nadal STOP; każdy częściowy overlap STOP. Dla takich samych kategorii obowiązuje wcześniejsza reguła arbitra.
- Argument evidence/source detektora NIE służy R2 za dowód struktury; tekst oryginału jest analizowany ponownie przez sprawdzalną mini-regułę. Zgodnie z filozofią Anchor, to nie jest powtórzenie walidacji OCR/sumy kontrolnej.
- Zachowujemy N1–N4, WORD_BOUNDARY przed ONE APPLY, tę samą próbkę z Atrapy Guarda. Nie naprawiamy pojedynczych fałszywych kotwic ani nie zmieniamy po drodze gramatyki @ i ul.
- Obie polityki mogą być jednocześnie błędne. Proste zamknięcie osoby wewnątrz FIRMA z końcową formą prawną NIE daje automatycznie poprawnego złotego spanu. Testy z niezależnym gold muszą to falsyfikować.

## Kluczowe niezależne próby
- X09: "ul. Jana Kowalskiego 5" + OSOBA "Jana Kowalskiego": R1 STOP, R2 ADRES całość.
- X10: "Kowalski i Wspólnicy Sp. z o.o." + BASE FIRMA oraz BASE OSOBA Kowalski: R1 STOP, R2 FIRMA całość.
- A10: "jan.kowalski@firma.pl" + BASE OSOBA w localpart: R1 STOP, R2 EMAIL całość.
- Negatywne: "Kowalski Projekt XYZ" bez formy prawnej — dalej STOP; ulica z nazwiskiem bez numeru — dalej STOP; częściowe nałożenia dwóch osób — STOP; ucięte "Ja" w "Jan" — STOP/WORD_BOUNDARY.
- Test starego strict uruchamianego nowym entrypointem ma dać bajtowo równy JSON co oryginał; kolejność kandydatów nie może zmieniać R2.

TASK_SCOPE:
- backend/arena_v02.py
- backend/tests/test_arena_v02.py

## Jak uruchomić
cd backend
py -3 arena_v02.py
py -3 -m pytest tests/test_arena_v02.py -q

Program czyta JSONL ze standardowego wejścia. Nie czyta datasetu, nie ma API, internetu, wywołań LLM ani dostępu do zawartości profilu. Cała nowa implementacja to dwa pliki; stara Arena i F0a bez zmian.

## Co wymagam od Codexa przed jakimkolwiek wnioskiem
1. Uruchom oryginalne 40 testów starej Areny oraz nowe testy w osobnym procesie na exact SHA tej gałęzi. Nie przyjmuj moich prognoz za oracle.
2. Sprawdź 16 oryginalnych cases i 19 ataków CC przez strict i structured na IDENTYCZNYCH kandydatach; podaj zmianę liczby STOP, osobno FN/FP i roundtrip wobec gold.
3. Stwórz nowe, nieznane autorowi przypadki, zwłaszcza fałszywa nazwa firmy zakończona "Sp. z o.o.", sprzeczne spany trzech detektorów, różne Unicode i sklejone e-maile.
4. Wykryj przypadki, w których R2 obniża liczbę odmów kosztem fałszywego połknięcia większego zakresu. Jeden nowy FN lub fałszywe scalenie nie jest sukcesem.
5. Zgłoś pełny wymóg GATE (kod nowej wersji >150 dodanych linii), bez uznawania za zatwierdzoną zmianę produkcyjną. Oryginalne decyzje o rozmiarze pierwszej Areny nie zastępują kontroli tej gałęzi.

## Cel i dalszy kierunek
Wynik R1 vs R2 to **tylko porównanie polityk arbitra na zgłoszonych kandydatach**. Nie mierzy skuteczności faktycznych detektorów. Następny osobny krok: generator.py z niezależnymi offsetami gold i adaptery rzeczywistych warstw, z jawnym mapping_error / ADAPTER_UNSUPPORTED. Nie włączać HerBERT, OCR i nowych słowników naraz.
