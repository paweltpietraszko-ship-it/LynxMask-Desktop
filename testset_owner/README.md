# Zbiór testowy Pawła (korpus porównania Mobile/Desktop)

Te same 693 teksty, na których 21.10.2026 porównano silnik Mobile i Desktop. Wszystko syntetyczne,
bez prawdziwych dokumentów.

| Zbiór (`set`) | Dok. | Skąd | Klucz (gold) |
|---|---:|---|---|
| `testy`  | 38  | repo Mobile `testy/` — ręczne przypadki z komentarzami „OCZEKIWANE: …” | brak (oczekiwanie w treści) |
| `clean`  | 300 | repo Mobile `dataset_clean/docs` — czyste pisma | `gold_clean.json` |
| `stress` | 300 | repo Mobile `dataset_stress/docs` — pisma firmowe z rzadkimi nazwiskami spoza top 1000, nazwiskami-słowami pospolitymi i rzadkimi miejscowościami | `gold_stress.json` |
| `pliki`  | 7   | Desktop `Pliki testowe/` | brak |
| `ocr`    | 48  | tekst z OCR 48 obrazów benchmarku Desktop `backend/dataset_20260627_095419` (2 z 50 obrazów silnik odrzucił) | brak |

## Pliki

- `corpus/<zbiór>__<nazwa>.txt` — teksty (UTF-8). Korekty wejścia z 21.10: w 3 plikach `testy/` gotowe tokeny
  `NUMER_011` zamienione na `NUMER-011` (Desktop odrzuca tekst z tokenami), `test_s1_s2_run.txt` przekodowany z UTF-16.
- `manifest.json` — `id`, `set`, `source` (plik źródłowy w repo Mobile lub Desktop).
- `gold_clean.json`, `gold_stress.json` — wartości, które w danym dokumencie muszą zniknąć (imię i nazwisko, adres,
  PESEL, dowód, telefon, e-mail, NIP…), skopiowane z `ground_truth.json` repo Mobile; `id` = nazwa pliku w `corpus/`.
- `baseline_2026-10-21_report.md`, `baseline_2026-10-21_porownanie.html` — wynik porównania Mobile `450204b`
  i Desktop `cc70822` z 21.10 (punkt odniesienia). W HTML kolumny Mobile | Desktop:
  żółty = zakrył tylko Mobile, niebieski = tylko Desktop, fioletowy = inny typ.

## Ograniczenia

- Klucz jest tylko dla `clean` i `stress` i opisuje dane, które muszą zniknąć. Nie mówi, czego nie wolno
  zakrywać, więc nadmaskowania (np. „Dział” jako osoba) nie zmierzy — do tego służy oko albo `testy/`.
- `clean`/`stress` to pisma z generatora Mobile: powtarzalne układy, łatwiejsze niż prawdziwe pisma.
  Dobre na regres („czy coś się popsuło”), słabe jako dowód jakości.
- To nie jest `dataset_gold_20261022` (GOLD dev/test z oznaczeniem PII i nie-PII), który dalej pozostaje miarką
  dla zmian silnika.
