# LYNX-NAMES-DICT-CLEAN — słownik imion bez form obcych słów + „Zawarta” jako kolizja (CC, 2026-10-21; poprawka bez Architekta)

Paczka 3 z pomiaru na prawdziwych zdaniach KPWr (CLARIN-PL, CC BY 3.0; 75 dok., lokalnie `%TEMP%\lynx_cc_review\kpwr\`): 94 fałszywe
OSOBA, głównie zwykłe słowa („Ale” 13, „Tym” 7, „Jest” 6, „Być” 5, „Albo”, „Nic”, „Była”), oraz 13 `[REDACTED]` / 14 blokad.
Paweł 21.10 wybrał naprawę słownika u źródła (zamiast filtra w kodzie).

## Przyczyna (diagnoza pomocnika CC)
`backend/names_inflected.json` (i odpowiednik w Mobile) zawiera pod imionami formy innych słów: Tom → być, jest, jestem, tym, tego,
była, będę; Ala → ale; Kim → kto; Nico → nic; Mai → mają; Inna → innym; Rana → rano; Tania → taniej. Generator
(`backend/generate_lookups_v3.py:145–160`, `get_inflections`) brał formy wszystkich interpretacji homografu bez sprawdzenia lematu
i kwalifikatora imię/nazwisko (plik pochodzi z wcześniejszej wersji generatora). Ścieżka FP: `layers/ner_adapter._apply_dictionary_names`
(samotne imię ze słownika) — 59 z 94. `[REDACTED]`/blokady to skutek: zakryte „Rogalik” → Guard widzi „rogalików” (dopasowanie bez
wielkości liter) — Guard działa poprawnie, bez zmian. „Zawarta” („Zawarta pomiędzy:”, 444 FP w `pl-pii-synthetic-v1`) — spaCy `persName`,
nie słownik.

## Zakres
1. **`backend/names_inflected.json`** — wyczyszczony skryptem `tasks/LYNX-NAMES-DICT-CLEAN/clean_names.py --closed` (odtwarzalny bajt
   w bajt: `clean_names.py backend/names_inflected.json out.json report.json --closed`). Forma zostaje, gdy: jest kluczem; Morfeusz daje
   lemat = baza; ma interpretację imię/nazwisko; jest wariantem ASCII formy zachowanej; Morfeusz jej nie zna i zaczyna się jak baza.
   Usuwana dodatkowo (`--closed`) forma inna niż klucz z interpretacją klasy zamkniętej (spójnik, partykuła, czasownik, przysłówek,
   zaimek), chyba że to forma l.poj. tego samego imienia. Wynik: 20 504 → 18 388 form (−2 116, 166 kluczy); format pliku 1:1.
   `surnames_top1000.json` Desktop bez zmian (reguła L1 nie usuwa nic; „Musiał” ma lemat „Musiał”).
2. **`backend/osoba_not_person.py`** — `OSOBA_DENYLIST` + „zawarta zawarty zawarte” (potwierdzona kolizja, jak lista Mobile; kompromis
   denylisty zaakceptowany przez Pawła 21.10 — samotne słowo z listy nie jest OSOBA, wielowyrazowe „Jan Zawarta” bez zmian).
- Bez zmian: kod warstw, Guard, spaCy, format tokenów, `surnames_top1000.json`. Mobile: osobno (plik + instrukcja w repo Mobile, Paweł 21.10).

TASK_SCOPE:
- backend/names_inflected.json
- backend/osoba_not_person.py
- backend/tests/test_names_dict_clean.py
- backend/tests/test_osoba_not_person.py

Zmiana `names_inflected.json` to 166 linii (jedna linia na klucz) — powyżej 150, dane, nie kod: zgoda Pawła wymagana i odnotowana w BOARD.

## Odbiór
Testy (`test_names_dict_clean.py`): „ale, jest, jestem, być, była, tym, tego, nic, kto, albo, rano, taniej, będę” nie są formami żadnego
imienia; prawdziwe formy zostają (annie, maję, oliwię, tomasza, katarzyny, piotrowi); „Ale to nie wszystko. Jest dobrze. Być może…
Nic…” → brak OSOBA; „Zawarta pomiędzy: Jan Kowalski a Anna Nowak.” → OSOBA tylko osoby; Maja, Zając, Kot nadal zakryte.
Kontrola strat (pomocnik): 390 unikalnych słów osób gold (KPWr, `dataset_clean`, pl-pii PERSON) — wszystkie obecne w słowniku przed
są po (0 strat). Pomiar (prototyp, kopia `git archive` main `2297e3d`): KPWr FP OSOBA 94 → 42, blokady 14 → 13, `[REDACTED]` 13 → 10,
osoby gold 335/360 bez zmian; pl-pii PERSON 2242/2242 bez zmian (FP „Zawarta” — po dopisaniu do denylisty do potwierdzenia pomiarem).
