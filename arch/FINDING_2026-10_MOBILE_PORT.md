# FINDING 2026-10 — Analiza portu LynxMask Mobile → Desktop

- Autor: CC (chmura), 2026-10-16. Diagnoza i plan, **bez zmian w kodzie produktu** (Desktop i Mobile).
- Mobile: `paweltpietraszko-ship-it/LynxMask@master` `450204b`, sklonowane tylko do odczytu (`/home/user/paweltpietraszko-ship-it/lynxmask`). Desktop: gałąź `audyt/2026-10` (baza `main@9c1ad7a` + raport audytu `ecb20f2`).
- Kontekst i ID bugów: `arch/FINDING_2026-10_AUDYT.md`. **[S]** = sprawdzone (komenda/repro), **[P]** = podejrzewam.
- Prototyp i pomiary tylko w `audyt/`: `anchor_proto.py` (port A.1–A.12 + CLEANUP), `port_rules.py`, `bench_offline.py`, `docs_variants.py`. Logi w `audyt/logs/` (`port_rules.txt`, `bench_offline_diff.txt`, `docs_variants.txt`, `known_fixes_check.txt`, `morfeusz_mapping.txt`, `rota_prefix_variant.txt`).
- PII zamaskowane. Przykłady w tabeli reguł to moje syntetyczne zdania pod konkretne reguły (dobór celowy, nie losowa próba).

---

## 1. Streszczenie

Najwięcej daje **nie AnchorEngine, tylko trzy zasady z NameEngine/StructuralEngine/OcrNormalizer**:

1. **Słownik imion/nazwisk przed każdym filtrem odrzucającym** (Mobile `NameEngine.isAdjective`) → zamyka BUG-NER-PREFIX-FILTER. Benchmark: OSOBA 85→105/106, recall 88,2→92,1%, **0 nowych FP**. Dokumenty: 4/5 wycieków. Rota: 30%→5% form jawnie.
2. **IBAN przed wzorcami cyfr** (Mobile `IBAN_EARLY`) → zamyka BUG-IBAN-RECEPTA i **3/3 krytyczne wycieki IBAN w benchmarku** (critical leakage 7,7→6,1% w pakiecie).
3. **Normalizacja OCR zakotwiczona** (telefon kończy się cyfrą, spacje e-mail tylko przy `@`) → zamyka BUG-OCR-NORMALIZER-WORDS i BUG-GLOBAL-SPACE-GLUE. To warunek działania kotwic tytułów („mec.”).

**AnchorEngine** jako post-pass: benchmark +1 encja / +31 FP. Na moich przykładach 22→32/35. Na dokumentach dokłada trafienia (telefon bez wzorca, data urodzenia słownie, nr lokalu, nr umowy/FV), ale nie zamyka żadnego wycieku z audytu. Warto portować wybiórczo (A.7, A.10, A.11e, A.12/A.12c, A.1, CLEANUP z mapą) i dopiero po punktach 1–3. „Rundy 2” nie odtwarzać.

---

## 2. Mapa warstw

| Kolejność Mobile (`PseudonymEngine.kt:22-31,242-388`) | Plik Mobile | Odpowiednik Desktop (`pipeline_new.py:85-104`) | Uwagi |
|---|---|---|---|
| W0 normalizacja OCR | `OcrNormalizer.kt` | `layers/ocr_normalizer.py` (krok 1) + `layers/ner_adapter._fix_ocr_email` (przed NER) | Desktop to port z Kotlina, ale poszerzony w złą stronę (telefon, e-mail globalnie) |
| (SESJA_XXXXXX) | `PseudonymEngine.kt:240` | brak — Desktop dopisuje nagłówek PSE w API | — |
| W0b AddressEngine (jedyny właściciel ADRES, **przed** NameEngine) | `AddressEngine.kt:65` | `layers/address.py` — po `extract_ner_results`, przed `apply_ner_layer` | podobna intencja; brak STREET_CITY („ul. X 5, Miasto”) |
| W2 StructuralEngine (IBAN_EARLY pierwszy; S5 sumy PESEL/NIP) | `StructuralEngine.kt:256-268` | `identity`, `credentials`, `financial`, `legal`, `numeric`, `contact`, `amount`, `verbal_amount` | w Desktop `credentials` stoi przed `financial` → BUG-IBAN-RECEPTA |
| W2b PESEL kształt + suma (bez kotwicy) | `PseudonymEngine.kt:294` | `identity` + `validation` (stdnum, tylko z anonymizerem) | — |
| W3 NameEngine: czarna lista kontekstowa + słowniki (bez NER) | `NameEngine.kt:695+` | **spaCy NER** (`ner_layer`, `ner_adapter`) | inny mechanizm; Mobile chroni słownik przed filtrami, Desktop odwrotnie |
| W3c propagacja form nazwisk | `PseudonymEngine.kt:303-347` | `ner_adapter._propagate_osoba` + `ner_variants` | — |
| W4a UserDictionary jako **zbieracz resztek** | `PseudonymEngine.kt:349-369` | `trie_layer` jako **pierwsza** warstwa (L0b) | Mobile przeniósł słownik na koniec, bo „kradł fragmenty e-maili” — to samo widać w Desktop (tokeny w środku e-maila, BUG-SEED-DEAD) |
| W4b AnchorEngine | `AnchorEngine.kt` | **brak**; `fallback` (8+ cyfr) to jedyny „zbieracz” | — |
| (Runda 2 — usunięta 14.07) | `PseudonymEngine.kt:33-35,378-383` | — | 0 tokenów na 300 dokumentach (StressBenchmarkTest) → **nie odtwarzać** |
| W5 flagi algorytmiczne | `NameEngine.detectAlgorithmicFlags` | brak | — |
| W6 OutputGuard (RED/YELLOW, **tylko ostrzega**) + GuardAllowlist (exact match) | `OutputGuard.kt`, `PseudonymEngine.kt:388-396` | `output_guard.py` (**blokuje**, S4) + allowlista substring | inna filozofia; S3/S4 Desktop zostają |

