"""LYNX-MAP-FIDELITY — przegląd rodziny klucza kwot (po FAIL r2 Codexa: precyzja Decimal).

Losowe kwoty (1–40 cyfr całości, 0–2 cyfry dziesiętne) w różnych zapisach (spacje/kropki tysięcy, kropka/przecinek
dziesiętny, zera wiodące/końcowe). Wyrocznia: Decimal o precyzji 200 cyfr. Wymóg: klucz równy ⇔ wartość równa (ta sama
waluta). Uruchom z katalogu repo: py -3 tasks/LYNX-MAP-FIDELITY/round_01/implementation/amount_sweep.py [N]
"""
import decimal
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))
from pipeline_core import _value_key  # noqa: E402

# Bez zmiany globalnego kontekstu Decimal: testowany kod dziedziczy kontekst wątku (prec=200 ukryłoby błąd r1).
# Decimal(str) jest dokładny niezależnie od precyzji kontekstu, a wyrocznia tylko porównuje wartości.
rnd = random.Random(2026)


def render(whole: str, frac: str) -> str:
    sep = rnd.choice(["", " ", "."])                   # separator tysięcy
    groups = []
    w = whole
    while len(w) > 3:
        groups.insert(0, w[-3:])
        w = w[:-3]
    groups.insert(0, w)
    text = sep.join(groups) if sep else whole
    if frac:
        text += rnd.choice([",", "."]) + frac
    return text + rnd.choice([" zł", "zł", " PLN"])


def main(n: int) -> int:
    samples = []
    for _ in range(n):
        whole = str(rnd.randint(0, 9)) + "".join(rnd.choice("0123456789") for _ in range(rnd.randint(0, 39)))
        frac = "".join(rnd.choice("0123456789") for _ in range(rnd.choice([0, 1, 2])))
        cur = "pln" if "PLN" in (r := render(whole, frac)) else "zł"
        samples.append((r, (decimal.Decimal(whole + "." + (frac or "0")), cur)))
        if rnd.random() < 0.3:                          # ten sam zapis inaczej: zera końcowe / inny separator
            frac2 = (frac + "0")[:2] if frac and len(frac) < 2 else frac
            r2 = render(whole, frac2)
            samples.append((r2, (decimal.Decimal(whole + "." + (frac2 or "0")), "pln" if "PLN" in r2 else "zł")))
    for length in range(20, 46):                       # pary różniące się dopiero ostatnią cyfrą (granica precyzji)
        base = str(rnd.randint(1, 9)) + "".join(rnd.choice("0123456789") for _ in range(length - 2))
        for last, frac in (("1", ""), ("2", ""), ("1", "5"), ("1", "50")):
            r = render(base + last, frac)
            samples.append((r, (decimal.Decimal(base + last + "." + (frac or "0")), "pln" if "PLN" in r else "zł")))
    errors = 0
    keys = {}
    for text, val in samples:
        k = _value_key(text, "KWOTA")
        if k in keys and keys[k][1] != val:
            errors += 1
            if errors <= 5:
                print("KOLIZJA:", keys[k][0][:50], "|", text[:50])
        keys.setdefault(k, (text, val))
    by_val = {}
    for text, val in samples:
        by_val.setdefault(val, set()).add(_value_key(text, "KWOTA"))
    split = sum(len(v) > 1 for v in by_val.values())
    print(f"próbek {len(samples)}, kolizji różnych wartości {errors}, wartości rozbitych na >1 klucz {split}")
    return 1 if errors or split else 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 20000))
