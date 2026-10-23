# LYNX-OSOBA-REDESIGN — brief Architekta v1 (23.10.2026)

**Status: propozycja kontraktu do Codexa BRIEF_ONLY; bez implementacji i bez zgody na merge.**
Źródła: `cc_proposal.md` (20.10), `cc_proposal_update_2026-10-23.md` i `evidence_2026-10-23/` na gałęzi zadania; `BOARD.md` wiersz `LYNX-OSOBA-REDESIGN` (23.10); zamrożone `arch/spec.md` S1–S5. Bazę implementacji CC musi odświeżyć po prechecku; nie zakładać, że main jest nieruchomy.

## 1. Problem i granice dowodów

Dziś automatyczne decyzje OSOBA podejmuje kilka ścieżek niezależnie (spaCy w `ner_layer.py`, propagacja/inicjały/słowniki w `layers/ner_adapter.py`); Guard ma dodatkowe własne R1. Skutkiem są jednocześnie zbędne zakrycia, ciche pozostawienia osób i niepotrzebne pytania.

Na pomiarach CC: `LYNX-OSOBA-HANDOFF` zmniejszył pytania R1 z **7448 do 902** na 255 dokumentach bez zmiany GOLD — nie przypisywać tego zysku przyszłemu redesignowi. Pozostałe R1 obejmują człony nazw urzędów, miejscowości i nazwy funkcji. Eksperyment z szerokim słownikiem PESEL poprawiał osoby kierowane do Guarda w GOLD (dev 9→3, test 13→1), lecz generował **+210** dodatkowych zakryć na 255 dokumentach. Próba oceny pojedynczego słowa ograniczała te zakrycia, ale **usuwała 28 wcześniejszych zakryć**, w tym rzeczywistych osób w parach imię–nazwisko. To obserwacje prototypów, nie wyniki produkcyjnej nowej architektury.

Cel: **jedna automatyczna decyzja OSOBA na całym wystąpieniu w kontekście dokumentu**, wykorzystująca istniejące źródła dowodów. Nie chodzi o dokładanie PESEL jako kolejnej ścieżki automatycznie zakrywającej obok starego NER.

## 2. Kontrakt wyniku

Dla kandydata w danym miejscu tekstu decyzja jest dokładnie jedna:
- `MASK`: wystarczające dowody osoby i brak rozstrzygającego dowodu przeciw → maskuj poprzez istniejący `TokenAllocator`, mapę i Przywróć.
- `ASK`: wiarygodne podejrzenie OSOBA z nierozstrzygniętą kolizją dowodów → **jedno ostrzeżenie R1 w Guardzie**, nie automatyczne maskowanie.
- `PASS`: wiarygodnie nieosobowe wystąpienie albo brak przesłanek pozwalających uznać je za kandydata → pozostaw jawne, bez pytania R1. Nie zastępuje kontroli pozostałych R2–R5/HIGH/MEDIUM/MAP_LEAK.

Decyzja należy do **wystąpienia/spanu**, nie do ciągu znaków globalnie. `Róża` jako osoba, kwiat i nazwa lokalu mogą dać różne decyzje. Pary `Jan Kowalski` / `Jana Kowalskiego` oceniać jako całość; nie wyciszać pełnej osoby z powodu pojedynczego członu. Nie scalać różnych osób o tym samym nazwisku. Jeśli wiarygodnie ta sama osoba występuje w odmianach, zachowuje jeden token; kanoniczny mianownik w Przywróć jest dopuszczalny. Wierność granic tokenu i dosłownej wartości mapy pozostaje obowiązkowa.

### Dowody i pierwszeństwo (reguły deterministyczne v1, bez uczenia wag)

Kandydaci: niezakryte całe spany z istniejącego spaCy, z przeglądu nazwisk PESEL (również samodzielne nazwiska poza spaCy), z istniejących imion i słownika biura; rozpatrywać sąsiadujące imię–nazwisko, inicjał–nazwisko i odmianę jako możliwy **jeden span**. Kandydata badać na kontekście, zanim utraci go przez podmiany ADRES/FIRMA/INSTYTUCJA; ostatecznie nie naruszać spanów już przejętych przez token strukturalny. Sam CAPS lub sama etykieta spaCy nie wystarcza do `MASK` ani automatycznego `ASK`.

