# Diagnoza 2026-10-18: dla każdego pliku -> HTML (odczyt backendu | wynik Desktop) + lista "HerBERT dołożyłby" + JSON do zbiorczego opisu.
# Wyniki (HTML/JSON z treścią dokumentów) zapisuj POZA repo. Backend musi działać (py -3 pseudominizer_api.py).
# Użycie z katalogu repo: py -3 audyt/diagnoza_2026_10_18/diag.py <out_dir poza repo> <plik> [<plik> ...]
import difflib, html, json, pathlib, re, sys, time, urllib.error, urllib.request, uuid

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import herbert_run  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from document_processor import _extract_text  # noqa: E402

CT = {".pdf": "application/pdf", ".txt": "text/plain",
      ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
TOK = re.compile(r"(?:FIRMA|OSOBA|ADRES|INSTYTUCJA|NUMER|EMAIL|KWOTA|DATA)_\d{3}")
UP = "A-ZĄĆĘŁŃÓŚŹŻ"
CAND = re.compile(rf"(?<![\w.])[{UP}][a-ząćęłńóśźż]{{2,}}(?:-[{UP}][a-ząćęłńóśźż]+)?")
HB_TYPES = {"PER", "ORG", "LOC", "ID", "EMAIL", "PHONE", "IBAN"}


def preview(path):
    blob = path.read_bytes()
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {CT.get(path.suffix.lower(), 'application/octet-stream')}\r\n\r\n").encode() + blob + f"\r\n--{b}--\r\n".encode()
    token = (REPO / "backend" / "api_token.txt").read_text(encoding="utf-8").strip()
    req = urllib.request.Request("http://127.0.0.1:8765/preview", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}", "x-api-token": token})
    try:
        return json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read()[:200]!r}"}


def kept_mask(src, out):
    kept = [False] * len(src)
    for a, _, n in difflib.SequenceMatcher(None, src, out, autojunk=False).get_matching_blocks():
        if n >= 3:
            kept[a:a + n] = [True] * n
    return kept


def one(path, out_dir):
    full = _extract_text(path.read_bytes(), path.name)[0]
    r = preview(path)
    src = r.get("original_text") or ""
    out = r.get("anonymized_preview") or ""
    out = out.split("]\n\n", 1)[1] if "]\n\n" in out else out
    blocked = bool(r.get("blocked"))
    rmap = {t["token"]: t["original"] for t in r.get("tokens", [])}
    t0 = time.time()
    hb = [e for e in herbert_run.predict(full) if e[2] in HB_TYPES]
    hb_time = time.time() - t0
    kept = kept_mask(src, out) if out else [True] * len(src)
    # HerBERT-encje widoczne w wyniku Desktop (>=50% liter jawnych) albo poza przetworzoną częścią
    extra = []
    off = full.find(src[:200]) if src else -1
    for s, e, t in hb:
        txt = full[s:e]
        if len(re.sub(r"\W", "", txt)) < 3:
            continue
        a, z = s - off, e - off
        if off >= 0 and 0 <= a and z <= len(src) and src[a:z] == txt:
            idx = [i for i in range(a, z) if src[i].isalnum()]
            vis = sum(kept[i] for i in idx) / max(1, len(idx))
            if vis >= 0.5:
                extra.append((t, txt, "jawne w Desktop"))
        elif off >= 0 and a >= len(src):
            extra.append((t, txt, "poza 15 000 znaków"))
    # HTML
    def r_src():
        parts, i = [], 0
        while i < len(src):
            j = i
            while j < len(src) and kept[j] == kept[i]:
                j += 1
            seg = html.escape(src[i:j]).replace("\n", "<span class=nl>↵</span>\n")
            parts.append(seg if kept[i] else f"<mark class=m>{seg}</mark>")
            i = j
        return "".join(parts)

    def r_out():
        esc = html.escape(out)
        esc = TOK.sub(lambda m: f"<mark class=t title=\"{html.escape(rmap.get(m.group(0), '')).replace(chr(10), ' ')}\">{m.group(0)}</mark>", esc)
        pieces = re.split(r"(<[^>]+>)", esc)
        def cand(m, p):
            prev = p[max(0, m.start() - 3):m.start()]
            return m.group(0) if re.search(r"[.:;!?\n]\s*$|^$", prev) else f"<span class=c>{m.group(0)}</span>"
        pieces = [p if p.startswith("<") else CAND.sub(lambda m, p=p: cand(m, p), p) for p in pieces]
        return "".join(pieces).replace("\n", "<span class=nl>↵</span>\n")

    rows = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(v)}</td></tr>" for k, v in rmap.items())
    hrows = "".join(f"<tr><td>{t}</td><td>{html.escape(x)}</td><td>{w}</td></tr>" for t, x, w in extra)
    status = ("ZABLOKOWANY: " + html.escape("; ".join(map(str, r.get("guard_reasons") or [])))) if blocked else (
        f"BŁĄD: {html.escape(str(r.get('error')))}" if r.get("error") else "OK")
    page = f"""<!doctype html><meta charset=utf-8><title>{html.escape(path.name)}</title>
<style>body{{font:13px/1.45 Consolas,monospace;margin:12px}} .g{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
pre{{white-space:pre-wrap;border:1px solid #ccc;padding:8px;margin:0}} mark.m{{background:#cfe8cf}} mark.t{{background:#ffe08a}}
.c{{background:#ffc9c9}} .nl{{color:#aaa}} table{{border-collapse:collapse;margin-bottom:12px}} td{{border:1px solid #ddd;padding:2px 6px}}</style>
<h3>{html.escape(path.name)} — {status} — odczytane {len(full)} znaków, przetworzone {len(src)}</h3>
<p>Lewa: tekst odczytany przez backend, <mark class=m>zielone</mark> = zniknęło z wyniku. Prawa: wynik Desktop,
<mark class=t>żółte</mark> = token (najedź = oryginał), <span class=c>różowe</span> = jawne słowo z wielkiej litery w środku zdania (podpowiedź). ↵ = koniec wiersza.</p>
<h3>HerBERT dołożyłby ({len(extra)}) — podpowiedź modelu, nie werdykt</h3><table>{hrows}</table>
<div class=g><pre>{r_src()}</pre><pre>{r_out()}</pre></div>
<h3>Tokeny Desktop ({len(rmap)})</h3><table>{rows}</table>"""
    name = path.parent.parent.name + "_" + path.stem
    (out_dir / f"{name}.html").write_text(page, encoding="utf-8")
    rec = {"file": str(path), "status": status[:120], "full": len(full), "processed": len(src), "tokens": rmap,
           "herbert_extra": extra, "herbert_s": round(hb_time, 1), "out": out}
    (out_dir / f"{name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{name:40} {status[:40]:40} znaki {len(full):6}/{len(src):6} tokeny {len(rmap):3} HerBERT+ {len(extra):3} ({hb_time:.1f}s)")


if __name__ == "__main__":
    od = pathlib.Path(sys.argv[1]); od.mkdir(parents=True, exist_ok=True)
    for f in sys.argv[2:]:
        try:
            one(pathlib.Path(f), od)
        except Exception as e:
            print(f, "BŁĄD NARZĘDZIA", type(e).__name__, e)
