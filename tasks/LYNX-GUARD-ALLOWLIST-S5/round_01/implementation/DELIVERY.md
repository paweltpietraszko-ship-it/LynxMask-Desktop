# DELIVERY — LYNX-GUARD-ALLOWLIST-S5 (round_01)

22.10.2026, CC. Brief `tasks/LYNX-GUARD-ALLOWLIST-S5/brief.md` (Architekt `5c40789`, Codex BRIEF_ONLY r1 PASS `30272e4`, uzupełnienie CC `287d3c8`).
Baza: `main` `35b3ad1ccf8ca3ae6f46c106767cad4e2252152a`. Implementacja: `a7c31d93ed5eedcfd2772d2cbb1131778a92c8de`.

## Zmiany (numstat względem bazy)
| plik | + | − | co |
|---|---|---|---|
| `backend/guard_allowlist.py` | 161 | 0 | nowy: `guard_allowlist.enc` (AES-256-GCM, `get_or_create_keys` profilu anonimizatora), pary (fragment, reguła), `*` = stary wpis, RED odrzucany, limit 500, migracja jawnego JSON (usunięcie po udanym zapisie), uszkodzony plik: `state()` = ([], True), `add/remove` → 409 bez nadpisania, `clear()` tylko lista; `silenced()` — RED nigdy |
| `backend/guard_residue.py` | 6 | 16 | `load_allowlist` = `guard_allowlist.load`; `collect_warnings` wycisza przez `silenced(fragment, rule)` (stare wywołania z `list[str]` = wpisy `*`) |
| `backend/pipeline.py` | 0 | 1 | `guard_output_with_map` bez `allowlist` — MAP_LEAK zawsze pyta |
| `backend/pseudominizer_api.py` | 34 | 49 | GET (`entries` + `damaged`), POST add `{value, rules}`, POST `/remove` `{value, rule}`, POST `/clear`; DELETE z frazą w URL usunięty; reset usuwa `guard_allowlist.paths()`. Plik 1055 → 1040 l. |
| `backend/tests/test_guard_allowlist_s5.py` | 125 | 0 | nowy, 13 testów |
| `frontend/src/screens/GuardPanel.tsx` | 62 | 10 | „Zawsze jawne” + „?” tylko żółte i poza Express; „Zawsze jawne — cofnij” usuwa wszystkie pary; błąd → pozycja bez decyzji + komunikat; helpery API (`listAllow/addAllow/removeAllow/clearAllow`, `ruleLabel`, `rulesOf`) tu, nie w osobnym pliku (gate: max 2 nowe pliki) |
| `frontend/src/screens/Pseudonimizuj.tsx` | 1 | 1 | ta sama linia `<GuardPanel …>` + `allowToken` (914 l. bez zmian) |
| `frontend/src/screens/SecurityScreen.tsx` | 34 | 38 | „Wyjątki Guard”: nowe teksty (zrzut Pawła), wartość + rodzaj reguły, usuwanie przez `/remove`, przy `damaged` „Wyczyść uszkodzoną listę wyjątków” z potwierdzeniem (2 kliknięcia) → `/clear`; reset: „wyjątki Guarda („Zawsze jawne”)”. 790 → 786 l. |

`frontend/src/screens/guardAllowlist.ts` z TASK_SCOPE nie powstał (helpery w `GuardPanel.tsx`).

## Gate (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: a7c31d93ed5eedcfd2772d2cbb1131778a92c8de
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 538 lines changed (threshold 150)
```
Rozmiar: 423 dodane / 115 usunięte. Szacunek briefu ~250 był zaniżony (moduł 161 zamiast ~90, testy 125, panel 62). **Zgoda OWNERA na 538 — CC pyta Pawła.** Ruff: `pseudominizer_api.py` 6 → 5 błędów (wszystkie stare), nowe pliki czyste.

## Testy (`.venv`, cwd = `backend/` worktree, plik po pliku)
- `tests/test_guard_allowlist_s5.py`: **13 passed** — szyfrowanie (bajty bez wartości, także UTF-16), migracja (`*` wycisza R1, nie MAP_LEAK), RED/`*`/puste odrzucone ×5, limit, para fragment+reguła, wiele reguł + cofnij, uszkodzony plik (409, plik nietknięty, `clear`), pipeline: `guard_output_with_map` wywołany bez `allowlist`, API (brak DELETE, add/RED 400/list/remove/damaged/409/clear).
- Regresja: `test_guard_residue` 54 passed (stary test `allowlist=["kawa"]` bez zmian), `test_output_guard_adversarial` 31 passed, `test_map_fidelity` 29 passed, `test_silent_pack1` 30 passed, `test_layers` 2 failed / 119 (znane), `test_audyt_2026_10` 1 failed / 122 / 2 xfailed (znane).
- Okno: `tsc --noEmit` exit 0; `vite build` OK.

## Żywy silnik (gałąź na profilu Pawła, potem przywrócony main)
Skrypt `round_01/implementation/probe_s5.py <api_token.txt>` (tekst syntetyczny „Świadek Śludkowskiego nie stawił się…”):
```
przed: [('Śludkowskiego', ['R1'], 'YELLOW')]
add: (200, {'ok': True, 'total': 1})
add RED: (400, ... „Czerwonych ostrzeżeń nie można zapamiętać jako „Zawsze jawne”.”)
po Zawsze jawne: []
DELETE stary: 404
po cofnij: [('Śludkowskiego', ['R1'], 'YELLOW')]
clear → lista: {'entries': [], 'damaged': False}
```
Po próbie w profilu Pawła brak `guard_allowlist.enc` (tylko `mapa.enc`, keystore). Słownik biura i `/profile/import-dict` (.lynxdict z Mobile) nietknięte.

## Znane ograniczenia (do oceny)
- Wpis dotyczy dokładnie fragmentu; odmiany (R1 „Kowalczyka”/„Kowalczyk”) = osobne pytania (poza zakresem w briefie).
- Pozycja panelu łącząca nakładające się trafienia: zapisywany jest scalony fragment; trafienie o innym zakresie niż scalony fragment nie zostanie wyciszone (więcej pytań, nie wyciek).
- Ochrona dostępu (DPAPI = konto Windows) — osobne `LYNX-DICT-ACCESS-PROTECTION` (Codex r1).

## Odtworzenie (Codex)
```
git worktree add <wt> a7c31d93ed5eedcfd2772d2cbb1131778a92c8de
cd <wt>/backend && <repo>/.venv/Scripts/python.exe -m pytest tests/test_guard_allowlist_s5.py -q -p no:cacheprovider --rootdir .
cd <wt>/frontend && (node_modules z <repo>/frontend) node node_modules/typescript/bin/tsc --noEmit -p .
```
