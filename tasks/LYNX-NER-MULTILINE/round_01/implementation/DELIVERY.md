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

---

# DELIVERY r2 (po FAIL r2 Codexa, F1)

Kod: `f37bdb7`. Reproduktor Codexa: `tasks/LYNX-NER-MULTILINE/round_01/tests/tests_r2_repro.py` (`991d6fd`).

## F1 — przyczyna i poprawka

F1 potwierdzony: span FIRMA bez formy prawnej z `\n` **tylko na brzegu** (`"Testopolia Systemy\n"`, `"\r\n"`, `"\nTestopolia Systemy"`, `"Testopolia\n"`) szedł do podziału, a warunek „FIRMA dzielona tylko z formą prawną” go porzucał — baza maskowała go dzięki `strip()`. Moje testy r1 tej granicy nie objęły (brak przeglądu rodziny przed oddaniem — błąd procesu CC).
Poprawka: `_split_lines` dzieli wyłącznie span z końcem wiersza **wewnątrz** (`"\n" not in span.strip()` → dotychczasowa ścieżka). Przy okazji przeglądu: forma prawna w następnej linii („Testopolia Systemy\nSp. z o.o.”) wracała przez `_firma_bounds` (doklejał `\n` + formę) — podział przeniesiony za `_firma_entities` (`_split_lines(text, _firma_entities(...))`).

## Przegląd rodziny (`round_01/implementation/edge_sweep.py`, baza `c62f819` vs bieżące drzewo, ścieżka jak reproduktor Codexa: kontrolowany NERResult → `pipeline.pseudonymize_document` z Guardem)

Macierz: etykieta (OSOBA/FIRMA) × treść (1 słowo, 2 słowa, dwie osoby, FIRMA bez formy, z „Sp. z o.o.”, ze „Spółka Akcyjna”) × położenie końca wiersza (brak, przód LF, tył LF, tył CRLF, oba brzegi, wnętrze LF, wnętrze CRLF, wnętrze ze spacjami, wnętrze + tył). **55 przypadków, 0 regresji** (jawne słowo, blokada/błąd, Przywróć); poprawa w 20 (osoby z wnętrzem, FIRMA z formą prawną). Bez zmian (świadomie): FIRMA bez formy z `\n` wewnątrz — dalej jawna jak na bazie (firma vs instytucja → K1, C1).

## Testy (r2)

| Zestaw | baza `c62f819` | gałąź `f37bdb7` |
|---|---|---|
| `tests/test_ner_multiline.py` (+5 wariantów F1) | 11 failed, 8 passed | 19 passed |
| `test_ner_multiline.py` + `test_layers.py` | — | 140 passed |
| `tests/` (z działającym backendem) | — | 167 passed, 2 skipped, 1 xfailed |
| `tests/test_audyt_2026_10.py` | 131 passed, 10 xfailed | 131 passed, 10 xfailed |

## Prawdziwe dokumenty przez działający backend (`/preview`, jak aplikacja; profil biura Pawła, 26 encji)

Uwaga Pawła: testy jednostkowe nie są dowodem — liczy się przepuszczenie dokumentu przez backend. Te same 17 dokumentów diagnozy przez `/preview`: backend bazowy (worktree `origin/main`, ten sam profil przez `ANONYMIZER_PROFILE_DIR`, osobny katalog archiwum) vs backend z gałęzi `f37bdb7`.
- jawne osoby przed → po: KIO 578/11 1 → 0; KIO_uzp_16714 2 → 0; C047 10 → 0; C024 wspólnicy 3 → 0;
- blokady Guarda 5 → 5 (te same dokumenty); równość Przywróć z wejściem i liczba `\n` w wyniku — bez zmian w każdym z 17;
- nowe wartości mapy: osoby jak wyżej + firmy z formą prawną przełamane wierszem; znikły śmieciowe `Sp. z o.o`, `z o.o. Sp. k`, `Komisji Rewizyjnej Rady P`.

## Gate r2 (dosłownie)

```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: f37bdb7b1d106b045f20520ded1d1806fe5ea540
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 168/1 = 168.0:1 (threshold 5:1)
  - TOTAL_LINES: 169 lines changed (threshold 150)
```
Kod produktu 24 linie (`ner_layer.py` 600/600), test 145 linii. Akceptacja rozmiaru — decyzja Pawła.

