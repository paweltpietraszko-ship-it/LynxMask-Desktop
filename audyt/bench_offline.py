"""Benchmark offline (bez HTTP) na zbiorze wygenerowanym przez benchmark.py — ta sama logika
co /preview (OCR → odrzucenie OCR → pseudonymize_document → tokeny) i ta sama ocena
(benchmark.analyze / build_report). OCR liczony raz i cache'owany (--cache, poza repo).
Warianty to wyłącznie monkeypatche w procesie audytu — kod produktu bez zmian.

  base     — Desktop jak dziś (świeży profil, bez seeda)
  anchor   — base + prototyp AnchorEngine (audyt/anchor_proto.py) jako post-pass
  prefix   — base + zasada Mobile: OSOBA, której słowo jest w słowniku imion/nazwisk,
             omija blocklistę (słowniki Desktop: names_inflected + surnames_top1000)
  prefixm  — jak prefix, ale słowniki Mobile (names 3,6k + top1000 + formy żeńskie) z --mobile
  pakiet   — prefixm + IBAN przed credentials (IBAN_EARLY) + telefon po 'tel.' wg Mobile
             + _fix_ocr_email tylko przy '@' + anchor

Użycie: python audyt/bench_offline.py --dataset DIR --cache plik.json --out DIR
        [--variants base,anchor,...] [--mobile ścieżka_repo_mobile]"""
import sys, os, re, json, argparse, logging, io, contextlib
from pathlib import Path
logging.disable(logging.CRITICAL)
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "..", "backend")
sys.path.insert(0, HERE); sys.path.insert(0, B); os.chdir(B)

import benchmark                              # noqa: E402
from anchor_proto import apply_anchor         # noqa: E402

MAX_TEXT_CHARS = 15_000


def ocr_all(dataset: Path, cache: Path) -> dict:
    if cache.exists():
        return json.load(open(cache, encoding="utf-8"))
    from document_processor import _extract_text
    gt = json.load(open(dataset / "ground_truth.json", encoding="utf-8"))
    out = {}
    for g in gt:
        p = dataset / "images" / Path(g["file"]).name
        text, err, meta = _extract_text(p.read_bytes(), p.name)
        out[g["file"]] = {"text": text, "err": err, "meta": meta}
    json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def name_dicts(mobile: str | None):
    def forms(path):
        d = json.load(open(path, encoding="utf-8"))
        return set(d) | {f for v in d.values() for f in v}
    if mobile:
        a = os.path.join(mobile, "app/src/main/assets")
        names, surn = forms(os.path.join(a, "names_inflected.json")), forms(os.path.join(a, "surnames_top1000.json"))
        fem = set()
        for s in surn:                     # jak LookupTables.generateFeminineVariants (uproszczone: -ski/-cki/-dzki)
            for x, y in (("ski", "ska"), ("cki", "cka"), ("dzki", "dzka")):
                if s.endswith(x):
                    st = s[: -len(x)]
                    fem |= {st + y, st + y[:-1] + "iej", st + y[:-1] + "ą"}
        return {w.lower() for w in names | surn | fem}
    return {w.lower() for w in forms("names_inflected.json") | forms("surnames_top1000.json")}


def patch_prefix(dict_words):
    """Zasada Mobile (NameEngine.isAdjective: 'surnamesForms ZAWSZE przed filtrem'):
    OSOBA ze słowem ze słownika imion/nazwisk nie przechodzi przez blocklistę."""
    import ner_layer
    orig = ner_layer._filter_institutions
    if getattr(orig, "_audyt", False):
        orig = orig._orig

    def patched(results):
        out = []
        for ner in results:
            words = re.findall(r"[^\W\d_]+", ner.text.lower())
            if ner.label == "OSOBA" and any(w in dict_words for w in words):
                bl, pf = ner_layer._NER_BLOCKLIST, ner_layer._NER_BLOCKLIST_PREFIXES
                ner_layer._NER_BLOCKLIST, ner_layer._NER_BLOCKLIST_PREFIXES = frozenset(), frozenset()
                try:
                    out += orig([ner])
                finally:
                    ner_layer._NER_BLOCKLIST, ner_layer._NER_BLOCKLIST_PREFIXES = bl, pf
            else:
                out += orig([ner])
        return out
    patched._audyt, patched._orig = True, orig
    ner_layer._filter_institutions = patched


