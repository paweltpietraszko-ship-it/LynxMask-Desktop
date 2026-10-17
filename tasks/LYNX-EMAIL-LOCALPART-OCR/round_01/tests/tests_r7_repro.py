"""Independent narrow recheck; synthetic inputs only; real pipeline and Guard."""
import contextlib
import io
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'audyt')]
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == '3fc5c7b05a40e1bbfaf3cad04fd91c659b76a181'
from pipeline_core import PipelineState, TokenAllocator
from layers.contact import apply_contact_layer
from pipeline_new import run_pipeline_new, run_pipeline_express
from unmask_sim import unmask
from output_guard import guard_output_with_map

counts = {'layer': 0, 'full': 0, 'express': 0}
def check(text, value, canonical=None):
    expected = text.replace(value, 'EMAIL_001')
    mapped = canonical or value
    state = PipelineState(text=text, allocator=TokenAllocator())
    apply_contact_layer(state)
    assert (state.text, state.allocator.reverse_map) == (expected, {'EMAIL_001': mapped}), ('layer', text, state.text, state.allocator.reverse_map)
    counts['layer'] += 1
    for label, fn in [('full', run_pipeline_new), ('express', run_pipeline_express)]:
        with contextlib.redirect_stdout(io.StringIO()):
            out, rev, blocked = fn(text, anon_map={})
        assert not blocked and out == expected and rev == {'EMAIL_001': mapped}, (label, text, out, rev, blocked)
        guard = guard_output_with_map(out, None, known_plain=list(rev.values()))
        assert not guard.blocked and not guard.redacted and guard.output() == out, (label, 'guard')
        if canonical is None:
            assert unmask(out, rev) == text, (label, 'restore', text)
        counts[label] += 1

# Retain the original reproducer and generalize only approved siblings.
for first, last in [('anna', 'nowak'), ('ANNA', 'NOWAK'), ('AnNa', 'NoWaK')]:
    for sep in [' ', '  ', '   ', '\t', '\t\t', '\t\t\t', ' \t', '\t ', ' \t ']:
        value = first + '.' + sep + last + '@example.pl'
        check('Kontakt: ' + value + '. Termin płatności.', value)
for value in ['anna.nowak@example.pl', 'kontakt. jan@example.pl', 'Podpisano. Jan@example.pl']:
    check('Prosimy o ' + value + '. Termin płatności.', value)
for sep in ['\n', '\r\n', '\r']:
    check('Kontakt.' + sep + 'jan@example.pl. Termin płatności.', 'jan@example.pl')
for value in ['jan@\nexample.pl', 'jan\n@example.pl', 'jan@ \nexample.pl', 'jan \n@example.pl', 'jan @example.pl', 'jan@ example.pl', 'jan@wp. pl']:
    check('Mail: ' + value + ' koniec', value, value.replace(' ', '').replace('\n', ''))
# At most one preceding word; no trailing sentence absorption.
check('Prosimy o pilny kontakt. jan@example.pl. Termin płatności.', 'kontakt. jan@example.pl')
for text in ['Kontakt. nie podano adresu.', 'example.pl. Termin płatności.']:
    state = PipelineState(text=text, allocator=TokenAllocator())
    apply_contact_layer(state)
    assert state.text == text and not state.allocator.reverse_map
    counts['layer'] += 1
# Retained T07 sibling: email owns digits; standalone run remains NUMER.
text = 'Kontakt: 123456789012345@example.pl. Numer: 123456789012345.'
for label, fn in [('full', run_pipeline_new), ('express', run_pipeline_express)]:
    with contextlib.redirect_stdout(io.StringIO()):
        out, rev, blocked = fn(text, anon_map={})
    assert not blocked and set(rev.values()) == {'123456789012345@example.pl', '123456789012345'}
    assert unmask(out, rev) == text
    guard = guard_output_with_map(out, None, known_plain=list(rev.values()))
    assert not guard.blocked and not guard.redacted and guard.output() == out
    counts[label] += 1
print('PASS independent approved matrix and retained reproducers:', counts)
print('Real NER and Guard used, no stubs. Existing @/TLD canonicalization is F3, not claimed as exact raw restoration.')