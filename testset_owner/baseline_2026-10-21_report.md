# Porównanie silników: LynxMask Mobile vs Desktop (te same teksty)

- Mobile: repo `C:\Projects\LynxMask` @ `450204b` (silnik `PseudonymEngine.pseudonymize`, test JVM bez telefonu, słowniki z `src/test/resources` = identyczne z `assets`, sprawdzone hashem).
- Desktop: `origin/main` @ `cc70822` (`git archive` + `/preview` w osobnym procesie, pusty profil, `LYNX_HERBERT` nie ustawione = off).
- Dokumenty: 693 (zbiory: testy=38, clean=300, pliki=7, stress=300, ocr=48). `ocr` = `original_text` z Desktop `/preview` dla 50 obrazów benchmarku, podane jako .txt obu silnikom (48 z 50: obrazy doc_00004 i doc_00012 Desktop odrzucił jako zbyt słabe do OCR, 2 pominięte).
- Błędy: Mobile 0, Desktop 0 (po poniższych korektach wejścia). Tokeny: Mobile 8560, Desktop 7114.
- Korekty wejścia (identyczne dla obu silników): 3 pliki `testy/` zawierały w treści gotowe tokeny (`NUMER_011`), które Desktop odrzuca (422) → zamiana `_`→`-`; `testy/test_s1_s2_run.txt` był w UTF-16 LE → UTF-8; puste pliki pominięte.
- Metoda: wyjście każdego silnika wyrównuję do tekstu źródłowego (kotwice = literalne kawałki między tokenami), co daje dla każdego wystąpienia tokenu fragment źródła, który zakrył. Potem: fragment zakryty przez A i w 0% przez B = „całość”, częściowo = „granice”, w pełni przez B ale innego typu = „inny typ”. Etykiety (PESEL:, NIP:, ul., zł) nie liczą się do pokrycia. Liczone są **wystąpienia** w tekście (nie unikalne wartości).
- Ograniczenia: wyrównanie nie udało się dla 302 tokenów Mobile i 289 tokenów Desktop (pominięte; głównie pliki z celową degradacją OCR i normalizacja OCR Mobile). Pliki z `testy/` zawierają komentarze („OCZEKIWANE: …”), które generują szum — dlatego osobna kolumna „bez testy/”. Typy: Mobile ma FIRMA/OSOBA/NUMER/EMAIL/KWOTA/ADRES, Desktop dodatkowo INSTYTUCJA (mapowanie 1:1, INSTYTUCJA bez odpowiednika w Mobile).
- Wizualne porównanie: `porownanie.html` (kolumny Mobile | Desktop, żółty = Mobile zakrył a Desktop nie, niebieski = Desktop zakrył a Mobile nie, fioletowy = inny typ).

## Podsumowanie: kierunek × rodzaj × typ

| Kierunek | Rodzaj | Typ | Wystąpień | Dokumentów | w tym bez testy/ |
|---|---|---|---:|---:|---:|
| Desktop zakrył, Mobile nie | częściowo (granice) | OSOBA | 436 | 197 | 402 |
| Mobile zakrył, Desktop nie | całość | ADRES | 344 | 173 | 268 |
| Mobile i Desktop zakryły | inny typ | (różne pary typów) | 313 | 96 | 144 |
| Mobile zakrył, Desktop nie | całość | KWOTA | 202 | 178 | 177 |
| Desktop zakrył, Mobile nie | całość | FIRMA | 175 | 76 | 114 |
| Mobile zakrył, Desktop nie | całość | NUMER | 169 | 44 | 23 |
| Desktop zakrył, Mobile nie | całość | INSTYTUCJA | 153 | 67 | 141 |
| Desktop zakrył, Mobile nie | całość | OSOBA | 143 | 43 | 48 |
| Desktop zakrył, Mobile nie | częściowo (granice) | FIRMA | 112 | 56 | 107 |
| Desktop zakrył, Mobile nie | całość | NUMER | 97 | 49 | 53 |
| Mobile zakrył, Desktop nie | częściowo (granice) | ADRES | 66 | 24 | 14 |
| Desktop zakrył, Mobile nie | częściowo (granice) | ADRES | 32 | 28 | 22 |
| Desktop zakrył, Mobile nie | całość | ADRES | 28 | 2 | 0 |
| Mobile zakrył, Desktop nie | częściowo (granice) | NUMER | 28 | 16 | 5 |
| Mobile zakrył, Desktop nie | częściowo (granice) | OSOBA | 20 | 12 | 6 |
| Mobile zakrył, Desktop nie | całość | OSOBA | 20 | 11 | 13 |
| Desktop zakrył, Mobile nie | częściowo (granice) | NUMER | 20 | 13 | 3 |
| Mobile zakrył, Desktop nie | częściowo (granice) | FIRMA | 16 | 15 | 13 |
| Mobile zakrył, Desktop nie | całość | EMAIL | 13 | 6 | 0 |
| Desktop zakrył, Mobile nie | całość | KWOTA | 12 | 5 | 7 |
| Desktop zakrył, Mobile nie | częściowo (granice) | EMAIL | 8 | 3 | 1 |
| Mobile zakrył, Desktop nie | częściowo (granice) | EMAIL | 7 | 6 | 2 |
| Mobile zakrył, Desktop nie | całość | FIRMA | 3 | 3 | 1 |
| Desktop zakrył, Mobile nie | całość | EMAIL | 3 | 3 | 2 |
| Desktop zakrył, Mobile nie | częściowo (granice) | INSTYTUCJA | 1 | 1 | 0 |
| Mobile zakrył, Desktop nie | częściowo (granice) | KWOTA | 1 | 1 | 1 |

## Klasy różnic (kierunek × rodzaj × typ × podtyp), malejąco

Podtyp jest wyznaczany heurystycznie z treści fragmentu i jego otoczenia. Klasy z < 3 wystąpieniami tylko w `diff.json`. Przykłady: fragment w `[[...]]`.

| # | Klasa | Typ | Podtyp | Wyst. | Dok. | bez testy/ |
|---:|---|---|---|---:|---:|---:|
| 1 | Desktop zakrył, Mobile nie — częściowo (granice) | OSOBA | 2+ wyrazów | 433 | 195 | 401 |
| 2 | Mobile zakrył, Desktop nie — całość | ADRES | miejscowość (1 wyraz) | 284 | 153 | 250 |
| 3 | Desktop zakrył, Mobile nie — całość | FIRMA | bez formy prawnej | 171 | 75 | 113 |
| 4 | Mobile zakrył, Desktop nie — całość | KWOTA | słownie (X tysięcy/milionów) | 168 | 168 | 166 |
| 5 | Desktop zakrył, Mobile nie — całość | INSTYTUCJA | instytucja | 153 | 67 | 141 |
| 6 | Desktop zakrył, Mobile nie — całość | OSOBA | 1 wyraz | 114 | 37 | 39 |
| 7 | Desktop zakrył, Mobile nie — częściowo (granice) | FIRMA | bez formy prawnej | 103 | 48 | 99 |
| 8 | Inny typ (Mobile=ADRES, Desktop=FIRMA) | Mobile=ADRES, Desktop=FIRMA | miejscowość (1 wyraz) | 64 | 29 | 59 |
| 9 | Mobile zakrył, Desktop nie — całość | NUMER | inna liczba | 63 | 15 | 2 |
| 10 | Inny typ (Mobile=NUMER, Desktop=OSOBA) | Mobile=NUMER, Desktop=OSOBA | 2+ wyrazów | 42 | 5 | 0 |
| 11 | Mobile zakrył, Desktop nie — całość | ADRES | inny adres | 34 | 24 | 15 |
| 12 | Inny typ (Mobile=ADRES, Desktop=FIRMA) | Mobile=ADRES, Desktop=FIRMA | inny adres | 30 | 15 | 30 |
| 13 | Desktop zakrył, Mobile nie — całość | OSOBA | 2+ wyrazów | 29 | 12 | 9 |
| 14 | Desktop zakrył, Mobile nie — całość | NUMER | telefon | 27 | 17 | 18 |
| 15 | Mobile zakrył, Desktop nie — częściowo (granice) | ADRES | ulica/numer domu | 25 | 11 | 4 |
| 16 | Desktop zakrył, Mobile nie — częściowo (granice) | ADRES | ulica/numer domu | 25 | 24 | 20 |
| 17 | Mobile zakrył, Desktop nie — częściowo (granice) | ADRES | inny adres | 23 | 16 | 9 |
| 18 | Desktop zakrył, Mobile nie — całość | NUMER | księga wieczysta (KW) | 23 | 16 | 15 |
| 19 | Inny typ (Mobile=OSOBA, Desktop=ADRES) | Mobile=OSOBA, Desktop=ADRES | 1 wyraz | 23 | 21 | 23 |
| 20 | Mobile zakrył, Desktop nie — całość | KWOTA | bez waluty (sama liczba) | 21 | 9 | 11 |
| 21 | Mobile zakrył, Desktop nie — częściowo (granice) | OSOBA | 2+ wyrazów | 20 | 12 | 6 |
| 22 | Mobile zakrył, Desktop nie — całość | NUMER | nr dokumentu/sygnatura/z literami | 20 | 10 | 1 |
| 23 | Mobile zakrył, Desktop nie — całość | NUMER | nr umowy | 20 | 18 | 16 |
| 24 | Mobile zakrył, Desktop nie — częściowo (granice) | ADRES | kod pocztowy (+miasto) | 18 | 9 | 1 |
| 25 | Desktop zakrył, Mobile nie — całość | ADRES | ulica/numer domu | 17 | 2 | 0 |
| 26 | Desktop zakrył, Mobile nie — całość | NUMER | nr dokumentu/sygnatura/z literami | 17 | 9 | 6 |
| 27 | Mobile zakrył, Desktop nie — całość | OSOBA | 1 wyraz | 17 | 9 | 13 |
| 28 | Mobile zakrył, Desktop nie — całość | NUMER | telefon | 16 | 8 | 1 |
| 29 | Mobile zakrył, Desktop nie — częściowo (granice) | FIRMA | z formą prawną | 16 | 15 | 13 |
| 30 | Inny typ (Mobile=OSOBA, Desktop=FIRMA) | Mobile=OSOBA, Desktop=FIRMA | 1 wyraz | 16 | 6 | 16 |
| 31 | Inny typ (Mobile=ADRES, Desktop=OSOBA) | Mobile=ADRES, Desktop=OSOBA | 1 wyraz | 14 | 11 | 7 |
| 32 | Mobile zakrył, Desktop nie — całość | ADRES | kod pocztowy (+miasto) | 14 | 7 | 1 |
| 33 | Mobile zakrył, Desktop nie — całość | KWOTA | z walutą | 13 | 4 | 0 |
| 34 | Mobile zakrył, Desktop nie — całość | EMAIL | email | 13 | 6 | 0 |
| 35 | Mobile zakrył, Desktop nie — całość | NUMER | sygnatura sprawy | 12 | 8 | 0 |
| 36 | Desktop zakrył, Mobile nie — całość | NUMER | 10 cyfr (NIP?) | 12 | 9 | 8 |
| 37 | Desktop zakrył, Mobile nie — całość | KWOTA | z walutą | 12 | 5 | 7 |
| 38 | Mobile zakrył, Desktop nie — całość | NUMER | dokument tożsamości | 12 | 4 | 1 |
| 39 | Mobile zakrył, Desktop nie — całość | ADRES | ulica/numer domu | 11 | 4 | 2 |
| 40 | Mobile zakrył, Desktop nie — całość | NUMER | nr faktury | 10 | 7 | 1 |
| 41 | Inny typ (Mobile=ADRES, Desktop=NUMER) | Mobile=ADRES, Desktop=NUMER | kod pocztowy (+miasto) | 10 | 3 | 0 |
| 42 | Desktop zakrył, Mobile nie — całość | ADRES | kod pocztowy (+miasto) | 10 | 2 | 0 |
| 43 | Desktop zakrył, Mobile nie — częściowo (granice) | FIRMA | z formą prawną | 9 | 9 | 8 |
| 44 | Desktop zakrył, Mobile nie — częściowo (granice) | EMAIL | email | 8 | 3 | 1 |
| 45 | Inny typ (Mobile=KWOTA, Desktop=OSOBA) | Mobile=KWOTA, Desktop=OSOBA | z walutą | 7 | 3 | 0 |
| 46 | Mobile zakrył, Desktop nie — częściowo (granice) | EMAIL | email | 7 | 6 | 2 |
| 47 | Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | nr faktury | 7 | 3 | 0 |
| 48 | Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | telefon | 6 | 5 | 0 |
| 49 | Inny typ (Mobile=EMAIL, Desktop=NUMER) | Mobile=EMAIL, Desktop=NUMER | email | 6 | 3 | 0 |
| 50 | Inny typ (Mobile=NUMER, Desktop=OSOBA) | Mobile=NUMER, Desktop=OSOBA | PESEL | 6 | 1 | 0 |
| 51 | Desktop zakrył, Mobile nie — częściowo (granice) | ADRES | kod pocztowy (+miasto) | 5 | 4 | 2 |
| 52 | Desktop zakrył, Mobile nie — całość | NUMER | IBAN/rachunek | 5 | 1 | 0 |
| 53 | Inny typ (Mobile=NUMER, Desktop=OSOBA) | Mobile=NUMER, Desktop=OSOBA | nr dokumentu/sygnatura/z literami | 5 | 4 | 0 |
| 54 | Mobile zakrył, Desktop nie — całość | NUMER | NIP | 5 | 4 | 0 |
| 55 | Inny typ (Mobile=ADRES, Desktop=NUMER) | Mobile=ADRES, Desktop=NUMER | inny adres | 5 | 1 | 0 |
| 56 | Desktop zakrył, Mobile nie — całość | NUMER | inna liczba | 5 | 5 | 4 |
| 57 | Inny typ (Mobile=EMAIL, Desktop=FIRMA) | Mobile=EMAIL, Desktop=FIRMA | bez formy prawnej | 5 | 1 | 0 |
| 58 | Inny typ (Mobile=KWOTA, Desktop=NUMER) | Mobile=KWOTA, Desktop=NUMER | z walutą | 4 | 4 | 0 |
| 59 | Inny typ (Mobile=ADRES, Desktop=OSOBA) | Mobile=ADRES, Desktop=OSOBA | 2+ wyrazów | 4 | 3 | 0 |
| 60 | Desktop zakrył, Mobile nie — całość | FIRMA | z formą prawną | 4 | 3 | 1 |
| 61 | Desktop zakrył, Mobile nie — całość | NUMER | data | 4 | 1 | 0 |
| 62 | Inny typ (Mobile=NUMER, Desktop=OSOBA) | Mobile=NUMER, Desktop=OSOBA | telefon | 4 | 2 | 0 |
| 63 | Mobile zakrył, Desktop nie — całość | NUMER | IBAN/rachunek | 4 | 2 | 0 |
| 64 | Inny typ (Mobile=EMAIL, Desktop=FIRMA) | Mobile=EMAIL, Desktop=FIRMA | email | 4 | 1 | 0 |
| 65 | Desktop zakrył, Mobile nie — częściowo (granice) | NUMER | sygnatura sprawy | 4 | 3 | 1 |
| 66 | Inny typ (Mobile=ADRES, Desktop=NUMER) | Mobile=ADRES, Desktop=NUMER | miejscowość (1 wyraz) | 3 | 3 | 1 |
| 67 | Desktop zakrył, Mobile nie — częściowo (granice) | OSOBA | 1 wyraz | 3 | 2 | 1 |
| 68 | Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | nr dokumentu/sygnatura/z literami | 3 | 3 | 1 |
| 69 | Inny typ (Mobile=OSOBA, Desktop=ADRES) | Mobile=OSOBA, Desktop=ADRES | 2+ wyrazów | 3 | 2 | 0 |
| 70 | Desktop zakrył, Mobile nie — częściowo (granice) | NUMER | nr faktury | 3 | 2 | 0 |
| 71 | Mobile zakrył, Desktop nie — całość | FIRMA | z formą prawną | 3 | 3 | 1 |
| 72 | Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | sygnatura sprawy | 3 | 2 | 0 |
| 73 | Desktop zakrył, Mobile nie — częściowo (granice) | NUMER | dokument tożsamości | 3 | 2 | 0 |
| 74 | Mobile zakrył, Desktop nie — całość | OSOBA | 2+ wyrazów | 3 | 3 | 0 |
| 75 | Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | NIP | 3 | 3 | 2 |
| 76 | Inny typ (Mobile=OSOBA, Desktop=NUMER) | Mobile=OSOBA, Desktop=NUMER | telefon | 3 | 3 | 1 |
| 77 | Desktop zakrył, Mobile nie — częściowo (granice) | NUMER | nr dokumentu/sygnatura/z literami | 3 | 2 | 0 |
| 78 | Desktop zakrył, Mobile nie — całość | EMAIL | email | 3 | 3 | 2 |
| 79 | Inny typ (Mobile=OSOBA, Desktop=FIRMA) | Mobile=OSOBA, Desktop=FIRMA | 2+ wyrazów | 3 | 1 | 3 |

## Szczegóły klas z przykładami

### 1. Desktop zakrył, Mobile nie — częściowo (granice) | OSOBA | 2+ wyrazów — 433 wyst., 195 dok.

Hipoteza: Mobile maskuje tylko jedno słowo z „Imię Nazwisko” (zwykle imię), a nazwisko — rzadkie lub obce — zostaje; Desktop maskuje całość. Mobile: brak reguły „Imię + Słowo z wielkiej litery” poza słownikiem nazwisk. W 97% przypadków niezakryty fragment zawiera ostatni wyraz (nazwisko).

- `stress__doc_00000.txt` — `...--------------\n\nDANE OSOBOWE WNIOSKODAWCY\n\nImię i nazwisko:\n[[Keith Grochola]]\nData urodzenia:\n13.03.1980\nPESEL:\n02322343214\nNr dowodu oso...` (niezakryte: `Grochola`)
- `stress__doc_00001.txt` — `...--------------\n\nDANE OSOBOWE WNIOSKODAWCY\n\nImię i nazwisko:\n[[Zoryna Pastuszka]]\nData urodzenia:\n20.12.1999\nPESEL:\n75121808105\nNr dowodu oso...` (niezakryte: `Pastuszka`)
- `stress__doc_00002.txt` — `...lne, dnia 07.02.2023\n\nSKARGA\n\nJa, niżej podpisany/podpisana [[Aram Góralewski]], zamieszkały/zamieszkała przy ul. Piasnicka 153 w Palędzie ...` (niezakryte: `Góralewski`)
- `stress__doc_00003.txt` — `...W dniu 01.06.2023 do biura zgłosiła/się następująca osoba:\n\n[[Kunegunda Tobolska]]\nPESEL: 67110515635\nAdres: ul. Osiedlencza 79/16, 65-001 Zal...` (niezakryte: `Tobolska`)
- `stress__doc_00004.txt` — `...--------------\n\nDANE OSOBOWE WNIOSKODAWCY\n\nImię i nazwisko:\n[[Aurelia Waszek]]\nData urodzenia:\n24.08.1950\nPESEL:\n64102427189\nNr dowodu oso...` (niezakryte: `Waszek`)
- `stress__doc_00006.txt` — `...SŁUG\nnr U-00958/2023\n\nzawarta dnia 22.02.2021 pomiędzy:\n\n1. [[Ulrich Jędral]]\n   zamieszkałym/ą: ul. Podbipiety 31, 40-001 Popowo-Ignacew...` (niezakryte: `Jędral`)
- `stress__doc_00007.txt` — `...wka, dnia 22.02.2023\n\nSKARGA\n\nJa, niżej podpisany/podpisana [[Armin Sauter]], zamieszkały/zamieszkała przy ul. Zielona polana 68/29 w Pl...` (niezakryte: `Sauter`)
- `stress__doc_00007.txt` — `...a, PESEL 50111311430, składam niniejszą skargę na działania [[Anetta Godzwon]].\n\nW dniu 22.02.2023 Anetta Godzwon dopuścił/dopuściła się z...` (niezakryte: `Godzwon`)

