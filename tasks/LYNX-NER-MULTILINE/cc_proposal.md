# PROPOZYCJA CC DO BRIEFU — LYNX-NER-MULTILINE — encja NER przełamana wierszem nie może przepaść przy podmianie

STATUS: PROPOZYCJA CC → Architekt pisze `brief.md` (zadanie) → Codex audytuje brief → CC ocenia i implementuje → Codex audyt exact SHA → merge wyłącznie na polecenie OWNERA.
AUTOR PROPOZYCJI: CC (Paweł 2026-10-18: „możemy pisać briefy”; kolejność wg zaakceptowanej diagnozy). Krok **K0** z `arch/DIAGNOZA_2026-10-18.md` r2 (`4f6c380`, Codex AKCEPTUJĘ `9c4db4e`).
PRODUCT_TRUTH: arch/spec.md S1 (brak jawnych danych), S2 (wierność tekstu: struktura wierszy zachowana, Przywróć 1:1), S3 (fail-closed), S4 (Guard bez zmian), S5.
Źródła: BOARD `LYNX-NER-MULTILINE` (regresja z T03 `bfdcaea`), diagnoza §3 A1/A2 i trace Codexa r1 (`1679a3a`).

## Defekt (potwierdzony)

- `ner_layer._process_ner` normalizuje wartość encji SpaCy: `re.sub(r"\s+", " ", entity_text)` (l. ~451). Encja, której span zawiera `\n`, dostaje wartość z ZAMIENIONYM znakiem nowej linii.
- `layers/ner_adapter._remap_ner_ids` (l. 212–214) nadaje numer tylko wartości obecnej dosłownie w tekście (`val in state.text`); dalej `state.text.replace(value, token_id)`. Wartość ze spacją zamiast `\n` nigdy nie występuje w tekście → **encja przepada w całości**, osoby/firmy z niej zostają jawne. Przed T03 słowa były zastępowane wspólnym tokenem bez wpisu w mapie (ukryte, bez Przywróć); od T03 jawne.
- Stan na `c62f819` (main): plik Mobile `C:/Projects/LynxMask/testy/test_imiona_nazwiska_100_11_07.txt`, pełny tryb, prawdziwy NER, pusty profil — **85/102 linii jawnych, 36/49 pełnych imion i nazwisk** (narzędzie `audyt/public_docs/bisect_names.py`, gałąź `task/LYNX-PUBLIC-REAL-DOCS`). 16.10 przed T01: 36/102.
- Odmiany spanów zaobserwowane na `dataset_real_public` dev (SpaCy, `c62f819`):
  1. osoba + słowo z następnej linii: `„Magdalena Grabarczyk\nProtokolant”` (KIO 578/11);
  2. dwie osoby w kolejnych liniach: `„Aneta Mlącka\nAndrzej Niwicki”` (KIO_uzp_16714);
  3. jedna osoba przełamana: `„Joanna \nWieteska”` (bip_7d1cff548e), `„Dominik \nSkiba”`, `„Sylwia Kotowicz Piotr \nIzdebski”` (C024);
  4. lista wielu osób w kilku liniach, z przecinkami: C047 (dwa spany po 5+ osób);
  5. instytucja/firma przełamana: `„Krajowej Izby\nOdwoławczej”`, `„Zamawiającego - Uzdrowisko Busko-\nZdrój Spółka Akcyjna”`, `„Biuro Rzecznika Praw \nObywatelskich, Al.”`;
  6. tylko końcowy `\n` (`„Daniel\n”`) — dziś działa dzięki `strip()`, nie może się zepsuć.

## Wymagane zachowanie

- **Encja NER, której span zawiera znak nowej linii, nie może zostać porzucona.** Każda niepusta linia spanu traktowana jest jak osobny kandydat tego samego typu (OSOBA/FIRMA): wartość = dokładny tekst tej linii z oryginału (po obcięciu białych znaków i interpunkcji na krawędziach), dalej przez TE SAME filtry i ścieżkę co zwykła encja jednowierszowa (instytucje, blocklista, `@`, forma prawna, propagacja, warianty).
- **Znak nowej linii nigdy nie wchodzi do tokenu ani do wartości mapy.** Struktura wierszy wyniku = struktura wejścia; Przywróć jednoprzejściowy = oryginał bajt w bajt.
- Skutek akceptowany (nadmaskowanie zamiast wycieku): osoba przełamana wierszem (odmiana 3) może dostać dwa tokeny („Joanna” / „Wieteska”) — oba zamaskowane, każdy przywracany dosłownie. Łączenie jej w jeden token jest POZA zakresem (wymaga rozróżnienia jednej osoby od dwóch osób/komórek — K5 diagnozy).
- Linia, która po filtrach nie jest osobą/firmą (np. `„Protokolant”`), zostaje jawna, tak jak dziś zostałaby jako osobna encja; NIE dodawać nowych list słów w tym Tasku. Jeśli takie słowo trafia do mapy jako OSOBA, odnotować w DELIVERY jako dowód dla K1 (C2), nie naprawiać.
- Lista wielu osób w jednej linii z przecinkami (odmiana 4) może zostać jednym tokenem — to klasa C3 (K3), poza zakresem; wymagane tylko: brak jawnych imion/nazwisk z tej linii i Przywróć 1:1.
- Encje jednowierszowe: zachowanie bez zmian (te same tokeny, te same wartości mapy na reproduktorach regresyjnych).

