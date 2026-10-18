# LYNX-ARCH-CANDIDATES — propozycja CC: silniki-kandydaci → arbiter → jedna podmiana

STATUS: cc_proposal (CC) → Architekt: brief(y) faz → Codex precheck → CC ocena + implementacja na osobnej gałęzi → A/B → decyzja Pawła.
POCHODZENIE: plan uzgodniony z Pawłem 2026-10-18 (BOARD `LYNX-ARCH-CANDIDATES`); diagnoza `arch/DIAGNOZA_2026-10-18.md` (gałąź `task/LYNX-DIAGNOZA-2026-10-18`, r2 po ocenie Codexa); ultrareview rdzenia F1–F10 (BOARD `LYNX-K2-INPUTS-ULTRAREVIEW`); findingi `LYNX-K1-INPUTS-MULTILINE`.
Model jest propozycją Pawła, którą CC ocenił i popiera z uzasadnieniem w §2. Nie jest to decyzja OWNERA w rozumieniu procesu. Kontrakty S1–S6 (`arch/spec.md`) pozostają bez zmian. Jedyne miejsce, które może ich dotknąć, jest opisane jako pytanie otwarte w §8.

## 1. Problem: łańcuch warstw przepisujących tekst

Dziś `pipeline_new.run_pipeline_new` (Full) to 16 kroków. **Każdy zmienia `state.text`**, a następny widzi już tekst po zmianach poprzedniego:

`ocr_normalizer` (przepisuje cały tekst: skleja, usuwa spacje, zamienia litery na cyfry) → `trie` (profil biura) → `identity` → `credentials` → `financial` → `legal` → `numeric` → `contact` → `amount` → `verbal_amount` → `extract_ner_results` (SpaCy na tekście po 9 warstwach) → `address` → `ner` (globalne zamiany napisów, propagacja nazwisk, inicjały, imiona) → `institution` → `validation` → `fallback`.

`TokenAllocator.reset_spans()` przed każdą warstwą: współrzędne poprzedniej warstwy nie pasują już do nowego tekstu, więc ochrona spanów działa tylko w obrębie jednej warstwy. `ConflictResolver` w `pipeline_core.py` istnieje, ale nikt go nie wywołuje.

Objawy, które wynikają wprost z tej budowy (wszystkie zaobserwowane i odtworzone, źródła w nawiasach):
- **Kolejność decyduje o wyniku zamiast dowodów.** Detektor, który działa wcześniej, wygrywa, nawet gdy ma słabsze uzasadnienie. Przykłady: instytucje jako FIRMA (C1), bo NER działa przed `institution`, a komentarz `BUG-INSTITUTION-ORDER` pokazuje, że kolejność stroiło się ręcznie; „Dz. U.” jako ADRES (C5).
- **SpaCy widzi tekst już z tokenami** (`ADRES_001`, `NUMER_003`), a nie zdanie użytkownika. Komentarz v0.4 w `pipeline_new.py` opisuje obejście tego jednego przypadku (NER przed adresem).
- **Podmiana w środku wyrazu / sklejone tokeny** (MAP-FIDELITY D2: 33 → 1 po łatce, ale klasa pozostaje, bo każda warstwa ma własne granice).
- **Przywróć ≠ wejście w 13/17 dokumentów diagnozy już na bazie.** Normalizacja OCR zmienia tekst użytkownika, a mapa przywraca tylko tokeny (K1-INPUTS (4), LYNX-TEXT-FIDELITY-F3, LYNX-SHADOW-NORMALIZE).
- **Encja przepada między krokami.** Przykłady: span SpaCy z `\n` nie pasował do tekstu po normalizacji (NER-MULTILINE); forma „z o.o” dostaje token, a nazwa firmy zostaje jawna (A4).
- **Propagacja i odmiany przez globalne `replace`** dają różne osoby pod jednym tokenem albo inną formę po Przywróć (ultrareview F8/F9).

Każdą z tych klas łatano punktowo w łańcuchu i każda łatka dodawała kolejną zależność od kolejności. Dlatego Paweł postawił regułę: w starym łańcuchu nie łatamy już propagacji, K2, instytucji jako FIRMA, sklejonych list ani OCR, a te błędy stają się testem odbioru nowego modelu.

