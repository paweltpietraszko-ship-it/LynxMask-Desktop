"""
guard_unknown.py — [LYNX-OSOBA-LAYOUT] pytanie Guarda o słowo, którego nikt nie opisał.

Model 23.10: silnik decyduje, Guard nie zgaduje osób. Słowa ze zwykłym znaczeniem i decyzje silnika są dla Guarda niewidzialne.
Pytanie dostaje: (a) słowo, które słownik zna wyłącznie jako imię/nazwisko, a silnik go nie zakrył („Kasprzak”);
(b) słowo z wielkiej litery, którego nie opisał nikt: Morfeusz go nie zna (ign), nie jest imieniem,
nie ma go na białej liście ani wśród skrótów z pism, i nie da się go odczytać jako zwykłe słowo zniekształcone przez OCR
(brak ogonków, jedna typowa pomyłka znaku). Słowa obce zostają pytaniem — użytkownik decyduje („Zawsze jawne”).
"""
from __future__ import annotations

import json
import os
import re

_UP = "A-ZĄĆĘŁŃÓŚŹŻ"
_LO = "a-ząćęłńóśźż"
_WORD_RE = re.compile(rf"(?<![\w-])[{_UP}][{_LO}]{{2,}}(?:-[{_UP}][{_LO}]{{2,}})?(?![\w-])")
# skróty z pism (z kropką lub bez) — nie pytamy
_ABBR = frozenset(("sygn", "wyd", "lex", "dz", "poz", "nr", "tel", "ul", "al", "pl", "os", "godz", "str", "ust", "pkt", "lit", "art",
                   "par", "rozdz", "zał", "red", "oprac", "tzw", "np", "itd", "ok", "tj", "im", "sp", "zob", "por", "kpc", "kpk",
                   "kpa", "pzp", "kc", "kk", "kp", "kro", "op", "cyt", "wg", "nt", "ws", "dot", "przyp", "uzas", "sent", "akt"))
# typowe pomyłki OCR: (co odczytano, co mogło być); od indeksu 9 — same ogonki
_OCR_SUBST = (("m", "rn"), ("rn", "m"), ("t", "ł"), ("i", "ł"), ("l", "ł"), ("i", "l"), ("l", "i"), ("o", "c"), ("c", "o"),
              ("a", "ą"), ("e", "ę"), ("o", "ó"), ("s", "ś"), ("z", "ż"), ("z", "ź"), ("c", "ć"), ("n", "ń"), ("ż", "ź"), ("ź", "ż"))
_DIACRITIC_FROM = 9
_WHITELIST: frozenset[str] | None = None


def _whitelist() -> frozenset[str]:
    global _WHITELIST
    if _WHITELIST is None:
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard_unknown_whitelist.json")
            with open(path, encoding="utf-8") as f:
                _WHITELIST = frozenset(json.load(f)["slowa"])
        except Exception:
            _WHITELIST = frozenset()  # brak listy = więcej pytań, nigdy mniej
    return _WHITELIST


def _known(interps) -> bool:
    return bool(interps) and not all(i[2][2] == "ign" for i in interps)


def _only_person_name(interps) -> bool:
    """Morfeusz zna słowo wyłącznie jako imię/nazwisko („Kasprzak”) — bez zwykłego znaczenia i bez nazwy miejsca („Góra”, „Kawa”)."""
    if not _known(interps):
        return False
    quals = [set(i[2][3]) for i in interps]
    return any(q & {"nazwisko", "imię"} for q in quals) \
        and not any(i[2][1][:1].islower() or i[2][2].startswith("adj") for i in interps) \
        and not any(q & {"nazwa_geograficzna", "człon_nazwy_geograficznej"} for q in quals)


def _ocr_common(word: str, analyse) -> bool:
    """Słowo ≥5 liter, które po jednej typowej pomyłce OCR (plus ewentualnie jednym ogonku) jest zwykłym słowem (lemat małą literą)."""
    if len(word) < 5:
        return False
    low = word.lower()
    cands = {low[:i] + b + low[i + len(a):] for a, b in _OCR_SUBST for i in range(len(low)) if low.startswith(a, i)}
    cands |= {c[:i] + b + c[i + len(a):] for c in list(cands) for a, b in _OCR_SUBST[_DIACRITIC_FROM:]
              for i in range(len(c)) if c.startswith(a, i)}
    for c in cands:
        q = analyse(c[:1].upper() + c[1:])
        if q and any(i[2][2] != "ign" and i[2][1][:1].islower() for i in q):
            return True
    return False


def unknown_words(text: str, analyse):
    """Pozycje słów nieopisanych przez nikogo: (start, end, "R1", powód). `analyse` = Morfeusz (None przy błędzie → pytanie)."""
    from osoba_not_person import _variants, first_names
    names, white = first_names(), _whitelist()
    for m in _WORD_RE.finditer(text):
        w = m.group(0)
        low = w.lower()
        if low in names or low in white or low in _ABBR or not re.search(r"[aeiouyąęó]", low):
            continue
        p = analyse(w)
        if p is not None:
            if _only_person_name(p):
                yield m.start(), m.end(), "R1", "Nazwisko lub imię według słownika — silnik go nie zakrył"
                continue
            if _known(p):
                continue  # Morfeusz opisał słowo
            if not re.search(r"[ąćęłńóśźż]", low) and any(_known(analyse(v)) for v in _variants(w)[1:]):
                continue  # bez ogonków po OCR („Platnosc” → „Płatność”)
            if _ocr_common(w, analyse):
                continue  # jedna typowa pomyłka OCR („Komomik”, „Wydziatu”)
        yield m.start(), m.end(), "R1", "Słowo nierozpoznane przez żadną warstwę — możliwe nazwisko"
