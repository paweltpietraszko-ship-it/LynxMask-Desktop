"""Co HerBERT mówi o słowach, które prototyp SURNAME-DICT nowo zakrył (kontekst z dokumentów publicznych) + zdania kontrolne."""
import json, os, re, sys
src, cache, base_json, new_json = sys.argv[1:5]
os.chdir(src); sys.path.insert(0, "."); sys.stdout.reconfigure(encoding="utf-8")
import herbert_net
a = json.load(open(base_json, encoding="utf-8")); b = json.load(open(new_json, encoding="utf-8"))
cases = []
for k in b:
    t = json.load(open(os.path.join(cache, k), encoding="utf-8"))["text"]
    for v in sorted(set(b[k]) - set(a.get(k, []))):
        m = re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", t)
        if m:
            cases.append((v, t[max(0, m.start() - 300):m.end() + 300], 300 if m.start() >= 300 else m.start()))
for t, w in [("Wczoraj Nowak zlecił wysłanie paczki.", "Nowak"), ("Paczkę wysłano. Mazur podpisał protokół odbioru.", "Mazur"),
             ("Pismo od Wróbla wpłynęło 3 marca.", "Wróbla"), ("W rozmowie telefonicznej Bocian potwierdził termin.", "Bocian"),
             ("Kawa i herbata zostały zamówione do sali konferencyjnej.", "Kawa"), ("Pismo przekazano do Sali konferencyjnej nr 2.", "Sali"),
             ("Komisja ds. Łączności z Polakami za Granicą przyjęła raport.", "Polakami")]:
    cases.append((w, t, t.index(w)))
for v, ctx, off in cases:
    spans = herbert_net.detect(ctx)
    hit = [(lab, round(sc, 2), ctx[s:e]) for s, e, lab, sc in spans if s <= off < e or (off <= s < off + len(v))]
    print(f"{v:14} -> {hit if hit else 'nic'}")
