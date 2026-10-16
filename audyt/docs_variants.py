"""Warianty z bench_offline.py na dokumentach z 'Pliki testowe/': które wycieki z audytu znikają,
ile tokenów dochodzi (z regułą kotwicy). Wypisuje tylko zamaskowane wartości.
Użycie: python audyt/docs_variants.py --mobile ścieżka_repo_mobile"""
import sys, os, re, glob, argparse, logging, collections
logging.disable(logging.CRITICAL)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_offline as bo                    # noqa: E402  (ustawia ścieżki i chdir do backend/)
from anchor_proto import apply_anchor         # noqa: E402

# Wycieki z FINDING_2026-10_AUDYT.md §3d (wzorce dopasowujące wartość w wyniku)
LEAKS = {
    "doc_lvl0_umowa_o_prace.txt": [r"Katarzyna Wiśniewska", r"PL6110"],
    "doc_lvl3_faktura_zlecenie.txt": [r"Ryszard\w* Kowalczyk\w*"],
    "doc_test_nowe_encje.txt": [r"Małgorzat\w* Kamińsk\w*", r"córka Jan\w*"],
}


def m(s):
    return re.sub(r"([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]{3})[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+", lambda x: x.group(1) + "*" * (len(x.group(0)) - 3), s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--mobile"); a = ap.parse_args()
    import importlib
    docs = sorted(glob.glob(os.path.join(HERE, "..", "Pliki testowe", "*.txt")))
    for variant in ("base", "anchor", "prefixm", "pakiet"):
        import ner_layer, pipeline_new, pipeline, layers.ocr_normalizer as on, layers.ner_adapter as na
        for mod in (ner_layer, on, na, pipeline_new, pipeline):
            importlib.reload(mod)
        if variant in ("prefixm", "pakiet"):
            bo.patch_prefix(bo.name_dicts(a.mobile))
        if variant == "pakiet":
            bo.patch_pakiet()
        from repro_pipeline import build_state
        tot_leak = tot_tok = 0; added = collections.Counter(); samples = collections.defaultdict(list)
        for f in docs:
            st = build_state(False)
            r = pipeline.pseudonymize_document(open(f, encoding="utf-8").read(), st)
            txt, rev = r.text, r.reverse_map
            if variant in ("anchor", "pakiet"):
                txt, al = apply_anchor(txt, rev)
                rev = al.rev
                for rule, tok, val in al.added:
                    added[rule] += 1
                    samples[rule].append(m(val.replace("\n", " "))[:45])
            leaks = [p for p in LEAKS.get(os.path.basename(f), []) if re.search(p, txt)]
            tot_leak += len(leaks); tot_tok += len(rev)
        print(f"{variant:8} wycieki z audytu w wyniku: {tot_leak}/5 | tokenów razem: {tot_tok} | dodane przez kotwice: {dict(added)}")
        for rule, ex in samples.items():
            print(f"{'':10}{rule}: {ex[:6]}")
