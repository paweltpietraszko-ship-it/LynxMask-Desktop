# LYNX-OSOBA-REDESIGN — brief Architekta v1.1 (23.10.2026, po Codex r1 C1/C2)

**Status: C1/C2 uzupełnione po Codex r1; C3 OWNER_DECISION_NEEDED. NIE kierować do Codexa r2 przed C3; bez implementacji i merge.**
Źródła: `cc_proposal.md` (20.10), `cc_proposal_update_2026-10-23.md` i `evidence_2026-10-23/` na gałęzi zadania; `BOARD.md` wiersz `LYNX-OSOBA-REDESIGN` (23.10); zamrożone `arch/spec.md` S1–S5. Bazę implementacji CC musi odświeżyć po prechecku; nie zakładać, że main jest nieruchomy.

## 1. Problem i granice dowodów

Dziś automatyczne decyzje OSOBA podejmuje kilka ścieżek niezależnie (spaCy w `ner_layer.py`, propagacja/inicjały/słowniki w `layers/ner_adapter.py`); Guard ma dodatkowe własne R1. Skutkiem są jednocześnie zbędne zakrycia, ciche pozostawienia osób i niepotrzebne pytania.

Na pomiarach CC: `LYNX-OSOBA-HANDOFF` zmniejszył pytania R1 z **7448 do 902** na 255 dokumentach bez zmiany GOLD — nie przypisywać tego zysku przyszłemu redesignowi. Pozostałe R1 obejmują człony nazw urzędów, miejscowości i nazwy funkcji. Eksperyment z szerokim słownikiem PESEL poprawiał osoby kierowane do Guarda w GOLD (dev 9→3, test 13→1), lecz generował **+210** dodatkowych zakryć na 255 dokumentach. Próba oceny pojedynczego słowa ograniczała te zakrycia, ale **usuwała 28 wcześniejszych zakryć**, w tym rzeczywistych osób w parach imię–nazwisko. To obserwacje prototypów, nie wyniki produkcyjnej nowej architektury.

Cel: **jedna automatyczna decyzja OSOBA na całym wystąpieniu w kontekście dokumentu**, wykorzystująca istniejące źródła dowodów. Nie chodzi o dokładanie PESEL jako kolejnej ścieżki automatycznie zakrywającej obok starego NER.

## 2. Rozstrzyganie OSOBA (C2 — zasady zamknięte)

Jedna funkcja na każde **wystąpienie**, a nie na pisownię: `MASK` (token OSOBA), `ASK` (jedno R1 w Guardzie), `PASS` (bez R1). Inne ostrzeżenia Guarda pozostają niezależne. Wystąpienia o identycznym zapisie mogą otrzymać różne decyzje; samo powtórzenie nazwiska nie dowodzi, że to ta sama osoba. Jeżeli nie sposób wiarygodnie ustalić wspólnego referenta, nie scalać tokenów tylko po pisowni. Dotychczasowy kanoniczny mianownik Przywróć dopuszczalny dla tej samej ustalonej osoby.

Zamknięta kolejność (pierwsza pasująca reguła wygrywa):

