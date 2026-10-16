"""Tabela reguł AnchorEngine (Mobile) vs Desktop: dla każdej reguły minimalny przykład
(dane syntetyczne) → pipeline Desktop (świeży profil, spaCy, jak /preview) → prototyp
kotwic (audyt/anchor_proto.py) na wyniku. Wypisuje wynik z zamaskowanym PII.
Użycie: python audyt/port_rules.py [--json plik]"""
import sys, os, json, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repro_pipeline import build_state, run          # noqa: E402
from anchor_proto import apply_anchor                # noqa: E402

# (reguła, tekst, PII które ma zniknąć, fragmenty które MUSZĄ zostać — kontrola FP)
CASES = [
    ("A.1",  "Umowę zawarto z Hydrotech Serwis S,A, w dniu 3 marca.", ["Hydrotech Serwis"], []),
    ("A.1",  "Dostawca: Zielony Ogrod sp,j, Radom", ["Zielony Ogrod"], []),
    ("A.2",  "Kontakt: anna nowak@ poczta .pl w sprawie umowy", ["anna", "nowak@", "poczta"], ["Kontakt"]),
    ("A.2",  "e-mail: jkowalski@interia. pl lub telefonicznie", ["jkowalski", "interia"], ["telefonicznie"]),
    ("A.2b", "pisz: biuro@kancelaria-lex .pl dziękuję", ["biuro", "kancelaria-lex"], ["dziękuję"]),
    ("A.3",  "tel. 5O1 234 S67 po godzinie 16", ["5O1 234 S67"], ["godzinie"]),
    ("A.3",  "kom.: (22) 765-43-21 sekretariat", ["765-43-21"], ["sekretariat"]),
    ("A.3",  "Proszę dzwonić +4B 601 234 567 wieczorem", ["601 234 567"], ["wieczorem"]),
    ("A.4",  "PESEL: 9OO4O5l2345 zamieszkały", ["9OO4O5l2345"], ["zamieszkały"]),
    ("A.4",  "PESEL 900405 12345", ["900405 12345"], []),
    ("A.5",  "NIP: 526-O2l-15-8l sprzedawca", ["526-O2l-15-8l"], ["sprzedawca"]),
    ("A.5",  "NIP (jeśli dotyczy):\n5260211581", ["5260211581"], []),
    ("A.5b", "Rejestr 12-34-56-78 wpisany", ["12-34-56-78"], ["wpisany"]),
    ("A.5b-FP", "Spotkanie w dniu 12-03-2024 r. o godz. 10", [], ["12-03-2024"]),
    ("A.6",  "konto PL 27 1l40 2OO4 0000 3002 0135 5387 w banku", ["1l40 2OO4 0000 3002 0135 5387"], ["w banku"]),
    ("A.7",  "ur. 21O5.l979 w Radomiu", ["21O5.l979", "2105.l979"], ["Radomiu"]),
    ("A.7",  "urodzony dnia 8 kwietnia 1963 roku w Radomiu", ["8 kwietnia 1963"], ["Radomiu"]),
    ("A.7b", "Jan, u r. 12.03.1985, zamieszkały", ["12.03.1985"], ["zamieszkały"]),
    ("A.8",  "sygn. akt I C 1234/22", ["1234/22"], []),
    ("A.8",  "Sygn. Km 155/23\nWezwanie", ["155/23"], ["Wezwanie"]),
    ("A.8-FP", "Ta sygnatura biologiczna planety jest słaba.", [], ["sygnatura biologiczna"]),
    ("A.8kw", "KW: KR1P/00012345/6 działka", ["KR1P/00012345/6"], ["działka"]),
    ("A.8kw", "KRS 0000123456 spółka", ["0000123456"], ["spółka"]),
    ("A.9b", "Wynagrodzenie: 4 5OO,OO zł brutto", ["4 5OO,OO"], ["brutto"]),
    ("A.9",  "zapłacono 1 250,5O PLN gotówką", ["1 250,5O"], ["gotówką"]),
    ("A.9c", "Do zapłaty 1 234,56 w terminie 30 dni", ["1 234,56"], ["terminie"]),
    ("A.9d", "przelano 15 tysięcy złotych", ["15 tysięcy"], []),
    ("A.10", "Pełnomocnik: mec. Zdzisław Brzęczyszczykiewicz", ["Brzęczyszczykiewicz"], []),
    ("A.10", "Opinię wydał dr hab. Kowalski z kliniki", ["Kowalski"], ["kliniki"]),
    ("A.10", "Przyjęła lek. med. Anna Wiśniewska-Kot rano", ["Wiśniewska-Kot", "Anna"], ["rano"]),
    ("A.10-FP", "Zgodnie z zaleceniem dr Sąd Rejonowy orzekł", [], ["Sąd"]),
    ("A.11", "zam. ul. Gdańska-Sopocka 3/1 w mieście", ["Gdańska-Sopocka 3/1"], ["mieście"]),
    ("A.11c", "Adres: ul. Polna 5, Radom", ["Polna 5", "Radom"], []),
    ("A.11e", "lokal 15/4, 00-950 Warszawa", ["15/4", "00-950"], []),
    ("A.12", "FAKTURA VAT\nNr FV-08217/08/2023 z dnia", ["08217/08/2023"], []),
    ("A.12", "UMOWA ZLECENIA\nnr U-00284/2023 zawarta", ["U-00284/2023"], ["zawarta"]),
    ("A.12-FP", "Kwota VAT wynosi 230,00 zł, punkt nr 5.2", [], ["punkt nr 5.2"]),
    ("A.12c", "Dotyczy FV20260700W012 oraz 260712/FV", ["FV20260700W012", "260712/FV"], []),
    ("CLEANUP", "Telefon: tel. +48 601 234 567, faks", ["601 234 567"], ["faks"]),
]


def mask(s, pii):
    for p in sorted(pii, key=len, reverse=True):
        s = s.replace(p, p[:3] + "*" * max(0, len(p) - 3))
    return s


def present(out, items):
    return [p for p in items if p in out]


if __name__ == "__main__":
    st = build_state(False)
    rows = []
    for rule, text, pii, keep in CASES:
        st = build_state(False)
        r = run(st, text)
        out_a, al = apply_anchor(r.text, r.reverse_map)
        d_leak, a_leak = present(r.text, pii), present(out_a, pii)
        d_fp = [k for k in keep if k not in r.text]
        a_fp = [k for k in keep if k in r.text and k not in out_a]   # FP wprowadzone przez kotwice
        row = {"rule": rule, "desktop_ok": not d_leak, "anchor_ok": not a_leak, "desktop_fp": d_fp, "anchor_fp": a_fp,
               "added": [(x[0], x[1]) for x in al.added],
               "in": mask(text, pii), "desktop": mask(r.text, pii), "anchor": mask(out_a, pii)}
        rows.append(row)
        print(f"{rule:8} DESK={'OK ' if row['desktop_ok'] else 'WYC'}{' FP' if d_fp else ''} | +KOTWICE={'OK ' if row['anchor_ok'] else 'WYC'}{' FP' + str(a_fp) if a_fp else ''} | {row['in']!r}")
        print(f"{'':8}   desktop: {row['desktop']!r}")
        if out_a != r.text:
            print(f"{'':8}   +kotwice: {row['anchor']!r}  {row['added']}")
    if "--json" in sys.argv:
        json.dump(rows, open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
