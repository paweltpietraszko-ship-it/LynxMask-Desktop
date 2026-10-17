# LYNX-NEWLINE-CROSSING: pary wartości w kolejnych liniach (jak komórki tabel) — oba tryby, NER wyłączony, dane syntetyczne.
# Uruchom z backend/. Problem = jawny fragment wartości, utracony podział linii, token w tokenie, lub Przywróć != wejście (poza znanym F3).
import contextlib, io, itertools, re, sys
from unittest.mock import patch
sys.path[:0] = [".", "../audyt"]
V = {"EMAIL1": "k.zalewska@example.pl", "EMAIL2": "m.nowicka@example.pl", "TEL": "512 987 654", "NIP": "526-000-12-46",
     "PESEL": "44051401359", "IBAN": "PL61 1090 1014 0000 0712 1981 2874", "KWOTA": "1 250,00 zł", "TXT": "Opis pozycji",
     "NIPL": "NIP: 526-000-12-46", "TELL": "tel: 512 987 654", "PESELL": "PESEL 44051401359", "TELW": "Tel. 512 987 654"}
TOKEN = re.compile(r"(?:OSOBA|FIRMA|INSTYTUCJA|NUMER|EMAIL|KWOTA|ADRES)_\d{3,}")

def check(t, out, rev):
    lines_in, lines_out = t.split("\n"), out.split("\n")
    if len(lines_in) != len(lines_out) or "_NUMER" in out or any(TOKEN.search(v) for v in rev.values()):
        return "granica/token"
    for k in V:
        if V[k] in t and k != "TXT":
            frags = [w for w in re.findall(r"[A-Za-z0-9]{3,}", V[k]) if w not in ("example", "NIP", "tel", "Tel", "PESEL")]
            if any(f in out for f in frags):
                return f"jawne:{k}"
    from unmask_sim import unmask
    restored = unmask(out, rev)  # etykiety bywają częścią wartości tokenu — sprawdzać po Przywróć
    for lab in ("Tel.", "tel:", "NIP", "PESEL", "Opis pozycji"):
        if t.count(lab) != restored.count(lab):
            return f"zmieniona etykieta:{lab}"
    return None

def run():
    import layers.ner_adapter as na
    from pipeline_new import run_pipeline_new, run_pipeline_express
    bad = []
    pairs = list(itertools.permutations(V, 2))
    for a, b in pairs:
        t = f"{V[a]}\n{V[b]}"
        for fn in (run_pipeline_new, run_pipeline_express):
            with patch.object(na, "process_ner", return_value=({}, {})), contextlib.redirect_stdout(io.StringIO()):
                out, rev, _ = fn(t, anon_map={})
            why = check(t, out, rev)
            if why:
                bad.append((a, b, fn.__name__, why, out))
    return pairs, bad

if __name__ == "__main__":
    pairs, bad = run()
    print(f"par {len(pairs)} × 2 tryby: problemy {len(bad)}")
    for a, b, mode, why, out in bad[:20]:
        print(f"  {a}->{b} [{mode}] {why}: {out!r}")
