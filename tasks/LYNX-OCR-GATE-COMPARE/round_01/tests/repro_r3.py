"""Independent targeted stage 2/2b chain checks, synthetic only.

Usage: python repro_r3.py <repo exact SHA> <writable temporary parent>.
No HTTP, OCR or datasets. Uses real masking pipeline and current Guard.
"""
import contextlib
import gc
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(sys.argv[1]).resolve()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == \
    '392a433ac1744b07553c2e15081935dc03136a63'
sys.path[:0] = [str(root/'backend'), str(root/'audyt')]
with tempfile.TemporaryDirectory(prefix='lynx-gate-r3-', dir=sys.argv[2]) as folder:
    # Isolate Guard allowlist/profile; no API import/server or user profile.
    os.environ['PROFILE_DIR'] = str(Path(folder)/'guard-profile')
    import engine_quality as eq
    from pipeline import pseudonymize_document
    (Path(folder)/'test-profile').mkdir()
    with contextlib.redirect_stdout(io.StringIO()):
        state = eq.build_state(str(Path(folder)/'test-profile'))
    samples = [
        ('CITY', 'Adres: ul. Polna 4, 00-001 Glogow', 'Glogow'),
        ('EMAIL', 'E-mail: test.audit@domena.pì', 'test.audit'),
        ('NIP_TAIL', 'NIP: 742-33-75-90 | Koniec.', '-90'),
        ('PARCEL_TAIL', 'Nr działki: 373251.0081.9795', '9795'),
        ('DOB', 'urodzony: Jan Nowak, ur. 2.O4.1990', '2.O4.1990'),
        ('NAME', 'Lista:\nGrażyna\nKoniec', 'Grażyna'),
        ('SURNAME', 'Lista:\nJankowski\nKoniec', 'Jankowski'),
    ]
    for sid, text, fragment in samples:
        with contextlib.redirect_stdout(io.StringIO()):
            result = pseudonymize_document(text, state)
        assert not result.error and fragment not in result.text, sid
        restored = result.text
        for token, value in sorted(result.reverse_map.items(), key=lambda item:len(item[0]), reverse=True):
            restored = restored.replace(token, value)
        print(json.dumps({'id':sid, 'fragment_hidden':fragment not in result.text,
                          'blocked':result.guard_blocked, 'roundtrip_equal':restored==text}))
        if sid in ('NAME', 'SURNAME'):
            assert restored == text and fragment in result.reverse_map.values(), sid
    # Deliberate Mobile exception remains: the new dictionary must not mask headings.
    with contextlib.redirect_stdout(io.StringIO()):
        result = pseudonymize_document('Data Dane Osoba', state)
    assert all(w in result.text for w in ('Data', 'Dane', 'Osoba'))
    gc.collect()
print('INDEPENDENT_STAGE2_2B PASS')

