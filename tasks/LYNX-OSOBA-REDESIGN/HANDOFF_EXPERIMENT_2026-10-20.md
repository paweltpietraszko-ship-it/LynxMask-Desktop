# HANDOFF / DOWÓD — OSOBA, test wieloznaczności (20.10.2026)

**To materiał do badania, nie zatwierdzony brief ani PRODUCT_TRUTH.** Repo `paweltpietraszko-ship-it/LynxMask-Desktop`, Task `LYNX-OSOBA-REDESIGN`. Dane całkowicie syntetyczne. Przekazany przez OWNERA wynik Mobile i fragment mapy Desktop; nie są to wyniki uruchomione samodzielnie przez Architekta. Nie dodawać do produkcyjnych profili. Zachować go jako stan przed zmianami.

## Stan i kolejność

- `BOARD.md` na main jest nadrzędnym źródłem **bieżącego statusu**, nie ten plik. Odczyt 20.10: `LYNX-PHOTO-CHAIN` — CC ma zgodę OWNERA na implementację pod flagą OFF (~370 l. z testami), nadal niezatwierdzone progi/aktywacja (wiersz `OWNER_DECISION_NEEDED`); `LYNX-OSOBA-REDESIGN` — propozycja CC do briefu Architekta (wiersz `READY_FOR_ARCHITECT`). Nie zaczynać OSOBA równolegle z trwającą integracją OCR bez świadomego rozdzielenia regresji.
- Główne źródło planu CC: `tasks/LYNX-OSOBA-REDESIGN/cc_proposal.md` (w tej gałęzi; sprawdzić aktualny SHA). Wspólny cel: kandydaci, dowody za/przeciw, **jedno miejsce podejmowania decyzji** dla OSOBA. HerBERT **na końcu, jako siatka na nadal jawne fragmenty**, nie konkurent/sprawca cofania wcześniejszych masek. Zmiana S4 Guarda jest osobna i wymaga decyzji OWNERA oraz zmiany zamrożonego `arch/spec.md`.
- Rozszerzenia późniejsze poza bieżącym scope: specjalistyczna lokalna klawiatura/Compose dla Androida bez zastępowania Gboarda oraz CLI/Batch dla folderów i baz danych. Są w sekcji `Kierunki zastosowania` w BOARD, nie implementować teraz.

## Hipoteza OWNERA i propozycja Architekta

OWNER proponuje, aby encja **udowadniała, że jest OSOBA**, zamiast być maskowana przez dowolną warstwę. Sygnały: duża litera, imię/nazwisko w słowniku, polskie końcówki fleksyjne, sąsiedztwo imienia lub drugiego słowa z wielkiej litery, zwroty pan/pani/dyrektor. Rozszerzenie Architekta: dowody *przeciw* (tytuł, firma, adres, termin techniczny, kwiat/zwierzę/owoc, nagłówek); sygnały skorelowane nie mogą być naiwnie sumowane. **Słowniki, spaCy i Morfeusz proponują kandydatów; dopiero jedno miejsce decyduje dla konkretnego wystąpienia.** Przy niepewności przyszły Guard pokazuje człowiekowi fragment; obecny S4 nie jest jeszcze tym mechanizmem. Rozwiązania, wagi i progi pozostają hipotezą do falsyfikacji — nie implementować w ciemno.

Ważne: rozdzielić (A) wykrycie kandydata, (B) ustalenie znaczenia tego wystąpienia, (C) identyfikację i ponowne użycie tokenu. Identyczne słowo `Róża` jako kwiat, projekt, lokal i osoba **nie musi oznaczać tego samego referenta**. Nie wolno automatycznie utożsamiać tokenów semantycznie na podstawie samych bajtów. Przed rozstrzygnięciem skutków dla mapy i `Przywróć` wymagana jest decyzja produktowa.

## Obserwacje testu — nie pomijać przy briefie

