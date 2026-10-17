# LYNX-FIRMA-LEGAL-FORM-RESTORE: ta sama firma bez formy i z formą (Sp.k./S.A./Sp. z o.o./Sp. j.) w obu kolejnościach,
# obie z formą, obie bez, + kontrpróby; prawdziwy NER, Full pipeline/Guard. Dane syntetyczne, wynik bez wartości.
# Uruchom z backend/ drzewa, które ma być zmierzone (baza: git worktree), np.: py -3 <ścieżka>/form_sweep.py > wynik.json
import contextlib, io, itertools, json, logging, os, re, sys, tempfile
sys.path[:0] = [".", "../audyt"]
logging.disable(logging.CRITICAL)
HEADS = ["Mega-Pack Polska", "Eko-Tech Consulting", "Apex-Transport Logistyka", "Bud-Expert Projekt", "Novi-Dom", "Alfa-Med Serwis",
         "Ekotech Consulting", "Apex Transport Logistyka"]
FORMS = ["Sp.k.", "S.A.", "Sp. z o.o.", "Sp. j."]
PAIRS = {"bez-z": ("{h}", "{h} {f}"), "z-bez": ("{h} {f}", "{h}"), "z-z": ("{h} {f}", "{h} {f}"), "bez-bez": ("{h}", "{h}")}
TEMPLATE = "Umowa z firmą {a} została podpisana. Wykonawca: {b}\nTermin: 30 dni."
NEGATIVES = ["Forma prawna: Sp.k. oraz Sp. z o.o. bez nazwy.", "Umowa z firmą Mega-Pack Polska Sp.k. Spółka działa od 2010.",
             "Umowa z firmą Mega-Pack Polska Sp.k. i Eko-Tech Consulting S.A. podpisana.", "ZAKRES OBOWIĄZKÓW\nOpis bez firm.",
             "Zwykły tekst bez żadnej firmy.", "Wykonawca: Mega-Pack Polska Sp. z o.o. Sp.k. — zapis błędny."]
FORM_RE = re.compile(r"Sp\.k\.|S\.A\.|Sp\. z o\.o\.|Sp\. j\.")


def main():
    import engine_quality as eq
    import pipeline
    from unmask_sim import unmask
    st = eq.build_state(tempfile.mkdtemp(prefix="lynx_form_"))
    rows = []
    cases = [(k, TEMPLATE.format(a=a.format(h=h, f=f), b=b.format(h=h, f=f)), h)
             for (k, (a, b)), h, f in itertools.product(PAIRS.items(), HEADS, FORMS)]
    cases += [("neg", t, None) for t in NEGATIVES]
    for kind, text, head in cases:
        with contextlib.redirect_stdout(io.StringIO()):
            r = pipeline.pseudonymize_document(text, st)
        restored = unmask(r.text, r.reverse_map) if not r.guard_blocked else None
        name_words = [w for w in re.findall(r"\w{3,}", head or "")]
        rows.append({"kind": kind, "blocked": r.guard_blocked, "exact": restored == text,
                     "forms_src": len(FORM_RE.findall(text)), "forms_out": len(FORM_RE.findall(restored or "")),
                     "name_visible": any(w in r.text for w in name_words),
                     "nested": bool(re.search(r"[A-Z]_\d{3}\w|\w(?:FIRMA|OSOBA)_", r.text))})
    json.dump(rows, sys.stdout)


if __name__ == "__main__":
    main()
