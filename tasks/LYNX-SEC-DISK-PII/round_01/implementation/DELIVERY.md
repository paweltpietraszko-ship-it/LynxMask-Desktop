# LYNX-SEC-DISK-PII — DELIVERY r1 (CC)

Kod: `9edf0a6` (commity `4e12040` + `9edf0a6`) na brief `f4adf06` (Codex PASS PREIMPLEMENTATION `2a7fc6c`). Gałąź zsynchronizowana z main (`77918d6`).

## F1 — automat profilu tylko w pamięci
- `anonymizer.AnonymizerMap._rebuild_trie`: brak `pickle.dump` i brak zapisu mapy z `update_trie_version`. Automat trafia wyłącznie do `_trie_cache`. `import pickle` usunięty.
- `load_trie`: bez porównania `version`/`trie_version`. To porównanie miało sens tylko przy pliku, a bez zapisu `trie_version` wymuszałoby przebudowę przy każdym wywołaniu. Pole `trie_version` zostaje w mapie jako nieaktywne: wybór CC dopuszczony w prechecku, bez migracji formatu `mapa.enc`.
- **Migracja:** `AnonymizerMap.__init__` usuwa `trie.pkl` i `trie.tmp` z katalogu profilu. Log mówi tylko „Usunięto jawny cache automatu profilu (trie.pkl)”, bez wartości.
- `anonymizer.py` 1577 → 1558 linii.

## F2 — reset usuwa to, co obiecuje, i działa od razu
- `profile_reset` (API) usuwa:
  - mapy sesji `PSE-*.enc` (jak dotąd);
  - `mapa.enc`/`mapa.json` (jak dotąd);
  - **`guard_allowlist.json`** (osobny `PROFILE_DIR`);
  - **`pseudominizer.log`** starego launchera (`_LAUNCHER_LOG`, błąd usunięcia → ostrzeżenie z samym typem);
  - **`db_store.reset_all()`** (nowe): `DELETE documents`, `DELETE audit_log`, `DROP documents_backup_filename` (tabela z nazwami plików z migracji pre-v1.22), `VACUUM`. Stara pętla usuwania rekord po rekordzie zastąpiona przez `reset_all` — plik API bez wzrostu.
- **Odtworzenie `_app_state.anonymizer` razem z `anon_map`.** Wcześniej `anonymizer` zostawał stary, więc warstwa profilu maskowała encjami sprzed resetu, a nowych nie znała. Nowy `AnonymizerMap` sam usuwa stary `trie.pkl` (migracja F1).
- Po resecie w dzienniku jest jedno zdarzenie „reset”, zapisywane jak dotąd po wyczyszczeniu. Wariant z prechecku: usunięcie wcześniejszych zdarzeń i precyzyjny tekst.
- Komunikaty błędów resetu (log i odpowiedź) bez treści wyjątku.
- `SecurityScreen.tsx`: „Zostanie usunięty słownik biura, wyjątki „to nie PII”, całe archiwum dokumentów, dziennik zdarzeń i plik logu silnika.”

## F3 — logi bez wartości na każdym poziomie; launcher bez pliku
- **Usunięte wartości:**

  | Plik | Co było w logu |
  |---|---|
  | `ocr_engine.py` | nazwa pliku w błędzie i w logu sukcesu `[OCR] {filename}: N słów` |
  | `export_pdf.py` | `title=` |
  | API | fraza allowlisty → długość; treść `extract_err`; `{e}` w add_entity, export-pdf (także odpowiedź), reset |
  | `ner_layer.py` | 11× `[FILTER]` i 4× `[NER]` debug z `entity_text` → długość / token |
  | `spacy_ner.py` | debug encji |
  | `pipeline.py` (stary łańcuch, tylko linie logów) | 3× FIX-NER, ADDR, `_apply_regex_layer`, 4× treść wyjątku |
  | `anonymizer.py` | `[STDNUM-L4]` z wartością, 2× treść wyjątku |
  | `anonymizer_crypto.py` | ścieżka keystore (nazwa konta) |
  | `output_guard.py` | fraza injekcji |
  | `verbal_amounts.py` | kwota słowna, wyjątek |

- `uruchom.vbs` v1.4: bez przekierowania `>> pseudominizer.log`. Stary plik usuwany przy starcie. `cmd /k`, żeby okno z komunikatem zostało po awarii.
- **ROZSZERZENIE CC** (w briefie): `anonymizer_crypto.py`, `output_guard.py`, `verbal_amounts.py` dopisane do TASK_SCOPE. Ta sama klasa, znalezione przeglądem wszystkich wywołań, także wieloliniowych.

