# PROPOZYCJA CC DO BRIEFU — LYNX-MAP-FIDELITY — wartość w mapie = dosłowny, całowyrazowy fragment; różne wartości nie dzielą tokenu

STATUS: PROPOZYCJA CC → Architekt pisze `brief.md` (zadanie) → Codex audytuje brief → CC ocenia i implementuje → Codex audyt exact SHA → merge wyłącznie na polecenie OWNERA.
AUTOR PROPOZYCJI: CC. Paweł 2026-10-18: „pisz propozycje, zacznij od kwot i dat, jeśli możesz nie robić osobnych zadań dla małych poprawek to łącz poprawki”.
ŁĄCZY (jedna klasa — mapa tokenów nie odpowiada tekstowi): BOARD `LYNX-CANONICAL-DEDUP` (ultrareview F10), `LYNX-REPLACE-BOUNDARY` (F7, F6). Źródło: ultrareview PR #3 na treści main `e1eb769`; odtworzenie i pomiar CC na main `d6a8a15`.
PRODUCT_TRUTH: arch/spec.md S1 (brak jawnych danych), S2 (wierność: Przywróć oddaje tekst, nie inną wartość), S3, S4 bez zmian, S5.

## Defekty i skala (pomiar CC: 178 dokumentów `backend/dataset_real_public`, pełny tryb, prawdziwy SpaCy, pusty profil)

**D1 (F10) — różne kwoty/daty pod jednym tokenem.** `pipeline_core._canonical` (klucz deduplikacji `TokenAllocator.assign`) usuwa spacje, kropki, myślniki i nawiasy dla KAŻDEGO typu. Odtworzone syntetykiem: „Opłata 15.00 zł, kara 1 500 zł. Termin 2.11.2023 oraz 21.1.2023.” → „Opłata KWOTA_001, kara KWOTA_001. Termin NUMER_001 oraz NUMER_001.”, mapa `KWOTA_001='1 500 zł'`, `NUMER_001='21.1.2023'` — AI dostaje jedną kwotę/datę, Przywróć wpisuje złą kwotę/datę. Daty mają typ NUMER (`layers/amount._DATE_PL_RE` → TOKEN_NUMER), więc sam podział po typie tokenu nie wystarcza.
Skala na 178 dok.: 86 tokenów obejmuje >1 dosłowny zapis (ADRES 35, NUMER 16, KWOTA 15, INSTYTUCJA 11, FIRMA 9; 51 dokumentów), **ale żaden nie łączy różnych wartości** (sprawdzone parsowaniem kwot i dat): to ta sama wartość w innym zapisie („3 700 zł”/„3700 zł”, „10-07-2024”/„10.07.2024”, NIP z myślnikami i bez, adres z/bez przełamania wiersza). To łączenie jest pożądane dla AI (jedna wartość = jeden token) i nie wolno go zlikwidować; D1 jest rzadki, lecz cichy i groźny w pismach (kwoty, terminy).

**D2 (F7) — podmiana wewnątrz dłuższego wyrazu, token sklejony z literami.** 32 sklejone tokeny w 17/178 dokumentów. Mechanizmy:
- `layers/ner_adapter.apply_ner_layer`: `state.text.replace(value, token_id)` (pętla główna i pętla wariantów) bez granic wyrazu — „Sąd” → „FIRMA_013u” (w „Sądu”), OSOBA „Szp” → „OSOBA_004italowi”, „Office” → „OpenFIRMA_016”; syntetyk: OSOBA „Nowak” + „Anna Nowakowska” → „Anna OSOBA_001owska” (końcówka nazwiska jawna);
- `layers/address._ADDR_RE` bez lewej granicy: „al” w środku „Szpitala …” → „SzpitADRES_002”;
- wartość kończąca się znakiem nie-literowym tuż przed literą („…Handlową „” + „INTERSERVICE”) → „FIRMA_002INTERSER”.
Skutek: sklejony token nie pasuje do żadnego `TOKEN_RE` (`…_\d{3}\b`) → Przywróć/Guard go nie widzą, fragment słowa jawny, AI dostaje bełkot.

**D3 (F6) — wielokrotne spacje/tab w nazwie osoby.** `ner_layer._process_ner` `[BUG-7]` zwija białe znaki w wartości (`re.sub(r"\s+", " ", …)`), więc „Jan  Kowalski”, „Jan\tKowalski” nie występuje w tekście, adapter odrzuca encję — osoba w całości jawna (odtworzone). Ta sama klasa co zmergowany LYNX-NER-MULTILINE (tam: `\n`). W 6/178 dokumentach wynik zawiera jawną parę słów z wielkiej litery rozdzieloną 2+ spacjami/tab (wskaźnik, nie werdykt).

## Wymagane zachowanie

