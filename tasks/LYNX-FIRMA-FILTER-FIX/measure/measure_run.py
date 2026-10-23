"""LYNX-FIRMA-FILTER-FIX: pomiar PRZED/PO przez prawdziwy /preview (TestClient, pusty izolowany profil).
Uzycie: python measure_run.py <SHA> <etykieta> <katalog_wyjscia>   (dane syntetyczne; bez realnych dokumentow)"""
import io, json, os, shutil, subprocess, sys, tarfile, tempfile, time, itertools
from pathlib import Path
REPO = Path(r"C:/Users/p_pie/Desktop/LynxMask-Desktop")
PY = str(REPO / ".venv/Scripts/python.exe")
HEADS = ["Apex-Transport Logistyka", "Eko-Tech Consulting", "Pro-Eko Serwis", "Mega-Pack Polska", "Bud-Expert Projekt", "Trans-Bud-Met", "Novi-Dom", "Alfa-Med Serwis", "Apex Transport Logistyka", "Ekotech Consulting"]
SUFFIXES = ["Sp.k.", "S.A.", "Sp. z o.o.", "Sp. j."]
CONTEXTS = ["Umowa z firmą {} została podpisana.", "Wykonawca: {}\nAdres: ul. Prosta 18", "{}\nul. Fabryczna 10, 31-553 Kraków", "Strony: {} oraz Jan Kowalski."]
CEL = {
 "c01_inline": "Umowa zawarta z ALFA Sp. z o.o. w Krakowie została podpisana.",
 "c02_sprzedawca": "SPRZEDAWCA:\nALFA Sp. z o.o.\nul. Prosta 18, 00-001 Warszawa\nNIP 525-000-11-22",
 "c03_alfa_sa_linia": "FAKTURA VAT\nALFA S.A.\nul. Prosta 18, 31-553 Kraków\nNabywca: Jan Kowalski",
 "c04_expert": "Doradztwo Biznesowe EXPERT S.A. wystawiła fakturę za usługi.",
 "c05_wspolnicy": "Kowalski i Wspólnicy Sp. k. reprezentuje klienta w sprawie.",
 "c06_firma_stop": "Umowa z firmą ALFA Sp. z o.o. została podpisana.",
 "c07_sama_forma": "Forma prawna: Sp. z o.o.\nSpółka z o.o. bez podanej nazwy nie jest identyfikowalna.",
 "c08_piekarnia": "Piekarnia Smaczek Sp. z o.o. dostarczyła pieczywo do sklepu.",
 "c09_marbud": "Przedsiębiorstwo Budowlane MARBUD S.A. wykonało roboty budowlane.",
 "c10_instytucje": "Sąd Rejonowy w Krakowie rozpatrzył sprawę. Urząd Skarbowy w Tarnowie wydał decyzję.",
 "c11_miasta": "Mieszkam w Zakopanem, jutro jadę do Zakopanego. Byłem w Gdyni, w Poznaniu, w Toruniu, w Krakowie, we Wrocławiu, w Katowicach, w Opolu, w Lublinie.",
 "c12_umowa_sprzedawca": "Umowa sprzedaży\nSprzedawca: Hurtownia Bud-Max Sp. z o.o. z siedzibą w Łodzi.\nKupujący: Anna Nowak.",
}
def worker(jobs_path, out_path):
    sys.path.insert(0, os.getcwd())
    res = {"items": []}
    try:
        t_imp = time.perf_counter()
        import pseudominizer_api as api
        res["import_secs"] = round(time.perf_counter() - t_imp, 2)
        from fastapi.testclient import TestClient
        t0 = time.perf_counter()
        with TestClient(api.app, base_url="http://127.0.0.1:8765") as c:
            res["startup_secs"] = round(time.perf_counter() - t0, 2)
            hdr = {"X-Api-Token": Path(api._API_TOKEN_PATH).read_text(encoding="utf-8").strip()}
            for p in json.loads(Path(jobs_path).read_text(encoding="utf-8")):
                t1 = time.perf_counter()
                try:
                    data = Path(p).read_bytes(); ext = Path(p).suffix.lower()
                    mime = "image/png" if ext == ".png" else "text/plain"
                    r = c.post("/preview", files={"file": ("doc" + ext, data, mime)}, headers=hdr)
                    j = r.json()
                    scal = {k: v for k, v in j.items() if isinstance(v, (str, int, float, bool, type(None))) and k not in ("anonymized_preview", "original_text")}
                    it = {"code": r.status_code, "blocked": j.get("blocked"), "error": j.get("error"), "scal": scal,
                          "guard": j.get("guard") or j.get("guard_result") or j.get("guard_questions"),
                          "preview": j.get("anonymized_preview") or "",
                          "tokens": [[t.get("token"), t.get("type"), t.get("original")] for t in j.get("tokens") or []],
                          "orig": j.get("original_text") if ext == ".png" else None}
                except Exception as e:
                    it = {"code": None, "exc": type(e).__name__}
                it["secs"] = round(time.perf_counter() - t1, 3); it["path"] = p
                res["items"].append(it)
    except Exception as e:
        import traceback
        res["startup_error"] = type(e).__name__ + ": " + traceback.format_exc()[-1500:]
    Path(out_path).write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
