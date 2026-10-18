# LYNX-MAP-FIDELITY — DELIVERY r1 (CC)

Gałąź `task/LYNX-MAP-FIDELITY`: brief architekta `5aa70b6` (PASS PREIMPLEMENTATION `760f362`), zsynchronizowana z main (`9fe2037`), ROZSZERZENIE CC w briefie `ea1abb6` (identity — przed kodem identity). Kod: `831a5d8`. Baza gate: `6389c33`.
Ocena CC briefu: zgoda; brief lepszy od propozycji (Decimal, zakaz zgadywania przy niejednoznacznym zapisie, jawne K2 NOT_FIXED).

## Zmiany (kod produktu +56/−17)
- **D1 `pipeline_core.py`** (+32/−3): `_value_key(value, token_type)` — klucz deduplikacji po wartości, użyty spójnie w `assign` i `register` (także kontrola kolizji `[TOKEN-COLLISION]`). KWOTA: `Decimal` + waluta; separator z 1–2 cyframi na końcu = dziesiętny, z 3 cyframi = tysięcy; zapis nierozpoznany → klucz = dokładny zapis (nie scalany z inną liczbą). NUMER: każda data `d.m.rrrr` (także wewnątrz wartości, np. „ur. 2.11.2023”) zamieniana na `#d:m:rrrr#` przed dotychczasową kanonizacją (`:`/`#` nie są kasowane). Identyfikatory, osoby, firmy, adresy — bez zmian. `amount.py` niezmieniony.
- **D2 `layers/ner_adapter.py`** (+19/−7): `_whole(value)` = wartość jako cały wyraz (`(?<!\w)…(?!\w)`); użyte w obecności (`_remap_ner_ids`, pętla wariantów) i w podmianie (główna pętla, warianty); łącznik jest granicą (nadmaskowanie „OSOBA_001-Kowalski” zamiast jawnego „Pyziak-Szafnicka” — zgodnie z polityką Pawła). Podmiana od najdłuższej wartości („Izby” nie w środku „Krajowej Izby Odwoławczej”). `apply_ner_layer` bez wzrostu (83). Propagacja nazwisk — wzorce bez zmian (`\b`).
- **D2 `layers/address.py`** (+1/−1): lewa granica `_ADDR_RE` — „Szpital Wojewódzki 5” nie jest „al. Wojewódzki 5”.
- **D2 `layers/identity.py`** (+2/−1, ROZSZERZENIE CC): numer nie jest wycinany ze środka dłuższego kodu (znak po nim litera/cyfra albo „_” przed nim); litera PRZED numerem nadal dozwolona („PESEL44051401359” maskowany).
- **D3 `ner_layer.py`** (+2/−5, 600 → 597 linii): bez zwijania białych znaków w wartości encji (dosłowny span); z końca wartości odcinany także otwierający cudzysłów „ “ i spacja („Agencja Usługowa „” → „Agencja Usługowa”).

## Testy
`backend/tests/test_map_fidelity.py` (nowy, 153 linie, jawnie): **main 17 failed / 5 passed** (5 = strażnicy już poprawnych przypadków) → **gałąź 29 passed**. Obejmuje: alokator (różne/te same kwoty, daty, daty w wartości, NIP), `register` (kolizja po wartości), dokument Full i Express z różnymi kwotami/datami (4 tokeny, Przywróć 1:1), całe wyrazy (Nowak/Nowakowska, Sąd/Sądu, Nowak-Kowalski, Pyziak-Szafnicka, cudzysłów, krótsza firma w dłuższej), lista osób z przecinkami (bez propagacji listy — interpelacja 1739), identity w kodzie „ocds-…”, „S_…” oraz „PESEL44051401359”, adres w „Szpital…”, spacje/tab w osobie (podstawiony NER i prawdziwy Full).
Regresje: `test_layers` + `test_ner_multiline` + `test_text_limit_15k` + `test_audyt_2026_10` + nowy: 310 passed, 10 xfailed; `tests/` z działającym backendem z gałęzi: 167 passed, 2 skipped, 1 xfailed. `ruff`: bez nowych uwag (identity.py — 3 istniejące W605).

## Pomiar: 178 dokumentów `dataset_real_public` przez działający `/preview` (profil biura Pawła)
Baza: backend z main `6389c33`; gałąź: backend z `831a5d8`, ten sam profil (`ANONYMIZER_PROFILE_DIR`), osobny `ARCHIVE_DIR`.

| | baza | gałąź |
|---|---|---|
| sklejone tokeny (token przyklejony do litery/cyfry) | 33 w 17 dok. | **1 w 1 dok.** |
| blokady Guarda | 59 | 59 (0 nowych, 0 zdjętych) |
| dokumenty z Przywróć = wejście | 47 | 47 (0 pogorszonych) |
| tokeny KWOTA / NUMER | 640 / 921 | 618 / 913 (ta sama wartość w innym zapisie scalona) |
| tokeny łączące >1 zapis (pomiar w procesie, pusty profil) | 86 | 106 |
| w tym łączące RÓŻNE wartości KWOTA/NUMER | 0 | **0** |