**Mocne ZA:** jawna etykieta/kotwica osoby (Pan/Pani, podpis, imię i nazwisko, świadek, osoba pełniąca funkcję), para imię–nazwisko lub inicjał–nazwisko, wiarygodne wcześniejsze pełne wystąpienie tej osoby w dokumencie, świadomy wpis OSOBA w słowniku biura. Nazwisko PESEL **≥1000 nosicieli** przy zapisie nazwy własnej jest mocnym ZA również samotnie, **o ile brak konkretnego silnego PRZECIW**. Słownik nazwisk ma wyższą rangę od samotnego wskazania spaCy. `Nowak`, `Mazur`, `Bocian` w zdaniach o działaniach ludzi to kandydaci rzeczywiści także przy znaczeniu pospolitym.

**Słabsze ZA / kolizja:** PESEL 100–999 bez niezależnej kotwicy, niejednoznaczne rozpoznanie fleksji oraz składnia „nazwisko + czynność osoby” (czasownik osobowy Morfeusza, nie samo „być”) mogą wspierać `MASK` lub prowadzić do `ASK`; nie są pretekstem do hurtowego zakrywania każdego słowa wielką literą. Sam spaCy PER jest słabym sygnałem.

**Mocne PRZECIW:** konkretne wystąpienie jako człon instytucji, firmy, adresu, nazwy geograficznej/ulicy w kontekście miejsca, termin prawny/funkcja, nie-słowo/OCR lub nagłówek bez niezależnej przesłanki osoby. Samo sąsiedztwo innego słowa wielką literą NIE jest dowodem instytucji: `Piotra G*********` oraz `Anna Nowak` należy ocenić jako pełną parę. Wyraz na początku zdania NIE jest globalnie wyłączony — `Nowak zlecił` to przypadek dodatni, `Kawa i herbata zostały` ujemny.

**Biała lista 316 zaakceptowanych słów** z `evidence_2026-10-23/biala_lista_pesel_zatwierdzona.csv`: odrzuca **samodzielne zgłoszenie tego słowa jako nazwiska** zarówno w silniku, jak i R1. Nie wolno jej użyć do przecięcia potwierdzonej pełnej osoby: złożony span ocenić jako całość (np. imię + nazwisko). Codex ma jawnie ocenić tę granicę wobec literalnej zasady OWNERA „słowa z białej listy wyłączone z maskowania i pytań”.

**Miesiące:** `Styczeń…Grudzień` jako samotne nazwy miesięcy → `PASS`; jako nazwiska tylko z niezależną kotwicą osoby. Mała litera bez wyraźnej kotwicy osoby nie staje się OSOBA. Samo nazwisko rzadkie lub nieobecne w PESEL nie może być automatycznie uznane za nie-PII, gdy kontekst wskazuje osobę → co najmniej `ASK`.

**Kolejność rozstrzygnięcia:** 1) już świadomie zamaskowane w profilu użytkownika i spany struktur innych kategorii pozostają pod ich obecnym ownerem; 2) cała para / mocne kotwice osoby; 3) kontekstowo pewne wyłączenia; 4) samodzielne nazwisko PESEL z progiem 1000; 5) kolizje → `ASK`; 6) brak przesłanek → `PASS`. Nie wolno stosować „dowodu przeciw” z członu instytucji do nazwiska w niezależnej, rozpoznanej parze osoby.

**Nie implementować w v1** regresji logistycznej, uczenia progów, zewnętrznego NER, arbitra LLM ani automatycznego odświeżania list. Jeśli prosty deterministyczny zestaw priorytetów nie przejdzie kontrprób, STOP i wrócić z pomiarem, nie dorabiać dziesiątek wyjątków.

## 3. Minimalny szew istniejącego pipeline