def main(sha, label, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    full = subprocess.run(["git", "-C", str(REPO), "rev-parse", sha], capture_output=True, check=True, text=True).stdout.strip()
    tmp = Path(tempfile.mkdtemp(prefix="lynx_ff2_"))
    try:
        tar = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", full, "backend"], capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t: t.extractall(tmp / "src", filter="data")
        sw = tmp / "sweep"; sw.mkdir(); jobs = []
        for p in sorted(Path(r"C:/Projects/LynxMask/dataset_clean/docs").glob("*.txt")): jobs.append(("clean", str(p), None))
        for p in sorted(Path(r"C:/Projects/LynxMask/testy").glob("*.txt")): jobs.append(("mobile", str(p), None))
        for p in sorted((REPO / "backend/dataset_20260627_095419/images").glob("*.png")): jobs.append(("img", str(p), None))
        i = 0
        for h, s, c in itertools.product(HEADS, SUFFIXES, CONTEXTS):
            name = f"{h} {s}"; f = sw / f"s{i:03d}.txt"; f.write_text(c.format(name), encoding="utf-8"); i += 1
            jobs.append(("sweep", str(f), name))
        for k, v in CEL.items():
            f = sw / f"{k}.txt"; f.write_text(v, encoding="utf-8"); jobs.append(("cel", str(f), None))
        tmp2 = Path(tempfile.mkdtemp(prefix="lynx_ffr2_"))
        shutil.copytree(tmp / "src" / "backend", tmp2 / "backend")
        (tmp2 / "backend" / "models").mkdir(exist_ok=True)
        shutil.copytree(REPO / "backend/models/ocr", tmp2 / "backend/models/ocr", dirs_exist_ok=True)
        for d in ("anon_profile", "profile", "archive"): (tmp2 / d).mkdir()
        (tmp2 / "jobs.json").write_text(json.dumps([j[1] for j in jobs]), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("LYNX_")}
        env["LYNX_OCR_MODEL_DIR"] = r"C:/Users/p_pie/Desktop/LynxMask-Desktop/backend/models/ocr"
        env.update(ANONYMIZER_PROFILE_DIR=str(tmp2 / "anon_profile"), PROFILE_DIR=str(tmp2 / "profile"), PSE_REGISTRY=str(tmp2 / "pse_registry.json"),
                   ARCHIVE_DIR=str(tmp2 / "archive"), HARDWARE_PROFILE=str(tmp2 / "hardware_profile.json"), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        t0 = time.time()
        subprocess.run([PY, "-B", str(Path(__file__).resolve()), "--worker", str(tmp2 / "jobs.json"), str(tmp2 / "res.json")], cwd=tmp2 / "backend", env=env, capture_output=True, timeout=10000)
        res = json.loads((tmp2 / "res.json").read_text(encoding="utf-8")); res["wall"] = time.time() - t0; res["sha"] = full
        res["jobs"] = [{"set": s, "path": p, "name": n, "text": (Path(p).read_text(encoding="utf-8", errors="replace") if p.endswith(".txt") else None)} for s, p, n in jobs]
        (out / f"raw_{label}.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        print(label, full[:8], len(res.get("items", [])), res.get("startup_error"), round(res["wall"]), res.get("import_secs"), res.get("startup_secs"), flush=True)
        shutil.rmtree(tmp2, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker": worker(sys.argv[2], sys.argv[3])
    else: main(*sys.argv[1:4])
