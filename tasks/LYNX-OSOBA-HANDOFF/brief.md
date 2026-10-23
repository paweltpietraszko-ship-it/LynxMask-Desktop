# LYNX-OSOBA-HANDOFF — silnik przekazuje Guardowi tylko kandydatów, którzy mogą być nazwiskiem

23.10.2026, CC. Poprawka (błąd + filtr przekazania) — brief CC + Codex, bez Architekta. Krok 1 pracy nad szumem Guarda R1;
`LYNX-GUARD-R1-NOISE` (strojenie samego Guarda) dopiero po scaleniu tego kroku, na tym, co silnik jeszcze przepuści (uzgodnione z Pawłem 23.10).
Kontrakt S4 bez zmian (Guard ostrzega, nie maskuje; „wiarygodne podejrzenia, nie przypadkowe wyrazy”).

## Problem (pomiar CC 22.10, main `2ea3a12`)
- 255 dokumentów publicznych (`real_public` BIP/Sejm/UZP/KIO/Codex, `dataset_public` KIO, `dataset_layout`, `Pliki testowe`):
  **7448 pytań R1, 3 dotyczą osoby z gold**; KIO 72 pytania/dok., a zapis jest zablokowany do decyzji przy każdej pozycji.
- **6760 (91%) pochodzi z `released()`** — słów, które spaCy wziął za osobę, a silnik (krok 2 PACK4) słusznie odrzucił.
  Najczęstsze: „Odwołującego/Odwołujący” ~1150, „……” 294, „Pzp” 148, „Powódka”, „Przystępującego”, „Protokolant”, „Pozwany”,
  „Komornika”; małe „odwołującego”, „powódki”, „sam”, „ani”, „i”, „a”.
- **Przyczyna — przekazanie między warstwami** (sprawdzone na żywo 23.10):
  1. spaCy (model statystyczny) niekonsekwentnie bierze termin procesowy za osobę: „Pełnomocnik Przystępującego…” → OSOBA,
     „Powódka wniosła…” → OSOBA, „Sąd uznał, że Odwołującemu…” → OSOBA; „Odwołujący wniósł…” → nic.
  2. Morfeusz (`osoba_not_person._common_or_person`) poprawnie mówi: tylko słowo pospolite, nie imię/nazwisko → silnik nie zakrywa.
  3. `single_osoba_evidence` wpisuje jednak KAŻDE odrzucone słowo do `released()` — nie rozróżnia „brak dowodu, może być nazwiskiem”
     („Kawa”, „Maciolus”) od „Morfeusz wie, że to tylko zwykłe słowo” („Odwołującego”).
  4. `guard_residue._released` szuka potem każdego wystąpienia słowa w dokumencie, także małymi literami (IGNORECASE dla CAPS „MALINA”,
     Codex PACK4 F1) → jedna pomyłka spaCy = dziesiątki pytań.
  5. **Błąd:** do `released()` trafia też pusty napis i nie-słowa („……”, „Pzp”, „Cz”, „G”); pusty rdzeń w `_released` dopasowuje same
     końcówki odmiany → pytania o „i”, „a”.

## Poprawka
1. **`backend/osoba_not_person.py`, `single_osoba_evidence`** — po istniejących warunkach, przed `_RELEASED.append`:
   słowo NIE trafia do `released()` (nie jest zakrywane i Guard o nie nie pyta), gdy:
   - **A.** Morfeusz zna je **wyłącznie** jako słowo pospolite (`common is True and person is False`) — „Odwołującego”, „Powódka”,
     „Protokolant”, „Przystępującego”, „Gwaranta”, „Mebla”; albo
   - **B.** nie ma kształtu nazwy: nie same litery (z łącznikiem), < 3 liter albo bez samogłoski — „……”, „”, „Pzp”, „Cz”, „G”, „9ee7”.
   Słowa z odczytem imię/nazwisko („Kawa”, „Malina”, „Róża”, „Nowak”, „Mazur”) i nieznane Morfeuszowi („Maciolus”, „Geyer”) — bez zmian
   (nadal do Guarda). Błąd Morfeusza (`None`) — bez zmian (zakrywamy).
2. **`backend/guard_residue.py`, `_released`** (odbiór przekazania) — pomija wystąpienia zapisane w całości małymi literami
   („odwołującego”, „sam”, „ani”); CAPS („MALINA”, „RÓŻY”) i zapis z wielkiej litery — bez zmian.
- Bez zmian: `_r1` i pozostałe reguły Guarda, co silnik zakrywa, allowlista S5, panel.

## Wynik prototypu (A + B + 2; `%TEMP%\...\scratchpad\r1\src\backend`)
| | main | prototyp |
|---|---|---|
| pytania R1, 255 dok. publicznych | 7448 | **899** |
| — w tym z `released()` | 6760 | 211 |
| KIO (B_kio / dataset_public) pytań R1/dok. | 72 / 54 | 5,6 / 5,0 |
| GOLD dev / test: ciche razem | 20 / 52 | 20 / 52 |
| GOLD dev / test: OSOBA ciche, z ostrzeżeniem | 1/9, 0/13 | 1/9, 0/13 |
| GOLD zbędne zakrycia | 69 / 152 | 69 / 152 |
Pozostałe ~690 pytań R1 to `_r1` (człony nazw własnych „Dzienniku Ustaw”, przymiotniki od miejsc, „Pan + funkcja”) — zakres `LYNX-GUARD-R1-NOISE`.
(Uwaga: w rozmowie z Pawłem 23.10 CC podał „531” — to wynik z dodatkową regułą Guarda o członach nazw; sam krok przekazania = 899.)