---

# DELIVERY r3 (ROZSZERZENIE CC po odbiorze okiem Pawła)

**OWNER_ACCEPTED 2026-10-18 (Paweł, dosłownie): „akceptuję przekroczenie linii”** — dotyczy limitów rozmiaru tej dostawy (gate WYMAGA_DECYZJI: TOTAL_LINES/RATIO). Nie jest zgodą na merge ani osłabienie ochrony.

Kod: `383a09e`. Sekcja ROZSZERZENIE CC w briefie (`cc0b6ee`, przed kodem).

## Co wykrył Paweł (C047 w działającym programie, r2)
Ostatnia linia „Henryk Piotr Siedlaczek” → „Henryk OSOBA_026 Siedlaczek”, OSOBA_026 = „Piotr Masłowski”. Przyczyna: `ner_adapter._propagate_osoba` (istniejąca Warstwa 3c) propaguje token na każdy człon nazwy, także imię, wzorcem `Imię[a-z…]{0,6}` → „Piotr” innej osoby dostaje cudzy token (Przywróć wstawiłby inną osobę); podmiana odcina też wariant tej linii (OSOBA_021), więc „Henryk”/„Siedlaczek” zostawały jawne. Przed dostawą mechanizm był ten sam, lecz senatorowie nie byli wykrywani.

## Poprawka
`_propagate_osoba` pomija człony będące imieniem (`names_inflected.json`, 199 imion z odmianami) — propaguje nazwiska. +12 linii w `ner_adapter.py`.

## Wynik
- `/preview` z profilem Pawła, 17 dokumentów, baza vs `383a09e`: C047 jawne 12 → 0 (z Henrykiem i Siedlaczkiem), ostatnia linia = OSOBA_021; KIO 578/11 1→0, KIO_uzp_16714 2→0, C024 3→0; blokady 5 → 5; **interpelacja_1739: Przywróć ≠ → = wejście** (stara propagacja imion psuła go na bazie); pozostałe 16: Przywróć i `\n` bez zmian.
- Plik Mobile: jawne linie 23 → 26 / 102, pełne imię+nazwisko 0 → 1 / 49. Porównanie linia po linii (stara propagacja vs nowa): stara zakrywała m.in. „Wójcik” tokenem „Wojciech Lewandowski”, „Maciej” tokenem „Bartłomiej Maciej Kowalski”, „Grażyna” tokenem „Grażyna Zuzanna” (cudze wartości). Teraz jawne zostają: samo imię w linii („Grażyna”, „Wiktoria”), imię w odwróconym zapisie obok zakrytego nazwiska tej samej osoby („OSOBA_008 Katarzyna”), „Pani Katarzyna”. **Kompromis świadomy: jawne samo imię zamiast cudzej osoby w Przywróć.** Propagacja imienia tylko przy własnym nazwisku wymaga decyzji o wartości mapy (K2) — zgłoszone.
- Testy: `test_ner_multiline.py` 20 passed (baza 12 failed / 8 passed; test propagacji failuje także na starym adapterze); + `test_layers.py` 141 passed; `tests/` z backendem 167 passed, 2 skipped, 1 xfailed; `test_audyt_2026_10.py` 131 passed, 10 xfailed; `edge_sweep.py` 55 przypadków, 0 regresji.
- Znane, poza zakresem (K2): wariant tej samej osoby w innej formie („Henryk Piotr Siedlaczek” → OSOBA_021 o wartości „Henryka Piotra Siedlaczka”) — Przywróć wstawia formę z mapy, nie dosłowną; tak samo propagowane odmiany nazwiska („Masłowskiego” → token wartości „Piotr Masłowski”).

## Gate r3 (dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 383a09e7cc69a7d9cbef93edd35e4556d28f481a
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 192/2 = 96.0:1 (threshold 5:1)
  - TOTAL_LINES: 194 lines changed (threshold 150)