**Gdzie AnchorEngine w `pipeline_new.py`:** jako ostatnia warstwa, po `apply_validation_layer` (l.103-104), przed `_apply_guard`. Zasada Mobile: „kotwice luźne wyłącznie na resztkach, po precyzyjnych regułach”. Musi przydzielać tokeny przez `state.allocator.allocate()` i sprawdzać `is_occupied`/overlap z istniejącymi tokenami (jak `matchOverlapsToken`). Własny licznik powtórzyłby BUG-TOKEN-COLLISION. W Express (`run_pipeline_express`) też na końcu.

---

## 3. Tabela reguł AnchorEngine

Kolumna „stan Desktop” = wynik `audyt/port_rules.py` (pipeline Desktop ze spaCy, świeży profil). „OK” znaczy, że wartość PII zniknęła z wyniku. Pełne wejścia/wyjścia: `audyt/logs/port_rules.txt`.
**Wynik zbiorczy [S]:** przypadki PII 35 — Desktop 22, Desktop + kotwice 32. FP wprowadzone przez kotwice: 2 (A.7, A.12).

| ID | plik:linia Mobile | Co łapie | Stan Desktop (dowód) | Werdykt | Szkic dla Pythona |
|---|---|---|---|---|---|
| A.1 FIRMA | `AnchorEngine.kt:102-110` | 1–7 słów z wielkiej litery przed formą prawną, także `S,A,` / `sp,j,` | `Hyd***** Serwis S,A,` → `FIRMA_001,A,` (OK, resztka „,A,”); `Zie***** sp,j,` → **jawne** | **PORTOWAĆ** | `LEGAL=r"(?:Sp[.,]\s*z\s*o[.,]o[.,]…|S[.,]A[.,]|sp[.,]j[.,]|…)"`, `W=r'[A-ZŁŚŹĆŃĄĘÓŻ][\w\-"„]{0,40}'`, `W(?:[^\S\n]+(?:W|[iz&])){0,6}[^\S\n]+LEGAL` (`anchor_proto.py`) |
| A.2 EMAIL | `:153` | `@` + rozszerzenie w lewo (1 słowo) / w prawo, spacje OCR wokół `@` i `.` | `jko*****@int****. pl` OK; `ann* now***@ poczta .pl` → zostaje „ann*” (oba warianty) | **JUŻ JEST**; resztę zamyka OCR_EMAIL_LOCALSPACE (§4) | — |
| A.2b osierocona domena | `:166` | `@domena .pl` po tokenie | `biu**@kan*** .pl` OK | **JUŻ JEST** | — |
| A.3 TELEFON | `:202-209` | `+48/+4B/0048/tel/kom/fax/mobile/gsm/wew/t:` + ciąg cyfropodobnych | `tel. 5O1 234 S67`, `kom.: (22) 765-…`, `+4B 601…` → OK (zostaje prefiks „+4B”) | **JUŻ JEST** (prefiks → CLEANUP) | — |
| A.4 PESEL | `:222-225` | `pe[s5][e3][lL1]` + 9–11 cyfropodobnych | `PESEL: 9OO4O5l2345`, `PESEL 900405 12345` → OK | **JUŻ JEST** | — |
| A.5 NIP | `:247-250` | `N[IiLl1]P` + do 25 znaków etykiety (także `\n`) + 10 cyfropodobnych | `NIP: 526-O2l-15-8l`, `NIP (jeśli dotyczy):\n526…` → OK | **JUŻ JEST** | — |
| A.5b kształt z myślnikami | `:257-260` | `D{2,4}-D{2,4}(-D{2,4})+` bez słowa-kotwicy | maskowane już dziś, także daty `12-03-2024` (FP po stronie Desktop) | **NIE PASUJE** — dubluje kształt, który Desktop już łapie (zakaz „kształt bez kotwicy”) | — |
| A.6 IBAN | `:267-270` | `PL` + 20–42 cyfropodobnych | `PL 27 1l40 2OO4 …` → OK | **JUŻ JEST** jako wzorzec; **PORTOWAĆ kolejność** (IBAN_EARLY, §4). [S w prototypie] klasa `[D \t\-]{20,42}` zjada następną literę cyfropodobną („… 5387 ok” → zostaje „k”) — to samo w Mobile [P: identyczna semantyka java.util.regex] | — |
| A.7 data urodzenia | `:297-300` | `ur./u[nr]./dob/urodzon…/data urodzenia` + ciąg + do 2 słów (bez innych kotwic) | `ur. 21O5.l979` → **jawne** (normalizator zmienia na `2105.l979`, nie maskuje); `urodzony dnia 8 k***** 1963` → **jawne**; w dokumencie „Data urodzenia słownie: pie***** sty*****” → jawne | **PORTOWAĆ** | `KW=r"(?:\bur\b\.?|u[nr]\.|\bdob\b[^\S\n]*:?|…|data[^\S\n]+urodzenia[^\S\n]*:?)"`, `KW+r"[^\S\n]*"+D+r"\S*(?:[^\S\n]+(?!(?:PESEL|NIP|…)\b)\S+){0,2}"`. FP: połyka do 2 słów („w Radomiu”) — akceptowane w Mobile |
| A.7b data → kotwica wstecz | `:314-330` | data `d.m.r` + `u r`/`u.r.` w oknie 60 zn. | `u r. 12.03.1985` → OK (Desktop maskuje daty jako NUMER) | **JUŻ JEST** | — |
| A.8 SYGNATURA | `:349-353` (walidacja `:41-47`) | `sygn.`/`sygn akt`/`sygnatur…` → do końca linii; pełne słowo walidowane Morfologikiem | `sygn. akt I C 1234/22`, `Sygn. Km 155/23` → OK (`Sygn.NUMER` — sklejone, BUG-GLOBAL-SPACE-GLUE); „sygnatura biologiczna” → bez FP | **JUŻ JEST** (`layers/legal.py`); maskowanie do końca linii zwiększyłoby nadmaskowanie (benchmark: „Syg* akt: … Wyg*****…”) | — |
| A.8kw KRS/KW | `:358-361` | `\bKRS\b`/`\bKW\b` + następny token | `KW: KR1P/…`, `KRS 0000…` → OK; kotwica dokłada FP „KRS nr”, „KW nr”, „KRS ===” | **NIE PASUJE** (Desktop `credentials` łapie; kotwica dodaje tylko FP) | — |
| A.9b KWOTA prefiks | `:368-371` | `kwota/suma/wartość/wynagrodzenie:` + liczba (D w grupach) | `Wynagrodzenie: 4 5OO,OO zł` → **jawne** | **PORTOWAĆ** (decyzja OWNERA, KWOTA to nie PII osobowe) | `(?:kwot[aęą]…|wynagrodzeni\w{0,4})[^\S\n]*:?[^\S\n]*`+liczba+`(?:zł|z[1l]|PLN|EUR…)?` |
| A.9 KWOTA sufiks | `:388-391` | liczba (pierwszy znak cyfra, dalej D) + waluta, także `z1/zl` | `1 250,5O PLN` → **jawne** | **PORTOWAĆ** (j.w.) | `(?<![A-Z0-9_])[0-9][D,.]*(?:[^\S\n]D{1,3})*(?:[,.]D{1,2})?[^\S\n]*(?:zł|z[1l]|PLN|…)(?![a-ząćęłńóśźż])` |
| A.9c KWOTA kształt `,dd` | `:423-426` | liczba + separator + dokładnie 2 cyfropodobne | `1 234,56` → **jawne**; FP kotwicy [S]: „3. sz”, „1. Os”, „06.07” (litery s/z/O w części dziesiętnej) | **PORTOWAĆ Z POPRAWKĄ**: część dziesiętna musi mieć ≥1 prawdziwą cyfrę (to samo FP istnieje w Mobile) | jak w Mobile + `(?=[^\S\n]?[,.][^\S\n]?\d|…\d)` dla ogona |
| A.9d KWOTA mnożnik | `:441-444` | cyfry + `tysi…/milion…/miliard…` | `15 tysięcy złotych` → OK (`verbal_amount`) | **JUŻ JEST** | — |
| A.10 OSOBA po tytule | `:456-466` (walidacja `:60-64`) | `dr (hab.)/prof./mgr (inż.)/inż./adw./mec./lek. (med.)` + 1–2 słowa z wielkiej litery; blokada tylko OSOBA_DENYLIST | `dr hab. Kow*****` → **jawne** (filtr prefiksu); `mec. Zdzisław Brz***…` → **jawne** także z kotwicą, bo `_fix_ocr_email` skleja „mec.Zdzisław” [S: na surowym tekście kotwica maskuje]; `lek. med. Ann* Wiś****-Kot` → `OSOBA_001-Kot` (resztka nazwiska) | **PORTOWAĆ po LYNX-T11 (sklejanie)**; odstępstwo do decyzji OWNERA: `lek\.` z wymaganą kropką (FP w dokumentach: „lek będzie wypisany” — `(?i)` + „lek” bez kropki) | regex z `anchor_proto.py` + `validate`: żadne słowo poza tytułem ∉ OSOBA_DENYLIST (88 słów z `NameEngine.kt:291`) |
| A.11 ADRES prefiks | `:488-491` | `ul./al./os./pl.` + 1–3 słowa | `ul. Gda****-Sop**** 3/1` → OK | **JUŻ JEST** | — |
| A.11c/d miasto przy tokenie | `:509-531` | słowo ze słownika miast/ulic tuż po/przed `ADRES_NNN` | `ul. Pol** 5, Rad**` → miasto **jawne** w obu (przecinek blokuje A.11c — znane w Mobile) | **NIE PORTOWAĆ A.11c/d**; zamiast tego **STREET_CITY** z `AddressEngine.kt:81-108` | `ul.[^\S\n]*Nazwa[^\S\n]*nr[^\S\n]*,[^\S\n]*Miasto` z walidacją miasta w `cities_forms.json` |
| A.11e nr budynku/lokalu | `:548-567` | `\d{1,4}[A-Za-z]?/\d{1,2}` (dokładnie 2 segmenty) + kod pocztowy / ADRES / miasto w oknie ±100 | `lokal 15/4, 00-950 …` → „15/4” **jawne** | **PORTOWAĆ** | jak w Mobile (`anchor_proto.py`, A.11e) |
| A.12 nr dokumentu | `:597-628` | `Nr/Numer (+≤2 słowa)/VAT` + id z cyfrą, sygnał `faktur|umow|zlecen|…` w 60 zn. wstecz | `FAKTURA VAT\nNr FV-…` → OK; `UMOWA ZLECENIA\nnr U-0***/2023` → **jawne**; FP kotwicy: „punkt nr 5.2” przy „VAT” w oknie | **PORTOWAĆ** (FP do zaakceptowania przez OWNERA albo węższe okno) | jak w Mobile |
| A.12c FV | `:641-670` | `FV/F.V./f-ra` + id (prefiks) albo `id/FV` (sufiks) | `FV2026…W012` → zamaskowane, ale jako **OSOBA** (zły typ); `260712/FV` → **jawne** | **PORTOWAĆ** | jak w Mobile |
| CLEANUP | `:679-698` | usuwa sieroce `+48/+/tel./kom./ul.` przed tokenem i doklejone ogony `TOKEN/xxx` | `+4B NUMER`, `tel. +NUMER` → czyści; `OSOBA_001-Kot` → usuwa „-Kot” **bez dopisania do mapy** [S] → Przywracanie zgubi tekst | **PORTOWAĆ Z POPRAWKĄ**: ogon dopisywać do wartości tokenu (dotyczy też Mobile) | `re.sub(TOK+r"(?:[/\-.](?!TOK)[A-Za-z0-9]+)+", …)` + `rev[tok] += ogon` |

