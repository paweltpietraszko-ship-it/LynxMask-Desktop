"""person_decision.py — [LYNX-OSOBA-REDESIGN] jedno miejsce decyzji „czy to OSOBA” (brief Architekta v1.4).

Wołane na finalnym tekście (po warstwach i HerBERT, przed Guardem): dla każdego jawnego wystąpienia słowa/pary z wielkiej litery
decyzja MASK (token OSOBA) / ASK (jedno R1 w Guardzie) / PASS. Kolejność reguł = tabela §2 briefu (pierwsza pasująca wygrywa).
Dowody: słownik nazwisk PESEL (≥100 osób, `person_surnames_pesel_20260120.json`), biała lista 316 (OWNER 23.10), imiona
(`names_inflected.json`), Morfeusz, kontekst (tytuł, etykieta roli, podpis, imię/inicjał obok, osoba rozpoznana wcześniej).
Sam spaCy nie jest dowodem. Przełącznik `LYNX_OSOBA_DECIDER` = off (domyślnie, E1: bez wpływu na wynik) | on.
Wykonanie: jeden niezmienny snapshot, podmiany MASK od prawej, pozycje ASK przeliczone tylko przez znane lokalne podmiany.
Logi wyłącznie liczby (S5).
"""
from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger("lynxmask.person_decision")

_DIR = os.path.dirname(os.path.abspath(__file__))
_UP, _LO = "A-ZĄĆĘŁŃÓŚŹŻ", "a-ząćęłńóśźż"
_WORD_RE = re.compile(rf"(?<![\w-])[{_UP}][{_LO}]+(?:-[{_UP}][{_LO}]+)?(?![\w-])")
_INITIAL_RE = re.compile(rf"(?<![\w.])[{_UP}]\.[ \t]?(?=[{_UP}][{_LO}])")
_TOKEN_RE = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)")
_PAIR_GAP_RE = re.compile(r"[ \t]+")
_ROLE_WORD_RE = re.compile(r"(?i)(?:protokolant|przewodnicząc|sędzi|prezes|dyrektor|kierownik|mecenas|prokurator|komornik|notariusz"
                           r"|radc|adwokat|minister|wojewod|marszał|burmistrz|wójt|starost|posł|poseł|senator|rzecznik|inspektor|referent"
                           r"|ławnik|biegł|świad|kurator|doktor|profesor|inżynier|kanclerz|premier|prezydent|członk|zastęp|sekretar"
                           r"|skarbnik|odwołując|przystępując|zamawiając|wykonawc|pozwan|powód|powod|wnioskodawc|uczestni|pełnomocni"
                           r"|skarżąc|protestując|wierzyciel|dłużni|pracowni|pracodawc)")
_SIGN_RE = re.compile(r"(?i)(?:z\s+poważaniem|z\s+wyrazami\s+szacunku|podpis(?:ano)?|sporządził[a]?)[ \t]*[,:]?\s*$")
_STREET_RE = re.compile(r"(?i)(?:\bul\.|\bal\.|\bpl\.|\bos\.|\bulic[aeyą]|\baleja|\baleje|\bplac)[ \t]*$")
_LOC_PREP_RE = re.compile(r"(?i)(?:^|\s)(?:w|we|na|pod|nad|koło)[ \t]+$")
_SURNAME_END_RE = re.compile(r"(?:[scd]k|dzk)(?:i|a|iego|iej|iemu|im|ą)$|(?:icz|wicz|czyk|czuk|iak|uk|ak|ek|ik)(?:a|owi|iem|em|u)?$")
_SUFFIX = [("skiego", "ski"), ("skiemu", "ski"), ("skim", "ski"), ("ską", "ska"), ("skiej", "ska"), ("ckiego", "cki"),
           ("ckiemu", "cki"), ("ckim", "cki"), ("cką", "cka"), ("ckiej", "cka"), ("dzkiego", "dzki"), ("dzkiej", "dzka"),
           ("owi", ""), ("em", ""), ("a", ""), ("u", ""), ("ie", ""), ("ę", "a"), ("ą", "a"), ("y", "a")]
COMMON_SURNAME = 1000   # OWNER 23.10: nazwisko noszone przez ≥1000 osób samo jest dowodem
_DATA: tuple | None = None
_MORF = None
_STREETS: frozenset | None = None
_CACHE: dict = {}


def enabled() -> bool:
    return os.environ.get("LYNX_OSOBA_DECIDER", "off").strip().lower() == "on"


def _data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(_DIR, "person_surnames_pesel_20260120.json"), encoding="utf-8") as f:
            d = json.load(f)
        _DATA = (d["surnames"], frozenset(d["whitelist"]), frozenset(d["months"]))
    return _DATA


def _streets() -> frozenset:
    global _STREETS
    if _STREETS is None:
        with open(os.path.join(_DIR, "street_names.json"), encoding="utf-8") as f:
            d = json.load(f)
        _STREETS = frozenset(d) | frozenset(x for v in d.values() for x in v)
    return _STREETS