```

---

# DELIVERY r4 (propozycja Pawła po r3)

Paweł 2026-10-18: „Wolałbym sytuację, gdyby zamiast gołego imienia, imię dostało inny token. Czyli zamiast OSOBA_008 Katarzyna było OSOBA_008 OSOBA_027”. Ocena CC: zgoda — imię nie jawne, wartość dosłowna (Przywróć 1:1), bez cudzej osoby; koszt: AI widzi dwa tokeny przy jednej osobie (nadmaskowanie, zgodne z polityką Pawła).
Kod: `a5846b5` (funkcja) + `f9bf74c`/`e31e0ed` (bez zmiany działania: `apply_ner_layer` z powrotem 83 linie — gate SIZE_FUNC „nie pogarszaj”).

`ner_adapter._apply_first_names` (po wariantach): imię z `names_inflected.json`, wielką literą, bezpośrednio obok tokenu `OSOBA_NNN` w tej samej linii albo po „Pan/Pani” → `allocator.assign("OSOBA", imię)` — własny token, dosłowna wartość (ta sama wartość = ten sam token). Bez kontekstu (samo imię w linii, „Róża”) — bez zmian (K1).

Wynik:
- plik Mobile: jawne linie 26 → **25** / 102, pełne imię+nazwisko 1 → **0** / 49; „Zielińska Katarzyna” → „OSOBA_008 OSOBA_050” (OSOBA_050 = „Katarzyna”), „Pani Katarzyna” → „Pani OSOBA_050”;
- `/preview` z profilem Pawła, 17 dokumentów (baza vs `a5846b5`): A1/A2 + C024 + C047 jawne osoby 18 → 0; blokady 5 → 5; Przywróć: interpelacja_1739 ≠ → =, pozostałe bez zmian; liczba `\n` bez zmian; nowe tokeny-imiona m.in. „Marcin” (wspólnik MAXTO — wcześniej część sklejonego tokenu);
- testy: `test_ner_multiline.py` + `test_layers.py` 143 passed; `tests/` z backendem 167 passed, 2 skipped, 1 xfailed; `test_audyt_2026_10.py` 131 passed, 10 xfailed; `edge_sweep.py` 55, 0 regresji.

## Gate r4 (dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: e31e0ed5433e139f5623cc58a109ae14ab7925c1
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 222/6 = 37.0:1 (threshold 5:1)
  - TOTAL_LINES: 228 lines changed (threshold 150)
```
Wcześniejszy przebieg na `a5846b5`: `STATUS: FAIL` — `SIZE_FUNC: backend/layers/ner_adapter.py:apply_ner_layer has 85 lines (max 50, before 83)`; na `f9bf74c`: 84 → usunięta pusta linia, 83. Rozmiar dostawy wzrósł od akceptacji Pawła (194 → 228 linii) — do potwierdzenia.

---

# Korekta opisu r4 (po odpowiedzi Codexa `8014887`)

Doprecyzowanie Pawła (zapis Codexa, dosłownie): „drugi token dla imienia to wyjście awaryjne, docelowo program imię i nazwisko przykrywać ma jednym tokenem.”
Opis r4 powyżej przedstawiał osobny token imienia jako rozwiązanie — to błąd opisu CC. Właściwie:

- **Cel (nie zrealizowany w tym zadaniu):** jedna osoba = jeden token obejmujący imię i nazwisko, także w zapisie odwróconym („Zielińska Katarzyna”) i w odmianach. Wymaga, by mapa/Przywróć oddawały dosłownie różne zapisy tej samej osoby pod jednym tokenem — dziś token ma jedną wartość, więc to zmiana kontraktu mapy → krok **K2** diagnozy (powtórzenia i odmiany); wpisane jako wymaganie do K2.
- **Co r3/r4 realizuje (wyjście awaryjne):** (r3) propagacja nie przypisuje imieniu tokenu innej osoby — usuwa cudze wartości w Przywróć; (r4) imię, które po tym zostałoby jawne obok tokenu osoby lub po „Pan/Pani”, dostaje własny token z dosłowną wartością. Skutek: imię nie jest jawne i nie ma cudzej wartości, ale jedna osoba może mieć dwa tokeny.
- **Pozostaje:** cel wyżej (K2); samotne imię bez kontekstu (K1); odmiany tej samej osoby z wartością innej formy (K2, finding w BOARD).
- **Status:** r3 i r4 to zmiany zachowania wymagające jawnego OWNER_ACCEPTED/OWNER_CORRECTED Pawła oraz potwierdzenia rozmiaru 228 linii — do uzupełnienia tutaj dosłownie.