## Minimalny szew

Miejsce rozbicia spanu: w `ner_layer.py` przed normalizacją wartości (gdy znany jest `ner.start/ner.end` i oryginalny tekst), tak aby każda linia przeszła istniejącą ścieżkę jak osobny wynik NER. Nie zmieniać `spacy_ner.py` (model/detekcja), kolejności pipeline, alokatora ani formatu tokenu. W `layers/ner_adapter.py` tylko jeśli precheck wykaże, że rozbicie w `ner_layer` nie wystarcza (np. warianty) — wtedy dopisać przed kodem jako ROZSZERZENIE CC.
Poza zakresem, choć ta sama okolica: A4 (`„z o.o”` jako osobna FIRMA w głównej ścieżce adaptera — K1), C1/C2 (instytucje, zwykłe słowa — K1), C3 (sklejone osoby — K3), łączenie jednej przełamanej osoby (K5), limit 15 000 znaków (osobny Task K0).

TASK_SCOPE:
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/tests/test_layers.py
- backend/tests/test_audyt_2026_10.py

OUT_OF_SCOPE: backend/spacy_ner.py, backend/ner_blocklist.py, backend/pipeline_new.py, backend/pipeline_core.py, alokator i TOKEN_RE, warstwy regex (`backend/layers/*` poza `ner_adapter.py`), Output Guard, `pseudominizer_api.py` (w tym MAX_TEXT_CHARS), UI, profil biura/seed, HerBERT, nowe listy słów. Jeśli precheck wykaże, że źródło jest w innym ownerze — STOP i punktowy finding przed implementacją.

## Minimalny test falsyfikujący (w `backend/tests/test_layers.py`, fikstura `_full_ner` — prawdziwy SpaCy, uruchamiany jawnie)

1. Syntetyczne bloki (bez realnych danych), oba tryby `run_pipeline_new` i `run_pipeline_express`:
   a) `"Skład:\nAdam Kowalczyk\nBeata Zielińska\nProtokolant: Celina Dąbrowska"`; b) `"Przewodniczący\nAdam Kowalczyk\nCzłonkowie:\nBeata Zielińska\nDariusz Wróblewski"`;
   c) osoba przełamana `"złożył Dariusz \nWróblewski oraz"`; d) firma przełamana `"Odwołanie wniosła Alfa Systemy \nSpółka Akcyjna z siedzibą"`.
   Dla każdego: żadne imię ani nazwisko z bloku nie jest jawne w wyniku; liczba i położenie `\n` w wyniku = w wejściu; żaden token ani wartość mapy nie zawiera `\n`; brak tokenu w tokenie; Przywróć = wejście. Jeśli SpaCy nie zwraca encji wielowierszowej na danym syntetyku, test musi to wykazać (asercja na spanie z `\n` w `detect_entities`) — inaczej nie falsyfikuje. Zastępczy syntetyk dobrać tak, by span z `\n` powstał.
2. Regresja: istniejące testy NER/FIRMA w `test_layers.py` (m.in. `test_firma_cala_nazwa_z_forma_full_ner`, `test_forma_prawna_nie_ginie_przy_przywroc`), `test_audyt_2026_10.py` (reproduktory xfail — zdjąć marker tylko tam, gdzie przejdzie w XPASS), standardowa suita bez nowych FAIL.
3. Plik Mobile `test_imiona_nazwiska_100_11_07.txt` (lokalny, nie do repo): przed/po na `c62f819` i exact SHA dostawy — liczba jawnych linii **istotnie poniżej 36/102** (stan sprzed T01), pełne imię+nazwisko jawne: wymienić każdy pozostały przypadek z przyczyną. Wartości nie w raporcie.
4. Dokumenty diagnozy (lokalnie, `audyt/diagnoza_2026_10_18/diag.py`, backend z gałęzi): KIO 578/11, KIO_uzp_16714, C047, C024, bip_7d1cff548e — przed/po: które osoby z odmian 1–5 przestały być jawne, czy pojawiły się nowe śmieciowe tokeny (linie typu „Protokolant”, „Al.”), Guard (blokady przed/po). Raport bez wartości (częściowo maskowane nazwiska).
5. Wynik = tekst, rzeczywiste tokeny, pełne wartości mapy i symulacja Przywróć; nie opierać PASS na braku podciągu ani na `guard_blocked`.

PASS: encje wielowierszowe nie przepadają; brak `\n` w tokenach/mapie; Przywróć 1:1; plik Mobile i dokumenty diagnozy wyraźnie lepiej, bez nowych wycieków i bez regresji encji jednowierszowych. Ocena okiem Pawła na KIO 578/11 i C047 w działającym programie przed merge. To nie jest naprawa C2/C3/A4 ani K5.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/ner_layer.py --symbol _process_ner
- TARGETS: backend/layers/ner_adapter.py --symbol _remap_ner_ids
- REASON: potwierdzić, że wartość encji traci `\n` w `_process_ner`, a adapter odrzuca ją w `_remap_ner_ids`; wybrać jedno miejsce rozbicia spanu.
GATE: zero nowych plików produktu; stare pliki powyżej limitu nie mogą rosnąć ponad regułę „nie pogarszaj”; >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI. Codex: BRIEF_ONLY precheck wykonalności i zakresu, bez implementacji.