## Testy
- **Nowy `tests/test_disk_pii.py`** (5 testów). Izolacja: profil, osobny `PROFILE_DIR`, archiwum, rejestr, `HARDWARE_PROFILE`, `_LAUNCHER_LOG`. Uwaga Codexa o incydencie izolacji z r1 uwzględniona.
  - **F1:** po `/profile/add-entity` żaden plik profilu nie zawiera nazwiska, a `trie.pkl` nie istnieje. Maskowanie odmiany („Jana Kowalskiego”) działa, także w nowej instancji z dysku („restart”).
  - **F1 migracja:** syntetyczny stary `trie.pkl` → po wczytaniu profilu go nie ma, a maskowanie działa.
  - **F2:** encja, wyjątek allowlisty, stary `trie.pkl`, log launchera, rekord archiwum, zdarzenie audytu i tabela `documents_backup_filename` ze znacznikiem, potem reset (200). Wyniki:
    - żaden plik pod katalogiem testu nie zawiera znacznika ani nazwiska;
    - plików nie ma — brak usuniętej allowlisty to sukces, a nie `FileNotFoundError`;
    - tabeli nie ma, `documents` puste, dziennik = `["reset"]`;
    - **warstwa profilu** (`_layer1_trie`, izolowany właściciel profilu, nie NER) nie maskuje już starej encji, a encja dodana po resecie jest maskowana.
  - **F3:** wszystkie loggery na DEBUG. Wywołania: add-entity, `/preview` TXT, `/preview` **prawdziwy PNG z OCR (Tesseract)**, `/export-pdf`, allowlista, reset — wszystkie z nazwami plików i wartościami zawierającymi znacznik. W logu nie ma znacznika, nazwiska, PESEL ani nazwy firmy, a log nie jest pusty.
  - **Launcher:** brak `>>` i `strLog` w poleceniu startu; usuwanie starego logu.
- **RED na kodzie z main** (ten sam test, `raising=False` dla nowego atrybutu): **5/5 failed**. Każdy pokazuje opisaną usterkę: `trie.pkl` istnieje; po resecie znacznik w `trie.pkl`; w logu `[OCR] Skan_…png`, `title='Pozew_…'`, `[GUARD-ALLOWLIST] Dodano: '…'`; vbs z `>>`. **GREEN: 5 passed.**
- **Regresje:**

  | Zestaw | Wynik |
  |---|---|
  | `test_disk_pii`, `test_failclosed`, `test_startup_check` (próba „profil biura” na izolowanym profilu), `test_express_one_engine`, `test_layers`, `test_ner_multiline`, `test_map_fidelity`, `test_audyt_2026_10` | **341 passed, 7 xfailed** |
  | `test_archive_adversarial` (z `test_disk_pii`) | 24 passed |
  | `tests/` na backendzie gałęzi | **167 passed, 2 skipped, 1 xfailed** |
  | `tsc --noEmit` | 0 |

- **Prawdziwy start z profilem Pawła** (zapowiedziana zmiana na jego profilu): log „Usunięto jawny cache automatu profilu (trie.pkl)”, próby startowe OK. Porównanie plików (SHA256, rozmiar, mtime):

  | Plik | Wynik |
  |---|---|
  | `mapa.enc` | bez zmian |
  | `triangulum_keystore.bin` | bez zmian |
  | `hardware_profile.json` | bez zmian |
  | **`trie.pkl`** | **usunięty** |

- **178 dok. `dataset_real_public` przez `/preview` z profilem Pawła:** gałąź vs main → **0 różnic** (wynik, tokeny, blokady, kody), 59 blokad jak wcześniej.

## Rozmiar
- Gate (dosłownie, bez list):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 9edf0a6ecdd514bda3bcf7f26753e5135a017732
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 362 lines changed (threshold 150)
```
- Produkcja: +91/−97 (netto −6). Test: 174 linie. Szacunek zaakceptowany przez Pawła: +60/−50 i test ok. 150. Wyszło więcej, bo rozszerzenie F3 objęło 3 dodatkowe moduły i wieloliniowe logi, a test sprawdza też OCR i PDF.
- Pliki legacy: `pseudominizer_api.py` 1060 → 1054 (pierwsza wersja dawała 1069, uproszczona przez `reset_all`), `anonymizer.py` 1577 → 1558.

## Uwagi
- `pseudominizer.log` z historycznych uruchomień: launcher v1.4 usuwa go przy starcie, a reset też go usuwa. Jeśli działa stary launcher (v1.3) z otwartym plikiem, reset zapisze ostrzeżenie i plik zostanie do następnego startu nowym launcherem.
- `run_review_r1.py` Codexa nie był zmieniany (dowód historyczny RED). Jego końcowy `read_bytes()` usuniętej allowlisty po poprawce może rzucić `FileNotFoundError`, co jest zgodne z prechecku.
- Poza zakresem bez zmian: R1 (wymóg zapisany w `LYNX-LAYOUT-COPY`), R2 zależności, szyfrowanie allowlisty, `api_token.txt`, OneDrive.
