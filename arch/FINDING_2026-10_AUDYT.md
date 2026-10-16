# FINDING 2026-10 — Remanent i debug LynxMask Desktop (LYNX-CLOUD-AUDIT)

- Autor: CC (Claude Code w chmurze), 2026-10-16. Diagnoza, NIE naprawa: kod produktu, `arch/spec.md`, CLAUDE.md/AGENTS.md i narzędzia w korzeniu są nietknięte.
- Baza: `main@9c1ad7a` (gałąź `audyt/2026-10`). `guard.py check arch/spec.md` → `STATUS: PASS`.
- Środowisko: Linux, Python 3.12.3 (venv), bez GUI. Dodatkowo Python 3.14.6 (tylko kompilacja).
- Dane w przykładach są syntetyczne. PII zamaskowane częściowo („Kow*****”, „PL61 ****”).
- Dowody: logi w `audyt/logs/`, skrypty w `audyt/`, reproduktory `backend/tests/test_audyt_2026_10.py` (23 × `xfail(strict=True)`).
- Konwencja: **[S]** = sprawdzone (komenda/repro), **[P]** = podejrzewam (nie zweryfikowane do końca).

---

## 1. Streszczenie

Backend uruchamia się na Linuksie bez ręcznych obejść (morfeusz2 i tesseract instalują się natywnie). Suita testów daje ten sam wynik co na Windows. Jakość maskowania jest jednak gorsza, niż sugerują liczby z czerwca. Główne przyczyny to dwa ciche błędy w ścieżce produkcyjnej: filtr blocklisty NER i martwy seed słownika. Do tego dochodzą poważne luki w API (token Express + CORS `*`) i błędna integralność tokenów.

Top 5 ryzyk:
1. **BUG-NER-PREFIX-FILTER (KRYT, wyciek):** filtr prefiksów blocklisty (zbudowany z 34 tys. nazw miejscowości/ulic) odrzuca osoby poprawnie wykryte przez spaCy. W benchmarku tłumaczy **20 z 21 (95%)** pominiętych OSOBA. W pytaniach w stylu Roty **30% form nazwisk przechodzi jawnie**.
2. **BUG-EXPRESS-TOKEN-SCOPE + CORS `*` (KRYT, bezpieczeństwo):** dowolna strona WWW otwarta w przeglądarce użytkownika może pobrać token z `/express/token` i odczytać słownik encji, eksport słownika i archiwum (sprawdzone curl-em z obcym `Origin`).
3. **BUG-TOKEN-COLLISION (KRYT, integralność):** jedna encja w profilu wystarczy, żeby dwie różne osoby dostały ten sam token. Druga osoba znika z mapy, a Przywracanie wstawia złe nazwisko.
4. **BUG-SEED-DEAD (KRYT, wyciek):** seed 12 288 form imion/nazwisk nigdy nie trafia do trie. Przyczyny: `NameError: MAX_ONBOARD_BATCH`, a po dodaniu importu — limit 100. Sama naprawa importu nie wystarczy: seed ma też efekty uboczne (FP, tokeny 4-cyfrowe, osobny token na każdą formę).
5. **Guard i fail-closed dziurawe (WYS):** `/preview-express` nie ma Guarda i jest fail-open. Przy MAP_LEAK tekst wraca niezamazany i da się go skopiować przyciskiem „Kopiuj tekst”. Ochronę AUD-01 (wstrzyknięcie tokenu) obchodzi `OSOBA_001x` / `OSOBA_1001`.

Rota: przy wymuszonym słowniku osób (`known_people`) pomiar daje **0/60 jawnych form**. Silnik da się użyć, ale jest stanowy (profil na dysku), ciężki (~1 GB RAM, ~6 s zimnego startu), a Przywracanie nie zniesie odmiany tokenu przez model.

---

## 2. Tabela bugów

Kolejność: wycieki PII > bezpieczeństwo > crashe > false positives > reszta. Status: **potwierdzony / obalony / częściowo / nowy**.

### 2a. Wycieki PII

