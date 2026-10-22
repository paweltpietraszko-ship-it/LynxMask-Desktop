# LYNX-GUARD-ALLOWLIST-S5 — „Zawsze jawne”: trwały wyjątek Guarda w zaszyfrowanym magazynie

22.10.2026, CC. Wiersz BOARD „CC (brief), potem Codex”. Zgodne z `arch/spec.md` S4 („trwałe zapamiętywanie = wyraźny wybór użytkownika, ochrona zgodna z S5; nie poszerzać jawnego `guard_allowlist.json`”); bez zmiany spec.
Wzór obsługi: LynxMask Mobile `GuardAllowlist.kt` (EncryptedFile AES-256-GCM, klucz = para (wartość, typ reguły), limit 500, migracja jawnego pliku).

## Stan na main (`35b3ad1`)
- `pseudominizer_api.py` `_load/_save_guard_allowlist`: **jawny** `guard_allowlist.json` (lista napisów) w `PROFILE_DIR` albo `~/.pseudominizer/profile`; endpointy GET/POST/DELETE `/profile/guard-allowlist[/{phrase}]` — DELETE niesie frazę w URL (trafia do logu dostępu uvicorn).
- `guard_residue.load_allowlist()` czyta ten plik; `collect_warnings` wycisza fragment niezależnie od reguły — także RED (HIGH, MAP_LEAK).
- `pipeline._apply_guard` przekazuje allowlistę także do `guard_output_with_map` → wycisza MAP_LEAK (wartość zakrytą gdzie indziej).
- Okno nie zapisuje do allowlisty (Guard B); Ustawienia → „Wyjątki Guard” pokazują i usuwają wpisy.
- Na komputerze Pawła pliku nie ma (0 wpisów); migracja dotyczy innych instalacji.

## Zachowanie produktu (wybory Pawła 22.10 na propozycje CC)
1. Przy **żółtej** pozycji panelu Guarda trzeci przycisk **„Zawsze jawne”** z „?”, obok „Maskuj” i „Zostaw jawne”. Kliknięcie = pozycja zostaje jawna w tym dokumencie (jak Zostaw) i wpis trafia do zaszyfrowanej listy; w kolejnych dokumentach Guard o ten fragment z tą regułą nie pyta. Po kliknięciu: „Zawsze jawne — cofnij” (usuwa wpis, pozycja wraca do decyzji).
2. **Czerwone** pozycje (HIGH, MAP_LEAK) — bez „Zawsze jawne”; lista ich nie wycisza nigdy (także stare wpisy i `guard_output_with_map`).
3. Tryb Express (bez profilu) — bez przycisku.
4. Tekst „?”: „Program nie będzie pytał o ten fragment w następnych dokumentach. Lista jest zaszyfrowana na tym komputerze; wpis usuniesz w Ustawieniach → Wyjątki Guard.”

## Zakres techniczny
### Backend — nowy moduł `backend/guard_allowlist.py` (logika poza dużymi plikami)
- Plik `guard_allowlist.enc` w katalogu profilu anonimizatora (`ANONYMIZER_PROFILE_DIR`, domyślnie `backend/anon_profiles/pseudominizer` — tam gdzie keystore), szyfrowany `anonymizer_crypto.encrypt_map` kluczem `get_or_create_keys` (AES-256-GCM, DPAPI na Windows). Treść: `{"v": 1, "entries": [{"value", "rule"}]}`; zapis atomowy (tmp + replace). Pusta lista → plik usunięty.
- API modułu: `load() -> list[(value, rule)]`, `add(value, rules)`, `remove(value, rule)`, `clear()`, `paths()` (do resetu).
- Dopasowanie: `value.strip().casefold()` + reguła (`R1`–`R5`, `MEDIUM …`). Reguły RED (`HIGH …`, `MAP_LEAK`) odrzucane przy `add` (błąd 400). Limit 500 wpisów (jak Mobile) → 400 z komunikatem, co zrobić („usuń stare wpisy w Ustawieniach”).
- **Migracja:** jawny `guard_allowlist.json` (stare ścieżki: `PROFILE_DIR`, `~/.pseudominizer/profile`) wczytany przy pierwszym `load`, wpisy z regułą `*` (= dowolna ŻÓŁTA reguła, nigdy RED), zapis zaszyfrowany, jawny plik usunięty. Nieczytelny jawny plik → usunięty, 0 wpisów, log bez treści.
- **Uszkodzony / nieodszyfrowany `.enc`:** `load` zwraca [] (więcej pytań = bezpiecznie), `add`/`remove` odmawiają (409, „Lista wyjątków jest uszkodzona — wyczyść ją w Ustawieniach → Wyjątki Guard”), nie nadpisują pliku; `clear` działa.
- Logi bez wartości (tylko długość/liczba) — S5.