### 2. Mobile zakrył, Desktop nie — całość | ADRES | miejscowość (1 wyraz) — 284 wyst., 153 dok.

Hipoteza: Desktop nie maskuje samej miejscowości w odmianie („w Warszawie”, „w Gdańsku”) po nazwie urzędu lub adresie; Mobile maskuje ją ze słownika miast (cities_forms). Do rozstrzygnięcia: świadoma polityka Desktop czy brak reguły.

- `clean__doc_00002.txt` — `...tr Wójcik, zamieszkały/zamieszkała przy ul. Różana 153/25 w [[Zabrzu]], PESEL 72072299408, składam niniejszą skargę na działania J...`
- `clean__doc_00006.txt` — `...ieczorek, zamieszkały/zamieszkała przy ul. Chopina 125/19 w [[Szczecinie]], PESEL 98082306208, składam niniejszą skargę na działania I...`
- `clean__doc_00008.txt` — `... Dąbrowska, zamieszkały/zamieszkała przy ul. Kwiatowa 171 w [[Białymstoku]], PESEL 62011827014, składam niniejszą skargę na działania M...`
- `clean__doc_00012.txt` — `...wski, zamieszkały/zamieszkała przy ul. Sienkiewicza 22/43 w [[Olsztynie]], PESEL 58051983821, składam niniejszą skargę na działania K...`
- `clean__doc_00013.txt` — `...zyna Krawczyk, zamieszkały/zamieszkała przy ul. Polna 184 w [[Toruniu]], PESEL 63032967103, składam niniejszą skargę na działania Z...`
- `clean__doc_00015.txt` — `Urząd Celno-Skarbowy w [[Gdańsku]]\n\nSygn.: SA.028860.2025\nData wydania: 11.06.2022\n\n\nDECYZJA A...`
- `clean__doc_00016.txt` — `Urząd Skarbowy w [[Warszawie]]\n\nSygn.: IW.033165.2024\nData wydania: 21.08.2022\n\n\nDECYZJA A...`
- `clean__doc_00023.txt` — `Powiatowy Urząd Pracy w [[Poznaniu]]\n\nSygn. akt: I C 7243/2025\nWarszawa, dnia 20.02.2021\n\n\nIwona...`

### 3. Desktop zakrył, Mobile nie — całość | FIRMA | bez formy prawnej — 171 wyst., 75 dok.

Hipoteza: Desktop maskuje jako FIRMA nazwy bez formy prawnej (sądy i komornicy: „SR Warszawa-Mokotów”, „Sąd Rejonowy”, kancelarie z „S.C”); Mobile wymaga formy prawnej (Sp. z o.o., S.A.). Możliwe nadmaskowanie Desktop.

- `clean__doc_00009.txt` — `...15075\n\n----------------------------------------\nSPRZEDAWCA:\n[[Agencja Reklamowa KREACJA]]\nAdres: pl. Wolności 65, 02-200 Kraków\nNIP: 624-278-68-00   ...`
- `clean__doc_00010.txt` — `Komornik Sądowy przy [[Sądzie Rejonowym]] Anna Zielińska\n\nSygn. akt: Km 79557/2024\nData: 13.11.2022\n\n...`
- `clean__doc_00027.txt` — `Komornik Sądowy przy [[SR Warszawa-Mokotów]] Tomasz Malinowski\n\nSygn. akt: Km 58253/2019\nData: 06.12.202...`
- `clean__doc_00066.txt` — `Komornik Sądowy przy [[SR Poznań]]-Grunwald Janusz Wierzbicki\n\nSygn. akt: Km 79420/2023\nData: ...`
- `clean__doc_00085.txt` — `...\n................................................\nKierownik [[Wydziału]]\nUrząd Skarbowy Kraków-Śródmieście\n\n------------------------...`
- `clean__doc_00218.txt` — `...76330\n\n----------------------------------------\nSPRZEDAWCA:\n[[Kancelaria Prawna LEGIS S.C]].\nAdres: ul. Polna 2, 02-200 Sosnowiec\nNIP: 697-779-01-44   ...`
- `pliki__doc_lvl0_umowa_o_prace.txt` — `...PRACOWNIKA\n1. Świadczenie pomocy prawnej na rzecz klientów [[Kancelarii]].\n2. Sporządzanie opinii prawnych, umów i pism procesowych....`
- `pliki__doc_lvl0_umowa_o_prace.txt` — `...gania sporów: Sąd Rejonowy dla m.st. Warszawy\nw Warszawie, [[XIV Wydział Pracy]].\n\nW przypadku sporu strony mogą skierować sprawę do media...`

### 4. Mobile zakrył, Desktop nie — całość | KWOTA | słownie (X tysięcy/milionów) — 168 wyst., 168 dok.

Hipoteza: Kwota słowna w „(słownie: 46 tysięcy 744 złotych)”: Mobile maskuje początek („46 tysięcy”), Desktop zostawia całość. Reguła: liczba + „tysięcy/milionów” w nawiasie po „słownie:”.

- `clean__doc_00003.txt` — `... zapłaci wynagrodzenie w kwocie 44,813 PLN brutto (słownie: [[44 tysięcy]] 813 złotych).\nZapłata nastąpi przelewem na rachunek bankowy...`
- `clean__doc_00010.txt` — `...ublin\n\nŁączna kwota zadłużenia wynosi: 39,563 PLN (słownie: [[39 tysięcy]] 563 złotych).\n\nDłużnik ma prawo złożyć oświadczenie o skład...`
- `clean__doc_00027.txt` — `...Biała\n\nŁączna kwota zadłużenia wynosi: 10,550 PLN (słownie: [[10 tysięcy]] 550 złotych).\n\nDłużnik ma prawo złożyć oświadczenie o skład...`
- `clean__doc_00031.txt` — `...Biała\n\nŁączna kwota zadłużenia wynosi: 12,939 PLN (słownie: [[12 tysięcy]] 939 złotych).\n\nDłużnik ma prawo złożyć oświadczenie o skład...`
- `clean__doc_00036.txt` — `... Radom\n\nŁączna kwota zadłużenia wynosi: 3,994 PLN (słownie: [[3 tysięcy]] 994 złotych).\n\nDłużnik ma prawo złożyć oświadczenie o skład...`
- `clean__doc_00037.txt` — `... zapłaci wynagrodzenie w kwocie 40,007 PLN brutto (słownie: [[40 tysięcy]] 7 złotych).\nZapłata nastąpi przelewem na rachunek bankowy Z...`
- `clean__doc_00041.txt` — `... zapłaci wynagrodzenie w kwocie 67,043 PLN brutto (słownie: [[67 tysięcy]] 43 złotych).\nZapłata nastąpi przelewem na rachunek bankowy ...`
- `clean__doc_00044.txt` — `... zapłaci wynagrodzenie w kwocie 46,744 PLN brutto (słownie: [[46 tysięcy]] 744 złotych).\nZapłata nastąpi przelewem na rachunek bankowy...`

### 5. Desktop zakrył, Mobile nie — całość | INSTYTUCJA | instytucja — 153 wyst., 67 dok.

Hipoteza: Typ INSTYTUCJA istnieje tylko w Desktop (Urząd Skarbowy, Powiatowy Urząd Pracy, ZUS, Sąd Rejonowy…); Mobile nie ma tego typu ani reguły (maskuje tylko miasto w nazwie). Różnica projektowa.

- `clean__doc_00015.txt` — `[[Urząd Celno-Skarbowy]] w Gdańsku\n\nSygn.: SA.028860.2025\nData wydania: 11.06.2022\n\n...`
- `clean__doc_00016.txt` — `[[Urząd Skarbowy]] w Warszawie\n\nSygn.: IW.033165.2024\nData wydania: 21.08.2022...`
- `clean__doc_00023.txt` — `[[Powiatowy Urząd Pracy]] w Poznaniu\n\nSygn. akt: I C 7243/2025\nWarszawa, dnia 20.02.2...`
- `pliki__doc_lvl0_umowa_o_prace.txt` — `...som Kodeksu Pracy.\n\nSąd właściwy do rozstrzygania sporów: [[Sąd Rejonowy]] dla m.st. Warszawy\nw Warszawie, XIV Wydział Pracy.\n\nW pr...`
- `testy__test_nip_warianty.txt` — `...odany numer kontrahenta: 526-000-13-20.\nWeryfikacja w bazie [[GUS]]: numer nieprawidłowy, brak rekordu.\n\nUwaga: liczba 526-000-...`
- `testy__test_pesel_warianty.txt` — `...óżana 44/2, 50-001 Wrocław.\nDokument wystawiony na potrzeby [[urzędu pracy]].\n\nWezwanie do zapłaty nr WZ/2024/0084.\nDłużnik: Tomasz Mali...`
- `testy__test_reczny_21_06.txt` — `...R\n========================================================\n\n[[Zakład Ubezpieczeń Społecznych]], Oddział w Krakowie\nul. Piastowska 14, 31-406 Kraków\n\nDotyc...`

### 6. Desktop zakrył, Mobile nie — całość | OSOBA | 1 wyraz — 114 wyst., 37 dok.

Hipoteza: Desktop maskuje pojedyncze słowa jako OSOBA — głównie komentarze w plikach testy/ (OCZEKIWANE, YELLOW, Anchor), w OCR także zwykłe słowa (Dlużnik, Splata). Nadmaskowanie Desktop; wśród dokumentów realistycznych także nazwiska bez imienia.

- `pliki__doc_lvl2_pismo_komornicze.txt` — `... i zarobkach)\n- wydruk z ksiegi wieczystej z 29.08.2024\n\n[[Poucze]] nie: Dluznikowi przysluguje prawo zlozenia skargi na czynno...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `[[FAKTURAvVAT]] Nr FV/2024/09/00847\n──────────────────────────────────────...`
- `stress__doc_00086.txt` — `...18.01.2024\n\nSKARGA\n\nJa, niżej podpisany/podpisana Nikoletta [[Hojnacka]], zamieszkały/zamieszkała przy ul. Niemczyka 53 w Maniów Mał...`
- `stress__doc_00092.txt` — `Urząd Gminy Warszawa-Wola\n\nSygn. akt: II Ns 2847/2015\n[[Ruska]] Wieś, dnia 27.11.2024\n\n\nEsra Tytko\nul. Pod walem 35\n65-001 ...`
- `stress__doc_00107.txt` — `...--------\n\nDANE OSOBOWE WNIOSKODAWCY\n\nImię i nazwisko:\nGagik [[Włodkowski]]\nData urodzenia:\n04.04.1975\nPESEL:\n86072839775\nNr dowodu oso...`
- `stress__doc_00115.txt` — `...kargę na działania Edyty Fröhlich.\n\nW dniu 24.07.2020 Edyta [[Fröhlich]] dopuścił/dopuściła się zachowania, które uważam za rażące n...`
- `stress__doc_00140.txt` — `...z 2023 r. poz. 775 ze zm.)\n\npo rozpatrzeniu wniosku:\nArthur [[Data]]\nPESEL: 60022618489\nNIP: 127-937-14-58\nadres: ul. Rostka 166...`
- `stress__doc_00142.txt` — `...2112868386, składam niniejszą skargę na działania Zbigniewa [[Kierzkowska]].\n\nW dniu 24.10.2020 Zbigniew Kierzkowska dopuścił/dopuściła...`

### 7. Desktop zakrył, Mobile nie — częściowo (granice) | FIRMA | bez formy prawnej — 103 wyst., 48 dok.

Hipoteza: Desktop obejmuje całą nazwę instytucji/firmy, Mobile tylko część (miasto lub początek); także osoby wzięte przez Desktop za FIRMA.

- `clean__doc_00024.txt` — `[[Zakład Ubezpieczeń Społecznych Oddział w Warszawie]]\n\nSygn.: PD.032046.2025\nData wydania: 02.02.2023\n\n\nDECYZJA A...` (niezakryte: `Zakład Ubezpieczeń Społecznych Oddział w`)
- `clean__doc_00036.txt` — `Komornik Sądowy przy [[SR Kraków-Nowa Huta]] Piotr Nowacki\n\nSygn. akt: Km 20380/2021\nData: 06.09.2023\n\n\n...` (niezakryte: `SR Kraków`)
- `pliki__doc_lvl0_umowa_o_prace.txt` — `...iada legitymację radcy prawnego nr WA/4521 wydaną przez\n   [[Okręgową Izbę Radców Prawnych w Warszawie]].\n\n§ 3. WYNAGRODZENIE\n1. Pracownikowi przysługuje wynagro...` (niezakryte: `Okręgową Izbę Radców Prawnych w`)
- `pliki__doc_lvl1_decyzja_administracyjna.txt` — `...stronie odwolanie do Wojewody Pomorskiego\nza posrednictwem [[Powiatowego Urzedu Pracy w Gdansku]] w terminie 14 dni\nod dnia doreczenia decyzji.\n\nDecyzja n...` (niezakryte: `Powiatowego Urzedu Pracy w`)
- `pliki__doc_lvl2_pismo_komornicze.txt` — `Komornik Sadowy\nprzy [[Sadzie Rejonowym w Krakowie]]\nArtur Wojciechowski\nul. Grodzka 65, 31-001 Krakow\ntel. 1...` (niezakryte: `Sadzie Rejonowym w`)
- `pliki__doc_stresstest_silnik_guard_lvl0_3.txt` — `...══════════════\n\nWEZWANIE DO ZAPŁATY\nKomornik Sądowy przy [[Sądzie Rejonowym w Krakowie]]\nArtur Wojciechowski, e-mail: komornik.wojciechowski@krakow...` (niezakryte: `Sądzie Rejonowym w`)
- `pliki__doc_test_nowe_encje.txt` — `...córka Jana.\n\n=== PLACÓWKI MEDYCZNE ===\nPacjent leczony w [[Szpitalu Miejskim w Gdańsku]].\nSkierowanie do Kliniki Kardiologii.\nWynik z Centrum Medy...` (niezakryte: `Szpitalu Miejskim w`)
- `pliki__doc_test_nowe_encje.txt` — `...im w Gdańsku.\nSkierowanie do Kliniki Kardiologii.\nWynik z [[Centrum Medycznego]] przy ul. Polnej.\nPrzychodnia Lekarzy Rodzinnych, Wrocław....` (niezakryte: `Centrum`)

### 8. Inny typ (Mobile=ADRES, Desktop=FIRMA) | Mobile=ADRES, Desktop=FIRMA | miejscowość (1 wyraz) — 64 wyst., 29 dok.

Hipoteza: Miasto/adres w nazwie instytucji: Mobile maskuje miejscowość jako ADRES, Desktop obejmuje ją tokenem FIRMA/INSTYTUCJA. To granice/typ, nie wyciek.

- `clean__doc_00024.txt` — `Zakład Ubezpieczeń Społecznych Oddział w [[Warszawie]]\n\nSygn.: PD.032046.2025\nData wydania: 02.02.2023\n\n\nDECYZJA A...`
- `pliki__doc_lvl1_decyzja_administracyjna.txt` — `...dy Pomorskiego\nza posrednictwem Powiatowego Urzedu Pracy w [[Gdansku]] w terminie 14 dni\nod dnia doreczenia decyzji.\n\nDecyzja n...`
- `pliki__doc_lvl2_pismo_komornicze.txt` — `Komornik Sadowy\nprzy Sadzie Rejonowym w [[Krakowie]]\nArtur Wojciechowski\nul. Grodzka 65, 31-001 Krakow\ntel. 1...`
- `pliki__doc_test_nowe_encje.txt` — `...LACÓWKI MEDYCZNE ===\nPacjent leczony w Szpitalu Miejskim w [[Gdańsku]].\nSkierowanie do Kliniki Kardiologii.\nWynik z Centrum Medy...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...yimku (NameEngine CITY_PREP — \b po nazwie)\nUmowa zawarta w [[Toruń]] dnia 01.01.2025.\nOCZEKIWANE: TOKEN ADRES na "Toruń", nie sa...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `... "ń"\n\n[B8] Miasto po "w" — Poznań\nZamawiający zamieszkały w [[Poznań]] od 2019 roku.\nOCZEKIWANE: TOKEN ADRES na "Poznań"\n\n[B9] Mia...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...ES na "Poznań"\n\n[B9] Miasto po "w" — Łódź\nDostawa towaru do [[Łódź]] w terminie 14 dni.\nOCZEKIWANE: TOKEN ADRES na "Łódź", zero ...`
- `testy__test_nip_warianty.txt` — `... na spacje.\n\nPismo z dnia 14.04.2024 do Urzędu Skarbowego w [[Poznaniu]].\nDane podatnika: NIP: 521 334 00 01.\nProszę o wydanie zaświ...`

### 9. Mobile zakrył, Desktop nie — całość | NUMER | inna liczba — 63 wyst., 15 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_stresstest_silnik_guard_lvl0_3.txt` — `...────\nPUŁAPKI (test Guard + blocklist NER — NIE powinny być [[OSOBA/FIRMA]]):\n\nDłużnik: ........................................\nWie...`
- `pliki__doc_test_guard.txt` — `...e?)\nTelefon infolinii: 801-000-000 (numer ogólnodostępny)\n[[Data urodzenia słownie: pierwszego stycznia]] tysiąc dziewięćset osiemdziesiąt pięć\n`
- `testy__bramka_merge_silnik_14_07.txt` — `...o jawnym fragmencie (OK dla gołych miast — decyzja 08.07)\n  [[NIE-OSOBA]] = słowo pospolite / kolizja — NIE powinno dostać tokenu OSO...`
- `testy__test_adresy_50.txt` — `...\nuI. Nowa 97, 10-100 Zielona Góra\nOCZEKIWANE: 1 ADRES\n\n[[[E10]]] "al." bez kropki (al bez kropki)\nal Różana 2/38, 60-001 Z...`
- `testy__test_adresy_50.txt` — `...ki)\nal Różana 2/38, 60-001 Zabrze\nOCZEKIWANE: 1 ADRES\n\n[[[E11]]] spacja w numerze lokalu\nul. Dębowa 19 /23, 87-100 Białyst...`
- `testy__test_adresy_50.txt` — `...ok\nOCZEKIWANE: 1 ADRES (lub min. ADRES dla ul. Dębowa)\n\n[[[E12]]] kod z O zamiast 0, miasto z literówką\nul. Zielona 176, 8O...`
- `testy__test_adresy_50.txt` — `...ej nazwy własnej\n\n--- SEKCJA G: TRUDNE PRZYPADKI (możliwe [[FP/FN]]) ---\n\n[G1] kod który wygląda jak rok (nie adres)\nWyrok z...`
- `testy__test_adresy_50.txt` — `...5-2024 roku\nOCZEKIWANE: NIE ADRES — kod pocztowy ma format [[XX-YYY]], rok XX-YYYY\n\n[G2] numer lokalu który wygląda jak adres\n...`

### 10. Inny typ (Mobile=NUMER, Desktop=OSOBA) | Mobile=NUMER, Desktop=OSOBA | 2+ wyrazów — 42 wyst., 5 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_hard_v2.txt` — `GROUND TRUTH (co silnik POWINIEN zamaskować):\n  OSOBA: [[Bartosz Jabłoński, Monika Nowakowska]]\n  PESEL: 91040512361 (PESE1: z cyfrą), 80012312349 (PESE1 ...`
- `testy__test_mix_encje.txt` — `...nna Nowak PESEL 85030612345 tel. 601 234 567\nPL611090101400[[00071219812874 Piotr Wi]]śniewski ur. 12.03.1985\naga.kowalska@gmail.com, 48 722 333 ...`
- `testy__test_nip_warianty.txt` — `...Termin ważności oferty: 30 dni.\n\nKarta klienta biznesowego. [[nip_nabywcy]]: 142-199-06-38.\nPrzyznany limit kredytowy: 50 000 PLN.\n\n---...`
- `testy__test_pesel_warianty.txt` — `...===========================================================\n[[TEST PESEL]] — WSZYSTKIE WARIANTY ZAPISU\nCel: sprawdzić czy silnik masku...`
- `testy__test_pesel_warianty.txt` — `...y: Korekta zeznania rocznego.\nDane podatnika: Jan Kowalski, [[PESEL: 730516499]]57, ul. Długa 12, Kraków.\nProszę o przyjęcie korekty formula...`
- `testy__test_pesel_warianty.txt` — `...arta dnia 15.03.2024 w Warszawie.\nWynajmujący: Maria Nowak, [[PESEL: 55091]]961277, zam. ul. Kwiatowa 3/5, Warszawa.\nNajemca: Piotr Wiśn...`
- `testy__test_pesel_warianty.txt` — `...zam. ul. Kwiatowa 3/5, Warszawa.\nNajemca: Piotr Wiśniewski, [[PESEL: 90010]]155382, zam. ul. Zielona 8, Gdańsk.\nStrony ustalają czynsz m...`
- `testy__test_pesel_warianty.txt` — `...nę Wrocław dnia 22.04.2024.\nImię i nazwisko: Anna Zając, nr [[PESEL: 85032]]204563.\nAdres zamieszkania: al. Różana 44/2, 50-001 Wrocław....`

