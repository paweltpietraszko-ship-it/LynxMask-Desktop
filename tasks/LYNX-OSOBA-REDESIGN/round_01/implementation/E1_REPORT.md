# LYNX-OSOBA-REDESIGN — raport E1 (CC, 23.10.2026): **BRAMKA STOP**

Kod E1: `cc516b7` (gałąź zadania; `backend/person_decision.py` 269 l., przełącznik `LYNX_OSOBA_DECIDER` domyślnie **off** — wynik
użytkownika bez zmian). Pomiar: ten sam kod, ten sam dokument, tryb off (stary silnik) vs on (jedna decyzja wg tabeli §2 briefu v1.4).
Narzędzia: `e1_compare.py` (255 dok. publicznych, manifesty CC lokalnie), GOLD `human_view.py all`. Nazwiska z pism publicznych
zamaskowane częściowo.

## Wyniki
| | off (stary) | on (decyzja §2) |
|---|---|---|
| GOLD dev: OSOBA zakryte / z ostrzeżeniem / **ciche** | 325 / 9 / **1** | 236 / 83 / **16** |
| GOLD test: OSOBA zakryte / z ostrzeżeniem / **ciche** | 657 / 13 / **0** | 480 / 154 / **36** |
| GOLD zbędne zakrycia dev / test | 69/440, 152/880 | 107/440, 215/880 |
| GOLD ostrzeżeń/dok. dev / test | 1,23 / 0,97 | 3,75 / 3,67 |
| 255 dok.: pytania R1 | 902 | 337 |
| 255 dok.: wszystkie ostrzeżenia | 2248 | 1941 |
| 255 dok.: słowa OSOBA dodane / utracone | — | 347 / 306 |

**Utracone (wybór):** same imiona (Katarzyna, Barbara, Jerzy, Magdalena, Wojciecha, Cezarego, Marek), nazwiska rzadkie/spoza PESEL≥100
(Kol*******, Saf***, Dzi*********, Saw****, Bet****), obce osoby i firmy (część z nich to dawne FP starego silnika: „Art”, „Rady”,
„Tom”, „Przystępującego”, „Odwołującego”, „Powódka”, CAPS „PODATEK/DO/MIASTA” — te utraty są pożądane).
**Dodane (wybór):** FP „Data” 50 (nagłówek „Data:”), „Zasada/Zasady/Zasadą” 21, „Górze” 7, „Wojewódzkiego” 7, „Konieczne” 5,
„Szczecinie/Szczecina” 6, „Niemcy” 4, „Kraj”, „Tryb”, „Kara”, „Skarb”; trafienia — prawdziwe nazwiska bez spaCy (Mas******* ×14,
Zaj** ×4, Pyz***-Sza******* …).
**R1 (on):** „Do” 155, „Skoro” 71, „Składanie” 17 — rzadkie nazwiska PESEL 100–999 na początku zdania → ASK (śmieci).

## Diagnoza
1. **spaCy jako „słaby dowód” (tabela §2: „sam spaCy PER → PASS”) gubi osoby.** W praktyce spaCy był głównym źródłem trafień dla
   osób spoza słowników: samotne imiona, nazwiska <100 nosicieli, obce, pary z imieniem spoza `names_inflected`. Decyzja §2 widzi
   tylko słowniki i kontekst → GOLD ciche 1→16 / 0→36.
2. **Próg 1000 bez kontekstu daje FP** w nagłówkach/etykietach i formach geograficznych („Data:”, „Zasada”, „Szczecinie”, „Niemcy”).
3. **ASK 100–999 bez kotwicy na początku zdania** zalewa Guarda słowami funkcyjnymi („Do”, „Skoro”) — w PESEL istnieją takie nazwiska.

## Wniosek (do korekty Architekta przed jakąkolwiek dalszą pracą)
Jedno miejsce decyzji — tak; **tabela §2 wymaga korekty**: (a) span PER spaCy obejmujący ≥2 słowa z wielkiej litery (para) = mocny
dowód jak para słownikowa; samotne słowo spaCy + jeden sygnał (imię z listy / Morfeusz imię-nazwisko / czasownik osoby) = MASK albo ASK,
nie PASS; (b) słownik bez kotwicy na początku zdania/linii i w etykietach („Data:”) — nie MASK; (c) ASK 100–999 tylko w środku zdania,
nie dla słów funkcyjnych (Morfeusz: prep/conj/qub/adv). Wtedy spaCy wymaga dostarczenia spanów PER do decydera (dziś ich nie ma na
finalnym tekście — trzeba albo przenieść spany przez warstwy, albo uruchomić spaCy ponownie na finalnym tekście; koszt czasu do oceny).
Bez tego E2 = regresja. Kod zostaje za przełącznikiem off; nic nie łatane po wynikach (brief §5).
