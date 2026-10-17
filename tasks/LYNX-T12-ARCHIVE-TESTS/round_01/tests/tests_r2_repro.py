"""Independent T12: first/prior import, repeat, failure cleanup, synthetic sentinel."""
import argparse
import gc
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == 'c96199b00028f7ce7b06ba1c77d51834a3242fec'
mode = argparse.ArgumentParser()
mode.add_argument('mode',choices=['first','prior'])
mode = mode.parse_args().mode
logging.disable(logging.CRITICAL)
sys.path.insert(0,str(ROOT/'backend'))
home = Path(tempfile.mkdtemp(prefix='lynx_codex_t12_sentinel_'))
os.environ['ARCHIVE_DIR'] = str(home/'archive')
os.environ['PROFILE_DIR'] = str(home/'profile')
os.environ['ANONYMIZER_PROFILE_DIR'] = str(home/'profile')
os.environ['PSE_REGISTRY'] = str(home/'pse.json')
archive = home/'archive'
archive.mkdir()
(archive/'sentinel.enc').write_bytes(b'SYNTHETIC_SENTINEL_DO_NOT_TOUCH')
if mode == 'prior':
    import pseudominizer_api
    import db_store
    pseudominizer_api._API_TOKEN = 'previous-synthetic-token'
def signature():
    return {str(p.relative_to(archive)):(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in archive.rglob('*') if p.is_file()}
before_files = signature()
env_before = os.environ['ARCHIVE_DIR']
spec = importlib.util.spec_from_file_location('t12_independent_archive',ROOT/'backend/tests/test_archive_adversarial.py')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
api = mod.api
store = mod.db_store
assert os.environ['ARCHIVE_DIR'] == env_before
saved = {key:getattr(api,key) for key in mod._GLOBALS}
saved_db = store._DB_PATH
real_setup = mod.setUpModule
active_roots=[]
def setup():
    real_setup()
    active_roots.append(Path(mod._tmp.name))
    assert Path(api.DB_PATH).is_relative_to(active_roots[-1])
    assert Path(api.MAPS_DIR).is_relative_to(active_roots[-1])
    assert Path(store._DB_PATH).is_relative_to(active_roots[-1])
mod.setUpModule=setup
runs=[]
for _ in range(2):
    result=unittest.TestResult()
    unittest.defaultTestLoader.loadTestsFromModule(mod).run(result)
    assert result.wasSuccessful(), result.errors+result.failures
    assert result.testsRun == 19
    assert all(getattr(api,key)==value for key,value in saved.items())
    assert store._DB_PATH == saved_db
    assert not active_roots[-1].exists()
    assert signature() == before_files
    runs.append(result.testsRun)

# Failure after a real temporary DB was initialized.
real_init=store.init
failed_roots=[]
def fail_init(path):
    real_init(path)
    failed_roots.append(Path(path).parent)
    raise RuntimeError('synthetic setup failure')
with patch.object(store,'init',fail_init):
    try:
        real_setup()
    except RuntimeError as error:
        assert str(error)=='synthetic setup failure'
    else:
        raise AssertionError('expected setup failure')
assert not failed_roots[-1].exists()
assert all(getattr(api,key)==value for key,value in saved.items())
assert store._DB_PATH==saved_db and signature()==before_files

# A failing body must still tear down the module fixture.
class FailingBody(unittest.TestCase):
    def test_synthetic_failure(self):
        self.fail('synthetic body failure')
FailingBody.__module__=mod.__name__
result=unittest.TestResult()
unittest.TestSuite([FailingBody('test_synthetic_failure')]).run(result)
assert len(result.failures)==1 and not result.errors
assert not active_roots[-1].exists()
assert all(getattr(api,key)==value for key,value in saved.items())
assert store._DB_PATH==saved_db and signature()==before_files
bootstrap = Path(mod._IMPORT_TMP.name) if mod._IMPORT_TMP else None
print(json.dumps({'mode':mode,'runs':runs,'globals_restored':True,'sentinel_unchanged':True,'active_fixture_dirs_after_cleanup':0,'setup_and_body_failure_cleanup':'PASS','import_bootstrap_exists_after_module':bool(bootstrap and bootstrap.exists()),'import_bootstrap_path':str(bootstrap) if bootstrap else None,'import_bootstrap_files':sorted(str(p.relative_to(bootstrap)) for p in bootstrap.rglob('*') if p.is_file()) if bootstrap else []}))
gc.collect()