### 11. Mobile zakrył, Desktop nie — całość | ADRES | inny adres — 34 wyst., 24 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00017.txt` — `...Lewandowska, zamieszkały/zamieszkała przy ul. Piaskowa 43 w [[Zielonej Górze]], PESEL 64091098791, składam niniejszą skargę na działania P...`
- `stress__doc_00002.txt` — `...óralewski, zamieszkały/zamieszkała przy ul. Piasnicka 153 w [[Palędzie Dolne]], PESEL 51011269683, składam niniejszą skargę na działania N...`
- `stress__doc_00023.txt` — `...drés Musioł, zamieszkały/zamieszkała przy ul. Wierzbina 6 w [[Skomack Wielki]], PESEL 53081178160, składam niniejszą skargę na działania A...`
- `stress__doc_00037.txt` — `...Vittoria Wrobel, zamieszkały/zamieszkała przy ul. Reja 27 w [[Wola Skrzydlańska]], PESEL 57072651601, składam niniejszą skargę na działania S...`
- `stress__doc_00060.txt` — `...Osoba, zamieszkały/zamieszkała przy ul. Sw. trojcy 185/19 w [[Bereżnica Wyżna]], PESEL 88081882526, składam niniejszą skargę na działania Y...`
- `stress__doc_00086.txt` — `[[Maniów Mały]], dnia 18.01.2024\n\nSKARGA\n\nJa, niżej podpisany/podpisana Nik...`
- `stress__doc_00117.txt` — `Starostwo Powiatowe w Radomiu\n\nSygn. akt: I Ns 5/2025\n[[Stężycka Huta]], dnia 26.06.2020\n\n\nSolomiya Górny\nul. Za stawem 44\n40-001 K...`
- `stress__doc_00124.txt` — `...013\nNIP: 105-577-84-80\nadres: ul. Świstaka 65, 02-200 Stare [[Leśne Bohatery]]\n\nORZEKAM:\n\nOrgan umarza się postępowanie administracyjne w ...`

### 12. Inny typ (Mobile=ADRES, Desktop=FIRMA) | Mobile=ADRES, Desktop=FIRMA | inny adres — 30 wyst., 15 dok.

Hipoteza: Miasto/adres w nazwie instytucji: Mobile maskuje miejscowość jako ADRES, Desktop obejmuje ją tokenem FIRMA/INSTYTUCJA. To granice/typ, nie wyciek.

- `clean__doc_00036.txt` — `Komornik Sądowy przy SR Kraków-[[Nowa Huta]] Piotr Nowacki\n\nSygn. akt: Km 20380/2021\nData: 06.09.2023\n\n\n...`

### 13. Desktop zakrył, Mobile nie — całość | OSOBA | 2+ wyrazów — 29 wyst., 12 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `stress__doc_00008.txt` — `...ygn. akt: II Ns 2533/2024\nLeśniewo Górne, dnia 05.11.2024\n\n\n[[Andrés Kisiała]]\nul. Lange 171/50\n90-001 Podstoła\n\n\nWEZWANIE DO ZŁOŻENIA WYJ...`
- `stress__doc_00020.txt` — `...r UMOWA/2020/NR/0654\n\nzawarta dnia 29.07.2020 pomiędzy:\n\n1. [[Sándor Wiechcińska]]\n   zamieszkałym/ą: ul. Krasińskiego 93/1, 45-001 Stary Krze...`
- `stress__doc_00023.txt` — `...lki, dnia 26.03.2023\n\nSKARGA\n\nJa, niżej podpisany/podpisana [[Andrés Musioł]], zamieszkały/zamieszkała przy ul. Wierzbina 6 w Skomack Wie...`
- `stress__doc_00062.txt` — `... Piotr Nowacki\n\nSygn. akt: Km 71276/2022\nData: 28.02.2023\n\n\n[[Büşra Brzozowy]]\nul. Krola 55\n65-001 Stanisławki\n\n\nZAWIADOMIENIE O WSZCZĘCIU...`
- `ocr__doc_00019.txt` — `[[Komomnik Sądowy]] przy SR Kraków-Nowa Huta Piotr Nowacki\nSygn. akt Km 54081/2...`
- `testy__test_anchor_full.txt` — `...raków\n\n=== ORGANIZACJA — kotwica S.A. / Sp. z o.o. ===\nKo[[walski i Part]]nerzy Sp. z o.o.\nPrzedsiębiorstwo Budowlane Nowak S.A.\nKan...`
- `testy__test_anchor_full.txt` — `...owalski i Partnerzy Sp. z o.o.\nPrzedsiębiorstwo Budowlane N[[owak S]].A.\nKancelaria Adwokacka Wiśniewski sp.j.\nKowalski i Partn...`
- `testy__test_anchor_full.txt` — `...Kowalski i Partnerzy Sp. z o.o,\nPrzedsiębiorstwo Budowlane [[Nowak S,A,\nKancelaria Adwokacka Wiśniewski sp,j,\nKowalski i Partnerzy Sp.z o.o.\nPrzedsiębiorstwo Budow1ane Nowak S]].A.\n\n=== DATA urodzenia — kotwica ur. / dob: ===\nur. 12.0...`

### 14. Desktop zakrył, Mobile nie — całość | NUMER | telefon — 27 wyst., 17 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00009.txt` — `...2\n3.   Naprawa sprzętu                   1    1401   8%     [[1401     1513\n4]].   Usługa transportowa               6     620   8%     372...`
- `clean__doc_00009.txt` — `...8\n5.   Instalacja oprogramowania         6    1363  23%     [[8178    10059]]\n----------------------------------------\nŁĄCZNIE DO ZAPŁATY...`
- `clean__doc_00021.txt` — `...2\n2.   Usługa transportowa               6    1286  23%     [[7716     9491\n3]].   Usługa doradcza                   2     518   8%     103...`
- `clean__doc_00148.txt` — `...-\n1.   Instalacja oprogramowania         9     994  23%     [[8946    11004]]\n2.   Usługa projektowa                 7     538   8%     3...`
- `clean__doc_00176.txt` — `...4\n3.   Wynajem sprzętu biurowego         4     651  23%     [[2604     3203\n4]].   Wynajem sprzętu biurowego         9     585  23%     526...`
- `clean__doc_00181.txt` — `...9\n4.   Wynajem sprzętu biurowego         8    1196  23%     [[9568    11769]]\n----------------------------------------\nŁĄCZNIE DO ZAPŁATY...`
- `clean__doc_00193.txt` — `...7\n2.   Instalacja oprogramowania         2    1416  23%     [[2832     3483\n3]].   Usługa serwisowa                  3     458   8%     137...`
- `clean__doc_00218.txt` — `...4\n5.   Szkolenie zawodowe                8    1042  23%     [[8336    10253]]\n----------------------------------------\nŁĄCZNIE DO ZAPŁATY...`

### 15. Mobile zakrył, Desktop nie — częściowo (granice) | ADRES | ulica/numer domu — 25 wyst., 11 dok.

Hipoteza: Mobile bierze cały adres (ulica + kod + miasto, razem z przecinkiem), Desktop dzieli lub urywa na kodzie pocztowym/mieście.

- `pliki__doc_lvl2_pismo_komornicze.txt` — `...7)\n- nieruchomosci — KW KR1P/00123456/7 (lokal mieszkalny, [[ul. Kosciuszki 18/7, Krakow]])\n\nDo akt komorniczych zalaczono:\n- oswiadczenie majatkow...` (niezakryte: `Krakow`)
- `pliki__doc_test_nowe_encje.txt` — `...lski zamieszkały w Gdańsku.\nPełnomocnik Tomasz Wiśniewski, [[ul. Leśna 12, Kraków]].\nDłużnik Piotr Nowak, Warszawa.\nWierzyciel Marek Wójcik....` (niezakryte: `Kraków`)
- `pliki__doc_test_nowe_encje.txt` — `...ami) ===\nZamieszkały: ul. Leśna 5, 00-001 Warszawa\nAdres: [[ul. Polna 12/3, Kraków]]\nZameldowany w Gdańsku przy ul. Morskiej 7\nMiejscowość: Po...` (niezakryte: `Kraków`)
- `pliki__doc_test_nowe_encje.txt` — `...\n\n=== KOMBINOWANE ===\nJan Nowak, PESEL 85010112345, zam. [[ul. Kwiatowa 3, Warszawa]],\njest właścicielem pojazdu WA 12345 oraz nieruchomości KW ...` (niezakryte: `Warszawa`)
- `testy__bramka_merge_silnik_14_07.txt` — `...ędzie.\n[D2] Poręczyciel: Marek Kot, PESEL 90010155382, zam. [[ul. Wiejska 4, Radom]].\n[D3] Świadek: Hanna Sowa, PESEL 85032204563, ul. Ogrodowa ...` (niezakryte: `Radom`)
- `testy__bramka_merge_silnik_14_07.txt` — `...jska 4, Radom.\n[D3] Świadek: Hanna Sowa, PESEL 85032204563, [[ul. Ogrodowa 2, Lublin]].\n[D4] Pełnomocnik: Jan Zając, tel. 601 111 222.\n[D5] Klient...` (niezakryte: `Lublin`)
- `testy__bramka_merge_silnik_14_07.txt` — `...-001 Gdynia\n[F4] ul. Jana Pawła II 10/5, 20-001 Lublin\n[F5] [[ul. Długa 7, Gdańsk]]\n[F6] ul. Zielona Góra 3, 65-001 Zielona Góra\n[F7] Spotkanie...` (niezakryte: `Gdańsk`)
- `testy__test_adresy_50.txt` — `...0 Lublin\nOCZEKIWANE: 1 ADRES\n\n[D3] po "NABYWCA"\nNABYWCA [[Łukasz Nowak, ul. Dębowa 19/23, 87-100 Białystok\nOCZEKIWANE: ADRES dla ulicy + opcjonalnie OSOBA dla imienia\n\n[D4] w Warszawie]] + kod gdzie indziej\nZamieszkały w Warszawie pod adresem ul...` (niezakryte: `OCZEKIWANE: ADRES dla ulicy + opcjonalnie OSOBA dla imienia\n\n[D4] w Warszawi`)

### 16. Desktop zakrył, Mobile nie — częściowo (granice) | ADRES | ulica/numer domu — 25 wyst., 24 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00140.txt` — `...08.2020 pomiędzy:\n\n1. Mariusz Nowakowski\n   zamieszkałym/ą: [[al. Jana Pawła II 38, 70-001 Rybnik]]\n   NIP: 389-752-67-74  |  PESEL: 69121976025\n   zwany/ą dal...` (niezakryte: `38`)
- `clean__doc_00147.txt` — `...03.2025 pomiędzy:\n\n1. Grzegorz Wieczorek\n   zamieszkałym/ą: [[al. Jana Pawła II 37, 44-100 Wrocław]]\n   NIP: 585-714-22-41  |  PESEL: 99041532652\n   zwany/ą dal...` (niezakryte: `37`)
- `clean__doc_00220.txt` — `...------------------------------\nSPRZEDAWCA:\nBETA S.A.\nAdres: [[al. Jana Pawła II 50, 40-001 Łódź]]\nNIP: 915-583-93-86   REGON: 165063739\nNr konta: PL961090101...` (niezakryte: `50`)
- `clean__doc_00230.txt` — `... PL33114019871952569040983665\n\nNABYWCA:\nMaciej Dudek\nAdres: [[al. Jana Pawła II 99, 50-001 Bydgoszcz]]\nNIP: 256-686-33-42\n\n---------------------------------------...` (niezakryte: `99`)
- `clean__doc_00237.txt` — `... paszportu:\nLE8506762\n\nDANE KONTAKTOWE\n\nAdres zamieszkania:\n[[al. Jana Pawła II 24, 40-001 Łódź]]\nTelefon:\n+48 728 160 930\nAdres e-mail:\nnatalia_jablonska@o2...` (niezakryte: `24`)
- `clean__doc_00277.txt` — `... 14.05.2025 pomiędzy:\n\n1. Bartosz Wójcik\n   zamieszkałym/ą: [[al. Jana Pawła II 129, 80-001 Bytom]]\n   NIP: 515-914-97-59  |  PESEL: 94060913936\n   zwany/ą dal...` (niezakryte: `129`)
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...EGON: 36 1298 450                       REGON: 000 309 256\n[[ul. Pulaskiego 2 0, 32-500 Chrzanow]]      ul. Lwowska 178, 33-100 Tarnow\ntel.: 32 623 45 67    ...` (niezakryte: `0`)
- `stress__doc_00046.txt` — `...osobistego:\nESW922680\n\nDANE KONTAKTOWE\n\nAdres zamieszkania:\n[[ul. Pogrzebieńska 148/21, 02-200 Rzechowo-Gać]]\nTelefon:\n+48 508 242 253\nAdres e-mail:\nsukhrobstachurska@on...` (niezakryte: `ć`)

### 17. Mobile zakrył, Desktop nie — częściowo (granice) | ADRES | inny adres — 23 wyst., 16 dok.

Hipoteza: Mobile bierze cały adres (ulica + kod + miasto, razem z przecinkiem), Desktop dzieli lub urywa na kodzie pocztowym/mieście.

- `clean__doc_00017.txt` — `[[Zielona Góra]], dnia 11.05.2024\n\nSKARGA\n\nJa, niżej podpisany/podpisana Ren...` (niezakryte: `Zielona`)
- `pliki__doc_test_nowe_encje.txt` — `...ńsku.\nSkierowanie do Kliniki Kardiologii.\nWynik z Centrum [[Medycznego przy]] ul. Polnej.\nPrzychodnia Lekarzy Rodzinnych, Wrocław.\nZaśw...` (niezakryte: `przy`)
- `stress__doc_00019.txt` — `...owiatowy Urząd Pracy w Poznaniu\n\nSygn. akt: III K 5633/2023\n[[Tarczek Górny]], dnia 07.03.2024\n\n\nIlkhom Ivanov\nul. Motelowa 170\n45-001 Ni...` (niezakryte: `Tarczek`)
- `stress__doc_00185.txt` — `Urząd Gminy Warszawa-Wola\n\nSygn. akt: I Co 3873/2023\n[[Uchań Górny]], dnia 06.03.2022\n\n\nIwa Przydryga\nul. Murna 164\n03-300 Kułyg...` (niezakryte: `Uchań`)
- `stress__doc_00232.txt` — `...Tatarska\n   zamieszkałym/ą: ul. Słoneczna dolina 120/29, 31-[[001 Czepów\n   N]]IP: 768-633-41-46  |  PESEL: 61060787373\n   zwany/ą dalej „Z...` (niezakryte: `N`)
- `stress__doc_00266.txt` — `[[Las Jaworski]], dnia 09.07.2022\n\nSKARGA\n\nJa, niżej podpisany/podpisana Sah...` (niezakryte: `Las`)
- `testy__bramka_merge_silnik_14_07.txt` — `..., tel. 601 111 222.\n[D5] Klient odwiedził oddział w mieście [[Jelenia Góra]] w zeszłym miesiącu.\n\n======================================...` (niezakryte: `Jelenia`)
- `testy__test_adres_60.txt` — `...cław\nWrocław, 50-001\n90-001 Łódź\nŁódź, 90-001\n40-001 Kat[[owice\nKatowice]], 40-001\n70-001 Szczecin\nSzczecin, 70-001\n15-950 Białysto...` (niezakryte: `Katowice`)

### 18. Desktop zakrył, Mobile nie — całość | NUMER | księga wieczysta (KW) — 23 wyst., 16 dok.

Hipoteza: Desktop maskuje numer działki ewidencyjnej (NNNNNN.NNNN.NNNN) po „Nr działki ewidencyjnej”; Mobile nie (etykieta „KW” to artefakt podtypu).

- `clean__doc_00001.txt` — `...księgi wieczystej:\nPO1P/00793300/9\nNr działki ewidencyjnej:\n[[711878.0052.5931]]/5\n\nOświadczam, że podane dane są zgodne ze stanem faktyczny...`
- `clean__doc_00019.txt` — `...księgi wieczystej:\nWA1M/00067174/8\nNr działki ewidencyjnej:\n[[232413.0082.8043]]/1\n\nOświadczam, że podane dane są zgodne ze stanem faktyczny...`
- `clean__doc_00100.txt` — `...księgi wieczystej:\nLD1M/00472094/0\nNr działki ewidencyjnej:\n[[786789.0041.203]]\n\nOświadczam, że podane dane są zgodne ze stanem faktycznym....`
- `clean__doc_00191.txt` — `...księgi wieczystej:\nKA1K/00024549/3\nNr działki ewidencyjnej:\n[[116656.0090.3084]]\n\nOświadczam, że podane dane są zgodne ze stanem faktycznym....`
- `clean__doc_00199.txt` — `...księgi wieczystej:\nKA1K/00133461/5\nNr działki ewidencyjnej:\n[[492649.0039.4817]]\n\nOświadczam, że podane dane są zgodne ze stanem faktycznym....`
- `clean__doc_00243.txt` — `...księgi wieczystej:\nLD1M/00599822/6\nNr działki ewidencyjnej:\n[[384682.0027.3016]]/19\n\nOświadczam, że podane dane są zgodne ze stanem faktyczn...`
- `clean__doc_00276.txt` — `...księgi wieczystej:\nWR1K/00272165/2\nNr działki ewidencyjnej:\n[[309215.0039.4998]]/19\n\nOświadczam, że podane dane są zgodne ze stanem faktyczn...`
- `stress__doc_00005.txt` — `...księgi wieczystej:\nWA1M/00617314/8\nNr działki ewidencyjnej:\n[[428838.0008.822]]\n\nOświadczam, że podane dane są zgodne ze stanem faktycznym....`

### 19. Inny typ (Mobile=OSOBA, Desktop=ADRES) | Mobile=OSOBA, Desktop=ADRES | 1 wyraz — 23 wyst., 21 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00000.txt` — `...AKTOWE\n\nAdres zamieszkania:\nul. Ogrodowa 36, 45-001 Bielsko-[[Biała]]\nTelefon:\n+48 663 794 026\nAdres e-mail:\npawel_szymanski98@on...`
- `stress__doc_00126.txt` — `...9.06.2023 pomiędzy:\n\n1. Mikola Kolon\n   zamieszkałym/ą: ul. [[Władysława]] łokietka 178, 45-001 Kańkowo\n   NIP: 131-207-35-64  |  PESE...`
- `ocr__doc_00006.txt` — `...AKTOWE\nAdres zamieszkania:\nul. Kolejowa 183, 20-100 Bielsko-[[Biala]]\nTelefon:\n+48 605 858 864\nAdres e-mail:\nkarolinazajac@o2.pl\n...`

### 20. Mobile zakrył, Desktop nie — całość | KWOTA | bez waluty (sama liczba) — 21 wyst., 9 dok.

Hipoteza: Kwoty w tabelach faktur bez „zł/PLN” (np. „2 800,00”, „350,00”): Mobile maskuje, Desktop nie. Reguła: liczba z 2 miejscami po przecinku w kolumnach tabeli.