| Sytuacja na konkretnym spanie | Wynik |
| --- | --- |
| Span już zakryty świadomą encją OSOBA użytkownika z profilu | Nie klasyfikować ponownie, istniejący token zostaje |
| Fragment należy w całości do potwierdzonej ADRES/FIRMA/INSTYTUCJA/innej kategorii, bez niezależnej pełnej osoby poza jej granicą | `PASS` jako OSOBA; obowiązuje dotychczasowa kategoria |
| Potwierdzona cała para imię–nazwisko / inicjał–nazwisko, bądź nazwisko wiarygodnie powiązane z pełną osobą w tym dokumencie | `MASK`; nie odrzucać z powodu pojedynczego członu przypominającego instytucję |
| Wyraźna kotwica osoby (Pan/Pani, Świadek, Wnioskodawca, podpis, pole imię i nazwisko) **i** wiarygodny kandydat imienia/nazwiska z PESEL lub imion/Morfeusza; bez kolizji kategorii | `MASK` |
| Tytuł/funkcja bez odrębnej nazwy osoby (`Pani dyrektor`, `Pełnomocnik Odwołującego`) | `PASS`; sama funkcja nie jest nazwiskiem |
| Samotny miesiąc/dzień tygodnia bez niezależnej kotwicy osoby, nagłówek/termin urzędowy, kontekst ulicy/miasta, nieliterowy szum OCR lub wyłącznie mała litera | `PASS` |
| Samodzielne słowo z białej listy 316 (bez potwierdzonego pełnego imienia i nazwiska) | `PASS` i bez R1 — zachowuje zatwierdzoną listę; wyjątek dla pełnej osoby wymaga C3 niżej |
| Samotne nazwisko z PESEL ≥1000, zapisane jak nazwa własna, niebędące funkcją, adresem, instytucją lub oczywistym nie-słowem | `MASK` również bez spaCy; początek zdania nie jest wykluczeniem |
| PESEL 100–999, pisownia nazwy własnej, bez kotwicy i bez mocnego przeciw; z samym spaCy PER lub bez niego | `ASK` (dodatkowy słaby sygnał nie zmienia na `MASK`) |
| Niejasna fleksja nazwiska albo słowo prawdopodobnie oznaczające osobę z czasownikiem czynności osoby, bez mocnej kotwicy, ale co najmniej z wiarygodnym słownikowym lub kontekstowym sygnałem osoby | `ASK`, nie `MASK`; `być` samo w sobie nie jest takim sygnałem |
| Rzeczywisty konflikt kotwicy osoby z rozpoznaną inną kategorią lub funkcją, nieobejmujący całej potwierdzonej pary | `ASK`, o ile fragment pozostał jawny; jeśli został prawidłowo zakryty przez inną kategorię, bez powtórnego R1 |
| Sam spaCy PER bez słownika, kotwicy, czynności osoby lub innego dowodu; sam CAPS; brak kandydata | `PASS` (to nie jest samodzielna podstawa pytania) |

Miesiące `Styczeń…Grudzień` jako nazwisko wymagają **kotwicy osoby** także przy liczbie nosicieli PESEL ≥1000. Słownik nazwisk jest ważniejszy od samotnego wyniku spaCy, ale nie unieważnia dowodu geograficznego lub prawnego dotyczącego tego konkretnego wystąpienia. PESEL 100 to tylko dolna granica pomocniczych kandydatów; próg automatycznego zakrycia samodzielnego nazwiska = 1000. Bez uczenia wag, regresji logistycznej i arbitra LLM.

**C3 — rozstrzygnięcie OWNERA wymagane przed ponownym precheckiem:** biała lista 316 słów (zaakceptowana 23.10) blokuje zgłoszenie samodzielnego wyrazu jako nazwiska. Architekt **rekomenduje** wyjątek tylko dla wiarygodnie rozpoznanej pełnej osoby (`Jan Termin` może być OSOBA, `Termin wykonania` nie); Codex potwierdził sens ochrony pełnej osoby, ale nie uznał wyjątku za zatwierdzony. Do jawnego wyboru OWNERA: (A) potwierdzić wyjątek dla pełnej osoby — preferowane; (B) wymagać wyłączenia członu z białej listy nawet wewnątrz imienia–nazwiska, z ryzykiem utraty właściwego zakrycia. Nie wprowadzać automatycznie A bez akceptacji.

## 3. Konkretny szew C1 — finalna decyzja bez przenoszenia starych offsetów

Codex poprawnie wskazał, że `PipelineState.ner_results` i `ner_variants` przechowują słowniki wartości, `TokenAllocator.reset_spans()` kasuje spany pomiędzy warstwami, a `run_pipeline_new` dotąd zwraca tylko `(text, reverse_map, force_block)`. Globalne `_sub_whole` także zamienia identyczne słowa naraz. To **nie jest transport per wystąpienie**.

