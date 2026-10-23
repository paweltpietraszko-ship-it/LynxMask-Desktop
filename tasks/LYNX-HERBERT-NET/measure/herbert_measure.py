"""LYNX-HERBERT-NET: pomiar przebiegow /preview (TestClient, w procesie, pusty izolowany profil). Bez danych w srodku.
Uzycie (z dowolnego katalogu):
  python herbert_measure.py run <nazwa> <sha|-> <LYNX_HERBERT|-> <MIN|-> <znany|wszystko|dlugi> [out_dir]
  (worker: python herbert_measure.py --worker jobs.json out.json)
Sciezki zbiorow i modeli podane na stale ponizej (maszyna CC); dane zbiorow czytane tylko z dataset_clean / testy Mobile / benchmark 20260627 (syntetyczne).
"""
import io, itertools, json, logging, os, shutil, subprocess, sys, tarfile, tempfile, time, ctypes
from ctypes import wintypes
from pathlib import Path

REPO = Path(r"C:/Users/p_pie/Desktop/LynxMask-Desktop")
WT = Path(r"C:/Users/p_pie/AppData/Local/Temp/claude/C--Users-p-pie-Desktop-LynxMask-Desktop/6fd99904-330e-4b1d-93e7-d4df460463ee/scratchpad/wt_herbert")
OUT = Path(r"C:/Users/p_pie/AppData/Local/Temp/lynx_cc_review/herbert_net")
PY = str(REPO / ".venv/Scripts/python.exe")
HERBERT_DIR = "C:/Users/p_pie/AppData/Local/Temp/claude/C--Users-p-pie-Desktop-LynxMask-Desktop/6fd99904-330e-4b1d-93e7-d4df460463ee/scratchpad/wt_herbert/backend/models/herbert"
OCR_SRC = REPO / "backend/models/ocr"   # WT nie ma modeli OCR; ten sam komplet co w repo wlasciciela
CLEAN = Path(r"C:/Projects/LynxMask/dataset_clean/docs")
MOBILE = Path(r"C:/Projects/LynxMask/testy")
IMGS = REPO / "backend/dataset_20260627_095419/images"
HEADS = ["Apex-Transport Logistyka", "Eko-Tech Consulting", "Pro-Eko Serwis", "Mega-Pack Polska", "Bud-Expert Projekt",
         "Trans-Bud-Met", "Novi-Dom", "Alfa-Med Serwis", "Apex Transport Logistyka", "Ekotech Consulting"]
SUFFIXES = ["Sp.k.", "S.A.", "Sp. z o.o.", "Sp. j."]
CONTEXTS = ["Umowa z firmą {} została podpisana.", "Wykonawca: {}\nAdres: ul. Prosta 18", "{}\nul. Fabryczna 10, 31-553 Kraków",
            "Strony: {} oraz Jan Kowalski."]
EXTRAS = ["Umowa z ALFA Sp. z o.o. została podpisana.", "Sprawa w Urząd Skarbowy w Krakowie.", "Wyrok wydał Sąd Rejonowy w Gliwicach.",
          "Faktura od ALFA Sp. z o.o. dla Jana Kowalskiego."]


