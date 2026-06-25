# conftest.py — dodaje katalog główny projektu do sys.path
# Wymagane żeby testy w tests/ mogły importować moduły z katalogu głównego
# (anonymizer, output_guard, pipeline, ner_layer itp.)
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
