# DELIVERY — LYNX-ARENA-SIGNALS-PILOT (CC, runda 1)

Gałąź: `task/LYNX-ARENA-SIGNALS-PILOT`. Kod: `ad3b6bcb5f211f93cbd1a9105df336d7313b3375`. Bez zmian produktu, bez merge.

## Przed kodem
- Review briefu `2ebdf1e`: przyjęty. Jedna korekta bazy: gałąź odchodziła od stanu sprzed `cfe8eb7` (ADDR-EMAIL-LEAKS), więc mierzyłaby nieaktualne `layers/address.py` i `layers/contact.py`. Za zgodą Pawła scalono `origin/main` do gałęzi (`add92f3`); `arena_sim.py`, `arena_v02.py` i ich testy bez zmian wobec `4c75236` (sprawdza test `test_frozen_arenas_unchanged`).
- Szacunek ~450–550 linii, zgoda Pawła przed kodem. Wyszło 585 (o ~6% ponad górną granicę szacunku).

## Gate (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: ad3b6bcb5f211f93cbd1a9105df336d7313b3375
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 585 lines changed (threshold 150)
EXCLUDED_ARTIFACTS: NONE
```
Polecenie: `py -3 gate.py tasks/LYNX-ARENA-SIGNALS-PILOT/brief.md add92f3 ad3b6bcb5f211f93cbd1a9105df336d7313b3375 <out>`.

## Co powstało (2 pliki z TASK_SCOPE)
- `backend/arena_signal_probe.py` (341 l.) — offline, read-only. Źródła osobno na oryginale, świeży `PipelineState`:
  - `identity` / `contact` / `address`: lokalna subklasa `TokenAllocator` zapisuje udane `allocate` (start, end, kind). **Dowód offsetu:** zapis odtworzony na oryginale musi dać bajtowo tekst wyjściowy warstwy; inaczej `MAPPING_ERROR`. Raw literal (`original[start:end]`) odróżniony od kanonicznego `value` (licznik `canonical_differs`).
  - `SPACY_DIRECT`: `spacy_ner.detect_entities(original)`; `original[start:end] != text` (skrócona wielowierszowa OSOBA) → `MAPPING_ERROR`; inne całowyrazowe wystąpienie wartości poza spanami (deduplikacja wrappera) → `ADAPTER_UNSUPPORTED`; brak modelu → `MODEL_UNAVAILABLE`; wyjątek → `DETECTOR_ERROR`.
  - Źródło nie-OK: gold jego typów dostaje `SOURCE_<kod>` (poza mianownikiem), Areny dla próby `NOT_RUN`.
  - Ta sama lista (kopia JSON, kontrola niezmienności) do R1=strict i R2=structured przez `arena_v02.run_case`.
  - Gold: `EXACT_CANDIDATE / WRONG_KIND / BAD_SPAN / NO_CANDIDATE / COVERED_BY_PARENT`; Areny: `ARBITER_STOP`, `ARBITER_DISCARDED`, dla RENDERED `fn` (gold całkiem widoczny), `fn_partial` (część znaków widoczna), `split` (zakryty kilkoma tokenami), `fp`, `overmask`, N1–N4/roundtrip. Czas na źródło i wariant. Raport: tylko liczniki i id.
  - CLI: `py -3 arena_signal_probe.py < proby.jsonl` (`{"id","text","gold":[{"start","end","kind","parent"?}]}`), wyjście bez tekstu; złe wejście → `INVALID_INPUT`, kod 2, bez echa.
- `backend/tests/test_arena_signal_probe.py` (244 l.) — 12 syntetyków S01–S12, gold przy składaniu z bloków (zagnieżdżenia przez offset w bloku, nie `.find`).

## Testy
```
cd backend
py -3 -m pytest tests/test_arena_signal_probe.py -q -s     → 16 passed
py -3 -m pytest tests/test_arena_sim.py tests/test_arena_v02.py -q   → 45 passed
py -3 -m ruff check arena_signal_probe.py tests/test_arena_signal_probe.py   → All checks passed!
```
Raport pilota drukuje `test_pilot_report_aggregates_only` (linia `PILOT_REPORT`). SpaCy: **dostępny** (`pl_core_news_lg`), status OK w 11/12, ADAPTER_UNSUPPORTED w 1/12.

## Wyniki (12 syntetyków, czysty tekst, detektory = main `90202d3`)
| Gold (24 pozycje) | n |
|---|---|
| EXACT_CANDIDATE | 11 |
| BAD_SPAN | 8 |
| NO_CANDIDATE | 2 |
| COVERED_BY_PARENT | 1 |
| SOURCE_ADAPTER_UNSUPPORTED (poza mianownikiem) | 2 |

| Wariant | RENDERED | STOP | NOT_RUN | arbiter_stop | arbiter_discarded | fn | fn_partial | split | fp | overmask | N1–N4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 strict | 10 | 1 (AMBIGUOUS) | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 0 |
| R2 structured | 10 | 1 (AMBIGUOUS) | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 0 |

Konflikty kandydatów: 1. Czas łącznie: SpaCy ~85 ms, warstwy regex ~0,4–1,2 ms; Areny ~1–2 ms.

## Największe zaobserwowane źródła strat (bez nowej architektury)
1. **Granice SpaCy (detekcja, nie arbiter).** Lista trzech osób oddzielonych przecinkami → jedna OSOBA (3× BAD_SPAN, overmask bez wycieku); firma „… S.A.” ucięta na „S.” + „A.” jako OSOBA (split, bez wycieku); firma z nazwiskiem rozbita na OSOBA + FIRMA bez spójnika (fn_partial); nazwisko w NFD niewykryte (fn); słowo „PESEL” jako OSOBA (fp).
2. **Szerokość spanów NUMER.** `contact` obejmuje etykietę „tel.” (3× BAD_SPAN, bez wycieku), a reguła OCR `identity` (10 cyfr ze spacjami) łapie cyfry numeru telefonu wewnątrz spanu `contact` → konflikt tego samego typu BASE⊂BASE → **STOP/AMBIGUOUS w obu Arenach** (jedyny STOP).
3. **Ograniczenie wrappera SpaCy (adapter).** Deduplikacja wartości → próba z powtórzeniami `ADAPTER_UNSUPPORTED`, Areny `NOT_RUN` (2 gold poza mianownikiem) — zgodnie z uwagą Codexa, bez naprawy wrappera.

Obserwacje dodatkowe: R1 i R2 dały identyczne wyniki — na tych rzeczywistych kandydatach nie pojawiło się zawieranie różnych typów, więc reguła R2 nie została w ogóle wywołana. Kotwica `@` Areny zamaskowała ucięty e-mail, którego nie zgłosił żaden detektor (NO_CANDIDATE, ale bez FN). Przypadek H1 (fałszywie szeroka FIRMA) nie wystąpił z rzeczywistego SpaCy; test H1 na podanych ręcznie kandydatach nadal pokazuje R2 RENDERED z overmask i odrzuconą osobą (falsyfikacja utrzymana).

## Ograniczenia
- 12 syntetyków diagnozuje metodę i klasy strat, nie jakość aplikacji ani OCR. Bez danych rzeczywistych.
- `fn` liczy znaki gold widoczne po masce (spacje pomijane); dokładne kryteria w docstringu `_render_counts`.
- `SOURCE_KINDS` (które typy gold blokuje awaria źródła) to stała deklaracja w module.