| ID | Status | Waga | plik:linia | Dowód | Proponowany fix (opis) |
|---|---|---|---|---|---|
| BUG-NER-PREFIX-FILTER | nowy | KRYT | `backend/ner_layer.py:226-228`, `backend/ner_blocklist.py:477-480` (prefiksy z `_GEO_WORDS`, l.50-90) | [S] spaCy wykrywa „Kat****** Wiś*******”, „Kow*****”, „Wiś*******” → `_filter_institutions` odrzuca (prefiksy `katarzyn`, `kowalski`, `wiśniews`; pochodzą z ulic „Kowalskiego”, „Wiśniewskiego” i miejscowości „Katarzynów”). 38% bazowych nazwisk z `surnames_top1000.json` i 23% imion trafia w prefiks. Benchmark: 20/21 pominiętych OSOBA ma prefiks w blockliście (`audyt/logs/benchmark_misses_masked.txt`). Dokumenty: **wszystkie 4 wycieki osób** z „Pliki testowe” mają tę przyczynę (spaCy wykrywa, filtr odrzuca), np. w `doc_lvl0_umowa_o_prace.txt` pełne imię i nazwisko pracownika jawne obok zamaskowanego PESEL. Rota prod: 18/60 form jawnych. Te same przyczyny dają 2 z 3 „znanych failów” (`test_prefix_nie_uderza_w_podobne_nazwy`, `test_prywatna_firma_nie_odfiltrowana`) i fail T20 „Wiś******* Consulting” w `test_pipeline.py`. Reproduktor: `test_filtr_ner_nie_odrzuca_osob`. | Nie odrzucać OSOBA po prefiksie. Prefiksy budować tylko z kuratorowanej listy słów pospolitych, nie z ulic/miejscowości (patronimiczne nazwy ulic = nazwiska). Ewentualnie tylko exact match. |
| BUG-SEED-DEAD (rozszerza BUG-ONBOARD-BATCH) | potwierdzony + nowy | KRYT | `backend/anonymizer.py:731,1530` (brak importu z `anonymizer_init.py:236`), `backend/seed_profile.py:90`, `backend/pseudominizer_api.py:228-232` (wyjątek połknięty jako WARNING) | [S] Log startu: `[STARTUP] seed_profile pominięty: name 'MAX_ONBOARD_BATCH' is not defined` (`audyt/logs/backend_log_excerpt.txt`). Seed podaje 12 288 wpisów, a limit wynosi 100 → po dodaniu importu `ValueError`. Dotknięte funkcje: `AnonymizerMap.add_entities_batch`, `onboard_entities_batch`, `seed_if_needed` (start backendu), `anonymize_with_ner` (ścieżka legacy, błąd połykany), `dict_auto_builder.py --apply`. Endpointy/UI: żaden endpoint nie woła batcha (`/profile/add-entity` używa `add_entity`); skutek jest cichy — słownik imion/nazwisk jest pusty, więc maskowanie osób opiera się wyłącznie na NER. [S] Hipotetyczny seed (obejście w procesie audytu) ujawnia kolejne problemy: FP na słowach pospolitych („piątku”, „niedzielę” → OSOBA, bo nazwiska Piątek/Niedziela); każda forma odmiany to osobna encja, więc inny token na każdy przypadek; tokeny `OSOBA_2187` (4 cyfry) nie pasują do żadnego `TOKEN_RE` (`\d{3}\b`); tokeny w środku e-maila (`OSOBA_964.OSOBA_2172@…`); brak form żeńskich nazwisk (seed mode: 2/60 jawnych, obie żeńskie). Reproduktory: `test_add_entities_batch_dziala`, `test_seed_profile_zasila_trie`. | Import stałej. Seed przez dedykowaną ścieżkę bez limitu UI (paczki) — **ale przed włączeniem decyzja OWNERA**: jedna encja = jedna osoba (forma bazowa + odmiany pod jednym tokenem), filtr słów pospolitych, formy żeńskie, numeracja zgodna z S2. |
| BUG-TOKEN-COLLISION | nowy | KRYT | `backend/layers/ner_adapter.py:239-249` (rejestracja ID z NER), `backend/pipeline_core.py:71-93` (`register` z `setdefault`) | [S] Profil z jedną encją „Jan Kow*****” (OSOBA_001) + tekst z drugą osobą: `Pacjent OSOBA_001 … Dłużnik OSOBA_001`, mapa `{'OSOBA_001': 'Jan Kow*****'}` — druga osoba znika z mapy, a Przywracanie wstawi pierwszą. Na żywym backendzie (profil zabrudzony testami HTTP) w `doc_test_nowe_encje.txt` „Pio** Now**” → token osoby „Jan Kow*****”. Reproduktor: `test_dwie_osoby_dwa_tokeny`. | NER ma przydzielać tokeny przez `state.allocator.allocate()`, nie własnym licznikiem w `ner_layer`; `register()` ma odrzucać ID już zajęte inną wartością. |
| BUG-GUARD-MAPLEAK-UNREDACTED | nowy | WYS | `backend/output_guard.py:414-421`, `backend/pipeline.py:338-344`, `frontend/src/screens/Pseudonimizuj.tsx:556-563` | [S] Przy naruszeniu MAP_LEAK guard zwraca `redacted_text=text`, więc zamazanie HIGH z pierwszego przebiegu ginie (PESEL wraca jawnie). `/preview` zwraca ten tekst jako `anonymized_preview`, a przycisk „Kopiuj tekst” nie jest blokowany przy `guardBlocked`. Reproduktor: `test_guard_map_leak_nie_odslania_pesel`. Odstępstwo od S3 („blokada wyniku”). | Przy blokadzie nie zwracać tekstu (albo tylko z zamazaniem HIGH i MAP). W UI zablokować kopiowanie, gdy `blocked`. |
| BUG-EXPRESS-NO-GUARD | nowy | WYS | `backend/pseudominizer_api.py:880-962`, `backend/pipeline_new.py:152-154` | [S] `/preview-express` nie woła Output Guarda (zawsze `blocked: False`). Wyjątek w `run_pipeline_express` zwraca oryginał z `force_block=False` (fail-open). Imiona i nazwiska przechodzą w 100% (z założenia: brak NER, Rota-test 60/60). Reproduktor: `test_express_fail_closed`. Odstępstwo od S3/S4. | Guard również w Express. Wyjątek → blokada. Decyzja OWNERA, czy Express w ogóle może zwracać tekst z osobami bez słownika. |
| BUG-IBAN-RECEPTA | nowy | WYS | `backend/credential_patterns.json:165` („Numer recepty” `\d{22}(?!\d)` bez lookbehind), `backend/pipeline_new.py:91-93` (credentials przed financial) | [S] Wejście `PL61 1090 …` → po ocr_normalizer sklejone → credentials łapie ostatnie 22 cyfry → wynik `PL6110NUMER_001` (kraj, suma kontrolna i 2 cyfry banku jawnie, typ „recepta”). To samo dla gołego NRB 26 cyfr. Guard nie reaguje. W dokumentach: `doc_lvl0` („rachunek ZUS: PL6110NUMER_010”). To przyczyna 3. „znanego faila” `test_iban_reverse_map_entry` (test jest poprawny). Reproduktor: `test_iban_pl_bez_jawnej_resztki`. | `(?<!\d)` w wzorcu recepty i/lub wymóg kontekstu „recept”. Rozważyć financial przed credentials. |
| BUG-AUD01-BYPASS | nowy | WYS | `backend/pseudominizer_api.py:280` (`_TOKEN_RE` z `\b`), `frontend/src/screens/Depseudonimizuj.tsx:68-73` | [S] curl `/preview`: `OSOBA_001` → 422, ale `OSOBA_001x`, `xOSOBA_001`, `OSOBA_1001` → 200. Przywracanie robi `replaceAll(token)` bez granic, więc wstrzyknięty `OSOBA_001x` zamieni się w prawdziwe nazwisko + „x”. Odstępstwo od S3. | Detekcja wstrzyknięcia zgodna z S2 (`(?!\d)` + brak litery/cyfry przed), Przywracanie po regexie z granicami. |
| BUG-UNMASK-SUBSTRING | nowy | WYS | `frontend/src/screens/Depseudonimizuj.tsx:68-73` | [S] Symulacja tej samej logiki (`audyt/unmask_sim.py`): `{OSOBA_100, OSOBA_1001}` → „Anna1 i Anna”; token zagnieżdżony w EMAIL zostaje nieprzywrócony; `Osoba_001`, `OSOBY_001`, `OSOBA 001` nie są przywracane. Mapa trzyma pierwszą napotkaną formę („Kow*******mu”), więc po przywróceniu jest zły przypadek. | Przywracanie regexem `(?<![A-Z0-9_])(KAT)_(\d+)(?!\d)`, dłuższe tokeny najpierw. Decyzja OWNERA co do tolerancji odmian tokenu. |
| BUG-NIP-LEAK | obalony | — | `backend/layers/identity.py`, `backend/output_guard.py:149-153` | [S] Pipeline: `512-34-56-789` → `NUMER_001` (również 3-3-2-2). Guard blokuje 3-2-2-3 z myślnikami i spacjami (`audyt/repro_guard.py`). Drobiazg: „VAT UE: PL65 51 97 93 13” → `PLNUMER_001` (zostaje samo „PL”, bez znaczenia). | — |
| BUG-IBAN-LETTERS | obalony (częściowo nowe) | NISK | `backend/output_guard.py:161` | [S] Guard ma już `[A-Z0-9]`: GB/IE/MT (ze spacjami i bez) → blokada. Pipeline maskuje GB w całości. Nowe drobne: (a) wzorzec połyka następne słowa WIELKIMI LITERAMI/cyfry („…19 W TERMINIE 7 DNI” → `[REDACTED]` bez reszty) — nadmierne zamazanie; (b) IBAN małymi literami nie jest łapany. NIP „PL65 51 97 93 13” w Guardzie: brak blokady (to FN Guarda, nie FP; pipeline go maskuje). Wzorzec z Mobile `\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}\b`: grupy po 4 zatrzymają połykanie, ale nie złapią ostatniej grupy <4 (np. GB „… 19”) — do oceny architekta. | Ograniczyć powtórzenia do grup 4 + końcówka 1-4; ewentualnie `(?i)` dla prefiksu kraju. |

### 2b. Bezpieczeństwo

