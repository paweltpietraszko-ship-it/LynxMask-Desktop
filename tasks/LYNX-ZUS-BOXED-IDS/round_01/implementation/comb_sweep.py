# LYNX-ZUS-BOXED-IDS: przegląd formularzy AcroForm z polami kratkowymi (comb) — reportlab + wypełnienie pypdf jak w próbce
# ZUS; PESEL/NIP w każdej parze z polami kontrolnymi, w obu kolejnościach, pola sąsiadujące (cyfry pod sobą w get_text).
# Baza (main) vs bieżący _extract_text, potem pipeline w obu trybach, NER wyłączony, dane syntetyczne. Uruchom z backend/.
import contextlib, importlib.util, io, itertools, re, subprocess, sys
from unittest.mock import patch
sys.path[:0] = [".", "../audyt"]
BASE = "29f130b"  # main przed Taskiem (po NEWLINE-CROSSING i DOCX-TABLES)
# nazwa: (wartość, maxlen, comb, czy poprawka ma ją zgrupować)
F = {"PESEL": ("44051401359", 11, True, True), "NIP": ("5260001246", 10, True, True),
     "NIP_PREF": ("4405140135", 10, True, True),            # NIP = początek PESEL-u
     "PESEL2": ("44051401359", 11, True, True),             # ten sam PESEL w drugim polu
     "TEL": ("512987654", 9, True, False), "DATA": ("14051944", 8, True, False), "REGON": ("123456785", 9, True, False),
     "PESEL_NOCOMB": ("90090515836", 11, False, False),     # zwykłe pole: cyfry w jednej linii (już maskowane)
     "TXT11": ("ABCDEFGHIJK", 11, True, False)}


def pdf(names, singles=0, page2=False):
    import pypdf
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 800, "Dane ubezpieczonego")
    vals, y = {}, 740
    for i, n in enumerate(names):
        v, maxlen, comb, _ = F[n]
        c.drawString(50, y + 4, f"Pole {i + 1}:")
        c.acroForm.textfield(name=f"f{i}", x=150, y=y, width=18 * maxlen, height=17, maxlen=maxlen,
                             fieldFlags="comb" if comb else "", borderWidth=1)
        vals[f"f{i}"], y = v, y - 30
    for k in range(singles):  # osobne pola jednoznakowe (kratki bez wspólnego pola) — nie wolno ich łączyć
        c.acroForm.textfield(name=f"s{k}", x=150 + 18 * k, y=y, width=18, height=17, maxlen=1, borderWidth=1)
        vals[f"s{k}"] = "44051401359"[k]
    c.drawString(50, 100, "Koniec formularza.")
    if page2:
        c.showPage()
        c.drawString(50, 800, "Strona 2")
    c.save()
    r = pypdf.PdfReader(io.BytesIO(buf.getvalue()))
    w = pypdf.PdfWriter()
    w.clone_document_from_reader(r)
    w.update_page_form_field_values(w.pages[0], vals)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def old_extract():
    src = subprocess.run(["git", "show", f"{BASE}:backend/document_processor.py"], capture_output=True, text=True,
                         encoding="utf-8").stdout
    spec = importlib.util.spec_from_loader("dp_base", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = "document_processor.py"
    exec(compile(src, "dp_base", "exec"), mod.__dict__)
    return mod._extract_text


def cases():
    names = list(F)
    out = [(a, b) for a, b in itertools.permutations(names, 2)]
    out += [(n,) for n in names]
    return out


def run():
    import layers.ner_adapter as na
    from document_processor import _extract_text
    from pipeline_new import run_pipeline_new, run_pipeline_express
    from unmask_sim import unmask
    old = old_extract()
    bad, n, base_bad = [], 0, 0
    docs = [(c, pdf(c)) for c in cases()] + [(("SINGLES",), pdf([], singles=11)), (("PESEL", "P2"), pdf(["PESEL"], page2=True))]
    for names, blob in docs:
        text, err, _ = _extract_text(blob, "f.pdf")
        base_text = old(blob, "f.pdf")[0]
        fix = [F[k][0] for k in names if k in F and F[k][3]]
        expect = base_text  # dokładnie bazowy tekst, w którym ciągi cyfra-na-linię grupowanych pól zastąpiono wartością
        for v in sorted(set(fix), key=len, reverse=True):
            expect = re.sub(r"(?<![^\n])" + re.escape("\n".join(v) + "\n"), v + "\n", expect)
        base_bad += any(v not in base_text.split("\n") for v in fix)
        for fn in (run_pipeline_new, run_pipeline_express):
            n += 1
            with patch.object(na, "process_ner", return_value=({}, {})), contextlib.redirect_stdout(io.StringIO()):
                masked, rev, _ = fn(text, anon_map={})
            lines = masked.split("\n")
            problem = (err or text != expect or any(text.split("\n").count(v) != fix.count(v) for v in fix)
                       or any(v in masked for v in fix) or any(sorted(rev.values()).count(v) != 1 for v in set(fix))
                       or masked.count("\n") != text.count("\n") or unmask(masked, rev) != text
                       or re.search(r"[0-9A-Z](?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|EMAIL)_|_[0-9]{4}", masked) or "Koniec formularza." not in lines)
            if problem:
                bad.append((names, fn.__name__))
    return n, bad, base_bad, len(docs)


if __name__ == "__main__":
    n, bad, base_bad, nd = run()
    print(f"dokumentów {nd}, przypadków {n}: problemy {len(bad)}; baza: dokumenty z PESEL/NIP bez pełnej wartości {base_bad}")
    for b in bad[:12]:
        print("  ", b)