Gold: 68 celowo trudnych zdań (36 `ZAKRYJ` dla wskazanego fragmentu, 32 `ZOSTAW` jako OSOBA; `FIRMA`/`ADRES` w odpowiednich zdaniach dopuszczalne). **Jednostka oceny to wskazany fragment w określonym zdaniu, NIE sama lista tokenów.** Wynik Mobile poniżej pochodzi z ręcznego wklejenia przez OWNERA. Wstępna analiza 20.10, do niezależnej weryfikacji parserem/okiem na tej wersji testu:
- Wśród 32 `ZOSTAW`, **18** celowo nieosobowych wystąpień ma `OSOBA` (ID 01,03,05,07,11,13,15,17,19,21,25,28,31,32,34,52,54,59). To błędy nadmaskowania w specjalnie trudnym zbiorze, nie wskaźnik produkcyjny.
- Wśród 36 `ZAKRYJ`, **5** ma jawny fragment, którego Mobile nie zakrył (10,24,41,51,56); ID 65 jest **częściowy**: `Anna` zakryta, `Maj` jawne. ID 33 uszkodzony: `OSOBA_009y` — rozdzielić uszkodzenie granicy tokenu od błędu klasyfikatora.
- Pozostałe anomalie **nie zaliczają się do samej klasyfikacji OSOBA**: ID 14 `imieOSOBA_031` w środku słowa, ID 42/43 `KWOTA_... anowna` (uszkodzenie `Szanowna`), ID 39/47/48/49 wieloczłonowe nazwiska rozbite na wiele tokenów, ID 59 tytuł książki błędnie maskowany. Zachować jako findingi fidelity/token-boundaries, nie łatać wszystkie w jednym silniku OSOBA.
- Mobile **zachowuje** nagłówki 61–64 bez maskowania; Desktop w przekazanej *mapie* ma `OCZEKIWANA` jako `OSOBA_022`. **Dla Desktop dostępna jest tylko mapa**, nie wynik zdanie-po-zdaniu — zakaz obliczania z niej FP/FN per 68.
- Przy `Róża` Mobile używa jednego `OSOBA_021` dla wielu znaczeń (01,34,52,53,54); podobny problem `Malina` (03/04/32). To wskazuje na mapowanie po pisowni, a nie rozstrzygnięcie per wystąpienie. Wynik końcowy `Przywróć` może tekstowo odtwarzać słowo, lecz nie odtwarza poprawnej etykiety znaczenia; oceniać oba aspekty osobno.
- Ten syntetyczny zbiór **nie jest niezależnym holdoutem** po ręcznym obejrzeniu wyników. Nie stroić pod niego a potem ogłaszać na nim obiektywny PASS. Zbudować nowe, odłożone dokumenty z kontekstem poza kontrolowanymi parami zdań oraz ustalone golden Mobile.

## Pary kontrolne (oryginalny plik wejściowy, 68 wierszy)

Skopiuj wyłącznie linie 01–68 do własnego TXT; dwa zdania nagłówka ze starego TXT nie są wymagane do testowania. Nie doklejać oczekiwań do tego samego wejścia.