| ID | Status | Waga | plik:linia | Dowód | Proponowany fix (opis) |
|---|---|---|---|---|---|
| BUG-EXPRESS-TOKEN-SCOPE + BUG-CORS-WILDCARD | nowy | KRYT | `backend/pseudominizer_api.py:296-300` (CORS `allow_origins=["*"]`, `allow_headers=["*"]`), `:309-319` (middleware akceptuje token Express wszędzie), `:328-333` (`/express/token` bez auth) | [S] curl z `Origin: https://evil.example`: `/express/token` → 200 + `access-control-allow-origin: *`. Preflight na `/profile/reset` → zezwolony. Z tym tokenem: `/profile/entities` → 200 i lista encji, `/profile/export-dict` → 200, `/archive` → 200. Bez tokenu → 401. Strona WWW w przeglądarce użytkownika może więc odczytać słownik (nazwiska klientów) i listę archiwum, usunąć archiwum lub zresetować profil (destrukcyjnych endpointów nie wywoływałem). Komentarz „localhost-only — wildcard bezpieczny” jest błędny. [P] Częściowo łagodzi to Private Network Access w nowszym Chrome; Firefox tego nie ma. Reproduktory: `test_express_token_nie_otwiera_profilu`, `test_cors_nie_wpuszcza_obcego_origin`. | CORS tylko dla originu Tauri. Token Express ważny wyłącznie dla `/preview-express`. `/express/token` dostępny tylko dla aplikacji (np. przez plik/IPC jak główny token). |
| BUG-AUTH-BYPASS | częściowo | ŚRED | `backend/pseudominizer_api.py:144,313` | [S] Gdy lifespan nie wystartował (TestClient bez `with`, osadzenie w innym ASGI), `_API_TOKEN=""` i `compare_digest("", "")` → żądanie bez nagłówka przechodzi. Istniejące `test_archive_adversarial.py` działa właśnie dzięki temu (żądania bez tokenu dostają 200). W produkcji uvicorn uruchamia lifespan przed nasłuchem, więc [P] tam niewykorzystywalne. Reproduktor: `test_pusty_token_nie_przepuszcza`. | Odrzucać, gdy token serwera pusty. Testy archiwum uruchamiać z lifespanem/tokenem. |
| BUG-S5-LOGS | nowy | WYS | `backend/uruchom.vbs:50-55` (stdout/stderr `>> pseudominizer.log`), `backend/output_guard.py:265-270,293-297,414` (wartość w logu), `backend/pseudominizer_api.py` (`[GUARD-ALLOWLIST] Dodano: {phrase!r}`), `backend/pytest.ini` (`log_file=pytest.log`, DEBUG) | [S] W logu backendu: `Plain text 'Kom***' — encja z reverse_map…` (wartość z benchmarku), `[GUARD-ALLOWLIST] Dodano: 'Zen***'` i access log uvicorna z frazą w URL `DELETE /profile/guard-allowlist/Zen***` (`audyt/logs/backend_log_excerpt.txt`, zamaskowane przeze mnie). `pytest.log`: 7 wierszy `[FILTER] pominięto (prefix): 'Kat***'`. Udokumentowany starter (`uruchom.vbs`) zapisuje te logi na dysk, a S5 mówi „bez FileHandler — PII nie trafia na dysk”. | Nie logować wartości (tylko kategoria/długość). Allowlista: DELETE z body zamiast frazy w ścieżce. `uruchom.vbs`: bez przekierowania albo poziom WARNING bez wartości. |
| BUG-S5-TRIE-PLAINTEXT | nowy | ŚRED | `backend/anonymizer.py:865-877` (`pickle.dump` trie), `backend/anonymizer_crypto.py:188-200` (keystore z kluczami obok mapy), `backend/pseudominizer_api.py:817-836` (allowlista w `~/.pseudominizer/profile/guard_allowlist.json`) | [S] `strings anon_profiles/pseudominizer/trie.pkl` → 224 trafienia nazw encji jawnym tekstem. `mapa.enc` jest szyfrowana kluczem z `triangulum_keystore.bin` w tym samym katalogu (0600), więc szyfrowanie bez sekretu użytkownika. Allowlista jawnym tekstem. Odstępstwo od S5 („mapa wyłącznie zaszyfrowana”). `pickle.load` z katalogu profilu = wykonanie kodu przy podmianie pliku (lokalnie, NISK). | Decyzja OWNERA: trie w pamięci albo szyfrowane, klucz profilu z hasła użytkownika (wymaga planu migracji — por. AUD-13/14). |
| BUG-GITIGNORE-REAL | nowy | WYS | `.gitignore`, `backend/preview_real_docs.py:74-86` | [S] `backend/preview_real_results/` nie jest ignorowane (`git status` pokazuje `??`). Raport zawiera `WYNIK MASKOWANIA` i oryginały tokenów z **realnych** dokumentów. Jedno `git add -A` = realne PII w repo (wbrew CLAUDE.md/AGENTS.md). `dataset_real/` jest ignorowane (`backend/dataset_*/`). | Dopisać `backend/preview_real_results/` do `.gitignore` (księgowość, mała zmiana — do decyzji, czy jako Task). |
| BUG-S3-ARCHIVE-403-DEAD | nowy | ŚRED | `frontend/src/screens/Pseudonimizuj.tsx:250-258` (body bez `guard_blocked`), `:235-237,776` (`handleSave(forceBypassGuard)` jako `onClick`), `backend/pseudominizer_api.py:526-530` | [S] Frontend nigdy nie wysyła `guard_blocked`, więc backend zapisuje `False` i kontrola „/archive → 403 dla guard_blocked” (S3) nie działa w praktyce. Flaga pochodzi od klienta. `onClick={handleSave}` przekazuje MouseEvent jako `forceBypassGuard=true` (błąd TS2322), dziś zablokowane tylko przez `disabled`. | Backend sam zapamiętuje blokadę per PSE (z `/preview`) zamiast ufać klientowi. W UI `onClick={() => handleSave()}`. |
| BUG-S3-PIPELINE-EXCEPTION | nowy | ŚRED | `backend/pipeline.py:253-263` | [S] Wyjątek w `_run_pipeline` → `PipelineResult(text=<oryginał>, guard_blocked=False)`, a `/preview` zwraca `blocked: False` i oryginał jako `anonymized_preview`. [P] Rzadkie, bo `run_pipeline_new` łapie wyjątki, ale `_apply_guard`/import mogą rzucić. Komunikat błędu zawiera mojibake („BĹ‚Ä…d”). | `guard_blocked=True` i pusty tekst przy wyjątku. |
| BUG-ALLOWLIST-SUBSTRING | nowy | ŚRED | `backend/output_guard.py:405-410` | [S] Allowlista porównuje frazę z treścią komunikatu naruszenia (`a in v.lower()`). Wpis „encja” (albo „plain”, „mapy”, jedna litera) wyłącza wszystkie naruszenia MAP_LEAK. Reproduktor: `test_allowlist_nie_wylacza_innych_naruszen`. | Porównywać z samą wartością naruszenia (exact, casefold). |
| AUDIT-LATENT | nowy | NISK | `backend/audit_log.py:123-146,163-173` | [S] Przy `AUDIT_MODE=True` rekord zawiera `stats.leaks[].original` i `guard_reasons` z wartościami — wraca CRIT-2. Dziś `AUDIT_MODE=False`, więc uśpione. | Usunąć wartości także z `leaks` i `guard_reasons`. |
| AUD-09 / AUD-10 (znane) | potwierdzony | NISK | `frontend/src-tauri/tauri.conf.json` (CSP `'unsafe-inline'`), `capabilities/default.json` (fs scope `$DOCUMENT/Pseudominizer/**`) | [S] Stan jak w PROJEKT_KONTEKST. fs scope jest już zawężony. | Bez zmian względem znanego planu. |
| PBKDF2 (opis, ODLOZONE) | — | — | `frontend/src-tauri/src/main.rs:30-33,276,376` | [S] PBKDF2-HMAC-SHA256, 500 000 iteracji, sól 16 B z pliku, klucz 32 B, AES-256-GCM, nonce 12 B. Ten sam KDF dla klucza odzyskiwania. Nie ruszane (ODLOZONE 2026-10-16). | — |
| Nasłuch / sekrety | sprawdzone, OK | — | `backend/pseudominizer_api.py:1122-1126`, `uruchom.vbs` | [S] Host `127.0.0.1` w obu ścieżkach (brak `0.0.0.0`). Historia git (76 commitów, wszystkie gałęzie): brak kluczy/tokenów, `api_token.txt`, `.enc`, `anon_profiles`, `rejestr.db`. Jedyne trafienie nazwy pliku: `preview_real_docs.py` (narzędzie, nie dane). | — |