Szczególnie (pkt 2 polecenia): e-mail rozbity po `@` — Desktop już łapie (A.2/A.2b JUŻ JEST, zostaje „ann*” przed spacją). NIP/IBAN/PESEL z literami cyfropodobnymi — Desktop łapie wszystkie warianty z tabeli (jego normalizator ma tę samą klasę D). Tytuł + nazwisko — **brak w Desktop**, port wartościowy. Telefon po „tel.” — Desktop łapie, ale jego normalizator psuje słowa za numerem (§4). Sygnatury — Desktop łapie.

---

## 4. Weryfikacja 5 znanych poprawek z Mobile

| Bug (audyt) | Poprawka w Mobile | Czy naprawia przypadek Desktop? (dowód: `audyt/logs/known_fixes_check.txt`) |
|---|---|---|
| BUG-IBAN-LETTERS | `OutputGuard.kt:75` `\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}\b` + `:88` tolerancyjny `PL[A-Z0-9\s]{14,40}` (≥10 cyfr) | **Częściowo.** Litery w BBAN Desktop już łapie (obalone w audycie). Wzorzec Mobile **usuwa nadmierne zamazanie** („…9268 19 W TERMINIE 7 DNI” → Mobile kończy na „9268”), ale **gubi ostatnią krótką grupę** („19”, „78”, „01S” zostają po zamazaniu; w Desktop i tak blokada HIGH). Małe litery: żaden nie łapie. „PL65 51 97 93 13” łapie tylko tolerancyjny wzorzec PL (u Mobile jako ostrzeżenie). Rekomendacja: grupy po 4 + końcówka `(?:\s?[A-Z0-9]{1,4})?`. |
| BUG-NER-FP | `OSOBA_DENYLIST` (88 słów, `NameEngine.kt:291`) + `TITLE_ADJECTIVE_ENDINGS` z ochroną słownikową (`NameEngine.kt:402-437`) | **Na „Kont0” nie** (brak na liście; Morfeusz: `ign`). **Ale ujawnia odwrotny problem Desktop [S]:** filtr końcówek przymiotnikowych Desktop (`ner_layer.py`, `_ADJECTIVE_ENDINGS_RE`) odrzuca pojedyncze „Bar*******”, „Mac***”, „Now******” (żeńskie), „Kow******go”. Mobile naprawił to (BUG-BARTLOMIEJ-PRZYMIOTNIK-FIX: słownik imion/nazwisk sprawdzany przed regexem) → **nowy BUG-NER-ADJ-FILTER**, reproduktor `test_filtr_ner_nie_odrzuca_odmienionych_imion`. OSOBA_DENYLIST zamknąłby FP „Osoba”/„Zapłata” jako OSOBA (Desktop dziś je zachowuje). |
| BUG-INSTITUTION-FP | Mobile nie ma kategorii INSTYTUCJA (taksonomia: ORGANIZACJA) ani warstwy instytucji | **Nie dotyczy.** W Desktop już naprawione `(?-i:…)` (obalone w audycie). Pozostały BUG-NER-FIRMA-INST (IGNORECASE w `ner_layer.py:194`) — w Mobile brak odpowiednika do przeniesienia. |
| BUG-NIP-LEAK (3-2-2-3) | `StructuralEngine.kt` v2.2 (kontekstowy NIP 3-2-2-3) + A.5 (keyword + 10 cyfropodobnych) | **Już naprawione w Desktop** (obalone w audycie: pipeline i Guard). A.5 dokłada etykiety wieloliniowe — Desktop też je łapie (tabela §3). |
| BUG-INSTITUTION-ORDER | Mobile: AddressEngine **przed** NameEngine (analogiczna zasada „pełny kontekst pierwszy”) | **Już naprawione w Desktop** (NER → institution). Zasada Mobile nadal ważna dla ADRES (STREET_CITY przed luźnymi blokami). |

