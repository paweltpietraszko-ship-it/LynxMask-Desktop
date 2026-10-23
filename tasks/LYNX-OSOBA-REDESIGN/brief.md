# LYNX-OSOBA-REDESIGN — brief Architekta v1.5 (23.10.2026, korekta po E1 STOP)

**Status: E1_STOP (raport CC 23.10); zmieniono wyłącznie reguły dowodowe §2 i warunki ponownego E1. Działający silnik bez zmian (`LYNX_OSOBA_DECIDER=off`). Bez E2, bez merge.**
Źródła: `cc_proposal.md` (20.10), `cc_proposal_update_2026-10-23.md` i `evidence_2026-10-23/` na gałęzi zadania; `BOARD.md` wiersz `LYNX-OSOBA-REDESIGN` (23.10); zamrożone `arch/spec.md` S1–S5. Bazę implementacji CC musi odświeżyć po prechecku; nie zakładać, że main jest nieruchomy.

## 1. Problem i granice dowodów

Dziś automatyczne decyzje OSOBA podejmuje kilka ścieżek niezależnie (spaCy w `ner_layer.py`, propagacja/inicjały/słowniki w `layers/ner_adapter.py`); Guard ma dodatkowe własne R1. Skutkiem są jednocześnie zbędne zakrycia, ciche pozostawienia osób i niepotrzebne pytania.

Na pomiarach CC: `LYNX-OSOBA-HANDOFF` zmniejszył pytania R1 z **7448 do 902** na 255 dokumentach bez zmiany GOLD — nie przypisywać tego zysku przyszłemu redesignowi. Pozostałe R1 obejmują człony nazw urzędów, miejscowości i nazwy funkcji. Eksperyment z szerokim słownikiem PESEL poprawiał osoby kierowane do Guarda w GOLD (dev 9→3, test 13→1), lecz generował **+210** dodatkowych zakryć na 255 dokumentach. Próba oceny pojedynczego słowa ograniczała te zakrycia, ale **usuwała 28 wcześniejszych zakryć**, w tym rzeczywistych osób w parach imię–nazwisko. To obserwacje prototypów, nie wyniki produkcyjnej nowej architektury.

Cel: **jedna automatyczna decyzja OSOBA na całym wystąpieniu w kontekście dokumentu**, wykorzystująca istniejące źródła dowodów. Nie chodzi o dokładanie PESEL jako kolejnej ścieżki automatycznie zakrywającej obok starego NER.

## 2. Rozstrzyganie OSOBA — tabela po E1 STOP (v1.5, 23.10)

**Powód korekty:** [E1_REPORT.md](round_01/implementation/E1_REPORT.md), kod E1 `cc516b7`, **nie przeszedł bramki**. Na GOLD ciche OSOBA wzrosły dev 1→16, test 0→36; zbędne zakrycia dev 69→107 i test 152→215. Spadek 902→337 R1 na 255 dokumentach NIE usprawiedliwia wycieków. Przyczyną nie jest samo wspólne miejsce decyzji, tylko utrata dowodów spaCy, samodzielny PESEL ≥1000 na etykietach oraz funkcje/wyrazy z PESEL 100–999 kierowane do ASK. **Poprzednie E1 pozostaje STOP; to kontrakt do nowego pomiaru, nie pozwolenie na E2.**

Jedna funkcja rozstrzyga **konkretne wystąpienie**, nie pisownię: `MASK` / `ASK` / `PASS`. `ASK` to **jedno** R1 dla nadal jawnego miejsca w aktualnym wyniku; nie zakrywa automatycznie. Dotychczasowe R2–R5/HIGH/MEDIUM/MAP_LEAK pozostają. Dwie osoby o tym samym nazwisku nie dzielą tokenu tylko przez zbieżność liter.

**Źródła dowodów:** istniejące nazwy/imiona, PESEL i Morfeusz, kotwice/składnia **oraz wystąpienia spaCy PER ze spanami**. SpaCy jest źródłem dowodu, **nie drugim autonomicznym wykonawcą maskowania**. Każdy wynik musi zostać oceniony na aktualnym tekście i z mocnymi dowodami PRZECIW.