### 2c. Crashe / build

| ID | Status | Waga | plik:linia | Dowód | Proponowany fix (opis) |
|---|---|---|---|---|---|
| BUG-ONBOARD-BATCH | potwierdzony | KRYT (patrz BUG-SEED-DEAD) | `backend/anonymizer.py:731,1530` | [S] ruff F821 ×4. `NameError` w logu startu. Reproduktor xfail. | Import z `anonymizer_init`. |
| BUILD-TSC | nowy | WYS | `frontend/src/theme.ts` (23), `screens/MainLayout.tsx:178-181` (4), `App.tsx:175`, `screens/Pseudonimizuj.tsx:776`, `screens/SecurityScreen.tsx:495,594` | [S] `npm run build` → `tsc` exit 2, 31 błędów (`audyt/logs/npm_build.txt`). `build.sh` i `tauri.conf.json beforeBuildCommand` wołają `npm run build`, więc build release nie przejdzie. `npx vite build` sam przechodzi (243 kB). | Poprawić typy (theme jako szeroki typ, nie literal `as const` dla obu motywów). |
| BUILD-ICONS | nowy | ŚRED | `frontend/src-tauri/icons/32x32.png`, `128x128.png`, `icon.icns` | [S] `cargo check` → `icon …/32x32.png is not RGBA` (proc macro panic). `icon.icns` to w rzeczywistości PNG. Na kopii z ikonami RGBA `cargo check` przechodzi bez ostrzeżeń (`audyt/logs/cargo_check_kopia_ikony_rgba.txt`). [P] Na Windows Tauri bierze `.ico`, więc tam przechodzi. Blokuje build Linux/macOS. | Wygenerować ikony `tauri icon`. |
| TEST-SMOKE-E2E | nowy | NISK | `backend/tests/test_smoke_e2e.py:179` | [S] 7/7 fail: `body.get("ocr", {})` zwraca `None` dla .txt → `AttributeError`. Błąd testu, nie produktu. | `(body.get("ocr") or {})`. |
| TEST-COLLECTION | nowy | ŚRED | `backend/pytest.ini` (`python_files=` lista) | [S] `pytest tests/` nie zbiera `test_layers.py` (60 testów, wszystkie zielone), `test_smoke_e2e.py` ani nowego `test_audyt_2026_10.py`. `test_pipeline.py` to osobny runner (24/25, fail = BUG-NER-PREFIX-FILTER). | Wzorzec `test_*.py` albo dopisanie plików. |

### 2d. False positives / false negatives silnika

| ID | Status | Waga | plik:linia | Dowód | Proponowany fix (opis) |
|---|---|---|---|---|---|
| BUG-NER-FP | częściowo | NISK | `backend/ner_layer.py`, `backend/ner_blocklist.py` | [S] „Kont0” (OCR z „Konto:”) → OSOBA — potwierdzone (reproduktor `test_kont0_nie_jest_osoba`). „KONTROLNA”, „Encje” → nie maskowane (obalone; filtr przymiotników działa). „Byt0m” → ocr_normalizer zamienia na „Bytom”, nie FIRMA (obalone). Samo imię z e-maila → w prod e-mail w całości EMAIL_001 (obalone); po naprawie seeda tokeny wchodzą do środka e-maila (patrz BUG-SEED-DEAD). | Blocklista dla form OCR „Kont0/Konto”. |
| BUG-INSTITUTION-FP | obalony | — | `backend/layers/institution.py:34-37` | [S] Skróty w `(?-i:…)`: „Nika”, „Gusa”, „pip”, „nik gus pip” → bez zmian. | — |
| BUG-NER-FIRMA-INST | nowy | ŚRED (FN) | `backend/ner_layer.py:194-197,242` | [S] `_INSTITUTION_IN_FIRMA_RE` z IGNORECASE odrzuca FIRMA „Nik-Pol Sp. z o.o.”, „Agro-Gus S.A.”, „Gusto Pip Sp. z o.o.”. Reproduktor: `test_firma_z_fragmentem_skrotu_nie_odrzucona`. | Wielkie litery, całe słowo (`(?-i:)` jak w institution.py). |
| BUG-INSTITUTION-ORDER | obalony | — | `backend/pipeline_new.py:85-93` | [S] Kolejność jest już NER → address → institution. „Kancelaria Sądu Rejonowego sp. z o.o.” → `FIRMA_001` w całości. | — |
| BUG-ADDR-FP | zmierzony | ŚRED | `backend/layers/address.py` | [S] Benchmark (100 dok., seed 42): ADRES **R=94,5%, P=68,8%** (86/91, FP=39). Uwaga metodologiczna [S]: benchmark liczy jako FP poprawne encje w wariancie OCR (np. „al. Niepodległości 150/47” zamiast „159/47”), więc precision jest zaniżona. | Do osobnego pomiaru z dopasowaniem rozmytym. |

### 2e. Reszta

