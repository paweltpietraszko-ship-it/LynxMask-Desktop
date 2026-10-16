"""Independent T02 audit: real HTTP middleware/routes, synthetic temporary state."""
import base64
import importlib.util
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == 'dc498366368b0b4d4767a61e6c6d56c939630713'
state = Path(tempfile.mkdtemp(prefix='lynx_t02_independent_'))
for key, part in [('ARCHIVE_DIR', 'archive'), ('ANONYMIZER_PROFILE_DIR', 'profile'), ('PROFILE_DIR', 'guard'), ('PSE_REGISTRY', 'pse.json')]:
    os.environ[key] = str(state / part)
sys.path.insert(0, str(ROOT / 'backend'))
os.chdir(ROOT / 'backend')
logging.disable(logging.CRITICAL)
from fastapi.testclient import TestClient
import pseudominizer_api as api
api._API_TOKEN, api._EXPRESS_TOKEN = 'full-synthetic-token', 'express-synthetic-token'
client = TestClient(api.app, base_url='http://127.0.0.1:8765')
count = 0
def req(method, path, **kwargs):
    global count
    count += 1
    return client.request(method, path, **kwargs)

for host in ['', 'testserver', 'evil.example:8765', '127.0.0.1', 'localhost', 'localhost:8766', '127.0.0.1:80', 'localhost.evil:8765', '[::1]:8765']:
    for path in ['/express/token', '/health', '/archive']:
        response = req('GET', path, headers={'Host': host, 'X-Api-Token': api._API_TOKEN})
        assert response.status_code == 400
        assert api._EXPRESS_TOKEN not in response.text
for host in ['127.0.0.1:8765', 'localhost:8765']:
    assert req('GET', '/express/token', headers={'Host': host}).status_code == 200

private = [('GET', '/profile/entities'), ('GET', '/profile/export-dict'), ('GET', '/archive'), ('GET', '/archive/PSE-2026-9001/blob'), ('POST', '/archive'), ('POST', '/archive/reencrypt'), ('DELETE', '/archive/PSE-2026-9001'), ('GET', '/version'), ('GET', '/preview'), ('PUT', '/preview'), ('DELETE', '/preview-express'), ('GET', '/profile%2fentities')]
for method, path in private:
    for token in ['', 'invalid-token', api._EXPRESS_TOKEN]:
        response = req(method, path, headers={'X-Api-Token': token})
        assert response.status_code == 401, (method, path, response.status_code)
for path in ['/version', '/archive']:
    assert req('GET', path, headers={'X-Api-Token': api._API_TOKEN}).status_code == 200

for origin in ['http://localhost:1420', 'http://tauri.localhost', 'https://evil.example', 'null', 'http://localhost:9999', 'http://tauri.localhost.evil', 'https://tauri.localhost']:
    response = req('GET', '/express/token', headers={'Origin': origin})
    allowed = origin in ['http://localhost:1420', 'http://tauri.localhost']
    assert response.headers.get('access-control-allow-origin') == (origin if allowed else None)
    response = req('OPTIONS', '/preview', headers={'Origin': origin, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'X-Api-Token'})
    assert response.status_code == (200 if allowed else 400)
assert 'access-control-allow-origin' not in req('GET', '/express/token').headers
for token in [api._EXPRESS_TOKEN, api._API_TOKEN]:
    for path in ['/preview', '/preview-express']:
        response = req('POST', path, headers={'X-Api-Token': token}, files={'file': ('synthetic.txt', b'Kontakt: synthetic.audit@example.org', 'text/plain')})
        assert response.status_code == 200, (path, response.status_code)
        assert 'synthetic.audit@example.org' not in response.json()['anonymized_preview']
api._API_TOKEN, api._EXPRESS_TOKEN = '', ''
assert req('GET', '/version').status_code == 401
assert req('POST', '/preview').status_code == 401

# Classify the seven reported archive failures without changing production/tests.
spec = importlib.util.spec_from_file_location('archive_retained', ROOT / 'backend/tests/test_archive_adversarial.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
raw = TestClient(api.app)
assert raw.get('/archive').status_code == 400
api._API_TOKEN = 'archive-synthetic-full-token'
assert client.get('/archive').status_code == 401
archive.TestClient = lambda app: TestClient(app, base_url='http://127.0.0.1:8765', headers={'X-Api-Token': api._API_TOKEN})
names = {'TestArchiveSave': ['test_d1_valid_save'], 'TestArchiveRead': ['test_d5_list_documents', 'test_d6_get_blob', 'test_d12_audit_log'], 'TestArchiveDelete': ['test_d8_delete_valid', 'test_d8b_delete_nonexistent'], 'TestArchiveReencrypt': ['test_d10_reencrypt_valid']}
suite = unittest.TestSuite(getattr(archive, cls)(name) for cls, methods in names.items() for name in methods)
result = unittest.TestResult()
suite.run(result)
assert result.wasSuccessful(), [(str(test), error[-350:]) for test, error in result.errors + result.failures]
print({'http_checks': count, 'archive_replay': result.testsRun, 'result': 'PASS', 'windows_release_origin_host': 'NOT_CHECKED'})