Kolejność pierwszej pasującej decyzji:

| Konkretny przypadek | Wynik / pierwszeństwo |
| --- | --- |
| Już świadomie zamaskowane przez profil OSOBA albo w całości zajęte przez strukturalne ADRES/FIRMA/INSTYTUCJA/NUMER | Pozostaw dotychczasowy token i kategorię; bez drugiego OSOBA/R1 |
| Pewny **nieosobowy kontekst konkretnego wystąpienia**: pole/nagłówek typu `Data:`, nazwa urzędu/firmy, funkcja bez nazwiska, ulica/miejscowość, oczywisty termin/nagłówek, sam miesiąc bez kotwicy; Morfeusz: prep/conj/qub/adv lub znany wyraz funkcyjny bez osobowej kotwicy | `PASS` jako OSOBA. Nie maskować `Do`, `Skoro`, `Składanie` tylko dlatego, że bywają nazwiskami; zapis wielką literą na początku linii nie wystarcza. **Nie stosować tego wyłączenia do potwierdzonej pełnej osoby** |
| Wiarygodne odniesienie do pełnej osoby ustalonej **w tym samym dokumencie** (`Jan Termin` → `Pan Termin`) | Ten sam referent → `MASK` i właściwy wspólny token; prawdopodobne nazwisko, lecz niejasne która z dwóch osób → `ASK`, bez scalania. `Termin wykonania` pozostaje `PASS` |
| Biały człon z listy 316 | Tylko **pełne sąsiadujące imię + nazwisko** z C3 (to samo zdanie, bez kropki/przecinka między członami) może być `MASK`. Poza potwierdzonym odniesieniem z wiersza wyżej sam tytuł `Pan Termin`, inicjał `J. Termin` i samotny `Termin` → `PASS` bez R1 |
| Potwierdzona pełna para imię–nazwisko / nazwisko–imię lub inicjał–nazwisko **bez białego członu** | `MASK` całego spanu, z prawidłową mapą; nie odcinać nazwiska przez ocenę sąsiedniego słowa |
| **spaCy PER obejmujący co najmniej dwa człony wyglądające na imię/nazwisko**, pełna wiarygodna para, brak konkretnego dowodu instytucji/geografii/funkcji | `MASK`. Sygnał spaCy o pełnym spanie jest mocnym dowodem, nawet gdy któregoś członu nie ma w PESEL / `names_inflected`. Nie maskować bez walidacji samych nagłówków/organizacji |
| Kotwica osoby (`Pan/Pani`, `Świadek`, podpis, pole `Imię i nazwisko`) + kandydat nazwiska/imienia z Morfeusza, PESEL lub spaCy, bez mocnego PRZECIW | `MASK`, z zachowaniem powyższego C3; sam tytuł/funkcja bez odrębnego nazwiska nie kwalifikuje się |
| **Samotny spaCy PER** zgodny z listą imion albo jednoznaczną osobową analizą Morfeusza, bez dowodu przeciw | `MASK`; obejmuje wcześniej gubione samotne imiona. Jeśli analiza dopuszcza także zwykły wyraz lub tożsamość jest niepewna → `ASK` |
| **Samotny spaCy PER** bez słownikowego potwierdzenia (obce/niezwykłe nazwisko), bez konkretnego dowodu przeciw | `ASK`, **nie cichy PASS**. Nie wymuszać `MASK` na samą etykietę spaCy |
| PESEL ≥1000, samodzielne nazwisko bez kotwicy | `MASK` tylko z kontekstowym dowodem osoby (np. `Nowak zlecił`, `Mazur podpisał`) i bez mocnego przeciw. Bez niego, jeśli rzeczywiście może być nazwiskiem → `ASK`, a nie `MASK`. Nagłówki, etykiety, lokalizacje i wyrazy pospolite rozstrzyga wcześniej wiersz PRZECIW |
| PESEL 100–999 lub niepewna fleksja, bez kotwicy | `ASK` dla wiarygodnego wystąpienia **wewnątrz zdania**, bez kwalifikacji jako wyraz funkcyjny/tytuł/termin. Na początku zdania/wiersza samo PESEL 100–999 **nie wystarcza nawet do ASK**; wymagany dodatkowy sygnał osoby (spaCy PER, imię/rola, osobowa czynność). Przy sygnale i niepewności → `ASK`; bez niego `PASS`. Krytyczna kontrpróba: `Do` / `Skoro` / `Składanie` nie tworzą R1 |
| Sam spaCy PER z pewnym dowodem PRZECIW; sam CAPS bez potwierdzenia; brak kandydata | `PASS` |

