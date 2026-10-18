# LYNX-TOKEN-RE-SPEC — rozpoznawanie tokenu zgodne z zamrożonym S2; drobne zaległości audytu (batch, seed)

STATUS: brief CC, obieg skrócony (CC → Codex precheck → CC implementacja → Codex audyt → merge na słowo Pawła). Polecenie Pawła: „rób małe zadanie” (po szacunku CC ok. 30 linii programu i 40 linii testów).
POCHODZENIE: znane błędy z audytu 2026-10 zapisane jako `xfail(strict)` w `backend/tests/test_audyt_2026_10.py`: BUG-TOKEN-RE-SPEC, BUG-ONBOARD-BATCH, BUG-SEED-DEAD. Diagnoza 18.10 (M1): seedu nie przywracać.
PRODUCT_TRUTH: `arch/spec.md` S2 („`TOKEN_RE` używa `(?!\d)`, NIE `\b`”), S3 („wejście zawierające ciąg pasujący do `TOKEN_RE` = 422”). **Specyfikacji i formatu tokenu nie zmieniamy.** Kod dostosowujemy do istniejącej specyfikacji. Wzorzec Mobile: `\b(FIRMA|OSOBA|NUMER|EMAIL|KWOTA|ADRES)_(\d{3})(?!\d)`.

## Stan (main `845d354`)
**A. Wzorzec tokenu (BUG-TOKEN-RE-SPEC).**
- Koniec wzorca to `\b`, więc token przyklejony do litery („OSOBA_001x”, „NUMER_004Teresa”) nie jest rozpoznawany.
- Kopii wzorca jest 9, a część jest niespójna:

  | Plik | Wzorzec / uwagi |
  |---|---|
  | `anonymizer_init.py` | `TOKEN_RE`, `TOKEN_SPAN_RE` |
  | `pseudominizer_api.py` | kontrola wejścia 422 |
  | `pipeline.py` | — |
  | `ner_layer.py` | — |
  | `layers/ner_adapter.py` | **bez INSTYTUCJA** |
  | `output_guard.py` | — |
  | `verbal_amounts.py` | — |
  | `frontend/src/screens/Pseudonimizuj.tsx` | podświetlanie, `[A-Z][A-Z_]+_\d{3}\b` |

- Skutek realny (korekta CC wobec wcześniejszej wypowiedzi): Przywróć w aplikacji (`Depseudonimizuj.restoreText`) podmienia klucze mapy wprost, więc przyklejony token **jest** przywracany.
- Problem leży gdzie indziej:
  - **kontrola wejścia (S3, 422) nie wykrywa przyklejonego podrobionego tokenu** w dokumencie, np. „OSOBA_001x”. Dokument przechodzi, a po Przywróć ten fragment zamienia się w wartość z mapy (token injection);
  - warstwy pomijające gotowe tokeny nie widzą przyklejonego tokenu.

**B. BUG-ONBOARD-BATCH.** `anonymizer.py` używa `MAX_ONBOARD_BATCH` bez importu (zdefiniowana w `anonymizer_init.py`), więc `add_entities_batch` i `onboard_entities_batch` zgłaszają `NameError`. Dziś nie dotyka użytkownika: wołają je tylko martwy seed, `dict_auto_builder` i nieużywane `anonymize_with_ner`. Import `.lynxdict` dodaje encje pojedynczo.

**C. BUG-SEED-DEAD.** `_lifespan` woła `seed_profile.seed_if_needed` na profilu użytkownika. Seed nigdy nie działał (`NameError`). Po naprawie B zacząłby działać częściowo (limit 100 < 12 tys. wpisów) i zaśmiecałby profil biura formami pospolitymi — diagnoza M1. Nazwiska ma pokryć słownik w nowym modelu (`LYNX-ARCH-CANDIDATES`), a nie profil biura.

## Kontrakt
1. Każda kopia wzorca tokenu w backendzie i w `Pseudonimizuj.tsx` kończy się `(?!\d)` zamiast `\b` i obejmuje pełną taksonomię Desktop (FIRMA, OSOBA, NUMER, KWOTA, ADRES, INSTYTUCJA, EMAIL). Początek `\b` bez zmian, jak w Mobile. Struktura grup każdej kopii bez zmian (`findall`/`sub` w `anonymizer.py` zależą od grup).
2. Kontrola wejścia `/preview` (pełny token i Express): „OSOBA_001x”, „NUMER_004Teresa” → 422, tak samo jak „OSOBA_001”. Normalny tekst bez tokenów → 200 bez zmian.
3. `anonymizer.py` importuje `MAX_ONBOARD_BATCH` z `anonymizer_init`, a `add_entities_batch` działa w limicie.
4. `_lifespan` nie woła seedu. Moduł `seed_profile.py` zostaje dla skryptów pomiarowych (`audyt/`) z nagłówkiem „nieużywany przez produkt — LYNX-TOKEN-RE-SPEC”. Reproduktor BUG-SEED-DEAD usunięty z `test_audyt_2026_10.py` z komentarzem o świadomym wyłączeniu (diagnoza M1).
5. Markery `xfail` BUG-TOKEN-RE-SPEC i BUG-ONBOARD-BATCH zdjęte, a testy przechodzą.
6. Wynik maskowania bez zmian dla dokumentów bez przyklejonych tokenów.

TASK_SCOPE:
- backend/anonymizer_init.py
- backend/anonymizer.py
- backend/pseudominizer_api.py
- backend/pipeline.py
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/output_guard.py
- backend/verbal_amounts.py
- backend/seed_profile.py
- frontend/src/screens/Pseudonimizuj.tsx
- backend/tests/test_audyt_2026_10.py
- backend/tests/test_token_re_spec.py

OUT_OF_SCOPE: zmiana S2/formatu tokenu/taksonomii, `pseudominizer.html` (stary frontend HTML), Mobile, `restoreText` (działa), `dict_auto_builder`, przywracanie seedu.

## Falsyfikacja
- Nowy `tests/test_token_re_spec.py`:
  - wszystkie kopie wzorca (importowane z modułów) dają ten sam wynik na zestawie: „OSOBA_001”, „OSOBA_001x”, „NUMER_004Teresa”, „INSTYTUCJA_002”, „EMAIL_003.”, „OSOBA_0012” (brak dopasowania), „xOSOBA_001” (brak — `\b` na początku), „FIRMA_01” (brak);
  - `/preview` z przyklejonym tokenem daje 422 dla tokenu pełnego i Express;
  - `add_entities_batch` z 2 encjami działa na izolowanym profilu.
- RED na main: przyklejony token → 200 (nie 422); niespójność kopii (ner_adapter bez INSTYTUCJA); `NameError` w batch.
- Regresje: `tests/` na backendzie gałęzi, `test_audyt_2026_10`, `test_failclosed`, `test_startup_check`, `test_disk_pii`, `test_layers`. 178 dok. przez `/preview` z profilem Pawła → 0 różnic względem main. `tsc --noEmit`.

GATE: 1 nowy plik testu; zmiany jednoliniowe w legacy (bez wzrostu). Szacunek: program ok. +15/−10, testy ok. +50.
