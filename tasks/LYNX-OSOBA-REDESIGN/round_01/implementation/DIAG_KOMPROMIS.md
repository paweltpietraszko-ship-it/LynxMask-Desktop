# LYNX-OSOBA-REDESIGN — DIAG_ONLY: kompromis „filtry w Guardzie, silnik bez zmian” (CC, 23.10.2026)

Bez nowego kodu i pomiarów. Dane: `r1_diag` na main po HANDOFF (902 R1, 255 dok.; zapisane kategorie dla wszystkich 902 i fragmenty
dla 295 wystąpień / 100 unikalnych słów — limit 60 fragmentów na kategorię), `e1_compare` (R1 trybu on z fragmentami, słowa OSOBA
dodane/utracone per dokument). Nazwiska z pism publicznych zamaskowane.

## 1. Co odpowiada za spadek 902 → 337
**Spadek jest strukturalny, nie jest miarą odsiania fałszywych alarmów.** W trybie on stare źródła R1 (`_r1` 688 i `released()` 214)
są **wyłączone w całości**, a 337 to zupełnie inne pytania decydera. Wspólnych słów między R1 off (znane 100) i R1 on (50 unikalnych)
jest **7** (Chrome, Fabryce, Gospodarki, Logi, Roz, Sam, Sama). R1 on to w większości nowe śmieci: „Do” 155, „Skoro” 71,
„Składanie” 17, nazwy miejscowości z łącznikiem. Różnicy 565 nie wolno czytać jako 565 usuniętych FP.

## 2. Klasyfikacja znanych ostrzeżeń off (295 z 902 = 33%)
| klasa | wystąpień | przykłady (wystąpienia, osób w PESEL) |
|---|---|---|
| FP — słowo z białej listy 316 | **137** | Dzienniku 15, Polski 14, Warunków 12, Forma 7, Warunki 6, Termin 4, Sposób 3, Poczty, Nowej, Składniki, Brak, Opieki |
| FP — przymiotnik od miejsca/urzędu w nazwie | **29** | Gdańskim 14, Gdańskiego 3, Podlaskim 2, Miejskiego 2, Wielkopolski 2, Tomaszowski 2 |
| FP — nazwa funkcji | **20** | Wojewody 13, Wojewoda 6, Starosty 1 |
| zniknęło, bo zakryte w on | 27 | część FP zakrycia (Konieczne 5, Wojewódzką, Komendę, Zimne), część prawdziwe osoby (Dom*****, Dzi****, Księ***) |
| **NIEUSTALONE** (brak kontekstu) | 82 | Wielka 8, Paryż 7, Sam 9, Mają 4, Sama 4, Ani 3, nazwy obce/marki (Chrome, Ecorys, Vissim, Brunnen*) |
Pozostałe **607 z 902 — NIEUSTALONE** (runner zapisał tylko kategorie). Wiarygodnie sklasyfikowane: 186 FP + 27 „zakryte” = 213 (24%).
Prawdziwe osoby w R1 off wg zgrubnej metryki gold: 4 dopasowania (r1_diag), więc FP dominują, ale bez kontekstu nie da się tego policzyć.

## 3. Grupy FP i istniejące wyłączenia Guarda (`guard_residue._person_word`)
- Biała lista 316 — **brak** w Guardzie (lista istnieje tylko na gałęzi REDESIGN, nie ma jej na main).
- Nazwy funkcji (Wojewoda, Starosta, Komornik) — **brak** (jest `_OFFICE_TERMS` tylko dla strona/pan; `_ROLE_RE` w `osoba_not_person` służy jako kotwica, nie wyłączenie).
- Człony nazw urzędów/miejsc — **częściowo**: `_in_institution` (tylko po słowie-głowie instytucji w tym samym wierszu) i `in_city_name`
  (wieloczłonowe miejscowości); brak reguły „przymiotnik -ski/-cki obok słowa z wielkiej litery niebędącego imieniem/nazwiskiem”.
- Mała litera, początek zdania, tytuł — już są.

## 4. Proponowane filtry (wyłącznie Guard R1; silnik OSOBA, tokeny, propagacja, Przywróć bez zmian)
Każdy filtr **nie działa przy kotwicy osoby** (Pan/Pani, imię lub inicjał obok, token OSOBA obok, etykieta roli) — wtedy pytanie zostaje.
1. **Biała lista 316 w R1** (lemat słowa ∈ lista) — znany zysk ≥137/295. Ryzyko: nazwisko z listy (100–999 nosicieli) bez kotwicy
   przestaje dawać pytanie — ten sam koszt, który OWNER przyjął dla białej listy (C3); z kotwicą pytanie zostaje.
2. **Nazwa funkcji bez osoby** (lista funkcji jak w briefie: wojewoda, starosta, komornik, prezes, sędzia…) — znany zysk ≥20. Ryzyko:
   nazwisko-funkcja bez kotwicy (np. Wojewoda — 3748 osób) nie da pytania; z „Pan/imieniem” zostaje.
3. **Przymiotnik geograficzny/urzędowy w nazwie** (forma -ski/-cki/-dzki itd. sąsiadująca w wierszu ze słowem z wielkiej litery, które
   nie jest imieniem/nazwiskiem z PESEL ≥100 ani tokenem osoby) — znany zysk ≥29. Ryzyko: para dwóch nazwisk („Nowak Kowalski”) —
   wyłączona warunkiem „sąsiad nie jest nazwiskiem”.
Szacowany zysk na znanej próbce: ≥186/295 (63%); na całości 902 — **nieznany** (607 NIEUSTALONE).

## 5. Zakres zmian
`backend/guard_residue.py` (filtry w `_person_word` i `_released`) **oraz** mały plik danych z białą listą 316 (dziś tylko na gałęzi
REDESIGN, np. wydzielony `backend/guard_whitelist.json` albo stała) i lista funkcji. Silnik (`ner_layer`, `ner_adapter`,
`osoba_not_person`, `pipeline*`) bez zmian.

## 6. Minimalny brakujący pomiar (przed decyzją o eksperymencie)
Jedno przejście istniejącego `r1_diag.py` na main (tryb off, te same 255 dok.) z zapisem **wszystkich** 902 ostrzeżeń R1 (fragment +
~60 znaków kontekstu + czy fragment należy do osoby z gold) zamiast top-60 na kategorię. To zmiana 2–3 linii w istniejącym narzędziu
(bez nowego narzędzia) — wymaga zgody. Pozwoli sklasyfikować 607 NIEUSTALONYCH i policzyć zysk każdego filtra oraz ryzyko.

## Werdykt
**WARTO PRZETESTOWAĆ KOMPROMIS** — na znanej trzeciej części 63% R1 to FP trzech powtarzalnych klas, których Guard dziś nie wyłącza,
a filtry nie dotykają silnika. Warunek: najpierw pomiar z pkt 6, potem decyzja OWNERA o małym eksperymencie.