1. **Wartość mapy = dosłowny fragment wejścia** dla każdego tokenu, który powstaje z podmiany (bez zwijania białych znaków, bez dopisanej interpunkcji).
2. **Podmiana tylko na granicach wyrazu**: token nie może powstać wewnątrz wyrazu ani przylegać do litery/cyfry tak, by wynik nie pasował do `TOKEN_RE`. Dotyczy podmian NER (pętla główna, warianty) i wzorców adresów; propagacja nazwisk już używa `\b…\b` — zachować.
3. **Deduplikacja po wartości, nie po ciągu bez separatorów** (klucz zależny od rodzaju): kwota → (liczba po rozpoznaniu separatora dziesiętnego, waluta); data → (dzień, miesiąc, rok); identyfikatory (PESEL/NIP/REGON/IBAN/KRS/telefon/konto) → same cyfry/znaki alfanumeryczne jak dziś; osoby/firmy/instytucje/adresy → jak dziś (porównanie bez wielkości liter, diakrytyków i białych znaków). Różne wartości → różne tokeny; ta sama wartość w innym zapisie → nadal jeden token.
4. **Znane ograniczenie, nie naprawiane tutaj (K2):** gdy jeden token obejmuje kilka zapisów tej samej wartości, Przywróć oddaje zapis z mapy (np. „3700 zł” zamiast „3 700 zł”). Mapa z wieloma dosłownymi zapisami pod jednym tokenem = cel K2 („jeden token na osobę/wartość, Przywróć dosłownie każdy zapis” — Paweł 2026-10-18). Ten Task nie może pogorszyć liczby dokumentów z dokładnym Przywróć.

## Minimalny szew (propozycja)
- `backend/pipeline_core.py`: `_canonical(value, kind)` / klucz w `assign`/`register` zależny od rodzaju; rodzaj przekazany z warstwy (kwota, data, identyfikator) albo rozpoznany po wzorcu — do decyzji architekta; bez zmiany formatu tokenu i numeracji.
- `backend/layers/amount.py`: przekazanie rodzaju dla kwot i dat (jeśli wybrany wariant „z warstwy”).
- `backend/layers/ner_adapter.py`: podmiany wartości i wariantów regexem z granicami (jak `_propagate_osoba`), z uwzględnieniem wartości zaczynających/kończących się znakiem nie-literowym.
- `backend/ner_layer.py`: wartość = dosłowny span (`text[ner.start:ner.end]` po obcięciu krawędzi) zamiast zwiniętych białych znaków; klucze stem/odmian mogą dalej używać postaci znormalizowanej.
- `backend/layers/address.py`: lewa granica w `_ADDR_RE` (i pokrewnych wzorcach z prefiksem ul./al./pl./os.).
- Testy: nowy `backend/tests/test_map_fidelity.py` (bez dopisywania do plików przy limicie).
Uwaga rozmiar: `ner_layer.py` 600/600 linii — zmiana D3 musi się zmieścić albo wymaga zgody Pawła; `ner_adapter.py` `apply_ner_layer` 83 linie (ratchet).

TASK_SCOPE:
- backend/pipeline_core.py
- backend/layers/amount.py
- backend/layers/ner_adapter.py
- backend/ner_layer.py
- backend/layers/address.py
- backend/tests/test_map_fidelity.py

OUT_OF_SCOPE: format tokenu i `TOKEN_RE`, alokacja numerów, propagacja nazwisk po prefiksach i wiele zapisów pod jednym tokenem (K2 — `LYNX-K2-INPUTS-ULTRAREVIEW`), fail-closed i Guard (osobna propozycja `LYNX-FAILCLOSED-S3`), normalizacja OCR (K3), profil/trie (`anonymizer._layer1_trie` — K2), UI.

## Test falsyfikujący i pomiar
1. Syntetyki RED→GREEN (Full i Express, gdzie dotyczy): (D1) „15.00 zł” i „1 500 zł” → dwa tokeny, „3 700 zł” i „3700 zł” → jeden; „2.11.2023” i „21.1.2023” → dwa, „10-07-2024” i „10.07.2024” → jeden; NIP z myślnikami i bez → jeden. (D2) OSOBA „Nowak” + „Nowakowska”, FIRMA „Sąd”/„Sądu”, „Szpitala … al. X 5” — brak tokenu przyklejonego do litery, końcówka nie jawna, wynik pasuje do `TOKEN_RE`. (D3) „Jan  Kowalski”, „Jan\tKowalski” z kontrolowanym NER → zamaskowane, wartość dosłowna. Każdy: Przywróć (symulacja) = wejście tam, gdzie nie ma wielu zapisów jednej wartości.
2. 178 dokumentów przez działający `/preview` (backend bazowy vs gałąź, profil Pawła): sklejone tokeny 32 → 0; tokeny łączące różne wartości 0 → 0; tokeny łączące zapisy tej samej wartości — bez spadku (nie rozbijać dobrego łączenia); blokady Guarda, liczba dokumentów z dokładnym Przywróć, jawne osoby z D3 — przed/po; rodzina wariantów (granice wyrazu × typ × położenie) jak `edge_sweep.py` w NER-MULTILINE.
3. Regresje: `test_layers.py` (m.in. `test_iban_pl_ocr_dedup`, `test_dedup_same_iban_twice`, `test_dedup_same_token`), `test_ner_multiline.py`, `test_text_limit_15k.py`, `test_audyt_2026_10.py`, suita standardowa z backendem.
4. Odbiór okiem Pawła: dokument z kwotami w różnych zapisach i KIO_uzp_19463 (sklejone „SzpitADRES”).

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_core.py --symbol _canonical
- TARGETS: backend/layers/ner_adapter.py --symbol apply_ner_layer
- TARGETS: backend/ner_layer.py --symbol _process_ner
- TARGETS: backend/layers/address.py --symbol _ADDR_RE
- REASON: klucz deduplikacji, miejsca podmiany bez granic, zwijanie białych znaków w wartości.
GATE: >150 linii lub ratio >5:1 = WYMAGA_DECYZJI; pliki przy limicie — ratchet.
