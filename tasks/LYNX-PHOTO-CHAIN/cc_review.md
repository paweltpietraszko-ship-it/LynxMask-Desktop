# LYNX-PHOTO-CHAIN — recenzja briefu i szacunek CC (2026-10-20)

Brief `08a8d528c6ccdd471f376142bba41a57008ceb03`, precheck Codexa r1 `4d0592a` (PASS PREIMPLEMENTATION).
Gałąź zaktualizowana do main `d5de2bd` (merge GATE-COMPARE `9d45115`). WHERE_MAP wykonany (`where.py` dla 4 celów briefu):
jedyny importer produkcyjny `extract_text_from_image` to `document_processor._extract_text`; jedyny importer `extract_rapid` to
`ocr_engine.extract_text_from_image`; `_extract_text` poza produkcją używa tylko `audyt/bench_offline.py`.

## Werdykt CC: przyjmuję brief, z trzema korektami wykonawczymi (bez zmiany kontraktu)

1. **Pakowanie — `tauri.conf.json` nie jest właścicielem modeli.** Instalator Tauri zawiera wyłącznie front (`bundle` bez `resources`);
   silnik Python startuje z katalogu repo przez `LynxMask.vbs` (`py -3 pseudominizer_api.py`), a pakowanie silnika to zaległość
   `LYNX-APP-LAUNCHER`. Wykonanie wymagania briefu „nie zakładać `~/lynx_models`”: domyślny katalog modeli = `backend/models/`
   (względem kodu, nie katalogu domowego), pliki niewersjonowane w git (~37 MB), lista SHA256 w kodzie, krok instalacyjny w `README.md`
   (modele det/rec/cls z pakietu `rapidocr`, model orientacji z przypiętego źródła — pobranie tylko przy instalacji, nigdy w trakcie pracy).
   Brak pliku / zły hash → PP niedostępny → Tesseract (zapas techniczny). „Test instalacyjny” = uruchomienie bez `LYNX_OCR_MODEL_DIR`
   i bez `~/lynx_models`. **TASK_SCOPE: dopisany `README.md`** (zgodnie z §4 briefu: zgłoszenie przed pracą); `tauri.conf.json` nietknięty.
2. **`startup_check.py` — bez blokady startu.** Każda nieudana próba w `_CHECKS` blokuje start silnika, a brak PP ma oznaczać zapas
   Tesseract, nie zablokowany program. Weryfikacja SHA przy pierwszym załadowaniu modelu (leniwie, w `ocr_rapid`/`photo_chain`) spełnia
   wymaganie „naruszenie hasha = PP niedostępny”; `startup_check.py` zostaje w TASK_SCOPE, ale planuję go nie zmieniać (redukcja).
   Koszt: zimny start pierwszego zdjęcia (~1–2 s) — zmierzę i pokażę osobno, jak wymaga §3.3.
3. **Pomiar E2E bez drugiego portu.** `_ALLOWED_HOSTS` w API przyjmuje tylko `:8765`, a silnik 8765 działa z profilem OWNERA. Integracja
   „prawdziwy `/preview` z obrazem” = ten sam kod API w procesie (klient testowy FastAPI, nagłówek Host `127.0.0.1:8765`) z izolowanym
   profilem tymczasowym i flagą włączoną, porównanie z tym samym na `main`. Bez ruszania serwera 8765 i bez profilu OWNERA.

## Uwagi merytoryczne (do pomiaru, nie do zmiany briefu)
- **Próg słownikowy 0,80 prawdopodobnie za wysoki.** Moje wcześniejsze pomiary (cc_proposal §2): syntetyki min 0,53, dobre zdjęcia realne
  0,79–0,91, złe 0,33. Przy 0,80 część poprawnych dokumentów dostałaby odmowę. Wartość wyznaczę rozkładem na znanym 50 (L0–L3, także
  obrócone) + 8 zdjęciach realnych; jeśli żadna granica nie oddziela złych od dobrych bez fałszywych odmów L0 — `NOT_READY`, jak w briefie.
- Minimum 5 słów: krótkie poprawne zdjęcie (np. kartka z 3–4 słowami) dostanie odmowę „wklej tekst” — raportuję liczbę takich przypadków.
- Morfeusz w `photo_chain`: przez bezpośredni `morfeusz2` jak `ner_layer.py` (bez przekazywania stanu przez `document_processor`).
- Odmowa: tekst komunikatu z briefu idzie przez istniejące `warning_msg` → 422 `ocr_rejected`; front dokłada przycisk „Wklej tekst”
  przełączający na istniejące pole; procent pewności pokazywany tylko dla Tesseracta. Log w `pseudominizer_api.py` (poza scope) wypisze
  `conf=0.0` przy odmowie PP — mylące, ale bez treści (S5 zachowane); zgłaszam, nie poprawiam.

## Szacunek rozmiaru (po redukcji)
| plik | zmiana |
|---|---|
| `backend/photo_chain.py` (nowy) | ~140 l. — orientacja (ONNX, SHA, miniatura, mapa klas), obrót pełnej rozdzielczości po EXIF, bramka słownikowa, decyzja ok/reject |
| `backend/ocr_rapid.py` | ~+30/−10 — wejście jako obraz, bezpiecznik `UNAVAILABLE_UNTIL_RESTART` po timeout, SHA, telemetria ONNX off, usunięcie wartownika C1 |
| `backend/ocr_engine.py` | ~+6/−4 — wywołanie łańcucha zamiast fazy A (plik 483 l., pod limitem) |
| `backend/document_processor.py` | ~+2 — kod przyczyny w `ocr_meta` |
| `frontend/src/screens/Pseudonimizuj.tsx` | ~+15 — przycisk „Wklej tekst”, brak procentu dla PP |
| `README.md` | ~+12 — instalacja modeli, SHA, licencje (Apache-2.0) |
| testy (`test_photo_chain.py` nowy, `test_ocr_rapid.py`) | ~+170/−30 |
| **razem** | **~200 l. kodu produktu + ~170 l. testów ≈ 370 l.** (powyżej 150 → zgoda OWNERA przed kodem) |

Narzędzie pomiaru E2E i raport UNKNOWN — w `tasks/LYNX-PHOTO-CHAIN/` (poza produktem). Flaga domyślnie OFF: bez zgody OWNERA na progi
użytkownik nie widzi zmiany.

## Prośba do OWNERA
Zgoda na rozmiar (~370 l. z testami) i na zachowanie widoczne po aktywacji: komunikat odmowy z briefu + przycisk „Wklej tekst”, brak
procentu pewności przy nowym czytniku. Progi zatwierdzasz osobno, po pomiarze.
