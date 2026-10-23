# LYNX-OSOBA-REDESIGN — aktualizacja propozycji CC (2026-10-23)

Uzupełnia `cc_proposal.md` (20.10). Powód powrotu do odłożonego Tasku: pomiar szumu Guarda R1 (22–23.10) i prototypy
„słownik nazwisk w silniku” pokazały w praktyce to, co OWNER powiedział 20.10 („OSOBA to źle napisany silnik, należy mu się jedno
miejsce wykrywania”): każda punktowa poprawka jednej ścieżki wychodzi bokiem w innej. Zadania `LYNX-OSOBA-SURNAME-DICT` i
`LYNX-GUARD-R1-NOISE` (część R1) włączamy tutaj — bez kodu do czasu briefu Architekta.

Dowody i skrypty: `tasks/LYNX-OSOBA-REDESIGN/evidence_2026-10-23/`. Dane wejściowe pomiaru (lokalne, nie w repo): 255 dokumentów
publicznych z manifestów `%TEMP%\lynx_cc_review\status_2210\jobs_realpub.json` i `jobs_pub.json` (BIP, Sejm, UZP, KIO, Codex,
dataset_public KIO, dataset_layout, Pliki testowe), GOLD `backend/dataset_gold_20261022` (dev/test, agregaty), OCR 150 dok.
biurowych (`%TEMP%\lynx_cc_review\guard_a\ocr`). Nazwiska z dokumentów publicznych w tym pliku zamaskowane.

## 1. Fakty z pomiarów (22–23.10)
1. **Szum Guarda R1 (main `2ea3a12`):** 7448 pytań na 255 dok., 3 dotyczyły osoby z gold; KIO 72 pytania/dok. 91% pochodziło z
   `released()` — spaCy niekonsekwentnie bierze terminy procesowe za osobę („Pełnomocnik Przystępującego…” → OSOBA,
   „Odwołujący wniósł…” → nic), Morfeusz poprawnie odrzuca, a krok 2 PACK4 przekazywał Guardowi każde odrzucone słowo, Guard szukał
   go wszędzie. Naprawione wąsko w `LYNX-OSOBA-HANDOFF` (zmergowane 23.10, `631cd10`): 7448 → 902, GOLD bez zmian.
2. **Reszta 902 (analiza Codexa po HANDOFF):** 602 pytania z `_r1` Guarda (Morfeusz zna słowo jako nazwisko): człony nazw urzędowych
   i geograficznych („Dzienniku”, „Polskiej”, „Gdańskim”), funkcje („Wojewody”, „Komornika”), słowa wieloznaczne („Warunków”,
   „Forma”). Codex: rozwiązać kontekstem, nie listą wyciszeń.
3. **Dwuznaczne nazwiska bez kotwicy** („Wczoraj Nowak zlecił…”) nie wystąpiły w żadnym dokumencie pomiaru — wyszły w zdaniach
   testowych CC (`evidence…/sentences.txt`); main: silnik nie zakrywa „Nowak”/„Mazur” (Morfeusz: także słowo pospolite), Guard pyta.
4. **Słownik nazwisk:** lista Mobile `surnames_extended.json` (39k, odmiana generowana Morfeuszem) ma braki i fałszywe formy (np. formy
   innych słów pod rzadkimi nazwiskami). Lepsze źródło: **wykaz PESEL** — dane.gov.pl zbiór 1681 „Nazwiska osób żyjących występujące
   w rejestrze PESEL”, Ministerstwo Cyfryzacji, **CC0**, zasoby 1148808/1148811, stan **2026-01-20**, kolumny `Nazwisko aktualne,
   Liczba` (M ~408 tys., K ~420 tys. wierszy; ≥100 osób: ~53 tys. nazwisk M+K). Dopasowanie bez generowania odmian: słowo → lematy
   Morfeusza (+ proste reguły końcówek dla słów nieznanych: -skiego→-ski, -skiej→-ska…) → PESEL. Sprawdzone: Nowaka→nowak 198 125,
   Wróbla→wróbel 49 102, Jelenia→jeleń 4 155, Bociana→bocian 3 674; Odwołującego/Powódka/Protokolant → brak w PESEL.
