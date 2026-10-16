r"""PROTOTYP (audyt, nie kod produktu) — port AnchorEngine.kt (LynxMask Mobile, master@450204b)
na Pythona, uruchamiany jako post-pass na wyniku pipeline Desktop.

Wierne odwzorowanie reguł A.1–A.12 + CLEANUP z app/src/main/java/com/lynxmask/app/AnchorEngine.kt.
Różnice wymuszone przez Python/Desktop (opisane przy regułach):
  - \p{L} → [^\W\d_]  (moduł re nie zna klas Unicode \p{..})
  - TOKEN obejmuje też INSTYTUCJA (taksonomia Desktop) i \d{3}(?!\d) jak TOKEN_RE w Mobile
  - MorfologikHelper.tags(w).isEmpty() → Morfeusz2: wszystkie interpretacje to 'ign'
  - LookupTables.cityForms/streetForms → backend/cities_forms.json, backend/street_names.json
  - OSOBA_DENYLIST skopiowana z NameEngine.kt (88 słów)
Tokeny nadaje Allocator kontynuujący numerację z reverse_map (bez kolizji, dedup po wartości).
"""
from __future__ import annotations

import json
import os
import re

_B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
D = r"[0-9OolIiSsBbZz]"
L = r"[^\W\d_]"                       # litera Unicode (odpowiednik \p{L})
TOK = r"(?:FIRMA|OSOBA|NUMER|EMAIL|KWOTA|ADRES|INSTYTUCJA)_\d{3}(?!\d)"
TOKEN_RE = re.compile(r"\b" + TOK)

OSOBA_DENYLIST = frozenset({
    'zamieszkania', 'zameldowania', 'służbowa', 'służbowy', 'wydział', 'wydziału', 'wydzialu',
    'wydziatu', 'informacji', 'informacj', 'uzyskanych', 'niejszej', 'nin', 'icznie', 'sąd',
    'sądu', 'rejonowy', 'rejonowa', 'okręgowy', 'okręgowa', 'skarbowy', 'skarbowa', 'sędzia',
    'sędziego', 'sędzi', 'urząd', 'urzędu', 'gminy', 'gmina', 'ulica', 'ulicy', 'adres', 'adresu',
    'imię', 'nazwisko', 'pesel', 'numer', 'miejscowość', 'miejscowości', 'rodo', 'data', 'dane',
    'danych', 'nikach', 'osoba', 'osoby', 'osobie', 'osobę', 'osobą', 'osób', 'osobom', 'osobami',
    'osobach', 'zapłata', 'zapłaty', 'zapłacie', 'zapłatę', 'zapłatą', 'zapłat', 'zapłatom',
    'zapłatami', 'zapłatach', 'łączna', 'łącznej', 'łączną', 'łączny', 'łączne', 'łącznego',
    'łącznemu', 'łącznym', 'łącznych', 'łącznymi', 'działający', 'działająca', 'działające',
    'działającego', 'działającej', 'działającemu', 'działającym', 'działających', 'działającymi',
    'działając', 'musi', 'musisz', 'musimy', 'musicie', 'muszę', 'muszą',
})

_morf = None


def _morf_unknown(word: str) -> bool:
    """MorfologikHelper.tags(word).isEmpty() ≈ Morfeusz zna słowo tylko jako 'ign'."""
    global _morf
    if _morf is None:
        import morfeusz2
        _morf = morfeusz2.Morfeusz()
    return all(i[2][2] == "ign" for i in _morf.analyse(word))


_CITY = _STREET = None


def _dicts():
    global _CITY, _STREET
    if _CITY is None:
        _CITY = {c.lower() for c in json.load(open(os.path.join(_B, "cities_forms.json"), encoding="utf-8"))}
        s = json.load(open(os.path.join(_B, "street_names.json"), encoding="utf-8"))
        _STREET = {k.lower() for k in s} | {f.lower() for v in s.values() for f in v}
    return _CITY, _STREET