Nowe jawne słowa (porównanie wyników): wyłącznie wyrazy pospolite, które wcześniej „zakrywał” token wbity w ich środek — Szpitala, Szpitalowi, Rezydenta, Konsorcjum, OpenOffice, X86_64. Żadna osoba.
Pozostałe sklejenie: „2012/S_239-394253” → „S_NUMER_018” (KIO_122113) — nie pochodzi z warstw nowej ścieżki (sprawdzone warstwa po warstwie), lecz z legacy `anonymizer.py` (warstwa regex) — poza TASK_SCOPE; numer ogłoszenia TED, nie PII → finding.

Wersje pośrednie (dla audytu): (a) łącznik jako część wyrazu w `_whole` i propagacji → jawne „Pyziak-Szafnicka”, a propagacja członu z przecinkiem („Suchoń,”) wpisywała token sklejonej listy w obcym miejscu (Przywróć ≠ w interpelacji 1739) — wycofane: propagacja z oryginalnym `\b`, łącznik = granica; (b) podmiana według pozycji → „Izby” w środku „Krajowej Izby Odwoławczej” — teraz najdłuższe najpierw.

## Ograniczenia (NOT_FIXED, zgodnie z briefem)
- K2: kilka zapisów tej samej wartości pod jednym tokenem — Przywróć oddaje zapis z mapy (np. „3700 zł” zamiast „3 700 zł”).
- Lista osób sklejona w jeden token (C3) — bez zmian.
- Legacy `anonymizer.py` — jedno sklejenie (wyżej).
- Uruchomienie testów HTTP z innego katalogu niż backend wymaga aktualnego `api_token.txt` (pomocnik testowy przy 401 zwraca surowy tekst — nie produkt).

## Gate (dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 831a5d8cc1c1c25f0b29f52b8911940c02c8928a
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 209/17 = 12.3:1 (threshold 5:1)
  - TOTAL_LINES: 226 lines changed (threshold 150)
```
153 z 226 linii to nowy test; kod produktu 56+17. Pliki przy limicie nie rosną (`ner_layer.py` 600 → 597). Wymaga decyzji Pawła.

---

# DELIVERY r2 (po FAIL r2 Codexa `3fee4af`, F1 — precyzja Decimal)

Kod: `793e1da`. F1 potwierdzony: `Decimal(...).normalize()` używa kontekstu wątku (28 cyfr znaczących) → różne kwoty o ≥29 cyfrach dostawały jeden klucz. Poprawka: klucz kwoty budowany wprost z cyfr, bez arytmetyki — część całkowita bez zer wiodących, część dziesiętna bez zer końcowych (`kwota:<cyfry>.<ułamek>:<waluta>`); import `Decimal` usunięty. Brief („bezstratnie, bez float”) spełniony bez zależności od kontekstu.

Przegląd rodziny `round_01/implementation/amount_sweep.py` (nowy): 26 100 próbek — losowe kwoty 1–40 cyfr w różnych zapisach (spacje/kropki tysięcy, kropka/przecinek dziesiętny, zera końcowe, zł/PLN) + pary celowane różniące się dopiero ostatnią cyfrą (20–45 cyfr); wyrocznia: dokładne `Decimal(str)` bez zmiany kontekstu. **Kod r1: 34 kolizje różnych wartości; poprawka: 0 kolizji, 0 rozbić tej samej wartości.** (Pierwsza wersja przeglądu ustawiała globalną precyzję 200 i przez to nie widziała błędu r1 — poprawione, opisane w nagłówku skryptu.)
Test: `test_kwoty_ponad_precyzje_decimal` (alokator + Full + Express, Przywróć 1:1) — na kodzie r1 2 failed, na r2 passed. `test_map_fidelity.py` 31 passed; regresje (`test_layers`, `test_ner_multiline`, `test_text_limit_15k`, `test_audyt_2026_10`) 281 passed, 10 xfailed.
Pomiar 178 dokumentów z r1 obowiązuje bez zmian: zmiana dotyczy wyłącznie kwot ≥29 cyfr znaczących (brak takich w zbiorze; klucz dla krótszych kwot identyczny co do równości).

Gate r2 (dosłownie):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 793e1dac7b30bd7b0dc6b82c45974796279405ff
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 221/17 = 13.0:1 (threshold 5:1)
  - TOTAL_LINES: 238 lines changed (threshold 150)
```
Kod produktu +55/−17 (166 linii to test). Rozmiar — decyzja Pawła.

**OWNER_ACCEPTED 2026-10-18 (Paweł, dosłownie):** „Potwierdzam rozmiar” — dotyczy gate WYMAGA_DECYZJI tej dostawy (TOTAL_LINES 238, RATIO 13:1; 166 linii to test).