Minimalny kontrakt do falsyfikacji w E1: **przenieść punkt podejmowania decyzji OSOBA na sam koniec przetwarzania tekstu, po obecnych warstwach i wywołaniu HerBERT, ale przed `guard_output_with_map` i `collect_warnings`**. W tym miejscu mamy jeden aktualny, niezmienny snapshot `text` i bieżącą `reverse_map`; decyzje `MASK/ASK/PASS` powstają i są wykonywane **na tych samych współrzędnych**. Nie ma potrzeby przenosić decyzji przez etap ADRES/FIRMA ani budować globalnej mapy offsetów. HerBERT zachowuje swoje miejsce po obecnych warstwach i ustawienie domyślnie OFF; nowa decyzja jest deterministycznym rozstrzygnięciem nazw, nie dodatkowym modelem.

**Owner i dane:** `backend/person_decision.py::resolve_final_persons(text, reverse_map, context) -> (text_after, reverse_map_after, ask_spans)`, gdzie `ask_spans` to wystąpienia `{start:int,end:int,rule:"R1",reason:str}` **w finalnym `text_after`**, przed dopisaniem nagłówka PSE. Start/end liczone w indeksach znaków Pythona (Unicode code points), po stronie API istniejące `shift_warnings` dla nagłówka i `toUtf16` w oknie; nie przenosić bajtów ani pozycji UTF-16 do backendu. Każdy kandydat oceniany z tego samego niemodyfikowanego snapshotu. Nakładające się kandydatury: potwierdzona pełna osoba pierwsza, krótsze w całości zawarte pomijane, nierozstrzygnięta kolizja → `ASK` jednej pozycji. `MASK` wykonywać według jednoznacznych spanów od prawej do lewej za pomocą istniejącego alokatora/tokenizacji, nigdy przez globalne `str.replace` ani `_sub_whole`. Indeksy `ASK` przeliczyć **wyłącznie przez znane lokalne podmiany `MASK` z tego snapshotu**, każdą z kontrolowanym start/end i różnicą długości. `ASK` przecinający `MASK` nie może pozostać jako osobny surowy alarm; konflikt trzeba rozstrzygnąć przed podmianą. Jeśli identyfikacja lub pozycja nie jest jednoznaczna, nie zgadywać: wynik `ASK` z właściwym spanem albo blokada S3, nigdy ciche `PASS`.

**Miejsce transportu:** `pipeline.py::_apply_guard` (wspólne wejście po `run_pipeline_new` i ewentualnej legacy ścieżce) wywołuje `resolve_final_persons` po obecnym `apply_net`, przekazuje otrzymane `ask_spans` bezpośrednio do `pipeline.py::_apply_output_guard`, która łączy je z pozostałymi ostrzeżeniami `guard_residue.collect_warnings`. R1 z `_r1` i `released()` zostaje wyłączone w obu dostępnych ścieżkach — **nie zostawić równoległego źródła R1**. R2–R5, HIGH/MEDIUM/MAP_LEAK i obecny mechanizm Guard/allowlist/S3/S4/S5 bez zmian. Do końcowego wyniku przekazać identyfikatory pozycji ostrzeżeń już istniejącym formatem.

**Warunek przełączenia:** obecne automatyczne ścieżki OSOBA w `ner_layer.py`/`layers/ner_adapter.py` muszą przestać autonomicznie maskować imiona/nazwiska; zachować obecną FIRMA, struktury i świadomą tokenizację OSOBA przez `trie_layer`. Nowy decyder analizuje to, co nadal jawne po tych warstwach, również **całe sąsiadujące imię–nazwisko**. Dane spaCy, Morfeusza, PESEL, słownika imion i kontekstu z bieżącego finalnego tekstu są wejściem jednego rozstrzygnięcia, nie kolejnymi właścicielami maskowania. Nie przyjmować nieprzeniesionych pozycji wcześniejszego spaCy jako dowodu tożsamości wystąpienia; jeśli późny etap traci jego poprawne trafienia, nie maskować tej straty dodatkowymi `_sub_whole`: **E1 STOP, szew wymaga korekty przed E2**. Ta decyzja minimalizuje transport, ale jej zachowanie na pełnych nazwach w pobliżu adresów jest **hipotezą do weryfikacji**, nie ustalonym faktem.

