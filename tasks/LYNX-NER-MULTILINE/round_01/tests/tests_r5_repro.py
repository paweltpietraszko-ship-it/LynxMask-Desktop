"""Independent completion of r4: synthetic inputs, exact delivered production files."""
import contextlib
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SHA = "71a3d50519e1c7388372868f8ce6985bfc95092d"
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "audyt")]
TOKEN = re.compile(r"OSOBA_\d{3}")


def main():
    for file in ("backend/ner_layer.py", "backend/layers/ner_adapter.py"):
        expected = subprocess.check_output(["git", "show", f"{SHA}:{file}"], cwd=ROOT).decode()
        assert (ROOT / file).read_text(encoding="utf-8") == expected
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from layers.ner_adapter import _apply_first_names, _propagate_osoba
        from pipeline_core import TokenAllocator
        import engine_quality
        import pipeline
        import spacy_ner
    cases = [
        ("OSOBA_008 Katarzyna", "Katarzyna"),
        ("Katarzyna OSOBA_008", "Katarzyna"),
        ("Pan Bartosz", "Bartosz"),
        ("Pani Wiktoria", "Wiktoria"),
        ("Pani Katarzynie", "Katarzynie"),
        ("OSOBA_008\tKatarzyna", "Katarzyna"),
        ("OSOBA_008\nKatarzyna", None),
        ("Katarzyna\nOSOBA_008", None),
        ("Róża rośnie. Katarzyna", None),
        ("Pani wiktoria", None),
    ]
    for text, name in cases:
        alloc = TokenAllocator()
        alloc.reserve("OSOBA_008")
        out = _apply_first_names(text, alloc)
        rev = alloc._reverse
        assert TOKEN.sub(lambda m: rev.get(m[0], m[0]), out) == text
        assert list(rev.values()) == ([name] if name else []), (text, rev)
        assert out.count("\n") == text.count("\n")
    text = "Bartosz Wrona oraz Bartoszewski; Malinowskiego."
    out = _propagate_osoba(text, "OSOBA_007", "Bartosz Malinowski")
    assert "Bartosz Wrona" in out and "Bartoszewski" in out and "Malinowskiego" not in out
    with tempfile.TemporaryDirectory(prefix="lynx_r5_") as folder:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            state = engine_quality.build_state(folder)
        for text, names in [("Pismo dla Pani Wiktorii; Pan Bartosz otrzyma kopię.", ["Wiktorii", "Bartosz"]),
                            ("Pani Katarzyna; ponownie Pani Katarzyna.", ["Katarzyna"])]:
            with patch.object(spacy_ner, "detect_entities", return_value=[]), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = pipeline.pseudonymize_document(text, state)
            assert not result.error and not result.guard_blocked
            assert all(name not in result.text for name in names)
            assert all(name in result.reverse_map.values() for name in names)
            assert TOKEN.sub(lambda m: result.reverse_map.get(m[0], m[0]), result.text) == text
    print("r5: 10 context/boundary/map cases + propagation control + 2 real pipeline/Guard cases PASS; controlled detector")


if __name__ == "__main__":
    main()
