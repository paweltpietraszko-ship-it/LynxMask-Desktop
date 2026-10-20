"""Independent phase A audit. Run: python repro_r3.py <backend> <writable temp parent>.

Only synthetic data. Direct real endpoint, isolated archive/PSE, no server/lifespan.
Local-model smoke blocks outbound socket connections; not a quality benchmark.
"""
import hashlib
import gc
import io
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

backend = Path(sys.argv[1]).resolve()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=backend, text=True).strip() == \
    'b72139461a2db14cb550b06523116dd4e6586dad'
sys.path.insert(0, str(backend))
from PIL import Image, ImageDraw
from fastapi import UploadFile
import ocr_engine as oe
import ocr_rapid as rapid

secret = 'Audit Person 44051401359 audit@example.org'
fake = lambda image: SimpleNamespace(boxes=[[[0, 0], [400, 0], [400, 20], [0, 20]]], txts=[secret])

with tempfile.TemporaryDirectory(prefix='lynx-step2-r3-', dir=sys.argv[2]) as folder:
    root = Path(folder)
    env = {'ARCHIVE_DIR': str(root/'archive'), 'PSE_REGISTRY': str(root/'pse.json'),
           'ANONYMIZER_PROFILE_DIR': str(root/'profile'), 'LYNX_OCR_ENGINE': 'rapid'}
    with patch.dict(os.environ, env):
        import pseudominizer_api as api
        print('ISOLATED_API_IMPORTED', flush=True)
        logs = io.StringIO()
        handler = logging.StreamHandler(logs)
        logging.getLogger().addHandler(handler)
        try:
            with patch.object(rapid, '_engine', fake), patch.object(api, 'pseudonymize_document',
                    side_effect=AssertionError('C1 must stop before pipeline')):
                upload = io.BytesIO(b'fake-image-for-interface-stub')
                upload._rolled = False  # UploadFile: input remains in memory, like a small real upload
                call = api.preview(None, UploadFile(filename='synthetic.png', file=upload))
                try:
                    call.send(None)  # in-memory UploadFile: coroutine finishes without async I/O
                except StopIteration as completed:
                    response = completed.value
                else:
                    raise AssertionError('Unexpected asynchronous I/O in isolated endpoint')
                body = json.loads(response.body)
                assert response.status_code == 422, response.status_code
                assert body['ocr_rejected'] is True
                assert body['ocr']['quality'] == 'reject' and body['ocr']['confidence'] == 0.0
                assert body['ocr']['engine'] == 'rapid' and body['ocr']['warning'] == rapid.C1_WARNING
                assert not {'original_text', 'tokens', 'reverse_map', 'anonymized_preview'} & body.keys()
                assert secret not in response.body.decode('utf-8')
            for quality, confidence in [('ok', 90), ('warn', 75), ('reject', 60)]:
                tess = oe.OCRResult('synthetic', confidence, quality, 'test', 'tesseract', 1)
                with patch.object(rapid, 'recognize', side_effect=RuntimeError(secret)), \
                     patch.object(oe, '_tesseract_available', return_value=True), \
                     patch.object(oe, '_run_tesseract', return_value=tess):
                    assert oe.extract_text_from_image(b'x', 'synthetic.png') is tess
            assert secret not in logs.getvalue() and '44051401359' not in logs.getvalue()
        finally:
            logging.getLogger().removeHandler(handler)
        gc.collect()  # close unreachable sqlite connections before removing isolated Windows files
print('INDEPENDENT_C1_ENDPOINT_AND_FALLBACK PASS', flush=True)

expected = {
    'PP-OCRv6_det_small.onnx': '090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f',
    'PP-OCRv6_rec_small.onnx': '6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884',
    'ch_ppocr_mobile_v2.0_cls_mobile.onnx': 'e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c',
}
for name, digest in expected.items():
    assert hashlib.sha256((rapid.model_dir()/name).read_bytes()).hexdigest() == digest
image = Image.new('RGB', (900, 130), 'white')
ImageDraw.Draw(image).text((30, 35), 'AUDIT TEST 123456789', fill='black', font_size=38)
buffer = io.BytesIO()
image.save(buffer, format='PNG')
with patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')), \
     patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')):
    result = rapid.extract_rapid(buffer.getvalue(), oe.OCRResult)
    assert result is not None and result.engine == 'rapid' and result.quality == 'reject'
    assert result.confidence == 0.0 and result.text.strip() and result.word_count > 0
print('LOCAL_MODEL_HASHES_AND_OFFLINE_SMOKE PASS (no quality claim)')

