"""Independent synthetic checks; run from backend, --red for pre-fix SHA."""
import json
import re
import sys
from unittest.mock import patch

from pipeline_new import run_pipeline_new
import layers.ner_adapter as ner
from layers.contact import _EMAIL_OCR_RE
from anonymizer_init import STRUCTURAL_PATTERNS, TOKEN_EMAIL

addresses = ['ul. Polna l2/8', 'ul. Św. Marcin 5', 'ul. 3 Maja 12/4',
             'ul. Ks. Brzozowa 8', 'ul. 11 Listopada I7/O2', 'ul. Polna 12/l4']
emails = ['żaneta@firma.pl', 'ale\u0301x@firma.pl', 'Ąnna@firma.pl',
          'łukasz.żak@firma.pl', 'doŻaneta@firma.pl', 'anna. nowak@firma.pl']
failed = []
for value in addresses + emails:
    text = 'Dane: ' + value + '; koniec.'
    with patch.object(ner, 'process_ner', return_value=({}, {})):
        out, rev, blocked = run_pipeline_new(text, anon_map={})
    restored = re.sub(r'\b(?:ADRES|EMAIL)_\d{3}(?!\d)', lambda m: rev.get(m[0], m[0]), out)
    if blocked or value not in rev.values() or restored != text:
        failed.append(value)
if '--red' in sys.argv:
    assert all(x in failed for x in addresses[:3] + emails[:2])
    print(json.dumps({'red_named_L1_L5': 5, 'failed_of_12': len(failed)}))
    raise SystemExit()
assert not failed, failed
for pattern in [_EMAIL_OCR_RE] + [p for k, p in STRUCTURAL_PATTERNS if k == TOKEN_EMAIL]:
    for value in emails[:5]:
        sample = value.replace('@', '\n@') if r'\n' in pattern.pattern and '©' not in pattern.pattern else value
        m = pattern.search('Dane: ' + sample + ';')
        assert m and m.group() == sample, (pattern.pattern, value)
for text in ['Profil: @administrator', 'Skrót ul. w instrukcji', 'Plac zabaw, al. pięć razy.',
             'Szpital X 5', 'Kontakt bez adresu.']:
    with patch.object(ner, 'process_ner', return_value=({}, {})):
        out, rev, _ = run_pipeline_new(text, anon_map={})
    assert out == text and not rev, (text, out)
print(json.dumps({'pipeline_roundtrip': 12, 'three_email_patterns': 15, 'clean': 5}))