## 2. Model docelowy

```
tekst użytkownika (ORYGINAŁ, nigdy nie zmieniany)
   │
   ├─ widok znormalizowany (kopia OCR + mapa przesunięć → oryginał)   [tylko do czytania]
   │
   ├─ silniki-kandydaci (każdy czyta oryginał lub widok, NIC nie zmienia)
   │     → Candidate(start, end w ORYGINALE, typ, wartość = oryginał[start:end], silnik, dowody[])
   │
   ├─ arbiter: rozstrzyga nakładanie i odrzuca kandydatów bez wystarczających dowodów
   │     → rozłączne spany + uzasadnienie każdego
   │
   ├─ łączenie encji (K2): które spany to ta sama osoba/firma → wspólny klucz
   │
   ├─ JEDNA podmiana na oryginale (od końca), tokeny przez wspólny TokenAllocator
   │
   ├─ silniki resztkowe (fallback cyfr, AnchorEngine): czytają oryginał z wyciętymi spanami
   │     → kandydaci → ten sam arbiter → druga, ostatnia podmiana tylko na resztkach
   │
   └─ Output Guard (bez zmian, S3/S4)
```

### 2.1 Kandydat i dowody
`Candidate` to dane bez logiki: `start`, `end` (współrzędne w oryginale), `type` (taksonomia S2 bez zmian), `value` (dosłowny wycinek oryginału), `engine`, `evidence: list[Evidence]`. `Evidence` ma postać `(rodzaj, siła)` z zamkniętego słownika rodzajów, na przykład:
- `CHECKSUM` (PESEL/NIP/REGON/IBAN z poprawną sumą kontrolną),
- `KEYWORD` („PESEL:”, „NIP”, „ul.”, „Sygn. akt”),
- `FORMAT` (sam kształt),
- `LEGAL_FORM` („Sp. z o.o.”, „S.A.”),
- `DICT_SURNAME` / `DICT_FIRSTNAME` (słownik + pospolitość),
- `TITLE` (Pan/Pani/adw./r.pr.),
- `ROLE_ANCHOR` (Przewodniczący:, Protokolant:),
- `NER_SPACY` / `NER_HERBERT` (z wynikiem modelu),
- `PROFILE` (słownik biura/użytkownika — jawna wola użytkownika),
- `INSTITUTION_LIST`,
- `REPEAT` (to samo w dokumencie jako encja z silnymi dowodami).

„Adres ma udowodnić, że jest adresem” (Paweł) oznacza tyle, że kandydat ADRES bez dowodu (prefiks ulicy + numer, kod pocztowy + miejscowość, „zam.”/„adres:”) nie przechodzi arbitra. Przypadek „ul. Nr 223” w cytacie „Dz. U.” nie ma numeru budynku ani kodu, więc odpada bez osobnej łatki (C5).

### 2.2 Silniki-kandydaci (mapowanie z dzisiejszego kodu)
Logika wykrywania istniejących warstw zostaje. Zmienia się tylko wyjście: zamiast `state.text = …` warstwa zwraca listę kandydatów. Każda warstwa ma już pętlę `finditer → allocate(start, end) → sklej tekst`, więc wydzielenie `find(text) -> list[Candidate]` to mechaniczne rozcięcie, a nie przepisanie reguł.

