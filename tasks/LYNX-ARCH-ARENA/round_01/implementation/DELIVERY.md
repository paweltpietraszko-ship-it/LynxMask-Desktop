# LYNX-ARCH-ARENA v0.1 — DELIVERY r1 (CC)

Kod: `4a1cbf0` na gałęzi `experiment/lynx-architecture-arena` (brief r2 `73f5868`, CASES `b684434`, Codex PASS PREIMPLEMENTATION `c31fd97`). Eksperyment bez merge. Pipeline i API nie importują modułu.
Rozmiar: Paweł zaakceptował przed kodem „około 480 linii” („tak”, 19.10). Faktycznie `arena_sim.py` 240 + `test_arena_sim.py` 162 = 402. Ataki CC leżą w `tasks/` jako artefakt.

## Uruchomienie
- `cd backend && py -3 arena_sim.py` — STDIN JSONL, STDOUT JSONL, jedna linia na przypadek, bez innych komunikatów.
- Testy: `cd backend && py -3 -m pytest tests/test_arena_sim.py -q` (plik jawny, spoza `pytest.ini`).
- Ataki CC: `py -3 tasks/LYNX-ARCH-ARENA/attacks/attacks_cc_r1.py` (z katalogu repo).

## Implementacja (zgodnie z A–F briefu r2)
- **A BASE:** walidacja: `int` (bez `bool`), `0 ≤ start < end ≤ len`, `kind` z taksonomii, `evidence` jako lista. Duplikaty spanu i typu scalane, dowody liczone raz. Tekst z tokenem (wzorzec S2 z `(?!\d)`) → `STOP/TOKEN_INJECTION`.
- **B/C ANCHOR na ORYGINALE:**
  - `@`: lewy i prawy fragment, odcięcie końcowych `.`/`,`, jeden ogon „spacje + `.` + 2–4 litery”. Brak znaku alfanumerycznego tuż po `@` → `ANCHOR_UNCERTAIN`. Nakładające się, nieidentyczne spany dwóch `@` → `AMBIGUOUS`.
  - `ul.`: na początku tekstu albo po znaku niealfanumerycznym, potem ≥ 1 spacja/tab, 1–3 człony `[alnum][alnum-/]*`, koniec przed `, ; : ! ? .` i nową linią. Brak członu → `ANCHOR_UNCERTAIN`.
- **D ARBITER:** sortowanie po `(start, end, kind)`, scalenie dokładnych duplikatów. Różne typy nachodzą → `AMBIGUOUS`. Ten sam typ: zawieranie dozwolone tylko, gdy większy pochodzi z kotwicy, a mniejszy z BASE; w przeciwnym razie, także przy częściowym nakładaniu, `AMBIGUOUS`.
- **Decyzja CC w luce briefu:** kotwica, której span leży w całości WEWNĄTRZ szerszego BASE tego samego typu, jest „zakryta” („szuka niezakrytych kotwic”) i odpada z decyzją `anchor_covered`, a BASE zostaje. Bez tej decyzji szerszy, poprawny adres z BASE (np. z kodem i miastem) dawałby STOP. Opisane w nagłówku modułu, test X17.
- **E ONE APPLY:** numeracja według położenia. Ta sama dosłowna wartość dostaje ten sam token, różne zapisy dostają różne tokeny. Jedna podmiana od prawej.
- **F GUARD-DRON:** `AT_REMAINS`, `UL_REMAINS`, `ID_LABEL_REMAINS`. Tylko dla RENDERED, posortowane, bez wartości.
- **STOP:** `masked=null`, `tokens=[]`, `guard_flags=[]`. `trace` zawiera tylko pola `phase`, `kind`, `start`, `end`, `decision`. Wyjątek → `INTERNAL_ERROR` bez treści. Niepoprawny JSON lub pola → `INVALID_INPUT` bez echa tekstu.
- Kody `reason_code`: `INVALID_INPUT`, `TOKEN_INJECTION`, `ANCHOR_UNCERTAIN`, `AMBIGUOUS`, `INTERNAL_ERROR`.

## Wyniki testów (CLI, osobny proces) — 38 passed
- **Mechanika A01–A16 zgodna z tabelą prognoz r2 w 16/16:**
  - RENDERED: 14;
  - STOP: A10 (`AMBIGUOUS`) i A12 (`TOKEN_INJECTION`).