def patch_pakiet():
    import pipeline_new, layers.ocr_normalizer as on, layers.ner_adapter as na
    fin, cred = pipeline_new.apply_financial_layer, pipeline_new.apply_credentials_layer

    def cred_after_iban(state):          # IBAN_EARLY: IBAN zabiera terytorium przed wzorcami cyfr
        fin(state); state.allocator.reset_spans(); cred(state)
    pipeline_new.apply_credentials_layer = cred_after_iban
    # OcrNormalizer.kt OCR_PHONE_AFTER_KW: koniec na cyfrze, litery tylko l/O/I/o
    on._PHONE_AFTER_KW_RE = re.compile(
        r"(?i)\b(tel(?:efon)?|kom(?:\.|orkowy)?|mob(?:\.|ile)?|fax|faks)\.?[^\S\n]*[:–\-]?[^\S\n]*(\+?(?:48[^\S\n]*)?[\d\s\-().lOIo]{7,22}\d)")
    # OcrNormalizer.kt OCR_EMAIL_*: spacje usuwane tylko przy '@', bez przekraczania \n
    def fix_email(text):
        text = re.sub(r"(@)[^\S\n]+([a-zA-Z0-9])", r"\1\2", text)
        text = re.sub(r"([a-zA-Z0-9._%+\-]*\.[a-zA-Z0-9._%+\-]+)[^\S\n]+([a-zA-Z0-9._%+\-]+@)", r"\1\2", text)
        return text
    na._fix_ocr_email = fix_email


def run_variant(name, gt, ocr, out_dir, mobile):
    import importlib, ner_layer, pipeline_new, layers.ocr_normalizer as on, layers.ner_adapter as na
    for m in (ner_layer, on, na, pipeline_new):
        importlib.reload(m)
    from repro_pipeline import build_state
    import pipeline
    importlib.reload(pipeline)
    if name in ("prefix",):
        patch_prefix(name_dicts(None))
    if name in ("prefixm", "pakiet"):
        patch_prefix(name_dicts(mobile))
    if name == "pakiet":
        patch_pakiet()
    use_anchor = name in ("anchor", "pakiet")
    st = build_state(False)
    results = []
    for g in gt:
        o = ocr[g["file"]]
        meta, text = o["meta"], (o["text"] or "").strip()[:MAX_TEXT_CHARS]
        if o["err"]:
            resp = {"error": o["err"], "ocr": meta, "bench_http_status": 400}
        elif meta and meta.get("quality") == "reject":
            resp = {"ocr_rejected": True, "ocr": meta, "bench_http_status": 422}
        else:
            r = pipeline.pseudonymize_document(text, st)
            txt, rev = r.text, r.reverse_map
            if use_anchor:
                txt, al = apply_anchor(txt, rev)
                rev = al.rev
            toks = [{"token": k, "original": v, "type": k.rsplit("_", 1)[0]} for k, v in rev.items()]
            resp = {"tokens": toks, "anonymized_preview": txt, "blocked": r.guard_blocked,
                    "guard_reasons": r.guard_reasons, "ocr": meta, "bench_http_status": 200}
        results.append(benchmark.analyze(g, resp))
    d = Path(out_dir) / name
    d.mkdir(parents=True, exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        benchmark.build_report(results, d)
    acc = [x for x in results if not x["ocr_rejected"] and x.get("http_status") == 200]
    ents = [e for x in acc for e in x["entities"]]
    fp = sum(len(x["false_positives"]) for x in acc)
    found = sum(e["privacy_found"] for e in ents)
    crit = [e for e in ents if e["critical"]]
    per = {}
    for e in ents:
        t = e["expected_type"]; per.setdefault(t, [0, 0]); per[t][0] += e["privacy_found"]; per[t][1] += 1
    toks = sum(len(x["tokens_found"]) for x in acc)
    prec = (toks - fp) / toks if toks else 0
    rec = found / len(ents)
    return {"variant": name, "docs": len(acc), "recall": rec, "precision": prec, "f1": 2 * rec * prec / (rec + prec),
            "fp": fp, "critical_leak": 1 - sum(e["privacy_found"] for e in crit) / len(crit),
            "per_type": {k: f"{v[0]}/{v[1]}" for k, v in sorted(per.items())}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--cache", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--variants", default="base,anchor,prefix,prefixm,pakiet"); ap.add_argument("--mobile")
    a = ap.parse_args()
    ds = Path(a.dataset)
    gt = json.load(open(ds / "ground_truth.json", encoding="utf-8"))
    ocr = ocr_all(ds, Path(a.cache))
    rows = []
    for v in a.variants.split(","):
        r = run_variant(v, gt, ocr, a.out, a.mobile)
        rows.append(r)
        print(f"{v:8} docs={r['docs']} R={100*r['recall']:.1f}% P={100*r['precision']:.1f}% F1={100*r['f1']:.1f}% FP={r['fp']} "
              f"CLR={100*r['critical_leak']:.1f}% | {r['per_type']}", flush=True)
    json.dump(rows, open(Path(a.out) / "_porownanie.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