- `pliki__doc_lvl1_decyzja_administracyjna.txt` — `...                          tel. 58 743 59 22\n\nZalaczniki:\n[[1. Os]]wiadczenie o wysokosci zarobkow za ostatnie 12 miesiecy\n2. ...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...───────\n1.   System monitorowania pacjenta      1    szt.  [[42 000,00]]  42 000,00\n     MEDITECH PRO X3 (SN: MP2024-0847)\n2.   In...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...847)\n2.   Instalacja i konfiguracja          8    godz.    [[350,00]]   2 800,00\n3.   Szkolenie personelu medycznego     2    dn...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...  Instalacja i konfiguracja          8    godz.    350,00   [[2 800,00]]\n3.   Szkolenie personelu medycznego     2    dni    1 500,...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...800,00\n3.   Szkolenie personelu medycznego     2    dni    [[1 500,00]]   3 000,00\n4.   Licencja oprogramowania 12 m-cy    1    sz...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...  Szkolenie personelu medycznego     2    dni    1 500,00   [[3 000,00]]\n4.   Licencja oprogramowania 12 m-cy    1    szt.   3 600,...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...000,00\n4.   Licencja oprogramowania 12 m-cy    1    szt.   [[3 600,00]]   3 600,00\n───────────────────────────────────────────────...`
- `ocr__doc_00013.txt` — `...23% 9400 11562\n3. Konsultacja techniczna 3 471 8% 1413 1526\n[[4. Sz]]kolenie zawodowe 3 1085 8% 3255 3515\nLACZNIE DO ZAPLATY: 338...`

### 21. Mobile zakrył, Desktop nie — częściowo (granice) | OSOBA | 2+ wyrazów — 20 wyst., 12 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady. W 55% przypadków niezakryty fragment zawiera ostatni wyraz (nazwisko).

- `clean__doc_00194.txt` — `...chał Nowakowski, zamieszkały/zamieszkała przy ul. Nowa 92 w [[Gdańsku, PESEL 5509183459]]5, składam niniejszą skargę na działania Adama Jankowskiego....` (niezakryte: `Gdańsku`)
- `clean__doc_00194.txt` — `...ały/zamieszkała przy ul. Nowa 92 w Gdańsku, PESEL 5509183459[[5, składam niniejszą skargę na działania Adama Jankowskiego]].\n\nW dniu 06.03.2020 Adam Jankowski dopuścił/dopuściła się z...` (niezakryte: `składam niniejszą skargę na działania`)
- `pliki__doc_lvl1_decyzja_administracyjna.txt` — `...acach),\nnastepnie: 1 173,80 PLN brutto miesiecznie.\n\nZasi[[lek bedzie wyplacany]] przelewem na rachunek bankowy:\nPL 43 1090 2590 0000 0001 4...` (niezakryte: `bedzie wyplacany`)
- `stress__doc_00095.txt` — `... 199917385\nNr konta: PL52109010146846022356972521\n\nNABYWCA:\n[[Indira Biała]]\nAdres: ul. Ścienna 143/7, 10-100 Niemojki\nNIP: 755-494-71-7...` (niezakryte: `Biała`)
- `stress__doc_00181.txt` — `...--------------\n\nDANE OSOBOWE WNIOSKODAWCY\n\nImię i nazwisko:\n[[Sascha Biała]]\nData urodzenia:\n23.01.1982\nPESEL:\n95061705777\nNr dowodu oso...` (niezakryte: `Biała`)
- `stress__doc_00227.txt` — `... 402321291\nNr konta: PL43325000033381674233629344\n\nNABYWCA:\n[[Oliviia Wrobel]]\nAdres: ul. Popieluszki 166, 00-001 Szymanowice Górne\nNIP: 7...` (niezakryte: `Wrobel`)
- `testy__bramka_merge_silnik_14_07.txt` — `...Na wniosek Jana Kowalskiego złożono pismo.\n[A2] Spotkanie z [[Piotrem Kowalskim odbyło się w biurze.\n[A3] W imieniu Anny Wiśniewskiej]] podpisano protokół.\n[A4] Pełnomocnictwo udzielone Marcinowi...` (niezakryte: `odbyło się w biurze.\n[A3] W imieniu`)
- `testy__bramka_merge_silnik_14_07.txt` — `...9109010147449555252110732.\n\nPełnomocnik zleceniodawcy: adw. [[Anna Wiśniewska, nr wpisu 67890.\nW imieniu Katarzyny Grabowskiej]] działam na podstawie pełnomocnictwa.\n\nUstaliliśmy z Tomkiem...` (niezakryte: `W imieniu`)

### 22. Mobile zakrył, Desktop nie — całość | NUMER | nr dokumentu/sygnatura/z literami — 20 wyst., 10 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_test_nowe_encje.txt` — `...r HC-2024-00789\nNr pacjenta PAC/2024/1234\nNumer kartoteki [[KAR-00045-B]]\n\n=== POLISA UBEZPIECZENIOWA ===\nPolisa ubezpieczeniowa n...`
- `testy__bramka_merge_silnik_14_07.txt` — `...2] Pozwana podaje: ur. 15.09.1992 w Krakowie.\n[K3] Pismo nr [[DEC-2026/0451]] w sprawie dotyczącej nieruchomości.\n[K4] Na podstawie art. ...`
- `testy__test_hard_v2.txt` — `...:\nImię i nazwisko: Bartosz Jab1oński\nPESE1: 91O4O512361\nN[[lP: 526-O3O-O1-34]]\nAdres: u. Niepodleg1ości I35, 2O-1OO Rybnik\nTel: +48 6O6 ...`
- `testy__test_hard_v2.txt` — `...ię i nazwisko: M0nka Nowak0sa\nPESE1 pacjenta: 800I23I2349\n[[NlP: 831-I45-84-O9]]\nAdres: u Kopernka I2O, 3I-OOI Katowce\nNr konta: PL04 3250...`
- `testy__test_hard_v2.txt` — `...56-786\nNIP nabywcy: 45I-OS2-35-26\nREGON: I23456785\nIBAN: [[PL89 1090 10l4 7449 5552 52llO732]]\n\nDANE DODATKOWE:\nNr PESEL: 9l040512 361\nNr paszportu: A...`
- `testy__test_nip_warianty.txt` — `...czekiwane: cały fragment "NIP: XXX-XXX-XX-XX" zamaskowany → [[NUMER-001]]\n\nFaktura VAT nr FV/2024/03/0041.\nSprzedawca: Firma Testowa ...`
- `testy__test_nip_warianty.txt` — `...W pliku widnieje numer 526-000-13-29 powiązany z reklamacją [[RK-204]].\n\n--- SEKCJA 7: PREFIKS PL ---\nOczekiwane: NIP z prefiksem ...`
- `testy__test_pesel_migracja.txt` — `90051512340\nPESEL: 85032145675\n[[63lZO9B76S3]]\n900515 12340\n8503214-5675\n90040512345\nPESEL: 6312098765...`

### 23. Mobile zakrył, Desktop nie — całość | NUMER | nr umowy — 20 wyst., 18 dok.

Hipoteza: Numer umowy w nagłówku („UMOWA O ŚWIADCZENIE USŁUG nr U-00255/2018”): Mobile maskuje, Desktop nie. Reguła: „nr” + litera-cyfry-/rok po tytule umowy.

- `clean__doc_00053.txt` — `UMOWA O ŚWIADCZENIE USŁUG\n[[nr U-00726/2025]]\n\nzawarta dnia 30.08.2022 pomiędzy:\n\n1. Elżbieta Kowalczyk\n ...`
- `clean__doc_00097.txt` — `UMOWA O ŚWIADCZENIE USŁUG\n[[nr U-00914/2018]]\n\nzawarta dnia 30.03.2024 pomiędzy:\n\n1. Ewa Piotrowska\n   za...`
- `clean__doc_00106.txt` — `UMOWA O ŚWIADCZENIE USŁUG\n[[nr U-00809/2025]]\n\nzawarta dnia 29.05.2020 pomiędzy:\n\n1. Paweł Nowak\n   zamie...`
- `clean__doc_00146.txt` — `UMOWA O ŚWIADCZENIE USŁUG\n[[nr U-00214/2018]]\n\nzawarta dnia 25.06.2024 pomiędzy:\n\n1. Zbigniew Krawczyk\n  ...`
- `clean__doc_00147.txt` — `UMOWA O ŚWIADCZENIE USŁUG\n[[nr U-00005/2019]]\n\nzawarta dnia 24.03.2025 pomiędzy:\n\n1. Grzegorz Wieczorek\n ...`
- `clean__doc_00150.txt` — `UMOWA O ŚWIADCZENIE USŁUG\n[[nr U-00641/2024]]\n\nzawarta dnia 28.12.2023 pomiędzy:\n\n1. Maria Jankowska\n   z...`
- `stress__doc_00006.txt` — `UMOWA O ŚWIADCZENIE USŁUG\n[[nr U-00958/2023]]\n\nzawarta dnia 22.02.2021 pomiędzy:\n\n1. Ulrich Jędral\n   zam...`
- `stress__doc_00063.txt` — `UMOWA O ŚWIADCZENIE USŁUG\n[[nr U-00234/2025]]\n\nzawarta dnia 06.02.2023 pomiędzy:\n\n1. Berenika Żurawska\n  ...`

### 24. Mobile zakrył, Desktop nie — częściowo (granice) | ADRES | kod pocztowy (+miasto) — 18 wyst., 9 dok.

Hipoteza: Mobile bierze cały adres (ulica + kod + miasto, razem z przecinkiem), Desktop dzieli lub urywa na kodzie pocztowym/mieście.

- `ocr__doc_00017.txt` — `... 84998/2018\nData: 21.08.2021\nMateusz Szymański\nul. Nowa 194\n[[40-001 Łód]]ž\nZAWIADOMIENIE O WSZCZECIU EGZEKUCJI\nNa podstawie tytulu wy...` (niezakryte: `Łód`)
- `testy__bramka_merge_silnik_14_07.txt` — `...a: PL61 1090 1014 0000 0712 1981 2874\n[H4] NIP 526-021-15-81[[00-001 Warszawa]]\n[H5] Faktura VAT nr FV/2026/000088\n[H6] Faktura VAT 26/06/0...` (niezakryte: `Warszawa`)
- `testy__test_adres_60.txt` — `...1-001\n50-001 Wrocław\nWrocław, 50-001\n90-001 Łódź\nŁódź, 9[[0-001\n40-001 Kat]]owice\nKatowice, 40-001\n70-001 Szczecin\nSzczecin, 70-001\n...` (niezakryte: `0-001`)
- `testy__test_adres_60.txt` — `...-001\n90-001 Łódź\nŁódź, 90-001\n40-001 Katowice\nKatowice, [[40-001\n70-001 Szc]]zecin\nSzczecin, 70-001\n15-950 Białystok\nBialystok, 15-950...` (niezakryte: `40-001`)
- `testy__test_adres_60.txt` — `...-001 Katowice\nKatowice, 40-001\n70-001 Szczecin\nSzczecin, [[70-001\n15-950 Biał]]ystok\nBialystok, 15-950\nLodz, 90-001\nKrakow, 31-610\n00-0...` (niezakryte: `70-001`)
- `testy__test_adres_60.txt` — `...rszawa\n00-001 Warszawa NIP 526-021-15-81\nNIP 526-021-15-81[[00-001 Wrocław]]\nIBAN PL61102010260000042270201111 00-001 Warszawa\n00-001 ...` (niezakryte: `Wrocław`)
- `testy__test_adresy_50.txt` — `...lności + miasto obcięte (z bugs doc_00059)\npI. Wolhoci 175 [[30-001 Wodaw]]\nOCZEKIWANE: prawdopodobnie BRAK (sufit OCR) — dokumentować...` (niezakryte: `Wodaw`)
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...ódź" (zero osieroconego "ź")\n\n[B2] Sam para kod+miasto Łódź\n[[90-001 Łódź]]\nOCZEKIWANE: 1 TOKEN ADRES na całość, zero jawnego "Łódź"\n\n[...` (niezakryte: `1`)

### 25. Desktop zakrył, Mobile nie — całość | ADRES | ulica/numer domu — 17 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_adres_60.txt` — `ul. Marszałkowska 15/3, 00-001 Warszawa\n[[ul. Marszałkowska 15/3, 00-001]]\nal. Niepodległości 21, 02-653 Warszawa\npl. Konstytucji 4,...`
- `testy__test_adres_60.txt` — `...wska 15/3, 00-001 Warszawa\nul. Marszałkowska 15/3, 00-001\n[[al. Niepodległości 21, 02-653 Warszawa]]\npl. Konstytucji 4, 00-552 Warszawa\nos. Słoneczne 8, 31-34...`
- `testy__test_adres_60.txt` — `...owska 15/3, 00-001\nal. Niepodległości 21, 02-653 Warszawa\n[[pl. Konstytucji 4, 00-552 Warszawa]]\nos. Słoneczne 8, 31-343 Kraków\nul. Długa 7\nul. Długa 7, ...`
- `testy__test_adres_60.txt` — `...ci 21, 02-653 Warszawa\npl. Konstytucji 4, 00-552 Warszawa\n[[os. Słoneczne 8, 31-343 Kraków]]\nul. Długa 7\nul. Długa 7, Gdańsk\nul .Długa 7, 80-001 Gdań...`
- `testy__test_adres_60.txt` — `...tytucji 4, 00-552 Warszawa\nos. Słoneczne 8, 31-343 Kraków\n[[ul. Długa 7]]\nul. Długa 7, Gdańsk\nul .Długa 7, 80-001 Gdańsk\nul,Długa ...`
- `testy__test_adres_60.txt` — `...ńsk\nul .Długa 7, 80-001 Gdańsk\nul,Długa 7, 80-001 Gdańsk\n[[ul. Gdańska-Sopocka 3/1, 81-001 Gdynia]]\nul. Jana Pawła II 15, 00-001 Warszawa\nul. Zielona Góra 3,...`
- `testy__test_adres_60.txt` — `...a 7, 80-001 Gdańsk\nul. Gdańska-Sopocka 3/1, 81-001 Gdynia\n[[ul. Jana Pawła II 15, 00-001 Warszawa]]\nul. Zielona Góra 3, 65-001 Zielona Góra\nul. Władysława Re...`
- `testy__test_adres_60.txt` — `... 3/1, 81-001 Gdynia\nul. Jana Pawła II 15, 00-001 Warszawa\n[[ul. Zielona Góra 3, 65-001 Zielona Góra]]\nul. Władysława Reymonta 8, 60-001 Poznań\nul. Kazimierza W...`

### 26. Desktop zakrył, Mobile nie — całość | NUMER | nr dokumentu/sygnatura/z literami — 17 wyst., 9 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...       e-mail: p.dabrowski @meditech-sol.pl\n               [[PWZ 2 345678]] (fizjoterapeuta)\n\nPrzedmiot zlecenia: Przeprowadzenie szk...`
- `pliki__doc_test_guard.txt` — `...ami: PL 27 1140 2004 0000 3002 0135 5387\nIBAN zagraniczny: [[DE89370400440532013000]]\nIBAN z enterem w środku (OCR):\nPL 2 7 1 1 4 0 2 0 0 4 0 0...`
- `pliki__doc_test_nowe_encje.txt` — `...JNE ===\nPojazd o numerze rejestracyjnym WA 12345\nSamochód [[KR 4AB67]]\nTablica rejestracyjna GD 99XYZ\nPojazd PO 12AB3\n\n=== KSI...`
- `pliki__doc_test_nowe_encje.txt` — `...racyjnym WA 12345\nSamochód KR 4AB67\nTablica rejestracyjna [[GD 99XYZ]]\nPojazd PO 12AB3\n\n=== KSIĘGI WIECZYSTE ===\nNieruchomość ...`
- `pliki__doc_test_nowe_encje.txt` — `...\nSamochód KR 4AB67\nTablica rejestracyjna GD 99XYZ\nPojazd [[PO 12AB3]]\n\n=== KSIĘGI WIECZYSTE ===\nNieruchomość objęta księgą wie...`
- `testy__test_anchor_full.txt` — `...14 0000 0712 1981 2874\nPL27 1140 2004 0000 3102 0135 5387\n[[PL61 1O9O 1O14 OOOO O712 1981 2874]]\nPL27 114O 2OO4 OOOO 31O2 O135 5387\nPL6l l090 l0l4 0000 07...`
- `testy__test_anchor_full.txt` — `...04 0000 3102 0135 5387\nPL61 1O9O 1O14 OOOO O712 1981 2874\n[[PL27 114O 2OO4 OOOO 31O2 O135 5387]]\nPL6l l090 l0l4 0000 07l2 l98l 2874\nPL 61 1090 1014 0000 0...`
- `testy__test_anchor_full.txt` — `...14 OOOO O712 1981 2874\nPL27 114O 2OO4 OOOO 31O2 O135 5387\n[[PL6l l090 l0l4 0000 07l2 l98l 2874]]\nPL 61 1090 1014 0000 0712 1981 2874\n\n=== ADRES — kotwica...`

### 27. Mobile zakrył, Desktop nie — całość | OSOBA | 1 wyraz — 17 wyst., 9 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00035.txt` — `[[Bielsko]]-Biała, dnia 17.05.2020\n\nSKARGA\n\nJa, niżej podpisany/podpisa...`
- `clean__doc_00035.txt` — `Bielsko-[[Biała]], dnia 17.05.2020\n\nSKARGA\n\nJa, niżej podpisany/podpisana Kam...`
- `clean__doc_00035.txt` — `... Wójcik, zamieszkały/zamieszkała przy ul. Nowa 96 w Bielsku-[[Białej]], PESEL 58030985174, składam niniejszą skargę na działania Ł...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...listyczny im.\nNIP: 7 12-304-56 78                      Sw. [[Lukasza]] w Tarnowie\nREGON: 36 1298 450                       REGON:...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...\nOCZEKIWANE: TOKEN KWOTA, zero jawnego "OOO" ani "zł"\n\n[A4] [[Samo]] zł na linii (minimalny przypadek)\n1500 zł\nOCZEKIWANE: TOKEN...`
- `testy__test_hard_v2.txt` — `...rwca 2O26 r. w Kielcach\n\nZLECENIODAWCA:\nImię i nazwisko: [[Bartosz]] Jab1oński\nPESE1: 91O4O512361\nNlP: 526-O3O-O1-34\nAdres: u...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...=======================================================\n\n-- [[Daty]] --\nData zawarcia: 15 marca 2024\nTermin płatności: 2024-03-1...`

### 28. Mobile zakrył, Desktop nie — całość | NUMER | telefon — 16 wyst., 8 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_test_guard.txt` — `...\n=== MEDIUM: TELEFON ===\nTel. kontaktowy: +48 600 123 456\n[[Telefon: 22-456-789]]\nKom: 501 234 567\nNumer: +48501234567\n\n=== KOMBINOWANE —...`
- `testy__test_degradacje_lvl.txt` — `...       ?       ?\n  IBAN         1       1       ?       ?\n  [[TELEFON      2       2]]       ?       ?\n  EMAIL        2       2       ?       ?\n  ...`
- `testy__test_hard_v2.txt` — `...1\nNlP: 526-O3O-O1-34\nAdres: u. Niepodleg1ości I35, 2O-1OO [[Rybnik\nTel: +48 6O6 2I9]] T2T\ne-mai1: bartosz.jab1owski@prawnik.p1\nDowód osobisty: ...`
- `testy__test_hard_v2.txt` — `...250 000J 5633 9560 7883 1852\ne-mail: b.nowakowska@onet.pl\n[[Tel: (32) 456-78-9O]]\n\nDANE PODATKOWE:\nNIP sprzedawcy: 5l2-34-56-786\nNIP naby...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...IP sprzedawcy: 521-33-15-332\nNIP nabywcy: 9571066250\nREGON: [[012345678]]\n\n-- OCR lvl3 --\nNlP: 651-554-28-60\nN1P: 549 744 89 42\n\n====...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...1066250\nREGON: 012345678\n\n-- OCR lvl3 --\nNlP: 651-554-28-60\n[[N1P: 549 744 89 42]]\n\n==========================================================...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...==========================================================\n\n[[tel. kom.: 48 606 219]] 727\nTelefon: +48 512 345 678\ntel. stacjonarny: 81 123-45-67...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...====================================\n\ntel. kom.: 48 606 219 [[727\nTelefon: +48 512 345 6]]78\ntel. stacjonarny: 81 123-45-67\nKontakt: (22) 765-43-21\nFa...`