class Allocator:
    """Kontynuuje numerację z istniejącej mapy; ta sama wartość (bez spacji/myślników) = ten sam token."""

    def __init__(self, reverse_map: dict):
        self.rev = dict(reverse_map)
        self.counters: dict[str, int] = {}
        self.canon: dict[str, str] = {}
        for tok, val in self.rev.items():
            t, n = tok.rsplit("_", 1)
            self.counters[t] = max(self.counters.get(t, 0), int(n))
            self.canon.setdefault(re.sub(r"[\s\-]", "", val), tok)
        self.added: list[tuple[str, str, str]] = []   # (reguła, token, wartość)

    def assign(self, value: str, ttype: str, rule: str) -> str:
        c = re.sub(r"[\s\-]", "", value)
        if c in self.canon:
            return self.canon[c]
        self.counters[ttype] = self.counters.get(ttype, 0) + 1
        tok = f"{ttype}_{self.counters[ttype]:03d}"
        self.rev[tok] = value
        self.canon[c] = tok
        self.added.append((rule, tok, value))
        return tok


def _overlaps(text: str, a: int, b: int) -> bool:
    return any(m.start() < b and a < m.end() for m in TOKEN_RE.finditer(text))


def _pad(acc: str, a: int, b: int, token: str) -> str:
    before = acc[a - 1] if a > 0 else " "
    after = acc[b] if b < len(acc) else " "
    pre = " " if (before.isalnum() or before == "_") else ""
    suf = " " if (after.isalnum() or after == "_") else ""
    return acc[:a] + pre + token + suf + acc[b:]


