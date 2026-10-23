# LYNX-FORMATS-PACK2 — DELIVERY r1 (CC, 2026-10-21)

Brief `acfeaf8`, Codex BRIEF_ONLY PASS `baf1716`. Baza main `10e62d95ecfa3d408d6ac3413056854ff425aece`, kod HEAD
`25f3b35614b29081f57a3f0905802e30f40203ab`.

## Zmiany
- `backend/layers/amount.py`: `_DATE_ISO_RE` — RRRR-MM-DD, lata 19xx/20xx (jak `_DATE_PL_RE`), miesiąc 01–12, dzień 01–31, bez cyfry/„-”
  przed i bez cyfry/„-cyfra” po (bez fragmentu z „1989-01-05-001”); NUMER, sama data.
- `backend/firma_context.py`: `_FORM_SCAN_RE` (forma z kropką po „sp”: sp.z o.o., sp.k.a., sp.j./k./p., p.s.a.) + `scan_legal_forms` —
  kandydat FIRMA „nazwa + forma” z `_name_start`, tylko gdy nie nakłada się na encję spaCy i nazwa istnieje.
- `backend/ner_layer.py` (596 → 597 l.): import + `_firma_entities` dołącza `scan_legal_forms` po `_firma_bounds`, przed `legal_form_entities`.
- `backend/layers/ocr_normalizer.py` (696 l., bez wzrostu): krok 13 (cyfra 1/0 → litera) tylko w słowach z małą literą albo ≥ 9 znaków;
  `_UL_PREFIX_RE` nie po cyfrze.
- `backend/tests/test_formats_pack2.py` (nowy, 19 testów).

**Korekta opisu w briefie:** brief twierdził, że WIELKIE nazwiska z cyfrą („KOWA1SKI”) były naprawiane — na main krok 13 zamieniał je
na „KOWAiSKI” (nie naprawa), krok 15 (`_de_leet`) obsługuje formy ze słownika („K0WALCZYK” → „KoWALCZYK” przed i po). r2: słowa CAPS
≥ 9 znaków normalizowane jak przed zmianą (regresja z pomiaru r1, niżej); krótsze CAPS (tablice, kody KW) zostają.

## Bramka (stdout dosłownie, `gate_r2.txt`)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 25f3b35614b29081f57a3f0905802e30f40203ab
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 100/5 = 20.0:1 (threshold 5:1)
```
RATIO: nowe reguły i testy; łącznie < 150 linii.

## Testy
`test_formats_pack2.py` 19 passed. Regresja (`test_layers test_pipeline_v2 test_audyt_2026_10 test_map_fidelity
test_pipeline_adversarial test_firma_context test_amounts_numbers`): 4 failed — te same 4 co na main (`LYNX-ENGINE-BACKLOG`).
`TestFirmaBounds` („Kowalski i Wspólnicy Sp. k.” — jedna FIRMA) przechodzi.

## Pomiar (pomocnik CC; lokalnie `%TEMP%\lynx_cc_review\plpii_pack2\`, `mobile_compare_pack2\`)
**r1 (`bde77c4`) — regresja z pomiaru:** `testy/test_ocr_normalizer_hard.txt` „Podpisano: BARTOSZ JAB1OWSKI” — po r1 OSOBA tylko
„BARTOSZ”, nazwisko jawne (krok 13 nie normalizował CAPS). r2 (`25f3b35`): plik identyczny jak na main (OSOBA „BARTOSZ JABiOWSKI”).
Uwaga: samo zdanie „Podpisano: BARTOSZ JAB1OWSKI” bez kontekstu — nazwisko jawne **także na main** (backlog, nie regresja).

**`pl-pii-synthetic-v1` (3000 dok., 18 047 encji gold), main → r2:**
| etykieta | main zakryte / częściowo / jawne | r2 |
|---|---|---|
| DOB | 620 / 0 / 69 | 689 / 0 / 0 |
| ORG | 652 / 0 / 41 | 693 / 0 / 0 |
| PLATE | 544 / 12 / 1 | 557 / 0 / 0 |
| PASSPORT | 244 / 1 / 0 | 245 / 0 / 0 |
| CARD | 743 / 4 / 0 | 743 / 4 / 0 |
| RAZEM | 17 918 / 18 / 111 | 18 042 / 5 / 0 |
Nowe tokeny bez gold: 60 NUMER — data zdarzenia ISO „2020-11-05” w `neg_noise` (nadmaskowanie zgodne z regułą dla DD.MM.RRRR).
Zniknęły fałszywe: 14 FIRMA („FBR HKiJC” — tablice psute przez normalizator) i 2 OSOBA.

**Porównanie z Mobile (693 teksty), main → r2:** jedyna klasa > 3: „Mobile zakrył, Desktop nie” NUMER 149 → 136 (daty ISO). Numery KW
z „1” w kodzie wierne („LD1M/…”, wcześniej „LDiM/…” w mapie). Nowe FIRMA: „Usługi IT sp. z o.o”, „Doradztwo Biznesowe EXPERT Sp. z o.o”
(poprawne); usunięta fałszywa „London SWiA”. Brak łączenia dwóch firm, brak zwykłych słów jako FIRMA. Osoby gold `dataset_clean` bez zmian.
