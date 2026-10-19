# LYNX-ARCH-ARENA — gra falsyfikująca architekturę, v0.1

STATUS: ARCHITECT_BRIEF / BRIEF_ONLY. Architekt ustala reguły i prognozy; CC implementuje i atakuje; Codex niezależnie uruchamia i sprawdza exact SHA; OWNER decyduje o przeniesieniu zasad do produktu.
BRANCH: experiment/lynx-architecture-arena — tylko eksperyment, bez merge.
ŹRÓDŁA: arch/spec.md S1–S5; tasks/LYNX-ARCH-CANDIDATES/architect_assessment.md i brief F0a (F0a bez zmian); tasks/LYNX-ARCH-ARENA/CASES_V01.md.
OWNER_INPUT: 19.10.2026 — Architekt przygotowuje symulator; CC pisze program i szuka ataków; Codex sprawdza, czy wynik rzeczywiście liczy kod, nie Architekt. Zgoda na eksperyment, NIE na nową ścieżkę pseudonimizacji.

## Role i antyoszustwa
Obrońca to deterministyczny program Python, bez modeli/API/sieci i bez podpowiedzi LLM w czasie testów. Wynik zależy TYLKO od wejścia i wersji kodu. CC przygotowuje implementację oraz nowe ataki syntetyczne, ale nie może zmieniać oczekiwanej odpowiedzi, by zaliczyć swój kod. Codex po zamrożeniu exact SHA samodzielnie uruchamia program w osobnym procesie, niezależnie sprawdza złote spany oraz opracowuje co najmniej pięć nowych testów (minimum dwa nieujawnione CC przed zamrożeniem). Nie uznaje dokumentacji lub odpowiedzi Architekta za wykonanie programu.

## Interface, jedna linia JSON na przypadek
Uruchomienie: cd backend && py -3 arena_sim.py. STDIN JSONL, stdout JSONL, bez dodatkowych komunikatów. Python stdlib; moduł NIE jest importowany przez pipeline/API.
WEJŚCIE: {"text":"Kontakt: ala@firma.pl","base_candidates":[{"start":9,"end":21,"kind":"EMAIL","source":"EmailEngine","evidence":["FORMAT"]}],"mode":"full"}
start/end są półotwarte, w indeksach oryginalnego Python str. Base candidates to WYNIKI fikcyjnych silników dostarczone przez atakującego. Pusty zbiór znaczy, że nic nie wykryły; simulator nie może sobie dopowiadać bazowej detekcji. Kind korzysta z istniejących kategorii tokenów. Obrońca nie otrzymuje gold, expected, target ani case_id; żadnego otwierania CASES_V01.md ani testów podczas działania.
WYJŚCIE: {"status":"RENDERED"|"STOP","masked":tekst_lub_null,"tokens":[{"token":"EMAIL_001","kind":"EMAIL","start":n,"end":n,"original":"..."}],"trace":[{"phase":"base|anchor|arbiter|guard","kind":"EMAIL","start":n,"end":n,"decision":"..."}],"reason_code":kod_lub_null,"guard_flags":[...]}.
Przy STOP masked=null i tokens=[]; trace zawiera tylko metadane (typ, indeks, klasa decyzji), bez surowych danych; nie ujawnia tekstu wejścia w wyjątku. Żadne pole status nie oznacza bezpiecznego wyniku gotowego do wysłania AI. Semantyka formatów i nazwy reason_code mają być stabilne i opisane przy implementacji.