| ID | Status | Waga | plik:linia | Dowód | Proponowany fix (opis) |
|---|---|---|---|---|---|
| BUG-TOKEN-RE-SPEC | nowy (kontrakt) | WYS | `anonymizer_init.py:231-232`, `pseudominizer_api.py:280`, `pipeline.py:132`, `ner_layer.py:136`, `layers/ner_adapter.py:68` (bez INSTYTUCJA), `output_guard.py:191`, `verbal_amounts.py:49`, `frontend/src/screens/Pseudonimizuj.tsx:89`, `ExpressModeScreen.tsx:33` | [S] Wszystkie 9 kopii używa `_\d{3}\b`, a zamrożony spec S2 mówi „`TOKEN_RE` używa `(?!\d)`, NIE `\b`”. Skutki: `PL6110NUMER_001` i `OSOBA_1001` nie są rozpoznawane (reproduktor `test_token_re_zgodny_z_spec`), podświetlenie i AUD-01 nie działają (patrz wyżej). Nie zmieniałem TOKEN_RE. | **Decyzja OWNERA** (wspólne z Mobile): ujednolicić do jednej definicji zgodnej z S2. |
| BUG-GLOBAL-SPACE-GLUE | nowy (kontrakt S2) | ŚRED | `backend/layers/ner_adapter.py:106-110` (`_fix_ocr_email`) | [S] Regex „a. b@” nie wymaga `@`: usuwa białe znaki (także `\n`) po każdej kropce poprzedzonej ≥2 znakami ASCII. „szpitalu. Dłużnik” → „szpitalu.Dłużnik”, „nieokreślony.\n2.” → „nieokreślony.2.”. To globalne sklejanie, którego S2 zakazuje („zniszczyło Mobile”). Reproduktor: `test_fix_ocr_email_nie_skleja_zdan`. | Ograniczyć do kontekstu z `@` w tym samym tokenie. |
| BUG-OCR-NORMALIZER-WORDS | nowy | ŚRED | `backend/layers/ocr_normalizer.py:62-93` (`_OCR_TO_DIGIT`: z→2, l→1, o→0) | [S] „(nr tel. 512 987 654) zglosil” → „2g10si1”. Zwykłe słowa po liczbie są zamieniane na cyfry, przez co model AI dostaje zepsuty tekst. Reproduktor: `test_ocr_normalizer_nie_psuje_slow`. | Konwersja tylko wewnątrz dopasowanego wzorca numeru. |
| BUG-UNMASK-FIDELITY | nowy | ŚRED | wynik pipeline + `Depseudonimizuj.tsx` | [S] Przywracanie (`audyt/roundtrip.py`) na 7 dokumentach: **0/7 identycznych z wejściem** (ratio 0,984-0,996). Przyczyny: sklejanie zdań, zmiany OCR (`©`→`@`, `1`→`i`, „Zl”→„21”), zjedzone dwukropki, `OSOBA_001 OSOBA_001` dla „Rob*** Now***” (po przywróceniu nazwisko podwójnie), tokeny nieprzywrócone przy kolizji. | Pipeline nie powinien zmieniać tekstu poza spanami tokenów. Mapa per span. |
| BUG-ARCHIVE-ISOLATION | częściowo | ŚRED | `backend/tests/test_archive_adversarial.py:48-62`, `backend/db_store.py:126` | [S] 2× z rzędu: 17 passed (brak duplikatu, bo `INSERT OR REPLACE`). Ale testy piszą do produkcyjnego `backend/archive/` (`PSE-2026-9001.enc` itd.) i nadpisują rekord bez ostrzeżenia. Testy HTTP (`test_pipeline.py` T19 i in.) dopisują encje do **prawdziwego profilu** użytkownika — 18 syntetycznych encji w profilu spowodowało kolizję tokenów w moich przebiegach. `/archive` nadpisuje istniejący PSE bez ostrzeżenia (utrata mapy) [S z kodu]. | `ARCHIVE_DIR`/`ANONYMIZER_PROFILE_DIR` tymczasowe w testach. `INSERT` bez `REPLACE` + 409. |
| BUG-10 | obalony / naprawiony | NISK | `backend/ocr_engine.py:85-95` | [S] v1.2: kandydaci Windows + PATH; na Linuksie `[STARTUP] OCR (Tesseract) dostepny`. Pozostałe hardkody: `uruchom.vbs:28-29` (`C:\Users\p_pie\…\python.exe`), `frontend/src-tauri/src/main.rs:139-152` (`%USERPROFILE%\Desktop\LynxMask-Desktop\backend`), `generator.py:93,1380-1382`, `scripts/generuj_obrazy_ocr.py:43`, przykłady w `benchmark_real.py`. | Konfiguracja przez zmienną środowiskową. |
| PIPELINE-MOJIBAKE | nowy | NISK | `backend/pipeline.py` (BOM + podwójnie zakodowane UTF-8 od commitu `ffeaff3`) | [S] Log `[PIPELINE] output_guard zaĹ‚adowany`, komunikat dla użytkownika „BĹ‚Ä…d pseudonimizacji”. Regexy nowej ścieżki nie są dotknięte. | Odkodować plik. |
| NO-REQUIREMENTS | nowy | ŚRED | `backend/` | [S] Brak `requirements*.txt`/lockfile. Zależności wyprowadzone z importów: fastapi, uvicorn, python-multipart, spacy + `pl_core_news_lg`, cryptography, python-stdnum, phonenumbers, pymupdf, python-docx, pillow, pytesseract, numpy, pyahocorasick, morfeusz2, requests (+ pytest, httpx). `postal-codes-tools` opcjonalne (tylko martwa ścieżka legacy). pip-audit na tym zestawie (najnowsze wersje): brak podatności — bez pinów to nic nie mówi o środowisku OWNERA. | `requirements.txt` z pinami. |
| PY314-SYNTAXWARNING | potwierdzony | NISK | docstringi: `output_guard.py:6`, `anonymizer_init.py:6`, `layers/contact.py:4`, `layers/ocr_normalizer.py:19`, `layers/identity.py:5` | [S] Python 3.14.6: kompilacja OK, 5 × `SyntaxWarning: "\d" is an invalid escape sequence. Such sequences will not work in the future`. Ruff W605 ×31 — wszystkie w docstringach, regexy są `r""`. | `r"""` w docstringach. |
| NPM-AUDIT | potwierdzony | NISK | `frontend/package-lock.json` | [S] 7 podatności (5 high, 2 moderate): esbuild, postcss, nanoid, source-map-js, browserslist, baseline-browser-mapping — narzędzia builda (dev), nie trafiają do aplikacji. | `npm audit fix` w osobnym Tasku. |

---

## 3. Wyniki testów, ruff i metryk

### 3a. Testy (`cd backend && python -m pytest tests/ -q -rs`)

| Przebieg | Wynik | Log |
|---|---|---|
| Bez backendu (Linux) | **3 failed, 122 passed, 40 skipped, 1 xfailed** — identycznie jak Windows | `audyt/logs/pytest_bez_backendu.txt` |
| Z backendem w tle | **3 failed, 160 passed, 2 skipped, 1 xfailed** (38 testów HTTP przechodzi) | `audyt/logs/pytest_z_backendem.txt` |
| `test_layers.py` (niezbierany przez pytest.ini) | 60 passed | — |
| `test_smoke_e2e.py` (niezbierany) | 7 failed (błąd testu, TEST-SMOKE-E2E) | — |
| `python tests/test_pipeline.py` (runner) | 24/25, fail T20 „Wiś******* Consulting” = BUG-NER-PREFIX-FILTER | — |
| `test_audyt_2026_10.py` (nowy) | **23 xfailed** (strict) | `audyt/logs/pytest_audyt_xfail.txt` |

Przyczyny źródłowe 3 „znanych failów” — **żaden nie jest nieaktualnym testem, wszystkie wykrywają realne błędy produktu**:
- `test_pipeline_v2.py::TestIbanWithSpace::test_iban_reverse_map_entry` → BUG-IBAN-RECEPTA. ocr_normalizer skleja IBAN, a credentials („Numer recepty” `\d{22}(?!\d)`) zabiera ostatnie 22 cyfry przed warstwą financial. `reverse_map['NUMER_001']='9010…2874'`, w tekście zostaje jawne `PL6110`.
- `test_pseudominizer.py::TestFilterFunction::test_prefix_nie_uderza_w_podobne_nazwy` i `::test_prywatna_firma_nie_odfiltrowana` → BUG-NER-PREFIX-FILTER (log: `[FILTER] pominięto (prefix): 'Sad******…'` / `'Kow*****…'`).