**Korekta do raportu audytu (BUG-TOKEN-RE-SPEC, naniesiona w `FINDING_2026-10_AUDYT.md`):** Mobile `TOKEN_RE = \b(…)_(\d{3})(?!\d)` (`PseudonymEngine.kt:89`). Zasada S2 dotyczy końca tokenu; `\b` na początku zostaje. `OSOBA_1001` i `PL6110NUMER_001` nie pasują także w Mobile — usunąłem je z testu. Realne odstępstwo Desktop: token przyklejony z tyłu (`OSOBA_001x`, `NUMER_004Teresa`). W pomiarze pakietu NER wziął „NUM**_004Ter***” za osobę właśnie z tego powodu.

---

## 5. Inne rzeczy z Mobile warte przeniesienia

| Element Mobile | Co zamyka w Desktop | Dowód / szacowany zysk |
|---|---|---|
| **Słownik przed filtrem** (`NameEngine.isAdjective` `:416-437`: surnamesForms/namesForms przed Morfologikiem i regexem; decyzja właściciela 14.07 „nazwisko ma się maskować ZAWSZE”) | BUG-NER-PREFIX-FILTER, BUG-NER-ADJ-FILTER | [S] benchmark: OSOBA 85→105/106, R 88,2→92,1%, FP bez zmian (`bench_offline` wariant `prefix`). Dokumenty: 4/5 wycieków z audytu. Rota prod: 18/60 → 3/60 form. Mój prototyp omija tylko blocklistę (nie filtr przymiotników), więc to dolna granica. |
| **Słowniki Mobile** (`assets/`: 3 609 imion ze zdrobnieniami vs 199 w Desktop; `surnames_extended.json` 38 783; formy żeńskie generowane; warianty ASCII; `city_surname_overlap.json` 769) | luki słownikowe (zdrobnienia w Rocie, rzadkie nazwiska, formy żeńskie — BUG-SEED-DEAD) | [S] na benchmarku i zdaniach Roty bez różnicy (oba korpusy zbudowane z list Desktop, więc tego nie zmierzą). [P] zysk na realnych dokumentach i zdrobnieniach. Same dane JSON — bez nowej biblioteki. |
| **IBAN_EARLY** (`StructuralEngine.kt:244-268`: IBAN pierwszy, zanim jakikolwiek wzorzec cyfr) | BUG-IBAN-RECEPTA (`PL6110…`) | [S] benchmark: 3/3 krytyczne IBAN naprawione, CLR 7,7→6,1% (w pakiecie). Dokument `doc_lvl0`: `PL6110` znika. Uwaga: wartość tokenu łapie końcowe `\n\n` (zmiana tekstu). |
| **OCR_PHONE_AFTER_KW** (`OcrNormalizer.kt:651-653`: litery tylko `lOIo`, koniec na `\d`) | BUG-OCR-NORMALIZER-WORDS („zglosil” → „2g10si1”) | [S] wzorzec Desktop (`ocr_normalizer.py:310-314`) poszerzony o `T,S,B,G,Z,z` i może kończyć się literą → zjada „) zglosil si”. Wzorzec Mobile tego nie robi. |
| **OCR_EMAIL_*** (`OcrNormalizer.kt:339-346`: spacje usuwane tylko przy `@`, `[^\S\n]`) | BUG-GLOBAL-SPACE-GLUE (`ner_adapter._fix_ocr_email`), warunek A.10 | [S] `_fix_ocr_email` skleja każde „x. Y”, a kotwica „mec.” przestaje działać. Desktop `ocr_normalizer._EMAIL_*` (l.130-140) używa `\s` (przekracza `\n`) — Mobile poprawił to 09.07 (BUG-EMAIL-CROSS-NEWLINE-FIX). |
| **OCR_EMAIL_LOCALSPACE** (`OcrNormalizer.kt:310,327`) | „ann* nowak@…” — imię przed spacją jawne | [S] przypadek z tabeli §3 (A.2). Mały zysk. |
| **UserDictionary jako zbieracz resztek (W4a)** | tokeny wewnątrz e-maili po seedzie (`OSOBA_964.OSOBA_2172@…`) | [S] przyczyna opisana w `PseudonymEngine.kt:349-353`; w Desktop trie stoi pierwsze (`[TRIE-L1]` — „priorytet nad regex/NER”). **Konflikt z decyzją w Desktop → OWNER.** |
| **Jeden `assignToken` dla wszystkich warstw** (`PseudonymEngine.kt:211-235`, dedup po wartości kanonicznej) | BUG-TOKEN-COLLISION | wzorzec architektoniczny (w Desktop: NER przez `TokenAllocator.allocate`). |
| **GuardAllowlist exact** (`PseudonymEngine.kt:390-395`: `matchedText.equals(value) && label == ruleType`) | BUG-ALLOWLIST-SUBSTRING | [S] porównanie wartości i etykiety zamiast podciągu komunikatu. |
| **Guard YELLOW: imię/nazwisko ze słownika niezamaskowane przy etykiecie lub obok tokenu OSOBA** (`OutputGuard.kt:115-180`) | siatka bezpieczeństwa na wycieki z BUG-NER-PREFIX-FILTER | [P] złapałaby „PRACOWNIKIEM:\nKat****** Wiś*******” (etykieta „pracownik”). W Desktop Guard blokuje, a lista HIGH w S4 jest zamrożona, więc tryb ostrzeżenie/blokada to **decyzja OWNERA**. |
| **D-klasa w Guardzie** (`OutputGuard.kt:17-25,74`) | Guard ślepy na „9OO4O512345” po OCR | [P] wyższy recall Guarda; w Desktop każde trafienie HIGH blokuje, więc więcej FP blokad → OWNER. |
| **OSOBA_DENYLIST** (88 słów) | FP „Osoba/Zapłata/Łączna” jako OSOBA | [S] Desktop dziś je zachowuje (§4). Potrzebne tym bardziej po wprowadzeniu „słownika przed filtrem”, bo Morfeusz daje tym słowom kwalifikator `nazwisko`. |