### Backend — podpięcie (bez wzrostu dużych plików)
- `guard_residue.load_allowlist()` → `guard_allowlist.load()`; `collect_warnings`: trafienie wyciszane, gdy `(fragment.casefold, rule)` albo `(fragment.casefold, "*")` jest na liście **i reguła nie jest RED**.
- `pipeline._apply_guard`: `guard_output_with_map` bez allowlisty (MAP_LEAK zawsze pyta) — usunięcie argumentu.
- `pseudominizer_api.py` (1055 l., nie może rosnąć): `_guard_allowlist_path/_load/_save` usunięte; endpointy cienkie:
  - `GET /profile/guard-allowlist` → `{"entries": [{"value","rule"}]}`;
  - `POST /profile/guard-allowlist` body `{"value", "rules": [...]}`;
  - `POST /profile/guard-allowlist/remove` body `{"value", "rule"}` (zamiast DELETE z frazą w URL; stary DELETE usunięty);
  - reset profilu usuwa `guard_allowlist.paths()` (enc + stare jawne).

### Okno
- `GuardPanel.tsx`: przycisk „Zawsze jawne” + „?” tylko dla żółtych wierszy, gdy podany `apiToken` (brak = Express); stan „Zawsze jawne — cofnij”. Wywołania API w nowym małym `frontend/src/screens/guardAllowlist.ts` (add / remove).
- `Pseudonimizuj.tsx` (914 l., nie może rosnąć): tylko podmiana istniejącej linii z `<GuardPanel …>` (przekazanie `apiToken` poza Express) — bez nowych linii.
- `SecurityScreen.tsx` (790 l., nie może rosnąć): lista pokazuje wartość + rodzaj reguły, usuwanie przez `POST …/remove`; bilans linii ≤ 0.
- Błąd zapisu „Zawsze jawne” → pozycja pozostaje bez decyzji + komunikat (nie udajemy zapisu).

## Poza zakresem
- `LYNX-GUARD-DECISION-LOG` (trwały dziennik decyzji).
- Wyciszanie odmian (R1 „Kowalczyka” vs „Kowalczyk”) — wpis dotyczy dokładnie tego fragmentu; odmiany = osobne pytania.
- Zmiana formatu tokenu, mapy, KDF (S5 bez zmian).

TASK_SCOPE:
- backend/guard_allowlist.py
- backend/guard_residue.py
- backend/pipeline.py
- backend/pseudominizer_api.py
- backend/tests/test_guard_allowlist_s5.py
- frontend/src/screens/GuardPanel.tsx
- frontend/src/screens/guardAllowlist.ts
- frontend/src/screens/Pseudonimizuj.tsx
- frontend/src/screens/SecurityScreen.tsx
- tasks/LYNX-GUARD-ALLOWLIST-S5/brief.md
- tasks/LYNX-GUARD-ALLOWLIST-S5/repo_before.hash
- tasks/LYNX-GUARD-ALLOWLIST-S5/round_01/implementation/DELIVERY.md

Szacunek: backend ~90 (moduł) − ~35 (API) + ~5; okno ~45; testy ~110 → ok. 215–250 l. (>150 — zgoda OWNERA przed kodem).

## Odbiór
- `tests/test_guard_allowlist_s5.py` (temp `ANONYMIZER_PROFILE_DIR`):
  1. zapis → plik `.enc` nie zawiera wartości jawnie (bajty), `load` zwraca wpis; jawnego `.json` brak;
  2. migracja: jawny `["Kowalczyk Budownictwo"]` → wpis `*`, jawny plik usunięty, R5 na tym fragmencie wyciszone, HIGH/MAP_LEAK na tym samym fragmencie nie;
  3. `add` z regułą `HIGH PESEL` / `MAP_LEAK` → odmowa; limit 500;
  4. `collect_warnings`: wpis (`X`, `R5`) wycisza R5 dla `X`, nie wycisza R1 dla `X`; wielkość liter bez znaczenia;
  5. MAP_LEAK: wartość z mapy obecna jawnie + ta sama wartość na liście → ostrzeżenie zostaje (pipeline);
  6. uszkodzony `.enc` → `load` = [], `add` odmawia, plik nietknięty; `clear` usuwa;
  7. API (TestClient lub funkcje endpointów): GET/POST/remove; DELETE z frazą w URL nie istnieje; reset usuwa oba pliki.
- Regresja: `test_guard_residue*`, `test_layers`, `test_map_fidelity`, `test_audyt_2026_10` (znane faile bez zmian), `npm run build` / `tsc` okna.
- Ręcznie (CC na silniku 8765, potem oko Pawła): żółta pozycja → „Zawsze jawne” → nowy dokument z tym samym fragmentem nie pyta; „cofnij” przywraca pytanie; Ustawienia pokazują i usuwają wpis; czerwona pozycja bez przycisku.