### 29. Mobile zakrył, Desktop nie — częściowo (granice) | FIRMA | z formą prawną — 16 wyst., 15 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00021.txt` — `...75597\n\n----------------------------------------\nSPRZEDAWCA:\n[[Serwis AGD ELEKTRO Sp. z o.o]].\nAdres: ul. Długa 151, 65-001 Białystok\nNIP: 434-123-28-19 ...` (niezakryte: `Serwis AGD`)
- `clean__doc_00135.txt` — `...67732\n\n----------------------------------------\nSPRZEDAWCA:\n[[GAMMA Sp. z o.o]]. S.K.A.\nAdres: ul. Dębowa 193, 02-200 Kielce\nNIP: 617-908-6...` (niezakryte: `GAMMA Sp`)
- `pliki__doc_lvl1_decyzja_administracyjna.txt` — `...24 r. Zgodnie z dokumentacja, Wnioskodawca byl zatrudniony\n[[w firmie STOCZNIA GDANSKA SERWIS Sp. z o.o]]., NIP 583-001-89-23, REGON 190560433,\nw okresie od 01.03.2...` (niezakryte: `w firmie`)
- `pliki__doc_lvl1_decyzja_administracyjna.txt` — `...wiadczenie o wysokosci zarobkow za ostatnie 12 miesiecy\n2. [[Kopia swiadectwa pracy z STOCZNIA GDANSKA SERWIS Sp. z o.o]].\n\nDoreczone: Robertowi Nowakowskiemu, PESEL 78031512378, ...` (niezakryte: `Kopia swiadectwa pracy z`)
- `testy__test_email_adres_hard.txt` — `...mail: piotr_dudek45@interia.pl, tel. 512 000 111.\nKupujący: [[Firma XYZ Sp. z o.o]]., ul. Przemysłowa 10, 00-001 Warszawa.\nPrzedmiot: laptop Le...` (niezakryte: `Firma`)
- `testy__test_nip_warianty.txt` — `...ny → NUMER-001\n\nFaktura VAT nr FV/2024/03/0041.\nSprzedawca: [[Firma Testowa Sp. z o.o]]., NIP: 521-334-00-01.\nNabywca: Jan Kowalski, ul. Polna 12, ...` (niezakryte: `Firma`)
- `testy__test_silnik_trudny_przed_merge_14_07.txt` — `...a: Kowalski, Nowak, Pietraszko, Wiśniewski, Kot.\n\nWspólnicy [[prowadzą działalność gospodarczą pod firmą AGROBUD Sp. z o.o]]. z siedzibą w Warszawie, NIP 5252445767, KRS 0000123456.\n\nM...` (niezakryte: `prowadzą działalność gospodarczą pod firmą`)

### 30. Inny typ (Mobile=OSOBA, Desktop=FIRMA) | Mobile=OSOBA, Desktop=FIRMA | 1 wyraz — 16 wyst., 6 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_stresstest_silnik_guard_lvl0_3.txt` — `...═════\n\nUMOWA ZLECENIA\n\nZleceniodawca: Kancelaria Prawna [[Nowak]] & Partnerzy Sp. k.\n               ul. Jana Kowalskiego 5/2...`
- `stress__doc_00054.txt` — `...o, PESEL 69072059273, składam niniejszą skargę na działania [[Asadbek]] Biała.\n\nW dniu 07.03.2024 Asadbek Biała dopuścił/dopuściła ...`
- `stress__doc_00054.txt` — `... 69072059273, składam niniejszą skargę na działania Asadbek [[Biała]].\n\nW dniu 07.03.2024 Asadbek Biała dopuścił/dopuściła się za...`
- `stress__doc_00162.txt` — `...a, PESEL 60110299985, składam niniejszą skargę na działania [[Ilgar]] Kiezik.\n\nW dniu 26.10.2021 Ilgar Kiezik dopuścił/dopuściła ...`
- `stress__doc_00235.txt` — `...Dz. U. z 2023 r. poz. 775 ze zm.)\n\npo rozpatrzeniu wniosku:\n[[Spartak]] Pronina\nPESEL: 67070371768\nNIP: 333-305-91-22\nadres: ul. Pl...`
- `stress__doc_00253.txt` — `...e, PESEL 73022494140, składam niniejszą skargę na działania [[Anar]] Data.\n\nW dniu 08.02.2023 Anar Data dopuścił/dopuściła się z...`
- `stress__doc_00292.txt` — `...a, PESEL 97062794073, składam niniejszą skargę na działania [[Rimma]] Data.\n\nW dniu 20.11.2022 Rimma Data dopuścił/dopuściła się ...`

### 31. Inny typ (Mobile=ADRES, Desktop=OSOBA) | Mobile=ADRES, Desktop=OSOBA | 1 wyraz — 14 wyst., 11 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00017.txt` — `Zielona [[Góra]], dnia 11.05.2024\n\nSKARGA\n\nJa, niżej podpisany/podpisana Ren...`
- `stress__doc_00019.txt` — `... Urząd Pracy w Poznaniu\n\nSygn. akt: III K 5633/2023\nTarczek [[Górny]], dnia 07.03.2024\n\n\nIlkhom Ivanov\nul. Motelowa 170\n45-001 Ni...`
- `stress__doc_00266.txt` — `Las [[Jaworski]], dnia 09.07.2022\n\nSKARGA\n\nJa, niżej podpisany/podpisana Sah...`

### 32. Mobile zakrył, Desktop nie — całość | ADRES | kod pocztowy (+miasto) — 14 wyst., 7 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl2_pismo_komornicze.txt` — `...n Zielinski\nPESEL: 82 09 14 23456\nul. Kosciuszki 18 m. 7\n[[31-127]] K r a k o w\ntel. kom.: 793 456 789\n\nWierzyciel:\nBanku M...`
- `testy__test_adres_60.txt` — `...om\nOO-OO1 Warszawa\n3l-61O Kraków\n00-001Warszawa\nWarszawa[[00-001\n70-001Szc]]zecin80-001Gdańsk31-610Kraków\n15-2024\n1999\n65-110\n43-300...`
- `testy__test_adres_60.txt` — `...001\n70-001Szczecin80-001Gdańsk31-610Kraków\n15-2024\n1999\n[[65-110]]\n43-300\n00-001 Warszawa, 80-001 Gdańsk, 31-610 Kraków\nPES...`
- `testy__test_adres_60.txt` — `...001Szczecin80-001Gdańsk31-610Kraków\n15-2024\n1999\n65-110\n[[43-300]]\n00-001 Warszawa, 80-001 Gdańsk, 31-610 Kraków\nPESEL 90051...`
- `testy__test_adresy_50.txt` — `...,\nOCZEKIWANE: 1 ADRES\n\n[C3] miasto przed kodem (spacja)\n[[Warszawa 00-001]]\nOCZEKIWANE: 1 ADRES\n\n[C4] miasto przed kodem (przecinek)...`
- `testy__test_adresy_50.txt` — `...OCZEKIWANE: 1 ADRES\n\n[C4] miasto przed kodem (przecinek)\n[[Kraków, 30-001]]\nOCZEKIWANE: 1 ADRES\n\n--- SEKCJA D: ADRES W ZDANIU (konte...`
- `testy__test_email_adres_hard.txt` — `...100 Lublin.\n(brak prefiksu ul.)\n\nSkrócony opis: Wolności 99 [[Sosnowiec 41-200]] (kolejność zamieniona).\n\n--- SEKCJA 6: OSOBA BEZ KEYWORDU —...`
- `testy__test_kod_pocztowy_migracja.txt` — `00-001 Warszawa\n80-001 Gdańsk\n31-610 Kraków\n[[00-001]]\nAdres zamieszkania: ul. Lipowa 5, 50-001 Wrocław\nZameldow...`

### 33. Mobile zakrył, Desktop nie — całość | KWOTA | z walutą — 13 wyst., 4 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_b_word_boundary_diacritics_08_07.txt` — `..."OOO" ani "zł"\n\n[A4] Samo zł na linii (minimalny przypadek)\n[[1500 zł]]\nOCZEKIWANE: TOKEN KWOTA\n\n[A5] Kontrola — PLN zamiast zł (St...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...LN zamiast zł (Structural powinien łapać bez Anchor)\nKwota: [[1234 PLN]] netto\nOCZEKIWANE: TOKEN KWOTA\n\n[A6] Kontrola — prefix zł (i...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...A6] Kontrola — prefix zł (inny wzorzec, \b przed zł działa)\n[[zł 2500,00]]\nOCZEKIWANE: TOKEN KWOTA\n\n[A7] Kwota słowna S4-A z samym "zł...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...ontrola S4-A — "złotych" kończy się ASCII (powinno działać)\n[[kwota pięćset złotych]]\nOCZEKIWANE: TOKEN KWOTA\n\n[A9] S4-B z (?!\p{L}) — kontrola n...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...WANE: TOKEN KWOTA\n\n[A9] S4-B z (?!\p{L}) — kontrola naprawy\n[[pięćset zł]]\nOCZEKIWANE: TOKEN KWOTA (ten sam tekst co A4, inna ścieżka ...`
- `testy__test_kwota_regresja_08_07.txt` — `...kiety\n15 000,00 zł\n\n[K5] litera O zamiast zer, bez etykiety\n[[15 OOO,OO zł]]\n\n[K6] czyste cyfry, Z etykietą "kwota:"\nkwota: 15 000,00 zł...`
- `testy__test_kwota_regresja_08_07.txt` — `...ałe złote)\n15 000 zł\n\n[K9] litera O zamiast zer, bez grosze\n[[15 OOO zł]]\n\n==========================================================...`
- `testy__test_kwota_regresja_08_07.txt` — `...00,00 zł\n\n[K11] ten sam kształt co K5, liczba 22 zamiast 15\n[[22 OOO,OO zł]]\n\n==========================================================...`

### 34. Mobile zakrył, Desktop nie — całość | EMAIL | email — 13 wyst., 6 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_email_adres_hard.txt` — `...01 Gdynia. PESEL: 87050612345.\n\nOCR wariant (spacja w local-[[part przed]] @):\nAdres mailowy: justyna.dud ek@gmail.com — do weryfikacj...`
- `testy__test_hard_v2.txt` — `...dleg1ości I35, 2O-1OO Rybnik\nTel: +48 6O6 2I9 T2T\ne-mai1: [[bartosz.jab1owski@prawnik.p1]]\nDowód osobisty: EFG 456789\nPaszport: AB I234567\n\nZLECEN...`
- `testy__test_hard_v2.txt` — `...owce\nNr konta: PL04 3250 000J 5633 9560 7883 1852\ne-mail: [[b.nowakowska@onet.pl]]\nTel: (32) 456-78-9O\n\nDANE PODATKOWE:\nNIP sprzedawcy: 5l...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...ki@interia.pl\nE-mail: m.wisniew ska@gmail.com\n\n-- OCR lvl3: [[spacja przed]] @ --\nAdres mailowy: pkowalski @firma.pl\n\n-- Z kontekstem e-...`
- `testy__test_sklejanie_encji_07_07.txt` — `...-654-32-10, tel. 511222333, PL91109010140000071219812875, z.[[baranowski@poczta-firmowa.pl, ul]]. Świętokrzyska 22/5, 00-050 Warszawa, 8765,43 zł, FV2026123...`
- `testy__test_ui2_encje_silnik.txt` — `... błędną sumą, ur. + data, ur. w + miasto, sygnatura z „nr”, [[email@fragment]]\n\n==========================================================...`
- `testy__test_ui2_guard_only.txt` — `...4/2022\n\nRubryka F — fragment adresu email w kopii (ucięty):\n[[jan.kowalski@\n\nRubryka]] G — inny fragment email:\nemail@fragment\n\nRubryka H — sygnat...`
- `testy__test_ui2_guard_only.txt` — `...A: 89765432 (jeśli silnik nie zamaskował)\n  EMAIL_FRAGMENT: [[jan.kowalski@]], email@fragment\n\nRED: brak (silnik maskuje wycieki — OK)\n\nK...`

### 35. Mobile zakrył, Desktop nie — całość | NUMER | sygnatura sprawy — 12 wyst., 8 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__bramka_merge_silnik_14_07.txt` — `...u (YELLOW — nie blokują eksportu)\nOCZEKIWANE: YELLOW na ur./[[sygn./gołym mieście jeśli silnik zostawił jawne]]\n===========================================================...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...n: +48 512 345 678\ntel. stacjonarny: 81 123-45-67\nKontakt: ([[22) 765-43-21]]\nFax: 12 456 78 90\n\n========================================...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `... 678\ntel. stacjonarny: 81 123-45-67\nKontakt: (22) 765-43-21\n[[Fax: 12 456 78 90]]\n\n==========================================================...`
- `testy__test_pesel_warianty.txt` — `...wie art. 104 k.p.a. orzekam jak w sentencji.\n\n--- SEKCJA 4: [[OCR-ARTEFAKT]] W SŁOWIE KLUCZOWYM ---\nOcrNormalizer powinien naprawić keyw...`
- `testy__test_pesel_warianty.txt` — `...03816. Sprawa sądowa sygn. akt I C 334/2024.\n\n--- SEKCJA 5: [[OCR-SPACJA]] / SPLIT W NUMERZE ---\nNumer rozbity spacją lub znakiem prze...`
- `testy__test_sklejanie_encji_07_07.txt` — `...okrzyska 22/5, 00-050 Warszawa, 8765,43 zł, FV20261234X567, [[sygn. akt III Co 991/2026]], ur. 12.05.1990, Zakład Usługowy Baranowski Sp. z o.o.\n`
- `testy__test_sklejanie_encji_07_07.txt` — `... 8765,43 zł, FV20261234X567, sygn. akt III Co 991/2026, ur. [[12.05.1990]], Zakład Usługowy Baranowski Sp. z o.o.\n`
- `testy__test_telefon_warianty.txt` — `... 67 89\nProszę o kontakt pod numerem telefonu: 501 234 567, [[wew. 22]]\nZadzwoń: tel.22 123 45 67\nNr telefonu 601 234 567\nFaktur...`

### 36. Desktop zakrył, Mobile nie — całość | NUMER | 10 cyfr (NIP?) — 12 wyst., 9 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00021.txt` — `...26\n5.   Wynajem sprzętu biurowego         9    1384  23%    [[12456    15321]]\n----------------------------------------\nŁĄCZNIE DO ZAPŁATY...`
- `clean__doc_00218.txt` — `...1\n2.   Usługa transportowa               6    1577  23%     [[9462    11638\n3]].   Naprawa sprzętu                   7     127   8%      88...`
- `pliki__doc_test_guard.txt` — `...miast myślnika: 855.019.31.23\nNIP z podwójnym separatorem: [[873 -000 -51-39]]\n\n=== HIGH: IBAN ===\nKonto bankowe: PL2711402004000030020...`
- `stress__doc_00025.txt` — `...2\n4.   Usługa transportowa               7    1409   8%     [[9863    10652\n5]].   Wynajem sprzętu biurowego         1     308  23%      30...`
- `stress__doc_00028.txt` — `...08\n4.   Konsultacja techniczna            8    1912  23%    [[15296    18814]]\n----------------------------------------\nŁĄCZNIE DO ZAPŁATY...`
- `ocr__doc_00013.txt` — `... II Cena VAT Netto Brutto\n1. Usluga transportowa 9 1560 23% [[14040 17269]]\n2. Instalacja oprogramowania 8 1175 23% 9400 11562\n3. Konsu...`
- `ocr__doc_00041.txt` — `...uslugi II. Cena VAT Netto Brutto\n1.Obsługa prawna 7 1895 8% [[13265 14326]]\n2. Usługa doradcza 2 1191 8% 2382 2573\n3.Obsluga prawna 6 1...`
- `ocr__doc_00041.txt` — `...ie zawodowe 1 1211 8% 1211 1308\n5.Obsługa prawna 8 1297 23% [[10376 12762]]\nŁACZNIE DO ZAPŁATY: 31714 PLN\nPłatność przelewem: PL4924010...`

### 37. Desktop zakrył, Mobile nie — całość | KWOTA | z walutą — 12 wyst., 5 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl0_umowa_o_prace.txt` — `...nagrodzenie zasadnicze w kwocie 12 500,00 PLN\n   (słownie: [[dwanaście tysięcy pięćset złotych 00/100]]) brutto miesięcznie.\n2. Wynagrodzenie płatne do 10. dnia k...`
- `pliki__doc_lvl2_pismo_komornicze.txt` — `...                      40 701,70 PLN\n  (slowa: czterdziesci [[tysiecy siedemset jeden zlotych 70/100]])\n\nWplate nalezy dokonac w terminie 7 dni od otrzymania ni...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...(s lownie: szescdziesiat trzy tysiac e dwiescie dwadziescia [[dwa zlote 00/100]])\n─────────────────────────────────────────────────────────...`
- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...\nWynagrodzenie: 3 000,00 PLN brutto\n               (slowa: [[trzy tysiace zlotych 00/100]])\n\nPlatnosc na nr rachunku: PL 27 1 160 2202 0000 0001 884...`
- `pliki__doc_stresstest_silnik_guard_lvl0_3.txt` — `...200 6258 0001\n\nKwota do zapłaty: 40 701,70 PLN\n(słownie: [[czterdzieści tysięcy siedemset jeden złotych 70/100]])\n\nSygnatura akt: Km 17224/2021\nData: 29.08.2024\n\nPłatn...`
- `testy__test_anchor_full.txt` — `...t I C 234 /24\n\n=== KWOTA — kotwica zł / PLN / kwota: ===\n[[15 000,00 zł]]\n230 500 PLN\nkwota: 49 999,99 zł\nwartość: 1 250 000,00 zł...`
- `testy__test_anchor_full.txt` — `...\n\n=== KWOTA — kotwica zł / PLN / kwota: ===\n15 000,00 zł\n[[230 500 PLN]]\nkwota: 49 999,99 zł\nwartość: 1 250 000,00 zł\n15 OOO,OO z...`
- `testy__test_anchor_full.txt` — `...ca zł / PLN / kwota: ===\n15 000,00 zł\n230 500 PLN\nkwota: [[49 999,99 zł]]\nwartość: 1 250 000,00 zł\n15 OOO,OO zł\n23O 5OO PLN\nkwota...`

### 38. Mobile zakrył, Desktop nie — całość | NUMER | dokument tożsamości — 12 wyst., 4 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl0_umowa_o_prace.txt` — `...kowie\n- Numer PESEL współmałżonka (do PIT): 89031198765\n- [[Seria i nr paszportu na potrzeby]] delegacji zagranicznych: EB 7654321\n\n        ____________...`
- `testy__test_hard_v2.txt` — `...rak wzorca — oczekiwany miss)\n  REGON: 123456785\n  DOWÓD: [[EFG 456789]]\n\nZNANE LUKI (silnik nie maskuje, guard powinien wykryć RE...`
- `testy__test_hard_v2.txt` — `...Tel: +48 6O6 2I9 T2T\ne-mai1: bartosz.jab1owski@prawnik.p1\n[[Dowód osobisty: EFG 456789]]\nPaszport: AB I234567\n\nZLECENIOBIORCA:\nImię i nazwisko: ...`
- `testy__test_hard_v2.txt` — `...: bartosz.jab1owski@prawnik.p1\nDowód osobisty: EFG 456789\n[[Paszport: AB I234567]]\n\nZLECENIOBIORCA:\nImię i nazwisko: M0nka Nowak0sa\nPESE1 ...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...==========================================================\n\n[[dowód osobisty: ABC 123456]]\nDowód os.: DEF 789012\nD.O. XYZ 345678\nseria i numer: GHI 90...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...====================\n\ndowód osobisty: ABC 123456\nDowód os.: [[DEF 789012]]\nD.O. XYZ 345678\nseria i numer: GHI 901234\n\npaszport: AB1234...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...=========\n\ndowód osobisty: ABC 123456\nDowód os.: DEF 789012\n[[D.O. XYZ 345678]]\nseria i numer: GHI 901234\n\npaszport: AB1234567\nPaszport nr ...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `... osobisty: ABC 123456\nDowód os.: DEF 789012\nD.O. XYZ 345678\n[[seria i numer: GHI 901234]]\n\npaszport: AB1234567\nPaszport nr PA 2345678\n\nPrawo jazdy: P...`

### 39. Mobile zakrył, Desktop nie — całość | ADRES | ulica/numer domu — 11 wyst., 4 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_test_nowe_encje.txt` — `...ie do Kliniki Kardiologii.\nWynik z Centrum Medycznego przy [[ul. Polnej]].\nPrzychodnia Lekarzy Rodzinnych, Wrocław.\nZaświadczenie z...`
- `stress__doc_00127.txt` — `...alej „Zleceniodawcą"\n\na\n\n2. Jeremi Żurek\n   zamieszkałym/ą: [[ul. Rondo nszz]] "solidarność" 189, 30-001 Ostrożeń Drugi\n   NIP: 892-513-27...`
- `testy__test_adresy_50.txt` — `...wa bez kodu\nul. Nowa Huta 5/2\nOCZEKIWANE: 1 ADRES\n\n[B4] [[pl. bez kodu]]\npl. Zamkowy 1\nOCZEKIWANE: 1 ADRES\n\n--- SEKCJA C: KOD + ...`
- `testy__test_adresy_50.txt` — `..., 87-100 Białystok\nOCZEKIWANE: 1 ADRES (lub min. ADRES dla [[ul. Dębowa]])\n\n[E12] kod z O zamiast 0, miasto z literówką\nul. Zielon...`
- `testy__test_adresy_50.txt` — `...tokeny ADRES\n\n[G8] adres bez numeru budynku (sama ulica)\n[[ul. Marszałkowska]], Warszawa\nOCZEKIWANE: może NIE być ADRES (brak numeru) — d...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...===========================\n\n-- Pełny adres --\nZamieszkały: [[ul. Szkolna 150]], 20-100 Kielce\nAdres korespondencyjny: al. Niepodległości 1...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...ały: ul. Szkolna 150, 20-100 Kielce\nAdres korespondencyjny: [[al. Niepodległości 12]], 60-001 Poznań\n\n-- OCR lvl3: adres rozbity newline --\nAdres...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...oznań\n\n-- OCR lvl3: adres rozbity newline --\nAdres dostawy: [[ul. Kazimierza Wielkiego\n14/3]], 50-001 Wrocław\n\n-- Różne prefiksy --\nos. Słoneczne 7/3, 30...`