## Mechanika — bez „inteligentnych” wyjątków pod testy
A. BASE. Sprawdź 0 <= start < end <= len(text), dozwolony kind, jednoznaczność granic, token injection i konflikty. Ten sam span/typ z dwóch silników scala dowody bez ich podwójnego liczenia. Różne typy na tym samym spanie lub częściowy overlap => wstępny konflikt. Silnik nie zmienia tekstu.
B. ANCHOR. Widzi cały ORYGINAŁ + mapę wstępnie przyjętych spanów (nigdy tekst już podmieniony). Szuka niezakrytych kotwic @ i samodzielnego ul., ale także podejrzanych resztek obok częściowo rozpoznanego e-maila/adresu. Nie waliduje ponownie email-formatu, sumy cyfr czy numeru budynku: podejrzewa uszkodzenie OCR. Zwraca EMAIL/ADRES Candidate z dowodem ANCHOR_AT/ANCHOR_UL. Kotwica sama w sobie NIE jest dowodem nieomylności — błędy FP liczy sędzia.
C. Zasięg ANCHOR v0.1: dla @ rozszerz lokalną frazę w lewo i prawo w TYM SAMYM wierszu; toleruj , zamiast . w domenie i jedno rozdzielenie " .pl" przy końcu; granice etykiet, ; i newline są twarde. Dla ul. przejmij do 1–3 sąsiednich członów ulicy/numeru, koniec na przecinku, średniku, dwukropku lub newline. To testowalna hipoteza i cel ataków, NIE zamrożona gramatyka produktu. Nie podbieraj kolejnego PESEL, firmy ani drugiej osoby. Nie stosuj arbitralnego limitu długości w znakach zamiast granic frazy.
D. ARBITER. Jeśli bazowy EMAIL to krótsza część anchor EMAIL, można go rozszerzyć do poprawnie ograniczonego kandydata, ale tylko bez połykania obcej encji. Analogicznie adres. Kolizja różnych typów albo nierozstrzygnięta granica => STOP/AMBIGUOUS, nie „najdłuższy wygrywa”. Wynik musi być niezależny od kolejności wejściowej. Ani Anchor, ani Guard nie decydują o priorytetach.
E. ONE APPLY. Po rozstrzygnięciu, jedna podmiana na oryginale od prawej strony. Nadaj tokeny KATEGORIA_NNN deterministycznie wg położenia w tekście; identyczne dosłowne wartości mogą współdzielić token, różne zapisy nigdy nie mogą w tej wersji dzielić tokenu. Mapa i token spany odpowiadają dokładnie wycinkom oryginału. Żadnego drugiego zamaskowania „resztek”.
F. GUARD-DRON (wyłącznie atrapa do gry, nie produkcyjny OutputGuard). Czyta TYLKO zamaskowany tekst, nie gold, nie wyniki detektorów. Wykrywa ogólnie pozostawione @ / ul. / podejrzany PESEL lub NIP po etykiecie; raportuje guard_flags, nie zmienia tekstu ani nie przyznaje tokenów. Jego trafienie nie jest sukcesem maskowania. Nie zmieniać obowiązującej polityki S4.

## Niezmienniki i warunki porażki
N1 poza zaakceptowanymi spanami tekst źródłowy znak w znak (po kodowaniu UTF-8). N2 żadnego tokenu w środku wyrazu/innego tokenu, żadnego sklejenia. N3 odtworzenie tego samego dosłownego tekstu przez mapę daje oryginał w przypadkach bez K2. N4 każda wartość tokenu dokładnie równa oryginał[start:end]. Każde złamanie = przegrana nawet bez wycieku.
Sędzia ma osobne niezależne gold spans, w tym dane rzeczywiście do maskowania i zakazane FP. Liczy: FN (pełny/częściowy wyciek), FP, uszkodzenie granic, mapę/Przywróć, STOP na rozwiązywalnym zadaniu, nierozstrzygnięte konflikty, Guard missed warning, czas. Nie wolno zdobyć wygranej przez STOP każdego wejścia ani zakrycie całego dokumentu. Zwycięstwo w Arena = mechanika przeżyła ten zestaw syntetyków; NIE certyfikat bezpieczeństwa realnych dokumentów.
Metamorfizmy Codexa: permutacja kolejności kandydatów, różne source/evidence bez zmiany faktów, dodanie emoji/diakrytyku przed spanem, zmiana błędów OCR, separator / newline, ten sam proces obsługuje kolejno dwa niezależne dokumenty, inne case_id. Zewnętrzny oracle nie używa wyniku obrońcy do wyliczenia expected.

TASK_SCOPE:
- backend/arena_sim.py
- backend/tests/test_arena_sim.py

OUT_OF_SCOPE: istniejący pipeline, backend/engine/* (osobne F0a), produkcyjny TokenAllocator i Guard, OCR/SpaCy/HerBERT, UI/API, archiwum/mapa .lynxdict, realne dokumenty, zmiana arch/spec.md, ENV ENGINE, merge, model lub sieć w runtime.

## Obieg
Codex najpierw BRIEF_ONLY precheck kontraktu i minimalności. CC potem implementuje dokładnie te 2 nowe pliki w odrębnym worktree gałęzi, uruchamia test oraz tworzy osobne ataki syntetyczne pod tasks/LYNX-ARCH-ARENA/attacks. DELIVERY podaje komendę, exact SHA i wyniki. Codex zamraża exact SHA, robi niezależny audit przez CLI, własne nieznane testy i raport w tasks/LYNX-ARCH-ARENA/round_01/tests/tests_r1.txt. Poprawka po porażce = nowa wersja reguł, ponowna rozgrywka przeciw wszystkim starym atakom. Brak automatycznego merge.
GATE: najwyżej 2 nowe pliki kodu, pliki <=600 l., funkcje <=50 l.; >150 zmienionych linii lub ratio >5:1 => WYMAGA_DECYZJI OWNERA przed pracą, nie zakładać wyjątku po samym zleceniu Areny.
WHERE_MAP:
- MODE: OPTIONAL
- TARGETS: backend/arena_sim.py
- REASON: wyłącznie izolowany eksperyment, bez przepięcia właściciela produkcyjnego.