def apply_anchor(text: str, reverse_map: dict, rules: set[str] | None = None) -> tuple[str, Allocator]:
    al = Allocator(reverse_map)
    t = text

    def on(rule):
        return rules is None or rule in rules

    def apply_all(rule, pattern, ttype, flags=0, validate=None):
        nonlocal t
        if not on(rule):
            return
        hits = list(re.finditer(pattern, t, flags))
        for m in reversed(hits):
            if _overlaps(t, m.start(), m.end()) or (validate and not validate(m)):
                continue
            t = _pad(t, m.start(), m.end(), al.assign(m.group(0).strip(), ttype, rule))

    # A.1 FIRMA — forma prawna (kropka lub przecinek)
    legal = r"(?:Sp[.,]\s*z\s*o[.,]o[.,]\s*(?:S[.,]K[.,]A[.,])?|S[.,]A[.,]|sp[.,]j[.,]|s[.,]c[.,]|Sp[.,]k[.,]|S[.,]K[.,]A[.,])"
    W = r'[A-ZŁŚŹĆŃĄĘÓŻ][A-Za-ząćęłńóśźżŁŚŹĆŃĄĘÓŻ0-9\-"„]{0,40}'
    apply_all("A.1", W + r"(?:[^\S\n]+(?:" + W + r"|[iz&])){0,6}[^\S\n]+" + legal, "FIRMA")

    # A.2 EMAIL — @ (z jednym słowem local-part przed spacją), A.2b osierocona domena
    apply_all("A.2", r"(?:" + L + r"[^\W_]*\s+)?(?!" + TOK + r")[^\s@]*\s*@\s*[^\s]+(?:\s*\.[^\s]+)*(?:(?<=\.)[^\S\n][a-zA-Z]{2,4}\b)?", "EMAIL")
    apply_all("A.2b", r"@[^\s@]+(?:[^\S\n]*\.[^\s@]+)+", "EMAIL")

    # A.3 TELEFON — kotwice +48/0048/tel/kom/fax/mobile/gsm/wew/t:
    apply_all("A.3", r"(?:\+4[8Bb]|0048|tel\w*+\.?|kom[oó]rk\w*+|kom\.?|fax\.?|mobile[^\S\n]*:?|gsm[^\S\n]*:?|wew\.?|\bt[^\S\n]*:)"
              r"[^\S\n]*:?[^\S\n]*\(?" + D + r"(?:[\s\-.()]?" + D + r")*(?![a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ])", "NUMER", re.I)

    # A.4 PESEL — keyword + 9..11 cyfropodobnych
    apply_all("A.4", r"pe[s5][e3][lL1]\b[^0-9OolIiSsBbZz\n]{0,15}(?:" + D + r"[\s\-]?){9,11}", "NUMER", re.I)

    # A.5 NIP — keyword + 10 cyfropodobnych; A.5b kształt z ≥2 myślnikami
    apply_all("A.5", r"N[IiLl1]P\b[^0-9]{0,25}" + D + r"(?:[\s\-]?" + D + r"){9}", "NUMER", re.I)
    apply_all("A.5b", r"(?<![0-9OolIiSsBbZz_])" + D + r"{2,4}-" + D + r"{2,4}(?:-" + D + r"{2,4})+(?![0-9OolIiSsBbZz_])", "NUMER")

    # A.6 IBAN — prefiks PL + 20..42 cyfropodobnych/spacji/myślników
    apply_all("A.6", r"(?<![A-ZŁŚŹĆŃĄĘÓŻ])PL[0-9OolIiSsBbZz \t\-]{20,42}", "NUMER")

    # A.7 DATA urodzenia — kotwica słowna + do 2 słów (bez innych kotwic)
    apply_all("A.7", r"(?:\bur\b\.?|u[nr]\.|\bdob\b[^\S\n]*:?|d\.o\.b\.?|date[^\S\n]+of[^\S\n]+birth[^\S\n]*:?|urodzon\w{0,5}\b(?:[^\S\n]+(?:dnia|w[^\S\n]+dniu))?|data[^\S\n]+urodzenia[^\S\n]*:?)"
              r"[^\S\n]*" + D + r"\S*(?:[^\S\n]+(?!(?:PESEL|NIP|REGON|IBAN|Nr|Numer|KRS|KW|PWZ)\b)\S+){0,2}", "NUMER", re.I)
    # A.7b data → kotwica urodzenia w oknie 60 zn. wstecz
    if on("A.7b"):
        date_re = re.compile(r"(?<!\d)" + D + r"{1,2}[./\-]" + D + r"{1,2}[./\-]" + D + r"{2,4}(?!\d)")
        birth = re.compile(r"(?:\bu\s*[rn]\s*\.?(?:\s|$)|\bu\.r\.?|\bdob\s*:?|\bd\.o\.b\.?|date\s+of\s+birth|urodzon\w{0,5}|data\s+urodzeni)", re.I)
        for m in reversed(list(date_re.finditer(t))):
            if TOKEN_RE.search(m.group(0)) or not birth.search(t[max(0, m.start() - 60):m.start()]):
                continue
            t = _pad(t, m.start(), m.end(), al.assign(m.group(0).strip(), "NUMER", "A.7b"))

    # A.8 SYGNATURA — sygn./sygn akt/sygnatur… (walidacja tylko gałęzi pełnego słowa) + KRS/KW
    codes = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "Km", "Co", "Ns", "Ka", "Ds"}

    def sygn_ok(m):
        a = re.match(r"(?i)sygnatur\w*", m.group(0))
        if not a:
            return True
        w = re.match(r"(?i)^[^a-ząćęłńóśźż]*(?:akt\.?[^a-ząćęłńóśźż]*)?([^\W\d_]+)", m.group(0)[a.end():])
        if not w:
            return True
        word = w.group(1)
        return word in codes or _morf_unknown(word)
    apply_all("A.8", r"\bsygn(?:\.|(?=[^\S\n]*akt\b)|atur\w*)[^\S\n]*(?:akt\.?)?[^\S\n]*:?[^\S\n]*[^\n]+", "NUMER", re.I, sygn_ok)
    apply_all("A.8kw", r"(?:\bKRS\b|\bKW\b)[^\S\n]*:?[^\S\n]*\S+", "NUMER", re.I)

    # A.9b / A.9 / A.9c / A.9d KWOTA
    cur = r"(?:zł|z[1l]|PLN|EUR|USD|GBP|CHF)"
    num = r"(?<![A-Z0-9_])[0-9][0-9OolIiSsBbZz,.]*(?:[^\S\n]" + D + r"{1,3})*(?:[,.]" + D + r"{1,2})?[^\S\n]*"
    apply_all("A.9b", r"(?:kwot[aęą][^\S\n]*:?|sum[aą][^\S\n]*:?|wartości?[^\S\n]*:?|wynagrodzeni\w{0,4}[^\S\n]*:?)[^\S\n]*" + num + cur + r"?(?![a-ząćęłńóśźż])", "KWOTA", re.I)
    apply_all("A.9", num + cur + r"(?![a-ząćęłńóśźż])", "KWOTA", re.I)
    apply_all("A.9c", r"(?<![0-9OolIiSsBbZz])[0-9][0-9OolIiSsBbZz]{0,5}(?:(?:[.,]|[^\S\n])[0-9OolIiSsBbZz]{3})*[^\S\n]?[,.][^\S\n]?[0-9OolIiSsBbZz]{2}(?![0-9OolIiSsBbZz]|[,.][0-9OolIiSsBbZz])", "KWOTA")
    apply_all("A.9d", r"(?<![0-9OolIiSsBbZz])[0-9OolIiSsBbZz]{1,6}[^\S\n]?(?:tysi" + L + r"{0,5}|milion" + L + r"{0,4}|miliard" + L + r"{0,4})(?![^\W_])", "KWOTA", re.I)

    # A.10 OSOBA — tytuł + 1–2 słowa z wielkiej litery (blokada tylko OSOBA_DENYLIST)
    titles = {"dr", "hab", "prof", "mgr", "inż", "adw", "mec", "lek", "med"}

    def a10_ok(m):
        words = [w.strip(".,") for w in re.split(r"[^\S\n]+", m.group(0))]
        return not any(w.lower() in OSOBA_DENYLIST for w in words if w and w.lower() not in titles)
    apply_all("A.10", r"(?:dr[^\S\n]+(?:hab\.?[^\S\n]+)?|prof\.?[^\S\n]+|mgr[^\S\n]+(?:inż\.?[^\S\n]+)?|inż\.?[^\S\n]+|adw\.?[^\S\n]+|mec\.?[^\S\n]+|lek\.?[^\S\n]+(?:med\.?[^\S\n]+)?)"
              r"(?!(?:OSOBA|FIRMA|NUMER|EMAIL|KWOTA|ADRES|INSTYTUCJA)_)"
              r"[A-ZŁŚŹĆŃĄĘÓŻ][a-ząćęłńóśźżA-ZŁŚŹĆŃĄĘÓŻ\-]{1,30}(?:[^\S\n]+[A-ZŁŚŹĆŃĄĘÓŻ][a-ząćęłńóśźżA-ZŁŚŹĆŃĄĘÓŻ\-]{1,40})?", "OSOBA", re.I, a10_ok)

    # A.11 ADRES — ul./al./os./pl. + 1..3 słowa
    apply_all("A.11", r"(?:ul[.,]|al\.|os\.|pl\.)[^\S\n]+[^\W_][\w/\-]*(?:[^\S\n]+[^\W_][\w/\-]*){0,2}", "ADRES", re.I)
    # A.11c/d miasto/ulica obok tokenu ADRES (słownik), A.11e numer budynku z kontekstem
    if on("A.11c") or on("A.11d") or on("A.11e"):
        city, street = _dicts()
        wp = r"[A-Za-ząćęłńóśźżA-ZŁŚŹĆŃĄĘÓŻ][A-Za-ząćęłńóśźżA-ZŁŚŹĆŃĄĘÓŻ\-]{2,}"

        def mask_dict(rule, pat):
            nonlocal t
            for m in reversed(list(re.finditer(pat, t))):
                if TOKEN_RE.search(m.group(0)):
                    continue
                ws = m.group(0).strip().lower().split()
                if not any(w in city or w in street for w in ws):
                    continue
                t = _pad(t, m.start(), m.end(), al.assign(m.group(0).strip(), "ADRES", rule))
        if on("A.11c"):
            mask_dict("A.11c", r"(?<=ADRES_\d{3})(?:-\d+)?[^\S\n]+" + wp + r"(?:[^\S\n]+" + wp + r")?")
        if on("A.11d"):
            mask_dict("A.11d", wp + r"(?:[^\S\n]+" + wp + r")?[^\S\n]+(?=ADRES_\d{3})")
        if on("A.11e"):
            for m in reversed(list(re.finditer(r"\b\d{1,4}[A-Za-z]?/\d{1,2}[A-Za-z]?\b(?![/\-]\d)", t))):
                if TOKEN_RE.search(m.group(0)):
                    continue
                wb, wa = t[max(0, m.start() - 100):m.start()], t[m.end():m.end() + 100]
                prev = (wb.rstrip().split() or [""])[-1].lower()
                if re.search(r"\b\d{2}-\d{3}\b", wb + wa) or re.search(r"ADRES_\d{3}", wb + wa) or prev in city or prev in street:
                    t = _pad(t, m.start(), m.end(), al.assign(m.group(0).strip(), "ADRES", "A.11e"))

    # A.12 NUMER dokumentu — Nr/Numer/VAT + sygnał dokumentu wstecz (60 zn.); A.12c FV
    if on("A.12"):
        doc = re.compile(r"(?<![a-ząćęłńóśźżA-ZŁŚŹĆŃĄĘÓŻ])(?:(?:[Nn]r|[Nn]umer)\.?(?:[^\S\n]+[a-ząćęłńóśźż]+){0,2}|(?i:vat(?!\s*:?\s*\d{1,3}(?:[.,]\d+)?\s*%)))"
                         r"[^\S\n]*:?[^\S\n]*(?=\S*\d)[A-Za-z0-9]+(?:[^\S\n]?[/\-.,][^\S\n]?[A-Za-z0-9]+)*")
        sig = re.compile(r"(?i)faktur|umow|zlecen|kontrahent|\bvat\b|uproszczon|dzia.k")
        for m in reversed(list(doc.finditer(t))):
            if _overlaps(t, m.start(), m.end()):
                continue
            self_sig = not m.group(0).strip().lower().startswith("vat") and sig.search(m.group(0))
            if not sig.search(t[max(0, m.start() - 60):m.start()]) and not self_sig:
                continue
            t = _pad(t, m.start(), m.end(), al.assign(m.group(0).strip(), "NUMER", "A.12"))
    apply_all("A.12c", r"(?<![a-ząćęłńóśźżA-ZŁŚŹĆŃĄĘÓŻ])(?i:fv|f\.v\.|f-ra)\.?[^\S\n]*:?[^\S\n]*(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+(?:[^\S\n]?[/\-.][^\S\n]?[A-Za-z0-9]+)*", "NUMER")
    apply_all("A.12c", r"(?<!\S)(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+(?:[^\S\n]?[/\-.][^\S\n]?[A-Za-z0-9]+)*[^\S\n]?[-/.][^\S\n]?(?i:fv|f\.v\.|f-ra)\b", "NUMER")

    # CLEANUP — sieroce prefiksy przed tokenami i ogony po tokenach
    if on("CLEANUP"):
        t = re.sub(r"\+4[8Bb][^\S\n]*(?=" + TOK + ")", "", t)
        t = re.sub(r"\+[^\S\n]*(?=" + TOK + ")", "", t)
        t = re.sub(r"(?i)(?:tel\.?|kom\.?|fax\.?)[^\S\n]*(?=" + TOK + ")", "", t)
        t = re.sub(r"(?i)(?:adres[^\S\n]*:?[^\S\n]*)?(?:ul[.,]|al\.|os\.|pl\.|u\.)[^\S\n]*(?=ADRES_\d{3})", "", t)
        t = re.sub(r"(" + TOK + r")(?:[/\-.](?!" + TOK + r"\b)[A-Za-z0-9]+)+", r"\1", t)
    return t, al


if __name__ == "__main__":
    import sys
    out, al = apply_anchor(sys.argv[1], {})
    print(out)
    for r in al.added:
        print(r)