### 40. Mobile zakrył, Desktop nie — całość | NUMER | nr faktury — 10 wyst., 7 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_test_guard.txt` — `...w treści przepisu)\nFaktura nr 123456789 z dnia 01.01.2024 ([[numer faktury 9]] cyfr = REGON false positive?)\nTelefon infolinii: 801-000-0...`
- `testy__bramka_merge_silnik_14_07.txt` — `...01 Warszawa\n[H5] Faktura VAT nr FV/2026/000088\n[H6] Faktura [[VAT 26/06/006]]\n[H7] Sygn. akt I C 234/2026\n[H8] Nr rachunku: 61 1090 1014 ...`
- `testy__test_faktura_20_warianty_07_07.txt` — `...faktury: FV-01079/04/2024\n\n5) Faktura VAT 26/06/006\n\n6) [[260712/FV]]\n\n7) FV/2026/07/142\n\n8) Nr faktury FV202607/0142\n\n9) F...`
- `testy__test_faktura_20_warianty_07_07.txt` — `...828\n\n16) Faktura VAT NR F.V. 26I06I006\n\n17) FAKTURA VAT [[F-ra 26/06/006]]\n\n18) FAKTURA VAT  FV  26 / 06 / 006\n\n19) FAKTURA VAT Nr...`
- `testy__test_faktura_20_warianty_07_07.txt` — `...6I006\n\n17) FAKTURA VAT F-ra 26/06/006\n\n18) FAKTURA VAT  [[FV  26 / 06 / 006]]\n\n19) FAKTURA VAT Nr FV-O8217/O8/2O23\n\n20) Faktura VAT 2...`
- `testy__test_numer_dokumentu.txt` — `...04/2024 kontrahent NIP 526-021-15-81\n\nNr FV-08217/08/2023 [[Nr U-00284/2023]]\n\nFaktura VAT Nr 8678/02/2023 Umowa nr U-00284/2023 zlecen...`
- `testy__wyniki_testy_reczne.txt` — `...→ NUMER  (numer faktury — FP)\n  I C 234/26        → NUMER  ([[sygnatura akt — FP)]]\n  2026-06-20        → NUMER-20  (data ISO częściowa — FP)\n ...`

### 41. Inny typ (Mobile=ADRES, Desktop=NUMER) | Mobile=ADRES, Desktop=NUMER | kod pocztowy (+miasto) — 10 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_adres_60.txt` — `...\n15-950 Białystok\nBialystok, 15-950\nLodz, 90-001\nKrakow, [[31-610]]\n00-001\n41-200 Byt0m\n4l-2OO Bytom\nOO-OO1 Warszawa\n3l-61...`
- `testy__test_adres_60.txt` — `...Białystok\nBialystok, 15-950\nLodz, 90-001\nKrakow, 31-610\n[[00-001\n41-20]]0 Byt0m\n4l-2OO Bytom\nOO-OO1 Warszawa\n3l-61O Kraków\n00-00...`
- `testy__test_email_adres_hard.txt` — `...niak@wp.pl\nAdres korespondencyjny: al. Niepodległości 13/2, [[65-001 Gliwice]].\n\nOCR wariant (spacja w local-part):\nKontakt e-mail: kamil ...`
- `testy__test_kod_pocztowy_migracja.txt` — `...ana Pawła II 15\n90-001 Łódź PESEL 90051512340\n90051512340 [[90-001 Łódź]]\n00-001 Warszawa80-001 Gdańsk\nPESEL 90051512340 00-001 War...`
- `testy__test_kod_pocztowy_migracja.txt` — `...15\n90-001 Łódź PESEL 90051512340\n90051512340 90-001 Łódź\n[[00-001 Warszawa]]80-001 Gdańsk\nPESEL 90051512340 00-001 Warszawa NIP 526-021...`
- `testy__test_kod_pocztowy_migracja.txt` — `... PESEL 90051512340\n90051512340 90-001 Łódź\n00-001 Warszawa[[80-001 Gdańsk]]\nPESEL 90051512340 00-001 Warszawa NIP 526-021-15-81\n00-00...`

### 42. Desktop zakrył, Mobile nie — całość | ADRES | kod pocztowy (+miasto) — 10 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_adres_60.txt` — `...zne 8, 31-343 Kraków\nul. Długa 7\nul. Długa 7, Gdańsk\nul .[[Długa 7, 80-001 Gdańsk]]\nul,Długa 7, 80-001 Gdańsk\nul. Gdańska-Sopocka 3/1, 81-001...`
- `testy__test_adres_60.txt` — `...25 Warszawa\nul. Polna 5A/12, 00-625 Warszawa\nal. Róż 12A, [[00-556]] Warszawa\n00-001 Warszawa\nWarszawa, 00-001\n80-244 Gdańsk...`
- `testy__test_adres_60.txt` — `...A/12, 00-625 Warszawa\nal. Róż 12A, 00-556 Warszawa\n00-001 [[Warszawa\nWarszawa, 00-001\n80-244 Gdańsk]]\nGdańsk, 80-244\n31-610 Kraków\nKraków, 31-610\n61-001 Pozn...`
- `testy__test_adres_60.txt` — `... Warszawa\nWarszawa, 00-001\n80-244 Gdańsk\nGdańsk, 80-244\n[[31-610 Kraków]]\nKraków, 31-610\n61-001 Poznań\nPoznań, 61-001\n50-001 Wroc...`
- `testy__test_adres_60.txt` — `...-244 Gdańsk\nGdańsk, 80-244\n31-610 Kraków\nKraków, 31-610\n[[61-001 Poznań]]\nPoznań, 61-001\n50-001 Wrocław\nWrocław, 50-001\n90-001 Łó...`
- `testy__test_adres_60.txt` — `...-610 Kraków\nKraków, 31-610\n61-001 Poznań\nPoznań, 61-001\n[[50-001 Wrocław]]\nWrocław, 50-001\n90-001 Łódź\nŁódź, 90-001\n40-001 Katowic...`
- `testy__test_adres_60.txt` — `...01 Poznań\nPoznań, 61-001\n50-001 Wrocław\nWrocław, 50-001\n[[90-001 Łódź]]\nŁódź, 90-001\n40-001 Katowice\nKatowice, 40-001\n70-001 Sz...`
- `testy__test_anchor_full.txt` — `...74\n\n=== ADRES — kotwica ul. / al. / kod pocztowy ===\nul. [[Marszałkowska 15/3, 00-001 Warszawa]]\nal. Grunwaldzka 156, 80-244 Gdańsk\nos. Tysiąclecia 8/12, ...`

### 43. Desktop zakrył, Mobile nie — częściowo (granice) | FIRMA | z formą prawną — 9 wyst., 9 dok.

Hipoteza: Desktop obejmuje całą nazwę instytucji/firmy, Mobile tylko część (miasto lub początek); także osoby wzięte przez Desktop za FIRMA.

- `clean__doc_00135.txt` — `...-------------------------------------\nSPRZEDAWCA:\nGAMMA Sp. [[z o.o. S.K.A]].\nAdres: ul. Dębowa 193, 02-200 Kielce\nNIP: 617-908-64-13   ...` (niezakryte: `S.K.A`)
- `pliki__doc_stresstest_silnik_guard_lvl0_3.txt` — `...═══════════════════════\n\nUMOWA ZLECENIA\n\nZleceniodawca: [[Kancelaria Prawna Nowak & Partnerzy Sp. k]].\n               ul. Jana Kowalskiego 5/2\n               3...` (niezakryte: `Kancelaria Prawna Nowak & Partnerzy Sp. k`)
- `testy__test_reczny_21_06.txt` — `...ienia: 21.06.2024\nTermin płatności: 05.07.2024\n\nSprzedawca:\n[[Przedsiębiorstwo Usług Technicznych "ALTEX" Sp. z o.o]].\nNIP: 7192505885\nNr konta: PL03 3250 0003 6637 2867 4401 41...` (niezakryte: `Przedsiębiorstwo Usług Technicznych`)

### 44. Desktop zakrył, Mobile nie — częściowo (granice) | EMAIL | email — 8 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl2_pismo_komornicze.txt` — `...\nul. Grodzka 65, 31-001 Krakow\ntel. 12 422 19 27\ne-mail: [[komornik.wojciechowski©krakow.pl]]\nNIP 677-204-89 31\n\nKrakow, dnia 3 wrzesnia 2024 r.\n\nKm...` (niezakryte: `krakow`)
- `testy__test_mix_encje.txt` — `... Dudek, ur. 07.09.1974, +48 576 477 050, NIP 108-329-91-94\n[[piotr.dudek45@interia.pl]] PL19102028926340039277573006 Lublin 87-100\nZofia Jankowska...` (niezakryte: `interia`)
- `testy__test_silnik_statystyki.txt` — `...MAIL_xxx\n 4. piotr.zajac@onet.pl               → EMAIL_xxx\n [[5. agnieszka.dabrowska123@gmail.com   → EMAIL_xxx]]\n 6. biuro@firma-consulting.pl          → EMAIL_xxx\n 7. t.wi...` (niezakryte: `EMAIL_xxx`)
- `testy__test_silnik_statystyki.txt` — `...gnieszka.dabrowska123@gmail.com   → EMAIL_xxx\n 6. biuro@firm[[a-consulting.pl          → EMAIL_xxx\n 7]]. t.wierzbicki@firma.pl             → EMAIL_xxx\n 8. l.szyman...` (niezakryte: `EMAIL_xxx`)
- `testy__test_silnik_statystyki.txt` — `...o@firma-consulting.pl          → EMAIL_xxx\n 7. t.wierzbicki@[[firma.pl             → EMAIL_xxx]]\n 8. l.szymanski@prawnik.pl            → EMAIL_xxx\n 9. barto...` (niezakryte: `EMAIL_xxx`)
- `testy__test_silnik_statystyki.txt` — `...t.wierzbicki@firma.pl             → EMAIL_xxx\n 8. l.szymansk[[i@prawnik.pl            → EMAIL_x]]xx\n 9. bartosz.lewandowski@prawnik.pl     → EMAIL_xxx\n10. j....` (niezakryte: `EMAIL_x`)
- `testy__test_silnik_statystyki.txt` — `... 8. l.szymanski@prawnik.pl            → EMAIL_xxx\n 9. bartos[[z.lewandowski@prawnik.pl     → EMAIL_xxx\n10. j]].malinowski@urzad.gov.pl         → EMAIL_xxx\n11. info@gov.pl...` (niezakryte: `EMAIL_xxx`)
- `testy__test_silnik_statystyki.txt` — `...z.lewandowski@prawnik.pl     → EMAIL_xxx\n10. j.malinowski@ur[[zad.gov.pl         → EMAIL_xxx\n11. in]]fo@gov.pl                        → EMAIL_xxx  ← może NIE (og...` (niezakryte: `EMAIL_xxx`)

### 45. Inny typ (Mobile=KWOTA, Desktop=OSOBA) | Mobile=KWOTA, Desktop=OSOBA | z walutą — 7 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...tera (np. "ź" po "Łód") — też problem\n- TOKEN = pełny token [[KWOTA/ADRES/OSOBA/NUMER (OK)\n- Kolory DEBUG: zielony=AddressEngine, niebieski=inne warstwy, czerwony=odkryte ręcznie\n\n================================================================================\nSEKCJA A — KWOTA: suffix "zł" (Structural \b(?:zł|PLN)\b — gałąź zł podatna)\nAnchor A.9 powinien ratować "cyfra + zł"; jeśli nie — jawne PII.\n================================================================================\n\n[A1] Suffix zł po kwocie (klasyczny bug)\nKwota do zapłaty: 1234,56 zł]] brutto\nOCZEKIWANE: TOKEN KWOTA na całość "1234,56 zł" (min....`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...płaty: 1234,56 zł brutto\nOCZEKIWANE: TOKEN KWOTA na całość "[[1234,56 zł]]" (min. bez jawnego "zł")\n\n[A2] Suffix zł bez przecinka\nNale...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...wnego "zł")\n\n[A2] Suffix zł bez przecinka\nNależność główna: [[500 zł]]\nOCZEKIWANE: TOKEN KWOTA, zero jawnego "500 zł"\n\n[A3] Suffix...`
- `testy__test_b_word_boundary_diacritics_08_07.txt` — `...] Suffix zł z OCR liter zamiast zer (Anchor D-class)\nkwota: [[15 OOO,OO zł]]\nOCZEKIWANE: TOKEN KWOTA, zero jawnego "OOO" ani "zł"\n\n[A4] ...`
- `testy__test_email_adres_hard.txt` — `..., 00-001 Warszawa.\nPrzedmiot: laptop Lenovo ThinkPad. Cena: [[2 800,00 PLN]].\n\n=========================================================...`
- `testy__test_nip_warianty.txt` — `...y. Wystawca: Jan Kowal. nip: 521-334-00-01.\nWartość usługi: [[750,00 PLN]] brutto.\n\nOferta handlowa nr OH/2024/88.\nWystawiający: Usług...`

### 46. Mobile zakrył, Desktop nie — częściowo (granice) | EMAIL | email — 7 wyst., 6 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl2_pismo_komornicze.txt` — `...echowski\nul. Grodzka 65, 31-001 Krakow\ntel. 12 422 19 27\n[[e-mail: komornik.wojciechowski]]©krakow.pl\nNIP 677-204-89 31\n\nKrakow, dnia 3 wrzesnia 202...` (niezakryte: `e-mail`)
- `pliki__doc_test_guard.txt` — `...a HIGH naraz ===\nDłużnik: Jan Kowalski, PESEL 85010112345, [[e-mail jan.kowalski@poczta.pl]],\nkonto PL27114020040000300201355387, dowód AYC123456.\n\n=...` (niezakryte: `e-mail`)
- `testy__test_email_adres_hard.txt` — `...pl. Termin realizacji: 30.06.2026.\n\nZapis formalny wniosku: [[adres poczty elektronicznej piotr_dudek45@interia.pl]],\nzamieszkały ul. Wolności 99, 41-200 Sosnowiec.\n\n--- SEKCJA...` (niezakryte: `adres poczty`)
- `testy__test_email_adres_hard.txt` — `...rahenta (tabelaryczne):\nMichalski Kamil | al.Niepodleglosci [[13/2 | 65-001 Gliwice | kamil.wozniak@wp.pl]]\n\nFormularz uproszczony — bez przecinków:\nadres: ul Dębowa 1...` (niezakryte: `13/2`)
- `testy__test_email_kropka_spacja_07_07.txt` — `...E Adres zamieszkania: ul. Lesna 64, 50-001 Gdansk Telefon: +[[48 481 865 133 Adres e-nnail kamil. woziak@wppl DANE]] PODATKOWE NIP jesli dotyczy): 519-317-\n` (niezakryte: `Adres e`)
- `testy__test_lvl3_dane_wrazliwe.txt` — `...- OCR lvl3: spacja w local-part (pułapka) --\nKontakt email: [[lszyman ski@interia.pl]]\nE-mail: m.wisniew ska@gmail.com\n\n-- OCR lvl3: spacja przed ...` (niezakryte: `lszyman`)
- `testy__test_mix_encje.txt` — `... Sylwia Kamińska PESEL 59072662418 ul. Kwiatowa 189 Lublin\n[[NIP 108-329-91-94 600 123 456 jan.nowak@firma.pl]] kwota 54 131 zł\nJustyna Kowalczyk date of birth 03.11.1988...` (niezakryte: `108-329-91`)

### 47. Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | nr faktury — 7 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_faktura_20_warianty_07_07.txt` — `...Nr FVI2025/12/1828\n\n12) FV20260700W012\n\n13) FAKTURA VAT [[FV KOR12.012.00012]]\n\n14) Faktura VAT FV 26/06/006/WAW\n\n15) FAKTURA VAT Nr F...` (niezakryte: `012.00012`)
- `testy__test_faktura_20_warianty_07_07.txt` — `...2\n\n14) Faktura VAT FV 26/06/006/WAW\n\n15) FAKTURA VAT Nr [[FVI2O25/12/1828]]\n\n16) Faktura VAT NR F.V. 26I06I006\n\n17) FAKTURA VAT F-r...` (niezakryte: `12/1828`)
- `testy__test_pesel_warianty.txt` — `...łożono w Wydziale Spraw Obywatelskich UM Szczecin.\n\nFaktura [[VAT 2024/03/0190]].\nNabywca: Agnieszka Duda, PESEL: 85032 204563, NIP: 678-901...` (niezakryte: `03/0190`)
- `testy__test_stress_pawel_08_07_pdf.txt` — `...4,\n\n PLN 1234\n\nPL08102028929730064553240202\n\nFAKTURA VAT Nr [[FV12025/12/1828]]\n\nFaktura VAT 26/06/006\n\nFV 91/07/26/VAT\n\nFS 00145/26\n\nFV 12...` (niezakryte: `12/1828`)
- `testy__test_stress_pawel_08_07_pdf.txt` — `...Nr FV12025/12/1828\n\nFaktura VAT 26/06/006\n\nFV 91/07/26/VAT\n\n[[FS 00145/26]]\n\nFV 12/06/2026/WAW\n\nFV KOR12.012.00012\n\nFV-145-97-2026\n\nFV2...` (niezakryte: `26`)
- `testy__test_stress_pawel_08_07_pdf.txt` — `... VAT 26/06/006\n\nFV 91/07/26/VAT\n\nFS 00145/26\n\nFV 12/06/2026/[[WAW\n\nFV KOR12.012.000]]12\n\nFV-145-97-2026\n\nFV202607000Q2\n\n260712/FV\n\nFV12/07/2026/D...` (niezakryte: `012.000`)
- `testy__test_stress_pawel_08_07_pdf.txt` — `.../07/26/VAT\n\nFS 00145/26\n\nFV 12/06/2026/WAW\n\nFV KOR12.012.000[[12\n\nFV-145-97-2]]026\n\nFV202607000Q2\n\n260712/FV\n\nFV12/07/2026/DET/WAW\n\nFaktura...` (niezakryte: `12`)

