# LYNX-PHOTO-CHAIN — DELIVERY r1 (CC, 2026-10-20)

Brief `08a8d528c6ccdd471f376142bba41a57008ceb03`, recenzja CC `5cc5b6f40e2dcf21f254d300c2496e29b19571a2` (= BEFORE dla gate).
HEAD implementacji: `df612f7c6257a25e6de122c478a05d1c41e50353` (gałąź `task/LYNX-PHOTO-CHAIN`, zawiera main `2c9fdb9`).
Flaga `LYNX_OCR_ENGINE=rapid` — **domyślnie OFF**; bez flagi ścieżka Tesseracta bez zmian. Aktywacja i progi — decyzja OWNERA;
aktywacja dla użytkowników zależy też od `LYNX-INSTALLER` (modele dostarcza instalator, bez ręcznych kroków — uwaga OWNERA 20.10).

## Gate (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: df612f7c6257a25e6de122c478a05d1c41e50353
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 559 lines changed (threshold 150)
```
Rozmiar: +457/−102 (produkt +254/−51 w 7 plikach, testy +218/−51). Zgoda OWNERA 20.10 dotyczyła ~370 l. dodanych; przekroczenie
~+90 l. = bezpiecznik dławienia Windows i limit wątków (uzgodnione z OWNEREM w trakcie, niżej) + testy do nich. Pełny raport gate:
`round_01/implementation/gate.txt`.

## Co zrobione (pliki z TASK_SCOPE)
- `backend/photo_chain.py` (nowy, 136 l.): dekodowanie (z EXIF) → `PP-LCNet_x1_0_doc_ori` (SHA256 `5dcaf4e3…37f5`, miniatura 224,
  preprocessing jak `inference.yml`; model zwraca prawdopodobieństwa) → obrót pełnej rozdzielczości → `ocr_rapid.recognize` →
  udział słów ≥3-literowych znanych Morfeuszowi → `ok` albo odmowa (`ORIENTATION_UNCERTAIN` / `QUALITY_UNEVALUABLE` (<5 słów) /
  `QUALITY_LOW`). Przy niepewnej orientacji PP w ogóle nie czyta. Awaria techniczna → kod (`PP_FAILURE`/`PP_TIMEOUT`) → jednorazowo
  Tesseract z jego bramką (`reason` w metadanych). Słaby odczyt PP nigdy nie idzie do Tesseracta. Odmowa: tekst pusty, komunikat
  z briefu, bez liczb.
- `backend/ocr_rapid.py`: modele w `backend/models/ocr/` (względem silnika; `LYNX_OCR_MODEL_DIR` nadpisuje) z weryfikacją SHA256,
  telemetria ONNX wyłączona, po przekroczeniu czasu PP wyłączony do restartu (bez nowych zadań w zawieszonym wykonawcy), limit wątków
  ONNX; usunięty wartownik C1 fazy A (`extract_rapid`, `C1_WARNING`).
- `backend/ocr_engine.py` (+`OCRResult.reason`), `backend/document_processor.py` (`reason` w `ocr_meta`, funkcja nie urosła).
- `backend/startup_check.py`: `keep_full_speed()` — patrz „Wydajność”. Nie blokuje startu; żadnej nowej próby blokującej (brak PP =
  zapas Tesseract, nie zablokowany program — recenzja CC pkt 2).
- `frontend/src/screens/Pseudonimizuj.tsx`: odmowa zdjęcia rozpoznawana także jako 400 z `ocr.quality="reject"` (odmowa PP nie
  przekazuje tekstu do API, więc trafia do ścieżki błędu ekstrakcji, nie do 422 — `pseudominizer_api.py` poza zakresem); przycisk
  „Wklej tekst” ustawia kursor w istniejącym polu; brak procentu pewności dla `engine="rapid"`. `npx tsc --noEmit` OK.
- `.gitignore`: `backend/models/`. `tauri.conf.json`, `README.md` nietknięte (bez instrukcji ręcznej instalacji).

## Testy
- `py -3 -m pytest tests/test_photo_chain.py tests/test_ocr_rapid.py -q` → **31 passed** (z lokalnymi modelami i
  `LYNX_SYNTH_DIR`=syntetyki 27.06; bez nich 1 skip). Pokrycie §3.1 briefu: 4 orientacje (jeden odczyt PP, wyprostowany obraz), EXIF
  bez podwójnego obrotu (ta sama tablica dla modelu i PP), granice progów i remis klasyfikatora, słaby/krótki/pusty odczyt bez
  Tesseracta, odmowa bez tekstu i z alternatywą, awaria → Tesseract raz bez treści i nazwy pliku w logach, timeout + 3 kolejne
  requesty < 0,5 s i bez nowych zadań, zły hash / brak modelu bez pobierania, domyślnie Tesseract bez importu łańcucha/onnxruntime,
  katalog modeli przy silniku, **prawdziwe modele z blokadą połączeń wychodzących** (mapa klas 0/90/180/270 + odczyt), limit wątków,
  wyłączenie dławienia.
- Pełna suita main `2c9fdb9` vs gałąź: identycznie `30 failed, 137 passed, 2 skipped, 1 xfailed` (porażki istniejące, niezależne).
- **Strażnik `benchmark.py` — nie uruchomiony (świadomie):** wymaga portu 8765, na którym chodzi silnik deweloperski OWNERA; przy
  fladze OFF ścieżka Tesseracta różni się od main jedną linią (`result.reason = ""`), warstwy maskowania nietknięte. Do decyzji
  Codexa, czy wymaga.

## Pomiar odbioru (§3) — `tasks/LYNX-PHOTO-CHAIN/measure/photo_measure.py`
Odtworzenie (Codex lokalnie, modele w `backend/models/ocr/` jak niżej, raport poza repo):
```
py -3 tasks/LYNX-PHOTO-CHAIN/measure/photo_measure.py --steps thresholds --known backend/dataset_20260627_095419 --real <zdjęcia> --out <json>
py -3 tasks/LYNX-PHOTO-CHAIN/measure/photo_measure.py --steps sizes --known backend/dataset_20260627_095419 --out <json>
py -3 tasks/LYNX-PHOTO-CHAIN/measure/photo_measure.py --steps e2e --sha df612f7c6257a25e6de122c478a05d1c41e50353 --rapid \
   --models <abs. ścieżka Windows do backend/models/ocr> --env LYNX_PHOTO_DICT_MIN=0.60 --set backend/dataset_20261016_fresh \
   --name branch_holdout --rotations 0 --protect <katalog backend OWNERA> --out <json>
