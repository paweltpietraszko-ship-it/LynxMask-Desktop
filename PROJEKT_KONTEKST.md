# LynxMask Desktop — Kontekst projektu dla Claude

## Czym jest projekt

Pseudonimizacja dokumentów OCR (LynxMask Desktop).
Backend: Python (`backend/`), Frontend: Tauri + React (`frontend/`).
Oryginalne foldery: `pseudominizer` (backend) i `pseudominizer-tauri` (frontend).

## Stan po Coverage-Fix (2026-06-14) — ZAMKNIĘTY

Refaktoryzacja pipeline z rozproszonych liczników na TokenAllocator.
Cel: CLR ≤ 5.3%, recall > 88%. Osiągnięty.

**Najlepszy run: Run F** (run_20260614_140053) — `pipeline_new.py` v0.4
- CLR: 4.3%, Recall: 89.7%, Precision: 70.4%, F1: 78.9%, Semantic: 87.7%
- OSOBA recall: 96.3%, ADRES recall: 93.5%, ADRES precision: 68.3%
- Dataset: dataset_20260614_081730 (50 doc, seed stały)
- `USE_NEW_PIPELINE=True` aktywny w `pipeline.py` l.298

## Wersje kluczowych plików

- `layers/identity.py` v1.1
- `layers/numeric.py` v1.0 (NOWY)
- `layers/address.py` v1.4
- `ner_blocklist.py` v1.3 (263 wpisy)
- `layers/ner_adapter.py` v1.1
- `pipeline_new.py` v0.4
- `pipeline_core.py` v0.2+

## Otwarte problemy

- **BUG-ADDR-FP** 🟡 — ADRES precision 68.3% (FP=20), duplikaty OCR multilinii → `layers/address.py`
- **BUG-10** 🔴 — hardkodowana ścieżka Tesseract (blokuje dystrybucję) → `ocr_engine.py`

## Dokumentacja w repo

- `backend/MASTER_LynxMask_Desktop.md` — główny dokument projektu
- `backend/MAPA_ARCHITEKTURY_LynxMask_Desktop_v2_1.md` — architektura
- `backend/RAPORT_Coverage_Fix.txt` — pełna tabela runów A/D/E/F

## Uwagi praktyczne

- `backend/api_token.txt` — generowany automatycznie przy starcie `pseudominizer_api.py`, nie w repo
- `backend/anon_profiles/` — dane użytkownika, nie w repo
- Dataset (50 doc) można wygenerować przez `backend/generator.py`
