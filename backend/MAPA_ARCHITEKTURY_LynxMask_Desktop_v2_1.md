# MAPA ARCHITEKTURY — LYNXMASK DESKTOP
**Wersja mapy:** 2.1
**Data ostatniej aktualizacji:** 14.06.2026
**Zmapowane pliki:** pseudominizer_api.py, pipeline.py, pipeline_core.py, pipeline_new.py, layers/ (9 modułów), output_guard.py, spacy_ner.py, db_store.py, anonymizer.py, ner_layer.py, anonymizer_crypto.py, anonymizer_init.py, ocr_engine.py, ner_blocklist.py, audit_log.py, document_processor.py, verbal_amounts.py, crypto_selftest.py, export_pdf.py + frontend Tauri (App/MainLayout/Pseudonimizuj/Biblioteka/Depseudonimizuj/LockScreen/SecurityScreen/OnboardingScreen/main.rs/global.css/theme.ts)
**MAPA KOMPLETNA — backend + frontend.**

**Nazwa produktu:** LynxMask Desktop (dawniej Pseudominizer).
Wewnętrzne nazwy plików na dysku (pseudominizer_api.py itp.) pozostają bez zmian.

**Terminologia UI (obowiązująca):**
- "Zamaskuj" — nie: pseudonimizuj
- "Przywróć" — nie: depseudonimizuj
- "maskowanie" — nie: pseudonimizacja
- W kodzie backendowym stare nazwy zostają (pipeline.py, pseudominizer_api.py itp.)

---

## SEKCJA 1 — TABELA PLIKÓW

| Plik | Wersja | Linie | Uwagi |
|------|--------|-------|-------|
| pseudominizer_api.py | v1.27-TAURI ¹ | 632 | Główny backend FastAPI. Niezgodność wewnętrzna: stała `API_VERSION = "1.26-TAURI"` w kodzie — nagłówek pliku mówi v1.27. |
| pipeline.py | v1.21 | ~510 | Orkiestrator warstw maskowania. Dodano USE_NEW_PIPELINE=True (przełącznik nowego pipeline). skip_guard=True w wywołaniu anonymize(). |
| pipeline_core.py | v0.2+ | ~330 | **NOWY (potok 14.06.2026).** Centralna alokacja tokenów: TokenAllocator, PipelineState, ConflictResolver. ner_results: dict (Coverage-Fix). |
| pipeline_new.py | v0.4 | ~142 | **NOWY (potok 14.06.2026).** Nowy pipeline oparty na TokenAllocator. run_pipeline_new(). |
| layers/ | — | — | **NOWY pakiet (potok 14.06.2026).** 9 modułów warstw + __init__.py. Szczegóły poniżej. |
| output_guard.py | v3.6 | ~436 | Guard sprawdzający wyciek PII po maskowaniu. |
| spacy_ner.py | v1.5 | ~415 | Lazy load SpaCy pl_core_news_lg (~500MB). |
| db_store.py | v1.0 | ~163 | Wydzielony z pseudominizer_api.py v1.23. |
| anonymizer.py | v4.25 | ~1490 | Główny moduł anonimizacji. anonymize() przyjmuje skip_guard=False. |
| ner_layer.py | v1.7 | ~220 | Adapter między pipeline.py a spacy_ner.py. |
| anonymizer_crypto.py | v1 | ~230 | AES-256-GCM + DPAPI (Windows) + HMAC-SHA256 per wpis. |
| anonymizer_init.py | v1.8 | ~200 | Inicjalizacja warstw opcjonalnych, stałe tokenów, 20 wzorców STRUCTURAL_PATTERNS. |
| ocr_engine.py | v1.3 | ~180 | OCR przez Tesseract + pytesseract. |
| ner_blocklist.py | v1.3 | ~200 | Dane statyczne dla ner_layer.py. 263 wpisów (Coverage-Fix: +24 wpisy). |
| audit_log.py | v1.1 | ~110 | Audyt /preview do pliku JSONL. |
| document_processor.py | v1.1 | ~100 | _next_pse(), _extract_text(). |
| verbal_amounts.py | v1.2 | ~160 | Maskowanie kwot słownych. |
| crypto_selftest.py | v1.0 | ~200 | 22 testy anonymizer_crypto.py. |
| export_pdf.py | v1.0 | ~100 | PDF server-side przez PyMuPDF. |

**Pliki pakietu layers/ (potok 14.06.2026, wersje po Coverage-Fix):**

