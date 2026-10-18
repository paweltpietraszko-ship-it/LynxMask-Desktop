"""Retained independent D1 reproducer: decimal precision, synthetic amounts only."""
import contextlib
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SHA = "2046610e4f23a2a6db0d9a65e207049c4584190a"
BASE = "9fe2037"
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "audyt")]
TOKEN = re.compile(r"KWOTA_\d{3}")


def main():
    for file in ("backend/pipeline_core.py", "backend/layers/amount.py", "backend/pipeline_new.py", "backend/pipeline.py"):
        expected = subprocess.check_output(["git", "show", f"{SHA}:{file}"], cwd=ROOT).decode()
        assert (ROOT / file).read_text(encoding="utf-8") == expected
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import pipeline_core as core
        import engine_quality
        import pipeline
        from pipeline_new import run_pipeline_express
    baseline = types.ModuleType("map_fidelity_base_allocator")
    sys.modules[baseline.__name__] = baseline
    source = subprocess.check_output(["git", "show", f"{BASE}:backend/pipeline_core.py"], cwd=ROOT).decode()
    exec(compile(source, "baseline_pipeline_core.py", "exec"), baseline.__dict__)
    cases = [
        ("28-significant-control", "12 345 678 901 234 567 890 123 456,81 zł", "12 345 678 901 234 567 890 123 456,82 zł", False),
        ("29-significant", "123 456 789 012 345 678 901 234 567,81 zł", "123 456 789 012 345 678 901 234 567,82 zł", True),
        ("29-significant-PLN", "123.456.789.012.345.678.901.234.567,81 PLN", "123.456.789.012.345.678.901.234.567,82 PLN", True),
    ]
    for label, a, b, collision in cases:
        for cls, expected in ((baseline.TokenAllocator, False), (core.TokenAllocator, collision)):
            allocator = cls()
            assert (allocator.assign("KWOTA", a) == allocator.assign("KWOTA", b)) == expected
        print(label, "head_collision", collision, "baseline_collision", False)
    a, b = cases[1][1:3]
    text = f"Kwota pierwsza {a}; kwota druga {b}."
    with tempfile.TemporaryDirectory(prefix="lynx_mapfidelity_r2_") as folder:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            state = engine_quality.build_state(folder)
        for label, cls in (("base-allocator", baseline.TokenAllocator), ("head", core.TokenAllocator)):
            with patch.object(core.TokenAllocator, "assign", cls.assign), \
                    patch.object(core.TokenAllocator, "register", cls.register), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                express = run_pipeline_express(text, {})
                full = pipeline.pseudonymize_document(text, state)
            for mode, out, rev, blocked, error in [
                ("Express", *express, False),
                ("Full/Guard", full.text, full.reverse_map, full.guard_blocked, bool(full.error)),
            ]:
                restored = TOKEN.sub(lambda m: rev.get(m[0], m[0]), out)
                assert not blocked and not error
                assert len(rev) == (2 if label == "base-allocator" else 1)
                assert (restored == text) == (label == "base-allocator")
                print(label, mode, "map_entries", len(rev), "roundtrip", restored == text)
    print("F1 reproduced on exact delivery; only allocator methods swapped for differential baseline")


if __name__ == "__main__":
    main()
