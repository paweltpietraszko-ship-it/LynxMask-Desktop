# LYNX-TOKEN-RE-SPEC — DELIVERY r1 (CC)

Kod: `a2f65a8` (commity `e3bb394` + `a2f65a8`) na brief `53eb470` (Codex PASS PREIMPLEMENTATION `a68c013`). Gałąź zsynchronizowana z main (`2fc0f61`).

## Zmiany
**A — wzorzec tokenu zgodny z S2.** Koniec każdej kopii to `(?!\d)` zamiast `\b`. Początek `\b` i struktura grup bez zmian.
- `anonymizer_init.TOKEN_RE` (2 grupy) i `TOKEN_SPAN_RE` (bez grup);
- `_TOKEN_RE` w `pseudominizer_api.py`, `pipeline.py`, `ner_layer.py`, `verbal_amounts.py`, `output_guard.py`;
- `layers/ner_adapter._TOKEN_RE`: dodana brakująca INSTYTUCJA, co daje pełną taksonomię Desktop;
- `Pseudonimizuj.tsx` (podświetlanie): `\d{3}(?!\d)`;
- **10. kopia, znaleziona przeglądem**: przycinanie wejścia `/profile/add-entity` (`re.split(... _\d{3}\b)`) w `pseudominizer_api.py` — plik w TASK_SCOPE, ta sama klasa.

Poza zakresem zostały: `pipeline_new.test_pipeline_new` (wewnętrzny autotest modułu, nie produkt), `pseudominizer.html` (stary frontend, OUT_OF_SCOPE), `pipeline._FIRMA_CLEANUP_RE` (inna funkcja, martwy kod).

**B — BUG-ONBOARD-BATCH.** `anonymizer.py` importuje `MAX_ONBOARD_BATCH` z `anonymizer_init`.

**C — BUG-SEED-DEAD.** `_lifespan` nie woła seedu (komentarz: diagnoza M1). `seed_profile.py` ma nagłówek „NIEUŻYWANY PRZEZ PRODUKT… tylko dla skryptów w audyt/”. W `test_audyt_2026_10.py`:
- markery xfail BUG-TOKEN-RE-SPEC i BUG-ONBOARD-BATCH zdjęte, a testy naprawdę przechodzą;
- test BUG-SEED-DEAD usunięty z komentarzem o świadomym wyłączeniu, bez naprawy seedu.

## Testy
- **Nowy `tests/test_token_re_spec.py`** (18 testów):
  - 8 przypadków × 8 kopii wzorca, porównanie dopasowanych tekstów (uwaga Codexa): „OSOBA_001”, „OSOBA_001x”, „NUMER_004Teresa”, „INSTYTUCJA_002, EMAIL_003.”, „KWOTA_005_ADRES_006”, „OSOBA_0012” (brak), „xOSOBA_001” (brak), „FIRMA_01/FIRMA_1” (brak);
  - grupy bez zmian (`TOKEN_RE.findall` → krotki, `TOKEN_SPAN_RE.findall` → teksty);
  - `/preview` z „OSOBA_001x”, „NUMER_004Teresa” i „INSTYTUCJA_002” → **422** dla tokenu pełnego i Express;
  - tekst bez tokenu → 200;
  - `add_entities_batch` (2 encje) na izolowanym profilu;
  - `_lifespan` nie zawiera `seed_if_needed`.
- **RED** na kodzie z main: **11 failed / 7 passed** (przyklejony token → 200, niezgodność kopii, `NameError` batch, seed w starcie). **GREEN: 18 passed.**
- `test_audyt_2026_10.py`: 3 xfailed zostają (BUG-NER-FIRMA-INST ×2, BUG-NER-FP). To jakość NER, test odbioru nowego silnika.
- Backend z gałęzi (`wt_board`, port 8765, profil Pawła):

  | Zestaw | Wynik |
  |---|---|
  | `tests/` | **167 passed, 2 skipped, 1 xfailed** |
  | `test_token_re_spec`, `test_audyt_2026_10`, `test_failclosed`, `test_startup_check`, `test_disk_pii`, `test_layers`, `test_express_one_engine`, `test_map_fidelity`, `test_ner_multiline` | **363 passed, 3 xfailed** |
  | `tsc --noEmit` | 0 |
  | `ruff` | bez nowych uwag (poprawiony jeden E401 w nowym teście) |

- **178 dok. przez `/preview` z profilem Pawła:** gałąź vs main → **0 różnic** (wynik, tokeny, blokady), 178× 200, 59 blokad. Żaden realny dokument nie zawiera przyklejonego tokenu, więc nowa kontrola nie odrzuciła żadnego.

## Gate (dosłownie, bez listy IMPORTERS_FOR_REVIEW)
```
STATUS: PASS
HEAD_SHA: a2f65a8b0185a066f6dacdc46bfb0d9378cf66a6
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
```
Program i test audytu: +18/−25. Nowy test: 105 linii (szacunek +15/−10 i +50; test większy przez parametryzację 8 kopii × 8 przypadków oraz dwa tryby tokenu).