5. **Biała lista (zatwierdzona przez OWNERA 23.10):** nazwisko noszone przez 100–999 osób **i** słowo występuje małą literą w ≥2
   pismach (445 dok.; bez e-maili/www) → 316 słów (`evidence…/biala_lista_pesel_zatwierdzona.csv`, skrypt `pesel_white2.py`):
   dzień, podstawa, termin, osoba, stan, warunek, cel, brak, forma, cena, strona, sposób, art, kopia, izba, poseł, komornik…
   Porównanie z listą liczoną na słowniku Mobile: wspólne tylko 200 — lista PESEL łapie 116 słów biurowych pominiętych przez
   Mobile, odrzuca 113 sztucznych wpisów.
6. **Prototypy „słownik w silniku” (`evidence…/prototyp_surname_dict.py`):**
   - tylko na kandydatach spaCy: 255 dok. +16 zakryć (2 osoby, 14 zbędnych), GOLD bez zmian — osoby z pytaniem Guarda w GOLD
     („Pan Jeleń”, „Bocian potwierdził”) w ogóle nie są kandydatami spaCy;
   - z przeszukiwaniem tekstu słownikiem PESEL (zamiast top1000): GOLD osoby z pytaniem Guarda **9→3 (dev), 13→1 (test)**, zbędne
     69→72 / 152→157; ale 255 dok. **+210 zakryć** (głównie miejscowości „w R*****u”, przymiotniki urzędów „Wojewódzki” ×37, ulice,
     słowa urzędowe) — przeszukiwanie przepuszcza słowa przez starą regułę silnika („nazwisko w Morfeuszu ∧ nie pospolite → zakryj”);
   - wersja z jedną funkcją rozstrzygającą (miejscowość/ulica/człon nazwy/miesiąc → nie): +75 zakryć, ale **28 zakryć z main
     znika** — w tym prawdziwe osoby (np. „Piotra G*********”, „M*******i”, „A*****i”): funkcja oceniała pojedyncze słowo i nie
     wiedziała, że spaCy rozpoznał „imię + nazwisko” razem → uznała sąsiada z wielkiej litery za człon nazwy urzędu.
   - **Wniosek:** decyzja musi widzieć **całych kandydatów** (para imię–nazwisko, wszystkie warstwy naraz), inaczej jedna poprawka
     odbiera to, co dawała inna ścieżka. To potwierdza projekt z 20.10.
7. **HerBERT** (`herbert_check.py`, `lexedit/herbert-polish-legal-ner`, min 0,7 domyślnie, tu surowe wyniki): na 21 zbędnych zakryciach
   prototypu — „nic” (słusznie), „z Polakami za Granicą” → ORG; osoby z pism: 1 dobrze (0,66), 1 fragment (0,36). Na zdaniach
   kontrolnych **gubi pojedyncze nazwiska**: „Wczoraj Nowak zlecił…”, „Mazur podpisał…”, „Pismo od Wróbla…” → nic; „Bocian” →
   fragment „an” 0,48. Jako sędzia cofający zakrycie przepuściłby nazwiska; zgodne z ustaleniem 19.10 (ostatnia warstwa, nigdy nie
   cofa decyzji).

## 2. Zasady uzgodnione z OWNEREM 22–23.10 (wejście dla briefu)
- Silnik decyduje, co zakryte; Guard ostrzega i pokazuje resztę — nie jest drugą warstwą maskowania.
- **Słownik nazwisk ma najwyższą wagę** (OWNER 23.10: „wtedy Nowak przestanie dokuczać”): samo „jest w słowniku” wystarcza do zakrycia,
  chyba że konkretny dowód przeciw (niżej). W pismach biurowych „Mazur”, „Bocian” z wielkiej litery to nazwisko, nie taniec/ptak.
- **Próg 1000:** nazwisko noszone przez ≥1000 osób zostaje nazwiskiem (zakrycie za dużo — użytkownik odkryje; wyciek jest cichy).
- **Miesiące** (Styczeń…Grudzień) są nazwiskiem **tylko z kotwicą** — bez niej nic (nagłówki, daty).
- Słowa z białej listy wyłączone i z zakrywania, i z pytań Guarda.
- Przy wątpliwości: zakryć albo zapytać, nigdy cicho przepuścić.