Mapowanie tokenów: wykorzystywać tę samą finalną `reverse_map` i reguły numeracji S2; nie tworzyć konkurencyjnej mapy. Przy takim samym zapisie dotyczącym dwóch różnych referentów nie wolno użyć tego samego tokenu wyłącznie dlatego, że `TokenAllocator.assign` deduplikuje po kanonicznej wartości — CC musi określić minimalny wariant rozróżnienia albo zakończyć E1 jako niewykonalne; nie rozszerzać całego alokatora dla innych typów.

**Nowe sprawdzenie C1:** tekst zawiera dwie identyczne frazy `Róża`, jedną osobową, drugą nie; między nimi warstwa adresu zamienia długi fragment na krótki `ADRES_001`. Osobowy span `MASK`, nieosobowy `PASS`, inny celowo niejednoznaczny homonim `ASK` → dokładnie ten trzeci fragment po finalnych podmianach. Powtórzyć z emoji przed każdym wystąpieniem (Python code points vs JavaScript UTF-16), dwiema identycznymi osobami o nieustalonej tożsamości, a także z `FIRMA_001`. Brak globalnej zamiany powtórzeń. W odbiorze E1 wymagać **pełnej listy poprawnych zakryć starego silnika, które nowy traci**; nawet jedno utracone prawdziwe nazwisko = STOP przed E2, a nie skompensowanie dodatkowymi trafieniami.

## 4. Dane i koszty

