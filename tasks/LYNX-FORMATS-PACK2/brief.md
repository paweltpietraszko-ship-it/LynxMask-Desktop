# LYNX-FORMATS-PACK2 — data urodzenia ISO, forma prawna bez spacji, kody psute przez normalizator OCR (CC, 2026-10-21; poprawka bez Architekta)

Źródło: pomiar silnika (main `10e62d9`) na niezależnym zbiorze `rafalrudol/pl-pii-synthetic-v1` (HF, 3000 dok., 18 047 encji gold,
licencja „synthetic-eval-only”; lokalnie `%TEMP%\lynx_cc_review\plpii\`, poza repo): 99,3% encji zakrytych; jawne/częściowe wycieki
w trzech klasach. Paweł 21.10: „silnik działa, a pomyłki to wina OCR lub specyficznych zapisów”. Diagnoza i prototyp — pomocnik CC
(sweep 3000 dok. przed/po przez `run_pipeline_new`: wycieki DOB/ORG/PLATE 75/41/13 → 0/0/0, 0 nowych tokenów bez gold; lokalnie
`%TEMP%\lynx_cc_review\paczka2\`, `paczka3\`).

## Przyczyny
1. **Data urodzenia ISO** („ur. 1989-01-05”, 69 jawnych): `layers/amount.py` `_BIRTH_DATE_CTX_RE` wymaga dnia na początku, `_DATE_PL_RE`
   zna tylko DD.MM.RRRR; `identity.py` też. „13.08.1974” jest zakrywane w każdym kontekście (polityka: data podobna do urodzenia
   maskowana także bez „ur.”). Mobile: kotwica A.7 (`AnchorEngine.kt:297–300`) łapie ISO po „ur./data urodzenia”.
2. **Forma prawna bez spacji** („Sprzedawca: Gamma sp.j.”, 41 jawnych): firma powstaje wyłącznie z encji spaCy, a spaCy dla
   „Gamma sp.j.” bez kontekstu zwraca nic; `ner_layer._firma_bounds` / `firma_context.legal_form_entities` tylko rozszerzają istniejące
   encje. Mobile ma deterministyczny wzorzec formy prawnej (`NameEngine.kt:577–580`, użyty `:714–719`).
3. **Kody psute przez normalizator OCR** (tablice „PW YHU1N”, „RKFL9U.”; 13): `layers/ocr_normalizer.py` krok 13 (`_DIGIT_IN_WORD_RE`,
   :323–325, :523) zamienia na ślepo cyfrę 1/0 między literami na literę (`YHU1N` → `YHUiN`), więc wzorzec tablicy nie ma cyfry;
   `_UL_PREFIX_RE` (:149–153) zamienia „U. ” po cyfrze na „ul. ” (`RKFL9U. Adres` → `RKFL9ul. Adres`). Mobile zamienia cyfrę na literę
   tylko, gdy wynik jest rozpoznanym słowem (`OcrNormalizer.kt:123–129`, `:785–795`). Ten sam mechanizm tworzył fałszywe FIRMA typu
   „FBR HKiJC”.

## Zakres
1. **`backend/layers/amount.py`:** wzorzec daty ISO `RRRR-MM-DD` z rokiem 19xx/20xx (poprawny miesiąc 01–12 i dzień 01–31; bez cyfry
   lub „-cyfra” bezpośrednio obok) jako NUMER, obok `_DATE_PL_RE` — **ten sam zakres co DD.MM.RRRR** (wszystkie lata 19xx/20xx, nie tylko
   po „ur.”), żeby nie zostawiać dat urodzenia dzieci (dokumentacja medyczna). Token: sama data.
2. **`backend/firma_context.py` + `backend/ner_layer.py`:** skan formy prawnej niezależny od spaCy: forma `sp.z o.o.` (z dowolnymi
   spacjami/kropkami), `sp.j.`, `sp.k.`, `sp.p.`, `sp.k.a.`, `p.s.a.` — **z kropką po „sp”** (nie „spj”); nazwa w lewo istniejącymi
   regułami `_form_start`/`_name_start` (słowa z wielkiej litery/CAPS/cyfra w tej samej linii, stop na `:`, `,`, `;`, słowie z małej litery);
   bez nazwy z wielkiej litery — brak encji. Wynik jako encja FIRMA dołączana do encji spaCy **po** `_firma_bounds` i przed
   `legal_form_entities` (kolejność chroni `TestFirmaBounds`); encje nakładające się — bez duplikatów. `S.A.` i `s.c.` poza skanem
   (inicjały „Jan S.A.”, spaCy łapie S.A.). W `ner_layer.py` (596/600 l.) tylko import i zmiana jednego wywołania.
3. **`backend/layers/ocr_normalizer.py`** (696 l. — plik nie może urosnąć; zmiana w istniejących liniach): krok 13 (cyfra 1/0 → litera)
   tylko w słowach zawierających małą literę; WIELKIE słowa z cyfrą zostają (nazwiska CAPS naprawia dalej krok 15 `_de_leet` ze
   słownikiem imion/nazwisk); `_UL_PREFIX_RE` nie zamienia „U.” bezpośrednio po cyfrze.
- Bez zmian: format tokenów, spaCy, Guard, API, wzorzec tablic, polityka miejscowości.

TASK_SCOPE:
- backend/layers/amount.py
- backend/firma_context.py
- backend/ner_layer.py
- backend/layers/ocr_normalizer.py
- backend/tests/test_formats_pack2.py

## Odbiór
Testy celowane (`test_formats_pack2.py`): „Data urodzenia: ur. 1989-01-05”, „Urodzony 2021-03-14 w Radomiu” → data NUMER; „2026-13-40”
i „1989-01-05-001” nietknięte; „Sprzedawca: Gamma sp.j.”, „Beta Sp.k.”, „Delta sp.z o.o.” bez kontekstu → jedna FIRMA z nazwą;
„jak sp.j. wyżej”, „Dział Sprzedaży sp. Dziękujemy”, „Gamma spj” → bez FIRMA; „Kowalski i Wspólnicy Sp. k.” → nadal jedna FIRMA
(strażnik `TestFirmaBounds`); normalizator: „rej. PW YHU1N” i „RKFL9U. Adres” bez zmian, „Kowa1ski” nadal → „Kowalski”, „KOWA1SKI”
(słownik) nadal naprawiane; Przywróć 1:1 (wartości mapy = dokładny fragment źródła).
Pomiar (pomocnik CC): `pl-pii-synthetic-v1` przed/po (wycieki per etykieta, tokeny bez gold w dokumentach pozytywnych i negatywnych)
**oraz** ponowne porównanie z Mobile (693 teksty) — żadna nowa klasa nadmaskowania > 5 bez wyjaśnienia; osoby gold `dataset_clean` bez
zmian. Szacunek: ~25 l. kodu + ~45 l. testów.