```text
01. Róża zakwitła rano na rabacie.
02. Pani Róża odebrała dokument w sekretariacie.
03. Malina dojrzała na krzewie przy płocie.
04. Malina podpisała zgodę na wycieczkę.
05. Jagoda spadła z krzewu podczas zbiorów.
06. Jagoda odebrała telefon od kierownika.
07. Pola uprawne zostały nawodnione przed żniwami.
08. Pola podpisała formularz w recepcji.
09. Maj był w tym roku chłodny i deszczowy.
10. Maj przekazał protokół do archiwum.
11. Baran beczał przy ogrodzeniu pastwiska.
12. Baran uczestniczył w naradzie zespołu.
13. Lis zakradł się do kurnika nocą.
14. Lis podpisał decyzję w imieniu komisji.
15. Kruk siedział na suchej gałęzi.
16. Kruk kierował kontrolą magazynu.
17. Wrona dziobała okruchy na chodniku.
18. Wrona zatwierdziła rachunek przed południem.
19. Sikora przyleciała do karmnika.
20. Sikora udzieliła wyjaśnień podczas przesłuchania.
21. Wróbel ćwierkał pod oknem.
22. Wróbel odebrał wezwanie z urzędu.
23. Kamień spadł z murku na chodnik.
24. Kamień kierował pracami zespołu.
25. Mak zakwitł na skraju pola.
26. Mak wręczył kierownikowi dokumenty.
27. Nowak przygotował raport finansowy.
28. Firma Nowak przygotowała raport finansowy.
29. Kowalski Sp. z o.o. wystawiła fakturę.
30. Kowalski przedłożył fakturę do podpisu.
31. Zakład Kowalski zajmuje się obróbką metali.
32. Spółka Malina i Synowie prowadziła księgowość.
33. W sprawie pana Maliny przeprowadzono kontrolę.
34. W kawiarni Róża sprzedawano świeże ciasta.
35. Pani dyrektor podpisała polecenie służbowe.
36. Pani dyrektor Anna Nowak podpisała polecenie służbowe.
37. W rozmowie wystąpił pan Jan Kowalski.
38. Sekretarz zarządu zaakceptował protokół.
39. Sekretarz zarządu Piotr Lis zaakceptował protokół.
40. Stanowisko dyrektora jest nieobsadzone.
41. Dyrektor Zielony przyjął interesantów.
42. Szanowna Pani Dyrektor, proszę o odpowiedź.
43. Szanowna Pani Dyrektor Nowak, proszę o odpowiedź.
44. Z panią Marią Kowalską uzgodniono nowe warunki.
45. Pismo skierowano do Marii Kowalskiej.
46. Decyzję przekazano Kowalskiemu osobiście.
47. Jan Paweł Kowalski odebrał dokument w sekretariacie.
48. Pani Ewa-Maria Wiśniewska zgłosiła pomyłkę.
49. Nowak-Kowalska odebrała przesyłkę z urzędu.
50. Pani Nguyen podpisała protokół.
51. Pan de la Cruz przekazał dokumenty.
52. Zespół nadał projektowi nazwę Róża.
53. Róża przygotowała umowę najmu.
54. Róża kwitła na rabacie przez całe lato.
55. Analityk zatytułował wykres Maj.
56. Maj zatwierdził wykres podczas narady.
57. Spotkanie odbędzie się w Nowej Soli.
58. Pani Nowak z Nowej Soli zadzwoniła rano.
59. Bibliotekarz odnalazł książkę pod tytułem Baran i Lis.
60. Autor książki Jan Baran podpisał dedykację.
61. KONTROLA OCZEKIWANA
62. WYNIKI ANALIZY
63. KWOTA I TERMIN
64. DANE OSOBOWE
65. Dane kontaktowe podała Anna Maj.
66. Prezes Andrzej Malinowski przesłał pismo.
67. Prezes ABC Development Sp. z o.o. przesłał pismo.
68. Zastępca dyrektora Ryszard Kaczmarek podpisał protokół.
```

## Klucz oceny (ID ZAKRYJ/ZOSTAW dotyczy tylko wskazanego fragmentu)

```text
01 ZOSTAW Róża
02 ZAKRYJ Róża
03 ZOSTAW Malina
04 ZAKRYJ Malina
05 ZOSTAW Jagoda
06 ZAKRYJ Jagoda
07 ZOSTAW Pola
08 ZAKRYJ Pola
09 ZOSTAW Maj
10 ZAKRYJ Maj
11 ZOSTAW Baran
12 ZAKRYJ Baran
13 ZOSTAW Lis
14 ZAKRYJ Lis
15 ZOSTAW Kruk
16 ZAKRYJ Kruk
17 ZOSTAW Wrona
18 ZAKRYJ Wrona
19 ZOSTAW Sikora
20 ZAKRYJ Sikora
21 ZOSTAW Wróbel
22 ZAKRYJ Wróbel
23 ZOSTAW Kamień
24 ZAKRYJ Kamień
25 ZOSTAW Mak
26 ZAKRYJ Mak
27 ZAKRYJ Nowak
28 ZOSTAW Nowak
29 ZOSTAW Kowalski
30 ZAKRYJ Kowalski
31 ZOSTAW Kowalski
32 ZOSTAW Malina
33 ZAKRYJ Maliny
34 ZOSTAW Róża
35 ZOSTAW Pani dyrektor
36 ZAKRYJ Anna Nowak
37 ZAKRYJ Jan Kowalski
38 ZOSTAW Sekretarz zarządu
39 ZAKRYJ Piotr Lis
40 ZOSTAW dyrektora
41 ZAKRYJ Zielony
42 ZOSTAW Pani Dyrektor
43 ZAKRYJ Nowak
44 ZAKRYJ Marią Kowalską
45 ZAKRYJ Marii Kowalskiej
46 ZAKRYJ Kowalskiemu
47 ZAKRYJ Jan Paweł Kowalski
48 ZAKRYJ Ewa-Maria Wiśniewska
49 ZAKRYJ Nowak-Kowalska
50 ZAKRYJ Nguyen
51 ZAKRYJ de la Cruz
52 ZOSTAW Róża
53 ZAKRYJ Róża
54 ZOSTAW Róża
55 ZOSTAW Maj
56 ZAKRYJ Maj
57 ZOSTAW Nowej Soli
58 ZAKRYJ Nowak
59 ZOSTAW Baran i Lis
60 ZAKRYJ Jan Baran
61 ZOSTAW KONTROLA OCZEKIWANA
62 ZOSTAW WYNIKI ANALIZY
63 ZOSTAW KWOTA I TERMIN
64 ZOSTAW DANE OSOBOWE
65 ZAKRYJ Anna Maj
66 ZAKRYJ Andrzej Malinowski
67 ZOSTAW ABC Development
68 ZAKRYJ Ryszard Kaczmarek
```

