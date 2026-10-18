# LYNX-NER-MULTILINE — DELIVERY r1 (CC)

Gałąź `task/LYNX-NER-MULTILINE`. Brief architekta `f0f3f22` (PASS PREIMPLEMENTATION Codexa `49cc0bb`); mechaniczna poprawka nagłówka `## TASK_SCOPE:` → `TASK_SCOPE:` w osobnym commicie (gate.py nie czytał nagłówka; treść briefu bez zmian).
Kod: `6b63efc`; HEAD z poprawką briefu: `88c003d`. Baza: `c62f819` (merge-base z origin/main; późniejsze commity main to wyłącznie BOARD/CLAUDE.md).

## Zmiana

`backend/ner_layer.py` (+23/−1, plik 578 → 600 linii): nowa `_split_lines(text, ner_results)` wołana w `_process_ner` przed `_firma_entities`, czyli zanim `re.sub(r"\s+", " ", …)` zgubi koniec wiersza. Dla wyniku SpaCy, którego span zawiera `\n`:
1. całość (z `\n`→spacja) najpierw przez istniejący `_filter_institutions` — odrzucona całość = brak kandydatów (instytucja/słowo pospolite nie rozpada się na tokeny);
2. FIRMA dzielona tylko, gdy span zawiera formę prawną (`sp.`/`spółka`/`s.a.`/`s.c.`) — bez niej w próbce to były instytucje (KIO, UZP, WIOŚ, Zarząd Dróg, NCBR), których filtr jeszcze nie zna (C1/K1); ich kawałki powodowały MAP_LEAK;
3. z każdej niepustej linii kandydat = dokładny fragment wejścia (obcięte `␣\t\r,;` na krawędziach), ta sama etykieta, dalej zwykła ścieżka i filtry;
4. linia jednowyrazowa tylko jako imię/nazwisko (`_is_person_word(strict=False)` — kontekst osoby z SpaCy, jak dla wielowyrazowej OSOBY); część FIRMA musi zaczynać się wielką literą i nie składać się wyłącznie ze słów formy prawnej (`_FORM_WORDS`).
`layers/ner_adapter.py` bez zmian — szew w `ner_layer` wystarczył (wartości mapy są teraz dosłownie w tekście).

`backend/tests/test_ner_multiline.py` (nowy, 131 linii, uruchamiany jawnie).

## Gate (dosłownie)

```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 88c003d06e2d9d6feefa706d3c5c188b2f36610a
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 154/1 = 154.0:1 (threshold 5:1)
  - TOTAL_LINES: 155 lines changed (threshold 150)
```
(lista IMPORTERS_FOR_REVIEW w `gate_r1.txt`). 131 z 155 linii to nowy plik testów; kod produktu 24 linie. Wymaga akceptacji Pawła; testów nie przycinano pod próg.
Pierwszy przebieg gate na `6b63efc` (przed poprawką nagłówka): `STATUS: FAIL` — `TASK_SCOPE: TASK_SCOPE missing in brief`, `DIFF_SCOPE: file outside TASK_SCOPE` ×2.

## Testy

| Zestaw | baza `c62f819` (worktree) | gałąź |
|---|---|---|
| `tests/test_ner_multiline.py` | **10 failed**, 4 passed (przechodzą: końcowy `\n`, Express, instytucja przełamana, UZP bez formy — strażnicy) | **14 passed** |
| `tests/test_layers.py` | 121 passed | 121 passed |
| `tests/` (pytest.ini, bez backendu) | 129 passed, 40 skipped, 1 xfailed | 129 passed, 40 skipped, 1 xfailed |
| `tests/test_audyt_2026_10.py` | 131 passed, 10 xfailed | 131 passed, 10 xfailed (brak XPASS) |
| `tests/` z działającym backendem z gałęzi | — | 167 passed, 2 skipped, 1 xfailed |

