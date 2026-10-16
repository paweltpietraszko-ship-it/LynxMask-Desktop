# audyt/ — narzędzia audytu 2026-10 (LYNX-CLOUD-AUDIT)

Raport: `arch/FINDING_2026-10_AUDYT.md`. Skrypty diagnostyczne, nie kod produktu. Uruchamiać z korzenia repo
interpreterem z zależnościami backendu. Pełne wyniki z PII syntetycznym zapisują się poza repo (`--out`).

| Skrypt | Co robi |
|---|---|
| `trace_layers.py "tekst" [--ner]` | tekst po każdej warstwie `pipeline_new` (NER domyślnie zmockowany) |
| `repro_pipeline.py [--seed]` | przypadki z listy bugów przez `pseudonymize_document` na świeżym profilu |
| `repro_guard.py` | przypadki IBAN/NIP w Output Guard |
| `run_docs.py --out DIR pliki…` | dokumenty przez działający backend `/preview` + detektor kandydatów wycieku |
| `roundtrip.py DIR` | wierność Przywracania (logika `Depseudonimizuj.tsx`) dla wyników `run_docs.py` |
| `unmask_sim.py` | symulacja `restoreText()` z frontendu — przypadki brzegowe |
| `rota_leak_test.py [--modes …] [--out plik]` | test szczelności dla zdań koordynatora (Elnath Rota) |

Logi w `logs/` (wartości PII zamaskowane, surowy log benchmarku i stdout backendu celowo pominięte).
Reproduktory błędów: `backend/tests/test_audyt_2026_10.py` (uruchamiać jawnie, pytest.ini go nie zbiera).