## Dosłowny wynik MOBILE przekazany przez OWNERA (nie poprawiać literówek, brak numerów 42/43 w oryginalnym wklejeniu)

```text
01. OSOBA_021 zakwitła rano na rabacie.
02. Pani OSOBA_008a odebrała dokument w sekretariacie.
03. OSOBA_022 dojrzała na krzewie przy płocie.
04. OSOBA_022 podpisała zgodę na wycieczkę.
05. OSOBA_023 spadła z krzewu podczas zbiorów.
06. OSOBA_023 odebrała telefon od kierownika.
07. OSOBA_024 uprawne zostały nawodnione przed żniwami.
08. OSOBA_024 podpisała formularz w recepcji.
09. Maj był w tym roku chłodny i deszczowy.
10. Maj przekazał protokół do archiwum.
11. OSOBA_011 beczał przy ogrodzeniu pastwiska.
12. OSOBA_011 uczestniczył w naradzie zespołu.
13. OSOBA_025 zakradł się do kurnika nocą.
14. OSOBA_025 podpisał decyzję w imieOSOBA_031 komisji.
15. OSOBA_012 siedział na suchej gałęzi.
16. OSOBA_012 kierował kontrolą magazynu.
17. OSOBA_013 dziobała okruchy na chodniku.
18. OSOBA_013 zatwierdziła rachunek przed południem.
19. OSOBA_014 przyleciała do karmnika.
20. OSOBA_014 udzieliła wyjaśnień podczas przesłuchania.
21. OSOBA_015 ćwierkał pod oknem.
22. OSOBA_015 odebrał wezwanie z urzędu.
23. Kamień spadł z murku na chodnik.
24. Kamień kierował pracami zespołu.
25. OSOBA_026 zakwitł na skraju pola.
26. OSOBA_026 wręczył kierownikowi dokumenty.
27. OSOBA_016 przygotował raport finansowy.
28. Firma OSOBA_016 przygotowała raport finansowy.
29. FIRMA_001 wystawiła fakturę.
30. OSOBA_017 przedłożył fakturę do podpisu.
31. Zakład OSOBA_017 zajmuje się obróbką metali.
32. Spółka OSOBA_022 i Synowie prowadziła księgowość.
33. W sprawie pana OSOBA_009y przeprowadzono kontrolę.
34. W kawiarni OSOBA_021 sprzedawano świeże ciasta.
35. Pani dyrektor podpisała polecenie służbowe.
36. Pani dyrektor OSOBA_003 podpisała polecenie służbowe.
37. W rozmowie wystąpił pan OSOBA_001.
38. Sekretarz zarządu zaakceptował protokół.
39. Sekretarz zarządu OSOBA_027 OSOBA_025 zaakceptował protokół.
40. Stanowisko dyrektora jest nieobsadzone.
41. Dyrektor Zielony przyjął interesantów.
KWOTA_002 anowna Pani Dyrektor, proszę o odpowiedź.
KWOTA_001 anowna Pani Dyrektor OSOBA_016, proszę o odpowiedź.
44. Z panią OSOBA_002 uzgodniono nowe warunki.
45. Pismo skierowano do OSOBA_004.
46. Decyzję przekazano OSOBA_018 osobiście.
47. OSOBA_028 OSOBA_029 OSOBA_017 odebrał dokument w sekretariacie.
48. Pani OSOBA_010-OSOBA_005 zgłosiła pomyłkę.
49. OSOBA_016-OSOBA_019 odebrała przesyłkę z urzędu.
50. Pani OSOBA_020 podpisała protokół.
51. Pan de la Cruz przekazał dokumenty.
52. Zespół nadał projektowi nazwę OSOBA_021.
53. OSOBA_021 przygotowała umowę najmu.
54. OSOBA_021 kwitła na rabacie przez całe lato.
55. Analityk zatytułował wykres Maj.
56. Maj zatwierdził wykres podczas narady.
57. Spotkanie odbędzie się w ADRES_001.
58. Pani OSOBA_016 z ADRES_001 zadzwoniła rano.
59. Bibliotekarz odnalazł książkę pod tytułem OSOBA_011 i OSOBA_025.
60. Autor książki OSOBA_028 OSOBA_011 podpisał dedykację.
61. KONTROLA OCZEKIWANA
62. WYNIKI ANALIZY
63. KWOTA I TERMIN
64. DANE OSOBOWE
65. Dane kontaktowe podała OSOBA_030 Maj.
66. Prezes OSOBA_006 przesłał pismo.
67. FIRMA_002 przesłał pismo.
68. Zastępca dyrektora OSOBA_007 podpisał protokół.
```

