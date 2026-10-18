# LYNX-EXPRESS-ONE-ENGINE — DELIVERY r1 (CC)

Kod: `ec2b892` na brief `cffd0ab` (Codex PASS PREIMPLEMENTATION `025b1fb`), gałąź zsynchronizowana z main (`b7108ce`).

## Zmiany
- **Backend.**
  - `pseudominizer_api.py` (−90/+4): usunięty `POST /preview-express`; `_EXPRESS_PATHS = {("POST", "/preview")}`; docstring `/express/token` i wpis historii v1.33 opisują usunięcie.
  - `pipeline_new.py` (−46/+2): usunięta `run_pipeline_express`, docstring poprawiony.
  - Plik API 1146 → 1060 linii.
- **Frontend.**
  - `ExpressModeScreen.tsx` usunięty (621 linii, nigdzie nieimportowany — `git grep` na `b7108ce`).
  - `MainLayout.tsx`: `expressMode` przekazywany do `Pseudonimizuj`; baner „⚡ Tryb Express — bez logowania” zamiast „Tryb demonstracyjny”. Dopisek „Biblioteka i odmaskowanie dostępne po zalogowaniu.” był już wcześniej.
  - `Pseudonimizuj.tsx`: przy `expressMode` ukryte są bloki „dodaj do profilu biura” i „Zapisz do biblioteki” oraz przycisk „To nie PII”. W panelu blokady Guarda zamiast instrukcji profilu jest tekst „Dodanie wartości do profilu biura i „to nie PII” są dostępne po zalogowaniu.” Ostrzeżenie, blokada i wyłączone „Kopiuj” bez zmian.
  - `LockScreen.tsx`: komentarz.
- **Testy** (Express = `/preview` z tokenem Express):
  - `test_failclosed.py`: awaria warstwy, token po OCR, zwykła korekta OCR i wyjątek endpointu na prawdziwym serwerze dla tokenu Express — wszystko na `/preview`;
  - `test_text_limit_15k.py`: 3 parametryzacje `/preview-express` → `/preview` + token Express;
  - `test_layers.py`, `test_map_fidelity.py`, `test_pipeline_adversarial.py`, `test_audyt_2026_10.py`: warianty `run_pipeline_express` usunięte, wariant pełny zostaje. Testy regex-only z `test_map_fidelity` używają `run_pipeline_new` z wyłączonym NER;
  - `test_ner_multiline.py`: test „Express bez NER” usunięty;
  - `test_audyt_2026_10.py::test_express_fail_closed` usunięty z komentarzem, gdzie ten przypadek jest teraz pokryty;
  - `audyt/rota_leak_test.py`: tryb `express` usunięty.
- **Nowy `tests/test_express_one_engine.py`** (6 testów, TestClient z prawdziwym silnikiem):
  - `/preview-express` z pełnym tokenem → 404, a `run_pipeline_express` nie istnieje;
  - ten sam dokument przez `/preview` z tokenem Express i pełnym daje identyczny wynik i tokeny; osoba (NER) i PESEL zakryte, brak blokady;
  - token Express na `POST /archive`, `POST /profile/add-entity`, `POST /profile/guard-allowlist`, `GET /archive` → 401.
- **ROZSZERZENIE CC** (w briefie): trzy pliki testów spoza pierwotnej listy (`test_ner_multiline`, `test_pipeline_adversarial`, `test_text_limit_15k`) dopisane do TASK_SCOPE — znalezione przez `git grep`, ta sama klasa.

## Dowody
- **RED:** `test_express_one_engine.py` na kodzie API/pipeline z main daje **1 failed** (`assert 200 == 404`: stary endpoint odpowiadał).
- **GREEN:** jawne pliki `test_express_one_engine`, `test_failclosed`, `test_layers`, `test_map_fidelity`, `test_ner_multiline`, `test_text_limit_15k`, `test_audyt_2026_10`, `test_startup_check`: **343 passed, 7 xfailed**.
- **Backend z gałęzi** (`wt_board`, port 8765, profil Pawła), `tests/`: **167 passed, 2 skipped, 1 xfailed** (subtesty IBAN 8 → 4, bo jest jeden pipeline zamiast dwóch). `tsc --noEmit`: 0 błędów.
- **Pomiar 178 dok. `dataset_real_public` przez działający `/preview`:**

  | Porównanie | Wynik |
  |---|---|
  | token Express vs pełny na gałęzi | **0 różnic** (wynik, tokeny, blokady, kody) |
  | pełny na gałęzi vs pełny na main `63f2658` (pomiar sprzed zmiany) | **0 różnic** |
  | tokeny OSOBA | 811 (jak na main) |
  | blokady | 59 (jak na main) |
  | `POST /preview-express` z pełnym tokenem | **404** |

- UI: NOT_RUN, do oceny okiem Pawła po `npm run tauri build`. W Express: nowy baner; brak przycisków profilu, biblioteki i „to nie PII”.

## Uwagi
- `layers/fallback.apply_fallback_layer(state, full=False)` — gałąź `full=False` używana była tylko przez usuniętą funkcję. Warstwa jest poza zakresem i została bez zmian (martwy parametr, do sprzątnięcia osobno).
- `audyt/logs/pytest_audyt_xfail.txt` to historyczny zapis z 16.10 z nazwą usuniętego testu. Archiwum, nie zmieniano.

## Gate (dosłownie, bez list)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: ec2b89292983b4f363abcdb05f2725823783df80
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 990 lines changed (threshold 150)
```
Dodanych 145, usuniętych 845 (netto −700). Paweł zaakceptował rozmiar przed kodem („Akceptuję rozmiar”) przy szacunku ok. 110 dodanych i ok. 800 usuniętych. Dodanych wyszło o 35 więcej, głównie przez przeniesienie testów z trzech plików spoza pierwotnej listy.
