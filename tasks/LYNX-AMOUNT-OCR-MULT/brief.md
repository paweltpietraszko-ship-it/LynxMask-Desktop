# LYNX-AMOUNT-OCR-MULT — kwoty z mnożnikiem („15 tys. zł”) i z „O” zamiast zera („15 OOO zł”)

23.10.2026, CC. Poprawka bez Architekta. Zgłoszenie Pawła 23.10: „silnik nie widzi 15 tysięcy i jak ktoś zamiast zer wciśnie O.
Czyli 15 OOO przechodzi bez guarda”. Teksty przykładów syntetyczne.

## Reprodukcja (main `9fb40b1`, pełny `pseudonymize_document`, pusty profil)
| wejście | wynik main | Guard |
|---|---|---|
| „Kara umowna 15 tys. zł za dzień.” | jawne | brak |
| „Odszkodowanie 2,5 mln zł.” | jawne | brak |
| „Kwota 2 mld zł” | jawne | brak |
| „Wynagrodzenie wynosi 15 tysięcy miesięcznie.” | jawne | brak |
| „Kwota do zapłaty: 15 OOO zł.” | jawne | brak |
| „Kwota 15OOO zł” / „Kwota 15.OOO zł” | jawne | brak |
| „Odsetki 1 2OO,5O zł” | jawne („1 200,5O zł” po normalizerze) | brak |
| dla porównania: „15 tysięcy złotych”, „15 000 zł”, „1O 000 zł” | KWOTA | — |

## Zasada (słowami)
Kwota = liczba + znak pieniędzy.
- Znak pieniędzy: waluta po liczbie (`zł`, `PLN`, `złotych`, `EUR`… — jak `_AMOUNT_RE`/`_AMOUNT_WORD_RE`), także po mnożniku
  `tys.`/`tysiąc*`/`tysięcy`, `mln`/`milion*`, `mld`/`miliard*`.
- Bez waluty: liczba z mnożnikiem jest kwotą tylko ze słowem kwotowym w tym samym zdaniu (istniejące `_AMOUNT_CTX_WORD_RE`,
  `_not_amount_ctx` z SILENT-PACK1). „15 tys. mieszkańców” bez słowa kwotowego — bez zmian.
- Litera `O`/`o` w liczbie = zero **tylko w liczbie przy znaku pieniędzy** (waluta albo słowo kwotowe jak wyżej): liczba zaczyna się cyfrą,
  dalej cyfry/`O`/`o` i separatory jak w `_AMOUNT_RE`. Tekst się nie zmienia (bez normalizacji) — maskowany jest oryginalny fragment, Przywróć 1:1.
- Guard bez zmian (model 23.10: decyduje silnik).

## Zmiana
- Właściciel: **`backend/layers/amount.py`** (195 l.) — nowe wzorce obok `_AMOUNT_RE`/`_AMOUNT_WORD_RE`, ten sam przydział `TOKEN_KWOTA`,
  te same wykluczenia (`_UNIT`, wersja, `_after_number_word` → `verbal_amounts`).
- Bez zmian w `layers/ocr_normalizer.py` (696 l., limit „nie rośnij”; globalna zamiana O→0 ryzykowna dla „OOO Gazprom”, kodów, sygnatur).
- `verbal_amounts` bez zmian (liczby słowne).

## Bez zmian (testy negatywne)
- „Ludność: 15 tys. mieszkańców.” (brak znaku pieniędzy) · „Pozycja 15 OOO szt.” (jednostka) · „Sprzedawca: OOO Gazprom” (brak cyfry)
- „Wersja 2 tys.” · „15 tys. km” · istniejące testy kwot (`test_amounts_numbers`, `test_silent_pack1`, `test_formats_pack2`).

## Poza zakresem (zgłoszone)
- „Na koncie było 15 OOO.” — bez waluty i bez słowa kwotowego z listy („konto”) — zostaje jawne; ewentualne poszerzenie listy słów kwotowych osobno.
- `I`/`l` zamiast `1` w kwotach — ta sama klasa, ale bez zgłoszenia i bez przykładu w zbiorach; do decyzji przy prechecku (ROZSZERZENIE CC tylko jeśli Codex uzna za tę samą klasę).

TASK_SCOPE:
- backend/layers/amount.py
- backend/tests/test_amount_ocr_mult.py
- tasks/LYNX-AMOUNT-OCR-MULT/brief.md
- tasks/LYNX-AMOUNT-OCR-MULT/repo_before.hash
- tasks/LYNX-AMOUNT-OCR-MULT/round_01/implementation/DELIVERY.md

Szacunek: kod ~30 l., testy ~50 l.

## Odbiór
- `tests/test_amount_ocr_mult.py`: wszystkie przypadki z tabeli reprodukcji → KWOTA (na main failują); negatywy → bez zmian.
- Regresja: `test_amounts_numbers`, `test_silent_pack1`, `test_formats_pack2`, `test_layers` (2 znane faile), `test_map_fidelity`.
- Pomiar: `testset_owner/run_testset.py` (clean/stress — kwoty nie są w kluczu, więc tylko „bez pogorszenia” liczby pytań),
  GOLD `human_view.py` dev/test: KWOTA ciche nie rosną, zbędne zakrycia nie rosną.
