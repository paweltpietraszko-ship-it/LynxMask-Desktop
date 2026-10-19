# LYNX-ADDR-EMAIL-LEAKS — DELIVERY r1 (CC)

Kod: `6ee688a` na brief `19b7259` (Codex PASS PREIMPLEMENTATION `7931a21`), gałąź zsynchronizowana z main (`8e499cc`).

## Zmiany (program +9/−6)
- `layers/address.py` — faza 1 `_ADDR_RE`, po prefiksie ulicy:
  - opcjonalnie `\d{1,2}` + spacja (L3: „3 Maja”, „11 Listopada”);
  - opcjonalnie jeden skrót `[litera]{1–4}.` + spacja (L2: „Św.”, „Gen.”, „Ks.”, „Z.”);
  - numer domu z opcjonalną literą OCR `[lIO]` przed cyfrą, także po `/` (L1: „l2/8”, „O5”, „12/l4”).

  Pozostałe fazy bez zmian.
- E-mail (L4, L5): część lokalna `[\ẁ-ͯ.%+\-]` (litery Unicode i znaki łączące NFD) z lewą granicą `(?<![\ẁ-ͯ.%+\-])`. Dzięki temu cała część lokalna trafia do tokenu i nie ma sklejenia. Zmienione w trzech wzorcach:
  - `layers/contact._EMAIL_OCR_RE` (także opcjonalny prefiks OCR „anna. ”);
  - dwa wzorce EMAIL w `anonymizer_init.STRUCTURAL_PATTERNS`.

  Domena bez zmian (ASCII).

## Testy
- **Nowy `tests/test_addr_email_leaks.py` (22 testy):**
  - L1–L5 i 6 wariantów rodziny („ul. Gen. Andersa 4a/12”, „al. 11 Listopada 7”, „ul. Polna O5”, „ul. Polna 12/l4”, „łukasz.żak@…”, „Ąnna@…”): wartość w całości w jednym tokenie, bez sklejenia, Przywróć = wejście;
  - 5 kontrprób bez PII bez zmian: „ul. w instrukcji”, „@administrator”, „@jan_kowalski”, „pl. zabaw”, „Al. 5 razy pytał.”;
  - „Dz. U. Nr 223” (C5) bez pogorszenia;
  - L1–L5 przez `/preview` z pełnym silnikiem: żaden człon wartości nie jest jawny.
- **RED** na kodzie z main: **16 failed / 6 passed** (passed = kontrpróby i C5). **GREEN: 22 passed.**
- Backend gałęzi (port 8765, profil Pawła):

  | Zestaw | Wynik |
  |---|---|
  | `tests/` | **167 passed, 2 skipped, 1 xfailed** |
  | `test_addr_email_leaks`, `test_layers`, `test_map_fidelity`, `test_audyt_2026_10`, `test_failclosed`, `test_token_re_spec`, `test_ner_multiline`, `test_startup_check` | **373 passed, 3 xfailed** |
  | `ruff` | bez nowych uwag |

- **178 dok. `dataset_real_public` przez `/preview` (profil Pawła), gałąź vs main:**
  - **16 dokumentów z różnicą — wszystkie to poprawy** (przegląd lokalny CC);
  - 16 nowych wartości ADRES w mapie:
    - adresy wcześniej całe jawne: „ul. 1 Maja …” ×5, „ul. Św. …”;
    - adresy wcześniej częściowo jawne: zostawał prefiks z inicjałem, skrótem lub liczbą, np. „ul. Z.”, „ul. Gen.”, „ul. 3”, „ul. 17”, „ul. W.”, „ul. J.”; teraz zakryte w całości;
  - 9 wartości „zniknęło”, bo zostały zastąpione dłuższymi, pełnymi;
  - **0 wartości zakrytych na main, a jawnych na gałęzi;**
  - blokady 59 → 59;
  - dwie nowe wartości zaczynają się od „ul. ul.” — w źródle jest dosłowny dubel „ul. ul.” (2 wystąpienia), więc zakrywany jest cały zapis.

  Dane dokumentów zostają lokalnie, tu są tylko liczby.

## Gate (dosłownie, bez list)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 6ee688ab57267f986ae6ca5580538e9b872d5173
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 102/6 = 17.0:1 (threshold 5:1)
```
RATIO wynika z nowego pliku testu (93 linie). Program to +9/−6, TOTAL 108 jest poniżej progu 150. Do potwierdzenia przez Pawła.

## Poza zakresem (bez zmian)
- normalizacja OCR wokół „@” (X02, klasa SHADOW-NORMALIZE);
- C5 „Dz. U.” — wartość w mapie to „ul. Nr 223” po normalizacji, a nie dosłowny zapis; znane, K3.