def _analyse(word: str) -> list:
    global _MORF
    if _MORF is None:
        import morfeusz2
        _MORF = morfeusz2.Morfeusz()
    return _MORF.analyse(word)


def _features(word: str) -> dict:
    """Cechy słowa (bez kontekstu): liczba nosicieli, biała lista, miesiąc, imię, Morfeusz osoba/nieznane."""
    if word in _CACHE:
        return _CACHE[word]
    from osoba_not_person import first_names
    surn, white, months = _data()
    w = word[:1].upper() + word[1:].lower()
    an = _analyse(w)
    unknown = all(i[2][2] == "ign" for i in an)
    lemmas = set()
    for i in an:
        tag, base = i[2][2], i[2][1].split(":")[0].lower()
        if tag.startswith("adj") and not re.search(r":(?:m1|f)(?:[.:]|$)", tag):
            continue   # „Konieczne” (przymiotnik nijaki) nie jest formą nazwiska „Konieczny” (brief §4: tylko rzeczywiste formy)
        lemmas.add(base)
    low = word.lower()
    cands = {low} | lemmas
    if unknown:
        cands |= {low[: len(low) - len(s)] + r for s, r in _SUFFIX if low.endswith(s) and len(low) - len(s) >= 3}
    quals = {q.split("_(")[0] for i in an for q in i[2][3]}
    f = {
        "count": max((surn[c] for c in cands if c in surn), default=0),
        "white": bool(({low} | lemmas) & white),
        "month": bool(({low} | lemmas) & months),
        "first": low in first_names(),
        "morf_person": bool(quals & {"imię", "nazwisko"}),
        "unknown": unknown,
        "lemmas": lemmas or {low},
    }
    _CACHE[word] = f
    return f


def _name_like(f: dict, word: str) -> bool:
    """Może być nazwiskiem/imieniem (dowód słownikowy albo nieznane słowo o kształcie nazwiska)."""
    return f["count"] >= 100 or f["morf_person"] or f["first"] or (f["unknown"] and bool(_SURNAME_END_RE.search(word.lower())))


def _line_before(text: str, s: int) -> str:
    return text[text.rfind("\n", 0, s) + 1:s]


def _anchor(text: str, s: int) -> bool:
    from osoba_not_person import _ROLE_RE, _TITLE_RE
    before = _line_before(text, s)
    return bool(_TITLE_RE.search(before[-14:]) or _ROLE_RE.search(before) or _SIGN_RE.search(text[max(0, s - 40):s]))


def _person_verb_after(text: str, e: int) -> bool:
    m = re.match(rf"[ \t]+([{_LO}]+)", text[e:e + 30])
    if not m:
        return False
    an = _analyse(m.group(1))
    return not any(i[2][1].split(":")[0] == "być" for i in an) and any(i[2][2].startswith(("fin:sg", "praet:sg")) for i in an)


def _place_or_street(text: str, s: int, e: int, f: dict) -> bool:
    from layers.address import _CITY_FORMS
    word, before = text[s:e], text[max(0, s - 14):s]
    if _STREET_RE.search(before) or (word.lower() in _streets() and (f["count"] < COMMON_SURNAME or re.match(r"[ \t]*\d", text[e:]))):
        return True
    return word in _CITY_FORMS and (f["count"] < COMMON_SURNAME or bool(_LOC_PREP_RE.search(before)))


def _in_name_chain(text: str, s: int, e: int, words_at: dict) -> bool:
    """Człon nazwy własnej/instytucji: sąsiad z wielkiej litery, który nie jest imieniem ani nazwiskiem („Urzędu Wojewódzkiego”)."""
    from guard_residue import _in_institution, _sentence_start
    if _in_institution(_line_before(text, s)):
        return True
    for nb in (words_at.get(("prev", s)), words_at.get(("next", e))):
        if nb is None:
            continue
        ns, ne = nb
        nw = text[ns:ne]
        if ns < s and _sentence_start(text, ns):
            continue   # „Wczoraj Nowak” — poprzednik to tylko początek zdania
        if not _name_like(_features(nw), nw):
            return True
    return False


def _words(text: str) -> list[tuple[int, int]]:
    tokens = [m.span() for m in _TOKEN_RE.finditer(text)]
    return [m.span() for m in _WORD_RE.finditer(text) if not any(ts < m.end() and m.start() < te for ts, te in tokens)]


def _adjacency(text: str, spans: list) -> dict:
    """Sąsiad w tym samym wierszu, oddzielony wyłącznie spacją/tabulatorem (bez przecinka i kropki — warunek C3)."""
    out: dict = {}
    for (a, b), (c, d) in zip(spans, spans[1:]):
        if _PAIR_GAP_RE.fullmatch(text[b:c]):
            out[("next", b)] = (c, d)
            out[("prev", c)] = (a, b)
    return out