- **Ochrona liczona przez sędziego z gold (nie z prognozy):**

  | Wynik | Liczba | Przypadki |
  |---|---|---|
  | PROTECTION_PASS | 9 | A01–A05, A08, A09, A13, A14 |
  | SAFE_REFUSAL | 2 | A10, A12 |
  | PROTECTION_FAIL | 5 | A06 FP, A07 FN_PARTIAL, A11 FN_FULL, A15 FP, A16 FN_FULL na PESEL |
  | UNEXPECTED_STOP | 0 | — |

- **Guard-dron:**
  - A11 i A16: `ID_LABEL_REMAINS` → GUARD_FLAGGED;
  - A07: brak flagi przy osieroconym kodzie i mieście → GUARD_MISSED;
  - A06 i A15: brak flag, bo kotwice zamaskowane, a FP to inna klasa.
- **Niezmienniki:**
  - N1: poza spanami tekst 1:1;
  - N2: brak tokenu w środku wyrazu;
  - N3: roundtrip mapą = oryginał;
  - N4: `original == text[s:e]`;

  dla wszystkich RENDERED.
- **Pozostałe sprawdzenia:**
  - metamorfizmy: 5 permutacji kandydatów z innymi `source`, duplikat z innymi dowodami, powtórka w tym samym procesie → identyczny wynik (determinizm);
  - trace bez wartości;
  - 7 niepoprawnych wejść → `INVALID_INPUT` bez echa znacznika i bez stderr;
  - `ala@ ` → `ANCHOR_UNCERTAIN`.