Aktualnie `pipeline_new.py` wywołuje `extract_ner_results` **przed adresem**, a `apply_ner_layer` po adresie. Nowy owner decyzji (proponowane `backend/person_decision.py`) ma **raz** zebrać/ocenić kandydatów OSOBA z pełnym kontekstem, zanim podmiany odbiorą relację imię–nazwisko. Zwraca tylko `MASK / ASK / PASS` dla spanów wraz z powodami/kodem dowodu do testów (bez logowania jawnego tekstu). Nie zmienia API S2 ani typów tokenów.

`ner_layer.py` i `layers/ner_adapter.py`: dotychczasowe źródła OSOBA (spaCy, lematy, słownik, propagacja, inicjały) mają dostarczać kandydatów/dowody lub zastosować **decyzję z jednego ownera**; nie mogą po decyzji `PASS` ani `ASK` ponownie autonomicznie zakryć tego samego fragmentu. Zachować dotychczasowy właściciel FIRMA, pozostałe warstwy i priorytety tokenów. Profilowe, **świadomie dodane** encje OSOBA z `trie_layer` pozostają nadrzędną decyzją użytkownika, nie są drugi raz klasyfikowane.

Przed maskowaniem zweryfikować aktualne granice spanów po OCR/warstwach. **Nie wolno zastosować zapamiętanych offsetów z tekstu sprzed zamiany ADRES** do tekstu po podmianie; użyć istniejących mechanizmów mapowania albo odtworzyć span w bieżącym tekście bez niejednoznacznego globalnego `str.replace`. Żaden `MASK` OSOBA nie przecina tokenu ADRES/FIRMA/INSTYTUCJA/NUMER. Bez nowych, równoległych map tokenów.

`guard_residue.py`: R1 ma pokazywać **tylko `ASK` tego samego ownera** dla nadal jawnych wystąpień, z przeliczeniem pozycji na finalny wynik. Usunąć równoległe wyrokowanie R1 przez `_r1` i `released()` po integracji, nie pozostawić dwóch źródeł tych samych pytań. R2–R5, HIGH/MEDIUM/MAP_LEAK, zachowanie UI, allowlista i S3/S4/S5 pozostają bez zmian.

`herbert_net.py`: pozostaje **po silniku, przed Guardem, domyślnie OFF**; może dołożyć rozpoznanie tylko na nadal jawnych spanach, **nie cofa `MASK`**. Osobny pomiar ON/OFF później, bez strojenia HerBERT i bez włączania go przy okazji tego Tasku.

Jeżeli obie ścieżki `USE_NEW_PIPELINE` są rzeczywiście dostępne dla użytkownika, CC musi zapewnić zgodny kontrakt na każdej aktywnej ścieżce albo zaproponować jawny wybór jednej; nie pozostawiać ukrytej drogi z dawnymi samodzielnymi decyzjami OSOBA.

## 4. Dane i koszty