**Czego nie przenosić:** Runda 2 (usunięta w Mobile 14.07, 0 tokenów na 300 dokumentach; brief v2 przewidywał trywialną tokenizację, nie powtórny przebieg). A.5b i A.8kw (dublują Desktop i dokładają FP). A.11c/d (zastąpić STREET_CITY).

**Błędy Mobile znalezione przy okazji** (tylko do wiadomości; repo Mobile nietknięte): A.6/IBAN_EARLY zjada następną literę cyfropodobną; A.9c FP na literach w części dziesiętnej; A.10 `lek` bez kropki pod `(?i)`; CLEANUP gubi ogon z mapy; `Deanonymizer.restore` ma tę samą pętlę `replace` co Desktop (BUG-UNMASK-SUBSTRING); `OutputGuard.kt:60`/`Deanonymizer.kt:22` mają `\d{3}\b` zamiast `(?!\d)`. **Rozjazd kontraktu:** MASTER Mobile §9 („ZAMKNIĘTE 20.06”) mówi o formacie `TYP_XXXXXX_NNN` i 9 typach (FIRMA+INSTYTUCJA→ORGANIZACJA, TELEFON, SYGNATURA, DATA). Kod Mobile używa `TYP_NNN` i 6 typów (z FIRMA), a zamrożony `arch/spec.md` Desktop — `KATEGORIA_NNN` z INSTYTUCJA. → **OWNER_DECISION_NEEDED**.

