# LynxMask Desktop — Kontekst projektu dla Claude

## Czym jest projekt

Pseudonimizacja dokumentów OCR (LynxMask Desktop).
Backend: Python (`backend/`), Frontend: Tauri + React (`frontend/`).
Repo: https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop (prywatne)

## Stan po Coverage-Fix (2026-06-14) — ZAMKNIĘTY

Refaktoryzacja pipeline z rozproszonych liczników na TokenAllocator.
Cel: CLR ≤ 5.3%, recall > 88%. Osiągnięty.

**Najlepszy run: Run F** (run_20260614_140053) — `pipeline_new.py` v0.4
- CLR: 4.3%, Recall: 89.7%, Precision: 70.4%, F1: 78.9%, Semantic: 87.7%
- OSOBA recall: 96.3%, ADRES recall: 93.5%, ADRES precision: 68.3%
- Dataset: dataset_20260614_081730 (50 doc, seed stały)
- `USE_NEW_PIPELINE=True` aktywny w `pipeline.py` l.298

## Stan po Test-Fix (2026-06-25) — ZAMKNIĘTY

Naprawiono 34 czerwone testy. Commit: `bb2f5d1`.

**Wynik: `157 passed, 2 skipped, 1 xfailed, 0 failed`**

Przyczyny i naprawy:
1. Stale `.pyc` z wbitą starą ścieżką (`pseudominizer\`) → usunięto `tests/__pycache__/`
2. `_API_TOKEN` generowany przy imporcie modułu zamiast w `_lifespan()` → uvicorn spawn na Windows tworzył dwa tokeny → 401 → przeniesiono do `_lifespan()`
3. Brak warstwy INSTYTUCJA w `pipeline_new.py` → stworzono `layers/institution.py`, dodano do pipeline
4. `DB_PATH` / `_init_db` usunięte z `pseudominizer_api.py` po wydzieleniu `db_store.py` → dodano aliasy kompatybilności
5. Output guard tylko PL IBAN → dodano generyczny pattern `[A-Z]{2}\d{2}[\s\d]{10,30}`
6. Testy b5/b21/c7 napisane przed security guardem → zaktualizowane

2 celowe skipy:
- `test_b14` — pomijany gdy Morfeusz dostępny (test trybu degraded)
- `test_c10` — placeholder (decrypt_map() niedostępna z poziomu testu)

1 xfailed (celowy):
- `test_b19_kancelaria_naming` — KI-1, SpaCy rozbija "Kowalski i Wspólnicy" na dwa tokeny

## Stan po Bug-Fix (2026-06-25) — ZAMKNIĘTY

Naprawiono 6 bugów z portu Kotlin. Branch: `claude/jolly-hopper-hid2oh` → scalony z `main`.

Naprawione:
1. BUG-IBAN-LETTERS — IBAN z literami (GB/IE/MT) — `output_guard.py`
2. BUG-NIP-LEAK — format 3-2-2-3 — `anonymizer_init.py`, `layers/identity.py`, `output_guard.py`
3. BUG-INSTITUTION-FP — skróty (PPK/KNF/RPO) z `re.IGNORECASE` — `layers/institution.py`
4. BUG-INSTITUTION-ORDER — institution przed NER → regresja recall — `pipeline_new.py`
5. BUG-NER-FP — blocklist (kontrolna/encje) + filtr przymiotników — `ner_blocklist.py`, `ner_layer.py`

Testy po fixie (środowisko zdalne, brak cffi/pyo3): `18 failed (env), 85 passed, 56 skipped, 1 xfailed`

## Wersje kluczowych plików

- `layers/identity.py` v1.2
- `layers/numeric.py` v1.0
- `layers/address.py` v1.8
- `layers/institution.py` v1.0 (NOWY — 2026-06-25)
- `ner_blocklist.py` v1.3 (263 wpisy + kontrolna/encje)
- `ner_layer.py` v1.10 + _ADJECTIVE_ENDINGS_RE
- `layers/ner_adapter.py` v1.3 — WYS-1: try/except w extract_ner_results/apply_ner_layer, ner_error flag
- `pipeline_new.py` v0.6 — WYS-2: zwraca (text, map, force_block), try/except całego pipeline
- `pipeline_core.py` v0.2+
- `db_store.py` v1.0 (wydzielony z pseudominizer_api.py)
- `output_guard.py` v4.2 — WYS-3: check_blacklist_context błąd → GUARD_ERROR + blokada (fail-closed)
- `anonymizer_init.py` v1.9 — paszport ze spacją OCR ([A-Z]{2}[ \t]?\d{7})
- `layers/identity.py` v1.4 — paszport ze spacją OCR, BUG-UR-DOB (data urodzenia)
- `layers/financial.py` v1.1 — zagraniczne IBAN (DE, UA, GB, FR, NL) w pipeline
- `layers/contact.py` v1.3 — BUG-EMAIL-GREEDY fix + OCR-tolerancyjny email
- `layers/address.py` v1.9 — BUG-ADDR-OCR-DIACRITICS fix + SIMC ASCII-folded
- `layers/identity.py` v1.2 — OCR-tolerancyjny PESEL/NIP (spacje w liczbach)
- `smoke_test.py` v1.1 — smoke test blokujący start przy wycieku PII; pokrywa wszystkie 14 warstw pipeline (credentials, legal, numeric, amount, institution, ocr_normalizer dodane w v1.1); guard FP: ZUS/NFZ nie mogą być zamaskowane
- `pseudominizer_api.py` v1.32 — CRASH-UX: zapis startup_error.json przed śmiercią
- `frontend/src-tauri/src/main.rs` v1.6 — CRASH-UX: komendy read_startup_error, restart_app
- `frontend/src/screens/CrashScreen.tsx` v1.0 — NOWY: ekran awarii z kodem błędu i akcjami
- `frontend/src/App.tsx` v1.6 — CRASH-UX: retry tokenu + detekcja crashu → CrashScreen

### ~~BUG-PROFIL-PIPELINE~~ — NAPRAWIONY (pipeline.py, 2026-06-27)
`pipeline.py` linia 349 przekazywał `state.spacy_ner_mod` (moduł SpaCy) jako
`anon_map` do `run_pipeline_new` zamiast `state.anon_map` (słownik encji biura).
Trie działał bo `anonymizer` był poprawny, ale profil biura nie trafiał do NER.
Fix: `run_pipeline_new(text, state.anon_map or {}, state.anonymizer)`.

---

## Otwarte bugi — do naprawienia (priorytet malejący)

### ~~BUG-IBAN-LETTERS~~ — NAPRAWIONY
### ~~BUG-NIP-LEAK~~ — NAPRAWIONY
### ~~BUG-NER-FP (kontrolna/encje/przymiotniki)~~ — NAPRAWIONY
### ~~BUG-INSTITUTION-FP~~ — NAPRAWIONY
### ~~BUG-INSTITUTION-ORDER~~ — NAPRAWIONY

---

Źródło fixów: wersja mobile (Kotlin) `C:\Projects\LynxMask\`.

### BUG-IBAN-LETTERS (KRYTYCZNY — wyciek PII)
`backend/output_guard.py` linia 101. Pattern `[\s\d]{10,30}` nie obsługuje liter →
IBANy GB/IE/MT (literowy BBAN) nie są blokowane.
```python
# Zamień:
("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[\s\d]{10,30}\b")),
# Na (z OutputGuard.kt linia 59):
("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}\b")),
```

### BUG-NIP-LEAK (WYSOKI — wyciek PII)
Format NIP 3-2-2-3 (np. "512-34-56-789") nie jest tokenizowany.
Fix 1 — `backend/anonymizer_init.py` (dodać po wzorcu NIP 3-3-2-2):
```python
(TOKEN_NUMER, re.compile(r"(?<!\d)\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3}(?!\d)")),
```
Fix 2 — `backend/output_guard.py` linia 97, rozszerzyć wzorzec NIP:
```python
("NIP", re.compile(
    r"\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b"   # 3-3-2-2
    r"|\b\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3}\b"  # 3-2-2-3
)),
```

### BUG-NER-FP (WYSOKI — fałszywe pozytywy)
Widziane w UI: OSOBA_006="KONTROLNA", OSOBA_007="Encje", OSOBA_008="Kont0", FIRMA_001="Byt0m".
Fix 1 — `backend/ner_blocklist.py` (dodać do listy):
```python
"kontrolna", "kontrolny", "kontrolne", "kontrolnych", "kontrolnego",
"encje", "encja", "encji",
```
Fix 2 — `backend/ner_layer.py` (dodać filtr przymiotników, z NameEngine.kt linie 287-362):
```python
_ADJECTIVE_ENDINGS_RE = re.compile(
    r'(?i)(?:owego|owej|owym|owych|iego|iej|iem|owy|owa|owe|ową'
    r'|czny|czna|czne|cznego|cznej|cznym|cznych'
    r'|wny|wna|wne|wnego|wnej|wnym|wnych'
    r'|lny|lna|lne|lnego|lnej|lnym|lnych)\b'
)
# W _filter_institutions() przed out.append(ner):
if ner.label == "OSOBA" and _ADJECTIVE_ENDINGS_RE.search(entity_text):
    continue
