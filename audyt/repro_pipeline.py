"""Reprodukcje end-to-end przez pipeline.pseudonymize_document z pełnym stanem
jak w API (spaCy + anonymizer + guard). Dane syntetyczne.
Użycie: python audyt/repro_pipeline.py"""
import sys
import os
import logging
import tempfile
logging.disable(logging.CRITICAL)
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, B); os.chdir(B)

def build_state(seed=False):
    from pipeline import AppState
    import spacy_ner
    from anonymizer import build_anonymizer
    st = AppState()
    st.spacy_ner_mod = spacy_ner
    d = tempfile.mkdtemp(prefix="lynx_audyt_")
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
    if seed:
        import anonymizer as A
        A.MAX_ONBOARD_BATCH = 10**6   # obejście BUG-ONBOARD-BATCH tylko w procesie audytu
        from seed_profile import seed_if_needed
        seed_if_needed(st.anon_map)
    return st

def run(st, text):
    from pipeline import pseudonymize_document
    r = pseudonymize_document(text, st)
    return r

CASES = [
 ("NIP 3-2-2-3",        "Sprzedawca NIP 512-34-56-789, płatność przelewem."),
 ("NIP 3-3-2-2",        "Sprzedawca NIP 512-345-67-89, płatność przelewem."),
 ("NIP PL 2-2-2-2",     "VAT UE: PL65 51 97 93 13 zgodnie z fakturą."),
 ("IBAN GB",            "Proszę o przelew na GB29 NWBK 6016 1331 9268 19 do piątku."),
 ("IBAN PL spacje",     "Przelew na konto: PL61 1090 1014 0000 0712 1981 2874."),
 ("IBAN PL ciągły",     "Konto 61109010140000071219812874 w banku."),
 ("Instytucja Nik",     "Spotkałem Nika i Gusa przy pip install requests."),
 ("Instytucja NIK",     "Kontrolę przeprowadził NIK, a dane zebrał GUS."),
 ("Kancelaria sp.zoo",  "Pełnomocnik: Kancelaria Sądu Rejonowego sp. z o.o. z siedzibą w Lublinie."),
 ("LISTA KONTROLNA",    "LISTA KONTROLNA\nEncje do sprawdzenia: Kont0: 123."),
 ("Byt0m",              "Siedziba w Byt0m, ul. Długa 5."),
 ("email imię",         "Kontakt: anna.nowak@example.pl w sprawie umowy."),
 ("Nazwisko samo",      "Kowalski nie przyszedł, a Wiśniewski był chory."),
 ("Imię+nazwisko",      "Jan Kowalski zawarł umowę z Anną Wiśniewską."),
]

if __name__ == "__main__":
    seed = "--seed" in sys.argv
    st = build_state(seed=seed)
    print(f"# seed={seed}")
    for name, t in CASES:
        r = run(st, t)
        print(f"{name:18} blocked={r.guard_blocked!s:5} OUT={r.text!r}")
        print(f"{'':18} map={r.reverse_map}")
