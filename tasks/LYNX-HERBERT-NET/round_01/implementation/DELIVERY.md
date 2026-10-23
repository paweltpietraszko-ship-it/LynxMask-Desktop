# LYNX-HERBERT-NET — DELIVERY r1 (CC, 2026-10-21)

Brief v2 `f69bc02` (+ TASK_SCOPE CC `455d142` = BEFORE), Codex precheck PASS `12781a2`. HEAD `7401ec3471145d232f62fbbc5e1a41a1303ee019`.
Budżet: zgoda Pawła 21.10 do 350 l. z testami — wykorzystane 281 (limit nie wymusił kompromisu w działaniu).

## Gate (dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 7401ec3471145d232f62fbbc5e1a41a1303ee019
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 280/1 = 280.0:1 (threshold 5:1)
  - TOTAL_LINES: 281 lines changed (threshold 150)
```

## Implementacja
- `backend/herbert_net.py` (142 l.): ONNX + `tokenizers`, SHA256 trzech plików, telemetria ONNX off, wątki = `ocr_rapid.THREADS`; okna 800 zn.
  z zakładką 200, okno > 512 subtokenów dzielone (bez obcięcia); PER→OSOBA, ORG→FIRMA tylko na spanach w całości jawnych, przez
  `ner_layer._filter_institutions`; spany przecinające token pomijane i liczone (log `przecinające_token`); tokeny tylko w mapie
  dokumentu, numer powyżej najwyższego w dokumencie i profilu (bez zapisu do profilu), ta sama wartość = ten sam token.
  `LYNX_HERBERT=off` (domyślnie) | PER | ORG | PER,ORG; próg `LYNX_HERBERT_MIN` domyślnie **0,7** (kalibracja niżej).
- `backend/pipeline.py`: `_apply_guard` = S3 force_block → siatka → `_apply_output_guard` (dotychczasowe ciało, bez zmian). Wyjątek siatki → S3.
- `backend/startup_check.py`: próba „dodatkowa kontrola HerBERT” (tylko gdy włączona). `requirements.txt`: `tokenizers==0.22.2`.
  `README.md`: atrybucja CC BY 4.0.
- Odstępstwo: dedykowany komunikat awarii HerBERT nie dociera do UI — API (poza zakresem) zwraca stały komunikat S3 z alternatywą.
- Znane ograniczenia (zgodnie z briefem): odziedziczony filtr prefiksów odrzuca część firm („Piekarnia…”, „Przedsiębiorstwo…”);
  „Nazwa Sp. FIRMA_001” = PARTIAL_FIRMA_UNFIXED — naprawiane osobno w `LYNX-FIRMA-FILTER-FIX`.

## Testy
`tests/test_herbert_net.py` 8 passed (atrapa + prawdziwy model offline z blokadą sieci, długi tekst bez obcięcia); `test_startup_check.py`,
`test_photo_chain.py` bez zmian (42 passed). Ruff: 2 uwagi w `pipeline.py` istniejące przed zmianą.

## Pomiar (pomocnik CC; skrypt `tasks/LYNX-HERBERT-NET/measure/herbert_measure.py` — ścieżki lokalne CC; wyniki `%TEMP%\lynx_cc_review\herbert_net\`)
ZNANY = dataset_clean 0–149 + firma_sweep 160; KONTROLNY = dataset_clean 150–299, 48 obrazów, testy Mobile. Pusty profil, `/preview` w procesie.
- **OFF = main:** 499 dokumentów tekstowych bajt w bajt identyczne (poza numerem PSE).
- **Kalibracja (ZNANY, PER,ORG):** MIN 0,3/0,5/0,7/0,9 → dołożone FIRMA 65/65/62/54, nadmaskowanie 9/9/6/3, sweep jawnych 10/10/10/13;
  dołożone OSOBA = 0 przy każdym progu. Wybór **0,7** zapisany przed kontrolnym.
- **KONTROLNY (0,7):** PER — 1 dołożone (zysk: nazwisko po zakrytym imieniu), 0 nadmaskowania; ORG — 22 dołożone: **4 firmy (zysk)**,
  **17 instytucji publicznych** (filtr nie łapie: „Urząd Miejski w Krakowie”, „Spraw Administracyjnych”, „Sądowy przy SR dla…”,
  „Urząd Marszałkowski…”, „Urząd Regulacji Energetyki”), 1 fragment formy prawnej. Firmy (gold z tekstu): jawne 21→19, zakryte 7→9.
  ZNANY: firma_sweep jawne 64→10. Kolizje 0, stare tokeny nietknięte, podstawienie dołożonych tokenów = OFF (0 niezgodności), Guard OFF=ON.
- **Koszt:** tekst 29→67 ms mediana, obrazy 1,25→1,32 s; RAM +~200 MB; dokument 66 tys. zn. 3,9→8,1 s, bez obcięcia (wykryta firma z końcówki).
- NOT_CHECKED: awaria S3 przez celowo uszkodzony model w pełnym /preview (test jednostkowy jest); HerBERT vs spaCy.

## Ocena CC (do decyzji Pawła)
PER na tych zbiorach praktycznie nic nie dodaje (osoby już zakrywa silnik). ORG daje realny zysk tam, gdzie spaCy nie widzi firmy
(BETA S.A. w polu SPRZEDAWCA, rodziny z firma_sweep), ale w kontrolnym nadmaskowuje instytucje ~4:1 — przez luki filtra instytucji.
Główny wyciek firm („Nazwa Sp. FIRMA_001”) leczy `LYNX-FIRMA-FILTER-FIX`, nie siatka. Rekomendacja: merge z siatką **wyłączoną**
(OFF = main), ponowny pomiar ORG po FIRMA-FILTER-FIX (i po domknięciu luk filtra instytucji), potem decyzja: ORG włączyć / całość usunąć.