Źródło nazwisk: ministerialny zestaw PESEL [dane.gov.pl zbiór 1681](https://dane.gov.pl/pl/dataset/1681) — zasoby 1148808 i 1148811, stan danych **20.01.2026**. Wziąć tylko agregaty nazwisk i liczbę nosicieli, wersję M+K, znormalizować deterministycznie. Artefakt produkcyjny (proponowane `backend/person_surnames_pesel_20260120.json`) i lista 316 muszą mieć źródło, datę, licencję, sumy SHA256 źródeł i odtwarzalny skrypt przygotowania **bez zależności sieciowej w czasie pracy aplikacji**. Pliku tego *nie ma jeszcze* w repo — prototyp CC nie jest gotowym assetem produkcyjnym. Limit pliku/ładowania zmierzyć, nie zgadywać. Aktualizacje wyłącznie osobnym Taskiem po rocznej publikacji PESEL, nie samoczynnie.

Skala i progi: zamiast arbitralnych punktów 0,35 / 0,7 zastosować kolejność silnych i słabych dowodów z §2; **1000** pozostaje progiem produktowym dla samodzielnego nazwiska, **100** dolnym progiem danych pomocniczych z propozycji CC. Reguły końcówek i lematyzacja nie mogą dopasowywać innych słów jako nazwisk bez kontekstu; rejestrować warianty tylko, gdy są rzeczywistymi formami dopasowanego kandydata.

Rozmiar i podział: **jeden Task**, dwa wewnętrzne kroki CC: E1 ślad decyzji/shadow na identycznym wejściu (nowa klasyfikacja i symulacja lokalnych podmian NIE wpływają na wynik użytkownika), E2 po zaakceptowanej bramce przełączenie ownera OSOBA + wyłączenie starych autonomicznych ścieżek + Guard R1. Po prechecku CC podaje budżet plików, linii, czasu i RAM; **>150 nowych/zmienionych linii wymaga zgody OWNERA**. Nowe reguły w jednym małym ownerze, nie powiększać bez końca `ner_layer.py`, `ner_adapter.py`, `pipeline.py`. E1 to bramka porównawcza, nie dodatkowa infrastruktura produktu.

## 5. Falsyfikacja i odbiór

Porównanie **na exact SHA**, dwie wersje na tych samych wejściach/profilach: (a) GOLD `dataset_gold_20261022` dev i niewykorzystywany do strojenia test; (b) 255 dokumentów publicznych z manifestów CC; (c) zdania kontrolne z `evidence_2026-10-23/sentences.txt`; (d) syntetyczne 68 zdań wyłącznie jako znany test regresji, **nie nowy holdout**. Mierzyć na finalnym tekście: ciche OSOBA, OSOBA z ostrzeżeniem, nadmaskowane nie-osoby, pytania R1/dokument, uszkodzenia granic/Przywróć, koszt czasu i RAM. Nie mieszać strat OCR z błędami silnika. Raport osobno pokazuje **nowe i utracone** zakrycia OSOBA, z podziałem czy były poprawne.

Minimalne przypadki:
- `Jan Nowak / Jana Nowaka / Nowak` jako ta sama rozpoznana osoba → spójność tokenu, bez sklejenia odrębnych Janów Nowaków.
- `Piotr [nazwisko]` i `[imię] [nazwisko]` w nazwie osoby → nie rozcinać i nie usuwać wcześniejszych trafień (regresja 28).
- `Wczoraj Nowak zlecił`, `Mazur podpisał`, `Świadek Malina zeznała`, `Wnioskodawca Kawa` → `MASK` albo — przy rzeczywistej kolizji — `ASK`, nigdy cichy wyciek.
- `Kawa i herbata zostały`, `Termin wykonania`, `Dziennik Urzędowy`, `Urząd Wojewódzki`, `w Krakowie`, `ul. ...`, `Odwołujący` → bez błędnego OSOBA/R1.
- `Styczeń` w dacie vs `Pani Styczeń` → miesiąc jawny, osoba maskowana; biały wpis samodzielny nie generuje R1.
- Dwa homonimy o innym znaczeniu w jednym dokumencie → różne decyzje per wystąpienie.
- Po `ASK` Guard pokazuje dokładnie **jedną** pozycję, nie maskuje automatycznie, nie blokuje S3; po `MASK` żaden surowy fragment nie zostaje przy tokenie.
- Awaria NER/decydera → zgodne z S3; brak jawnego PII w logach. Pozostałe typy FIRMA/ADRES/NUMER i mapy bez regresji.

**Bramka odbioru (przed kodem kryterium, nie dorabiać po wynikach):** brak nowego cichego wycieku OSOBA na GOLD dev/test; bez utraty potwierdzonych zakryć pełnych osób z bazy; na 255 dokumentach **nie zaakceptować nowej fali +210 błędnych zakryć** z prototypu ani powrotu do 7448 pytań R1. Każdy wzrost zbędnych zakryć / pytań R1 musi być jawnie sklasyfikowany i przedstawiony OWNEROWI, nie chowany w sumie. Brak regresji Przywróć, formatu tokenów, S3 i innych kategorii. Nie ogłaszać procentowej skuteczności z 68 przygotowanych zdań.

Jeśli E1 pokaże, że prosta wspólna decyzja odbiera prawdziwe pełne osoby albo nie ogranicza kosztu pytań, **STOP przed E2**. Nie „naprawiać” wyniku nową autonomiczną regułą lub kolejną warstwą.

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

## 7. Przekazanie

**Codex BRIEF_ONLY r2 (DOPIERO PO C3):** przeczytaj zmiany C1/C2 w tym briefie i jedną decyzję OWNERA dla C3; wyłącznie punktowo wskazane szwy. Bez kodowania, testów, pobierania danych PESEL czy benchmarków. Zweryfikuj wykonalność jednej decyzji na całym spanie przy obecnej kolejności NER/ADRES/FIRMA i braku bezpiecznych offsetów po podmianie; niełamanie decyzji słownika biura; przeniesienie ASK do Guarda bez równoległego R1; definicję białej listy dla par imię–nazwisko; progi i odbiór; S2/S3/S4/S5 i minimalną liczbę zmienianych ownerów. Zwróć `PASS PREIMPLEMENTATION` albo **jedną zamkniętą listę** niejasności/konfliktów. Jeśli istotna decyzja produktowa nadal jest niejednoznaczna, `OWNER_DECISION_NEEDED`, nie dorabiać samodzielnie nowej architektury. Dopiero po PASS → szacunek CC → zgoda OWNERA na koszt → implementacja → niezależny audyt Codexa exact SHA → decyzja OWNERA o merge.
