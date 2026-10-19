# LYNX-ARCH-ARENA — ocena Architekta po pierwszym wykonaniu i atakach CC (19.10.2026)

STATUS: ARCHITECT_REVIEW — wnioski z raportu CC, nie niezależny PASS kodu ani nowa zgoda na implementację v0.2.
WEJŚCIA: `tasks/LYNX-ARCH-ARENA/round_01/implementation/DELIVERY.md`, `tasks/LYNX-ARCH-ARENA/attacks/attacks_cc_r1.py`, `backend/arena_sim.py`, `backend/tests/test_arena_sim.py`, BOARD: LYNX-ARCH-ARENA, ARENA-REAL, ARENA-VS-REAL. Kod do audytu na exact SHA `4a1cbf093c3f489ef119ba2f0058358b01069da2` (wg CC). Obecny main nie jest zmieniany.

## Werdykt wstępny

Hipoteza "kandydaci na oryginale → rozłączność → jeden APPLY" NIE została obalona testami CC. Została obalona moja produkcyjna intuicja, że **każde nakładanie różnych typów uzasadnia odmowę całego dokumentu**. W tej wersji to jawna, zbyt konserwatywna polityka arbitra, a nie własność konieczna nowej architektury. To ograniczenie mechaniki symulatora, nie dowód jakości realnych detektorów.

CC raportuje: 16/16 zgodność z przewidywaną mechaniką; skuteczność ochrony w tych 16: 9 PASS, 5 FAIL (A06/A07/A11/A15/A16), 2 SAFE_REFUSAL; 38 testów; na 19 atakach: 5 PASS, 8 FAIL, 5 UNEXPECTED_STOP, 1 SAFE_REFUSAL. **Wszystkie te wartości to deklaracja CC**, przed niezależnym wykonaniem testów przez Codex. Pomyślna zgodność z przewidzianą porażką oznacza mechanizm działający zgodnie z kontraktem, NIE ochronę.

## Co falsyfikuje każda klasa

1. **Nadmierne STOP:** X01 lista e-maili bez spacji; X02 znak @ użyty poza e-mailem; X09 nazwisko w nazwie ulicy; X10 nazwisko w nazwie firmy; X18 nakładające się proponowane osoby z listy. Pięć przypadków z 19 to testy celowo skonstruowane do zaatakowania tej reguły, a NIE miara częstości w dokumentach. Nie wolno z tego wyciągać procentu realnych odmów.
2. **Reguły zasięgu Anchor:** X03/X04/X15 obcięte e-maile po OCR lub przy łączącym znaku Unicode; X05/X06/X07/X08 adresy i warianty prefiksu; X12 @uchwyt maskowany jak EMAIL. To błędy przyjętej hipotezy języka kotwic, nie koniecznie arbitra. A07 osierocony kod i miasto po poprawnym początku adresu nadal są poza kontrolą samego Anchor.
3. **Mocne strony niezmienników:** gdy spany są poprawne i rozłączne, One Apply może zachować oryginał poza spanami i 1:1 Przywróć dla dosłownych wystąpień. Codex musi sprawdzić te twierdzenia na niezależnych przypadkach, w tym z nieoczekiwanym duplikowaniem wartości oraz NFD.
4. **Guard:** „dron” wskazuje niektóre resztkowe numery, ale nie wykrywa A07 ani części nieobsłużonych prefiksów ulic. Sygnalizacja po błędzie nie czyni maskowania skutecznym. To atrapa, nie dowód zachowania produkcyjnego Guarda/S4.
5. **Wewnętrzna decyzja CC w D.ii:** Anchor w całości zawarty w szerszym BASE tego samego typu zostaje odrzucony jako zakryty. Sensowna hipoteza, lecz Codex musi sprawdzić, czy szerszy BASE nie zawiera przypadkowo danych innego typu lub fragmentu zwykłej prozy.

## Propozycja dalszej falsyfikacji, BEZ ZMIANY v0.1 przed audytem

**GATE 1 — niezależny audyt v0.1:** Codex ma uruchomić źródło na exact SHA `4a1cbf0`, jawnych 16 i 19 próbach CC oraz co najmniej 5 nowych (2 nieznane CC), zweryfikować sędziego, N1–N4, źródłowe indeksy i brak gold/LLM w runtime. Nie podmieniać kodu, prognoz ani raportów. Szczególnie sprawdzić X01 i X18, gdzie proste poszerzenie zasięgu może ukryć niezależną drugą encję.