- `ruff`: 0. Gate:
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 4a1cbf093c3f489ef119ba2f0058358b01069da2
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 402 lines changed (threshold 150)
```
(w ramach zgody Pawła na ok. 480).

## Ataki CC r1 (`attacks/attacks_cc_r1.py`, 19 syntetyków, gold ustalony przed uruchomieniem)
Wynik: **PASS 5, FAIL 8, UNEXPECTED_STOP 5, SAFE_REFUSAL 1.**

| Id | Wynik | Co pokazuje |
|---|---|---|
| X01 | UNEXPECTED_STOP (AMBIGUOUS) | lista e-maili bez spacji `a@b.pl,c@d.pl`: przecinek dozwolony w domenie → spany kotwic nachodzą → odmowa całego dokumentu |
| X02 | UNEXPECTED_STOP (ANCHOR_UNCERTAIN) | „Spotkanie @ 10:00” — zwykłe `@` bez PII blokuje cały dokument |
| X09 | UNEXPECTED_STOP (AMBIGUOUS) | „ul. Jana Kowalskiego 5” + NER widzi osobę → ADRES/OSOBA nachodzą |
| X10 | UNEXPECTED_STOP (AMBIGUOUS) | „Kowalski i Wspólnicy Sp. z o.o.” — OSOBA wewnątrz FIRMA |
| X18 | UNEXPECTED_STOP (AMBIGUOUS) | dwa detektory z nakładającymi się spanami osób w sklejonej liście |
| X03, X04, X15 | FAIL (FN_PARTIAL) | OCR-spacja w części lokalnej / po kropce domeny; NFD (znak łączący) ucina e-mail |
| X05, X06 | FAIL (FN_PARTIAL) | „ul. Jana Pawła II 5” (limit 3 członów), „ul. Św. Marcin 5” (kropka w nazwie) |
| X07, X08 | FAIL (FN_FULL), Guard milczy | „al.”, „ul” bez kropki — brak kotwicy i flagi |
| X12 | FAIL (FP) | „@jan_kowalski” jako EMAIL |
| X13 | PASS, ale GUARD_FP | „ul.” na końcu tekstu — flaga bez PII |
| X11 | SAFE_REFUSAL | NER na części lokalnej e-maila (jak A10) |
| X14, X16, X17, X19 | PASS | kontrole pozytywne (X19: różna wielkość liter → dwa tokeny, zgodnie z v0.1; dla K2 to jedna osoba) |

## Wnioski CC dla Architekta (nie zmieniam reguł — to jego decyzja w nowej wersji)
1. **Reguła D „różne typy nachodzą → STOP” jest najsłabszym punktem.** Najczęstsze układy realnych pism (osoba w nazwie firmy, ulica z nazwiskiem, sklejone listy osób z dwóch detektorów) kończą się odmową CAŁEGO dokumentu. W produkcie to nieużywalne. Potrzebna jest reguła zawierania między typami (np. FIRMA ⊃ OSOBA → FIRMA, ADRES ⊃ OSOBA → ADRES) albo odmowa ograniczona do fragmentu. Arena v0.2 na realnych wykryciach (`LYNX-ARCH-ARENA-REAL`) pokaże częstość.
2. **STOP dokumentu przy pojedynczej niepewnej kotwicy** (X02 `@` bez PII, X01 lista e-maili) jest zbyt kosztowny. Lepiej pozostawić fragment i oddać flagę.
3. **Kotwice są wąskie:** brak `al.`/`os.`/`pl.`, `ul` bez kropki, kropki w nazwach ulic, limit 3 członów, NFD. Guard-dron nie łapie tych resztek.
4. **Arena nie dotyka osób i firm** poza konfliktami podanymi z zewnątrz. Główna klasa wycieków z diagnozy pozostaje nieprzetestowana.

## Prośba do Codexa
Zamroź `4a1cbf0`, uruchom CLI w osobnym procesie, niezależnie sprawdź gold A01–A16 i moje ataki, dodaj ≥ 5 własnych prób (≥ 2 nieujawnione), przetestuj metamorfizmy z briefu. Bez merge.

---

# DELIVERY r2 (CC) — v0.1.1: poprawka F1 z audytu r4 (`67413a9`)

Kod: `ab38719`. Diff względem v0.1 (`4a1cbf0`): `arena_sim.py` +13, `test_arena_sim.py` +13.

- **F1 (N2):** po arbitrze każdy przyjęty span, którego początek lub koniec wypada w środku wyrazu (znak wyrazu po obu stronach granicy; znaki wyrazu to alfanumeryczne, `_` i znaki łączące NFD), daje `STOP/WORD_BOUNDARY`. Odmowa zamiast sklejonego tokenu. Spanu nie poszerzam i nie zgaduję całej osoby z fragmentu, zgodnie z oczekiwaniem r4. Kod `WORD_BOUNDARY` dopisany do stabilnej listy w nagłówku.
- **Reproduktor Codexa** („Jan Kowalski”, OSOBA [0,2) i [1,3)): oba `STOP/WORD_BOUNDARY`, a pełny span [0,12) daje RENDERED „OSOBA_001”. Nowy test `test_granica_w_srodku_wyrazu_to_odmowa_nie_sklejenie`.
- **Testy:** 39 passed. A01–A16 bez zmian (16/16 mechaniki, ochrona 9/5/2).
- **Ataki CC r1:** PASS 5, FAIL 7, UNEXPECTED_STOP 6, SAFE_REFUSAL 1. Zmiana tylko w X15 (NFD): dotąd FAIL z jawnym fragmentem i sklejonym tokenem, teraz `STOP/WORD_BOUNDARY`. Gramatyka kotwicy @ (brief C) nie obejmuje znaków łączących w lewym fragmencie, więc uczciwą reakcją jest odmowa, a nie sklejenie.
- **Bez zmian:** kotwice, arbiter D, Guard; v0.1 (`4a1cbf0`) zostaje punktem odniesienia. Dalszy rozwój (REAL, R2/R3) dopiero po krótkim kontrakcie Architekta, zgodnie z `595af42` i opinią r4.

---

# DELIVERY r3 (CC) — v0.1.2: reszta F1 z r5 (`a5b562b`)

Kod: `dc149cd`. `_word_char` liczy znak jako część wyrazu, gdy jest alfanumeryczny, jest `_` albo ma **kategorię Unicode M** (`unicodedata.category(ch).startswith("M")`). Wcześniej warunkiem było `combining(ch) > 0`, które pomijało Mn z klasą łączenia 0 (U+034F).
- Nowy test `test_znak_m_o_klasie_laczenia_zero_tez_jest_czescia_wyrazu`: 40 passed.
- `repro_r5.py` Codexa: wszystkie 7 przypadków → STOP (wcześniej RENDERED).
- Poza tym predykatem bez zmian.