Skipy z backendem (2): degraded Morfeusz (Morfeusz dostępny) i C10 (test ręczny).

### 3b. Ruff (`ruff check backend --statistics`, ruff 0.17.1, `ruff.toml` z korzenia)

122 naruszenia: W605 31, F401 29, F541 27, F841 10, E701 7, E731 4, **F821 4**, W292 3, E402 3, E401 3, E741 1. Klasy E722 i F811: 0.
- **Realne bugi:** tylko F821 ×4 (`MAX_ONBOARD_BATCH`, BUG-ONBOARD-BATCH).
- F841 ×10: kosmetyka (benchmark, self-testy w `pipeline_new.py`, testy, skrypt) — żadne nie zmienia zachowania.
- W605: docstringi (patrz PY314). F401/F541/E70x/E731/E741/E40x: kosmetyka.

### 3c. Frontend i Tauri

- `npm ci`: OK. `npm run build`: **FAIL** (31 × TS, BUILD-TSC). `npx vite build`: OK. `npm audit`: 7 (dev).
- `cargo check` (Tauri 2, po doinstalowaniu `libwebkit2gtk-4.1-dev` itd.): **FAIL** na ikonach RGB (BUILD-ICONS). Na kopii z ikonami RGBA: OK, 0 ostrzeżeń.

### 3d. Metryki maskowania

**Benchmark syntetyczny OCR** (`python benchmark.py --count 100 --seed 42`, lvl ≤ 3, backend jak w produkcji, czyli bez seeda) — `audyt/logs/benchmark_summary_seed42_n100.txt`:

| Metryka | Teraz (2026-10-16) | Czerwiec 2026 |
|---|---|---|
| Recall (privacy) | 88,2% (456/517) | 89,7% |
| Precision | 59,8% (307 FP) | 70,4% |
| F1 | 71,3% | 78,9% |
| OSOBA recall | 80,2% (85/106) | 96,3% |
| Critical leakage (PESEL/NIP/IBAN/dowód/paszport) | 7,7% (14/181) | CLR ≤ 4,3% |
| Akceptacja OCR | 80/100 (19 odrzuconych, 1 Guard) | — |

Per kategoria (R / P): ADRES 94,5 / 68,8 · NUMER 91,0 / 59,8 · TELEFON 91,2 / 100 · SYGNATURA 87,5 / 100 · OSOBA 80,2 / 70,8 · EMAIL 40,0 / 100 (4/10). Per poziom: lvl0 91,1 · lvl1 91,4 · lvl2 92,8 · lvl3 76,5.
Zastrzeżenia: inna próba niż w czerwcu (seed 42, n=100), więc różnice to nie czysta regresja. FP zawyżone przez warianty OCR liczone jako FP. EMAIL: na czystym tekście 3/3 adresów z pominiętych wzorców jest maskowanych [S], więc spadek w benchmarku to [P] OCR obrazu albo łączenie e-maila z tokenem OSOBA. Spadek OSOBA wyjaśnia BUG-NER-PREFIX-FILTER (20/21 pominięć) [S].

**Dokumenty z `Pliki testowe/` (7) i `backend/test_docs/` (2, identyczne z kopiami w „Pliki testowe”)** przez `/preview` (`audyt/run_docs.py`, `audyt/logs/docs_preview_summary.txt`). Brak ground truth (pliki tego nie zawierają), więc wynik to detektor kandydatów + ręczny przegląd. Guard nie zablokował żadnego dokumentu.

Lista WYCIEKÓW (jawne PII w wyniku):

| Dokument | Kategoria | Kontekst (zamaskowany) | Przyczyna |
|---|---|---|---|
| doc_lvl0_umowa_o_prace | OSOBA | „PRACOWNIKIEM:\nKat****** Wiś*******\nPESEL: NUMER_004” (2×) | BUG-NER-PREFIX-FILTER (`katarzyn`) |
| doc_lvl0_umowa_o_prace | NUMER (IBAN, częściowo) | „rachunku ZUS: PL6110NUMER_010” | BUG-IBAN-RECEPTA |
| doc_lvl3_faktura_zlecenie | OSOBA | „reprezentowany przez: dyr.Ry*** Ko***, PESEL: NUMER_004” (także na świeżym profilu) | BUG-NER-PREFIX-FILTER (spaCy wykrywa, odrzucone: prefiks `ryszarda`) [S] |
| doc_test_nowe_encje | OSOBA | „Ma*** Ka***-Za***, córka Ja***.” (także na świeżym profilu) | BUG-NER-PREFIX-FILTER (prefiks `małgorza`; „Ja***” exact w blockliście) [S] |
| doc_test_nowe_encje | integralność | „Dł***** Pio** Now**” → token innej osoby | BUG-TOKEN-COLLISION (profil zabrudzony testami) |
| doc_stresstest | integralność | jeden token nieprzywrócony przy Przywracaniu | BUG-TOKEN-COLLISION / UNMASK |
| (Rota, zdania) | OSOBA | „Kow*******mu nie dało soboty, ma L4…” | BUG-NER-PREFIX-FILTER |

Kandydaci „CYFRY≥6” w wynikach to fałszywe alarmy detektora: kod PSE w nagłówku, „Znak: GT.022.4531.2024”, daty, kod tytułu ubezpieczenia „01 10 00” — nie PII.
False positives (przegląd): „FIRMA_002 = 'z o.o'” (forma prawna jako osobna firma, lvl1), „OSOBA_001 OSOBA_001” (podwojenie), „Kont0” → OSOBA; przy seedzie także „piątku”/„niedzielę” → OSOBA.
**Przywracanie 1:1: NIE** — 0/7 dokumentów (BUG-UNMASK-FIDELITY).

---

## 4. Gotowość pod Elnath Rota

### 4a. Pomiar (`audyt/rota_leak_test.py`, `audyt/logs/rota_leak_test.txt`)

36 zdań koordynatora (6 przypadków × {2 mężczyzn imię+nazwisko, 2 kobiety imię+nazwisko, 2 samo nazwisko}). 60 form. Imiona z `backend/names_inflected.json`, nazwiska z `backend/surnames_top1000.json`, formy przypadków z Morfeusza 2, ziarno 2026. Plików `big_*`/`benchmark_results/cursor_stress` nie ma w repo; `benchmark_results/` jest w `.gitignore` (fakt, nie błąd).

| Tryb | Formy jawnie | Zdania z wyciekiem | Czas / zdanie (mediana, max) |
|---|---|---|---|
| **prod** — jak API dziś (spaCy + anonymizer, seed martwy) | **18/60 (30%)** | 14/36 | 18 ms, 43 ms |
| seed naprawiony (hipotetycznie, obejście w procesie) | 2/60 (3%) — obie formy żeńskie | 2/36 (+ FP „niedzielę” → OSOBA) | 62 ms, 93 ms |
| **known_people** (do pustego profilu dodane osoby z pytania, `add_entity` + Morfeusz) | **0/60 (0%)**, cała osoba = 1 token | 0/36 | 24 ms, 33 ms |
| express (bez NER) | 60/60 (100%) | 36/36 | <1 ms |

