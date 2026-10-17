# LYNX-FIRMA-HYPHEN-SUFFIX: rodzina nazw firm (łącznik / bez, Sp.k. / S.A. / Sp. z o.o. / Sp. j.) w kilku kontekstach,
# prawdziwy NER (Full), baza (= bez _firma_entities, czyli kod sprzed Tasku) vs bieżący + kontrpróby. Dane syntetyczne. Uruchom z backend/.
import contextlib, io, itertools, logging, os, re, sys, tempfile
from unittest.mock import patch
sys.path[:0] = [".", "../audyt"]
logging.disable(logging.CRITICAL)
HEADS = ["Apex-Transport Logistyka", "Eko-Tech Consulting", "Pro-Eko Serwis", "Mega-Pack Polska", "Bud-Expert Projekt",
         "Trans-Bud-Met", "Novi-Dom", "Alfa-Med Serwis", "Apex Transport Logistyka", "Ekotech Consulting"]
SUFFIXES = ["Sp.k.", "S.A.", "Sp. z o.o.", "Sp. j."]
CONTEXTS = ["Umowa z firmą {} została podpisana.", "Wykonawca: {}\nAdres: ul. Prosta 18", "{}\nul. Fabryczna 10, 31-553 Kraków",
            "Strony: {} oraz Jan Kowalski."]
NEGATIVES = ["Flaga jest biało-czerwona, a spółka S.A. nie została wskazana.", "Wniosek do ZUS i KNF złożono w terminie.",
             "ZAKRES OBOWIĄZKÓW\nOpis stanowiska.", "Forma prawna: Sp. z o.o.", "Spotkanie w Bielsko-Białej odbyło się wczoraj.",
             "Pan Jan Nowak-Kowalski podpisał wniosek.", "Umowa z Apex-Transport Sp. z o.o. i Eko-Tech S.A. Następne zdanie."]


def run():
    import engine_quality as eq
    import ner_layer
    import pipeline
    from unmask_sim import unmask
    tmp = tempfile.TemporaryDirectory()
    st = eq.build_state(tmp.name)

    def go(text, base):
        ctx = patch.object(ner_layer, "_firma_entities", lambda t, rs: rs) if base else contextlib.nullcontext()
        with ctx, contextlib.redirect_stdout(io.StringIO()):
            return pipeline.pseudonymize_document(text, st)

    stats = {"base": {}, "task": {}}
    regress, broken, base_broken = [], [], 0
    for head, suf, c in itertools.product(HEADS, SUFFIXES, CONTEXTS):
        name = f"{head} {suf}"
        text = c.format(name)
        for label in ("base", "task"):
            res = go(text, label == "base")
            s = eq.classify_m1(text, name, "FIRMA", res)
            stats[label][s] = stats[label].get(s, 0) + 1
            bad_rt = not res.guard_blocked and (unmask(res.text, res.reverse_map) != text
                                                or re.search(r"[A-Z]_\d{3}\w|\w(?:FIRMA|OSOBA)_", res.text))
            if label == "base":
                base_broken += bool(bad_rt)
            else:
                if s != "masked" and base_s == "masked":
                    regress.append((name, c[:12], s))
                if bad_rt:
                    broken.append((name, c[:12]))
            base_s = s
    neg = []
    for t in NEGATIVES:
        b, a = go(t, True), go(t, False)
        if (b.text, b.reverse_map) != (a.text, a.reverse_map):
            neg.append((t[:40], sorted(b.reverse_map.values()), sorted(a.reverse_map.values())))
        if not a.guard_blocked and unmask(a.text, a.reverse_map) != t:
            broken.append((t[:30], "neg"))
    return stats, regress, broken, neg, base_broken


if __name__ == "__main__":
    stats, regress, broken, neg, base_broken = run()
    print("przypadków", sum(stats["task"].values()), "| baza", stats["base"], "| po", stats["task"])
    print("regresje", len(regress), regress[:8])
    print("Przywróć/token-w-tokenie: baza", base_broken, "po", len(broken), broken[:8])
    print("kontrpróby ze zmianą wyniku", len(neg))
    for n in neg:
        print("  ", n)