Prawdziwy SpaCy (pkt 2 briefu): 4 syntetyki z obowiązkową asercją, że `detect_entities` zwraca span z `\n` (dwie osoby w liniach, lista senatorów z przecinkami, osoba przełamana, lista w czterech liniach) — wszystkie przechodzą przez pełny pipeline z Guardem bez blokady, Przywróć 1:1. Firma przełamana: model nie dał spanu z `\n` na syntetyku — sprawdzona tylko na podstawionym wyniku NER (NOT_CHECKED dla prawdziwego modelu).
`/preview` (backend z gałęzi), syntetyczny TXT ze składem orzekającym: brak jawnych nazwisk i PESEL, bez blokady.

## Próbka lokalna (pkt 4; pełny tryb, prawdziwy SpaCy, pusty profil, ta sama wersja backendu przed/po; dane tylko lokalnie)

Plik Mobile `test_imiona_nazwiska_100_11_07.txt`: jawne linie **85 → 23** / 102, pełne imię+nazwisko **36 → 0** / 49. Pozostałe 23 to linie jednowyrazowe: negatywy pliku (Data, Dane, Osoba, Polskiej, Sądowy… — mają zostać jawne) oraz samotne imię/nazwisko w osobnej linii (2 nazwiska, 4 imiona/imiona-słowa), jawne także na bazie — SpaCy nie daje dla nich spanu wielowierszowego; klasa „samotne nazwisko” → K1 (słownik).

Dokumenty diagnozy A1/A2 — jawne osoby przed → po: KIO 578/11 przewodnicząca **1 → 0**; KIO_uzp_16714 członkowie składu **2 → 0**; C047 senatorowie (biernik) **10 → 0**.
17 dokumentów diagnozy: **blokady Guarda bez zmian** (5 przed, te same 5 po), status Przywróć (równość z wejściem) bez zmian w każdym dokumencie, liczba `\n` w wyniku bez zmian w każdym dokumencie.
Nowe wartości mapy OSOBA/FIRMA poza A1/A2 (częściowo maskowane): osoby z tabel C024 (Sylwia K./Piotr I., Dominik S.), firmy z formą prawną przełamane wierszem (Optima „Centrum Sp. z o.o”, WYG „International sp. z o.o”, Rejonowy Zarząd Infrastruktury — ten ostatni to instytucja, klasa C1). Znikły dawne śmieciowe wartości: `Sp. z o.o`, `z o.o. Sp. k`, `Rb-N`, `Komisji Rewizyjnej Rady P`; „Narodowego Centrum Badań i Rozwoju” (instytucja) nie jest już maskowana.

Pośrednie wersje (do wiadomości audytu): bez kwalifikacji linii jednowyrazowych powstały tokeny „Protokolant”/„Odwoławczej” i nowa blokada KIO 578/11; bez warunku formy prawnej — kawałki instytucji („Zamówień Publicznych”) i nowa blokada KIO_114738 (Guard porównuje bez wielkości liter z „Prawo zamówień publicznych”). Oba usunięte; negatywy w teście.

## Ograniczenia i findingi (nie naprawiane tutaj)

- Połowa przełamanej osoby, która jest na liście dokładnych nazw geo (`_NER_BLOCKLIST`, np. „Wierzbicka”, „Zielińska”), zostaje jawna — filtr bez zmian zgodnie z briefem → K1 (słownik nazwisk / kontekst osoby).
- FIRMA przełamana wierszem bez formy prawnej nie jest maskowana (jak dotąd) — rozróżnienie firma/instytucja → K1 (C1).
- `_is_person_word(strict=False)` przyjmuje też „Członkowie” (bez dwukropka) — w nagłówkach składu słowo występuje z dwukropkiem i nie kwalifikuje się; brak takiego FP w próbce.
- Przywróć ≠ wejście w 13/17 dokumentów diagnozy już na bazie (po zmianie także 13/17, te same) (normalizacja OCR/F3, wartości ADRES z `\n`) — bez zmian tą dostawą; klasa K3 (SHADOW-NORMALIZE / TEXT-FIDELITY-F3).
- Express nie ma NER — bez zmian i bez obietnic.

## Do odbioru

Ocena okiem Pawła w działającym programie: KIO 578/11 (`Pobrane`) i C047 (`backend/dataset_real_public/C_codex/docs/C047.pdf`) — skład orzekający i lista senatorów zakryte, brak nowej blokady. Backend z tej gałęzi uruchomiony lokalnie przez CC.