**Miesiące:** `Styczeń…Grudzień` jako nazwiska tylko z osobową kotwicą, nie od samego PESEL. **Nie-pewność:** jeżeli istnieje wiarygodny sygnał osoby, a brak pewnego PRZECIW i brak przesłanek do `MASK`, preferuj `ASK` nad cichy `PASS`; nie dotyczy to wszystkich słów z wielkiej litery. **Bez punktacji trenowanej, LLM, nowej allowlisty ani dodatkowych niezależnych decydentów.**

**C3 obowiązuje bez zmian (decyzja OWNERA 23.10):** biała lista 316 wyłącza samodzielne słowa i tytuł/inicjał bez pełnego imienia; jedyny wyjątek to wiarygodna pełna sąsiadująca para imię + nazwisko (bez kropki/przecinka w jednym zdaniu) albo wiarygodne późniejsze odniesienie do tej pełnej osoby w tym samym dokumencie. `Jan Termin` → MASK; `Pan Termin` bez wcześniejszej osoby → PASS; późniejsze `Pan Termin` odnoszące się do `Jan Termin` → MASK albo ASK przy niepewnej tożsamości; `Termin wykonania` → PASS.

## 3. Konkretny szew C1 — finalna decyzja bez przenoszenia starych offsetów

Codex poprawnie wskazał, że `PipelineState.ner_results` i `ner_variants` przechowują słowniki wartości, `TokenAllocator.reset_spans()` kasuje spany pomiędzy warstwami, a `run_pipeline_new` dotąd zwraca tylko `(text, reverse_map, force_block)`. Globalne `_sub_whole` także zamienia identyczne słowa naraz. To **nie jest transport per wystąpienie**.

Minimalny kontrakt do falsyfikacji w ponownym E1: **zachować pojedynczy punkt podejmowania decyzji OSOBA na końcu przetwarzania tekstu, po obecnych warstwach i HerBERT, ale przed `guard_output_with_map` i `collect_warnings`**. W tym miejscu mamy jeden aktualny, niezmienny snapshot `text` i bieżącą `reverse_map`; decyzje `MASK/ASK/PASS` powstają i są wykonywane **na tych samych współrzędnych**. Nie ma potrzeby przenosić decyzji przez etap ADRES/FIRMA ani budować globalnej mapy offsetów. HerBERT zachowuje swoje miejsce po obecnych warstwach i ustawienie domyślnie OFF; nowa decyzja jest deterministycznym rozstrzygnięciem nazw, nie dodatkowym modelem.