```
Modele: det `090f04ab…f94f`, rec `6f327246…4884`, cls `e47acedf…215c` (z pakietu `rapidocr`), orientacja `5dcaf4e3…37f5`
(konwersja ONNX `PP-LCNet_x1_0_doc_ori`; u CC `~/lynx_models/doc_ori/a_marsena.onnx`). E2E = jednorazowa kopia `git archive`,
TestClient, pusty profil, izolacja migawką: `startup=OK isolation=OK changed_paths=0` w obu przebiegach.

**Progi (wybrane na ZNANYM 50, przed zbiorem 100):** orientacja 200/200 poprawnie (0/90/180/270), min. pewność 0,846 → próg
**0,60** z zapasem. Udział słownikowy na odczycie PP: L0 min 0,872, L1 0,857, L2 0,613, L3 0,763; odmowy znanych 50 przy progu
0,80 = 7 (L2 4, L3 3), 0,65–0,75 = 2 (L2), ≤0,60 = 0 → kandydat **0,60** (kandydat briefu 0,80 odrzucał poprawne dokumenty).
Minimalnie 32 słowa na stronie syntetycznej. Realne zdjęcia OWNERA (8, tylko agregaty): orientacja 0,83–0,93 + jedno złe 0,35;
udział 0,79–0,91 dla dobrych, **0,28 dla formularza wypełnionego ręcznie** (PP nie czyta pisma odręcznego — odmowa właściwa).
Przy 0,60/0,60: 6/8 przyjęte, odmowy: złe zdjęcie (orientacja) i formularz odręczny (jakość). Plik do oceny okiem OWNERA — lokalnie. **Oko OWNERA 20.10: wyprostowanie poprawne na wszystkich poza nr 4** (złe zdjęcie, odmowa); ocena czytelności przyjętych — w toku (plik powiększony).
**Progi czekają na aprobatę OWNERA.**

**E2E, prawdziwy `/preview` z obrazem, gałąź z flagą, progi 0,60/0,60:**
| zbiór | dok. | przyjęte / odmowy / awarie | silnik | dziury kryt. | dziury niekryt. (mech.) | UNKNOWN | NOT_IN_OCR | would_ask med/max | czas /preview med / p95 | RSS max |
|---|---|---|---|---|---|---|---|---|---|---|
| znany 50 | 50 | 50 / 0 / 0 | rapid 50 | **0** (126 kryt. zakrytych) | 3 | 5 | 3 | 9,5 / 35 | 1,28 s / 1,60 s | 1529 MB |
| kontrolny 100 | 100 | 99 / 1 (L2, z alternatywą) / 0 | rapid 100 | **0** (207 zakrytych, 1 ASKED) | 9 | 1 | 11 | 10 / 31 | 1,53 s / 2,68 s | 1632 MB |
L0 odrzucone: 0 w obu. Odmowy bez instrukcji: 0. Blokady obecnego Guarda: 0. `would_ask` hipotetyczne (GUARD-RESIDUE niewdrożony).
Zbiór 100 był używany historycznie — to nie świeży holdout.

**Przegląd wszystkich HOLE/UNKNOWN (syntetyki, wartości tylko lokalnie):** 0 prawdziwych dziur.
- Znany 50 (8): 3× numer umowy zakryty (`nr NUMER_005`), miarka liczy słowo „UMOWA” z tytułu jako fragment `UMOWA/…/NR/…`;
  3× adres/sygnatura bez jawnego fragmentu (zakryte, inny zapis OCR niż oryginał w mapie); 1× data urodzenia (dowód = „19” z działki);
  1× numer działki: zakryty, za tokenem zostaje końcówka „/19” (nieidentyfikujący fragment).
- Kontrolny 100 (10): 3× numer umowy jak wyżej; 3× sygnatura administracyjna/akt — dowód to rok „2023” z cytatu „Dz. U. z 2023 r.”;
  1× adres — dowód to nazwa sądu „Wrocławia-Fabrycznej” (polityka: samo miasto nie jest maskowane); 3× sygnatura akt zakryta, ale
  rok z sygnatury zostaje za tokenem (`NUMER_004/2019`, `NUMER_004 18`) — nieidentyfikujący fragment.
- **17 UNKNOWN z GATE-COMPARE (`dataset_clean`, main):** 7× nazwisko „oskarżonego” bez jawnego fragmentu (zakryte; miarka nie
  dopasowuje odmiany do mapy), 7× PESEL/dowód/NIP/paszport/IBAN/data zakryte (dowód miarki = pojedyncza cyfra „5”/„19” albo słowo
  „Zleceniobiorca” dopasowane rozmyto), 3× numer działki zakryty z końcówką „/5”, „/19” za tokenem. Skrypt: lokalny przegląd przez
  funkcje `chain_compare.value_status`/`evidence` na tej samej kopii backendu.
- **FINDING (inna klasa, nie naprawiane — do `LYNX-ENGINE-BACKLOG`):** końcówki numerów działek („/19”) i rok sygnatury po OCR
  („/2019”) zostają za tokenem — nieidentyfikujące, ale niepełne pokrycie wartości.

## Wydajność (§3.3, §3.6) — znalezione i naprawione w Tasku za zgodą OWNERA 20.10
- **Windows 11 dławi proces w tle bez okna (EcoQoS)** — silnik uruchamiany `LynxMask.vbs` jest takim procesem. Dowód: czyste
  mnożenie macierzy 0,34 s → 1,43 s po ~3 s pracy; z wyłączonym dławieniem 0,36–0,7 s. PP: 7–8 s/str. → 2,2–3,8 s. Tesseract to
  omijał, bo startuje jako nowy proces przy każdym zdjęciu. Naprawa: `startup_check.keep_full_speed()` (`SetProcessInformation`,
  ProcessPowerThrottling, tylko dla procesu silnika; poza Windows no-op). Dotyczy całego silnika (spaCy, przyszły HerBERT).
- **Wątki ONNX** (bez dławienia; syntetyki / zdjęcia 16 MP / średnie CPU): wszystkie 24 → 1,7–2,2 s / 4,0–6,2 s / 84%; 4 → 1,2–1,6 /
  2,8–4,7 / 31%; **6 → 1,0–1,4 / 2,4–4,0 / 47%**; 8 → 1,3–1,6 / 2,4–3,8 / 56%. Limit: `min(6, max(2, logiczne // 4))`,
  `LYNX_OCR_THREADS` nadpisuje.
- **Zmniejszanie obrazu przed PP — odrzucone pomiarem:** syntetyki gold w odczycie 310/342 (pełna) → 307 (1600 px) → 296 (1400) →
  290 (1200) → 270 (1000) przy zysku 2,7 → 2,0 s; zdjęcia OWNERA 4,4 → 4,0 s przy 2000 px. Czas zależy od ilości tekstu, nie pikseli.
- Cel ≤3 s/str.: syntetyki spełniony (E2E mediana 1,3–1,5 s, p95 ≤2,7 s); zdjęcia 16 MP z telefonu 2,4–4,0 s — **czasem powyżej celu**.
  Zimny start PP (pierwsze zdjęcie) +~0,5 s. Pomiar na i7 OWNERA (24 wątki); maszyny biurowe — ocena w `LYNX-INSTALLER`.

## Odstępstwa od briefu (jawnie)
- Pełny E2E tylko w pozycji 0° na 50 i 100 (bez obrotów 90/180/270 i bez przebiegu main): po wyprostowaniu obraz jest piksel w piksel
  identyczny z prostym; prostowanie sprawdzone osobno (200/200, krok `thresholds`), pełny `/preview` z obrazem obróconym o 90° —
  próba na 3 dokumentach (przyjęte, `rapid`). Main/Tesseract odrzucony wcześniejszymi pomiarami (`LYNX-OCR-PARITY`, `GATE-COMPARE`);
  OWNER 20.10: „po co stary czytnik, on już jest skreślony”.
- Pakowanie modeli i test instalacyjny na czystej maszynie → `LYNX-INSTALLER` (instalator Tauri nie pakuje silnika).
- Odmowa PP dociera do UI jako 400 z `ocr.quality="reject"`, nie 422 `ocr_rejected` (API poza zakresem; tekst nie opuszcza silnika).

## Do Codexa
Audyt exact SHA `df612f7c6257a25e6de122c478a05d1c41e50353`: kod (S3/S5, fallback jednorazowy, timeout, SHA, offline, UI) i
odtworzenie pomiaru wg poleceń wyżej (modele: skopiuj 3 pliki z `site-packages/rapidocr/models/` i plik orientacji do
`backend/models/ocr/` — SHA w kodzie). Po audycie: OWNER — aprobata progów 0,60/0,60 i decyzja o merge (flaga OFF).