## 3. Dowody za / przeciw (rozwinięcie pkt 2 propozycji z 20.10)
**Za:** (1) słownik — nazwisko PESEL / imię (najwyższa waga); (2) kotwica — Pan/Pani, dr, mec., etykieta danych osobowych
(„Imię i nazwisko:”, „Pełnomocnik:”, „Wnioskodawca:”), podpis; (3) imię lub inicjał obok („Jan Nowak”, „J. Nowak”, „Nowak Jan”);
(4) to samo nazwisko rozpoznane wcześniej w dokumencie w pełnej postaci; (5) słownik biura użytkownika; (6) składnia — słowo jest
podmiotem czynności osoby (Morfeusz: czasownik fin/praet w liczbie pojedynczej, nie „być”: „Nowak zlecił”, „Malina zeznała”);
(7) spaCy / HerBERT — **słaby** dowód (sam nie wystarcza ani do zakrycia, ani do pytania Guarda).
**Przeciw:** (1) biała lista; (2) Morfeusz: wyłącznie pospolite i brak w słowniku nazwisk („Odwołującego”); (3) nazwa funkcji
(lista wyzwalaczy jak NKJP); (4) człon nazwy własnej („Dziennik Urzędowy”, „Urząd Wojewódzki”) — **ale nie, gdy sąsiad jest imieniem
albo nazwiskiem ze słownika** (para osób, dzisiejszy błąd 28 utraconych zakryć); (5) miejscowość / ulica w kontekście miejsca
(„w Rybniku”, „ul. … 12”); (6) miesiąc/dzień tygodnia bez kotwicy; (7) nie-słowo (brak samogłoski, cyfry, „……”, nagłówek WIELKIMI
LITERAMI bez innych dowodów); (8) mała litera; (9) początek zdania bez czynności osoby („Konieczne jest…”, „Kawa i herbata zostały…”).
**Decyzja:** mocny dowód za i brak mocnego przeciw → zakryj; brak dowodu za poza modelem albo mocny przeciw → nic; dowody w obie strony
→ **pytanie Guarda**. Guard R1 pyta dokładnie o wynik „zapytaj” z tego samego miejsca (koniec osobnego strojenia R1).

## 4. Stan wiedzy (to nie jest nowy problem)
- **Microsoft Presidio** (otwarte narzędzie do PII): wykrycie ma punktację; słowa kontekstu w oknie 5 wyrazów przed podnoszą wynik
  (domyślnie +0,35, min. 0,4), listy deny/allow, próg odcięcia —
  https://raw.githubusercontent.com/microsoft/presidio/main/presidio-analyzer/presidio_analyzer/context_aware_enhancers/lemma_context_aware_enhancer.py ,
  https://deepwiki.com/microsoft/presidio/3.1-analyzer-component
- **NKJP** (Savary, Piskorski, IPI PAN 2010): słowniki nazwisk z liczbą nosicieli, imion, przymiotników od nazw miejsc; ~476 słów-
  wyzwalaczy i ~1500 form nazw funkcji jako dowody w regułach; osoby: precyzja 0,85, kompletność 0,69 (same reguły gubią ~30%) —
  https://nkjp.pl/settings/papers/sav-pisk-iis10.pdf
- **PersonNames** (ok. 346 tys. imion i nazwisk ze znacznikiem „także zwykłe słowo”), hybrydy sieć + słowniki dla polskiego —
  https://www.degruyterbrill.com/document/doi/10.1515/psicl-2019-0010/pdf , https://arxiv.org/pdf/1811.10418
- **CLARIN-PL Anonimizator** (model WiNER) — https://wiki.clarin-pl.eu/pl/nlpservices/list/anonymizer ; **GALL** w sądach
  administracyjnych podpowiada zakrycia człowiekowi (2× szybciej i bezpieczniej niż ręcznie) —
  https://czasopisma.uksw.edu.pl/index.php/kpp/article/view/3962
- Wniosek CC: punktacja dowodów z progiem (zakryj / zapytaj / nic) = sprawdzony wzorzec (Presidio); słownik z liczbą nosicieli +
  wyzwalacze + przymiotniki geograficzne = NKJP; spaCy zostaje jako słaby dowód, Guard jako siatka.

## 5. Pytania do Architekta (uzupełnienie listy z 20.10)
1. Skala punktów i progi (stałe vs prosty model na śladzie dowodów) — z wagą słownika najwyższą (OWNER) i progiem 1000.
2. Miejsce w łańcuchu: kandydaci = spany spaCy + przeszukiwanie słownikiem PESEL + słownik biura, oceniani **razem** (pary imię–
   nazwisko), przed adresem/firmą czy po (kolizje miejscowość/ulica — wyniki pkt 1.6).