**Owner i dane:** `backend/person_decision.py::resolve_final_persons(text, reverse_map, context) -> (text_after, reverse_map_after, ask_spans)`, gdzie `ask_spans` to wystąpienia `{start:int,end:int,rule:"R1",reason:str}` **w finalnym `text_after`**, przed dopisaniem nagłówka PSE. Start/end liczone w indeksach znaków Pythona (Unicode code points), po stronie API istniejące `shift_warnings` dla nagłówka i `toUtf16` w oknie; nie przenosić bajtów ani pozycji UTF-16 do backendu. Każdy kandydat oceniany z tego samego niemodyfikowanego snapshotu. Nakładające się kandydatury: potwierdzona pełna osoba pierwsza, krótsze w całości zawarte pomijane, nierozstrzygnięta kolizja → `ASK` jednej pozycji. `MASK` wykonywać według jednoznacznych spanów od prawej do lewej za pomocą istniejącego alokatora/tokenizacji, nigdy przez globalne `str.replace` ani `_sub_whole`. Indeksy `ASK` przeliczyć **wyłącznie przez znane lokalne podmiany `MASK` z tego snapshotu**, każdą z kontrolowanym start/end i różnicą długości. `ASK` przecinający `MASK` nie może pozostać jako osobny surowy alarm; konflikt trzeba rozstrzygnąć przed podmianą. Jeśli identyfikacja lub pozycja nie jest jednoznaczna, nie zgadywać: wynik `ASK` z właściwym spanem albo blokada S3, nigdy ciche `PASS`.

**Miejsce transportu:** `pipeline.py::_apply_guard` (wspólne wejście po `run_pipeline_new` i ewentualnej legacy ścieżce) wywołuje `resolve_final_persons` po obecnym `apply_net`, przekazuje otrzymane `ask_spans` bezpośrednio do `pipeline.py::_apply_output_guard`, która łączy je z pozostałymi ostrzeżeniami `guard_residue.collect_warnings`. R1 z `_r1` i `released()` zostaje wyłączone w obu dostępnych ścieżkach — **nie zostawić równoległego źródła R1**. R2–R5, HIGH/MEDIUM/MAP_LEAK i obecny mechanizm Guard/allowlist/S3/S4/S5 bez zmian. Do końcowego wyniku przekazać identyfikatory pozycji ostrzeżeń już istniejącym formatem.

**Warunek przełączenia:** obecne automatyczne ścieżki OSOBA w `ner_layer.py`/`layers/ner_adapter.py` muszą przestać autonomicznie maskować imiona/nazwiska; zachować obecną FIRMA, struktury i świadomą tokenizację OSOBA przez `trie_layer`. Nowy decyder analizuje to, co nadal jawne po tych warstwach, również **całe sąsiadujące imię–nazwisko**. Dane spaCy, Morfeusza, PESEL, słownika imion i kontekstu z bieżącego finalnego tekstu są wejściem jednego rozstrzygnięcia, nie kolejnymi właścicielami maskowania. Powiązanie z rozpoznaną pełną osobą może korzystać z ustaleń tego samego snapshotu i istniejącej reverse_map, także gdy jej wcześniejsze wystąpienie jest już tokenem. Nie wyciągać tożsamości z samych bajtów nazwiska lub numeracji tokenu. Brak wiarygodnego mapowania → `ASK` dla rzeczywiście podejrzanego odniesienia; nie ciche `PASS` z powodu białej listy. Nie przyjmować nieprzeniesionych pozycji wcześniejszego spaCy jako dowodu tożsamości wystąpienia; jeśli późny etap traci jego poprawne trafienia, nie maskować tej straty dodatkowymi `_sub_whole`: **E1 STOP, szew wymaga korekty przed E2**. Ta decyzja minimalizuje transport, ale jej zachowanie na pełnych nazwach w pobliżu adresów jest **hipotezą do weryfikacji**, nie ustalonym faktem.

Mapowanie tokenów: wykorzystywać tę samą finalną `reverse_map` i reguły numeracji S2; nie tworzyć konkurencyjnej mapy. Przy takim samym zapisie dotyczącym dwóch różnych referentów nie wolno użyć tego samego tokenu wyłącznie dlatego, że `TokenAllocator.assign` deduplikuje po kanonicznej wartości — CC musi określić minimalny wariant rozróżnienia albo zakończyć E1 jako niewykonalne; nie rozszerzać całego alokatora dla innych typów.

