"""Ataki CC r1 na Arenę v0.1 (syntetyki, bez danych realnych). Gold i oczekiwania ustalone PRZED uruchomieniem.

Uruchomienie: py -3 tasks/LYNX-ARCH-ARENA/attacks/attacks_cc_r1.py   (z katalogu repo)
Sędzia jak w brief r2/C2: tylko gold i tekst. STOP poprawny tylko gdy stop_ok=True (formalna przyczyna z kontraktu
I sensowna odmowa); każdy inny STOP = UNEXPECTED_STOP. Wynik: tabela + liczby; bez wartości poza syntetykami.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SIM = os.path.join(ROOT, "backend", "arena_sim.py")


def c(s, e, k, src="Engine"):
    return {"start": s, "end": e, "kind": k, "source": src, "evidence": ["FORMAT"]}


def span(text, sub, k, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = text.index(sub, i + 1)
    return (i, i + len(sub), k)


T = {}  # id → (text, base, gold, stop_ok, cel ataku)


def add(cid, text, base, gold, stop_ok, why):
    T[cid] = (text, base, gold, stop_ok, why)


t = "Lista: a@b.pl,c@d.pl"
add("X01", t, [], [span(t, "a@b.pl", "EMAIL"), span(t, "c@d.pl", "EMAIL")], False,
    "lista e-maili bez spacji (CSV/OCR) → nakładające się kotwice → STOP całego dokumentu")
t = "Spotkanie @ 10:00 w sali B."
add("X02", t, [], [], False, "zwykłe użycie @ ze spacją → ANCHOR_UNCERTAIN blokuje cały dokument bez PII")
t = "Pisz: ala .kot@firma.pl"
add("X03", t, [], [span(t, "ala .kot@firma.pl", "EMAIL")], False, "OCR: spacja w części lokalnej → FN_PARTIAL")
t = "Pisz: ala@firma. pl dziś"
add("X04", t, [], [span(t, "ala@firma. pl", "EMAIL")], False, "OCR: spacja PO kropce domeny → ogon nie łapie")
t = "Adres: ul. Jana Pawła II 5, Kraków"
add("X05", t, [], [span(t, "ul. Jana Pawła II 5", "ADRES")], False, "ulica 3-członowa + numer → limit 3 członów")
t = "Adres: ul. Św. Marcin 5"
add("X06", t, [], [span(t, "ul. Św. Marcin 5", "ADRES")], False, "skrót z kropką w nazwie ulicy")
t = "Adres: al. Jerozolimskie 5"
add("X07", t, [], [span(t, "al. Jerozolimskie 5", "ADRES")], False, "aleja — brak kotwicy, Guard też milczy")
t = "Adres: ul Polna 5"
add("X08", t, [], [span(t, "ul Polna 5", "ADRES")], False, "ul bez kropki (OCR) — FN i brak flagi Guarda")
t = "Mieszka przy ul. Jana Kowalskiego 5."
add("X09", t, [c(*span(t, "Jana Kowalskiego", "OSOBA")[:2], "OSOBA", "NER")],
    [span(t, "ul. Jana Kowalskiego 5", "ADRES")], False, "ulica z nazwiskiem + NER widzi osobę → STOP")
t = "Pełnomocnik: Kowalski i Wspólnicy Sp. z o.o."
add("X10", t, [c(*span(t, "Kowalski", "OSOBA")[:2], "OSOBA", "NER"),
               c(*span(t, "Kowalski i Wspólnicy Sp. z o.o", "FIRMA")[:2], "FIRMA", "LegalForm")],
    [span(t, "Kowalski i Wspólnicy Sp. z o.o", "FIRMA")], False, "osoba w nazwie firmy → STOP (częsty układ)")
t = "Kontakt: jan.kowalski@firma.pl"
add("X11", t, [c(*span(t, "jan.kowalski", "OSOBA")[:2], "OSOBA", "NER")],
    [span(t, "jan.kowalski@firma.pl", "EMAIL")], True, "NER na części lokalnej e-maila (jak A10) → STOP oczekiwany")
t = "Profil: @jan_kowalski"
add("X12", t, [], [], False, "uchwyt społecznościowy jako EMAIL → FP")
t = "Patrz skrót ul."
add("X13", t, [], [], False, "ul. na końcu tekstu → brak kotwicy; Guard-dron flaguje bez PII (GUARD_FP)")
t = "NIP: brak danych, PESEL nie podano."
add("X14", t, [], [], False, "etykiety bez numeru — Guard nie powinien flagować")
t = "Kontakt: aléx@firma.pl"
add("X15", t, [], [span(t, "aléx@firma.pl", "EMAIL")], False, "Unicode NFD (znak łączący) w części lokalnej")
t = "Adres: ul. 3 Maja 12/4; tel."
add("X16", t, [], [span(t, "ul. 3 Maja 12/4", "ADRES")], False, "ulica liczbowa — kontrola pozytywna")
t = "Adres: ul. Polna 12, 65-001 Poznań"
add("X17", t, [c(7, 34, "ADRES", "AddressEngine")], [(7, 34, "ADRES")], False,
    "BASE szerszy niż kotwica (decyzja CC: kotwica zakryta) — kontrola pozytywna")
t = "Świadkowie: Jan Kowalski Anna Nowak"
add("X18", t, [c(12, 24, "OSOBA", "NER"), c(16, 35, "OSOBA", "NER2")],
    [(12, 24, "OSOBA"), (25, 35, "OSOBA")], False, "dwa NER z nakładającymi się spanami osób (sklejona lista)")
t = "Kontakt: Ala@Firma.pl oraz ala@firma.pl"
add("X19", t, [], [span(t, "Ala@Firma.pl", "EMAIL"), span(t, "ala@firma.pl", "EMAIL")], False,
    "ta sama skrzynka różną wielkością liter → dwa tokeny (K2: jedna osoba, dwa tokeny)")


def judge(text, gold, stop_ok, r):
    if r["status"] == "STOP":
        return ("SAFE_REFUSAL" if stop_ok else "UNEXPECTED_STOP"), 0, 0
    got = {(t["start"], t["end"], t["kind"]) for t in r["tokens"]}
    fn = [g for g in gold if g not in got]
    fp = [x for x in got if x not in set(gold)]
    return ("PASS" if not fn and not fp else "FAIL"), len(fn), len(fp)


def main():
    ids = sorted(T)
    inp = "".join(json.dumps({"text": T[i][0], "base_candidates": T[i][1], "mode": "full"}, ensure_ascii=False) + "\n"
                  for i in ids)
    p = subprocess.run([sys.executable, SIM], input=inp.encode("utf-8"), capture_output=True, timeout=60)
    out = [json.loads(x) for x in p.stdout.decode("utf-8").splitlines()]
    sys.stdout.reconfigure(encoding="utf-8")
    summary = {}
    for i, r in zip(ids, out):
        text, base, gold, stop_ok, why = T[i]
        verdict, fn, fp = judge(text, gold, stop_ok, r)
        summary[verdict] = summary.get(verdict, 0) + 1
        flags = [f["kind"] for f in r["guard_flags"]]
        print(f"{i} {verdict:15} status={r['status']:8} reason={r['reason_code']} FN={fn} FP={fp} guard={flags} | {why}")
    print("PODSUMOWANIE", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