3. Kontrakt z Guardem: Guard R1 zastąpiony wynikiem „zapytaj”; los `released()` i `_r1`.
4. Dane: plik PESEL w repo (CC0, ~0,8 MB dla ≥100 osób + biała lista) i proces odświeżania (raz w roku?).
5. Etapy i rozmiar (OWNER: mniej szwów, ale >150 l. wymaga zgody); kryteria odbioru: GOLD (ciche OSOBA, zbędne), 255 dok. publicznych
   (nowe/utracone zakrycia z oceną), zdania kontrolne, pytania Guarda/dok.

## 6. Cel produktu (OWNER 23.10, wybór spośród opcji CC: „model rozumiejący” vs „człowiek decyduje w szarej strefie”)
OWNER: „pogodzić się z tym, że człowiek decyduje 2–4 razy na dokument; robimy wszystko, by śmieci nie trafiały do Guarda i nie było
idiotycznego FP”. Ocena CC: zgodne ze sprawdzonym wzorcem (GALL w sądach administracyjnych — system podpowiada, człowiek decyduje;
Presidio — pasmo niepewności), program zostaje deterministyczny i wytłumaczalny (RODO), bez kosztu modelu (rozmiar, czas, licencja,
powtarzalność). **Kryteria odbioru projektu:**
1. pytania Guarda (R1/osoby): średnio **2–4 na dokument** w zbiorach odbiorczych;
2. **zero oczywistych śmieci** wśród pytań: słowa ról i funkcji, człony nazw urzędów/miejsc, skróty i nie-słowa, słowa z białej
   listy, zapis małymi literami (warunek przeciw „zmęczeniu alarmami” — użytkownik klikający „Zostaw” odruchowo przepuści prawdziwe
   nazwisko);
3. **żadne prawdziwe nazwisko nie przechodzi cicho** (bez zakrycia albo pytania) w zbiorach odbiorczych; FP po stronie zakrycia
   akceptowalne (OWNER: zakryć za dużo > wyciek; użytkownik odkryje, „Zawsze jawne” ogranicza powtórki);
4. model rozumiejący zdanie (np. lokalny Bielik jako sędzia szarej strefy) **poza zakresem** — wpis w `ODLOZONE.md`; projekt nie musi
   go przewidywać, ale nie powinien go wykluczać (punkt decyzji „zapytaj” jako jedyne wejście).

## 7. Ryzyko dopasowania do naszych zbiorów i kontrola (pytanie OWNERA 23.10)
**Różnorodność dziś:** GOLD dev 40 dok., 7 rodzajów (umowa 8, faktura 7, pismo/decyzja 7, wezwanie 5, protokół 5, pełnomocnictwo 3,
e-mail 5), 120 różnych osób/nazwisk — wg PESEL: ≥10 tys. 18, 1000–9999 62, 100–999 20, <100 17, brak 3; trudna klasa
(`surname_common_word`) tylko w 10 dok. i z powtarzalnych szablonów zdań. Dokumenty publiczne: 255, ~200 różnych osób w gold
(głównie pisma o firmach — dobre do FP, słabe do kompletności osób).
**Ryzyka:** (a) biała lista liczona z tych samych 445 pism, na których mierzymy — słownictwo przetargów/KIO, brak dziedzin
(medycyna, kadry, budowa, księgowość) → FP gdzie indziej i zawyżony wynik; (b) trudna klasa mała i szablonowa → dopasowanie do
szablonu; (c) reguły dopisywane po błędach z naszego zbioru → silnik uczy się zbioru, nie polszczyzny.
**Kontrola (propozycja do briefu):**
1. biała lista z **niezależnego źródła ogólnej polszczyzny** (np. listy frekwencyjne NKJP — dostępność i licencja do sprawdzenia
   przez CC przed użyciem), nasze pisma tylko jako kontrola;
2. rozdzielenie danych: zbiór do strojenia ≠ zbiór odbiorczy (nigdy nie używany przy projektowaniu): GOLD test (CC nie otwiera),
   pl-pii (3000 syntetyków z osobami), testy/`dataset_clean` Mobile (300 z gold), dokumenty OWNERA (agregaty);
3. **nowy GOLD od innego autora**, inne szablony, brakujące dziedziny; zasady OWNERA: autor pisze dokument i gold, osobny
   weryfikator, bez powtarzania encji, minimalne liczby na typ;
4. każdy wyjątek uzasadniony ogólną zasadą (słownik, liczba nosicieli, budowa zdania), nie pojedynczym dokumentem;
5. wyniki raportowane osobno per dziedzina/rodzaj dokumentu.
