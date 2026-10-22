# LYNX-GUARD-RESIDUE — doprecyzowanie OWNERA dla CC (22.10.2026)

Powiązane z zatwierdzonym briefem v2 `52d83580c4209fbf578f54e11a2dcd23cc27acdc` i PASS PREIMPLEMENTATION Codexa r4 `93c656cc037d9ca1a05bfa61f1bf53874cfa4e99`. Ten dokument wyjaśnia odniesienie do Mobile; **nie rozszerza R1–R5, nie zmienia akceptowanego kontraktu i nie uruchamia implementacji**.

**Mobile to wzór zachowania interfejsu, a nie źródło kodu/reguł rozpoznawania Guarda.** Przejmujemy: lista konkretnych ostrzeżeń RED/YELLOW, osobne `Zakryj` lub `Zostaw` dla każdej pozycji, blokada zwykłego zapisu/kopii/eksportu do rozstrzygnięcia całości. Nie przenosić z Mobile jego skanera, progów, słowników ani heurystyk generujących masowe, przypadkowe ostrzeżenia.

OWNER wskazuje problem Mobile: pokazuje do oceny dużo „śmieci”, co jest uciążliwe i zachęca do bezrefleksyjnego `Zostaw`. Desktop ma wykorzystywać rozpoznane przez CC klasy pozostałości R1–R4 oraz dodatkową R5 (nazwy firm), istniejące sygnały z własnego silnika i wyłączenia z briefu. Samo słowo z wielkiej litery, zwykła fraza biurowa czy przypadkowy ciąg znaków nie jest wystarczającą podstawą alertu bez wiarygodnej przesłanki. Nie należy też wyciszać rzeczywiście podejrzanych resztek tylko po to, aby zmniejszyć liczbę ostrzeżeń.

**W odbiorze liczą się dwie cechy jednocześnie:** wykrycie reprezentatywnych jawnych pozostałości i użyteczna, niezaśmiecona lista pytań na typowych polskich dokumentach biurowych. Dedupikować to samo wystąpienie, nie pokazywać fragmentów już zamaskowanych, zachować kontekst i czytelny powód. Diagnostyka CC z 19–21.10 jest punktem odniesienia; nie zlecać ponownie eksperymentów rozpoznawczych na etapie szacunku.

**Następny krok CC:** wyłącznie krótka estymacja zakresu implementacji na istniejących ownerach (pliki, orientacyjne linie, ryzyko lawiny alertów). Nie kopiować Guarda Mobile i nie pisać jeszcze kodu. Po formalnej zmianie frozen S4/lock oraz zatwierdzeniu kosztu przez OWNERA — realizacja i audyt na exact SHA.
