# DELIVERY — LYNX-FIRMA-SILENT2 (round 01)

Brief `ad35f6c` (Codex BRIEF_ONLY r1 PASS `4b1bac7`), baza `f617ef6fecf9c1c409afb2bf19c9a579d12a2e33`, kod `281b7d9c3aa87d9aa244e205db68a79ac39d6503`.
CC nie wystawia PASS/FAIL — ocena: gate + Codex.

## gate.py (stdout dosłownie, pierwsze linie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 281b7d9c3aa87d9aa244e205db68a79ac39d6503
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 127/5 = 25.4:1 (threshold 5:1)
```
RATIO: zmiana głównie dodaje (nowe reguły + testy). Rozmiary: `firma_context.py` 153 → 201, `ner_layer.py` 597 → 597 (tylko zmiana istniejących linii).

## Zmiany
- **A — JDG** (`firma_context.jdg_entities`, `is_jdg`): rzeczownik działalności z zamkniętej listy briefu + słowa z wielkiej litery w tej samej
  linii + ostatnia para imię (lista imion) + nazwisko → jedna FIRMA dla każdego wystąpienia (ten sam token). Wpięte w `_firma_entities`
  (zmiana istniejącej linii). Dodatkowo (konieczne dla A): istniejący filtr działów wewnętrznych `_INTERNAL_ORG_RE` („Biuro …”) w
  `_filter_institutions` odrzucał nazwę JDG zaczynającą się od „Biuro” — wyjątek `not is_jdg(...)` w tej samej linii.
  Działy bez osoby („Biuro Obsługi Klienta”, „Dział Kadr”) — nadal odrzucane.
- **B — s.c.** (`_FORM_SCAN_RE` + warunek w `scan_legal_forms`): „s.c.” po nazwie; wyraz tuż przed formą musi mieć ≥2 litery („J. S.C.” — nie firma).
  Powtórzenie bez formy — istniejące `firma_core_variants`.
- **C — rozcięte powtórzenie** (`firma_context._absorb_inside_core`, wołane z `firma_core_variants`): encja, której każde wystąpienie leży
  wewnątrz wystąpień rdzenia firmy („Ulotny” w „Ulotny Rys”), przechodzi na token rdzenia (jak dotychczas OSOBA równa rdzeniowi).
  Owner: `firma_context` (rdzenie); `layers/ner_adapter.py` bez zmian.

## Testy (cwd = backend, `.venv`)
- `tests/test_firma_silent2.py` (nowy): 10 passed — A (2, w tym nagłówek WYKONAWCA + „Biuro …”), B, C przez pełny `pseudonymize_document`
  (wartość w mapie + ten sam token przy powtórzeniu), negatywy (dział bez osoby ×2, „Biuro Rzecznika Praw Pacjenta”, mała litera, inicjały
  przed „S.C.”), `is_jdg`/`jdg_entities` bez imienia.
- Regresja: test_firma_context 14, test_silent_pack1 30, test_formats_pack2 20, test_map_fidelity 29, test_osoba_layout 49, test_ner_multiline 21,
  test_osoba_pack4 12, test_osoba_not_person 25, test_pipeline_v2 41, test_addr_email_leaks 22, test_amount_ocr_mult 24;
  test_layers 2 failed/119 i test_audyt_2026_10 1 failed/122/2 xfailed — jak main.

## Pomiar (main `f617ef6` → gałąź)
| zbiór | miara | main | gałąź |
|---|---|---|---|
| GOLD dev (40) | ciche wycieki (wszystkie typy) | 20 | **0** |
| GOLD test (80, tylko agregat) | ciche wycieki | 52 | **1** (FIRMA nierodo) |
| GOLD dev / test | FIRMA zakryte rodo / nierodo | 56·69 / 104·136 | **80·80 / 160·158** |
| GOLD dev / test | pytania Guarda na dok. | 0,90 / 0,86 | **0,53 / 0,53** |
| GOLD dev / test | zbędne zakrycia (not_pii) | 69/440 / 152/880 | 69/440 / 152/880 |
| `testset_owner` | wszystkie zbiory | — | identycznie z main |
Klasy zaprojektowane na GOLD dev (20/20); GOLD test nieoglądany — spadek 52 → 1 to wynik na danych spoza projektowania
(ten sam generator szablonów GOLD, więc nie dowód dla dowolnych pism). Opinia Qwena (pkt 4: filtr przed regułami) potwierdzona przy A.

---

# Runda 2 — po Codex r2 FAIL (`d32fcd6`, `tests_r2.txt`)
Kod r2: `b9315c5890d5838eab38ad9afbc8f0af8f8d0e71` (diff od `281b7d9`: commit `b9315c5`).

## gate.py (stdout dosłownie, pierwsze linie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: b9315c5890d5838eab38ad9afbc8f0af8f8d0e71
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 133/5 = 26.6:1 (threshold 5:1)
```
RATIO 133/5: zmiana prawie wyłącznie dodaje (reguły + testy). Uwaga Codexa r2 słuszna — zgoda Pawła na miarkę linii dotyczyła kwot;
dla tego Tasku pytanie o RATIO przekazane Pawłowi osobno (CC nie traktuje wcześniejszej zgody jako ogólnej).

## F1 (P2) — nazwisko będące też imieniem wyłączało JDG
- Przyczyna: `jdg_entities` wymagał, by ostatni wyraz NIE był na liście imion („Cezary Marek”, „Anna Roman”, „Jan Marek” — odrzucone).
- Poprawka: ostatnia para = imię (lista imion) + następny wyraz z wielkiej litery, bez warunku „nie-imię” dla nazwiska.
- Retained `repro_r2.py` na `b9315c5890d5838eab38ad9afbc8f0af8f8d0e71`: 6/6 zgodne (A_control, A_surname_firstname, A_surname_firstname2, A_short_jdg → jedna FIRMA, wspólny
  token w obu wzmiankach; B, C bez zmian).
- Testy: `test_firma_silent2` 13 passed (+3 przypadki F1); regresja: test_firma_context 14, test_silent_pack1 30, test_formats_pack2 20,
  test_map_fidelity 29, test_osoba_layout 49, test_ner_multiline 21, test_osoba_pack4 12, test_pipeline_v2 41.
- Pomiar r2: GOLD ciche dev 0 / test 1, zbędne 69/152, pytania 0,53/0,53 (= r1); `testset_owner` identycznie z main.

## Zgoda na RATIO
Paweł 23.10, na pytanie CC o RATIO 133/5 dla LYNX-FIRMA-SILENT2: „Tak” (akceptacja przekroczenia miarki dla tego Tasku).