### 48. Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | telefon — 6 wyst., 5 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_degradacje_lvl.txt` — `... PL89109010147449555252110732\n  TELEFON:  +48 601 234 567, ([[32) 456-78-90]]\n  EMAIL:    krzysztof.nowicki@firma.pl, b.kaminska@onet.pl\n...` (niezakryte: `32`)
- `testy__test_email_adres_hard.txt` — `...277\n2. Anna Wiśniewska, ul. Dębowa 19/23, 87-100 Białystok, [[tel. 506 111 222\n3]]. Tomasz Górski, ul. Długa 72, 70-001 Rybnik, e-mail: t.gors...` (niezakryte: `3`)
- `testy__test_lvl3_dane_wrazliwe.txt` — `...606 219 727, +48 512 345 678, 81 123-45-67,\n               ([[22) 765-43-21]], 12 456 78 90\nADRES (6):     ul. Szkolna 150 / 20-100 Kielc...` (niezakryte: `22`)
- `testy__test_silnik_statystyki.txt` — `...owodu os.:       DEF 789012\nData urodzenia:      12.03.1978\n[[Telefon:             (22) 765-43-21]]\nE-mail:              piotr.zajac@onet.pl\nAdres zamieszkania...` (niezakryte: `22`)

### 49. Inny typ (Mobile=EMAIL, Desktop=NUMER) | Mobile=EMAIL, Desktop=NUMER | email — 6 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_degradacje_lvl.txt` — `...ly u. Llp0wa 22, 4l-200 Byt0m, tel: 48 60l 234 567,\ne-mail: [[krzyszt0f. n0wicki@flrma.pl]], dow0d 0sobisty: EFG 456789.\n\nZleceniobiorca: Be4ta Kamlnsk...`
- `testy__test_email_adres_hard.txt` — `...liwice.\n\nOCR wariant (spacja w local-part):\nKontakt e-mail: [[kamil wozniak@wp.pl]], tel. 601 234 567.\n\nOCR wariant (brak kropki między nazwą a...`
- `testy__test_email_adres_hard.txt` — `...k@wp.pl, tel. 601 234 567.\n\nOCR wariant (brak kropki między [[nazwą a]] @ → sklejenie):\ne-mail kamil.wozniak@wp pl (spacja przed TL...`
- `testy__test_email_adres_hard.txt` — `...7.\n\nOCR wariant (brak kropki między nazwą a @ → sklejenie):\n[[e-mail kamil.wozniak@wp pl]] (spacja przed TLD)\n\n=======================================...`
- `testy__test_ocr_normalizer_hard.txt` — `...podleg1ości I35, 2O-1OO Rybnik\nTel: +48 6O6 2I9 T2T\ne-mai1: [[bartosz.jab1owski@prawnik.p1]]\n\nZLECENIOBIORCA:\nImię i nazwisko: Monka Nowakosa\nPESE1 pacj...`
- `testy__test_ocr_normalizer_hard.txt` — `...enta: 8OOI23I2345\nNlP: 83I-I4S-84-O9\nAdres: u Kopernka I2O, [[3I-OOI Katowce\nNr konta: PLO4 325O OOOJ 5633 9S6O T883 I852\ne-mail: monka nowakowska@wp p1]]\n\nDANE PODATKOWE:\nNIP sprzedawcy: I42-I99-O6-38\nNIP nabywcy:...`

### 50. Inny typ (Mobile=NUMER, Desktop=OSOBA) | Mobile=NUMER, Desktop=OSOBA | PESEL — 6 wyst., 1 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_pesel_warianty.txt` — `...y: Korekta zeznania rocznego.\nDane podatnika: Jan Kowalski, [[PESEL: 73051649957]], ul. Długa 12, Kraków.\nProszę o przyjęcie korekty formularz...`
- `testy__test_pesel_warianty.txt` — `...nie do zapłaty nr WZ/2024/0084.\nDłużnik: Tomasz Malinowski, [[PESEL 66111503816]], ul. Leśna 7, Poznań.\nKwota zaległości: 4 320,00 PLN. Termi...`
- `testy__test_pesel_warianty.txt` — `...ziła: insp. Barbara Kowalczyk.\nZgłaszający: Ryszard Wiktor, [[pesel: 85032204563, t]]el. 604 123 456.\nTreść zgłoszenia: hałas w godzinach nocnych...`
- `testy__test_pesel_warianty.txt` — `...poważnionych pracowników działu kadr.\n\n--- SEKCJA 10: PESEL [[SKLEJONY Z KONTEKSTEM (OCR ARTIFACT) ---\nSilnik powinien wyciąć numer mimo braku separatora.\n\nAkta sprawy sądowej.\nDaneosobyJan KowalskiPESEL73051649957]]zamieszkałyWarszawa.\n(sklejony tekst OCR — silnik powinien w...`
- `testy__test_pesel_warianty.txt` — `...tej samej sprawie jako świadkowie wystąpili:\n1. Hanna Sowa, [[PESEL: 85032204563]], ul. Ogrodowa 2, Lublin,\n2. Zbigniew Sowa, PESEL: 661115038...`
- `testy__test_pesel_warianty.txt` — `...Sowa, PESEL: 85032204563, ul. Ogrodowa 2, Lublin,\n2. Zbignie[[w Sowa, PESEL: 661115038]]16, ul. Ogrodowa 2, Lublin.\n\n--- SEKCJA 12: PESEL Z RÓŻNYMI ...`

### 51. Desktop zakrył, Mobile nie — częściowo (granice) | ADRES | kod pocztowy (+miasto) — 5 wyst., 4 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `stress__doc_00131.txt` — `...0101357600490824043350\n\nNABYWCA:\nFreya Kolodziej\nAdres: ul. [[Rondo im. marszałka józefa piłsudskiego 180, 03-300 Zarębin]]\nNIP: 855-855-66-57\n\n---------------------------------------...` (niezakryte: `marszałka józefa piłsudskiego 180`)
- `stress__doc_00280.txt` — `... K 3454/2023\nŁążki, dnia 22.01.2025\n\n\nMalena Steglińska\nul. [[Rondo im. jana pawła ii 71/11\n44-100 Kulesze Podlipne]]\n\n\nWEZWANIE DO ZŁOŻENIA WYJAŚNIEŃ\n\nDziałając na podstawie ar...` (niezakryte: `jana pawła ii`)
- `testy__test_adresy_50.txt` — `...] ul. → u (bez kropki) + skrócona nazwa (z bugs doc_00050)\n[[u Kiatowa 189, 87-100 Lubin]]\nOCZEKIWANE: prawdopodobnie BRAK (sufit OCR) — dokumentować...` (niezakryte: `u`)
- `testy__test_kod_pocztowy_migracja.txt` — `...0 zł\nKowalski Sp. z o.o. 00-001 Warszawa\n00-001 Warszawa K[[owalski Sp. z o.o.\nur. 12.03.1985 00-001 Warszawa\n00-001 War]]szawa ur. 12.03.1985\n70-001 Szczecin80-001 Gdańsk31-610 Kra...` (niezakryte: `ur`)
- `testy__test_kod_pocztowy_migracja.txt` — `...alski Sp. z o.o.\nur. 12.03.1985 00-001 Warszawa\n00-001 War[[szawa ur. 12.03.1985\n70-001 Szczecin80-001 Gdańsk31-610 Kraków]]\nKW GD1M/00234567/8 00-001 Warszawa\n00-001 Warszawa KW GD1...` (niezakryte: `ur`)

### 52. Desktop zakrył, Mobile nie — całość | NUMER | IBAN/rachunek — 5 wyst., 1 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_anchor_full.txt` — `...\ntel.22 123 45 67\n\n=== PESEL — kształt z tolerancją ===\n[[90040512345\n75121867890\n03281512367\n9OO4O512345\n751218678O0\nO328l512367\n9004051234S\n7S121867890\n90040 512345]]\n75121-867890\n\n=== NIP — kształt z tolerancją ===\n526-02...`
- `testy__test_anchor_full.txt` — `...512345\n75121-867890\n\n=== NIP — kształt z tolerancją ===\n[[526-021-15-81\n722-30-32-34\n5260211581\n526-O21-15-81\n722-3O-32-34\nS260211581\n526 021 15 81]]\n726-3O-B2-34\n\n=== IBAN — kotwica PL ===\nPL61 1090 1014 ...`
- `testy__test_anchor_full.txt` — `...\n526 021 15 81\n726-3O-B2-34\n\n=== IBAN — kotwica PL ===\n[[PL61 1090 1014 0000 0712 1981 2874]]\nPL27 1140 2004 0000 3102 0135 5387\nPL61 1O9O 1O14 OOOO O7...`
- `testy__test_anchor_full.txt` — `... IBAN — kotwica PL ===\nPL61 1090 1014 0000 0712 1981 2874\n[[PL27 1140 2004 0000 3102 0135 5387]]\nPL61 1O9O 1O14 OOOO O712 1981 2874\nPL27 114O 2OO4 OOOO 31...`

### 53. Inny typ (Mobile=NUMER, Desktop=OSOBA) | Mobile=NUMER, Desktop=OSOBA | nr dokumentu/sygnatura/z literami — 5 wyst., 4 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_degradacje_lvl.txt` — `... (32) 456-78 90, e-mall: b .kamlnska@0net.pl.\n\nKont0: IBAN: [[PL89l090l0l474495552 52ll0732]].\n\n\n========================================================...`
- `testy__test_nip_warianty.txt` — `...-01.\nWartość usługi: 750,00 PLN brutto.\n\nOferta handlowa nr [[OH/2024/88]].\nWystawiający: Usługi IT sp. z o.o., NIP 415-112-22-69.\nTer...`
- `testy__test_pesel_warianty.txt` — `...n zamaskować.\n\nWyciąg z rejestru. Osoba: Jadwiga Włodarska.\n[[PE5EL: 73051649957]]. Adres: ul. Piękna 18, Łódź.\n\nZaświadczenie o zatrudnieniu....`
- `testy__test_pesel_warianty.txt` — `...\nZaświadczenie o zatrudnieniu.\nPracownik: Sławomir Górecki, [[PESE1: 55091961277]].\nZatrudniony od: 01.09.2018 r., stanowisko: specjalista.\n\nD...`
- `testy__test_ui2_encje_silnik.txt` — `...===========================================================\n[[PLIK TESTOWY — UI-2 + encje silnika\nData: 2026-06-22]]\nCel: smoke test panelu wyniku (UI-2) ORAZ podstawowe typy e...`

### 54. Mobile zakrył, Desktop nie — całość | NUMER | NIP — 5 wyst., 4 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_hard_v2.txt` — `...nowakowska@onet.pl\nTel: (32) 456-78-9O\n\nDANE PODATKOWE:\n[[NIP sprzedawcy: 5l2-34-56-786]]\nNIP nabywcy: 45I-OS2-35-26\nREGON: I23456785\nIBAN: PL89 1...`
- `testy__test_hard_v2.txt` — `...56-78-9O\n\nDANE PODATKOWE:\nNIP sprzedawcy: 5l2-34-56-786\n[[NIP nabywcy: 45I-OS2-35-26]]\nREGON: I23456785\nIBAN: PL89 1090 10l4 7449 5552 52llO732...`
- `testy__test_nip_warianty.txt` — `... cały fragment "NIP: XXX-XX-XX-XXX" zamaskowany → NUMER-001\n[[BUG-NIP-CTX-3223]]: wcześniej "NIP:" zostawało w tekście, same cyfry były mask...`
- `testy__test_pesel_obca_litera_07_07.txt` — `...0 794 zamieszkalej Szkolna 67, 85-001 Krakow.\n\nKontrahent [[NIP: 426-1A1-78-03]] zarejestrowany w Radomiu.\n`
- `testy__test_ui2_encje_silnik.txt` — `...=====\n\n[NIP 3-2-2-3] 526-000-13-29 — pełny NIP wierzyciela ([[BUG-NIP-CTX]] historyczny)\n[NIP błędna suma] 526-000-13-20 — silnik może ...`

### 55. Inny typ (Mobile=ADRES, Desktop=NUMER) | Mobile=ADRES, Desktop=NUMER | inny adres — 5 wyst., 1 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_ocr_normalizer_hard.txt` — `UMOWA ZLECENIA nr [[UZ/2O26/OO42\nzawarta dnia I8 czerwca 2O26 r. w Kielcach]]\n\nZLECENIODAWCA:\nImię i nazwisko: Bartosz Jab1oński\nPESE1: T...`
- `testy__test_ocr_normalizer_hard.txt` — `...ab1oński\nPESE1: T2O3O3T5656\nNlP: 526-O3O-O1-34\nAdres: u. Nie[[podleg1ości I35, 2O-1OO]] Rybnik\nTel: +48 6O6 2I9 T2T\ne-mai1: bartosz.jab1owski@prawn...`
- `testy__test_ocr_normalizer_hard.txt` — `...D OSOBISTY: FOH6 I4892\nPaszport: AB I234567\n\nAdres dostawy:\n[[u1. S1oneczna I9]]\n85-OOI Sosnowec\n\nAdres korespondencyjny:\na1. Nepodleg1ości ...`
- `testy__test_ocr_normalizer_hard.txt` — `...I4892\nPaszport: AB I234567\n\nAdres dostawy:\nu1. S1oneczna I9\n[[85-OOI Sosnowec]]\n\nAdres korespondencyjny:\na1. Nepodleg1ości 95, OO-OOI Bytom...`
- `testy__test_ocr_normalizer_hard.txt` — `...:\nu1. S1oneczna I9\n85-OOI Sosnowec\n\nAdres korespondencyjny:\n[[a1. Nepodleg1o]]ści 95, OO-OOI Bytom\n\nORZEKAM:\nNa podstawie art. IO4 ustawy ...`

### 56. Desktop zakrył, Mobile nie — całość | NUMER | inna liczba — 5 wyst., 5 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00048.txt` — `...2\n4.   Wynajem sprzętu biurowego         9     643  23%     [[5787     7118]]\n----------------------------------------\nŁĄCZNIE DO ZAPŁATY...`
- `clean__doc_00158.txt` — `...5\n3.   Wynajem sprzętu biurowego        10     143   8%     [[1430     1544]]\n----------------------------------------\nŁĄCZNIE DO ZAPŁATY...`
- `stress__doc_00050.txt` — `...4\n4.   Szkolenie zawodowe                8     255   8%     [[2040     2203]]\n----------------------------------------\nŁĄCZNIE DO ZAPŁATY...`
- `ocr__doc_00033.txt` — `...ortowa 1 1104 23% 1104 1358\n2. Szkolenie zawodowe 5 548 23% [[2740 3370]]\nŁACZNIE DO ZAPŁATY: 4728 PLN\nPłatność przelewem: PL62102028...`
- `testy__test_pesel_warianty.txt` — `...a zgodę na przetwarzanie danych.\nPełnomocnik (nr PESEL 90010[[155382]]) działa w imieniu mocodawcy.\n\n--- KONIEC DOKUMENTU TESTOWEG...`

### 57. Inny typ (Mobile=EMAIL, Desktop=FIRMA) | Mobile=EMAIL, Desktop=FIRMA | bez formy prawnej — 5 wyst., 1 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_silnik_statystyki.txt` — `...AIL_xxx\n 5. agnieszka.dabrowska123@gmail.com   → EMAIL_xxx\n [[6. biuro@firm]]a-consulting.pl          → EMAIL_xxx\n 7. t.wierzbicki@firma....`
- `testy__test_silnik_statystyki.txt` — `..._xxx\n 6. biuro@firma-consulting.pl          → EMAIL_xxx\n 7. [[t.wierzbicki@]]firma.pl             → EMAIL_xxx\n 8. l.szymanski@prawnik.pl ...`
- `testy__test_silnik_statystyki.txt` — `...MAIL_xxx\n 7. t.wierzbicki@firma.pl             → EMAIL_xxx\n [[8. l.szymansk]]i@prawnik.pl            → EMAIL_xxx\n 9. bartosz.lewandowski@...`
- `testy__test_silnik_statystyki.txt` — `...xx\n 9. bartosz.lewandowski@prawnik.pl     → EMAIL_xxx\n10. j.[[malinowski@ur]]zad.gov.pl         → EMAIL_xxx\n11. info@gov.pl              ...`
- `testy__test_silnik_statystyki.txt` — `...xxx\n10. j.malinowski@urzad.gov.pl         → EMAIL_xxx\n11. in[[fo@gov.pl]]                        → EMAIL_xxx  ← może NIE (ogólny)\n\n--...`

### 58. Inny typ (Mobile=KWOTA, Desktop=NUMER) | Mobile=KWOTA, Desktop=NUMER | z walutą — 4 wyst., 4 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__bramka_merge_silnik_14_07.txt` — `...PLN, ul. Kamienna 5, 00-950 Warszawa\n[G2] Kwota do zapłaty: [[PLN 1234]]\n[G3] Wartość netto: 15 000,00 zł. Wartość brutto: 18 450,00...`
- `testy__test_kod_pocztowy_migracja.txt` — `...4 567\nkwota 1500 zł 00-001 Warszawa\n00-001 Warszawa kwota [[1500 zł]]\nKowalski Sp. z o.o. 00-001 Warszawa\n00-001 Warszawa Kowal...`

### 59. Inny typ (Mobile=ADRES, Desktop=OSOBA) | Mobile=ADRES, Desktop=OSOBA | 2+ wyrazów — 4 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_adresy_50.txt` — `...0 Lublin\nOCZEKIWANE: 1 ADRES\n\n[D3] po "NABYWCA"\nNABYWCA [[Łukasz Nowak]], ul. Dębowa 19/23, 87-100 Białystok\nOCZEKIWANE: ADRES dla ...`
- `testy__test_email_adres_hard.txt` — `...ia wspólnoty mieszkaniowej z dnia 10.06.2026.\nObecni: Kamil [[Michalski (al. Niepodległości 1]]3/2), Zofia Dąbrowska (al. Niepodległości 14),\nRyszard Kowal...`
- `testy__test_email_adres_hard.txt` — `...i: Kamil Michalski (al. Niepodległości 13/2), Zofia Dąbrowsk[[a (al. Niepodl]]egłości 14),\nRyszard Kowal (al. Niepodległości 15/3). Nieobe...`
- `testy__test_reczny_21_06.txt` — `...PL03 325O 0003 6637 2867 44O1 4154\nDluzn: P4na Agat3 K0walcz[[yk ul Kopernik]] 19 00001 Rad\n\nWierz: Sp. z o.o. ZUS-Warsz NIP 525OO5885O\n\n-...`

### 60. Desktop zakrył, Mobile nie — całość | FIRMA | z formą prawną — 4 wyst., 3 dok.

Hipoteza: Desktop maskuje jako FIRMA nazwy bez formy prawnej (sądy i komornicy: „SR Warszawa-Mokotów”, „Sąd Rejonowy”, kancelarie z „S.C”); Mobile wymaga formy prawnej (Sp. z o.o., S.A.). Możliwe nadmaskowanie Desktop.

- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...:                              Nabywca:\nMEDITECH SOLUTIONS [[SP Z O.O              Szpital Specjalistyczny im]].\nNIP: 7 12-304-56 78                      Sw. Lukasza w Ta...`
- `testy__test_anchor_full.txt` — `...4 Gdańsk\n3l-61O Kraków\n\n=== ORGANIZACJA — kotwica S.A. / [[Sp. z o.o. ===\nKo]]walski i Partnerzy Sp. z o.o.\nPrzedsiębiorstwo Budowlane No...`
- `testy__test_anchor_full.txt` — `...ORGANIZACJA — kotwica S.A. / Sp. z o.o. ===\nKowalski i Part[[nerzy Sp. z o.o.\nPrze]]dsiębiorstwo Budowlane Nowak S.A.\nKancelaria Adwokacka Wiśn...`
- `testy__test_ui2_encje_silnik.txt` — `... 20-100 Kielce; os. Słoneczne 7/3, 30-001 Kraków\n  FIRMA:   [[Przedsiębiorstwo „ALTEX” Sp. z o.o]]. (jeśli wykryte)\n  KWOTA:   12 500,00 PLN (jeśli wykryte)\n\n...`

### 61. Desktop zakrył, Mobile nie — całość | NUMER | data — 4 wyst., 1 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_anchor_full.txt` — `... Nowak S.A.\n\n=== DATA urodzenia — kotwica ur. / dob: ===\n[[ur. 12.03.1985]]\nur. 5.11.1972\ndob: 1990-07-22\ndata urodzenia: 8 kwietnia...`
- `testy__test_anchor_full.txt` — `...== DATA urodzenia — kotwica ur. / dob: ===\nur. 12.03.1985\n[[ur. 5.11.1972]]\ndob: 1990-07-22\ndata urodzenia: 8 kwietnia 1963\nur. l2.O...`

### 62. Inny typ (Mobile=NUMER, Desktop=OSOBA) | Mobile=NUMER, Desktop=OSOBA | telefon — 4 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_degradacje_lvl.txt` — `...\n\nZleceniobiorca: Be4ta Kamlnska, PE5EL: 7408l934 521, NlP: [[678-90l-23-45,\ntel]]: (32) 456-78 90, e-mall: b .kamlnska@0net.pl.\n\nKont0: IBAN:...`
- `testy__test_degradacje_lvl.txt` — `...ta Kamlnska, PE5EL: 7408l934 521, NlP: 678-90l-23-45,\ntel: ([[32) 456-78 90]], e-mall: b .kamlnska@0net.pl.\n\nKont0: IBAN: PL89l090l0l4744...`
- `testy__test_pesel_warianty.txt` — `...łyWarszawa.\n(sklejony tekst OCR — silnik powinien wychwycić [[73051649957]])\n\nWydruk z systemu ewidencji:\nNazwiskoNowakImieAnna55091961...`
- `testy__test_pesel_warianty.txt` — `...EL bez keywordu — S5 decyduje)\n\nFormularz uproszczony:\nPESEL[[90010155382]]DataUrodzenia19900101PlecMeski.\n\n--- SEKCJA 11: WIELE PESEL ...`

### 63. Mobile zakrył, Desktop nie — całość | NUMER | IBAN/rachunek — 4 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_lvl3_dane_wrazliwe.txt` — `...==\n\n-- IBAN ze spacjami (powinien być wykryty) --\nNr konta: [[PL 36 1020 2892 0020 0886 2353 5888]]\n\n-- IBAN bez spacji (BUG-IBAN-NOSPACES — może nie być wykry...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `... spacji (BUG-IBAN-NOSPACES — może nie być wykryty) --\nIBAN: [[PL62102028920020886235358884]]\n\n-- Z kontekstem --\nIBAN: PL 61 1090 1014 0000 0712 1981 28...`
- `testy__test_lvl3_dane_wrazliwe.txt` — `...BAN: PL62102028920020886235358884\n\n-- Z kontekstem --\nIBAN: [[PL 61 1090 1014 0000 0712 1981 2874]]\n\n==========================================================...`
- `testy__test_sklejanie_encji_07_07.txt` — `...aranowski, PESEL 90051212387, NIP 987-654-32-10, tel. 511222[[333, PL91109010140000071219812875, z]].baranowski@poczta-firmowa.pl, ul. Świętokrzyska 22/5, 00-05...`

### 64. Inny typ (Mobile=EMAIL, Desktop=FIRMA) | Mobile=EMAIL, Desktop=FIRMA | email — 4 wyst., 1 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_silnik_statystyki.txt` — `...AIL_xxx\n 6. biuro@firma-consulting.pl          → EMAIL_xxx\n [[7. t.wierzbicki@firma.pl]]             → EMAIL_xxx\n 8. l.szymanski@prawnik.pl         ...`
- `testy__test_silnik_statystyki.txt` — `...MAIL_xxx\n 7. t.wierzbicki@firma.pl             → EMAIL_xxx\n [[8. l.szymanski@prawnik.pl]]            → EMAIL_xxx\n 9. bartosz.lewandowski@prawnik.pl  ...`
- `testy__test_silnik_statystyki.txt` — `...MAIL_xxx\n 9. bartosz.lewandowski@prawnik.pl     → EMAIL_xxx\n[[10. j.malinowski@urzad.gov.pl]]         → EMAIL_xxx\n11. info@gov.pl                        ...`
- `testy__test_silnik_statystyki.txt` — `...EMAIL_xxx\n10. j.malinowski@urzad.gov.pl         → EMAIL_xxx\n[[11. info@gov.pl]]                        → EMAIL_xxx  ← może NIE (ogólny)\n\n--...`

### 65. Desktop zakrył, Mobile nie — częściowo (granice) | NUMER | sygnatura sprawy — 4 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `ocr__doc_00032.txt` — `Starostwo Powiatowe w Radomiu\n[[Sygn. akt 1 Ns 5551/2025]]    Bytom, dnia 17.03.2023\nZbigniew Wieczorek\nul. Piaskowa 1...` (niezakryte: `1`)
- `testy__test_ui2_encje_silnik.txt` — `...wne.\n3. YELLOW: PESEL 12345678901, ur. 17.07.1985, sygn. nr [[1204/EI/2024]],\n   flagi „Pełnomocnik… Oskar Zepelin”, „Inspektor… Ewa Cel...` (niezakryte: `1204`)

### 66. Inny typ (Mobile=ADRES, Desktop=NUMER) | Mobile=ADRES, Desktop=NUMER | miejscowość (1 wyraz) — 3 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl0_umowa_o_prace.txt` — `...działu kadr:\n- Data urodzenia Pracownika: ur. 23.05.1991 w [[Krakowie]]\n- Numer PESEL współmałżonka (do PIT): 89031198765\n- Seria...`

### 67. Desktop zakrył, Mobile nie — częściowo (granice) | OSOBA | 1 wyraz — 3 wyst., 2 dok.

Hipoteza: Mobile maskuje tylko jedno słowo z „Imię Nazwisko” (zwykle imię), a nazwisko — rzadkie lub obce — zostaje; Desktop maskuje całość. Mobile: brak reguły „Imię + Słowo z wielkiej litery” poza słownikiem nazwisk. W 0% przypadków niezakryty fragment zawiera ostatni wyraz (nazwisko).

- `pliki__doc_lvl1_decyzja_administracyjna.txt` — `...iesiacach),\nnastepnie: 1 173,80 PLN brutto miesiecznie.\n\n[[Zasilek]] bedzie wyplacany przelewem na rachunek bankowy:\nPL 43 1090...` (niezakryte: `Zasi`)
- `testy__bramka_merge_silnik_14_07.txt` — `...rzygotuje Kasia.\n[B4] Nie widziałem Kasi w biurze.\n[B5] Pan [[Marek]] przyszedł na spotkanie. Pani Halina złożyła wniosek.\n\n=====...` (niezakryte: `k`)
- `testy__bramka_merge_silnik_14_07.txt` — `... Kasi w biurze.\n[B5] Pan Marek przyszedł na spotkanie. Pani [[Halina]] złożyła wniosek.\n\n=========================================...` (niezakryte: `a`)

### 68. Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | nr dokumentu/sygnatura/z literami — 3 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl3_faktura_zlecenie.txt` — `... 1    szt.  42 000,00  42 000,00\n     MEDITECH PRO X3 (SN: [[MP2024-0847]])\n2.   Instalacja i konfiguracja          8    godz.    350...` (niezakryte: `0847`)
- `testy__test_email_adres_hard.txt` — `...=================================\n\nProtokół odbioru prac nr [[PO/2026/0019]].\nZamawiający: Justyna Dudek, e-mail: justyna.dudek@gmail.co...` (niezakryte: `0019`)
- `testy__test_pesel_warianty.txt` — `...silnik maskuje / nie maskuje poprawnie.\nUżyte prawidłowe PES[[ELe (S5 OK): 73051649957, 55091961277]],\n  90010155382, 85032204563, 66111503816\nBłędny PESEL (zły ...` (niezakryte: `S5`)

### 69. Inny typ (Mobile=OSOBA, Desktop=ADRES) | Mobile=OSOBA, Desktop=ADRES | 2+ wyrazów — 3 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_email_adres_hard.txt` — `...06.2026.\nObecni: Kamil Michalski (al. Niepodległości 13/2), [[Zofia Dąbrowska]] (al. Niepodległości 14),\nRyszard Kowal (al. Niepodległości ...`
- `testy__test_email_adres_hard.txt` — `...podległości 13/2), Zofia Dąbrowska (al. Niepodległości 14),\n[[Ryszard Kowal]] (al. Niepodległości 15/3). Nieobecni: Jan Kowalski.\nUchwała...`
- `testy__test_ui2_encje_silnik.txt` — `...EL 85071792056, NIP 521-334-00-01,\nzamieszkałym ul. Szkolna [[150, 20-100 Kielce]], tel. 512 345 678,\ne-mail jan.kowalski@wp.pl, a Moniką Wiśn...`

### 70. Desktop zakrył, Mobile nie — częściowo (granice) | NUMER | nr faktury — 3 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_faktura_20_warianty_07_07.txt` — `...==========================================================\n[[TEST NUMER FAKTURY — 20 WARIANTÓW (CZYSTE + IMITACJA OCR)\nCel: zamknięcie sesji 07.07 (FV/VAT jako kotwica w AnchorEngine).\nKażda linia to osobny przypadek — sprawdź w Podglądzie tekstu czy\nCAŁY numer faktury zniknął (token NUMER_xxx), bez jawnej resztki.\nPunkt 10 jest KONTROLNY — "23%" to stawka VAT, NIE numer faktury,\nMUSI zostać widoczne w tekście (nie powinno się zamaskować).\n=============================================================\n\n--- SEKCJA 1: ZAPISY CZYSTE (bez degradacji OCR) ---\n\n1) Faktura VAT nr FV/2026/07/0142]]\n\n2) FAKTURA VAT Nr FV-08217/08/2023\n\n3) Faktura nr 4704...` (niezakryte: `10 jest KONTROLNY — "23%" to stawka VAT, NIE numer faktury,\nMUSI zostać widocz`)
- `testy__test_faktura_20_warianty_07_07.txt` — `...9/04/2024\n\n5) Faktura VAT 26/06/006\n\n6) 260712/FV\n\n7) [[FV/2026/07/142\n\n8) Nr faktury FV202607/0142\n\n9) Faktura VAT FV20260700142\n\n10) Faktura VAT 23%\n\n--- SEKCJA 2: IMITACJA DEGRADACJI OCR ---\n\n11) FAKTURA VAT Nr FVI2025/12/1828\n\n12) FV20260700W012\n\n13) FAKTURA VAT FV KOR12]].012.00012\n\n14) Faktura VAT FV 26/06/006/WAW\n\n15) FAKTUR...` (niezakryte: `8) Nr faktury FV202607/0142\n\n9) Faktura VAT FV20260700142\n\n10) Faktura V`)
- `testy__test_nip_warianty.txt` — `...ksem PL zamaskowany.\n\nFaktura unijna. Numer VAT sprzedawcy: [[PL5213340001]].\nUsługa świadczona na terenie UE. Data wystawienia: 28.02.2...` (niezakryte: `PL`)

### 71. Mobile zakrył, Desktop nie — całość | FIRMA | z formą prawną — 3 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_stresstest_silnik_guard_lvl0_3.txt` — `...sc przelewem:\nPL 98 1 053 1 875 0000 0023 4567 8901\nBank: [[ING Bank Slaski S.A]].\n\n───────────────────────────────────────────────────────...`
- `testy__test_firma_miasto_jako_osoba_09_07.txt` — `...zawa. Nabywca: Jan Kowalski, PESEL 82030112345.\n\nWykonawca: [[Doradztwo Biznesowe EXPERT Sp. z o.o]]. z siedzibą w Krakowie, NIP 526-000-12-46.\n\nPrzedsiębiorstw...`
- `testy__test_sklejanie_encji_07_07.txt` — `... FV20261234X567, sygn. akt III Co 991/2026, ur. 12.05.1990, [[Zakład Usługowy Baranowski Sp. z o.o]].\n`

### 72. Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | sygnatura sprawy — 3 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_hard_v2.txt` — `...wakowska@onet.pl\n  TEL:   +48 606 219 727 (T2T artefakt), ([[32) 456-78-90]]\n  ADRES: ul. Niepodległości 135, 20-100 Rybnik; ul. Kopern...` (niezakryte: `32`)
- `testy__test_reczny_21_06.txt` — `... k Sạdowy pr Wroclaw-Sr 3 Kr0p0wack\nD 15062024 wzywa P4nina [[Agat3 K0walczyk\nPESEL 77I1281 4755 do wys tep0wania\nw spraw e nr KM 8923/2023]]\n\nNi n. kont a kom: PL03 325O 0003 6637 2867 44O1 4154\nDluzn...` (niezakryte: `2023`)
- `testy__test_reczny_21_06.txt` — `...inien naprawić O→0 → silnik maskuje\n[SPODZIEWANE YELLOW] nr [[KM 8923/2023]] → SYGNATURA (kotwica "nr", wzorzec "8923/2023")\n[PUŁAPKA FP...` (niezakryte: `2023`)

### 73. Desktop zakrył, Mobile nie — częściowo (granice) | NUMER | dokument tożsamości — 3 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_hard_v2.txt` — `... 1090 10l4 7449 5552 52llO732\n\nDANE DODATKOWE:\nNr PESEL: [[9l040512 361\nNr paszportu: AB 1234567\nNr dowodu: EFG 456789\nData urodzenia: 21.O5.I979\n\nKLAUZULA POUFNOŚCI:\nNiniejsza umowa zawiera dane osobowe w rozumieniu RODO.\nZleceniobiorca zobowiązuje się do zachowania poufności\ndanych osobowych zleceniodawcy: Bartosz Jabłoński,\nPESEL 91040512361]], NIP 526-030-01-34.\n` (niezakryte: `91040512361`)
- `testy__test_ocr_normalizer_hard.txt` — `...83 I852\ne-mail: monka nowakowska@wp p1\n\nDANE PODATKOWE:\nNIP [[sprzedawcy: I42-I99-O6-38\nNIP nabywcy: 45I-OS2-35-26\nREGON: OI2345GT8\nIBAN: PLB7 I5OO IOI3 I625 5I9O 45IT 6SST\n\nDOWÓD OSOBISTY: FOH6 I4892\nPaszport: AB I234567]]\n\nAdres dostawy:\nu1. S1oneczna I9\n85-OOI Sosnowec\n\nAdres kor...` (niezakryte: `FOH6 I4892`)
- `testy__test_ocr_normalizer_hard.txt` — `...SST\n\nDOWÓD OSOBISTY: FOH6 I4892\nPaszport: AB I234567\n\nAdres [[dostawy:\nu1. S1oneczna I9\n85-OOI Sosnowec\n\nAdres korespondencyjny:\na1. Nepodleg1ości 95, OO-OOI Bytom\n\nORZEKAM:\nNa podstawie art. IO4 ustawy z dnia I4 czerwca I96O r.\nPESE1 świadka: 6OO6258O298]]\nNIP świadka: 4I5-II2-22-69\n\nPodpisano: BARTOSZ JAB1OWSKI\nDa...` (niezakryte: `ści 95, OO-OOI Bytom\n\nORZEKAM:\nNa podstawie art. IO4 ustawy z dnia I4 czerwca`)

### 74. Mobile zakrył, Desktop nie — całość | OSOBA | 2+ wyrazów — 3 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_lvl3_dane_wrazliwe.txt` — `...ani Anna Grabowska, PESEL: 78052312345.\nOrdynator oddziału: [[dr hab]]. Piotr Zając, nr PWZ 1234567.\nPodpisano: BARTOSZ LEWANDOWSK...`
- `testy__test_ui2_encje_silnik.txt` — `... NameEngine (YELLOW w UI-2) --\nPełnomocnik strony pozwanej: [[dr inż]]. Oskar Zepelin, specjalista ds. mediacji.\nInspektor nadzoru...`

### 75. Mobile zakrył, Desktop nie — częściowo (granice) | NUMER | NIP — 3 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...OLUTIONS SP Z O.O              Szpital Specjalistyczny im.\n[[NIP: 7 12-304-56 78]]                      Sw. Lukasza w Tarnowie\nREGON: 36 1298...` (niezakryte: `7`)
- `testy__test_nip_warianty.txt` — `...0 PLN brutto.\n\nOferta handlowa nr OH/2024/88.\nWystawiający: [[Usługi IT sp. z o.o., NIP 415-112-22-69.\nTermin ważności oferty: 30 dni.\n\nKarta klienta biznesowego. nip_nabywcy: 142-199-06-38]].\nPrzyznany limit kredytowy: 50 000 PLN.\n\n--- SEKCJA 6: NIP ...` (niezakryte: `30`)

### 76. Inny typ (Mobile=OSOBA, Desktop=NUMER) | Mobile=OSOBA, Desktop=NUMER | telefon — 3 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `clean__doc_00194.txt` — `..., zamieszkały/zamieszkała przy ul. Nowa 92 w Gdańsku, PESEL [[55091834595]], składam niniejszą skargę na działania Adama Jankowskiego.\n...`
- `testy__test_pesel_warianty.txt` — `...  | Tester oprogramowania\n5  | Górski          | Tomasz   | [[66111503816]]   | Administrator sieci\n\nPowyższa lista zawiera dane osobow...`
- `testy__test_ui2_encje_silnik.txt` — `...521-334-00-01,\nzamieszkałym ul. Szkolna 150, 20-100 Kielce, [[tel. 512 345 678]],\ne-mail jan.kowalski@wp.pl, a Moniką Wiśniewską, PESEL 8001...`

### 77. Desktop zakrył, Mobile nie — częściowo (granice) | NUMER | nr dokumentu/sygnatura/z literami — 3 wyst., 2 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `testy__test_reczny_21_06.txt` — `...\nskłada wniosek o przeliczenie emerytury.\n\nNumer sprawy: nr [[1204/EI/2024]]\nPoprzednia decyzja: poz. 4/2022\n\n-- PUŁAPKI GUARD --\n[SPODZ...` (niezakryte: `1204`)

### 78. Desktop zakrył, Mobile nie — całość | EMAIL | email — 3 wyst., 3 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `pliki__doc_lvl3_faktura_zlecenie.txt` — `...3 45 67                       NIP: 873 -000 -51-39\ne-mail: [[biuro©meditech-sol.pl]]            tel.: 14 631 02 00\n\nData wystawienia:    02.09...`
- `testy__test_silnik_statystyki.txt` — `...       → EMAIL_xxx\n11. info@gov.pl                        → [[EMAIL]]_xxx  ← może NIE (ogólny)\n\n--- PESEL (8) ---\n 1. 65051012345...`

### 79. Inny typ (Mobile=OSOBA, Desktop=FIRMA) | Mobile=OSOBA, Desktop=FIRMA | 2+ wyrazów — 3 wyst., 1 dok.

Hipoteza: Brak oczywistego wzoru — patrz przykłady.

- `stress__doc_00054.txt` — `...ejszą skargę na działania Asadbek Biała.\n\nW dniu 07.03.2024 [[Asadbek Biała]] dopuścił/dopuściła się zachowania, które uważam za rażące n...`
