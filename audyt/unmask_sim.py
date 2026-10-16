"""Symulacja logiki Przywracania z frontend/src/screens/Depseudonimizuj.tsx:66-73
(for token of Object.keys(map): result = result.replaceAll(token, map[token])).
Kolejność kluczy = kolejność tokens z /preview (sort po typie, potem po nazwie tokenu)."""
TYPE_ORDER = {"OSOBA": 0, "FIRMA": 1, "INSTYTUCJA": 2, "NUMER": 3, "EMAIL": 4, "KWOTA": 5, "ADRES": 6}

def ordered(rev):
    return sorted(rev.items(), key=lambda kv: (TYPE_ORDER.get(kv[0].split("_")[0], 9), kv[0]))

def unmask(text, rev):
    for tok, orig in ordered(rev):
        text = text.replace(tok, orig)
    return text

if __name__ == "__main__":
    # 1) token w tokenie przy >=1000 encji (np. po naprawie seeda: OSOBA_2187)
    rev = {"OSOBA_100": "Anna", "OSOBA_1001": "Kowalski"}
    print("1:", repr(unmask("OSOBA_1001 i OSOBA_100", rev)))
    # 2) zagnieżdżony token w EMAIL (wynik repro_pipeline --seed)
    rev = {"OSOBA_964": "anna", "OSOBA_2172": "nowak", "EMAIL_001": "OSOBA_964.OSOBA_2172@example.pl"}
    print("2:", repr(unmask("Kontakt: EMAIL_001", rev)))
    # 3) odmieniony/zmieniony token przez model AI
    rev = {"OSOBA_001": "Kowalski"}
    for t in ["OSOBA_001 ma L4", "Osoba_001 ma L4", "OSOBY_001 nie dano soboty", "OSOBA_001'owi", "OSOBA 001"]:
        print("3:", repr(t), "->", repr(unmask(t, rev)))