| Silnik | Źródło | Uwagi |
|---|---|---|
| Strukturalny | `identity`, `credentials`, `financial`, `legal`, `numeric`, `contact`, `amount`, `verbal_amount` | czyta widok znormalizowany (OCR cyfr); span mapowany do oryginału |
| Adres | `address` | dowód obowiązkowy (§2.1) |
| Instytucja | `institution` + lista instytucji | w konflikcie z FIRMA/OSOBA wygrywa dowodem `INSTITUTION_LIST` (C1) |
| Firma — forma prawna | nowy (LYNX-FIRMA-NO-CANDIDATE) | kotwica `LEGAL_FORM`, span w lewo do granicy nazwy |
| NER SpaCy | `spacy_ner` / `ner_layer` (bez podmian) | czyta ORYGINAŁ, a nie tekst z tokenami |
| NER HerBERT | `~/lynx_models/herbert-polish-legal-ner` | drugi głos; tryb pracy wg ODLOZONE (dwa poziomy) |
| Słownik nazwisk | zasoby Mobile `surnames_extended.json`, `city_surname_overlap.json` | niepospolite same; nazwisko-słowo tylko z `TITLE`/`ROLE_ANCHOR`/imieniem |
| Profil biura (trie) | `trie_layer` | `PROFILE` = najsilniejszy dowód (wola użytkownika) |
| Resztkowe | `fallback`, AnchorEngine (port wybiórczy, LYNX-CONTEXT-ANCHORS) | tylko na resztkach, nie zmieniają już przyjętych spanów |

### 2.3 Arbiter
Jedna funkcja i jedna tabela reguł zamiast kolejności warstw:
1. **Rozłączność.** Nakładające się kandydatury rozstrzyga siła dowodów, a nie kolejność silników. Przy remisie wygrywa dłuższy span, czyli nadmaskowanie zamiast wycieku (zasada Pawła). Wynik jest zawsze rozłączny.
2. **Zgoda wielu silników** na ten sam span sumuje dowody, ale tylko z różnych rodzajów, żeby dwa regexy na ten sam kształt nie liczyły się podwójnie.
3. **Weto typu:**
   - `INSTITUTION_LIST` wyklucza FIRMA/OSOBA na tym samym spanie;
   - sama forma prawna bez nazwy nie jest FIRMA (A4);
   - wartość pasująca do `TOKEN_RE` nigdy nie jest kandydatem (S2/S3).
4. **Próg przyjęcia** dla każdego typu jest zapisany jawnie w tabeli i ustalony PRZED pomiarem A/B, a nie dopasowany do wyniku (por. ocena CC w LYNX-CONTEXT-ANCHORS).
5. **Ślad** każdej decyzji: silnik, rodzaje dowodów i powód odrzucenia. Trzymany tylko w pamięci, w odpowiedzi do debugowania i ewentualnie w UI („dlaczego to zakryto”). Bez wartości w logach (S5).

### 2.4 Łączenie encji (K2)
Po arbitrze spany OSOBA/FIRMA dostają klucz encji: ten sam napis to ta sama encja, a odmiana tego samego nazwiska (Morfeusz/lemat) przy tym samym imieniu lub tej samej osobie w dokumencie to też ta sama encja. Różne osoby o podobnym nazwisku (Nowak / Nowakowska, ultrareview F8) to różne encje. **Propagacja** polega na tym, że wystąpienie bez własnych dowodów, ale z dowodem `REPEAT` encji przyjętej w tym dokumencie, staje się kandydatem. Nie ma już globalnego `replace`.
Wpływ na mapę i Przywróć opisuje pytanie otwarte Q1 (§8).

### 2.5 Jedna podmiana i niezmiennik
Spany są rozłączne i leżą w oryginale, więc podmiana to jedno przejście od końca. Ta budowa daje dwa niezmienniki, które można testować mechanicznie na każdym dokumencie:
- **N1 — wierność dokumentu:** tekst poza spanami jest bajt w bajt taki jak wejście. Normalizacja nie dotyka wyniku, a dzisiejsze 13/17 przypadków Przywróć ≠ wejście znika z budowy.
- **N2 — brak sklejeń:** token zawsze zastępuje dokładnie `oryginał[start:end]`, a granice sprawdza arbiter raz, wspólnie dla wszystkich typów.

### 2.6 Widok znormalizowany (OCR)
`normalize_ocr` pozostaje, ale zamiast przepisywać tekst produkuje kopię plus mapę przesunięć (normalizator zmienia długość: usuwa spacje, skleja wiersze). Implementacja ma dwie opcje do decyzji w briefie: (a) śledzenie każdej podmiany regexu, (b) wyrównanie oryginału i kopii po fakcie (`difflib.SequenceMatcher`; zmiany są lokalne). Silnik, który znalazł „PESEL 9l0405l2367” w kopii, zgłasza span oryginału. Do mapy trafia dosłowny zapis z błędem OCR, a dowodem jest `CHECKSUM` liczony na kopii. To zamyka klasę LYNX-SHADOW-NORMALIZE / TEXT-FIDELITY-F3 / IBAN-OCR-PREFIX w całości, a nie punktowo.

