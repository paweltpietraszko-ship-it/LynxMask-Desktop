# LYNX-OSOBA-NOT-PERSON — OSOBA krok 1: zasada Mobile dla słów, które nie są osobą (CC, 2026-10-21, wersja 2; poprawka bez Architekta)

Kolejka BOARD → TERAZ pkt 1. Wersja 1 (reguły z Morfeusza) wycofana po uwadze Pawła: „Mobile nie maskuje tych słów — mamy coś bardzo źle
przemyślane”. Krok 2 („udowodnij, że jesteś OSOBA”: pojedyncze słowo bez dowodu → lista „do oceny” w Guardzie) idzie osobno, razem
z `LYNX-GUARD-RESIDUE`; ten Task go **nie** robi.

## Zgłoszenie i diagnoza
Paweł: `Pliki testowe/doc_lvl3_faktura_zlecenie.txt`, linia po OCR `zamieszkaly: ul. Prz emyslowa 7/4, 32-5 00 Chrzanow` →
`OSOBA_015: ADRES_001, …`; w jego testach OSOBA zakrywa też „Data”, „Zapłata”. Mobile tych słów nie zakrywa.

Porównanie (pomocnik CC, tylko odczyt + sondy w procesie na syntetykach):
- **Mobile** nie ma modelu NER. OSOBA powstaje tylko z dowodu: słownik imion (`names_inflected.json`) / nazwisk top-1000
  (`surnames_top1000.json`) albo kontekst (Pan/Pani, tytuł, imię+nazwisko z dowodem po obu stronach) — `NameEngine.kt` `applyContextualBlacklist`
  :695–967. Każde przypisanie OSOBA przechodzi przez `OSOBA_DENYLIST` (:291–332, ~100 form dopisywanych po potwierdzonych kolizjach:
  data, zapłata, osoba, zamieszkania, adres…) i `isOnWhiteList` (:585: `WHITE_LIST_DOCUMENTS` :217 — faktura, umowa, aneks…;
  `WHITE_LIST_COMMON_WORDS` :244 — m.in. zamieszkały/a/e, wydziału, adres; kalendarz, kraje, miasta). Regexy wymagają wielkiej litery
  (np. :756).
- **Desktop**: spaCy proponuje kandydatów; `ner_layer._filter_institutions` (:331–402) zostawia jednowyrazową OSOBA, jeśli żaden filtr jej
  nie odrzuci (domyślnie zostaje). Obejście `[LYNX-T01]` (:356): słowo z `_PERSON_FORMS` omija wszystkie filtry — „Data” jest w
  `names_inflected.json` jako imię, więc przechodzi. `OSOBA_DENYLIST` z Mobile jest już w Desktop (`layers/ner_adapter.py:224–242`), ale
  działa tylko w ścieżce słownikowej `_apply_dictionary_names`, **nie** na kandydatach spaCy. Sonda: `_filter_institutions` dla
  jednowyrazowej OSOBA zostawia „Data”, „Zapłata”, „Faktura”, „Osoba”, „Termin”, „Dane”, „Zamieszkaly”, „zamieszkaly”; spaCy na fakturze
  zwraca „zamieszkaly” jako OSOBA.

## Zakres
1. **Jedno miejsce na listy z Mobile:** nowy moduł `backend/osoba_not_person.py` — `OSOBA_DENYLIST` przeniesiona z `ner_adapter.py`
   (bez zmian treści) + port 1:1 z Mobile `WHITE_LIST_DOCUMENTS` i `WHITE_LIST_COMMON_WORDS` (formy z `NameEngine.kt`, z komentarzem
   źródła i linii). Funkcja `not_person_word(word) -> bool`: wyraz (małe litery) na którejkolwiek z tych list.
   `ner_adapter._apply_dictionary_names` używa tego modułu zamiast własnej kopii (zachowanie bez zmian).