**GATE 2 — REAL jako tylko adapter pomiarowy:** uruchomić stare detektory na PRAWDZIWYM wejściu do ekstrakcji bez zmian produktu. Ważne: warstwy nie są automatycznie niezależnymi funkcjami `find`; mogą zależeć od wcześniejszej normalizacji, trie i już zamienionego tekstu. Każdy adapter musi dowieść zgodności spanu z oryginałem. W innym wypadku oznaczyć ADAPTER_UNSUPPORTED / mapping_error, a NIE "brak kandydata". Najpierw zbiór jawnych syntetyków + mały dev sample, dopiero później 178 dokumentów lokalnych. Zależności profilu i ekstrakcji utrzymać identyczne; żadne PII, raw spany i nazwy plików klientów nie trafiają do repo/logów. Zbiór bez gold nie może sam poświadczyć recall.

**GATE 3 — porównanie wariantów arbitra bez rozszerzania reguł detekcji w tym samym kroku:**
- R1: obecny, celowo nadmiernie konserwatywny STOP całego dokumentu (baseline).
- R2: reguła zawierania INNEGO typu, ale tylko przy udokumentowanej silnej kotwicy obejmującej całą encję (np. forma prawna zweryfikowana na FIRMA, składnia ADRES z prefiksem i granicami), a nie "dłuższy wygrywa". Jeżeli brak dowodu, konflikt pozostaje. Wola profilu nie może automatycznie nadpisać każdej innej encji.
- R3: stan NIEPEWNY ograniczony do fragmentu oraz przekazanie do niezależnego ostrzeżenia/oceny. To wyłącznie hipoteza do eksperymentu; nie można wydawać nieprzetworzonej reszty z PII ani uznać regionalnego STOP za bezpieczny produkt bez dokładnego kontraktu.
Porównać w tym samym harness na tych samych kandydatach: odsetek STOP, odsetek połykania dwóch encji, FN/FP tam, gdzie istnieje niezależny gold, odwracalność, czas. Nie zmieniać jednocześnie arbitra, słowników, modeli i źródeł danych, bo wynik nie będzie przypisywalny jednej przyczynie.

**GATE 4 — dopiero potem kolejne klocki K1–K5:** regex, profil, SpaCy; HerBERT i słowniki Mobile jako osobne kolejne przebiegi ze stałym sędzią. Porównania wyłącznie względem silnika bazowego nie mogą przesądzać, który model jest poprawny: istniejący pipeline ma udokumentowane FN/FP i przepisuje tekst. Potrzebny syntetyczny niezależny gold oraz osobny holdout. HerBERT dodatkowo mierzyć na CPU maszyny docelowej.

## Porównanie z istniejącym LynxMask (LYNX-ARCH-ARENA-VS-REAL)

CC zapisał w BOARD, że bazowy /preview przetwarza wszystkie 5 przypadków UNEXPECTED_STOP Areny, ale dla części zmienia tekst (X02) albo rozbija jedną nazwę firmy (X10). Raportuje również **podejrzane nowe wycieki w starym pipeline**: adresy z uszkodzonym/nietypowym numerem (A04/A09/A16/X06/X16), e-mail z polską literą/Unicode NFD (A13/X15), "Dz. U." jako ADRES i zmianę białych znaków wokół @. Na obecnym etapie to ustalenia CC zapisane w BOARD, nie niezależny audyt dokładnego SHA. Przed oznaczeniem SAFETY_PRIVACY/FAIL należy wykonać celowany reproduktor na wskazanym main oraz sprawdzić granice tokenu, a nie tylko jego obecność. Naprawy starego silnika i przebudowa Areny to odrębne zadania, bez mieszania zakresów.

## Decyzje Architekta

- ODRZUCAM jako domyślną przyszłą politykę arbitra: STOP całego dokumentu przy KAŻDYM częściowym overlap.
- ODRZUCAM równie bezwarunkową alternatywę: "szerszy span wygrywa" dla każdego typu.
- ZACHOWUJĘ wymóg: detektor daje kandydata i dowody, arbiter nie ufa kolejności warstw, jedna podmiana na oryginale; Anchor szuka resztek i NIE powtarza checksum z silnika bazowego.
- Na razie NIE zatwierdzam R2/R3 dla produktu. Najpierw pomiar częstotliwości i błędów przy rzeczywistych sygnałach i niezależne sprawdzenie pierwszej dostawy przez Codex.
- F0a (osobna gałąź) pozostaje niezależny, a v0.1 Areny zamrożony do audytu. Nowy brief v0.2 po decyzji o zakresie, nie teraz.

ZAKAZ: wprowadzania zmian do `backend/arena_sim.py` lub przypadków r1 przed audytem dokładnego SHA, przepychania eksperymentu do API, odkładania raw PII w repo i utożsamiania przebiegu bez gold z certyfikacją bezpieczeństwa. 