## 3. Czego model NIE zmienia
- Format tokenu, `TOKEN_RE`, taksonomia, `.lynxdict` (S2, wspólne z Mobile, zmienia tylko Paweł).
- Output Guard i S3/S4 (blokada przy awarii zawsze; S4 do osobnej formalnej zmiany LYNX-SPEC-S4-GUARD-WARN).
- `TokenAllocator` jako jedyne źródło numerów (rozszerzony o klucz encji — §2.4).
- API `/preview`, `/preview-express`, UI.
- Reguły wykrywania istniejących warstw. W fazie 1 są tylko przeniesione, bez zmiany treści.

## 4. Fazy (osobna gałąź; każda faza osobny brief, A/B i ocena Pawła)

Nowy kod trafia do osobnego pakietu (`backend/engine/`: `candidate.py`, `arbiter.py`, `apply.py`, `view.py`, `link.py`, po jednym pliku na silnik). Każdy plik ma mniej niż 300 linii, a stare pliki nie rosną (uwaga Pawła o plikach-olbrzymach). Przełączanie: `ENGINE=candidates` w tym samym backendzie gałęzi. Dzięki temu oba modele liczą na identycznym kodzie wykrywania, a A/B porównuje tylko architekturę.

| Faza | Zakres | Co powinno się zmienić w A/B | Ryzyko |
|---|---|---|---|
| **F0** | szkielet: `Candidate`, arbiter (rozłączność + ślad), jedna podmiana, widok OCR z mapą przesunięć, testy N1/N2 | nic poza N1/N2 (silników jeszcze nie ma) | mapa przesunięć OCR |
| **F1** | silniki strukturalne + adres + instytucja jako kandydaci (wydzielone `find()`), weta typu | numery/kwoty/adresy ≥ stary łańcuch; C5 znika; Przywróć == wejście; sklejone tokeny 0 | adres bez dowodu = mniej ADRES → sprawdzić wycieki |
| **F2** | osoby i firmy: SpaCy na oryginale, forma prawna, słownik nazwisk, HerBERT; łączenie encji (K2) | A1–A5, C1–C3 z §7 diagnozy; brak różnych osób pod jednym tokenem | FP słownika/HerBERT; czas CPU |
| **F3** | resztkowe: fallback cyfr, AnchorEngine (wybiórczo) | resztki A1/A3; próg N/M z LYNX-CONTEXT-ANCHORS ustalony przed pomiarem | FP |
| **F4** | sprzątanie po decyzji Pawła: stary łańcuch usunięty (z martwym kodem `pipeline.py` za `USE_NEW_PIPELINE=True`, ~170 linii) | — | — |

Szacunek rozmiaru (do potwierdzenia przez Pawła PRZED kodem każdej fazy):

| Faza | Produkcja | Testy |
|---|---|---|
| F0 | ~350 | ~250 |
| F1 | ~250 (rozcięcie istniejących warstw, przeważnie przeniesienia) | ~200 |
| F2 | ~500 | ~300 |
| F3 | ~200 | ~150 |

F2 i F3 zależą od wyniku F1. Architekt może podzielić F2 na osoby i firmy.

## 5. Pomiar A/B (dla każdej fazy)
- Ten sam zbiór: 178 dokumentów `backend/dataset_real_public` przez działający `/preview`, profil Pawła (`ANONYMIZER_PROFILE_DIR`), backend gałęzi raz z `ENGINE=chain`, raz z `ENGINE=candidates`.
- Miary:
  1. sklejone tokeny;
  2. blokady Guarda (z rozbiciem na rzeczywistą wartość i śmieciową encję);
  3. Przywróć(Zamaskuj(x)) == x;
  4. nowe jawne słowa względem drugiej strony (wycieki w obu kierunkach);
  5. różne wartości pod jednym tokenem;
  6. liczba tokenów na 1000 słów (nadmaskowanie);
  7. czas na dokument.