| Plik | Wersja | Co maskuje |
|------|--------|-----------|
| layers/identity.py | v1.1 | PESEL (11 cyfr), NIP (separator `[\-\.]`), REGON (9/14), dowód osobisty ([A-Z]{3}\d{6}), paszport ([A-Z]{2}\d{7}) |
| layers/contact.py | v1.0 | Email (TOKEN_EMAIL z STRUCTURAL_PATTERNS), telefon (+48…) |
| layers/financial.py | v1.0 | IBAN PL, konta 24-cyfrowe, formaty z kreskami |
| layers/legal.py | v1.0 | Sygnatury sądowe/komornicze, sygnatury administracyjne, księgi wieczyste (KW) |
| layers/numeric.py | v1.0 | Numery klienta KL-NNNNN, faktury FV-*/VAT/*, umowy UMW/* |
| layers/address.py | v1.5 | Adresy z kodem pocztowym jako kotwicą. v1.5: `_CITY_FORMS` (frozenset SIMC GUS, 179k form) + `_match_city(text, pos)` — miasto musi być w bazie SIMC |
| layers/ner_adapter.py | v1.1 | Adapter process_ner() → allocator (OSOBA/FIRMA przez NER). `extract_ner_results()` do pre-ekstrakcji NER przed address layer |
| layers/fallback.py | v1.0 | Siatka bezpieczeństwa: \d{8,} które przeżyły wcześniejsze warstwy |
| layers/validation.py | v1.0 | Deleguje do anonymizer._layer4_stdnum() i _layer5_phonenumbers() |

**Pliki danych:**
| Plik | Rozmiar | Status |
|------|---------|--------|
| names_inflected.json | 36 KB | Generowany przez generate_lookups_v3.py. Nie importowany przez żaden zmapowany plik — prawdopodobnie nieużywany w runtime. |
| surnames_top1000.json | 206 KB | j.w. |
| cities.json | ~600 KB | **NOWY (14.06.2026).** 31 117 unikalnych nazw miejscowości z SIMC GUS (RM=01+96, MZ=1). Plik źródłowy do generowania cities_forms.json. |
| cities_forms.json | ~2.5 MB | **NOWY (14.06.2026).** 179 370 unikalnych form morfologicznych (Morfeusz2 `generate()`). Ładowany przez layers/address.py v1.5 do `_CITY_FORMS` (frozenset) przy starcie. |
| RAPORT_Pipeline_Refactor.txt | 14 KB | **NOWY (potok 14.06.2026).** Dokumentacja refaktoryzacji z benchmarkiem. |
| RAPORT_Coverage_Fix.txt | ~8 KB | **NOWY (14.06.2026).** Tabela Run A/D/E/F, naprawione bugi, otwarte problemy. |
| RAPORT_Testy_Slownik.txt | ~5 KB | **NOWY (14.06.2026).** Tabela Run A/F/G/H, integracja SIMC, fix benchmark HTTP 400. |

**Frontend:**
| Plik | Wersja | Uwagi |
|------|--------|-------|
| pseudominizer.html | — | Aktywny frontend HTML (73 KB), serwowany przez FastAPI GET / |
| App.tsx | v1.3 | Stan: unlocked, apiToken; idle timer 9/10 min |
| theme.ts | v2.3 | Jedyne źródło kolorów — nie hardkodować hex bezpośrednio |
| global.css | — | Placeholder, scrollbar, focus outline, select styling |
| MainLayout.tsx | v1.5 | Router ekranów |
| Pseudonimizuj.tsx | v1.3 | Ekran maskowania |
| Biblioteka.tsx | v1.6 | Ekran biblioteki dokumentów. Drzewko odpowiedzi AI z lazy load (list_depseudo_responses). Nowy prop onDemask. |
| Depseudonimizuj.tsx | v1.5 | Ekran przywracania |
| LockScreen.tsx | v1.2 | Ekran blokady/logowania |
| SecurityScreen.tsx | v1.1 | Ekran bezpieczeństwa (pusty — do zapełnienia) |
| OnboardingScreen.tsx | v1.0 | Onboarding przy pierwszym uruchomieniu |
| main.rs | v1.5 | Backend Tauri (Rust) |
| tauri.conf.json | — | productName = "LynxMask Desktop", port 1420 |
| pytest.ini | — | testpaths = tests; python_files = test_pseudominizer.py test_pipeline_v2.py |

¹ Niezgodność wewnętrzna: nagłówek pliku mówi v1.27-TAURI, stała `API_VERSION = "1.26-TAURI"` w kodzie linia ~178. Mapa używa wersji z nagłówka pliku (1.27). Do wyrównania przy kolejnej edycji pliku.

---

## SEKCJA 2 — MAPA FUNKCJI PER PLIK

### pseudominizer_api.py (v1.27-TAURI, 632 linie)

| Funkcja / Klasa | Linia start | Linia end | Co robi | Wywołuje | Wywoływana przez |
|-----------------|-------------|-----------|---------|----------|-----------------|
| `_lifespan(app)` | ~122 | ~158 | Async context manager startu serwera. Ładuje spacy_ner, anonymizer, output_guard, crypto_selftest. Wywołuje `build_anonymizer()` i `run_all()`. redirect_stdout przy crypto_selftest (fix UnicodeEncodeError Windows). | `build_anonymizer()`, `crypto_selftest.run_all()` | FastAPI lifespan hook |
| `_require_api_token(request, call_next)` | ~201 | ~208 | Middleware HTTP. Blokuje żądania bez nagłówka X-Api-Token. Pomija /health i OPTIONS. | `_secrets.compare_digest()` | Każde żądanie HTTP |
| `version()` | ~213 | ~215 | GET /version — zwraca wersję API i OCR. | — | klient |
| `health()` | ~218 | ~226 | GET /health — status: anonymizer, spacy_ner, morfeusz, crypto_ok. Pomija token middleware. | — | klient / Tauri startup |
| `preview(request, file)` | ~229 | ~309 | POST /preview — główny endpoint. Ekstrakcja tekstu z pliku, maskowanie, zwrot JSON z tokenami i podglądem. Dodaje nagłówek PSE do tekstu wyjściowego. Zwraca też `has_sensitive`, `anonymizer_active`. Guard [AUD-01] odrzuca tekst zawierający tokeny maskujące (injection protection). | `_next_pse()`, `_extract_text()`, `pseudonymize_document()`, `record_preview()` | Pseudonimizuj.tsx |
| `archive_save(request)` | ~312 | ~381 | POST /archive — zapisuje zaszyfrowany blob mapy sesji na dysk (.enc) i rekord w SQLite. Atomowy zapis przez .tmp. | `db_store.save()`, `db_store.record_audit()` | Pseudonimizuj.tsx (przycisk Zapisz) |
| `archive_list()` | ~384 | ~397 | GET /archive — lista dokumentów z SQLite + flaga enc_exists. | `db_store.list_documents()` | Biblioteka.tsx |
| `archive_get_blob(pse)` | ~400 | ~421 | GET /archive/{pse}/blob — zwraca zaszyfrowany blob .enc jako base64. | `db_store.record_audit()` | Depseudonimizuj.tsx |
| `archive_delete(pse)` | ~424 | ~451 | DELETE /archive/{pse} — usuwa plik .enc i rekord SQLite. | `db_store.delete()`, `db_store.record_audit()` | Biblioteka.tsx |
| `archive_reencrypt(request)` | ~454 | ~508 | POST /archive/reencrypt — atomowa zmiana hasła: klient przesyła nowe blobs, backend podmienia .enc przez .tmp (dwie fazy). | `db_store.record_audit()` | Biblioteka.tsx (zmiana hasła) |
| `archive_audit()` | ~511 | ~517 | GET /archive/audit — log zdarzeń bez PII. | `db_store.list_audit()` | klient / debug |
| `export_pdf(request)` | ~531 | ~564 | POST /export-pdf — generuje PDF server-side bez metadanych (autor=""). Wymaga PyMuPDF. | `_generate_pdf()` (z export_pdf.py) | Pseudonimizuj.tsx |
| `profile_add_entity(request)` | ~569 | ~609 | POST /profile/add-entity — [VARIANT-A] persystuje encję do profilu biura (AnonymizerMap). Idempotentne. | `_app_state.anon_map.add_entity()` | Pseudonimizuj.tsx (ręczna korekta encji) |
| `serve_frontend()` | ~614 | ~618 | GET / — serwuje pseudominizer.html. | — | przeglądarka / Tauri WebView |

**Stałe kluczowe:**
- `_TYPE_LABELS` — etykiety UI dla 7 typów tokenów: OSOBA, FIRMA, NUMER, KWOTA, ADRES, INSTYTUCJA, EMAIL
- `_TYPE_ORDER` — kolejność sortowania tokenów w tabeli: OSOBA=0, FIRMA=1, INSTYTUCJA=2, NUMER=3, EMAIL=4, KWOTA=5, ADRES=6
- `_TOKEN_RE` — regex dopasowujący wszystkie typy tokenów (FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)\_\d{3}

---

### pipeline.py (v1.21, ~510 linii)

**v1.21 — Zmiany (14.06.2026):**
- `USE_NEW_PIPELINE: bool = True` — przełącznik nowego pipeline (nad `_run_pipeline`)
- `_run_pipeline()` na początku sprawdza flagę: gdy True, wywołuje `run_pipeline_new()` i zwraca wynik
- `anonymize()` wywołane ze `skip_guard=True` — guard injection na poziomie API ([AUD-01])

| Funkcja / Klasa | Linia start | Linia end | Co robi | Wywołuje | Wywoływana przez |
|-----------------|-------------|-----------|---------|----------|-----------------|
| `USE_NEW_PIPELINE` | ~298 | — | `bool = True`. Gdy True: _run_pipeline() wywołuje run_pipeline_new() zamiast starego kodu. Zmiana jednej stałej przełącza ścieżkę. Stary kod nienaruszony. | — | — |
| `AppState` (dataclass) | ~182 | ~193 | Kontener stanu serwera: spacy_ner_mod, anonymizer, anon_map, morf_env. | — | pseudominizer_api.py |
| `PipelineResult` (dataclass) | ~195 | ~203 | Wynik maskowania: text, reverse_map, guard_blocked, guard_reasons, error. | — | pseudominizer_api.py preview() |
| `pseudonymize_document(text, state)` | ~207 | ~217 | Publiczne API pipeline. Opakowuje `_run_pipeline` w try/except. Fail-soft. | `_run_pipeline()` | pseudominizer_api.py preview() |
| `_apply_regex_layer(text, reverse_map, pattern, prefix, min_len)` | ~222 | ~246 | Wspólna logika warstw regex. Iteruje od końca tekstu. | `re.Pattern.finditer()` | `_run_pipeline()` (warstwy 2a, 2b, 2c) |
| `_run_pipeline(text, state)` | ~302 | ~460 | Główna implementacja. Gdy USE_NEW_PIPELINE=True: lazy import run_pipeline_new, wywołanie i return PipelineResult. Gdy False: stary kod 7 warstw. | `run_pipeline_new()` lub stare warstwy | `pseudonymize_document()` |

**Warstwy `_run_pipeline` (USE_NEW_PIPELINE=False — stary kod):**

| Warstwa | Co robi |
|---------|---------|
| Normalizacja cudzysłowów | „" « » → " |
| Warstwa 1: NER | SpaCy, detect_entities + process_ner + check_and_block |
| Normalizacja IBAN | Usuwa spacje z IBAN PL |
| Warstwa 2a: dowód osobisty | _apply_regex_layer(_ID_CARD_RE) → NUMER_xxx |
| Warstwa 2b: instytucje | _apply_regex_layer(_INSTITUTION_RE) → INSTYTUCJA_xxx |
| Warstwa 2c: sygnatury | _apply_regex_layer(_CASE_SIG_RE) → NUMER_xxx |
| Warstwa 3: adresy | _ADDR_RE → ADRES_xxx |
| Warstwa 4: kwoty słowne | verbal_amounts.mask_verbal_amounts() → KWOTA_xxx |
| Warstwa 5: anonymizer | state.anonymizer.anonymize(skip_guard=True) |
| Warstwa 6: FIX-NER-GLOBAL | Warianty fleksyjne NER, filtry FIRMA/OSOBA |
| Warstwa 7: output_guard | guard_output_with_map() |

---

### pipeline_core.py (v0.2+, ~330 linii) — NOWY

> Centralny moduł alokacji tokenów. Stworzone w potoku refaktoryzacji 14.06.2026.
> Nie importuje z pipeline.py — zero zależności cyklicznych.

| Klasa / Funkcja | Co robi |
|-----------------|---------|
| `_canonical(value)` | Normalizacja: usuwa spacje/kreski/kropki → lowercase. Klucz deduplication. |
| `TokenAllocator` | Jeden obiekt alokacji tokenów na cały pipeline. Gwarantuje unikalność, deduplikację i ochronę spanów. |
| `TokenAllocator.allocate(token_type, value, start, end)` | Tworzy token. Dedup po canonical(value, token_type). Zwraca None gdy span zajęty. Zwraca istniejący token gdy ta sama wartość już widziana. |
| `TokenAllocator.register(token_id, value, start, end)` | Rejestruje token zewnętrzny (NER, trie). Podnosi podłogę licznika — przyszłe allocate() nie kolizjonują numerycznie. |
| `TokenAllocator.reset_spans()` | Czyści listę spanów między warstwami. Liczniki i mapa deduplication zostają. Konieczne bo każda podmiana tekstu (PII → TOKEN_NNN) zmienia offsety — stare spany byłyby błędne w nowym tekście. |
| `TokenAllocator.reverse_map` | Property: {token_id: oryginalna_wartość}. |
| `TokenAllocator.is_occupied(start, end, overlap)` | overlap="partial": True przy jakimkolwiek nakładaniu. overlap="full": True tylko przy identycznym spanie. |
| `PipelineState` | @dataclass: text (str), allocator (TokenAllocator), ner_results (dict), ner_variants (dict). Przekazywany przez wszystkie warstwy jako jedyny argument. |
| `ConflictResolver` | Polityka rozwiązywania konfliktów spanów. resolve(existing_type, new_type, overlap_mode) → bool. |
| `ENTITY_PRIORITY` | {EMAIL:100, PESEL/IBAN:95, NIP:90, REGON/DOWOD:85, TELEFON:80, ADRES/SYGNATURA:75, OSOBA/FIRMA:70, NUMER:50} |

---

### pipeline_new.py (v0.4, ~142 linie) — NOWY

> Nowy pipeline oparty na TokenAllocator. Wywołany przez pipeline.py gdy USE_NEW_PIPELINE=True.

| Funkcja | Co robi |
|---------|---------|
| `_apply(state, fn, *args)` | Wywołuje `state.allocator.reset_spans()` przed każdą warstwą, potem `fn(state, *args)`. Reset spanów rozwiązuje "span coordinate drift" — po każdej podmianie tekstu stare offsety są nieważne. |
| `run_pipeline_new(text, anon_map, anonymizer=None)` | Orkiestrator 9 warstw + pre-NER w kolejności: identity → financial → legal → numeric → contact → [extract_ner_results] → address → ner_adapter → fallback → validation (jeśli anonymizer != None). Zwraca (str, dict). |

**Kolejność warstw i typy tokenów:**

| Kolejność | Warstwa | Typy tokenów |
|-----------|---------|--------------|
| 1 | identity | NUMER (PESEL, NIP, REGON, dowód, paszport) |
| 2 | financial | NUMER (IBAN, konta bankowe) |
| 3 | legal | NUMER (sygnatury sądowe, komornicze, admin, KW) |
| 4 | numeric | NUMER (numery klienta KL-, faktury FV-/VAT/, umowy UMW/) |
| 5 | contact | EMAIL, NUMER (telefon) |
| — | `extract_ner_results` | Pre-ekstrakcja NER (bez modyfikacji tekstu). SpaCy widzi tekst po PESEL/NIP/IBAN, przed adresem — fix regresu OSOBA |
| 6 | address | ADRES |
| 7 | ner_adapter | OSOBA, FIRMA (używa cache z extract_ner_results) |
| 8 | fallback | NUMER (luźne cyfry 8+) |
| 9 | validation | NUMER (stdnum + phonenumbers, jeśli anonymizer != None) |

---

### layers/ — pakiet warstw (9 modułów) — NOWY

> Każdy moduł ma niezależną funkcję `apply_X_layer(state: PipelineState)` i test jednostkowy.
> Łączna pokrycie testami: 133 PASS, 0 FAIL (szczegóły w RAPORT_Pipeline_Refactor.txt).

**layers/identity.py v1.1** — PESEL, NIP, REGON, dowód, paszport
- `_IDENTITY_SOURCES` frozenset — podzbiór STRUCTURAL_PATTERNS (wzorce numeryczne PII)
- Sortuje hity od końca tekstu, zastępuje `allocator.allocate("NUMER", ...)`
- v1.1: `_NIP_RE` rozszerzony o separator `[\-\.]` — fix NIP z OCR (766-444-75.06)

**layers/contact.py v1.0** — email, telefon
- `_CONTACT_EMAIL_PATTERNS` — filtr `tok == TOKEN_EMAIL` z STRUCTURAL_PATTERNS (2 wzorce: standard + łamanie linii OCR)
- `_CONTACT_PHONE_PATTERNS` — filtr `r"\+?48" in pat.pattern` z STRUCTURAL_PATTERNS

**layers/financial.py v1.0** — IBAN PL, konta bankowe
- Explicit frozenset wzorców — wyklucza NIP-PL i PLN (oba zawierają "PL")

**layers/legal.py v1.0** — sygnatury, KW
- `_CASE_SIG_RE`, `_ADMIN_SIG_RE`, `_KW_RE` mirrowane z pipeline.py (bez importu — pipeline.py ma side effects przy imporcie)

**layers/numeric.py v1.0** — numery klienta, faktury, umowy
- `KL-NNNNN` → NUMER_xxx, `FV-*/VAT/*` → NUMER_xxx, `UMW/*` → NUMER_xxx
- Dodany po apply_legal_layer w v0.3 pipeline_new.py

**layers/address.py v1.5** — adresy z kodem pocztowym
- Faza 2 split na sub-fazy 2a (`_ADDR_STRUCTURAL_FULL`) i 2b (`_POSTAL_ANCHOR_RE` + `_match_city`)
- v1.4: `_fix_city()` z precyzyjnym wzorcem miasta zamiast chciwego `\w[\w ,]{2,40}\b`
- v1.5: `_CITY_FORMS` (frozenset z cities_forms.json — SIMC GUS, 179 370 form morfologicznych wygenerowanych przez Morfeusz2). `_match_city(text, pos)` — próbuje 2 słowa, potem 1; pomija ` \t,\n\r`. Miasto musi być w SIMC — redukuje FP z ogólnego `[A-Z][a-z]+`
- sort (start, -(end-start)) — dłuższy span wygrywa

**layers/ner_adapter.py v1.1** — adapter process_ner()
- Wywołuje `ner_layer.process_ner(state.text, anon_map)`; rejestruje przez `allocator.register()`
- v1.1: `extract_ner_results(state, anon_map)` — wywołać PRZED apply_address_layer; nie modyfikuje state.text. `apply_ner_layer()` sprawdza `if state.ner_results:` → używa cache
- ner_layer.py nie jest modyfikowany
- Mock pattern: `sys.modules[__name__]` dla `patch.object` bez względu na tryb importu

**layers/fallback.py v1.0** — siatka bezpieczeństwa
- `_FALLBACK_RE = re.compile(r"(?<!\d)\d{8,}(?!\d)")`
- Sprawdza `is_occupied()` przed `allocate()` — nie duplikuje tokenów z wcześniejszych warstw

**layers/validation.py v1.0** — stdnum + phonenumbers
- Deleguje do `anonymizer._layer4_stdnum()` i `anonymizer._layer5_phonenumbers()`
- Zaseedowuje licznik NUMER z `state.allocator._counters["NUMER"]` — brak kolizji
- Wymaga `anonymizer != None` (opcjonalna — testy bez API działają bez zmian)

---

### output_guard.py (v3.6, ~436 linii)

| Funkcja / Klasa | Linia start | Linia end | Co robi | Wywołuje | Wywoływana przez |
|-----------------|-------------|-----------|---------|----------|-----------------|
| `GuardMode` (enum) | ~66 | ~69 | Tryby: STRICT (blokuj ≥1), REDACT (HIGH→blokada, MEDIUM→zamazanie+próg), DIAGNOSE (tylko log). | — | pipeline.py, guard_output(), guard_output_with_map() |
| `GuardResult` (dataclass) | ~122 | ~144 | Wynik guarda: blocked, redacted, reasons, safe_text, redacted_text, detection_count, high_hit, mode. | — | pipeline.py, Pseudonimizuj.tsx |
| `guard_output(text, mode)` | ~150 | ~245 | Skanuje tekst na wzorce HIGH i MEDIUM. | `re.Pattern.finditer()` | `guard_output_with_map()` |
| `guard_output_with_map(text, anon_map, mode, known_plain)` | ~252 | ~316 | Rozszerzone guard_output + encje z mapy sesji i profilu biura. | `guard_output()`, `check_blacklist_context()`, `anon_map.get_entity_names()` | pipeline.py warstwa 7 (stary pipeline) |
| `is_malicious_prompt(question, attached_text)` | ~380 | ~394 | Sprawdza prompt injection (~35 wzorców PL+EN). | `_INJECTION_RE.findall()` | `check_prompt()` |
| `SYSTEM_PROMPT_SECURITY` (stała) | ~414 | ~435 | System prompt z zasadami bezpieczeństwa dla modeli AI. | — | pseudominizer_api.py preview() |

---

### spacy_ner.py (v1.5, ~415 linii)

| Funkcja / Klasa | Co robi |
|-----------------|---------|
| `NERBlockError` | Wyjątek rzucany gdy wykryto niezanonimizowane imię+nazwisko. |
| `NERResult` | Encja NER: text, label, confidence, start, end. |
| `_get_nlp()` | Lazy load modelu SpaCy pl_core_news_lg (~500 MB). |
| `_merge_adjacent_entities(results, text, max_gap)` | Scala sąsiadujące encje tej samej kategorii gdy przerwa ≤ 4 znaki. |
| `detect_entities(text)` | Główna detekcja NER. Filtruje przez _SPACY_LABEL_MAP, deduplikuje, scala. |
| `check_and_block(text, ner_results, known_entities)` | Rzuca NERBlockError jeśli tekst zawiera imię+nazwisko nieobecne w known_entities. |

---

### ner_layer.py (v1.7, ~220 linii)

| Funkcja | Co robi |
|---------|---------|
| `_filter_institutions(ner_results)` | Usuwa instytucje publiczne, słowa pospolite i tokeny PSE z wyników NER. |
| `process_ner(text, spacy_ner_mod)` | Publiczne API. NERBlockError NIE jest łapana — propaguje do pipeline.py. |
| `_process_ner(text, spacy_ner_mod)` | Implementacja: detect_entities → filtr → sort malejąco po długości → tokeny OSOBA_/FIRMA_. Zwraca (reverse_map, all_variants). |

---

### db_store.py (v1.0, ~163 linie)

| Funkcja | Co robi |
|---------|---------|
| `init(db_path)` | Inicjalizacja bazy: katalog, migracja, tabele. |
| `save(pse, token_count, description)` | INSERT OR REPLACE do documents. Thread-safe (_db_lock). |
| `list_documents()` | SELECT * FROM documents ORDER BY created_at DESC. |
| `delete(pse)` | DELETE FROM documents WHERE pse. |
| `record_audit(pse, action)` | INSERT do audit_log. Zero PII. |
| `list_audit(limit)` | SELECT z audit_log ORDER BY timestamp DESC LIMIT. |

---

### anonymizer.py (v4.25, ~1490 linii)

**v4.25 — Zmiany (14.06.2026):**
- `anonymize()` przyjmuje `skip_guard: bool = False`
- Gdy `skip_guard=True`: blok guard injection (TOKEN_SPAN_RE check) jest pomijany
- Wywołania z pipeline.py przekazują `skip_guard=True` — guard na poziomie API ([AUD-01]) wystarczy
- Zachowanie domyślne (skip_guard=False) identyczne z v4.24

> Importuje wszystkie stałe z `anonymizer_init.py`.

| Funkcja / Klasa | Co robi |
|-----------------|---------|
| `_normalize(text)` | NFKC + lower — do porównań wewnętrznych. |
| `_canonical_value(token_type, raw)` | Klucz idempotentności: dla NUMER usuwa myślniki/spacje/kropki. |
| `MorfEnv` | Wykrywa i abstrakcyjnie udostępnia Morfeusz2. Tryby: NATIVE, WSL2, BLOCKED. |
| `AnonymizerMap` | Zarządza mapą encji (mapa.enc + trie.pkl). Thread-safe. |
| `Anonymizer` | Anonimizuje tekst w 5 warstwach (trie → regex → postal → stdnum → phonenumbers). |
| `Anonymizer.anonymize(text, known_tokens, existing_reverse_map, skip_guard)` | Główna metoda. Limit: INPUT_LIMIT_BYTES. Guard pomijalny przez skip_guard=True. |
| `Anonymizer._layer4_stdnum` | Walidacja przez python-stdnum: IBAN, PESEL, NIP-PL, REGON, VAT-EU, EDRPOU-UA. Wywoływana też przez layers/validation.py. |
| `Anonymizer._layer5_phonenumbers` | Telefony przez libphonenumber. Default region PL. Wywoływana też przez layers/validation.py. |
| `Deanonymizer` | Odtwarza tekst z tokenów. Token nieznany → ERR_TOKENS. |
| `check_blacklist_context` | Trzy ścieżki weryfikacji wycieku encji z mapy sesji i profilu biura. |
| `build_anonymizer(profile_dir, hardware_profile)` | Factory: MorfEnv + AnonymizerMap + Anonymizer + Deanonymizer. |

---

### anonymizer_init.py (v1.8, ~200 linii)

> Inicjalizuje warstwy opcjonalne **przy imporcie modułu** (nie lazy). Każda warstwa ma graceful fallback gdy biblioteka niedostępna.

| Element | Co robi |
|---------|---------|
| `_init_postal_patterns()` | Kody pocztowe dla 8 krajów (PL/DE/FR/IT/ES/NL/GB/UA). |
| `_init_stdnum_validators()` | Walidatory: VAT-EU, IBAN, PESEL, NIP-PL, REGON, EDRPOU-UA, RNTRC-UA. |
| `TOKEN_RE` | `re.compile(r"\b(FIRMA|OSOBA|NUMER|KWOTA|ADRES|EMAIL)_(\d{3})\b")` — **NIE zawiera INSTYTUCJA** |
| `TOKEN_SPAN_RE` | `re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|EMAIL)_\d{3}\b")` |
| `STRUCTURAL_PATTERNS` | 20 wzorców regex + siatka bezpieczeństwa. Importowane przez layers/identity.py, layers/contact.py. |

---

### Pozostałe pliki (bez zmian w v2.1)

**anonymizer_crypto.py (v1)** — AES-256-GCM + DPAPI + HMAC-SHA256.
**ocr_engine.py (v1.3)** — OCR przez Tesseract. ⚠ BUG-10: hardkodowana ścieżka `C:\Users\p_pie\...`.
**ner_blocklist.py (v1.3)** — 263 wpisów blocklist + _LEGAL_SUFFIXES. Wpisy < 6 znaków nie trafiają do _NER_BLOCKLIST_PREFIXES.
**audit_log.py (v1.1)** — Audyt /preview do JSONL. AUDIT_MODE = True.
**document_processor.py (v1.1)** — _next_pse() + _extract_text(). ⚠ BUG-12: PSE_REGISTRY ścieżka względna.
**verbal_amounts.py (v1.2)** — Maskowanie kwot słownych. Uwaga: kwota_counter to list[int], nie int.
**crypto_selftest.py (v1.0)** — 22 testy anonymizer_crypto.py. run_all() → 0 (OK) lub 1 (FAIL).
**export_pdf.py (v1.0)** — PDF przez PyMuPDF. author="" (FIX-PDF-META).

---

## SEKCJA 3 — GRAF ZALEŻNOŚCI MIĘDZY PLIKAMI

```
pseudominizer_api.py
  ├── pipeline.py              (import: AppState, pseudonymize_document)
  ├── db_store.py              (import: init, save, list_documents, delete,
  │                                     record_audit, list_audit)
  ├── document_processor.py   (import: _next_pse, _extract_text)
  │     └── ocr_engine.py     (wywołuje extract_text_from_image dla obrazów)
  ├── audit_log.py             (import: record_preview)
  ├── anonymizer.py            (import: build_anonymizer — w _lifespan)
  ├── output_guard.py          (import: SYSTEM_PROMPT_SECURITY — w _lifespan)
  ├── crypto_selftest.py       (import: run_all — w _lifespan)
  └── export_pdf.py            (import: generate_pdf — opcjonalny, try/except)

pipeline.py
  ├── pipeline_new.py          (lazy import gdy USE_NEW_PIPELINE=True)
  ├── ner_layer.py             (import: process_ner)
  ├── verbal_amounts.py        (import: mask_verbal_amounts)
  ├── ner_blocklist.py         (import: _LEGAL_SUFFIXES_LOWER as _FIRMA_SUFFIXES)
  └── output_guard.py          (import: guard_output, guard_output_with_map, GuardMode)

pipeline_new.py                (NOWY — używany gdy USE_NEW_PIPELINE=True)
  ├── pipeline_core.py         (import: PipelineState, TokenAllocator)
  ├── layers/identity.py       (import: apply_identity_layer)
  ├── layers/contact.py        (import: apply_contact_layer)
  ├── layers/financial.py      (import: apply_financial_layer)
  ├── layers/legal.py          (import: apply_legal_layer)
  ├── layers/numeric.py        (import: apply_numeric_layer)
  ├── layers/address.py        (import: apply_address_layer)
  ├── layers/ner_adapter.py    (import: apply_ner_layer, extract_ner_results)
  ├── layers/fallback.py       (import: apply_fallback_layer)
  └── layers/validation.py     (import: apply_validation_layer)

layers/*.py
  ├── pipeline_core.py         (import: PipelineState, TokenAllocator)
  ├── anonymizer_init.py       (identity.py, contact.py: STRUCTURAL_PATTERNS, TOKEN_*)
  └── anonymizer.py            (validation.py: _layer4_stdnum, _layer5_phonenumbers)

layers/ner_adapter.py
  └── ner_layer.py             (import: process_ner — nie modyfikowany)

output_guard.py
  └── anonymizer.py            (lazy import: check_blacklist_context)

anonymizer.py
  └── anonymizer_init.py       (import: STRUCTURAL_PATTERNS, TOKEN_*, TOKEN_RE,
                                _POSTAL_PATTERNS, _STDNUM_VALIDATORS, _crypto,
                                INPUT_LIMIT_BYTES, MAX_TOKENS_PER_REQUEST)

anonymizer_init.py
  └── anonymizer_crypto.py     (import: jako _crypto — opcjonalny, przy imporcie)

ner_layer.py
  ├── spacy_ner.py             (wywołuje detect_entities przez spacy_ner_mod)
  └── ner_blocklist.py         (import: _LEGAL_SUFFIXES_LOWER, _NER_BLOCKLIST,
                                _NER_BLOCKLIST_PREFIXES)

spacy_ner.py
  └── spacy                    (lazy load pl_core_news_lg ~500MB)
```

**Przepływ danych — nowy pipeline (USE_NEW_PIPELINE=True):**
```
POST /preview (pseudominizer_api.py)
  → [AUD-01] guard injection check (_TOKEN_RE.search)
  → _extract_text() [document_processor.py]
  → pseudonymize_document() [pipeline.py]
      → _run_pipeline()
          → run_pipeline_new(text, anon_map, anonymizer) [pipeline_new.py]
              → PipelineState(text, TokenAllocator())
              → _apply(apply_identity_layer)         [layers/identity.py]
              → _apply(apply_financial_layer)        [layers/financial.py]
              → _apply(apply_legal_layer)            [layers/legal.py]
              → _apply(apply_numeric_layer)          [layers/numeric.py]
              → _apply(apply_contact_layer)          [layers/contact.py]
              → extract_ner_results(state, anon_map) [layers/ner_adapter.py] ← bez _apply, bez modyfikacji tekstu
              → _apply(apply_address_layer)          [layers/address.py]
              → _apply(apply_ner_layer, anon_map)    [layers/ner_adapter.py → ner_layer.py, cache]
              → _apply(apply_fallback_layer)         [layers/fallback.py]
              → _apply(apply_validation_layer)       [layers/validation.py → anonymizer.py]
              → return (state.text, allocator.reverse_map)
          → PipelineResult(text, reverse_map)
  → record_preview() [audit_log.py]
  → return JSON: blocked, guard_reasons, tokens, anonymized_preview, ...
```

**Przepływ danych — stary pipeline (USE_NEW_PIPELINE=False):**
```
POST /preview (pseudominizer_api.py)
  → pseudonymize_document() [pipeline.py]
      → spacy_ner_mod.detect_entities()
      → ner_layer.process_ner()
      → verbal_amounts.mask_verbal_amounts()
      → state.anonymizer.anonymize(skip_guard=True)
      → guard_output_with_map() [output_guard.py]
```

---

## SEKCJA 4 — TABELA ENDPOINTÓW API

| Endpoint | Metoda | Przyjmuje | Zwraca | Wywołuje |
|----------|--------|-----------|--------|----------|
| `/version` | GET | — | `{api, ocr}` | — |
| `/health` | GET | — | `{status, anonymizer, spacy_ner, morfeusz, crypto_ok}` | — |
| `/preview` | POST | multipart/form-data: `file` (PDF/DOCX/TXT/obraz, max 5 MB) | `{blocked, error, guard_reasons, tokens[], total, has_sensitive, anonymizer_active, anonymized_preview, original_text, pse_code, system_prompt, ocr}` | `_extract_text`, `pseudonymize_document`, `record_preview` |
| `/archive` | POST | JSON: `{pse, token_count, enc_blob (base64), description? (base64)}` | `{ok, pse}` | `db_store.save`, `db_store.record_audit` |
| `/archive` | GET | — | `{documents[], total}` + enc_exists per dokument | `db_store.list_documents` |
| `/archive/{pse}/blob` | GET | path param: pse (PSE-YYYY-NNNN) | `{pse, enc_blob (base64)}` | `db_store.record_audit` |
| `/archive/{pse}` | DELETE | path param: pse | `{ok, pse, file_deleted}` | `db_store.delete`, `db_store.record_audit` |
| `/archive/reencrypt` | POST | JSON: `{blobs: [{pse, enc_blob}]}` | `{ok, updated}` | `db_store.record_audit` |
| `/archive/audit` | GET | — | `{log[]}` | `db_store.list_audit` |
| `/export-pdf` | POST | JSON: `{text, filename?}` | PDF bytes (application/pdf) | `_generate_pdf` |
| `/profile/add-entity` | POST | JSON: `{text, token_type}` | `{ok, token_id}` | `anon_map.add_entity` |
| `/` | GET | — | pseudominizer.html | — |

---

## SEKCJA 5 — FRONTEND TAURI

**Wersje (stan 09.06.2026, bez zmian w potoku 14.06.2026):** App v1.3 / MainLayout v1.5 / Pseudonimizuj v1.3 / Biblioteka v1.5 / Depseudonimizuj v1.5 / LockScreen v1.2 / SecurityScreen v1.1 / OnboardingScreen v1.0 / theme.ts v2.3 / main.rs v1.5

### Struktura plików pseudominizer-tauri/

```
src/
  main.tsx
  App.tsx               ← v1.3 — idle timer 9/10 min
  theme.ts              ← v2.3 — jedyne źródło kolorów
  global.css            ← placeholder, scrollbar, focus, select
  screens/
    LockScreen.tsx      ← v1.2
    MainLayout.tsx      ← v1.5
    Pseudonimizuj.tsx   ← v1.3
    Biblioteka.tsx      ← v1.5
    Depseudonimizuj.tsx ← v1.5
    SecurityScreen.tsx  ← v1.1 (pusty)
    OnboardingScreen.tsx ← v1.0
src-tauri/
  src/main.rs           ← v1.5
  tauri.conf.json       ← productName = "LynxMask Desktop", port 1420
  Cargo.toml
  capabilities/default.json
```

### Komendy Rust (main.rs v1.5)

| Komenda | Parametry | Zwraca | Uwagi |
|---------|-----------|--------|-------|
| `derive_and_store_key` | `password: String` | `Result<(), String>` | PBKDF2-SHA256, 500 000 iteracji. Weryfikuje przez key_verify.bin. |
| `encrypt_data` | `plaintext: Vec<u8>` | `Result<Vec<u8>, String>` | AES-256-GCM. |
| `decrypt_data` | `ciphertext: Vec<u8>` | `Result<Vec<u8>, String>` | AES-256-GCM. |
| `clear_key` | — | `()` | Zeruje klucz z pamięci. |
| `is_unlocked` | — | `bool` | Sprawdza czy klucz aktywny. |
| `read_api_token` | — | `Result<String, String>` | Szuka api_token.txt w 4 miejscach. |
| `is_first_run` | — | `bool` | Sprawdza czy key_verify.bin nie istnieje. |
| `save_depseudo_result` | `pse, text` | `Result<String, String>` | Zapisuje Dokumenty\Pseudominizer\{pse}\odpowiedz_NNN.txt. |
| `list_depseudo_responses` | `pse` | `Result<Vec<String>, String>` | Lista plików odpowiedz_NNN.txt. |
| `read_depseudo_response` | `pse, filename` | `Result<String, String>` | Czyta treść. Sanityzuje filename. |

---

## SEKCJA 6 — GDZIE SZUKAĆ GDY COŚ NIE DZIAŁA

```
PROBLEM: Nowy pipeline nie maskuje encji (USE_NEW_PIPELINE=True)
→ Sprawdź kolejność warstw w pipeline_new.py (reset_spans między nimi)
→ Sprawdź czy anonymizer != None w run_pipeline_new (validation wymaga)
→ Benchmark Run F (Coverage-Fix): Recall 89.7%, CLR 4.3%, OSOBA 96.3%

PROBLEM: Brakujące encje w nowym pipeline — numer_klienta / numer_faktury / numer_umowy
→ Nowy pipeline nie ma odpowiednika _layer2_regex (trie + słownik biurowy z anonymizer.py)
→ Planowana layers/trie.py jako adapter do anonymizer._layer1_trie() i _layer2_regex()
→ Formaty: KL-NNNNN, FV-NNNNN/MM/RRRR, UMW/RRRR/NNN

PROBLEM: Guard injection blokuje dokumenty niepotrzebnie
→ Stary pipeline: 4 blokady per 50 dok. Nowy: 0.
→ Stary: anonymize() sprawdzał tokeny wstawione przez własny pipeline (bez skip_guard)
→ Nowy: anonymize(skip_guard=True) + API [AUD-01] jako jedyna bariera

PROBLEM: Kolizje tokenów NUMER_NNN
→ W starym pipeline: 5 rozproszonych liczników (anonymizer.py×3, pipeline.py, verbal_amounts.py)
→ W nowym: jeden TokenAllocator — kolizje niemożliwe architekturalnie
→ Stary fix: existing_reverse_map + _layer2_regex skan TOKEN_SPAN_RE (v4.23-v4.24)

PROBLEM: Guard przepuszcza plaintext nazwisk
→ STATUS: BUG-1 NAPRAWIONY w pipeline.py v1.4
→ Dotyczy tylko starego pipeline (USE_NEW_PIPELINE=False)

PROBLEM: Tesseract nie działa na innej maszynie
→ ocr_engine.py BUG-10: hardkodowana ścieżka C:\Users\p_pie\... — krytyczne przed dystrybucją

PROBLEM: PSE_REGISTRY ścieżka względna
→ document_processor.py — BUG-12 otwarty

PROBLEM: guardBlocked=true nie wyświetla komunikatu użytkownikowi
→ Pseudonimizuj.tsx — BUG-UI-04 otwarty
```

---

## SEKCJA 7 — CHANGELOG MAPY

| Data | Co mapowano | Co zmieniono |
|------|-------------|--------------|
| 05.06.2026 | Pierwsze mapowanie — backend + frontend (Tauri v1.1) | Sekcje 1-6, 4 aktywne bugi zmapowane |
| 05.06.2026 | anonymizer.py v4.19, ner_layer.py v1.3 | Sekcja 2: tabele funkcji. Sekcja 3: graf. |
| 05.06.2026 | anonymizer_crypto.py v1, anonymizer_init.py | Sekcja 1+2: oba pliki. STRUCTURAL_PATTERNS. |
| 05.06.2026 | ocr_engine.py v1.1, ner_blocklist.py | BUG-10 zmapowany. |
| 05.06.2026 | audit_log.py, document_processor.py, verbal_amounts.py, crypto_selftest.py, export_pdf.py | Backend KOMPLETNY. BUG-11, BUG-12. |
| 05.06.2026 | Scalenie z mapą Tauri | Sekcja 5 kompletna. BUG-2 zamknięty, BUG-6 nowy, BUG-14 nowy. MAPA KOMPLETNA. |
| 09.06.2026 | Aktualizacja v2.0 — weryfikacja na rzeczywistych plikach | Nazwa → LynxMask Desktop. Wersje z plików. Nowe komendy Rust. BUG-1/4/B/B2/3/D/13/14 naprawione. |
| 14.06.2026 | Aktualizacja v2.1 — potok refaktoryzacji TokenAllocator | **Nowe pliki:** pipeline_core.py v0.2, pipeline_new.py v0.2, layers/ (8 modułów v1.0). **Wersje:** pipeline.py v1.21 (USE_NEW_PIPELINE), anonymizer.py v4.25 (skip_guard), anonymizer_init.py v1.8. **Benchmark:** Run A vs Run C — Precision +12.5pp (FP: 174→91), CLR remis 5.3%, Recall −8.1pp (regresja znana). **Graf:** dodano ścieżkę nowego pipeline. **Sekcja 6:** nowe scenariusze diagnostyczne. |
| 14.06.2026 | Aktualizacja v2.1 — Coverage-Fix (Run D/E/F) | **Wersje:** identity.py v1.1, address.py v1.4, ner_blocklist.py v1.3, ner_adapter.py v1.1, pipeline_new.py v0.4, pipeline_core.py v0.2+. **Nowy moduł:** layers/numeric.py v1.0 (KL-/FV-/UMW/). **Fix regresu OSOBA:** pre-ekstrakcja NER przed address layer (`extract_ner_results`). **Benchmark Run F:** CLR 4.3%, Recall 89.7%, OSOBA 96.3% (regres odwrócony), ADRES 93.5%. **Bugi:** BUG-NEW-1 ✅, BUG-NEW-2 ✅, BUG-ADDR-FP 🟡 nowy. |
| 14.06.2026 | Aktualizacja v2.1 — Testy + Słownik SIMC + Benchmark fix (Run G/H) | **Testy:** tests/test_pipeline_v2.py przepisane na run_pipeline_new + mock process_ner — 41 passed, 0 skip, 0 fail. **SIMC:** cities.json (31 117 miast, RM=01+96), cities_forms.json (179 370 form Morfeusz2). **address.py v1.5:** `_CITY_FORMS` frozenset + `_match_city()` — miasto musi być w bazie SIMC. **Run G = Run F** (FP ADRES to duplikaty z poprawnymi miastami — SIMC nie pomaga). **benchmark.py fix HTTP 400:** `accepted` filtr rozszerzony o `r.get("http_status") == 200` — doc z błędem ekstrakcji nie liczy się jako wyciek. **Run H:** CLR 3.2% (3/94), Recall 91.4%. **BUG-ADDR-FP** świadomy trade-off, deduplication zaplanowana. |

---

## OTWARTE BUGI (według priorytetu)

| ID | Opis | Plik | Priorytet |
|----|------|------|-----------|
| ~~BUG-NEW-1~~ | ~~NIP 766-444-75-06 nie wykrywany przez nowy pipeline.~~ **NAPRAWIONY** (identity.py v1.1, `[\-\.]` jako separator) | layers/identity.py | ✅ |
| ~~BUG-NEW-2~~ | ~~Brak pokrycia KL-NNNNN / FV-* / UMW/*.~~ **NAPRAWIONY** (layers/numeric.py v1.0) | layers/numeric.py | ✅ |
| BUG-ADDR-FP | ADRES precision 68.3% (FP=20). FP generowane przez duplikaty OCR multilinii — OCR dostarcza ten sam adres dwukrotnie w różnych formatach (z/bez łamania linii). Miasta w duplikatach są poprawne (SIMC potwierdza), więc SIMC integracja (Run G) nie pomogła. **Świadomy trade-off:** deduplication po kodzie pocztowym zaplanowana. Priorytet: potok Bezpieczeństwo (CLR). | layers/address.py | 🟡 |
| BUG-UI-04 | guardBlocked=true nie wyświetla komunikatu użytkownikowi | Pseudonimizuj.tsx | 🟡 |
| BUG-6 | Regex TOKEN_MATCH nie obsługuje sufiksu literowego (FIRMA_001A) — wymaga weryfikacji czy de facto naprawiony przez iterację po kluczach mapy | Depseudonimizuj.tsx | 🟡 |
| BUG-10 | Hardkodowana ścieżka Tesseract (C:\Users\p_pie\...) | ocr_engine.py | 🔴 przed dystrybucją |
| BUG-12 | PSE_REGISTRY ścieżka względna (CWD-dependent) | document_processor.py | 🟡 |
| BUG-I | Część adresu ("Władysława Andersa") wykrywana jako OSOBA | ner_layer / spacy_ner | 🟡 |
| BUG-E | Potencjalna utrata encji w _merge_adjacent_entities przy 4+ encjach z rzędu | spacy_ner.py | 🟡 |
| BUG-PERF-2 | SpaCy przetwarza tekst dwa razy per dokument — świadoma decyzja, do obserwacji | pipeline.py warstwa 1 | 🟢 |
