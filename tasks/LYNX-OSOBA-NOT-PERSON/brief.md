# LYNX-OSOBA-NOT-PERSON — OSOBA krok 1: słowa, które na pewno nie są osobą (CC, 2026-10-21; poprawka bez Architekta)

Kolejka BOARD → TERAZ pkt 1 (uzgodniona z Pawłem 21.10 wieczorem). Krok 2 („udowodnij, że jesteś OSOBA” + lista „do oceny” w Guardzie)
idzie osobno, razem z `LYNX-GUARD-RESIDUE`; ten Task go **nie** robi.

## Zgłoszenie Pawła i diagnoza CC
Paweł: w pliku `Pliki testowe/doc_lvl3_faktura_zlecenie.txt` linia po OCR `zamieszkaly: ul. Prz emyslowa 7/4, 32-5 00 Chrzanow`
wychodzi jako `OSOBA_015: ADRES_001, 32-5 00 Chrzanow` („OSOBA zakrywa nawet »zamieszkały«”).

Odtworzenie (main `1f60c06`, żywy silnik 8765 i w procesie):
- „zamieszkaly w Krakowie” → `OSOBA:zamieszkaly`; „zamieszkały” (z ogonkiem), „platnosc”, „wystawil” → bez OSOBA.
- Śledzenie warstw `pipeline_new`: token dodaje `layers.ner_adapter.apply_ner_layer` — spaCy zwraca jednowyrazową OSOBA, a
  `ner_layer._filter_institutions` jej nie odrzuca.
- **Przyczyna ogólna:** w `_filter_institutions` jednowyrazowa OSOBA niepotwierdzona (`_is_person_word` = False) przechodzi przez filtry
  (prefiks geo, przymiotnik `_ADJECTIVE_ENDINGS_RE`) i jeśli żaden jej nie odrzuci — **domyślnie zostaje OSOBA** (`out.append(ner)` na
  końcu). „zamieszkaly” to dla Morfeusza `ign` (nieznane), nie ma końcówki przymiotnikowej → zostaje.
- Morfeusz (SGJP 2026-06-01) nie rozróżni wszystkiego: kwalifikator `nazwisko` mają m.in. „Data”, „Zapłata”, „Osoba”, ale też „Nowak”,
  „Mróz”, „Wilk”, „Kowalczyka”. Bez kwalifikatora imię/nazwisko są np. „Faktura”, „Nabywca”, „Razem”, „Płatność”, „Kwota”.
  Dlatego krok 1 bierze tylko to, co **na pewno** nie jest osobą; słowa dwuznaczne („Data” vs „Nowak”) zostają do kroku 2 (dowód albo
  człowiek). Uwaga przy okazji: wcześniejsze różnice „w procesie vs żywy silnik” wynikały z CRLF w pliku testowym — to nie jest przyczyna,
  sama linia z LF daje ten sam błąd.

## Zakres
Nowy moduł `backend/osoba_not_person.py` z funkcją `certainly_not_person(word: str) -> bool`; w `ner_layer._filter_institutions` jedno
wywołanie: jednowyrazowa OSOBA, która **nie** jest potwierdzona (`_street_person`/`_is_person_word`), a `certainly_not_person` = True →
odrzucona (tak jak inne filtry, z `logger.debug` bez treści). Reguły (wszystkie bez list słów):
1. **Typ tokenu jako słowo:** wyraz równy nazwie typu tokenu z istniejącej stałej typów (OSOBA, FIRMA, ADRES, NUMER, KWOTA, EMAIL,
   INSTYTUCJA…) w dowolnej wielkości liter → nie osoba.
2. **Śmieci OCR:** wyraz zawiera cyfrę albo znak spoza liter / łącznika / apostrofu → nie osoba.
3. **Mała litera:** wyraz zaczyna się małą literą, nie ma go w `_PERSON_FORMS` (słowniki imion/nazwisk), a Morfeusz dla formy z wielkiej
   litery nie daje kwalifikatora imię/nazwisko → nie osoba („zamieszkaly” → nie osoba; „nowak” → zostaje).
4. **Znane tylko jako słowo pospolite:** Morfeusz zna wyraz (co najmniej jedna interpretacja inna niż `ign`), żadna interpretacja nie ma
   kwalifikatora imię/nazwisko, wyrazu nie ma w `_PERSON_FORMS` → nie osoba („Faktura”, „Nabywca”, „RAZEM”). Dotyczy także WIELKICH LITER.
- Bez Morfeusza (tryb degraded) reguły 3 i 4 nie działają (zostaje dzisiejsze zachowanie) — wolimy fałszywy alarm niż wyciek (S1/S3).
- **Nie** zmieniamy: wielowyrazowych OSOBA, słów z kwalifikatorem nazwisko/imię („Data”, „Zapłata”, „Nowak”), nieznanych Morfeuszowi
  wyrazów z wielkiej litery („Wroblewski”, „Dabrowskl” — nazwiska po OCR), spaCy, HerBERT, Guarda, API, formatu tokenu, profilu.

TASK_SCOPE:
- backend/osoba_not_person.py
- backend/ner_layer.py
- backend/tests/test_osoba_not_person.py

`ner_layer.py` ma 595/600 l. — w nim tylko import i wywołanie (≤ 4 linie).

## Odbiór (pomiar: pomocnik CC; Codex odtwarza)
Testy celowane (`test_osoba_not_person.py`): „zamieszkaly w Krakowie” → bez OSOBA; „Jan Kowalski, zamieszkały w Krakowie” → OSOBA tylko
„Jan Kowalski”; „Faktura”, „OSOBA”, „Nabyw3a” jako samotne → bez OSOBA; „Nowak”, „Wroblewski”, „Kowalczyka” samotne → bez zmian
(nadal OSOBA, jeśli spaCy je zwróci); bez Morfeusza reguły 3–4 nieaktywne. Plik Pawła `doc_lvl3_faktura_zlecenie.txt`: „zamieszkaly”
jawne, 4 osoby nadal zakryte.
Pomiar przed/po przez `/preview` w procesie (pusty profil): `dataset_clean` (gold osób), testy Mobile, `Pliki testowe`, obrazy benchmarku
`dataset_20260627_095419` — **OSOBA: 0 nowych wycieków** (osoby gold zakryte jak przed), liczba jednowyrazowych OSOBA-FP przed/po
z podziałem na reguły 1–4. Szacunek: ~40 l. modułu + ~50 l. testów + ≤ 4 l. w `ner_layer.py`.

## Znalezione przy okazji (zgłoszone do `LYNX-ENGINE-BACKLOG`, nie w tym Tasku)
Ten sam plik: „Szpital … im. Sw. Lukasza” → `OSOBA` „Sw. Lukasza” (patron w nazwie instytucji); NIP po OCR „7 NUMER_021” (pierwsza cyfra
poza tokenem); kod pocztowy i miasto po OCR „32-5 00 Chrzanow” poza `ADRES` (jawne).