- Lista kontrolna diagnozy §7 (A1–A7, B, C1–C6) z poziomami D/S/W/P/O, reproduktory K1-INPUTS-MULTILINE, K2-INPUTS-ULTRAREVIEW (F8/F9) i raporty Codexa jako testy odbioru.
- Odbiór: ocena okiem Pawła w działającym programie na plikach porównawczych. 17 dokumentów diagnozy to dev, a holdout nietknięty do odbioru końcowego.
- Codex odtwarza pomiar: skrypt w repo, SHA backendu i ścieżka danych lokalnych w wierszu BOARD.

## 6. Ryzyka i jak je ograniczyć
- **Czas.** SpaCy na oryginale zamiast dwóch przebiegów to zysk, ale HerBERT to 1–6 s do 10 tys. znaków i około 40 s przy 63 tys. (diagnoza §6). Maszyna biurowa jest 2–4× wolniejsza. Ograniczenie: decyzja z ODLOZONE (dwa poziomy) przed F2.
- **Regres przy rozcinaniu warstw** w F1. Ograniczenie: F1 nie zmienia reguł, a A/B na numerach musi dać ≥ starego łańcucha, zanim F2 ruszy.
- **Mapa przesunięć OCR** może źle wskazać granicę. Ograniczenie: test na wszystkich przykładach z testów normalizatora (33+) plus warunek, że kandydat z kopii, którego nie da się jednoznacznie zmapować, ma maskować szerzej, a nie przepadać.
- **Dwa modele w jednym backendzie** to tymczasowo więcej kodu. Ograniczenie: F4 usuwa przegrany model.

## 7. Prośba do architekta
1. Ocena modelu (§2) i jego granic (§3).
2. Brief **F0** (szkielet + niezmienniki N1/N2 + widok OCR) z TASK_SCOPE w nowym pakiecie i kryteriami A/B (§5).
3. Rozstrzygnięcie, czy Q1 (§8) wymaga formalnej zmiany kontraktu przed F2.

## 8. Pytania otwarte
**Q1 — jeden token na osobę a Przywróć (odpowiedź Pawła 2026-10-18).** Napisy „Kowalski”, „Kowalskiego” i „Jan Kowalski” dla jednej osoby dostają JEDEN token (`OSOBA_001`). Gdyby AI widziało kilka „osób”, pogubiłoby się i sens pseudonimizacji by się zatracił (Paweł). Przywróć w odpowiedzi AI wstawia jedną, pełną formę (np. imię i nazwisko w mianowniku), bo program nie wie, w jakim przypadku AI użyło tokenu. Odmiana może być niegramatyczna („w imieniu Jan Kowalski”), ale osoba zawsze się zgadza. Dokument źródłowy wraca dosłownie dzięki liście wystąpień w lokalnej mapie. Format tokenu bez zmian (S2, Mobile nie odczuje). Paweł o tym kompromisie: „Tak, pasuje”.
Dla architekta: lista wystąpień to nowy element mapy (dane lokalne, S5 bez zmian). Trzeba ustalić jego miejsce w formacie mapy i w szyfrowanym archiwum oraz zgodność ze starymi mapami.
Później, osobno: odmiana formy w odpowiedzi AI według słowa przed tokenem. **Morfeusz już jest w programie** (`anonymizer.py`, tryb `native`, w `/health`), ale Paweł pamięta, że kiedyś miał problemy z działaniem. Dlatego przed oparciem na nim czegokolwiek trzeba sprawdzić przy starcie, że naprawdę działa (zob. BOARD `LYNX-STARTUP-COMPONENTS`).

**Q2.** Express (bez NER) w nowym modelu to ten sam arbiter bez silników NER. Do potwierdzenia w briefie F1.

**Q3.** HerBERT domyślnie czy tylko „dokładne sprawdzenie”? Decyzja po pomiarze czasu na maszynie biurowej (ODLOZONE), przed F2.
