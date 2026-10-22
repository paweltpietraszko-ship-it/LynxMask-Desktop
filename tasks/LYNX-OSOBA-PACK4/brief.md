# LYNX-OSOBA-PACK4 — błędy OSOBA z oglądu OWNERA + krok 2 „udowodnij, że jesteś osobą” (z Guardem)

22.10.2026, CC. Poprawki bez Architekta (zasada OWNERA 21.10). OWNER 22.10: „Tak, włącz krok 2 do paczki”, „Tak, robimy paczkę”
(wariant: kandydat bez dowodu nie jest zakrywany, ale trafia do Guarda). Diagnoza i prototypy pomocnika CC na kopii main `6264290`
(lokalnie `%TEMP%\lynx_cc_review\osoba_pack4\`: `raport.md`, `proto_bugs1-4.diff`, `proto_krok2.diff`, skrypty `work\`).
Teksty przykładów syntetyczne (`Pliki testowe/`, repo Mobile `testy/`).

## Błędy 1–4 (przyczyna → poprawka w istniejącym miejscu)
1. **„OCZEKIWANE:” (WERSALIKI) jako OSOBA, zakrywane wszędzie.**
   - Przyczyna: spaCy daje persName; `osoba_not_person.reject_single_osoba` przepuszcza; `ner_adapter` podmienia wszystkie wystąpienia.
   - Poprawka: pojedyncze słowo WERSALIKAMI odrzucane, chyba że jest w `_PERSON_FORMS` albo Morfeusz zna je jako imię lub nazwisko.
   - Kontrola: „NAZWISKO: KOWALSKI” nadal zakryte.
2. **Lista nazwisk po przecinkach = 1 token.**
   - Przyczyna: `spacy_ner._merge_adjacent_entities` skleja persName przez „, ”, a także przez „. ” i „ - ”.
   - Poprawka: OSOBA sklejana tylko przez spacje/tabulatory albo sam łącznik („Kowalska-Nowak”); FIRMA bez zmian.
   - Wymagane w tym samym Tasku: `tests/test_ner_multiline.py::test_prawdziwy_spacy_span_z_nowa_linia` (3 przypadki) ma warunek wstępny „model zwrócił span z \n”. Ten span powstawał z błędnego sklejania. Warunek do poprawy; zakrycie nazwisk w tych tekstach bez zmian.
3. **Patroni ulic i człony nazw miast jako OSOBA poza adresem.**
   - Przykłady: „Góra” z „Zielona Góra”, „Jana”/„Pawła” z „ul. Jana Pawła II”, „Władysława Stanisława” z ul. Reymonta → „Jelenia OSOBA_x”.
   - Przyczyna: span spaCy bez „ul.” omija filtr ulic w `ner_layer`; ścieżka słownikowa w `ner_adapter` zakrywa imię bez kontekstu; „Góra” jest w słowniku nazwisk.
   - Poprawka: `inside_street_name()` wołane także dla spanów spaCy i w ścieżce słownikowej; pomijać słowo, które z sąsiadem tworzy miejscowość z `_CITY_FORMS`.
4. **„Pani Róża Zielona” → zakryta tylko „Róża”.**
   - Poprawka (S4: jedna wiarygodnie ustalona osoba = jeden token): w `_apply_first_names` słowo z wielkiej litery tuż za samym imieniem
     należy do tej samej osoby. Zakres encji rozszerzamy na „Róża Zielona”: jeden token OSOBA, w mapie wartość „Róża Zielona”.
     Nie dostaje osobnego tokenu. Kolejne wystąpienia tej osoby (odmiany, samo nazwisko) dostają ten sam token według dotychczasowej
     logiki mapy. Nie scalamy różnych osób.

## Krok 2 — pojedyncze słowo jest OSOBA tylko z dowodem
Jedno miejsce decyzji: `osoba_not_person.single_osoba_evidence(text, start, end, …)`. Wołają je oba źródła pojedynczych OSOBA:
- `ner_layer` po `_filter_institutions`;
- ścieżka słownikowa w `ner_adapter`;
- `herbert_net`, gdy jest włączony.

Dowody:
- tytuł lub forma przed słowem (Pan/Pani/p./dr/mgr/adw./mec./sędzia…);
- rola w linii („Nabywca:”, „Wykonawca:”, „Świadek”, „Pełnomocnik”…);
- imię, inicjał albo token OSOBA obok;
- lista z innym dowodem w sąsiedztwie;
- to samo słowo w pełnym imieniu i nazwisku w tym dokumencie;
- Morfeusz: imię/nazwisko bez znaczenia pospolitego. Przymiotniki na -ski/-cki nie liczą się jako pospolite; słowo bez ogonków sprawdzane w wariantach z ogonkami.

Bez Morfeusza (błąd): zakrywamy jak dotąd (fail-safe).
Samo imię mające znaczenie pospolite (Malina, Róża) i słowo nieznane Morfeuszowi **nie są dowodem**.

**Guard (decyzja OWNERA 22.10):**
- Każdy kandydat OSOBA odrzucony z braku dowodu trafia do Guarda jako ostrzeżenie „Możliwe nazwisko” w każdym wystąpieniu w tekście (poza tokenami), także na początku zdania i WERSALIKAMI.
- Silnik przekazuje listę odrzuconych do `guard_residue.collect_warnings`. Bez cichych wycieków: nic, co silnik uznał za możliwą osobę, nie przechodzi bez pytania.
- Wyjątek: słowa z białych list/denylist (krok 1) i etykiety z dwukropkiem nie trafiają do Guarda (decyzja z kroku 1).

## Granice
- `ner_layer.py` ma 597 l. (ratchet): w nim tylko wywołanie; logika w `osoba_not_person.py`.
- `guard_residue.py`: kod gałęzi `LYNX-GUARD-FIX1`, więc start po jej scaleniu (rebase).
- Bez zmian formatu tokenów, `TOKEN_RE`, `.lynxdict`, S4. Poza zakresem: adres „w mieście Jelenia Góra” / ulica bez numeru (warstwa ADRES, do DROBNYCH UWAG).

TASK_SCOPE:
- backend/osoba_not_person.py
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/spacy_ner.py
- backend/guard_residue.py
- backend/pipeline.py
- backend/herbert_net.py
- backend/tests/test_osoba_pack4.py
- backend/tests/test_ner_multiline.py
- backend/tests/test_guard_residue.py
- backend/tests/test_audyt_2026_10.py
- tasks/LYNX-OSOBA-PACK4/brief.md
- tasks/LYNX-OSOBA-PACK4/repo_before.hash

Szacunek: kod ~200 l. + testy ~150 l. (>150 — zgoda OWNERA przed kodem).

## Odbiór
- `tests/test_osoba_pack4.py`: reproduktory 1–4 i kroku 2 (teksty syntetyczne):
  - „W ogrodzie rosła Malina i Róża, a płot był Zielony.” → bez OSOBA, 3 ostrzeżenia Guarda;
  - „Pani Malina przyniosła dokumenty.”, „Anna Malina”, „Nabywca: Malina” → OSOBA;
  - lista „Kowalski, Nowak, Pietraszko, Wiśniewski, Kot” → 5 tokenów;
  - „OCZEKIWANE:” jawne; „Jelenia Góra” bez OSOBA; „Pani Róża Zielona podpisała umowę.” → „Pani OSOBA_n podpisała umowę.”, jeden token, mapa `OSOBA_n = "Róża Zielona"`, bez jawnego „Zielona” (S4).
- Pomiar (pomocnik CC, skrypty z diagnozy):
  - osoby gold zakryte: fresh 127/127 i KPWr 328/358 dla błędów 1–4;
  - krok 2: straty wyłącznie jako ostrzeżenia Guarda — **0 cichych wycieków osób gold**;
  - liczba ostrzeżeń na dokument fresh przed i po.
- Gdy gotowy będzie `LYNX-GOLD-SET`: pomiar także na części dev/test (ciche wycieki, zbędne zakrycia).

## Korekta C1 (Codex BRIEF_ONLY r1 `3cdcb3c`)
Punkt 4 i odbiór ujednolicone z S4: „Pani Róża Zielona” = jedna osoba = jeden token z wartością „Róża Zielona”. Alternatywa dwóch tokenów usunięta.
Zgoda OWNERA na rozmiar (~350 l. z testami) udzielona 22.10 („Zgoda”).

## ROZSZERZENIE CC (22.10, ta sama klasa — skutki kroku 2 widoczne w pomiarze LYNX-GOLD-SET)
Wykryte pomiarem „widoku człowieka” na zbiorze GOLD (dev) po wdrożeniu kroku 2:
1. **Człony miejscowości przestały być zakrywane jako OSOBA**, ale Guard R1 pytał o nie („Góra” w „Jelenia Góra” 14×, „Tomaszów” w „Tomaszów Mazowiecki” 10×).
   - `osoba_not_person.in_city_name()` (baza SIMC `_CITY_FORMS`) to jedno miejsce. Używają go krok 2 (nie OSOBA, nie pytanie), ścieżka słownikowa i Guard R1.
   - Słowo znane Morfeuszowi wyłącznie jako nazwa miejsca nie jest pytaniem (samo miasto jawne — polityka OWNERA).
2. **Miasto tuż po zakrytym adresie** („ADRES_003, Ostrów Wielkopolski”) wcześniej przypadkiem pytane przez R1. Teraz jawna reguła R3 „Miejscowość obok zakrytego adresu”: to część adresu, nie „samo miasto”.
3. **Kandydat OSOBA będący samą liczbą** („6658,63” z NER) zostaje zakryty jak dotąd. „Kont0” (OCR) ocenia krok 2.

Testy:
- `test_guard_residue.py` +2: człon miasta bez pytania; miejscowość po ADRES = pytanie.
- `test_audyt_2026_10.py`: `test_kont0_nie_jest_osoba` przeszedł (XPASS) → marker zdjęty zgodnie z zasadą pliku.
4. **Odmiany słowa odrzuconego przez krok 2** (pomiar KPWr: „Maciolus” pytane, „Maciolusa” ciche): Guard pyta także o formy z typową końcówką odmiany (`_INFLECTIONS`). „Kawałek” nie jest odmianą „Kawa”. Test w `test_guard_residue.py`.
