"""Independent geometry audit. python repro_r2.py <repo exact SHA>.

No real OCR, models, profiles or datasets. Exit 1 confirms retained F1/F2.
"""
import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

root = Path(sys.argv[1]).resolve()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == \
    '359fca88ce923c322d377078f0d585531a2cb1cb'
sys.path.insert(0, str(root/'tasks/LYNX-OCR-CASCADE/measure'))
import paired_ocr as p


def line(gap):
    return {'rect': (10, 20, 200+gap, 40), 'words': [
        {'rect': (10, 20, 100, 40), 'text': '74233', 'conf': 90},
        {'rect': (110+gap, 20, 200+gap, 40), 'text': '37590', 'conf': 90},
    ]}


assert dict(p.ids('7423337590')) == {'7423337590': True}
near = p.classify_doc([], [line(0)])
assert len(near) == 1 and near[0]['reason'] == 'valid_id'
far = p.classify_doc([], [line(650)])
f1 = len(far) == 1 and far[0]['reason'] == 'valid_id'
print(json.dumps({'id':'F1_CROSS_COLUMN', 'regions':len(far),
                  'reasons':[r['reason'] for r in far], 'false_join':f1}))

# A bad individual box is a measurement-status input, not an uncaught exception.
from PIL import Image
buffer = io.BytesIO()
Image.new('RGB', (1000, 1000), 'white').save(buffer, format='PNG')
tsv = {'level':[1], 'page_num':[1], 'block_num':[0], 'par_num':[0], 'line_num':[0],
       'left':[0], 'top':[0], 'width':[1000], 'height':[1000], 'conf':[-1], 'text':['']}
f2 = False
try:
    doc = p.measure_doc(buffer.getvalue(), lambda b:SimpleNamespace(boxes=[None], txts=['synthetic']),
                        lambda img:tsv)
    assert doc['unmeasurable'] or any(r['status']=='UNMEASURABLE' for r in doc['regions'])
    print('F2_BAD_BOX: explicit UNMEASURABLE')
except (TypeError, ValueError, IndexError) as exc:
    f2 = True
    print('F2_BAD_BOX: uncaught', type(exc).__name__)
print(json.dumps({'F1_reproduced':f1, 'F2_reproduced':f2}))
raise SystemExit(1 if f1 or f2 else 0)

