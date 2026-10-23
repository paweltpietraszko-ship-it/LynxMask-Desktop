# DELIVERY — LYNX-AMOUNT-OCR-MULT (round 01)

Brief `8356de7` (Codex BRIEF_ONLY r1 PASS `c7b1d84`), baza `9fb40b1c438b67c85059e1a3dbd2342937f6c9d9`, kod `8681158bc06734bf4a03d45ce2f09a10e28f3f74`.
CC nie wystawia PASS/FAIL — ocena: gate + Codex.

## gate.py (stdout dosłownie, pierwsze linie)
```
STATUS: PASS
HEAD_SHA: 8681158bc06734bf4a03d45ce2f09a10e28f3f74
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
```

## Zmiana (`backend/layers/amount.py` 195 → 230 l.)
- `_MULT_CUR_RE`: liczba + mnożnik (`tys.`, `tysięcy`, `mln`, `mld`, `milion*`, `miliard*`) + waluta → KWOTA (skip jak `_AMOUNT_RE`: liczebnik przed liczbą → verbal_amounts).
- `_MULT_CTX_RE`: liczba + mnożnik bez waluty → KWOTA tylko ze słowem kwotowym w zdaniu (`_not_amount_ctx`), bez jednostki (`_UNIT`);
  gdy po mnożniku idzie dalszy ciąg liczby („44 tysięcy 813 złotych”) — zostaje dla `verbal_amounts` (jeden token; wykryte przez
  `test_amounts_numbers::test_mixed_verbal_amount_is_one_token` w trakcie pracy).
- `_AMOUNT_O_RE` / `_AMOUNT_O_CTX_RE`: liczba zaczynająca się cyfrą, z `O`/`o` zamiast zer, przy walucie albo (grupy tysięcy) przy słowie
  kwotowym; tylko gdy liczba faktycznie zawiera O (`_no_letter_o`) — pozostałe kwoty biorą dotychczasowe wzorce bez zmian.
- Nowe wzorce na liście przed dotychczasowymi (przy tym samym starcie wygrywa dłuższy). Tekst bez zmian: mapa trzyma fragment literalnie.
- Granica Przywróć (uwaga Codexa r1): literalnie wraca fragment w postaci, w jakiej dotarł do warstwy kwot; wcześniejsze zmiany
  `ocr_normalizer` (np. „1 2OO,5O zł” → „1 200,5O zł”) nie są cofane — normalizer poza zakresem.
- `ocr_normalizer.py`, `verbal_amounts`, Guard — bez zmian. `I`/`l` zamiast `1` — poza zakresem (Codex r1).

## Testy (cwd = backend, `.venv`)
- `tests/test_amount_ocr_mult.py` (nowy): 20 passed — 11 pozytywów z tabeli briefu (wartość w mapie literalnie), 7 negatywów
  („15 tys. mieszkańców”, „15 OOO szt.”, „OOO Gazprom”, „Wersja 2 tys.”, „15 tys. km”, „Na koncie było 15 OOO.”, „Model 15 OOO…”),
  mnożnik z dalszym ciągiem, istniejące kwoty bez zmian.
- Regresja: test_amounts_numbers 20 passed; test_silent_pack1 30; test_formats_pack2 20; test_map_fidelity 29; test_pipeline_v2 41;
  test_addr_email_leaks 22; test_layers 2 failed/119 (jak main); test_audyt_2026_10 1 failed/122/2 xfailed (jak main).
- Pełny pipeline (`pseudonymize_document`, pusty profil) na wszystkich wierszach tabeli briefu: wszystkie pozytywy → KWOTA, negatywy bez zmian.

## Pomiar „bez pogorszenia” (main `9fb40b1` → gałąź)
| zbiór | main | gałąź |
|---|---|---|
| GOLD dev / test: ciche, zbędne, pytania/dok, KWOTA zakryte | 20·52, 69/440·152/880, 0,90·0,86, 120·240 | identycznie |
| testset_owner (clean/stress/testy/pliki/ocr) | jak w tabeli `run_testset.py` | identycznie |
Kwot z mnożnikiem/O w tych zbiorach nie ma w kluczu — poprawę wykazują testy celowane (zgodnie z Codex r1).