TASK_SCOPE:
- backend/osoba_not_person.py
- backend/guard_residue.py
- backend/surnames_extended.json
- backend/tests/test_osoba_handoff.py
- tasks/LYNX-OSOBA-HANDOFF/brief.md
- tasks/LYNX-OSOBA-HANDOFF/repo_before.hash
- tasks/LYNX-OSOBA-HANDOFF/round_01/implementation/DELIVERY.md
- tasks/LYNX-OSOBA-HANDOFF/round_01/implementation/r1_diag.py
- tasks/LYNX-OSOBA-HANDOFF/round_01/implementation/c1_evidence.py

Szacunek: kod ~10 l., testy ~60 l. (< 150).

## Odbiór
- `tests/test_osoba_handoff.py`:
  - `released()` po zdaniu z „Pełnomocnik Przystępującego…”, „Powódka wniosła…”, „…że Odwołującemu…” — bez tych słów, bez zakrycia;
  - „Kawa”, „Malina”, „Maciolus” — nadal w `released()` (gdy bez dowodu) / nadal R1;
  - `released()` nie zawiera „”, „……”, „Pzp”, „Cz”;
  - `_released`: „Kawa zlecił… kawa stygnie” → tylko „Kawa”; „MALINA” → R1 (Codex PACK4 F1); małe „odwołującego” → brak;
  - reproduktor błędu „i”/„a”: dokument z kandydatem dającym pusty rdzeń → brak R1 na „i”, „a”.
- Regresja: `test_guard_residue`, `test_osoba_pack4`, `test_osoba_not_person`, `test_guard_allowlist_s5`, `test_layers`, `test_audyt_2026_10`
  (znane faile bez zmian).
- Pomiar: `r1_diag.py` (do repo, `round_01/implementation/`) na tych samych 255 dok. (main vs gałąź) + GOLD `human_view.py all`:
  R1 ≤ 950, GOLD ciche razem i OSOBA nie większe niż main, zbędne zakrycia bez zmian.
- Oko Pawła: pismo KIO na silniku z gałęzi.

## Odpowiedź na Codex BRIEF_ONLY r1 C1 (`b4ac3be`) — granica „tylko pospolite” dla nazwisk
**Dowód** (`round_01/implementation/c1_evidence.py <backend> <katalog PESEL CSV> <lista>`; lista = Mobile `surnames_extended.json` oczyszczona
`tasks/LYNX-NAMES-DICT-CLEAN/clean_names.py`; PESEL = dane.gov.pl zbiór 1681 „Nazwiska osób żyjących występujące w rejestrze PESEL”, CC0,
zasoby 1148808/1148811 stan 2026-01-20, kolumny `Nazwisko aktualne, Liczba`; bez danych z dokumentów):
- 38 783 hasła listy; **113** Morfeusz klasyfikuje jako tylko-pospolite (`common=True, person=False`) — razem 51 092 osoby w PESEL; 11 z nich jest w `person_forms`.
  Największe: Kim 4012, Li 2111, Holub 2107, Prokopenko 1673, Park 1240, Lysak 1211, Islam 1052, Palii 1003, Yang 1000, Sokol 890 … (głównie nazwiska obce).
- Najczęstsze słowa `released()` na main: **żadne słowo roli nie jest na liście nazwisk** — „Odwołującego/Odwołujący/Odwołującemu”, „Przystępującego”,
  „Protokolant”, „Powódka”, „Powodowi”, „Pozwanemu”, „Protestującego”, „Skarżącego”, „Zaskarżonemu”, „Gwaranta”, „Poręczyciela”, „Mebla”, „Ergo”, „Loco”,
  „Komornika”, „Sam”. Na liście są: „Mają”, „Rady”, „Marszałek”, „Konieczne”, „Pola” — mają odczyt imię/nazwisko (`person=True`), więc reguła A ich i tak nie dotyczy.
**Granica (zastępuje pkt 1.A):** słowo NIE trafia do `released()`, gdy Morfeusz zna je wyłącznie jako pospolite **i** nie ma go ani w `person_forms`, ani
na liście nazwisk `backend/surnames_extended.json` (Mobile 39k oczyszczona; formy z odmianą; zapis zwarty w 1 linii; ładowana raz; brak pliku → reguła A wyłączona,
zachowanie jak main). Wtedy 113 nazwisk z klasy C1 (i każde inne z listy) nadal idzie do Guarda — **brak kosztu w tej klasie**, decyzja OWNERA niepotrzebna.
Ograniczenie wniosku: nazwisko spoza listy 39k (nosiciele < ok. 100 w PESEL), tylko-pospolite w Morfeuszu i bez dowodu w zdaniu nie dostanie pytania z `released()`
(może je dać `_r1`/inna reguła). Rozmiar tej klasy nieznany; lista 39k obejmuje nazwiska od ok. 100 nosicieli wzwyż.
**Odbiór — dodatkowe klasy w `test_osoba_handoff.py`:** kandydat tylko-pospolity z listy nazwisk (np. „Holub”, „Prokopenko” — klasyfikacja Morfeusza sprawdzona w teście) → nadal w `released()`;
kandydat w `person_forms` → nadal w `released()`; słowo roli spoza listy → nie; brak pliku listy → zachowanie jak main.
Szacunek: kod ~15 l., testy ~70 l.; `surnames_extended.json` 1 linia (6,4 MB; zgoda Pawła 22.10 na plik tej wielkości).