# ---------------------------------------------------------------- worker
def _peak_rss():
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ps = ctypes.WinDLL("psapi", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    c = PMC(); c.cb = ctypes.sizeof(PMC)
    ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return {"peak_ws_mb": round(c.PeakWorkingSetSize / 1048576, 1), "ws_mb": round(c.WorkingSetSize / 1048576, 1)}


class _Cap(logging.Handler):
    def __init__(self): super().__init__(logging.INFO); self.buf = []
    def emit(self, r): self.buf.append(r.getMessage())


def worker(jobs_path, out_path):
    sys.path.insert(0, os.getcwd())
    res = {"items": []}
    try:
        import pseudominizer_api as api
        from fastapi.testclient import TestClient
        cap = _Cap()
        spans = []
        if os.environ.get("HM_SPANS"):   # opakowanie po stronie pomiaru (kod produktu bez zmian): zapis wszystkich spanow siatki
            import herbert_net as hn
            _d = hn.detect
            def _w(text):
                r = _d(text)
                spans.extend({"v": text[s:e], "k": k, "p": round(p, 3), "ctx": text[max(0, s - 40):e + 40]} for s, e, k, p in r)
                return r
            hn.detect = _w
        lg = logging.getLogger("lynxmask.herbert_net"); lg.setLevel(logging.INFO); lg.addHandler(cap)
        t0 = time.perf_counter()
        with TestClient(api.app, base_url="http://127.0.0.1:8765") as c:
            res["startup_secs"] = round(time.perf_counter() - t0, 2)
            res["rss_after_startup"] = _peak_rss()
            hdr = {"X-Api-Token": Path(api._API_TOKEN_PATH).read_text(encoding="utf-8").strip()}
            for job in json.loads(Path(jobs_path).read_text(encoding="utf-8")):
                p = job["path"]; cap.buf.clear(); t1 = time.perf_counter()
                try:
                    ext = Path(p).suffix.lower()
                    mime = "image/png" if ext == ".png" else "text/plain"
                    r = c.post("/preview", files={"file": ("doc" + ext, Path(p).read_bytes(), mime)}, headers=hdr)
                    j = r.json()
                    it = {"code": r.status_code, "blocked": j.get("blocked"), "error": j.get("error"),
                          "preview": j.get("anonymized_preview") or "",
                          "tokens": [[t.get("token"), t.get("type"), t.get("original")] for t in j.get("tokens") or []],
                          "orig": j.get("original_text") if ext == ".png" else None}
                except Exception as e:
                    it = {"code": None, "exc": type(e).__name__ + ": " + str(e)[:200]}
                it["secs"] = round(time.perf_counter() - t1, 3)
                it["herbert_log"] = list(cap.buf)
                it["hn_spans"] = list(spans); spans.clear()
                it.update(job)
                res["items"].append(it)
            res["rss_end"] = _peak_rss()
    except Exception:
        import traceback
        res["startup_error"] = traceback.format_exc()[-2000:]
    Path(out_path).write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- jobs
def build_jobs(kind, workdir):
    cl = sorted(CLEAN.glob("*.txt"))
    if kind == "dlugi":   # ~60 tys. znakow: dokumenty z BETA S.A. (jawna tylko dla siatki) na poczatku, w srodku i na samym koncu
        beta = [p for p in cl if "BETA S.A." in p.read_text(encoding="utf-8")]
        fill = [p for p in cl[150:] if p not in beta]
        parts, n = [beta[-1].read_text(encoding="utf-8")], 0
        for i, p in enumerate(fill):
            parts.append(p.read_text(encoding="utf-8"))
            if sum(map(len, parts)) > 30000 and n == 0:
                parts.append(beta[-2].read_text(encoding="utf-8")); n = 1
            if sum(map(len, parts)) > 60000:
                break
        parts.append(beta[-3].read_text(encoding="utf-8"))
        f = Path(workdir) / "dlugi.txt"; f.write_text("\n\n".join(parts), encoding="utf-8")
        return [{"set": "dlugi", "path": str(f), "chars": f.stat().st_size}]
    znany = [{"set": "clean", "path": str(p)} for p in cl[:150]]
    sw = Path(workdir) / "sweep"; sw.mkdir(parents=True, exist_ok=True)
    for i, (h, s, c) in enumerate(itertools.product(HEADS, SUFFIXES, CONTEXTS)):
        f = sw / f"s{i:03d}.txt"; f.write_text(c.format(f"{h} {s}"), encoding="utf-8")
        znany.append({"set": "sweep", "path": str(f), "name": f"{h} {s}"})
    if kind == "znany":
        return znany
    kontr = [{"set": "clean", "path": str(p)} for p in cl[150:]]
    kontr += [{"set": "mobile", "path": str(p)} for p in sorted(MOBILE.glob("*.txt"))]
    kontr += [{"set": "img", "path": str(p)} for p in sorted(IMGS.glob("*.png"))]
    ex = Path(workdir) / "extra"; ex.mkdir(exist_ok=True)
    for i, t in enumerate(EXTRAS):
        (ex / f"e{i}.txt").write_text(t, encoding="utf-8"); kontr.append({"set": "extra", "path": str(ex / f"e{i}.txt")})
    if kind == "wszystko":
        return znany + kontr
    if kind == "text":   # ZNANY + KONTROLNY bez obrazow (porownanie z main)
        return [j for j in znany + kontr if not j["path"].endswith(".png")]
    raise SystemExit("kind?")


def run(name, sha, mode, minv, kind, out_dir=OUT):
    tmp = Path(tempfile.mkdtemp(prefix="lynx_hn_" + name + "_"))
    try:
        tar = subprocess.run(["git", "-C", str(WT), "archive", "--format=tar", sha, "backend"], capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(tmp, filter="data")
        (tmp / "backend" / "models").mkdir(exist_ok=True)
        shutil.copytree(OCR_SRC, tmp / "backend/models/ocr", dirs_exist_ok=True)
        for d in ("anon_profile", "profile", "archive"):
            (tmp / d).mkdir()
        jobs = build_jobs(kind, tmp)
        if os.environ.get("HM_LIMIT"):
            jobs = jobs[:int(os.environ["HM_LIMIT"])]
        (tmp / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("LYNX_")}
        env.update(ANONYMIZER_PROFILE_DIR=str(tmp / "anon_profile"), PROFILE_DIR=str(tmp / "profile"),
                   PSE_REGISTRY=str(tmp / "pse_registry.json"), ARCHIVE_DIR=str(tmp / "archive"),
                   HARDWARE_PROFILE=str(tmp / "hardware_profile.json"), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
                   LYNX_OCR_MODEL_DIR=str(tmp / "backend/models/ocr").replace("\\", "/"))
        if mode != "-":
            env.update(LYNX_HERBERT=mode, LYNX_HERBERT_MODEL_DIR=HERBERT_DIR)
        if minv != "-":
            env["LYNX_HERBERT_MIN"] = minv
        t0 = time.time()
        pr = subprocess.run([PY, "-B", str(Path(__file__).resolve()), "--worker", str(tmp / "jobs.json"), str(tmp / "res.json")],
                            cwd=tmp / "backend", env=env, capture_output=True, timeout=20000)
        f = tmp / "res.json"
        res = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {"startup_error": "no_result " + pr.stderr[-800:].decode("utf-8", "replace")}
        res["wall"] = round(time.time() - t0, 1)
        res["meta"] = {"name": name, "sha": sha, "mode": mode, "min": minv, "kind": kind}
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / f"raw_{name}.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        print(name, len(res.get("items", [])), res.get("startup_error"), res["wall"], flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        worker(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "run":
        run(*sys.argv[2:8], *([sys.argv[8]] if len(sys.argv) > 8 else []))
