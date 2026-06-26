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

- `layers/identity.py` v1.1
- `layers/numeric.py` v1.0
- `layers/address.py` v1.8
- `layers/institution.py` v1.0 (NOWY — 2026-06-25)
- `ner_blocklist.py` v1.3 (263 wpisy + kontrolna/encje)
- `ner_layer.py` v1.10 + _ADJECTIVE_ENDINGS_RE
- `layers/ner_adapter.py` v1.1
- `pipeline_new.py` v0.4 — institution PO NER
- `pipeline_core.py` v0.2+
- `db_store.py` v1.0 (wydzielony z pseudominizer_api.py)
- `output_guard.py` v3.7 — IBAN z literami, NIP 3-2-2-3

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

### ~~NUMER-RECALL (telefon)~~ — NAPRAWIONY częściowo (contact.py v1.1, 2026-06-26)
TELEFON 0% — 9-cyfrowy numer bez separatorów był pochłaniany przez identity jako REGON.
_PHONE_CONTEXT_RE: tel./kom./mob./fax + numer → TOKEN_NUMER, rejestrowany przed identity.
Pozostałe przyczyny FP (EMAIL 20%, NUMER 3.8%) — otwarte, wymagają analizy wzorców.

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

### ~~BUG-7~~ — ZAMKNIĘTY (zweryfikowane 2026-06-26)
check_blacklist_context() jest wywoływana w output_guard.py linia 300,
w ramach guard_output_with_map() → _apply_guard() w pipeline.
Funkcja nie zginęła — przeniesiona do warstwy guard. check_and_block() to osobna
funkcja SpaCy w pipeline.py (linia 379), wywołuje ją stary pipeline przed NER.

### ~~OBS-ADRES-DOUBLE-TOKEN~~ — NAPRAWIONY (address.py v1.7, 2026-06-26)
Wszystkie trzy fazy zbierają hity na tym samym tekście wejściowym, potem
jeden _apply_hits. Wcześniej offset shift między fazami powodował że
is_occupied nie wykrywał pokryć → duplikat ADRES token.

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

## Dokumentacja w repo

- `backend/MASTER_LynxMask_Desktop.md` — główny dokument projektu
- `backend/MAPA_ARCHITEKTURY_LynxMask_Desktop_v2_1.md` — architektura
- `backend/RAPORT_Coverage_Fix.txt` — pełna tabela runów A/D/E/F