### 5a. Zależności: MorfologikHelper ↔ Morfeusz (pkt 5 polecenia)

Da się odwzorować bez nowej biblioteki: `morfeusz2` jest już zależnością Desktop i działa natywnie na Linuksie. Oba słowniki dzielą tagset SGJP. [S] `audyt/logs/morfeusz_mapping.txt`:
- `tags(w).isEmpty()` (A.8, OcrNormalizer) ↔ wszystkie interpretacje Morfeusza mają tag `ign` („Kont0”, „Brz***…” → `ign`; „biologiczna” → `adj`, więc walidacja A.8 działa identycznie).
- `isAdjective(w)` ↔ wszystkie klasy = `adj` („rejonowy”, „biologiczna” → True; „Kowalskiego”, „Wiśniewskiej” → `adj+subst` → False, jak w Mobile).
- `isDefinitelyNotPerson` ↔ te same prefiksy klas.
- **Bonus Morfeusza:** kwalifikatory `imię`/`nazwisko`/`nazwa_pospolita`/`nazwa_geograficzna`. „Bar*******” → `imię`, „Wiś*******” → `nazwisko`, „piątku”/„niedzielę” → tylko `nazwa_pospolita`. To rozwiązuje FP seeda (BUG-SEED-DEAD) bez ręcznych list. Uwaga: „Osoba”, „Zapłata”, „Zając”, „Mazur” mają też `nazwisko`, więc OSOBA_DENYLIST nadal potrzebna.
- `LookupTables` (słowniki JSON) — czyste dane; formy żeńskie i warianty ASCII to proste generatory (`LookupTables.kt:94-98`).