def _pairs(text: str, spans: list, adj: dict) -> list[tuple[int, int]]:
    """Pełne osoby: imię(+imię) + nazwisko, nazwisko + imię, inicjał + nazwisko (biały człon tylko w parze z imieniem — C3)."""
    out, used = [], set()
    for s, e in spans:
        if (s, e) in used:
            continue
        w, f = text[s:e], _features(text[s:e])
        if _STREET_RE.search(text[max(0, s - 14):s]) or _ROLE_WORD_RE.match(w):
            continue
        chain = [(s, e)]
        while ("next", chain[-1][1]) in adj and _features(text[slice(*chain[-1])])["first"] and len(chain) < 3:
            chain.append(adj[("next", chain[-1][1])])
        if len(chain) >= 2:
            last = text[slice(*chain[-1])]
            lf = _features(last)
            if (lf["white"] or _name_like(lf, last)) and not _ROLE_WORD_RE.match(last) and not lf["month"]:
                out.append((chain[0][0], chain[-1][1]))
                used.update(chain)
                continue
        nxt = adj.get(("next", e))
        if nxt and not f["white"] and not f["first"] and _name_like(f, w) and _features(text[slice(*nxt)])["first"]:
            out.append((s, nxt[1]))   # „Nowak Jan”
            used.update({(s, e), nxt})
    for m in _INITIAL_RE.finditer(text):
        nm = next(((s, e) for s, e in spans if s == m.end()), None)
        if nm and nm not in used:
            w = text[slice(*nm)]
            f = _features(w)
            if not f["white"] and not f["month"] and _name_like(f, w) and not _ROLE_WORD_RE.match(w):
                out.append((m.start(), nm[1]))
                used.add(nm)
    return sorted(out)


def _decide_single(text: str, s: int, e: int, adj: dict, persons: list) -> tuple[str, str | None]:
    """(MASK|ASK|PASS, token osoby, do której to odniesienie) — tabela §2, pierwsza pasująca reguła."""
    from guard_residue import _sentence_start
    w = text[s:e]
    f = _features(w)
    anchor = _anchor(text, s)
    refs = {tok for tok, val in persons if f["lemmas"] & _features(val.split()[-1])["lemmas"]} if len(w) >= 3 else set()
    if refs and (not f["white"] or anchor or _person_verb_after(text, e)):
        return ("MASK", next(iter(refs))) if len(refs) == 1 else ("ASK", None)
    if f["white"]:
        return "PASS", None
    if anchor and (_name_like(f, w) or f["month"]) and not _ROLE_WORD_RE.match(w):
        return "MASK", None
    if (_ROLE_WORD_RE.match(w) or f["month"] or _place_or_street(text, s, e, f) or not re.search(r"[aeiouyąęó]", w, re.I)
            or _in_name_chain(text, s, e, adj)):
        return "PASS", None
    if f["count"] >= COMMON_SURNAME:
        return "MASK", None
    if f["count"] >= 100:
        return "ASK", None
    if (f["morf_person"] or f["first"] or (f["unknown"] and _SURNAME_END_RE.search(w.lower()))) and _person_verb_after(text, e) \
            and not (_sentence_start(text, s) and not f["count"] and not f["first"]):
        return "ASK", None
    return "PASS", None


def resolve_final_persons(text: str, reverse_map: dict, context: dict | None = None) -> tuple[str, dict, list[dict]]:
    """Decyzja OSOBA na finalnym tekście. Zwraca (tekst po MASK, mapa, ask_spans w finalnym tekście: {start,end,rule,reason})."""
    from herbert_net import _next_token
    anon_map = (context or {}).get("anon_map")
    rmap = dict(reverse_map)
    spans = _words(text)
    adj = _adjacency(text, spans)
    pairs = _pairs(text, spans, adj)
    in_pair = lambda s, e: any(ps <= s and e <= pe for ps, pe in pairs)  # noqa: E731
    by_value = {v: t for t, v in rmap.items() if t.startswith("OSOBA_")}

    def token_for(value: str) -> str:
        if value not in by_value:
            tok = _next_token("OSOBA", rmap, anon_map)
            rmap[tok] = value
            by_value[value] = tok
        return by_value[value]

    masks = [(ps, pe, token_for(text[ps:pe])) for ps, pe in pairs]
    persons = [(t, v) for t, v in rmap.items() if t.startswith("OSOBA_") and len(v.split()) >= 2]
    asks = []
    for s, e in spans:
        if in_pair(s, e):
            continue
        verdict, ref = _decide_single(text, s, e, adj, persons)
        if verdict == "MASK":
            masks.append((s, e, ref or token_for(text[s:e])))
        elif verdict == "ASK":
            asks.append((s, e))
    out, shifts = text, []
    for s, e, tok in sorted(masks, reverse=True):
        out = out[:s] + tok + out[e:]
        shifts.append((s, e, len(tok) - (e - s)))
    ask_spans = []
    for s, e in asks:
        d = sum(delta for ms, me, delta in shifts if me <= s)
        ask_spans.append({"start": s + d, "end": e + d, "rule": "R1", "reason": "Możliwe nazwisko — do decyzji"})
    logger.info("[OSOBA-DECIDER] MASK %d, ASK %d", len(masks), len(ask_spans))
    return out, rmap, ask_spans