**Sprawdzenie C1 nadal obowiązuje:** tekst zawiera dwie identyczne frazy `Róża`, jedną osobową, drugą nie; między nimi warstwa adresu zamienia długi fragment na krótki `ADRES_001`. Osobowy span `MASK`, nieosobowy `PASS`, inny celowo niejednoznaczny homonim `ASK` → dokładnie ten trzeci fragment po finalnych podmianach. Powtórzyć z emoji przed każdym wystąpieniem (Python code points vs JavaScript UTF-16), dwiema identycznymi osobami o nieustalonej tożsamości, a także z `FIRMA_001`. Brak globalnej zamiany powtórzeń. W odbiorze E1 wymagać **pełnej listy poprawnych zakryć starego silnika, które nowy traci**; nawet jedno utracone prawdziwe nazwisko = STOP przed E2, a nie skompensowanie dodatkowymi trafieniami.

## 4. Dane i koszty

Źródło nazwisk: ministerialny zestaw PESEL [dane.gov.pl zbiór 1681](https://dane.gov.pl/pl/dataset/1681) — zasoby 1148808 i 1148811, stan danych **20.01.2026**. Wziąć tylko agregaty nazwisk i liczbę nosicieli, wersję M+K, znormalizować deterministycznie. Artefakt produkcyjny (proponowane `backend/person_surnames_pesel_20260120.json`) i lista 316 muszą mieć źródło, datę, licencję, sumy SHA256 źródeł i odtwarzalny skrypt przygotowania **bez zależności sieciowej w czasie pracy aplikacji**. Plik danych powstał na gałęzi eksperymentalnej E1, lecz jego przygotowanie i pochodzenie wymagają weryfikacji przed wydaniem; nie traktować samego istnienia pliku jako odbioru danych. Limit pliku/ładowania zmierzyć, nie zgadywać. Aktualizacje wyłącznie osobnym Taskiem po rocznej publikacji PESEL, nie samoczynnie.

Skala i progi: zamiast arbitralnych punktów 0,35 / 0,7 zastosować kolejność silnych i słabych dowodów z §2; **1000** pozostaje progiem produktowym dla samodzielnego nazwiska, **100** dolnym progiem danych pomocniczych z propozycji CC. Reguły końcówek i lematyzacja nie mogą dopasowywać innych słów jako nazwisk bez kontekstu; rejestrować warianty tylko, gdy są rzeczywistymi formami dopasowanego kandydata.

Rozmiar i podział: **jeden Task**; E1 pozostaje eksperymentem `off/on` niewpływającym na użytkownika; E2 dopiero po odrębnej decyzji OWNERA na podstawie powtórzonego E1 i niezależnego audytu. OWNER 23.10 dopuścił implementację bez wstępnego szacunku z twardym ograniczeniem **żaden plik nie przekracza 600 linii**; dla nowych danych odbiorczych osobno ustalić liczbę i koszt. Nowe reguły w jednym małym ownerze, nie powiększać bez końca `ner_layer.py`, `ner_adapter.py`, `pipeline.py`. E1 to bramka porównawcza, nie dodatkowa infrastruktura produktu.

## 5. Ponowne E1: warunki pomiaru i odbioru

**Zanim CC rozpocznie ponowne E1:** uzupełnić decyder o kandydatów spaCy na **bieżącym finalnym snapshocie**, bez ponownego maskowania przez stare warstwy OSOBA. Punktowe `spacy_ner.detect_entities(final_text)` jest najmniejszą hipotezą do próby; trzeba zmierzyć czas i RAM, ponieważ spaCy jest już wywoływane wcześniej. **Uwaga z kontroli Architekta:** obecne `spacy_ner.detect_entities` usuwa powtórzenia po `(entity_text.lower(),label)`, więc **nie przekazuje wszystkich wystąpień**. W wariancie E1 zachować `start/end` i każdą osobną pozycję bez tej deduplikacji, z wąską zmianą API lub wywołania; nie używać słownika wartości ani globalnego `_sub_whole` do odtwarzania spanów. Gdy drugi przebieg na finalnym tekście traci poprawne pełne osoby z powodu zniknięcia kontekstu po adresach, **STOP** i zgłosić konieczność innego szwu zamiast pisać system ogólnego przenoszenia offsetów.

**Porównanie z tą samą bazą co E1 STOP**, osobno dev i test: lista **każdego utraconego poprawnego zakrycia** (również samotne imiona, zagraniczne i rzadkie nazwiska), nowych cichych OSOBA, nowych błędnych zakryć, ostrzeżeń R1/wszystkich i wyników Przywróć; rozróżnić utratę prawdziwej osoby od usunięcia dawnego fałszywego trafienia. Kontrole `Data:`, `Zasada`, `Szczecinie`, `Wojewódzkiego`, `Do`, `Skoro`, `Składanie`, `Katarzyna`, `Barbara`, obce nazwisko spoza PESEL, `Jan Termin` / `Pan Termin` / `Termin wykonania`. Żadnego nowego cichego nazwiska; dodatkowe pytania nie mogą być „śmieciami”. **Sprawdzić koszt dodatkowego spaCy**, limit 600 linii w każdym pliku, `off` bitowo zgodny z dotychczasowym wynikiem.

**Nie dostrajać na GOLD test.** Raport pierwszego E1 zawiera już agregaty test (0→36 cichych), więc nie przedstawiać powtarzanego testu jako świeżego, niezależnego holdoutu. Dopasowanie reguł tylko na dev/znanych kontrpróbach, przy teście wyłącznie zamrożone porównanie i STOP/PASS; nowy niezależny GOLD z innych dziedzin nadal wymagany przed E2.

## 5. Falsyfikacja i odbiór

Porównanie **na exact SHA**, dwie wersje na tych samych wejściach/profilach: (a) GOLD `dataset_gold_20261022` dev i niewykorzystywany do strojenia test; (b) 255 dokumentów publicznych z manifestów CC; (c) zdania kontrolne z `evidence_2026-10-23/sentences.txt`; (d) syntetyczne 68 zdań wyłącznie jako znany test regresji, **nie nowy holdout**. Mierzyć na finalnym tekście: ciche OSOBA, OSOBA z ostrzeżeniem, nadmaskowane nie-osoby, pytania R1/dokument, uszkodzenia granic/Przywróć, koszt czasu i RAM. Nie mieszać strat OCR z błędami silnika. Raport osobno pokazuje **nowe i utracone** zakrycia OSOBA, z podziałem czy były poprawne.

Minimalne przypadki:
- `Jan Nowak / Jana Nowaka / Nowak` jako ta sama rozpoznana osoba → spójność tokenu, bez sklejenia odrębnych Janów Nowaków.
- `Piotr [nazwisko]` i `[imię] [nazwisko]` w nazwie osoby → nie rozcinać i nie usuwać wcześniejszych trafień (regresja 28).
- `Wczoraj Nowak zlecił`, `Mazur podpisał`, `Świadek Malina zeznała`, `Wnioskodawca Kawa` → `MASK` albo — przy rzeczywistej kolizji — `ASK`, nigdy cichy wyciek.
- `Kawa i herbata zostały`, `Termin wykonania`, `Dziennik Urzędowy`, `Urząd Wojewódzki`, `w Krakowie`, `ul. ...`, `Odwołujący` → bez błędnego OSOBA/R1.
- `Styczeń` w dacie vs `Pani Styczeń` → miesiąc jawny, osoba maskowana; biały wpis samodzielny nie generuje R1.
- **Granica C2/C3 bez wcześniejszej osoby:** `Jan Termin` → MASK całej wiarygodnej pary, natomiast w osobnym, pozbawionym pełnego nazwiska dokumencie `Pan Termin`, `J. Termin`, `Jan, Termin`, `Jan. Termin`, `Termin wykonania` → biały człon PASS bez R1 OSOBA. Sam tytuł lub inicjał nie przełamują białej listy.
- **Nowa kontrpróba OWNERA — odniesienie w tym samym dokumencie:** `Jan Termin przyszedł na posiedzenie. Pan Termin przedstawił zaświadczenie.` → obie wzmianki chronione jako ten sam referent, jeśli ustalenie tożsamości jest wiarygodne. Dodatkowe `Termin wykonania upływa jutro.` → jawne, bez R1. Gdy dokument zawiera `Jan Termin` i `Piotr Termin`, a później tylko `Pan Termin`, bez jasnego kontekstu → **ASK**, nie mechaniczne połączenie tokenów ani PASS; porównać wynik, mapę i Przywróć. Bez poprawy wyniku przez globalne zastępowanie wszystkich `Termin`.
- Dwa homonimy o innym znaczeniu w jednym dokumencie → różne decyzje per wystąpienie.
- Po `ASK` Guard pokazuje dokładnie **jedną** pozycję, nie maskuje automatycznie, nie blokuje S3; po `MASK` żaden surowy fragment nie zostaje przy tokenie.
- Awaria NER/decydera → zgodne z S3; brak jawnego PII w logach. Pozostałe typy FIRMA/ADRES/NUMER i mapy bez regresji.

**Bramka odbioru (kryteria sprzed E1 nadal obowiązują):** brak nowego cichego wycieku OSOBA na GOLD dev/test; bez utraty potwierdzonych zakryć pełnych osób z bazy; na 255 dokumentach **nie zaakceptować nowej fali +210 błędnych zakryć** z prototypu ani powrotu do 7448 pytań R1. Każdy wzrost zbędnych zakryć / pytań R1 musi być jawnie sklasyfikowany i przedstawiony OWNEROWI, nie chowany w sumie. Brak regresji Przywróć, formatu tokenów, S3 i innych kategorii. Nie ogłaszać procentowej skuteczności z 68 przygotowanych zdań.

Jeśli E1 pokaże, że prosta wspólna decyzja odbiera prawdziwe pełne osoby albo nie ogranicza kosztu pytań, **STOP przed E2**. Nie „naprawiać” wyniku nową autonomiczną regułą lub kolejną warstwą.

### Uzupełnienie odbioru CC 23.10 — cel produktu i niezależna kontrola

**Cel użytkowy:** OWNER akceptuje średnio 2–4 decyzje o osobach na dokument, ale nie zalewanie Guarda oczywistymi śmieciami. W raporcie mierzyć osobno R1 i wszystkie ostrzeżenia. Cel 2–4 R1/dokument średnio na niezależnych zbiorach odbiorczych nie może zostać osiągnięty przez ukrycie rzeczywistych nazwisk. Każde nazwisko oznaczone w gold musi być MASK lub ASK — bez cichego PASS. Nie oznacza to gwarancji wykrywania dowolnych nieznanych nazwisk na świecie.

**Jakość pytań:** zero oczywistych śmieci R1 w oznaczonych dokumentach odbiorczych: nazwy funkcji i ról bez osoby, człony nazw urzędów i miejscowości, skróty, nie-słowa/OCR, sama mała litera bez kotwicy oraz samodzielne słowa z białej listy. Mierzyć też, czy przypadki ASK są rzeczywiście niejednoznaczne. Gdy cel liczby pytań koliduje z ochroną nazwisk, raportować i STOP, a nie obniżać metrykę przez ciche PASS.

**Oddzielenie diagnozy od odbioru:** 255 dokumentów publicznych, GOLD dev i znane zdania to materiały do rozwijania reguł i porównania baseline, NIE niezależny dowód generalizacji. GOLD test pozostaje zamknięty dla strojenia. Przed decyzją o wdrożeniu E2 wymagany jest dodatkowy, nieoglądany przez implementera GOLD przygotowany przez innego autora, zweryfikowany niezależnie, na innych szablonach i w brakujących dziedzinach (kadry, księgowość, medycyna, budowa). CC proponuje liczbę dokumentów na dziedzinę i koszt Ownerowi — nie twierdzić, że zbiór już istnieje. Istniejące pl-pii/Mobile służą porównaniu, ale holdoutem są wyłącznie nieoglądane wcześniej części. Wyniki prezentować osobno per dziedzina, z poprawnymi i utraconymi zakryciami; dokumenty prywatne nie trafiają do repo.

**Biała lista:** 316 słów pozostaje wejściem zaakceptowanym przez OWNERA, bez cichej podmiany. Przed odbiorem ocenić jej ograniczenie do języka pism KIO na niezależnym korpusie ogólnej polszczyzny, jeżeli licencja i dostęp na to pozwalają (np. NKJP). Rozbieżności raportować; ewentualna zmiana listy wymaga osobnej decyzji. Brak zależności sieciowej podczas pracy aplikacji.

Model rozumiejący zdanie (np. Bielik) jest już odłożony w `ODLOZONE.md`. Nie budować dla niego interfejsu ani integracji w tym Tasku.

## 6. TASK_SCOPE (proponowany; CC ma skorygować tylko na podstawie exact SHA)

- backend/person_decision.py (nowy, owner pojedynczego finalnego rozstrzygnięcia)
- backend/layers/ner_adapter.py (wyłączenie autonomicznych OSOBA i aplikacja decyzji)
- backend/ner_layer.py (spaCy jako źródło kandydatów; FIRMA niezmieniona)
- backend/osoba_not_person.py (wspólne dowody/wyłączenia i odejście od osobnego released)
- backend/guard_residue.py (R1 z `ASK`, pozostały Guard bez zmian)
- backend/pipeline_new.py (oddanie autonomicznej decyzji OSOBA; weryfikacja obecnej kolejności i jej wpływu na E1)
- backend/pipeline.py (**wymagany wspólny szew** decydera i Guard na aktywnej nowej/legacy ścieżce)
- backend/person_surnames_pesel_20260120.json (nowy, z manifestem/odtwarzalnym generatorem)
- backend/pipeline_core.py (tylko jeśli konieczny wąski szew istniejącego TokenAllocator dla rozróżnienia referentów; nie zmieniać innych kategorii)
- backend/tests/test_person_decision.py (kontrpróby i integracja)
- tasks/LYNX-OSOBA-REDESIGN/round_01/implementation/DELIVERY.md (po kodzie)
- tasks/LYNX-OSOBA-REDESIGN/brief.md (ten kontrakt)

Nie zmieniać S2, `arch/spec.md`, `FROZEN.lock`, FIRMA, OCR, UI, allowlisty, HerBERT ON/OFF, instalatora, ani pełnego rejestru decyzji. Usunięcie starej ścieżki tylko po pokazaniu nowego ownera i przejściu testów.

**WHERE_MAP:** REQUIRED przed kodem, TARGETS: `backend/ner_layer.py::process_ner`; `backend/layers/ner_adapter.py::apply_ner_layer`; `backend/layers/ner_adapter.py::_apply_dictionary_names`; `backend/osoba_not_person.py::single_osoba_evidence`; `backend/guard_residue.py::collect_warnings`. Powód: przenosimy/wyłączamy dotychczasowe owners decyzji OSOBA, nie możemy zostawić ukrytych równoległych zakryć.

## 7. Przekazanie po E1 STOP

**CC → ponowne E1, nie E2:** zaktualizować wyłącznie pojedynczy decyder OSOBA i minimalny szew dostarczenia pełnych spanów spaCy; stare autonomiczne OSOBA pozostają wyłączone tylko w eksperymentalnym trybie `on`, `off` produkcyjnie bez zmian. Nie dopisywać wyjątków „bo taki wynik w gold” i nie rozbudowywać Guarda R1 na własną rękę. Zwrócić raport `tasks/LYNX-OSOBA-REDESIGN/round_01/implementation/E1_REPORT_R2.md` z exact SHA kodu, statystykami porównania, kosztami oraz diagnozą każdej **nowej cichej** osoby. E1 nadal jest bramką STOP, dopóki dowody nie pokażą spełnienia warunków §5. Nie zmieniać frozen spec, UI, FIRMA/ADRES ani trybu HerBERT. Niezależny Codex ocenia kolejną dostawę exact SHA; OWNER podejmuje decyzję przed jakimkolwiek E2/merge.