Per przypadek (prod, jawne/razem): nom 1/10, gen 4/10, dat 3/10, acc 4/10, inst 5/10, loc 1/10.
Przykład z briefu: „czemu Kow*******mu nie dało soboty, ma L4 bo złamał nogę” → prod: bez zmian (wyciek nazwiska + dana o zdrowiu przy osobie); known: `czemu OSOBA_001 nie dało soboty…`.
Zimny start (import pipeline + `pl_core_news_lg`): **5,9 s**, RSS **~960 MB** po załadowaniu modelu.

### 4b. Co da się użyć wprost

- `pipeline_new.run_pipeline_new(text, anon_map, anonymizer)` + `TokenAllocator` (stan per wywołanie) — rdzeń regex/NER działa na Linuksie bez Tauri/UI/GPU/sieci. Wyniki są deterministyczne [S: dwa przebiegi `rota_leak_test.py --modes prod,known` — identyczne teksty i mapy].
- `AnonymizerMap.add_entity()` + Morfeusz 2 generuje odmiany — mechanizm „wymuszonego słownika” daje 0/60 w pomiarze.
- Warstwy regex (`layers/*`), Output Guard (`guard_output_with_map(…, known_plain=…)`).

### 4c. Co blokuje

1. **Stan na dysku:** `build_anonymizer(profile_dir, hw)` tworzy/zapisuje `mapa.enc`, keystore, `trie.pkl`. `add_entity` zapisuje na dysk przy każdym wywołaniu. Bezstanowe `mask()` wymaga trie w pamięci per żądanie (dziś brak takiego API).
2. **Stan globalny i współbieżność:** `spacy_ner._nlp` (singleton — OK), `ocr_normalizer._DICT_LOADED`, wspólny `Anonymizer` w `AppState`. `known_people` per żądanie przez wspólny profil = wyścigi i przeciek osób między kontami.
3. **Błędy silnika istotne dla Roty:** BUG-NER-PREFIX-FILTER (30% wycieku bez słownika), BUG-TOKEN-COLLISION (słownik + NER = dwie osoby jeden token), BUG-GLOBAL-SPACE-GLUE i OCR-normalizer modyfikują tekst pytania (dla krótkich pytań bez znaczenia dla bezpieczeństwa, ale zmieniają treść).
4. **Ciężar:** ~1 GB RAM i ~6 s startu (spaCy lg). [P] Przy wymuszonym słowniku NER jest potrzebny tylko do osób spoza obsady — można rozważyć tryb bez NER z Guardem (decyzja OWNERA o ryzyku).
5. **Przywracanie nie zniesie odmiany pseudonimu przez model** [S, `audyt/unmask_sim.py`]: `OSOBY_001`, `Osoba_001`, `OSOBA 001` zostają nieprzywrócone. `OSOBA_001'owi` → „Kow*****'owi”. Mapa trzyma pierwszą formę z pytania („Kow*******mu”), więc odpowiedź modelu „OSOBA_001 ma L4” wraca jako „Kow*******mu ma L4” (zły przypadek). Potrzebna mapa token → forma bazowa (+ opcjonalnie odmiana Morfeuszem po tagu z kontekstu) i tolerancyjny regex.
6. Imiona spoza listy, zdrobnienia („Ania”, „Kuba”) i samo imię bez nazwiska (w trybie known z samym nazwiskiem imię „Jan” przeszło) — `known_people` musi zawierać imię, nazwisko i [P] zdrobnienia.

### 4d. ARCHITECTURE_PROPOSAL (nieblokujące, decyzja OWNERA)

```text
ARCHITECTURE_PROPOSAL: LYNX-ROTA-MASK-CORE
Cel: bezstanowy moduł maskowania krótkich pytań, importowalny przez usługę Roty (Linux),
bez Tauri/UI/FastAPI/dysku. Format tokenu i TOKEN_RE bez zmian (S2).

Moduł: backend/lynx_core.py (nowy szew; korzysta z istniejących ownerów: layers/*,
pipeline_core.TokenAllocator, output_guard, Morfeusz przez MorfeuszEnv)

  @dataclass(frozen=True)
  class Person:      id: str; first: str | None; last: str | None; aliases: tuple[str, ...] = ()
  @dataclass(frozen=True)
  class MaskResult:  masked_text: str; mapping: dict[str, str]   # token -> forma BAZOWA
                     blocked: bool; reasons: list[str]

  def mask(text: str, known_people: list[Person], *, use_ner: bool = False) -> MaskResult
     1. Trie w PAMIĘCI z known_people: imię, nazwisko, "imię nazwisko", odmiany Morfeusza
        (m/ż), aliasy → JEDEN token na osobę (OSOBA_NNN wg kolejności w known_people,
        deterministycznie).
     2. Warstwy regex (identity/contact/financial…) przez TokenAllocator.
     3. Opcjonalnie NER (use_ner) — tokeny WYŁĄCZNIE przez allocator (por. BUG-TOKEN-COLLISION).
     4. Guard: guard_output_with_map(masked, None, known_plain=wszystkie formy known_people)
        → blocked=True, jeśli jakakolwiek forma przetrwała (fail-closed, S3).
     Brak zapisu na dysk, brak logowania wartości (S5).

  def unmask(text: str, mapping: dict[str, str]) -> str
     Regex z granicami (S2: (?!\d) + brak [A-Za-z0-9_] przed), dłuższe najpierw;
     tolerancja: wielkość liter, odmiana kategorii (OSOBY_/OSOBIE_…), spacja zamiast "_".
     Wstawia formę bazową (bez zgadywania przypadku).

Wymagania niefunkcjonalne: < 50 ms dla ~500 znaków bez NER (pomiar: 24 ms z NER na krótkich
zdaniach); start bez spaCy < 1 s [P]; test szczelności = audyt/rota_leak_test.py w CI
(cel 0 jawnych form dla known_people, raport jako artefakt — dowód staranności RODO).
Otwarte dla OWNERA: (a) czy NER w ogóle (koszt 1 GB vs osoby spoza obsady);
(b) zdrobnienia — lista czy pole aliases od klienta; (c) czy model ma dostawać
"OSOBA_001" czy np. "Pracownik 1" (dziś Rota planuje "Pracownik N" — S2 dotyczy formatu LynxMask).
```

---

## 5. Remanent

