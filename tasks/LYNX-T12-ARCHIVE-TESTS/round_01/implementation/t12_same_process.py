# Dowód kryterium 2/4: API zaimportowane wcześniej przez inny moduł testów, moduł T12 uruchomiony 2x w jednym procesie.
import sys, os, pathlib, glob, tempfile, unittest
sys.path[:0] = [os.getcwd(), os.path.join(os.getcwd(), "tests")]
import test_pipeline_adversarial  # noqa: F401 — importuje pseudominizer_api z produkcyjną ścieżką (stan sprzed T12)
import pseudominizer_api as api, db_store
before = (api.ARCHIVE_DIR, api.MAPS_DIR, api.DB_PATH, api._API_TOKEN, db_store._DB_PATH)
print("API imported first:", "pseudominizer_api" in sys.modules, "| DB_PATH before:", api.DB_PATH)
import test_archive_adversarial as t12
print("T12 import-time tmp used:", t12._IMPORT_TMP is not None)
for i in (1, 2):
    seen = {}
    orig = t12.make_client
    def spy(*a, **k):
        seen.setdefault("db", db_store._DB_PATH); seen.setdefault("maps", api.MAPS_DIR); return orig(*a, **k)
    t12.make_client = spy
    r = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w")).run(unittest.defaultTestLoader.loadTestsFromModule(t12))
    t12.make_client = orig
    tmp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    print(f"run {i}: tests={r.testsRun} fail={len(r.failures)} err={len(r.errors)} skip={len(r.skipped)}",
          "| db under TEMP:", tmp_root in pathlib.Path(seen['db']).resolve().parents,
          "| db exists after:", pathlib.Path(seen['db']).exists(), "| maps exists after:", pathlib.Path(seen['maps']).exists())
after = (api.ARCHIVE_DIR, api.MAPS_DIR, api.DB_PATH, api._API_TOKEN, db_store._DB_PATH)
print("globals restored:", before == after, "| leftover lynx_t12_ dirs:", len(glob.glob(os.path.join(tempfile.gettempdir(), "lynx_t12_*"))))
