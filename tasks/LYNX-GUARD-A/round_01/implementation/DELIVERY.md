# DELIVERY — LYNX-GUARD-A (etap A Guarda), CC 22.10.2026

Gałąź `task/LYNX-GUARD-A`, baza `94a7954` (S4 zamrożone przez Architekta), HEAD `6469503`. Brief: `tasks/LYNX-GUARD-A/brief.md`.

## gate.py (dosłownie, `round_01/gate_r3.txt`)
```
STATUS: WYMAGA_DECYZJI
WYMAGA_DECYZJI:
  - RATIO: 337/40 = 8.4:1 (threshold 5:1)
  - TOTAL_LINES: 377 lines changed (threshold 150)
```
Oba punkty to rozmiar; OWNER zgodził się na koszt etapu A 22.10 (BOARD, wiersz LYNX-GUARD-RESIDUE). Pozostałe sprawdzenia bez uwag
(RUFF: `pseudominizer_api.py` 6 → 6 dzięki `noqa: E402` przy nowym imporcie; rozmiary plików/funkcji nie rosną).

## Zmiany
- `backend/guard_residue.py` (nowy, 237 l.): `collect_warnings` — HIGH/MEDIUM/MAP_LEAK jako ostrzeżenia RED/YELLOW + R1–R5; dedup nachodzących; nic w tokenach; allowlista tylko odczyt.
- `backend/pipeline.py`: `_apply_output_guard` bez `[REDACTED]` i bez `guard_blocked` z Guarda; `guard_warnings` w wyniku; S3 bez zmian.
- `backend/pseudominizer_api.py`: `guard_warnings` w `/preview` (pozycje względem `anonymized_preview`), plik bez wzrostu.
- `frontend/src/screens/Pseudonimizuj.tsx` (zgodność do etapu B, bez wzrostu): ostrzeżenia ustawiają dotychczasową blokadę zapisu/kopii, panel listuje fragmenty. `tsc --noEmit` exit 0.

## Testy
- `tests/test_guard_residue.py` + `tests/test_failclosed.py`: **56 passed**.
- Importerzy zmienionych modułów (lista z gate), plik po pliku: `test_addr_email_leaks` 22, `test_archive_adversarial` 19, `test_disk_pii` 6,
  `test_express_one_engine` 6, `test_map_fidelity` 29, `test_ner_multiline` 21, `test_ocr_chain_compare` 52, `test_pipeline_v2` 41,
  `test_startup_check` 17, `test_text_limit_15k` 7, `test_token_re_spec` 18 — wszystkie passed.
- Faile **identyczne na bazie `94a7954`** (sprawdzone w osobnym worktree): `test_audyt_2026_10` 2 (Komornik Sądowy, ul. Kowalskiego),
  `test_layers` 2 (TestFirmaBounds, forma prawna S.A.), `test_engine_quality_layout` 7 failed/8 passed na obu — poza zakresem, do ENGINE-BACKLOG.
- Uruchomienie wszystkich naraz w jednym procesie kończy się segfaultem (natywne biblioteki) — uruchamiać plik po pliku.

## Pomiar zalewu ostrzeżeń (pomocnik CC + CC)
Zbiory `backend/dataset_20261016_fresh` (100) i `dataset_20260627_095419` (50) — obrazy, OCR silnika, pusty profil.
Skrypty i wyniki lokalnie: `%TEMP%\lynx_cc_review\guard_a\` (`run.py` OCR+silnik → `results.json`; `rerun_cc.py <wt>/backend` liczy ostrzeżenia
na zapisanych tekstach; `kpwr_guard.py <wt>/backend` — KPWr).
- Pierwsza wersja: 277 ostrzeżeń / 150 dok. (śr. 1,85, maks 14); R1 = 94% i w 91% śmieci (nazwy urzędów 102, szum OCR 47, miasta 30,
  „Pana” 26, role umowy 22). R4 10/10 trafnych.
- Po zawężeniu R1 (ciąg nazwy instytucji, Pan/Pani, „zwanym dalej”, słowo nieznane Morfeuszowi tylko z końcówką nazwiska, złożenia
  geograficzne) i R3 (cyfra daty po „dnia”, „4” = OCR „ul.”): **25 ostrzeżeń / 150 dok., śr. 0,17, mediana 0, maks 3, 130 dok. bez ostrzeżeń**
  (R1 14, R3 9, R4 10).
- Koszt zawężenia: z 19 trafnych R1 pierwszej wersji zostaje ok. 6 (np. „Pawtowska”, „Ogrowski”, „Dębowa”); odpadły słowa zniekształcone
  przez OCR bez końcówki nazwiska („Fetr Nowack”) i resztki adresów (te to braki silnika ADRES, nie Guarda).
- KPWr (75 tekstów, proza): 1,88 ostrzeżenia/tekst; z 33 jawnych słów nazw osób Guard wskazuje 17. Niewskazane: pseudonimy i obce imiona
  (Olo, Ciacho, Yochai, Whitehurst), nazwisko będące przymiotnikiem („Szpiegowski”).
- R2 i R5 bez trafień na zbiorach obrazów (brak takich przypadków) — pokryte testami jednostkowymi.

## Uwagi dla audytu
- **Etapu A nie scalać bez B**: A zostawia stary zbiorczy „To nie PII — zapisz mimo to” (B go usuwa).
- MAP_LEAK nadal korzysta z istniejącej allowlisty (tylko odczyt); nowy kod jej nie zapisuje (S5).
- Wartości fragmentów są w odpowiedzi `/preview` (dla UI), nie w logach — log tylko liczba ostrzeżeń.
