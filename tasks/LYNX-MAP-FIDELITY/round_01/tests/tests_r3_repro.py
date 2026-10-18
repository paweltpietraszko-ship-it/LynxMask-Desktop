"""Re-check F1 without modifying its retained original; ordinary value controls."""
from pathlib import Path
import contextlib
import io
import re
import subprocess
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SHA = "4be9f90c5e3d03e959223636a885fc1af6b00caf"
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "audyt")]


def main():
    old = Path(__file__).with_name("tests_r2_repro.py")
    s = old.read_text(encoding="utf-8").replace("2046610e4f23a2a6db0d9a65e207049c4584190a", SHA)
    s = s.replace("for label, a, b, collision in cases:", "for label, a, b, collision in cases:\n        collision = False")
    s = s.replace('(2 if label == "base-allocator" else 1)', '2')
    s = s.replace('(restored == text) == (label == "base-allocator")', 'restored == text')
    s = s.replace("F1 reproduced on exact delivery; only allocator methods swapped for differential baseline", "F1 fixed on exact r2")
    exec(compile(s, str(old), "exec"), {"__file__": str(old), "__name__": "__main__"})
    from pipeline_core import TokenAllocator
    pairs = [
        ("KWOTA", "0 zł", "0,00 zł", True),
        ("KWOTA", "00015,50 zł", "15.5 zł", True),
        ("KWOTA", "15,50 zł", "1550 zł", False),
        ("KWOTA", "134.460,00 PLN", "134460 PLN", True),
        ("KWOTA", "100 EUR", "100 USD", False),
        ("KWOTA", "1 234,50 zł", "1234.50 zł", True),
        ("NUMER", "1.12.2024", "11.2.2024", False),
        ("NUMER", "01/12/2024", "1.12.2024", True),
        ("NUMER", "701-090-21-85", "7010902185", True),
    ]
    for typ, a, b, same in pairs:
        al = TokenAllocator()
        assert (al.assign(typ, a) == al.assign(typ, b)) == same
        al = TokenAllocator()
        al.register(typ + "_001", a, 0, len(a))
        try:
            al.register(typ + "_001", b, 100, 100 + len(b))
        except ValueError:
            assert not same
        else:
            assert same
    print("9 ordinary amount/date/currency/identifier pairs: assign and register PASS")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import spacy_ner
        import pipeline_new
        import layers.ner_adapter as head
    text = "Pozwana Anna Nowakowska. Świadek Bartosz Nowak."
    frag = "Bartosz Nowak"
    start = text.index(frag)
    ent = spacy_ner.NERResult(text=frag, label="OSOBA", confidence=.9, start=start, end=start + len(frag))
    base = types.ModuleType("map_fidelity_base_adapter_r3")
    base.__file__ = head.__file__
    sys.modules[base.__name__] = base
    source = subprocess.check_output(["git", "show", "9fe2037:backend/layers/ner_adapter.py"], cwd=ROOT).decode()
    exec(compile(source, base.__file__, "exec"), base.__dict__)
    observed = []
    for owner in (base.apply_ner_layer, head.apply_ner_layer):
        with patch.object(spacy_ner, "detect_entities", return_value=[ent]), \
                patch.object(pipeline_new, "apply_ner_layer", owner), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            observed.append(pipeline_new.run_pipeline_new(text, {}))
    assert observed[0] == observed[1]
    out, rev, blocked = observed[1]
    restored = re.sub(r"OSOBA_\d{3}", lambda m: rev.get(m[0], m[0]), out)
    assert not blocked and restored != text
    print("SEPARATE BASELINE finding: surname propagation can assign another person's value; unchanged by delivery")


if __name__ == "__main__":
    main()