**Mapa użycia (graf importów, `where.py` jako surowe trafienia):**
- Ścieżka produkcyjna: `pseudominizer_api.py` → `pipeline.pseudonymize_document` → `pipeline_new.run_pipeline_new` (`USE_NEW_PIPELINE=True`, `pipeline.py:298`) → `layers/*`, `ner_adapter` → `ner_layer` → `spacy_ner`; `anonymizer.py` tylko jako trie (`_layer1_trie`) + walidacja (`_layer4_stdnum`, `_layer5_phonenumbers`) + mapa profilu; `output_guard`; `document_processor` + `ocr_engine`; `db_store`, `audit_log`, `export_pdf`, `smoke_test`, `crypto_selftest`, `seed_profile` (martwy w praktyce, BUG-SEED-DEAD).
- **Martwy kod:** `pipeline.py:366-537` (stary pipeline za flagą) + `_apply_regex_layer`; w `anonymizer.py`: `anonymize()`, `anonymize_with_ner()`, `_layer2_regex`, `_layer3_postal_addresses` (jedyny użytkownik `postal-codes-tools`) — osiągalne tylko ze starej ścieżki; self-testy `test_*()` wewnątrz modułów produkcyjnych (`pipeline_new.py:165+`, `layers/validation.py`, `ner_adapter.py:305+`).
- **Duplikaty:** 9 definicji `TOKEN_RE` (BUG-TOKEN-RE-SPEC); dwie implementacje IBAN (`layers/financial.py` vs Guard); `backend/test_docs/*` = kopie dwóch plików z `Pliki testowe/`.
- **Stare pliki:** `backend/pseudominizer.html` + `backend/index.html` (stary UI webowy; `/` wymaga tokenu → 401, więc `uruchom.vbs` otwiera przeglądarkę na 401); `backend/package.json`, `tsconfig.json`, `package-lock.json` (szkielet z kroku 1); `backend/URUCHOMIENIE.md` (opis „Kroku 1” Tauri — nieaktualny); `backend/python` (pusty plik); `RAPORT_Coverage_Fix.txt`; `MASTER_LynxMask_Desktop.md` / `MAPA_ARCHITEKTURY_…v2_1.md` w `backend/` (ostatnia zmiana 2026-06-27); `gus_simc.zip` (3,3 MB, brak użycia w kodzie [S: grep]); `ocr_testy/` (5,9 MB obrazów). Windows-only: `uruchom.vbs`, `zatrzymaj.vbs`, `init_profile.bat`, `run_*.bat`, `build.bat`, `dev.bat` (są odpowiedniki `.sh`: `build.sh`, `dev.sh`).
- **Docs do aktualizacji:** `PROJEKT_KONTEKST.md` (liczby testów 157/85, „seed_profile podpięty”, wersja API 1.33 vs 1.35, „logi tylko konsola” wobec `uruchom.vbs`, brak informacji o braku requirements); `README.md` OK jako opis portfolio; `CLAUDE.md` — sekcja testów nazywa 3 faile „nie naprawiaj przy okazji”, a są to realne wycieki (to zgłoszenie, nie zmiana); komenda `py -3` nie istnieje na Linuksie (tam `python3`).
- **Długi techniczne:** brak requirements/lockfile; testy HTTP piszą do produkcyjnego profilu i archiwum; `pytest.ini` zbiera tylko wybrane pliki; mojibake w `pipeline.py`; build release niemożliwy (TS + ikony).

---

## 6. Rekomendowana kolejność prac (kandydaci na Taski dla architekta)

| ID | Cel (jedno zdanie) | Pliki | Waga |
|---|---|---|---|
| LYNX-T01-NER-PREFIX | Przestać odrzucać osoby wykryte przez NER po prefiksie z nazw ulic/miejscowości. | `ner_layer.py`, `ner_blocklist.py` | KRYT |
| LYNX-T02-CORS-EXPRESS | Zamknąć dostęp obcych originów i ograniczyć token Express do `/preview-express`. | `pseudominizer_api.py`, `App.tsx` | KRYT |
| LYNX-T03-TOKEN-ALLOC | NER przydziela tokeny przez wspólny alokator; jedna osoba = jeden token, dwie osoby nigdy jeden. | `layers/ner_adapter.py`, `ner_layer.py`, `pipeline_core.py` | KRYT |
| LYNX-T04-SEED (po decyzji OWNERA) | Naprawić import i seed tak, by słownik działał bez FP na słowach pospolitych i bez tokenu per forma. | `anonymizer.py`, `seed_profile.py` | KRYT |
| LYNX-T05-GITIGNORE-REAL | Dodać `backend/preview_real_results/` do `.gitignore`. | `.gitignore` | WYS |
| LYNX-T06-GUARD-BLOCK | Blokada Guarda = brak tekstu do skopiowania; Guard i fail-closed także w Express. | `output_guard.py`, `pipeline.py`, `pipeline_new.py`, `pseudominizer_api.py`, `Pseudonimizuj.tsx`, `ExpressModeScreen.tsx` | WYS |
| LYNX-T07-IBAN-RECEPTA | Wzorzec recepty nie może zjadać IBAN/NRB. | `credential_patterns.json` (+ ew. kolejność w `pipeline_new.py`) | WYS |
| LYNX-T08-TOKEN-RE (decyzja OWNERA, wspólne z Mobile) | Jedna definicja TOKEN_RE zgodna z S2, użyta w detekcji wstrzyknięcia i w Przywracaniu z granicami. | 9 plików z listy BUG-TOKEN-RE-SPEC, `Depseudonimizuj.tsx` | WYS |
| LYNX-T09-LOGS-S5 | Logi bez wartości PII; `uruchom.vbs` bez zapisu wartości na dysk. | `output_guard.py`, `pseudominizer_api.py`, `uruchom.vbs`, `pytest.ini` | WYS |
| LYNX-T10-BUILD | Przywrócić `npm run build` (TS) i ikony RGBA, żeby build release przechodził. | `frontend/src/*`, `src-tauri/icons/*` | WYS |
| LYNX-T11-TEXT-FIDELITY | Pipeline nie zmienia tekstu poza spanami tokenów (sklejanie po kropce, OCR na słowach). | `layers/ner_adapter.py`, `layers/ocr_normalizer.py` | ŚRED |
| LYNX-T12-TEST-ISOLATION | Testy na tymczasowym profilu/archiwum, pytest zbiera wszystkie pliki, naprawić `test_smoke_e2e`. | `backend/tests/*`, `pytest.ini`, `conftest.py` | ŚRED |
| LYNX-T13-ARCHIVE-FLAG | Stan blokady Guarda trzymany po stronie backendu per PSE; `/archive` bez cichego nadpisania. | `pseudominizer_api.py`, `db_store.py`, `Pseudonimizuj.tsx` | ŚRED |
| LYNX-T14-PROFILE-AT-REST (decyzja OWNERA, z planem migracji) | trie i allowlista nie leżą jawnym tekstem, klucz profilu nie leży obok mapy. | `anonymizer.py`, `anonymizer_crypto.py` | ŚRED |
| LYNX-T15-NER-FIRMA-INST | Skróty instytucji w FIRMA tylko wielkimi literami jako całe słowo. | `ner_layer.py` | ŚRED |
| LYNX-T16-REQUIREMENTS | `requirements.txt` z pinami + instrukcja Linux. | `backend/` | ŚRED |
| LYNX-T17-CLEANUP | Usunąć martwą ścieżkę legacy i stare pliki, zaktualizować PROJEKT_KONTEKST. | `pipeline.py`, `anonymizer.py`, `backend/*.html`, docs | NISK |
| LYNX-ROTA-MASK-CORE (po T01, T03) | Bezstanowy `mask/unmask` wg ARCHITECTURE_PROPOSAL 4d + test szczelności w CI. | nowy `backend/lynx_core.py` | — (feature) |

Reproduktory xfail z `backend/tests/test_audyt_2026_10.py` są gotowe dla T01-T03, T05-T08, T11, T15 i AUTH: po naprawie test przejdzie do XPASS (strict), co jest sygnałem do zdjęcia markera w Tasku.