2. **Kandydaci spaCy** (korekta C1 Codexa r1 `f645f3a` — kolizje z prawdziwymi imionami/nazwiskami): w `ner_layer._filter_institutions`,
   **przed** obejściem `[LYNX-T01]`, jednowyrazowa OSOBA jest odrzucana w dwóch odrębnych przypadkach:
   a) słowo jest na **`OSOBA_DENYLIST` właściwej** (pierwsza część obecnej listy: potwierdzone kolizje — data, dane, osoba, zapłata,
      zamieszkania, sąd, urząd…) → odrzucone **zawsze**, także gdy jest w `_PERSON_FORMS` („Data” jako imię, „Osoba”/„Zapłata” jako
      nazwisko wg SGJP). **Jawny kompromis jak w Mobile:** samotne słowo z tej listy nie jest zakrywane nawet wtedy, gdy w danym tekście
      jest nazwiskiem; wielowyrazowa osoba („Anna Osoba”, „Jan Data”) nadal zakryta (reguła dotyczy tylko jednowyrazowej OSOBA).
      Kompromis przedstawiony Pawłowi 21.10 — zaakceptowany.
   b) słowo jest na **białych listach** (kalendarz, kraje, miasta z obecnej listy + port `WHITE_LIST_DOCUMENTS` /
      `WHITE_LIST_COMMON_WORDS`) → odrzucone **tylko gdy nie ma go w `_PERSON_FORMS`** (słowniki imion/nazwisk). Dzięki temu „Maja”,
      „Maj”, „Bill” itp. — jeśli są w słownikach osób — zostają OSOBA; „Faktura”, „Zamieszkały”, „Styczeń” odpadają.
   Moduł rozdziela te dwie listy (`OSOBA_DENYLIST` i `WHITE_LISTS`); `_apply_dictionary_names` dalej używa ich sumy jak dziś (bez zmian
   zachowania).
3. **Mała litera:** jednowyrazowa OSOBA zaczynająca się małą literą → odrzucona (jak regexy Mobile; „zamieszkaly”).
- Bez nowych list układanych przez nas: listy to wyłącznie istniejące, potwierdzone kolizje z Mobile. Kolejne słowa dopisujemy tylko po
  potwierdzonym fałszywym alarmie (jak Mobile).
- **Nie** zmieniamy: wielowyrazowych OSOBA, słów spoza list z wielkiej litery (krok 2), spaCy, HerBERT, Guarda, API, formatu tokenu,
  profilu, `_PERSON_FORMS`.

TASK_SCOPE:
- backend/osoba_not_person.py
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/tests/test_osoba_not_person.py

`ner_layer.py` ma 595/600 l. — w nim tylko import i wywołanie (≤ 4 linie). `ner_adapter.py` się zmniejsza (lista wyjęta).

## Odbiór (pomiar: pomocnik CC; Codex odtwarza)
Testy celowane (`test_osoba_not_person.py`, na `_filter_institutions` z encjami OSOBA i przez `run_pipeline_new` z atrapą NER):
„Data”, „Zapłata”, „Faktura”, „Osoba”, „Zamieszkały”, „zamieszkaly” jako jednowyrazowa OSOBA → odrzucone; „Nowak”, „Kowalczyka”,
„Wroblewski”, „Zając”, „Wróbel”, „Kot” → bez zmian (zostają); kolizje z białą listą będące w `_PERSON_FORMS` („Maja”, „Maj” — test
sprawdza najpierw obecność w `_PERSON_FORMS`) → zostają; „Anna Osoba” (wielowyrazowa) → zakryta; „Jan Kowalski, zamieszkały w Krakowie” → OSOBA tylko „Jan Kowalski”; `_apply_dictionary_names`
zachowuje się jak przed zmianą. Plik Pawła `doc_lvl3_faktura_zlecenie.txt`: „zamieszkaly” jawne, 4 osoby nadal zakryte.
Pomiar przed/po przez `/preview` w procesie (z `git archive`, pusty profil — NIE z katalogu Pawła, lifespan kasuje jego `api_token.txt`):
`dataset_clean` (gold osób), testy Mobile, `Pliki testowe`, obrazy benchmarku `dataset_20260627_095419` — **OSOBA: 0 nowych wycieków** poza jawnym kompromisem 2a (samotne słowo z `OSOBA_DENYLIST` — każdy taki przypadek wypisany osobno),
liczba jednowyrazowych OSOBA-FP przed/po. Szacunek: ~60 l. modułu (listy) + ~50 l. testów + ≤ 4 l. w `ner_layer.py`.

## Znalezione przy okazji (zgłoszone do `LYNX-ENGINE-BACKLOG`, nie w tym Tasku)
Ten sam plik: „im. Sw. Lukasza” → OSOBA (patron w nazwie instytucji); NIP po OCR „7 NUMER_021”; „32-5 00 Chrzanow” poza ADRES (jawne).