```

### BUG-INSTITUTION-FP (ŚREDNI — fałszywe pozytywy)
`\bNIK\b`, `\bGUS\b`, `\bPIP\b` z `re.IGNORECASE` matchują imiona i polecenia IT.
Fix — `backend/layers/institution.py` linia 34:
```python
# Zamień:
r"|\bPPK\b|\bKNF\b|\bRPO\b|\bTK\b|\bPIP\b|\bGUS\b|\bNIK\b|\bUOKiK\b"
# Na (inline flag wyłącza IGNORECASE dla samych skrótów):
r"|(?-i:\bPPK\b|\bKNF\b|\bRPO\b|\bTK\b|\bPIP\b|\bGUS\b|\bNIK\b|\bUOKiK\b)"
```

### BUG-INSTITUTION-ORDER (ŚREDNI — architektura)
`apply_institution_layer` przed NER niszczy firmy zawierające słowa kluczowe instytucji
(np. "Kancelaria Sądu Rejonowego Sp. z o.o." → NER nie widzi pełnej nazwy).
Fix — `backend/pipeline_new.py`: przenieść `apply_institution_layer` PO `apply_ner_layer`:
```python
extract_ner_results(state, anon_map)
_apply(state, apply_address_layer)
_apply(state, apply_ner_layer, anon_map)
_apply(state, apply_institution_layer)   # PO NER, nie przed
_apply(state, apply_fallback_layer)
```
Zasada: `allocator.is_occupied()` zablokuje re-tokenizację spanów zajętych przez NER (FIRMA).

### ~~BUG-ADDR-FP~~ — NAPRAWIONY (address.py v1.6, 2026-06-26)
Faza 2a: gdy brak kodu pocztowego w dopasowaniu, wymagamy potwierdzenia
miejscowości w bazie SIMC GUS (179k form). Brak miasta w SIMC → pomiń.
Wcześniej wzorce bez kodu były akceptowane bez walidacji → FP.

### ~~BUG-10~~ — NAPRAWIONY (ocr_engine.py v1.2)
Hardkodowana ścieżka osobista C:/Users/p_pie/... zastąpiona przez
`os.path.expandvars("%LOCALAPPDATA%")` w `_TESSERACT_CANDIDATES`.

---

## Bugi z testu ręcznego PSE-2026-0756 (21.06.2026)

Plik testowy: 4 poziomy degradacji OCR, 4 typy dokumentów.
Wyniki encji z UI (37 tokenów) — poniżej NOWE bugi nieznane wcześniej.

### ~~BUG-NER-FP-INSTRUKCJE~~ — NAPRAWIONY (ner_blocklist.py v1.3+)
Słowa z instrukcji/UI dodane do `_NER_BLOCKLIST`:
"guardem", "wkleić", "wklej", "wklejam", "wklejanie", "share", "red", "dluzn"
Zweryfikowane w kodzie: wpisy istnieją w aktualnym ner_blocklist.py.

### ~~BUG-OCR-DEDUP~~ — NAPRAWIONY (ner_layer.py v1.12, 2026-06-26)
Przed obliczeniem `_person_stem` aplikujemy `normalize_ocr(entity_text)`.
"P4nina Agat3 K0walczyk" → po normalizacji OCR → ten sam stem co "Paulina Agate Kowalczyk".
entity_text (wartość tokenu) pozostaje oryginalna.
Plik: `backend/ner_layer.py` ~linia 336.

### ~~BUG-PESEL-DUP~~ — NAPRAWIONY (pipeline_core.py v0.2)
`TokenAllocator.allocate()` już deduplikuje przez `_canonical_to_token`.
Dwa PESEL-e z tą samą wartością kanoniczną dostają ten sam token.
Test E w pipeline_core.py potwierdza: len(reverse_map)==1 dla dwóch wariantów.

### ~~BUG-FIRMA-TRUNC~~ — NAPRAWIONY (ner_layer.py v1.11, 2026-06-26)
SpaCy zatrzymywał granicę encji przed sufiksem prawnym.
Naprawa: po rstrip() sprawdzamy czy entity_text kończy się na "Sp"/"S.A" itp.
i czy text[ner.end:] zaczyna się od ". z o.o." itp. — jeśli tak, doklejamy.
Regex `_SUFFIX_COMPLETION_RE` + `_TRUNC_ENDINGS` w ner_layer.py ~linia 145.

### ~~BUG-FIRMA-ZUS-MIX~~ — NAPRAWIONY (ner_layer.py v1.12, 2026-06-26)
`_filter_institutions` pomija encję FIRMA jeśli zawiera fragment instytucji
publicznej (ZUS, NFZ, KRUS, PIP itp.) — regex `_INSTITUTION_IN_FIRMA_RE`.
Plik: `backend/ner_layer.py` ~linia 139.

---

## Bugi z MASTER_LynxMask_Desktop.md (2026-06-26)

### ~~BUG-3~~ — NAPRAWIONY (pseudominizer_api.py [AUD-01])
Token injection: odrzut 422 gdy tekst wejściowy zawiera TOKEN_RE (FIRMA_001 itp.).

### ~~BUG-9~~ — ZAMKNIĘTY przez [AUD-01] (zweryfikowane 2026-06-26)
Scenariusz "mieszany dokument z nowym PII" nie może wystąpić — AUD-01 odrzuca
każdy tekst zawierający TOKEN_RE z kodem 422 przed wejściem do pipeline.
Pełny fix pipeline był zbędny — ochrona jest na poziomie wejścia.

### ~~BUG-2~~ — NAPRAWIONY (ner_layer.py v1.13, 2026-06-26)
Firma w cudzysłowie rozbijana — "Wiśniewski i Wspólnicy" → OSOBA_001.
Naprawa: encja SpaCy otoczona cudzysłowem w oryginalnym tekście wymusza FIRMA.

### ~~BUG-NEW-4~~ — NAPRAWIONY (pseudominizer_api.py, 2026-06-26)
Profil biura akceptował słowa pospolite. Dodana walidacja: _NER_BLOCKLIST +
_PL_STOPWORDS + min. 3 znaki przed zapisem w /profile/add-entity.

### ~~NUMER-RECALL~~ — NAPRAWIONY (contact.py v1.2, identity.py v1.2, 2026-06-26)
TELEFON 0% — fix w v1.1: _PHONE_CONTEXT_RE (tel./kom./mob./fax + numer przed REGON).
EMAIL 20% — fix w v1.2: _EMAIL_OCR_RE lapie emaile rozbite przez OCR:
  spacja/newline wokol @, © zamiast @, przecinek jako kropka w TLD.
  Wartosc kanoniczna w reverse_map = znormalizowany email (bez smieci OCR).
NUMER 3.8% — fix w identity.py v1.2: _DIGITS_WITH_SPACES_RE lapie PESEL/NIP
  rozbite spacjami przez OCR (11 cyfr=PESEL, 10 cyfr=NIP, z kanoniczna forma).
  REGON (9 cyfr) wykluczony — nie do odroznienia od telefonu z spacjami.
Mobile (OcrNormalizer.kt): emaile/telefony NIE sa normalizowane w OcrNormalizerze
  (tylko znaki 1/0/| miedzy literami i spacje w nazwach ulic/miast).
  Logika detekcji emaili jest w PseudonymEngine — nasza architektura spójna.

### ~~BUG-NER-FP-GRANICE~~ — NAPRAWIONY (ner_layer.py v1.14, 2026-06-26)
3 nowe filtry w _filter_institutions (zainspirowane analizą mobile Kotlin):
1. Nagłówki ALL-CAPS ≤2 słów bez sufiksu prawnego → odfiltrowane
2. Czyste akronimy [A-Z]{2,6} (ERP/CRM/IT) bez sufiksu → odfiltrowane
3. Jednosłowny przymiotnik jako FIRMA → odfiltrowany
Zachowuje: ABC S.A., wielosłowne nazwy z przymiotnikiem, OSOBA.

### ~~BUG-10-MASTER~~ — NAPRAWIONY (App.tsx v1.5, 2026-06-26)
tokenReady state blokuje MainLayout dopóki read_api_token nie ukończy.
Wcześniej UI było aktywne przez chwilę z apiToken="" → 401.

### ~~BUG-NEW-3~~ — NAPRAWIONY (db_store.py v1.1 + pseudominizer_api.py, 2026-06-26) [CRIT-1]
/archive/{pse}/blob zwraca 403 gdy guard_blocked=True. Nowa kolumna guard_blocked
w SQLite, migracja addytywna. POST /archive przyjmuje flagę od klienta; GET /blob
sprawdza przed wydaniem pliku .enc.

---

## Luki bezpieczeństwa (audyt 2026-06-26)

### ~~CRIT-2~~ — NAPRAWIONY (audit_log.py v1.2, 2026-06-26)
AUDIT_MODE był domyślnie True — logował PII przy każdej sesji produkcyjnej.
Pole "original" w _build_token_summary zawierało plaintext encji w logach.
Fix: AUDIT_MODE = False domyślnie; pole "original" usunięte z rekordu.

### ~~CRIT-3~~ — NAPRAWIONY (output_guard.py v3.8, 2026-06-26)
Fallback get_entity_names() w guard_output_with_map() połykał cicho wyjątek
→ guard martwy gdy metoda nie istniała. Fix: wyjątek dodaje violation GUARD_ERROR
i blokuje odpowiedź zamiast przepuszczać.

### ~~HIGH-2~~ — NAPRAWIONY (db_store.py v1.1, 2026-06-26)
Migracja używała DROP TABLE documents — niszczyła wszystkie archiwa użytkownika.
Fix: ALTER TABLE documents RENAME TO documents_backup_filename.

### ~~HIGH-5~~ — NAPRAWIONY razem z CRIT-2 (audit_log.py v1.2)
AUDIT_MODE = True domyślnie = zbędne logowanie w trybie produkcyjnym.

### ~~MED-1~~ — NAPRAWIONY (pipeline.py v1.23, 2026-06-26)
Guard wywoływany z niekompletną mapą gdy anonymizer się wysypał.
Fix: błąd anonymizera → force_block=True do _apply_guard(). Wyjątek samego
guarda też teraz blokuje zamiast cicho przepuszczać.

### ~~MED-2~~ — NAPRAWIONY (audit_log.py v1.3, 2026-06-26)
Audit log rósł bez limitu (open "a" bez rotacji).
Fix: RotatingFileHandler, max 2 MB, 3 backupy (.jsonl.1/2/3).

### ~~MED-4~~ — NAPRAWIONY (pseudominizer_api.py v1.31, 2026-06-26)
Logger w /profile/add-entity ujawniał token_type ("OSOBA", "FIRMA").
Fix: usunięty z logu — zostaje tylko token_id.

### ~~WYS-1~~ — NAPRAWIONY (ner_adapter.py v1.3, 2026-06-26)
`extract_ner_results()` i `apply_ner_layer()` nie miały try/except — crash NER
(np. brak SpaCy, wyjątek w process_ner) był połykany cicho, pipeline kontynuował
bez NER, imiona i nazwy firm nie były maskowane.
Fix: try/except w obu funkcjach → `state.ner_error = True` przy błędzie.
`run_pipeline_new()` sprawdza flagę i zwraca `force_block=True` do callera.
Zasada: fail-closed — błąd NER blokuje odpowiedź, nie przepuszcza niezamaskowaną.

### ~~WYS-2~~ — NAPRAWIONY (pipeline_new.py v0.6, 2026-06-26)
`run_pipeline_new()` nie miała obsługi błędów — nieoczekiwany wyjątek z dowolnej
warstwy leciał niezłapany do callera który nie wiedział o blokadzie.
Fix: try/except wokół całego pipeline → przy wyjątku zwraca `(text, {}, True)`.
Sygnatura zmieniona: `→ tuple[str, dict, bool]` (dodano force_block).
`pipeline.py` zaktualizowany — rozpakowuje 3 wartości i przekazuje `force_block`
do `_apply_guard()`.

### ~~WYS-3~~ — NAPRAWIONY (output_guard.py v4.2, 2026-06-26)
`check_blacklist_context` błąd w `guard_output_with_map()` był tylko logowany
jako `logger.warning` — pipeline kontynuował bez sprawdzenia blacklisty → PII
mogło przejść przez guard bez detekcji.
Fix: `except` dodaje `violation = ["GUARD_ERROR: ..."]` → guard blokuje odpowiedź.
Fail-closed: błąd guard = blokada, nie ostrzeżenie.

### ~~BUG-7~~ — ZAMKNIĘTY (zweryfikowane 2026-06-26)
check_blacklist_context() jest wywoływana w output_guard.py linia 300,
w ramach guard_output_with_map() → _apply_guard() w pipeline.
Funkcja nie zginęła — przeniesiona do warstwy guard. check_and_block() to osobna
funkcja SpaCy w pipeline.py (linia 379), wywołuje ją stary pipeline przed NER.

### ~~OBS-ADRES-DOUBLE-TOKEN~~ — NAPRAWIONY (address.py v1.7, 2026-06-26)
Wszystkie trzy fazy zbierają hity na tym samym tekście wejściowym, potem
jeden _apply_hits. Wcześniej offset shift między fazami powodował że
is_occupied nie wykrywał pokryć → duplikat ADRES token.

### ~~BUG-UR-DOB~~ — NAPRAWIONY (identity.py v1.4, 2026-06-26)
Wzorzec `ur. DD.MM.RRRR` nie był maskowany mimo że istniał w `STRUCTURAL_PATTERNS`.
Przyczyna: `_IDENTITY_SOURCES` miał literalne `ZŁŚŹĆŃ`, a `anonymizer_init.py`
kompilował wzorzec z `ŁŚŹĆŃ` — te same znaki, ale inne
bajty w stringu → `pat.pattern in frozenset` zwracał `False` → wzorzec cicho
wypadał z `_IDENTITY_PATTERNS`.
Fix: klucz w `_IDENTITY_SOURCES` zmieniony na zapis `\u` zgodny z `anonymizer_init.py`.

### ~~BUG-PASSPORT-SPACE~~ — NAPRAWIONY (anonymizer_init.py v1.9, identity.py v1.3, output_guard.py v4.1, 2026-06-26)
Paszport ze spacją (`ZX 1234567`) nie był maskowany przez pipeline ani wykrywany przez Guard.
OcrNormalizer usuwa spację tylko gdy w kontekście jest słowo "paszport:" — bez kontekstu
spacja pozostaje i stary wzorzec `[A-Z]{2}\d{7}` nie pasował.
Fix pipeline: wzorzec zmieniony na `[A-Z]{2}[ \t]?\d{7}` — łapie oba warianty.
Fix Guard: dodano DOWOD i PASZPORT do `_LEAK_HIGH` — Guard w ogóle nie miał tych wzorców.
Wzorce Guard zgodne z zasadą GUARD-BROAD: opcjonalna spacja między serią a numerem.

### ~~GUARD-BROAD~~ — NAPRAWIONY (output_guard.py v4.0, 2026-06-26)
Guard nie może powielać wzorców pipeline — jeśli pipeline coś przepuści, identyczny
wzorzec w Guardzie też to pominie. Guard powinien patrzeć szerzej.
IBAN: zamiast walidować grupy po 4 znaki (jak pipeline), Guard używa prostego
"odcisku palca": CC (2 litery) + DD (2 cyfry) + min. 11 znaków alfanumerycznych
z opcjonalnymi spacjami — agnostyczny wobec formatu zapisu. Łapie IBAN z grupami
po 3 (OCR), niestanddardowymi spacjami itp. — cokolwiek co "wygląda jak IBAN".
NIP: dodano `\d{10}` jako trzecia alternatywa — łapie NIP bez separatora
i z dowolnym separatorem (np. OCR wstawi `.` zamiast `-`).
Zasada: pipeline = precyzyjny, Guard = szerszy odcisk palca.

### ~~BUG-4~~ — NAPRAWIONY (financial.py v1.1, output_guard.py v3.9, 2026-06-26)
Zagraniczne IBAN (DE, UA, GB, FR, NL i inne) nie były maskowane przez pipeline
ani flagowane przez Guard.
Fix pipeline: `_IBAN_FOREIGN_RE` — dwa warianty: ze spacjami (grupy po 4) i compact
(ciągły). Stosowany po wzorcach PL. Guard FP-filtr: min 15 znaków (najkrótszy IBAN = NO).
Fix Guard: zaktualizowano `_LEAK_HIGH` IBAN pattern — stary wzorzec `\s?` nie łapał
compact IBANs. Nowy: dwa alternatywy (spaced + compact), pokrywa wszystkie kraje.

### ~~BUG-EMAIL-GREEDY~~ — NAPRAWIONY (contact.py v1.3, 2026-06-26)
`_EMAIL_OCR_RE` bez `(?!\w)` na końcu łapał zbyt dużo: po emailu `firma.pl,`
separator `, ` pasował do `[ \t]{0,1}[.,][ \t]{0,1}`, a `paszpo` (6 znaków)
pasowało do `[a-zA-Z]{2,6}` jako rzekomy TLD → `jan.kowalski@firma.pl, paszpo`
zamiast `jan.kowalski@firma.pl`. Email zostawał niezamaskowany.
Fix: dodano `(?!\w)` — TLD nie może być poprzedzone kolejną literą/cyfrą.
Regex cofa się i dopasowuje właściwy TLD (`pl` po `.` z poprzednim backtracking).

### ~~BUG-ADDR-OCR-DIACRITICS~~ — NAPRAWIONY (address.py v1.9, 2026-06-26)
OCR często gubi diakrytyki w nazwach miast: `Krakow` zamiast `Kraków`,
`Gdansk` zamiast `Gdańsk`. Baza SIMC zawiera tylko formy z polskimi znakami
→ `_match_city("Krakow")` zwracało `None` → adres z kodem pocztowym nie był maskowany.
Fix: zbudowano `_CITY_FORMS_ASCII` (słownik ascii-fold → oryginalna forma SIMC).
`_match_city` sprawdza najpierw dokładne dopasowanie, potem ASCII-folded.
Wartość w tokenie = oryginalna forma SIMC (np. `Kraków`).

### ~~CRASH-UX~~ — NAPRAWIONY (pseudominizer_api.py v1.32, main.rs v1.6, CrashScreen.tsx v1.0, App.tsx v1.6, 2026-06-26)
Gdy smoke test blokował start backendu, użytkownik widział pusty ekran "Ładowanie sesji…"
bez żadnej podpowiedzi co zrobić.
Fix — 4 warstwy:
1. **Backend**: `_write_startup_error(code, message)` zapisuje `backend/startup_error.json`
   przed re-raise RuntimeError. Na początku `_lifespan()` plik jest kasowany (stare błędy
   nie blokują nowego startu).
2. **Tauri** (`main.rs`): `read_startup_error()` — szuka `startup_error.json` w katalogu
   backendu (ta sama logika co `find_token_file`, ale bez wymagania istnienia pliku).
   `restart_app()` — restartuje aplikację przez `app.restart()`.
3. **CrashScreen.tsx**: nowy pełnoekranowy komponent — kod błędu, przycisk "Uruchom ponownie",
   link mailto z wypełnionym tematem/treścią, instrukcja reinstalacji krok po kroku.
4. **App.tsx**: po nieudanym `read_api_token()` czeka 4s i próbuje ponownie (backend może
   jeszcze startować). Drugi błąd → `read_startup_error()` → jeśli plik istnieje: CrashScreen
   z kodem błędu; jeśli nie: CrashScreen z `STARTUP-NO-RESPONSE`.

### ~~SMOKE-RESET-SPANS~~ — NAPRAWIONY (smoke_test.py, 2026-06-26)
Smoke test wywołał warstwy bez `reset_spans()` między nimi. Allocator
przechowywał spany z `identity_layer` (pozycje w oryginalnym tekście).
Po zamianie tokenów pozycje się przesuwają — spany identity trafiały
na offsety emaila i adresu w zmodyfikowanym tekście → `is_occupied()` zwracało True
→ contact i address layer nie maskowały PII. Email i adres wyciekały.
Fix: `reset_spans()` przed każdą warstwą — identycznie jak `_apply()` w pipeline_new.py.
Smoke test teraz przechodzi: wszystkie 7 kategorii PII zamaskowane.

### ~~BUG-ADDR-STREET-LOST~~ — NAPRAWIONY (address.py v1.8, 2026-06-26)
Gdy adres zawierał kod pocztowy (np. "ul. Kwiatowa 12/3, 30-001 Kraków"),
ulica wypadała z tokenu — token zawierał tylko "30-001 Kraków".
Przyczyna: faza 2b (_POSTAL_ANCHOR_RE) tworzyła hit "30-001 Kraków" (start=31),
który był przetwarzany przed hitem fazy 1 (start=12, pełny adres) — sort malejący
po start. Faza 2b allokowała span, faza 1 trafiała na is_occupied → odrzucona.
Fix: _apply_hits najpierw alokuje od największego spanu (większy hit wygrywa
przy nakładaniu), potem podmienia tekst od prawej (spójność pozycji).
Zweryfikowane na mobile: OcrNormalizer.kt reaguje na sam prefiks ul./al./pl./os.
bez wymagania kodu pocztowego — ta sama zasada działania.

## Uwagi praktyczne

- `backend/api_token.txt` — generowany przy starcie `pseudominizer_api.py` przez `_lifespan()`, nie w repo
- `backend/anon_profiles/` — dane użytkownika, nie w repo
- Testy: `cd backend && python -m pytest tests/ -q` (wymaga działającego backendu na :8765)
- Backend start: `cd backend && python pseudominizer_api.py`
- Logi testów: `backend/pytest.log` (DEBUG, generowany automatycznie)
- Dataset (50 doc): `backend/generator.py`

## Wersje kluczowych plików (aktualne po 2026-06-26)

- `layers/identity.py` v1.4
- `layers/contact.py` v1.4 — BUG-EMAIL-GREEDY + OCR email + 3-2-2 telefon
- `layers/legal.py` v1.1 — KRS + sygnatura ukośnikowa
- `layers/credentials.py` v1.0 (NOWY) — prawa zawodu, licencje, legitymacje
- `layers/trie_layer.py` v1.0 (NOWY) — słownik klienta L1 jako pierwsza warstwa
- `credential_patterns.json` — 20 wzorców, edytowalny JSON
- `pipeline_new.py` v0.9 — credentials po identity, trie jako L1
- `ner_layer.py` v1.16 — _COURT_PREFIX_RE filtr sądów z miastem
- `layers/ner_adapter.py` v1.6 — _ADDR_PREFIX_RE, _BARE_SUFFIX_RE, _FIRMA_CLEANUP_RE
- `ner_blocklist.py` v1.3
- `street_names.json` (NOWY) — 10959 ulic z odmianami Morfeusza

---

## Różnice funkcjonalne Mobile ↔ Desktop (stan 2026-06-26)

Źródło: analiza porównawcza Pawła. Podstawa do planowania ujednolicenia.

### 1. Obraz — największa różnica produktowa

| Funkcja | Mobile | Desktop |
|---|---|---|
| Wejście obrazu | Share z galerii/apki → ShareTargetActivity | Drag PDF/obraz → OCR w backendzie |
| Redakcja pikseli | ✅ ImageRedactionPipeline — blur twarzy, ręczne prostokąty, linie tekstu z PII | ❌ brak |
| OCR na obrazie | ML Kit + silnik decyduje co zamazać na bitmapie | Tesseract → tekst → maskowanie w tekście, obraz oryginalny bez redakcji wizualnej |
| Zapis w bibliotece | ✅ sesja typu obraz (saveRedactedImage, JPEG) | ❌ tylko tekst + mapa tokenów |
| UI edycji | ✅ ImageRedactionScreen (podgląd, regiony, zapis) | ❌ |

**Wniosek:** Mobile ma warstwę obrazu (P1 w MASTER Mobile). Desktop ma „czytanie obrazów" tylko jako OCR → pipeline tekstowy. Użytkownik na telefonie dostaje zamazany JPG, na Desktopie zanonimizowany tekst.

### 2. Onboarding — jest na obu, ale nie wspólny

| Element | Mobile (OnboardingScreen.kt) | Desktop (OnboardingScreen.tsx) |
|---|---|---|
| Długość | 1 ekran, 3 kroki + „Zacznij" | 5 kart + ustawienie hasła |
| Treść | Udostępnij → Zamaskuj → Wyślij | Pseudonimizacja, wgrywanie, ręczne uzupełnianie, odmaskowanie, karta OCR |
| Hasło | Osobno w LoginScreen | Wbudowane w onboarding (pierwsze uruchomienie) |

MASTER Desktop: „adaptowany z Mobile, treść do zmiany później" — wspólny onboarding to cel, nie stan.
Desktop bogatszy; Mobile nie ma kart OCR / odmaskowania / profilu biura.

**Do ujednolicenia:** ta sama lista kart (min. OCR, ręczne maskowanie, odmaskowanie, lokalność danych) + ten sam język, nawet jeśli UI (Compose vs React) osobne.

### 3. Przenoszenie pamięci / plików Mobile ↔ Desktop

| Mechanizm | Mobile | Desktop | Wspólny? |
|---|---|---|---|
| Eksport słownika .lynxdict | ✅ Ustawienia → eksport/import JSON | ❌ brak UI | Tylko Mobile |
| Profil biura (encje ręczne) | UserDictionary (słownik A) | POST /profile/add-entity → anon_profiles/ | Osobne magazyny, brak sync |
| GuardAllowlist (słownik B) | ✅ „Nie maskuj" → trwały wpis | ❌ nie zaimplementowany | Tylko Mobile |

MASTER (sekcja 4 obu projektów): sync .lynxdict planowany, trigger po 10 encjach — nie zrobiony end-to-end.

**Sesje nie da się teraz przenosić** — różne formaty identyfikatorów:
- Mobile: `SESJA_XXXXXX` (6 znaków, PseudonymEngine) / UUID w SQLCipher
- Desktop: `PSE-1234-5678` (nagłówek API) / SQLite + .enc bloby (Tauri/Rust)

Docelowy format z MASTER: `TYP_XXXXXX_NNN` — jeszcze nie wdrożony.

### 4. Wejście dokumentu — różne „okna" na ten sam cel

| Funkcja | Mobile | Desktop |
|---|---|---|
| Share z innej apki | ✅ ShareTargetActivity | ❌ |
| Kafelek szybkiego schowka | ✅ ClipboardCheckActivity + tile | ❌ |
| Wklej ze schowka | ✅ (przez share/tile) | ✅ kolumna tekstu |
| PDF / DOCX natywnie | ❌ (obraz/tekst) | ✅ document_processor |
| Eksport PDF zamaskowany | ❌ | ✅ /export-pdf |
| Jakość OCR — hard reject | banner ostrzegawczy | HTTP 422 przy conf < 70% |

### 5. Słowniki — wzorzec wspólny w MASTER, różny w kodzie

MASTER definiuje dwa słowniki (Mobile = wzorzec):
- **A — UserDictionary:** maskuj to zawsze
- **B — GuardAllowlist:** Guard, nie alarmuj

| Element | Mobile | Desktop |
|---|---|---|
| Słownik A + UI | ✅ | częściowo (profile/add-entity, bez pełnego ekranu zarządzania) |
| Słownik B | ✅ | ❌ |
| Eksport .lynxdict | ✅ | ❌ |
| UX Guard YELLOW: „Maskuj" / „Nie maskuj" | ✅ PseudonymResultPanel | ❌ brak GuardAllowlist |
| Silnik konsultuje słownik A | ✅ | ✅ trie_layer (gdy profil podpięty) |

### 6. Bezpieczeństwo i sesja — podobny cel, inna implementacja

| Element | Mobile | Desktop |
|---|---|---|
| Szyfrowanie danych | SQLCipher + Keystore | AES-256-GCM, PBKDF2, Rust |
| Timeout / wylogowanie | flagi w prefs | 10 min idle → kasowanie klucza |
| Ekran „Zabezpieczenia" | w ustawieniach (fragment) | ✅ SecurityScreen (pełny opis) |
| Audit log | SessionStore.recordAudit | pseudominizer_audit.jsonl |

Funkcja podobna; format plików niekompatybilny.

### 7. Rzeczy tylko Desktop / tylko Mobile (poza silnikiem)

**Tylko Mobile:**
- Redakcja obrazu (twarz, podpis, regiony)
- Share Target + kafelek schowka
- Sesje-obrazy w bibliotece
- Eksport/import .lynxdict
- GuardAllowlist w UI

**Tylko Desktop:**
- PDF/DOCX pipeline
- Eksport PDF
- Profil biura w plikach anon_profiles/
- Benchmark + generator datasetów
- Backend FastAPI (osobny proces)
- SpaCy NER (backend)

**Planowane oba, brak w kodzie:**
- Express Mode (bez logowania, bez biblioteki)
- Sync pełnej biblioteki Mobile ↔ Desktop
- Taksonomia 9 typów tokenów
- Format tokenu z sufiksem sesji: `TYP_XXXXXX_NNN`

---

## Dokumentacja w repo

- `backend/MASTER_LynxMask_Desktop.md` — główny dokument projektu
- `backend/MAPA_ARCHITEKTURY_LynxMask_Desktop_v2_1.md` — architektura
- `backend/RAPORT_Coverage_Fix.txt` — pełna tabela runów A/D/E/F
