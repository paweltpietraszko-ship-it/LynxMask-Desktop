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

## Wersje kluczowych plików

- `layers/identity.py` v1.1
- `layers/numeric.py` v1.0
- `layers/address.py` v1.4
- `layers/institution.py` v1.0 (NOWY — 2026-06-25)
- `ner_blocklist.py` v1.3 (263 wpisy)
- `layers/ner_adapter.py` v1.1
- `pipeline_new.py` v0.4 + apply_institution_layer
- `pipeline_core.py` v0.2+
- `db_store.py` v1.0 (wydzielony z pseudominizer_api.py)
- `output_guard.py` — generyczny IBAN pattern

## Otwarte bugi — do naprawienia (priorytet malejący)

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

### BUG-ADDR-FP (SREDNI)
ADRES precision 68.3% (FP=20), duplikaty OCR multilinii → `layers/address.py`

### BUG-10 (WYSOKI — blokuje dystrybucję)
Hardkodowana ścieżka Tesseract → `ocr_engine.py`

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
