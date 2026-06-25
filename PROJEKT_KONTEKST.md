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

### Czerwone testy (34 failures) — pre-existing, nie spowodowane migracją

Uruchom: `cd backend && python -m pytest tests/ --tb=line -q`

Klasy z failami (wymagają naprawy pipeline dla plain text przez /preview):
- `TestBug1PublicInstitutions` — ZUS, sądy, urzędy skarbowe, trybunal nie tokenizowane jako INSTYTUCJA
- `TestNERDetection` — Jan Kowalski, IBAN, OSOBA, PESEL nie wykrywane przez NER
- `TestConsistency` — ta sama osoba dostaje różne tokeny
- `TestEdgeCases` — długi dokument z wyciekiem
- `TestFirmaAttackToken::test_b5` — ValueError przy fake tokenach w inputcie

Uwaga: benchmark (OCR pipeline) działa poprawnie — OSOBA recall 96.3% w Run F.
Problem dotyczy ścieżki plain text → /preview (bez OCR). spaCy model działa.

### Stan suite testów (2026-06-25)
`106 passed, 34 failed, 19 skipped, 1 xfailed`

---

## ZADANIE STARTOWE DLA CLAUDE

**Cel: przywrócić testy do zielonego stanu (były zielone wcześniej).**

Zacznij od diagnostyki — uruchom testy i znajdź root cause:

```bash
cd backend
python -m pytest tests/test_pseudominizer.py -x --tb=long -q
```

Hipoteza do sprawdzenia: pipeline `/preview` dla pliku `.txt` (plain text, bez OCR)
nie przechodzi przez warstwę NER/spaCy — podczas gdy benchmark wysyła obrazy PNG
i działa poprawnie (OSOBA recall 96.3%). Sprawdź w `pseudominizer_api.py` jak
endpoint `/preview` rozgałęzia się dla `text/plain` vs `image/*`.

Kluczowe pliki:
- `backend/pseudominizer_api.py` — endpoint `/preview`
- `backend/pipeline.py` / `backend/pipeline_new.py` — pipeline główny
- `backend/spacy_ner.py` / `backend/ner_layer.py` — warstwa NER
- `backend/tests/test_pseudominizer.py` — failing tests

Backend uruchomisz przez: `python pseudominizer_api.py`
Token do requestów: czytany automatycznie z `api_token.txt` (generowany przy starcie).

## Dokumentacja w repo

- `backend/MASTER_LynxMask_Desktop.md` — główny dokument projektu
- `backend/MAPA_ARCHITEKTURY_LynxMask_Desktop_v2_1.md` — architektura
- `backend/RAPORT_Coverage_Fix.txt` — pełna tabela runów A/D/E/F

## Aktywny problem — TESTY CZERWONE (2026-06-25)

Testy które były zielone padły po sesji sprzątania backendu/benchmarku.

**Hipoteza (drugi Claude):** problem z `/preview` — różnica obsługi plain text vs OCR.
Kluczowe pliki do sprawdzenia: `pseudominizer_api.py` (endpoint `/preview`), `pipeline.py` (l.298 `USE_NEW_PIPELINE=True`).

**Komenda startowa:**
```
cd C:\Users\p_pie\Desktop\pseudominizer
python -m pytest tests\test_pipeline_v2.py tests\test_pipeline_adversarial.py -x --tb=long
```

Wklej wynik (stacktrace) do Claude — bez tego diagnoza jest zgadywaniem.

## Uwagi praktyczne

- `backend/api_token.txt` — generowany automatycznie przy starcie `pseudominizer_api.py`, nie w repo
- `backend/anon_profiles/` — dane użytkownika, nie w repo
- Dataset (50 doc) można wygenerować przez `backend/generator.py`
- Benchmark (Linux): `cd backend && python run_benchmark.py --count 50`
- Testy (Linux): `cd backend && python -m pytest tests/ -q`
- Backend start: `cd backend && python pseudominizer_api.py`