---

## 6. Wynik pomiaru prototypu

**Benchmark offline** (`audyt/bench_offline.py`): ten sam zbiór 100 obrazów (seed 42) i ta sama ocena (`benchmark.analyze`/`build_report`). Baseline odtwarza przebieg HTTP 1:1 (R 88,2%, FP 307, CLR 7,7%, identyczne liczby per typ). Liczby z `summary.txt` każdego wariantu:

| Wariant | Recall | Precision | F1 | FP | Critical leakage | OSOBA |
|---|---|---|---|---|---|---|
| base (Desktop dziś) | 88,2% | 59,8% | 71,3% | 307 | 7,7% (14/181) | 85/106 |
| + AnchorEngine (post-pass) | 88,4% | 57,5% | 69,7% | 338 | 7,7% | 85/106 |
| + słownik przed filtrem (słowniki Desktop) | **92,1%** | **60,8%** | **73,2%** | 307 | 7,7% | **105/106** |
| + słownik przed filtrem (słowniki Mobile) | 92,1% | 60,8% | 73,2% | 307 | 7,7% | 105/106 |
| pakiet: słownik + IBAN_EARLY + telefon/e-mail z Mobile + AnchorEngine | **92,8%** | 58,1% | 71,5% | 346 | **6,1% (11/181)** | 105/106 |

Rozbicie [S] (`audyt/logs/bench_offline_diff.txt`):
- **Naprawione w pakiecie:** 20 OSOBA (wszystkie dzięki zasadzie słownika), 3 krytyczne IBAN (IBAN_EARLY), 1 nr umowy (A.12).
- **Nowe „FP” kotwic:** 25 to KWOTA (np. „25 tysięcy”) — benchmark nie ma KWOTA w ground truth, więc każdy token kwoty liczy jako FP; realne FP to „3. sz”, „06.07” (A.9c). 4 × NUMER to A.8 maskujące do końca linii; 2 × ORGANIZACJA to A.1 z dłuższym zakresem niż ground truth.
- **Pakiet dokłada 11 × OSOBA FP**, m.in. „NUM**_004Ter***” (token przyklejony do imienia + BUG-TOKEN-RE-SPEC) i słowa po zmianie spacji w tekście dla spaCy. Wniosek: zasadę słownika wdrażać razem z poprawką TOKEN_RE.

**Dokumenty z „Pliki testowe/”** (`audyt/docs_variants.py`), 5 wycieków z audytu:

| Wariant | Wycieki z audytu w wyniku | Tokenów razem |
|---|---|---|
| base | 5/5 | 281 |
| + AnchorEngine | 5/5 (żaden nie znika) | 298 (+17) |
| + słownik przed filtrem | 1/5 (zostaje `PL6110`) | 286 |
| pakiet | **0/5** | 301 |

17 tokenów kotwic na dokumentach:
- trafienia: kwoty (5), „Tel****: 22-456-789” (A.3 — telefon, którego Desktop nie złapał), data urodzenia słownie (A.7), „BUD*** S.A.” (A.1), „ul. Pol***” (A.11), „Gda**** prz*” (A.11d);
- FP: „1. Os” (A.9c), „lek będzie wypisany” (A.10, tylko bez pakietu), „KW nr” / „KRS nr” / „KRS ===” (A.8kw), „num** fak**** 9” (A.12, częściowe).

