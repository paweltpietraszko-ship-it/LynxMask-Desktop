# LYNX-AMOUNTS-NUMBERS — DELIVERY r1 (CC, 2026-10-21)

Brief `204e14e` + ROZSZERZENIE CC (tablica rejestracyjna przed „/cyfra”) i korekta zakresu testu `test_audyt_2026_10.py` (opis w briefie).
Codex BRIEF_ONLY PASS `e17e59f`. Baza main `cc70822d8356398a331799d6de4a30370476738f`, kod HEAD `d3f96740d80d0d68454ee02de559ed726655f097`.

## Zmiany
- `backend/layers/amount.py`: `_AMOUNT_WORD_RE` (cyfry + złotych/złote/złoty); `_AMOUNT_NOCUR_RE` (przecinek + 2 cyfry groszy, spacja/
  twarda spacja tysięcy; nie przy `%`, jednostkach, `/`, `-`, cyfrze/`.,cyfra` obok; `_not_amount_nocur`: nie po „wersja/wer./v” i nie
  wewnątrz kwoty z walutą); `_after_number_word`: `_AMOUNT_RE` i `_AMOUNT_WORD_RE` pomijane, gdy przed liczbą stoi liczebnik/mnożnik
  (bez „i”) — całą kwotę bierze `verbal_amounts` (warunek 3 Codexa: kolejność amount → verbal). `_apply_patterns` przyjmuje opcjonalny filtr.
- `backend/verbal_amounts.py`: `_CURRENCY_RE` + gołe „zł”; skan wstecz przyjmuje grupy `\d{1,3}`; `_has_number_word` — kwota słowna tylko
  z liczebnikiem/mnożnikiem (same cyfry → amount.py; samo „i” już nie tworzy kwoty). Długość `_mask_verbal_amounts` bez zmian.
- `backend/layers/numeric.py`: `_NUM_DOC_RE` + `_doc_number_span` — numer po „nr/numer” z cyfrą w samym numerze, separatorem albo ≥ 4
  znakami, nie częścią tokenu (`(?![_\w])`), słowo dokumentu w 60 znakach wstecz; maskowany sam numer.
- `backend/layers/legal.py`: `_CASE_SIG_RE` — `(?i:km|kmp|ko|kms)`.
- `backend/credential_patterns.json` (ROZSZERZENIE CC): wzorzec tablicy rejestracyjnej `(?!/\d)`.
- `backend/tests/test_amounts_numbers.py` (nowy, 20 testów); `backend/tests/test_audyt_2026_10.py`: kotwica „Faktura nr NUMER_001. Kontakt”.

## Bramka (stdout dosłownie, `gate_r2.txt`)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: d3f96740d80d0d68454ee02de559ed726655f097
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 137/11 = 12.5:1 (threshold 5:1)
```
RATIO: nowe reguły i testy, prawie nic usuniętego. Łącznie < 150 linii.

## Testy
`test_amounts_numbers.py` 20 passed; `amount.py` (wbudowany) 9 PASS, `legal.py` 15 PASS. Regresja (`test_layers test_pipeline_v2
test_audyt_2026_10 test_map_fidelity test_pipeline_adversarial` + amounts): 4 failed — te same 4 co na main `1f60c06`/`cc70822`
(`LYNX-ENGINE-BACKLOG`), reszta passed.

## Pomiar (pomocnik CC; porównanie z Mobile tym samym narzędziem, 693 teksty syntetyczne; Desktop z `git archive`, pusty profil)
**r1 (`16ff8b7`) — regresja wykryta pomiarem:** `_NUM_DOC_RE` brał słowo „NUMER” z istniejącego tokenu („Nr NUMER_005”) — Guard
zamieniał potem każde „NUMER” na `[REDACTED]` w 129/693 dokumentach. Poprawka r2 (`d3f9674`) + test `test_existing_tokens_not_taken_as_document_number`.
**r2 (`d3f9674`), PRZED `cc70822` → PO:**
| klasa (Mobile zakrył, Desktop nie) | przed | po |
|---|---|---|
| A kwota słowna | 168 | 2 |
| B kwota bez waluty | 21 | 13 |
| C numer umowy | 20 | 0 |
| C numer faktury (częściowo) | 7 | 3 |
| E sygnatura (częściowo) | 3 | 1 |
- Nowe „Desktop zakrył, Mobile nie”: KWOTA z walutą 151 i słownie 15 — pełne kwoty („39 tysięcy 563 złotych”), które Mobile zakrywa
  częściowo; bez waluty tylko „49 999,99” (kwota z OCR „z1”). Nowe KWOTA bez waluty: 10, wszystkie prawdziwe (ceny/wartości tabeli lvl3,
  „49 999,99”); ilości, stawki, jednostki niezakryte. Nowe NUMER: 23, wszystkie numery dokumentów/sygnatury; fałszywych alarmów 0.
- `[REDACTED]` w podglądzie: przed 4, po 5 — dodatkowy `testy/test_numer_dokumentu.txt`: wejście zawiera dosłowny token „NUMER_012”
  obok „Nr U-00284/2023”; wartość zakryta przez Guard (bez wycieku), plik nietypowy (token w danych wejściowych).
- Osoby gold `dataset_clean` (300 dok.): 100% zakrytych przed i po, różnic 0.
- `doc_lvl3_faktura_zlecenie.txt` PO: numery faktury/umowy/zamówienia/rachunku jako NUMER, pozycje tabeli KWOTA_005–010, kwota słowna
  jedną KWOTA, słowo „Numer” jawne.
Wyniki lokalnie: `%TEMP%\lynx_cc_review\mobile_compare_po2\` (`raw_desktop_przed.json`, `raw_desktop_po.json`, `diff_*.json`, `report.md`).
Odtworzenie: `desktop_run.py <SHA> ..\mobile_compare\jobs_all.json raw_desktop_po.json`, potem `compare.py` (narzędzie
`%TEMP%\lynx_cc_review\mobile_compare\`, Mobile `raw_mobile.jsonl` bez zmian).