Źródło nazwisk: ministerialny zestaw PESEL [dane.gov.pl zbiór 1681](https://dane.gov.pl/pl/dataset/1681) — zasoby 1148808 i 1148811, stan danych **20.01.2026**. Wziąć tylko agregaty nazwisk i liczbę nosicieli, wersję M+K, znormalizować deterministycznie. Artefakt produkcyjny (proponowane `backend/person_surnames_pesel_20260120.json`) i lista 316 muszą mieć źródło, datę, licencję, sumy SHA256 źródeł i odtwarzalny skrypt przygotowania **bez zależności sieciowej w czasie pracy aplikacji**. Pliku tego *nie ma jeszcze* w repo — prototyp CC nie jest gotowym assetem produkcyjnym. Limit pliku/ładowania zmierzyć, nie zgadywać. Aktualizacje wyłącznie osobnym Taskiem po rocznej publikacji PESEL, nie samoczynnie.

Skala i progi: zamiast arbitralnych punktów 0,35 / 0,7 zastosować kolejność silnych i słabych dowodów z §2; **1000** pozostaje progiem produktowym dla samodzielnego nazwiska, **100** dolnym progiem danych pomocniczych z propozycji CC. Reguły końcówek i lematyzacja nie mogą dopasowywać innych słów jako nazwisk bez kontekstu; rejestrować warianty tylko, gdy są rzeczywistymi formami dopasowanego kandydata.

Rozmiar i podział: **jeden Task**, dwa wewnętrzne kroki CC: E1 ślad decyzji/shadow na identycznym wejściu (nic nie maskuje w trybie próby), E2 przełączenie ownera OSOBA + wyłączenie starych autonomicznych ścieżek + Guard R1. Po prechecku CC podaje budżet plików, linii, czasu i RAM; **>150 nowych/zmienionych linii wymaga zgody OWNERA**. Nowe reguły w jednym małym ownerze, nie powiększać bez końca `ner_layer.py`, `ner_adapter.py`, `pipeline.py`. E1 to bramka porównawcza, nie dodatkowa infrastruktura produktu.

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

- backend/person_decision.py (nowy, owner jednej automatycznej decyzji)
- backend/layers/ner_adapter.py (wyłączenie autonomicznych OSOBA i aplikacja decyzji)
- backend/ner_layer.py (spaCy jako źródło kandydatów; FIRMA niezmieniona)
- backend/osoba_not_person.py (wspólne dowody/wyłączenia i odejście od osobnego released)
- backend/guard_residue.py (R1 z `ASK`, pozostały Guard bez zmian)
- backend/pipeline_new.py (szew pełnego kontekstu i ostatecznej aplikacji)
- backend/pipeline.py (tylko jeśli aktywna legacy ścieżka wymaga zgodności)
- backend/person_surnames_pesel_20260120.json (nowy, z manifestem/odtwarzalnym generatorem)
- backend/tests/test_person_decision.py (kontrpróby i integracja)
- tasks/LYNX-OSOBA-REDESIGN/round_01/implementation/DELIVERY.md (po kodzie)
- tasks/LYNX-OSOBA-REDESIGN/brief.md (ten kontrakt)

Nie zmieniać S2, `arch/spec.md`, `FROZEN.lock`, FIRMA, OCR, UI, allowlisty, HerBERT ON/OFF, instalatora, ani pełnego rejestru decyzji. Usunięcie starej ścieżki tylko po pokazaniu nowego ownera i przejściu testów.

**WHERE_MAP:** REQUIRED przed kodem, TARGETS: `backend/ner_layer.py::process_ner`; `backend/layers/ner_adapter.py::apply_ner_layer`; `backend/layers/ner_adapter.py::_apply_dictionary_names`; `backend/osoba_not_person.py::single_osoba_evidence`; `backend/guard_residue.py::collect_warnings`. Powód: przenosimy/wyłączamy dotychczasowe owners decyzji OSOBA, nie możemy zostawić ukrytych równoległych zakryć.

## 7. Przekazanie

**Codex BRIEF_ONLY:** czytaj brief, dwie propozycje CC i wyłącznie punktowo wskazane szwy. Bez kodowania, testów, pobierania danych PESEL czy benchmarków. Zweryfikuj wykonalność jednej decyzji na całym spanie przy obecnej kolejności NER/ADRES/FIRMA i braku bezpiecznych offsetów po podmianie; niełamanie decyzji słownika biura; przeniesienie ASK do Guarda bez równoległego R1; definicję białej listy dla par imię–nazwisko; progi i odbiór; S2/S3/S4/S5 i minimalną liczbę zmienianych ownerów. Zwróć `PASS PREIMPLEMENTATION` albo **jedną zamkniętą listę** niejasności/konfliktów. Jeśli istotna decyzja produktowa nadal jest niejednoznaczna, `OWNER_DECISION_NEEDED`, nie dorabiać samodzielnie nowej architektury. Dopiero po PASS → szacunek CC → zgoda OWNERA na koszt → implementacja → niezależny audyt Codexa exact SHA → decyzja OWNERA o merge.