**Minimalne przykłady** (§3): 22 → 32/35 przypadków PII, 2 nowe FP. Pozostałe 3 wymagają elementów spoza AnchorEngine (OCR_EMAIL_LOCALSPACE, naprawa sklejania spacji, STREET_CITY).
**Zdania Roty** (`audyt/logs/rota_prefix_variant.txt`): prod 18/60 (30%) → **3/60 (5%)** przy zasadzie słownika (słowniki Desktop), 4/60 przy słownikach Mobile; 0 tokenów nie-osób. Reszta to osoby, których spaCy nie wykrył — dla Roty nadal potrzebny `known_people`.
**Reproduktory:** IBAN-RECEPTA, NER-PREFIX-FILTER, OCR-NORMALIZER-WORDS i GLOBAL-SPACE-GLUE mają przypisany element Mobile, który je zamyka (wyżej). Dodany reproduktor BUG-NER-ADJ-FILTER. `test_audyt_2026_10.py`: 26 xfailed (`audyt/logs/pytest_audyt_xfail.txt`).

---

## 7. Kandydaci na Taski dla architekta (propozycje, bez briefów)

| ID | Cel (jedno zdanie) | Pliki Desktop | Waga | Zależność od Tasków z FINDING_2026-10_AUDYT |
|---|---|---|---|---|
| LYNX-P01-DICT-FIRST | Słownik imion/nazwisk (i kwalifikator Morfeusza `imię`/`nazwisko`) sprawdzany przed blocklistą i filtrem przymiotników; OSOBA_DENYLIST z Mobile. | `ner_layer.py`, `ner_blocklist.py` | KRYT | realizuje **LYNX-T01**; wdrażać razem z **LYNX-T08** (TOKEN_RE), inaczej FP „NUMER_004Imię” |
| LYNX-P02-IBAN-EARLY | IBAN (`PL` + cyfropodobne) przed credentials/innymi wzorcami cyfr. | `pipeline_new.py`, `layers/financial.py`, `credential_patterns.json` | WYS | realizuje **LYNX-T07** |
| LYNX-P03-OCR-ANCHORED | Telefon po „tel.” wg Mobile (koniec na cyfrze) i naprawa spacji e-mail tylko przy `@`, bez przekraczania `\n`; usunąć globalne sklejanie z `_fix_ocr_email`. | `layers/ocr_normalizer.py`, `layers/ner_adapter.py` | WYS | realizuje **LYNX-T11**; warunek P05 (A.10) |
| LYNX-P04-DICT-DATA | Przenieść słowniki Mobile (imiona ze zdrobnieniami, `surnames_extended`, formy żeńskie, ASCII, `city_surname_overlap`) jako dane. | `backend/*.json`, `seed_profile.py`, `ner_blocklist.py` | ŚRED | po **LYNX-T04** (seed) i P01; ważne dla **LYNX-ROTA-MASK-CORE** |
| LYNX-P05-ANCHOR-LAYER | Warstwa kotwic na końcu `pipeline_new` przez `TokenAllocator`: A.1, A.7, A.10 (`lek.` z kropką — OWNER), A.11e, A.12, A.12c, A.9/A.9b (+A.9c z cyfrą w części dziesiętnej — OWNER), CLEANUP z dopisaniem ogona do mapy. | nowy `layers/anchor.py`, `pipeline_new.py` (obie ścieżki: pełna i Express) | ŚRED | po **LYNX-T03** (alokator), P03, **LYNX-T08** |
| LYNX-P06-STREET-CITY | Reguła „ul. Nazwa nr, Miasto” (STREET_CITY) ze słownikiem miast. | `layers/address.py` | NISK | — |
| LYNX-P07-GUARD-MOBILE | Allowlista exact (wartość + kategoria); końcówka IBAN z grupami po 4; decyzja OWNERA o ostrzeżeniu (nie blokadzie) „nazwisko ze słownika przy etykiecie / obok OSOBA”. | `output_guard.py`, `pipeline.py`, `pseudominizer_api.py` | ŚRED | uzupełnia **LYNX-T06**; S4 — decyzja OWNERA |
| LYNX-P08-DICT-ORDER (decyzja OWNERA) | Czy słownik klienta (trie) ma być zbieraczem resztek jak w Mobile (W4a), czy zostać pierwszą warstwą (`[TRIE-L1]`). | `pipeline_new.py`, `layers/trie_layer.py` | ŚRED | wpływa na **LYNX-T04** i **LYNX-ROTA-MASK-CORE** |
| LYNX-P09-CONTRACT-SYNC (OWNER_DECISION_NEEDED) | Ustalić jeden kontrakt tokenu/taksonomii: MASTER Mobile §9 (`TYP_XXXXXX_NNN`, 9 typów) vs kod Mobile (`TYP_NNN`, 6 typów) vs `arch/spec.md` S2 (`KATEGORIA_NNN`, INSTYTUCJA). | `arch/spec.md` (po decyzji), oba repo | WYS | blokuje ostateczny kształt **LYNX-T08** |

Kolejność rekomendowana: P01 (+T08) → P02 → P03 → P04 → P05 → P07 → P06; P08 i P09 to decyzje równoległe.