## Fragment MAPY Desktop przekazany przez OWNERA (nie jest pełnym wynikiem 68 zdań)

```text
OSOBA_002 = Kowalska
OSOBA_003 = Jan Kowalski
OSOBA_015 = Ewa-Maria Wiśniewska
OSOBA_016 = Jan Paweł Kowalski
OSOBA_017 = Andrzej Malinowski
OSOBA_018 = Ryszard Kaczmarek
OSOBA_019 = Kowalskiemu
OSOBA_020 = Anna Nowak
OSOBA_021 = de la Cruz
OSOBA_022 = OCZEKIWANA
OSOBA_023 = Piotr Lis
OSOBA_024 = Jan Baran
OSOBA_025 = Anna Maj
OSOBA_026 = Zielony
OSOBA_027 = Jagoda
OSOBA_028 = Maliny
OSOBA_029 = Nguyen
OSOBA_030 = Wrona
OSOBA_031 = Marią
OSOBA_032 = Kruk
OSOBA_033 = Róża
OSOBA_034 = Marii
OSOBA_035 = Baran
OSOBA_036 = Sikora
OSOBA_037 = Wróbel
OSOBA_038 = Malina
OSOBA_039 = Pola
OSOBA_040 = Mak
OSOBA_041 = Soli
FIRMA_002 = Kowalski Sp. z o.o.
FIRMA_009 = ABC Development Sp. z o.o
FIRMA_010 = Spółka Malina
```

## Dalsze kroki następcy — bez wymyślania kodu przed testem

1. Odświeżyć HEAD main oraz stan `PHOTO-CHAIN` / `BOARD.md`. Nie cofać bieżącej pracy CC; nie dopisywać tego testu do wyników produktowych bez osobnego pomiaru.
2. Przed briefem `OSOBA-REDESIGN` przeprowadzić mały **diagnostyczny** replay na identycznym oryginale, profilach izolowanych, exact SHA obu silników; dla każdego ID zanotować maskowane spany, category, map entries i `Przywróć`. Desktop ma dotąd tylko mapę (nie pełny output), brak podstaw do tabeli porównawczej na wszystkich 68.
3. Zmierzyć niezależnie FN (OSOBA jawne), FP (nieosobowe OSOBA), błędne kategorie FIRMA/ADRES, **częściowe tokeny**, sztuczne dzielenie, przeklejanie tokenów między wystąpieniami, realne działanie Guarda. Jakość i ochronę danych raportować osobno.
4. Pierwsza falsyfikacja: porównać obecną autonomiczną regułę słownikową z modelem `kandydat + silny kontekst + dowody przeciw` na znanym zbiorze i **nowym** holdoucie, z jawnymi przypadkami np. `Róża zakwitła` vs `Pani Róża`, `Firma Nowak` vs `Nowak podpisał`. Nie dokładać trzeciego silnika, heurystycznego punktowania ani HerBERT od razu, o ile mały eksperyment nie uzasadni.
5. Jeśli wynik uzasadnia architekturę, przygotować dopiero minimalny brief task `LYNX-OSOBA-REDESIGN`, zgodny z `arch/spec.md`, `AGENTS.md` i przeglądem Codexa. Nie zmieniać zamrożonego S2/S3/S4 ani mapy bez zgody OWNERA. **Nie implementować bez prechecku i zgody OWNERA; nie merge bez jego polecenia.**
