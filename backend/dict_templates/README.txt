dict_templates — szablony słowników LynxMask Desktop
====================================================

LENIWY TRYB (Paweł):
  1. Odpal benchmark (run_benchmark.bat) LUB masz juz wyniki w benchmark_results/
  2. Odpal: run_dict_auto.bat
  3. Daj Claude pliki z dict_templates/generated/ — on reszte

  run_dict_auto.bat --apply     = od razu wrzuca do profilu biura (bez Claude)
  run_dict_auto.bat --run-benchmark = benchmark + build w jednym

Wygenerowane pliki (dict_templates/generated/):
  auto_kontrahenci.json      — gotowe wpisy do maskowania
  auto_ner_boilerplate.json  — slowa do blocklisty NER (Claude → ner_blocklist.py)
  auto_engine_fixes.txt      — email/NIP/telefon — poprawka silnika, NIE slownik

RECZNY TRYB (opcjonalnie): pliki kontrahenci.json, placowki_medyczne.json poniżej.

TRZY PLIKI — TRZY CELE (nie mieszaj):

1. kontrahenci.json          → słownik MASKOWANIA (profil biura / trie)
2. placowki_medyczne.json    → słownik MASKOWANIA (to samo)
3. ner_boilerplate.json      → BLOCKLIST NER (NIE maskować — Claude dopisuje do ner_blocklist.py)

JAK WYPEŁNIAĆ (Paweł):
- value = dokładnie jak w dokumencie (możesz bez polskich znaków jeśli tak OCR czyta)
- type = FIRMA | OSOBA | ADRES | EMAIL (patrz komentarz w pliku)
- forms = opcjonalnie: warianty OCR / skróty (puste [] = Morfeusz wygeneruje sam)
- source = skąd wpis (np. "faktura_2024-09", "benchmark miss") — dla Ciebie, silnik ignoruje
- _example = true → wpisy przykładowe, usuń przed importem produkcyjnym

IMPORT DO PROFILU (Claude Code):
- POST /profile/add-entity per wpis (UI), albo
- add_entities_batch() z anonymizer.py: lista (value, type)
- Po imporcie: restart backendu lub przebudowa trie (add_entity robi _rebuild_trie)

BLOCKLIST (ner_boilerplate.json):
- NIE idzie do mapa.json — tylko rozszerzenie ner_blocklist.py
- Słowa krótsze niż 4 znaki pomijane przez Guard — wpisuj formy OCR bez ogonków

Czego NIE wpisywać do kontrahenci/placowki:
- NIP, PESEL, IBAN, telefon, PWZ → regex silnika
- Płatność, Odebrał, Dłużnik → ner_boilerplate.json
- samo "Sp. z o.o." bez nazwy własnej
