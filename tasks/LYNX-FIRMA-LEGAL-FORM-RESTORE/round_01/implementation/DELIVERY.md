# LYNX-FIRMA-LEGAL-FORM-RESTORE — DELIVERY round_01 (CC)

Gałąź `task/LYNX-FIRMA-LEGAL-FORM-RESTORE`, zsynchronizowana z `main` (merge `9393fa5`). Gate base: `1084b6978f0ed486f0cc390ed72d6b6e761b07ef`. Implementacja: `ba0560386ed84106ebbcdd4d363cc5c941a4b9f1`.
Pliki (TASK_SCOPE): `backend/layers/ner_adapter.py` (+2/−7), `backend/tests/test_layers.py` (+16, 583 l.). Artefakt: `round_01/implementation/form_sweep.py`. Rozszerzenia CC: brak.

## Ocena briefu
Zgodny z kodem; przyjęty. `where.py`: `_FIRMA_CLEANUP_RE` w `ner_adapter.py` używany tylko w końcowym `sub` w `apply_ner_layer`.
Drugi identyczny wzorzec stoi w `backend/pipeline.py:207/535`, ale w starej ścieżce `_run_pipeline` za `if USE_NEW_PIPELINE:` (`USE_NEW_PIPELINE = True`). W produkcji jest nieosiągalny, poza zakresem, opisany w findingu.

## Zmiana
Usunięte stratne `state.text = _FIRMA_CLEANUP_RE.sub(r"\1", state.text)` i nieużywany już wzorzec. Forma prawna stojąca za tokenem („FIRMA_001 Sp.k.”) zostaje w tekście. Pełna encja z formą nadal daje jeden FIRMA z pełną wartością w mapie. NER, Guard, Express, format tokenów i przydział ID są bez zmian.

## Dowody
1. **Reproduktor Codexa** (`tasks/LYNX-FIRMA-HYPHEN-SUFFIX/round_01/tests/tests_r2_repro.py`, uruchomiony bez asercji SHA; prawdziwy NER, Full, Guard):
   - repeat-form-0: baza `restoration_exact false, legal_form_restored 0` → po **`true, 1`**;
   - repeat-form-1: `true` → `true`;
   - 3 kontrole: PASS.
   - **repeat-form-2: nadal niedokładne, inna przyczyna** (opis niżej). Klasyfikuję osobno, bez zmiany zakresu.
2. **`form_sweep.py`** (prawdziwy NER, Full; 8 nazw × 4 formy × 4 układy {bez→z, z→bez, z→z, bez→bez} + 6 kontrprób = 134). Baza to `main` w worktree.

   | | utrata formy | Przywróć dokładny | inne niedokładne | blokady | zagnieżdżone tokeny |
   |---|---|---|---|---|---|
   | baza | 14 | 116 | 4 | 0 | 0 |
   | po | **0** | 130 | 4 | 0 | 0 |

   - **Regresje 0** (dokładność, widoczność nazwy, zagnieżdżenia, blokady — porównanie przypadek po przypadku).
   - 4 „inne niedokładne” to klasa repeat-form-2, identyczna na bazie i po.
   - Kontrpróby bez zmian: sama forma bez nazwy, „Spółka” po tokenie, dwie firmy, nagłówek WERSALIKAMI, tekst bez firmy, podwójna forma.
3. **Testy** `test_layers.py`: 121 passed. Nowy test: 4 formy × 2 kolejności, prawdziwy NER, brak blokady, nazwa niejawna, Przywróć 1:1. Bez poprawki 3 failed (kolejność „bez formy → z formą”); układ „z → z” przechodzi w obu wersjach (kontrola).
4. **Pozostałe sprawdzenia:**
   - standardowa suita: 129 passed / 40 skipped / 1 xfailed;
   - **z backendem**: 167 passed / 2 skipped / 1 xfailed, 0 failed;
   - `test_audyt_2026_10.py`: 131 passed / 10 xfailed;
   - `firma_sweep.py` (160): wynik bez zmian (masked 96, regresje 0, Przywróć 0 błędów);
   - ruff: czysto.

## gate.py (stdout dosłownie)
```
STATUS: PASS
HEAD_SHA: ba0560386ed84106ebbcdd4d363cc5c941a4b9f1
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
```
(IMPORTERS_FOR_REVIEW i EXCLUDED_ARTIFACTS w `gate.txt`.)

## Repeat-form-2 — inna przyczyna (nie naprawiane, owner poza zakresem)
Układ: „Eko-Tech Consulting” bez formy, potem „Eko-Tech Consulting S.A.”. W `ner_layer._process_ner` oba warianty mają ten sam `_ner_stem`, więc gołe wystąpienie staje się wariantem tokenu, którego wartość w mapie to „… S.A”. Przywróć **dopisuje** wtedy formę do wystąpienia, które jej nie miało. Owner: `ner_layer.py` (OUT_OF_SCOPE). Finding niżej.

## FINDING — PILNE: LYNX-FIRMA-BARE-REPEAT (regresja prywatności z FIRMA-HYPHEN-SUFFIX)
`form_sweep` na trzech wersjach kodu (przed FIRMA-HYPHEN-SUFFIX `5ae6f8d` / `main` / ten Task), układ „najpierw z formą, potem goła nazwa”:
- nazwa jawna w wyniku: przed 26/32 → `main` **32/32**;
- per przypadek: **6 regresji** (gołe drugie wystąpienie wcześniej zamaskowane, teraz jawne) i 10 poprawek w innych układach;
- łącznie przypadki z jawną nazwą: 36 → 32.

Przyczyna: od FIRMA-HYPHEN-SUFFIX wartość encji obejmuje formę („X Sp.k”), więc podmiana w tekście nie trafia w późniejsze gołe „X”, a SpaCy drugiego wystąpienia nie wykrywa. Wcześniej encja „X” bez formy łapała oba wystąpienia, a stratny cleanup kasował formę.
Mój przegląd z FIRMA-HYPHEN-SUFFIX nie obejmował powtórzeń tej samej firmy, a audyt też tego nie wychwycił.
**Propozycja CC** (owner `ner_layer.py`): dla FIRMA rozszerzonej o formę zarejestrować także rdzeń bez formy **jako osobny token** (FIRMA_002 = „X”), a nie wariant tokenu z formą. To zgodne z uwagą Pawła, że „X” i „X Sp.k.” to prawnie potencjalnie różne podmioty. Załatwia naraz wyciek (gołe „X” zamaskowane) i repeat-form-2 (Przywróć bez dopisywania formy). Kryterium: `form_sweep` — jawna nazwa 0 w układach, gdzie SpaCy wykrył firmę, Przywróć 1:1, 0 regresji vs `5ae6f8d` i `main`.

Drobny finding: martwa kopia stratnego cleanupu w `backend/pipeline.py` (stara ścieżka) — usunąć przy okazji sprzątania legacy.
