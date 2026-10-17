# PROPOSAL 2026-10-17 — warstwa kontekstowa (kotwice) dla osób, bez AI

Autor: CC, po rozmowie z OWNEREM 2026-10-17 („LynxMask nie ma żadnej warstwy wykrywającej PII z kontekstu.
Czy to możliwe bez używania AI?” → „Tak, dopisz bo to ważne”). Propozycja do oceny, nie decyzja
(`AGENTS.md` → OWNER_INPUT_IS_A_PROPOSAL). Status w `BOARD.md`: LYNX-CONTEXT-ANCHORS.

## 1. Stan

Kontekst wykorzystują dziś: spaCy NER (statystyczny, lokalny), wzorce z etykietą (NIP:, sygn., ul.) i propagacja odmian
już wykrytej osoby (`ner_adapter._propagate_osoba`). Brakuje reguł, które wskażą osobę, gdy spaCy jej NIE wykrył,
a kontekst mówi to wprost. Mobile ma taką warstwę (`AnchorEngine.kt`, W4b — `arch/FINDING_2026-10_MOBILE_PORT.md` §3).

## 2. Propozycja (port wybiórczy, nie cały AnchorEngine)

Kotwica → następne 1–3 słowa z wielkiej litery → Morfeusz potwierdza rzeczownik (nie przymiotnik/nazwę pospolitą
w znaczeniu ogólnym) → token OSOBA przez `allocator.assign()` (T03), tylko na resztkach tekstu (po wszystkich warstwach):

- **tytuł/forma grzecznościowa:** Pan/Pani/Panu/Pana…, mec., adw., r.pr., dr, prof., inż., lek. (MOBILE_PORT: A.10);
- **rola w piśmie:** dłużnik, wierzyciel, wnioskodawca, pracownik, pacjent, pełnomocnik, świadek, najemca, zleceniobiorca…;
- **pola formularza:** „Imię i nazwisko:”, „Nazwisko:”, „Zamieszkały/a:”, „Podpis:”, „ur.” + data (A.7);
- **propagacja na cały dokument:** osoba potwierdzona kotwicą w jednym miejscu → wszystkie jej formy (Morfeusz) w całym
  dokumencie, także bez kotwicy.

Spełnia kierunek D2 z `arch/PROPOSAL_2026-10-16_SLOWNIK_SZCZELNOSCI.md` („Zając” jako słowo zostaje, „Pan Zając” — maskowany),
którego bez reguł kontekstowych nie da się zrealizować.

## 3. Uzasadnienie i granica

- Plan (`arch/PLAN_2026-10.md` p.15) odłożył P05 ANCHOR-LAYER: „+1 encja / +31 FP” na benchmarku. Benchmark praktycznie nie ma
  zdań z kotwicą, w których spaCy zawodzi, więc nie mógł pokazać zysku (to ograniczenie miary, nie dowód braku zysku).
- Szacunek z pomiaru T01 (holdout 120 nazwisk spoza słownika): z 50 pozostałych wycieków ~11 to „Pan X ma L4” (kotwica tytułu);
  reszta („dla X”, „czemu X nie dano”) — bez kotwicy, poza zasięgiem reguł (tam: spaCy, słownik, ewentualnie douczenie — `ODLOZONE.md`).
- Granica świadoma: reguły nie złapią nazwiska bez kotwicy („rozmawiałem z Zającem”).

## 4. Warunki (proponowane do briefu)

1. Najpierw pomiar M1/M2 z LYNX-DICT-LEAKTEST (`arch/PROPOSAL_2026-10-16_SLOWNIK_SZCZELNOSCI.md` §6) — M1 ma osobne warianty
   „tytuł przed nazwiskiem” i „rola + nazwisko”, więc pokaże zysk przed/po; FP mierzone na zbiorze bez PII (M2).
2. Tokeny wyłącznie przez wspólny alokator (T03); żadnego własnego licznika.
3. Bez „Rundy 2” Mobile i bez kotwic zachłannych, które w Mobile dawały FP (MOBILE_PORT: A.5b, A.8kw).
