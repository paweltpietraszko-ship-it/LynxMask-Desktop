# audyt/ — narzędzia audytu 2026-10 (LYNX-CLOUD-AUDIT)

Raporty: `arch/FINDING_2026-10_AUDYT.md`, `arch/FINDING_2026-10_MOBILE_PORT.md`. Skrypty diagnostyczne, nie kod produktu. Uruchamiać z korzenia repo
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
| `anchor_proto.py "tekst"` | PROTOTYP portu AnchorEngine.kt (Mobile) jako post-pass — raport `arch/FINDING_2026-10_MOBILE_PORT.md` |
| `port_rules.py [--json plik]` | tabela reguł A.x: przykład → pipeline Desktop → + kotwice |
| `bench_offline.py --dataset … --cache … --out … [--variants] [--mobile repo]` | benchmark bez HTTP (OCR raz, cache) z wariantami portu (monkeypatch w procesie) |
| `docs_variants.py --mobile repo` | warianty portu na `Pliki testowe/` — które wycieki z audytu znikają |

Logi w `logs/` (wartości PII zamaskowane, surowy log benchmarku i stdout backendu celowo pominięte).
Reproduktory błędów: `backend/tests/test_audyt_2026_10.py` (uruchamiać jawnie, pytest.ini go nie zbiera).
