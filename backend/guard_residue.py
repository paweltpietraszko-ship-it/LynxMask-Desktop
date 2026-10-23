"""
guard_residue.py — [LYNX-GUARD-A] lista ostrzeżeń Guarda zamiast automatycznego [REDACTED] (S4 22.10).

Guard wskazuje JAWNE fragmenty finalnego tekstu, każdy do decyzji użytkownika (Zakryj/Zostaw). Nic tu nie maskuje.
Źródła: dotychczasowe wzorce HIGH/MEDIUM i MAP_LEAK (`output_guard`) + grupy pozostałości R1–R5 (brief v2):
R1 słowa nieopisane przez nikogo (`_unknown`), R2 inicjały, R3 resztki przy tokenach, R4 identyfikatory w kontekście,
R5 nazwy firm. [LYNX-OSOBA-LAYOUT] Guard nie zgaduje osób w całym tekście: słowa znane Morfeuszowi i decyzje silnika są dla niego
niewidzialne (dawne R1 „słownik/końcówka” i kanał `released` usunięte — osobę rozpoznaje silnik, `person_layout`).
Wartości fragmentów trafiają tylko do odpowiedzi dla UI, nigdy do logów (S5).
"""
from __future__ import annotations

import re

from guard_allowlist import ANY_YELLOW, silenced
from guard_allowlist import load as load_allowlist  # noqa: F401  [S5] zaszyfrowana lista (pipeline)
from output_guard import _LEAK_HIGH, _LEAK_MEDIUM, _TOKEN_RE

_UP = "A-ZĄĆĘŁŃÓŚŹŻ"
_LO = "a-ząćęłńóśźż"
_PUBLIC_RE = re.compile(  # R5: tylko urzędy/sądy/samorząd/organy — nie „Centrum”, „Instytut”, „Fundusz” (bywają firmami)
    r"\b(?:Sąd\w*|Urz[ąę]d\w*|Gmin\w*|Powiat\w*|Starostw\w*|Województw\w*|Skarb\w* Państwa|Prokuratur\w*|Policj\w*"
    r"|Ministerstw\w*|Komornik\w*|Rad\w* Miasta|Izb\w* Skarbow\w*|ZUS|NFZ|KRUS|GUS|NIK|UODO|KNF|UOKiK)\b")
# R2: imię albo token osoby + jedna wielka litera z kropką (bez „S.A.”)
_INITIAL_RE = re.compile(rf"\b(?:(OSOBA_\d{{3}})|([{_UP}][{_LO}]+))[ \t]+([{_UP}])\.(?![ \t]?[A-Za-z]\.)")
# R3: cyfry tuż przed/po tokenie NUMER/ADRES, kod pocztowy (+ miejscowość) po ADRES, litery doklejone do tokenu
_DIGITS_BEFORE_RE = re.compile(r"(?<![\w/.-])(\d[\d \-]{0,10}?)[ \t]?$")
_DIGITS_AFTER_RE = re.compile(r"[ \t]?(\d[\d\-]*(?:[ \t]\d+)?)(?![\w/])")
# [LYNX-OSOBA-PACK4] miejscowość tuż po zakrytym adresie („ADRES_003, Ostrów Wielkopolski”) — część adresu, nie „samo miasto”
_CITY_AFTER_RE = re.compile(rf",[ \t]+([{_UP}][{_LO}]+(?:[ \t-][{_UP}][{_LO}]+){{0,2}})(?![\w-])")
_POSTAL_AFTER_RE = re.compile(rf",?[ \t]+(\d\d[ \t]?-[ \t]?\d(?:[ \t]?\d){{2}}(?:[ \t]+[{_UP}][\w-]+)?)")
_GLUED_RE = re.compile(r"([A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]{2,})")
# R4: słowo-klucz + wartość z co najmniej dwiema cyframi
_ID_KEY_RE = re.compile(
    r"\b(?:nr|numer\w*|działk\w*|klient\w*|kont[ao]|rachunk\w*|ur\.|urodz\w*|tel\.|telefon\w*|kom\.|PESEL|NIP|REGON|KRS"
    r"|dowod\w*|paszport\w*|legitymacj\w*|KW|księg\w* wieczyst\w*)(?![\w])[ \t]*[.:#]?[ \t]*", re.IGNORECASE)
_ID_VALUE_RE = re.compile(r"[A-Z0-9][A-Z0-9/.\-]*[A-Z0-9]|\d")
_DZU_RE = re.compile(r"Dz\.\s?U|poz\.|art\.|ust\.|§", re.IGNORECASE)
# [LYNX-FIRMA-PROOF] „nr” po rzeczowniku porządkowym / aktu publicznego to struktura pisma, nie dana osoby: „Dz. U. z 2010 r.
# Nr 113”, „droga krajowa nr 87”, „załącznik nr 2”, „pytanie nr 21”, „ogłoszenie nr 2016/S …”, „uchwała nr XII/1/19”.
_STRUCT_NR_RE = re.compile(r"(?:Dz\.\s?U|M\.\s?P|Dziennik\w*|Biuletyn\w*)\b[\s\S]{0,45}$|\b(?:drog\w*|autostrad\w*|załącznik\w*|pytani\w*|rozdział\w*|punkt\w*|pkt\.?|tabel\w*|częś\w*|zadani\w*|pakiet\w*|pozycj\w*|str\.?|stron\w*|wzor\w*|wzór|formularz\w*|rysun\w*|ogłoszeni\w*|uchwał\w*|zarządzeni\w*|rozporządzeni\w*|ustaw\w*|norm\w*|lini\w*|decyzj\w*|zał\.|zarzut\w*|odpowied\w*|jednostk\w*|LEX|Legalis|OSN\w*)(?:\s+\w+)?\s*$", re.IGNORECASE)
_BLANK_RE = re.compile(r"[ \t]*")
# R5: rola kontrahenta + nazwa; nazwa z formą prawną
_ROLE_RE = re.compile(
    r"\b(?:Sprzedawc\w*|Nabywc\w*|Kontrahent\w*|Usługodawc\w*|Zleceniobiorc\w*|Zleceniodawc\w*|Wykonawc\w*|Dostawc\w*"
    r"|Odbiorc\w*|Zamawiając\w*|Najemc\w*|Wynajmując\w*|Pracodawc\w*|Ubezpieczyciel\w*|Płatnik\w*|Firma)[ \t]*:[ \t]*"
    r"([^\r\n,;]{2,80})")
_FORM = r"(?i:sp\.[ \t]*z[ \t]*o\.[ \t]*o\.?|sp\.[ \t]*k\.[ \t]*a\.?|sp\.[ \t]*[jkp]\.?|s\.[ \t]*a\.|s\.[ \t]*c\.|p\.[ \t]*s\.[ \t]*a\.?)"
_LABEL_RE = re.compile(r"[^\W\d_][\w ]{0,30}:")  # etykieta pola: „Nabywca:”, „Dane kontaktowe:”
_SENTENCE_END_RE = re.compile(rf"\.[ \t]+(?=[{_UP}][{_LO}])")
_FORM_NAME_RE = re.compile(
    rf"(?<![\w„\"])[{_UP}0-9„\"][\w„\"&.\-]*(?:[ \t]+[{_UP}0-9„\"&][\w„\"&.\-]*){{0,4}}[ \t]+{_FORM}(?!\w)")

_morf = None


def _morf_interps(word: str) -> list | None:
    global _morf
    try:
        if _morf is None:
            import morfeusz2
            _morf = morfeusz2.Morfeusz()
        return _morf.analyse(word)
    except Exception:
        return None


# ── [LYNX-OSOBA-LAYOUT] R1: słowo nieopisane przez nikogo ─────────────────────────────────────────────────────
# Pytanie dostaje: (a) słowo, które słownik zna wyłącznie jako imię/nazwisko, a silnik go nie zakrył („Kasprzak”);
# (b) słowo, którego Morfeusz nie zna (ign), nie imię, nie z białej listy ani skrótów, i nie zwykłe słowo po błędzie OCR.
# Słowa ze zwykłym znaczeniem („Kawa”, „Termin”) i decyzje silnika są dla Guarda niewidzialne. Obce → pytanie.
# biała lista (316 słów ze słownika nazwisk PESEL używanych w pismach jako zwykłe słowa; zatwierdzona 23.10.2026,
# tasks/LYNX-OSOBA-REDESIGN/evidence_2026-10-23/biala_lista_pesel_zatwierdzona.csv na gałęzi task/LYNX-OSOBA-REDESIGN)
_WHITELIST = frozenset("""
angielski art badan bank bać beda beza bieg blat brak bram brudny budynek budziło być ból błąd cały cech cel cena
chodnik choroba chyba ciemny ciepła ciągło ciężar ciężki cyfra czarna czuja czynsz członka dabrowski dach dal daleki dan
dana danych doba dobra dobry dola dorobek dota druk duży dym działa dzienia dziennik dzierżawa dzień długi forma franka
fundament gleba godzina gorączka gotówka granica graniczna graniczny grecki grono grosz grunt grupa handel izba jakim
jasny jałowy jeżyk kamień karny kasa kilka klub klucz koda kol kola kolej komoda komornik koniec kopia kosa koła końca
kość kropka krótki ksiąg książka kul kupiecki kupny kurs lampa lata lec lepsza lewy leśna leśny lider link litera los
luka macierzyński mandat marcu mas masa masek mazowiecki mała mały miedza miesiąc moc mocny mokry mostowa mostowy
musiała myć nadzieja nagły należyta należyty nam naprawa nast naturalny nauka nica niewiadoma niewiadomy niska niski
nocny nowy obecna obecny obrał ofiara oko okrągła okrągły olej opieka organ osada osoba ołówek paczek paczka pakiet pal
paleta pan papier parka pas paz per pieczątka pieniądz pieniężna pieniężny pilny pilot pić poczta poda podstawa pokrywa
pokój pola polska polski pompa ponieważ poprawka pora poseł posiadała postawa potrzeba powaga powierza pożyczka prawda
proba przeszło przyczyna przypis próba pusty rad radna radny ram rama rana raz reja robota rodzaj rok rynka rząd równa
równy ręka sadowy sali sekunda senator siatka sil silny skrajny składnik spadek spora sporna sporny sposób stal stan
stary statek stawiany stań stempel straż strona studencki student sum suma surowy syty szega szkoła sztuk szybka szybko
słowy tam tama termin tom tor trafny trawa troska trąd tuta tylko tym tys tysiąc udziela uliczny ułamek walka walor
warta warunek ważna widok winny wiosna woda wola wszelaki wycinka wyraz wójt wątek zamiar zapłata zasadny zatoka zawarty
zbieg zera zieleń zielony znak związek złoty łączna łączny ściana ścieżka ścisło ścisły środek śruba świadek świat
światowy żałoba żołnierz żyto żółty
""".split())

_ABBR = frozenset(("sygn", "wyd", "lex", "dz", "poz", "nr", "tel", "ul", "al", "pl", "os", "godz", "str", "ust", "pkt", "lit", "art",
                   "par", "rozdz", "zał", "red", "oprac", "tzw", "np", "itd", "ok", "tj", "im", "sp", "zob", "por", "kpc", "kpk",
                   "kpa", "pzp", "kc", "kk", "kp", "kro", "op", "cyt", "wg", "nt", "ws", "dot", "przyp", "uzas", "sent", "akt"))
# typowe pomyłki OCR: (co odczytano, co mogło być); od indeksu 9 — same ogonki
_OCR_SUBST = (("m", "rn"), ("rn", "m"), ("t", "ł"), ("i", "ł"), ("l", "ł"), ("i", "l"), ("l", "i"), ("o", "c"), ("c", "o"),
              ("a", "ą"), ("e", "ę"), ("o", "ó"), ("s", "ś"), ("z", "ż"), ("z", "ź"), ("c", "ć"), ("n", "ń"), ("ż", "ź"), ("ź", "ż"))
_DIACRITIC_FROM = 9
_WORD_RE = re.compile(rf"(?<![\w-])[{_UP}][{_LO}]{{2,}}(?:-[{_UP}][{_LO}]{{2,}})?(?![\w-])")


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


def _unknown(text: str, analyse):
    """Pozycje słów nieopisanych przez nikogo: (start, end, "R1", powód). `analyse` = Morfeusz (None przy błędzie → pytanie)."""
    from osoba_not_person import _variants, first_names
    names, white = first_names(), _WHITELIST
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
            if not re.search(r"[ąćęłńóśźż]", low):
                variants = [analyse(v) for v in _variants(w)[1:]]
                if any(_only_person_name(q) for q in variants):
                    yield m.start(), m.end(), "R1", "Nazwisko lub imię według słownika — silnik go nie zakrył"
                    continue  # Codex r1 F1: „Ladzinski” → „Ladziński” (wyłącznie nazwisko) — pytanie, nie wyciszenie
                if any(q and any(i[2][2] != "ign" and i[2][1][:1].islower() for i in q) for q in variants):
                    continue  # bez ogonków po OCR zwykłe słowo („Platnosc” → „płatność”)
            if _ocr_common(w, analyse):
                continue  # jedna typowa pomyłka OCR („Komomik”, „Wydziatu”)
        yield m.start(), m.end(), "R1", "Słowo nierozpoznane przez żadną warstwę — możliwe nazwisko"


def _r2(text: str):
    from ner_layer import _PERSON_FORMS
    for m in _INITIAL_RE.finditer(text):
        if m.group(1):
            yield m.start(3), m.end(), "R2", "Inicjał obok zakrytej osoby"
        elif m.group(2).lower() in _PERSON_FORMS:
            yield m.start(), m.end(), "R2", "Imię z inicjałem nazwiska"


def _r3(text: str):
    for t in _TOKEN_RE.finditer(text):
        kind = t.group(0).split("_")[0]
        found = []
        if kind in ("NUMER", "ADRES"):
            lo = max(0, t.start() - 14)
            b = _DIGITS_BEFORE_RE.search(text[lo:t.start()])
            s0 = lo + b.start(1) if b else 0
            if b and not (s0 and text[s0 - 1] in "/.-" or text[max(0, s0 - 6):s0].rstrip().endswith("dnia")
                          or kind == "ADRES" and len(b.group(1).strip()) == 1):  # „4 ADRES_001” = OCR „ul.”
                found.append(((lo + b.start(1), lo + b.end(1)), "Resztka numeru obok zakrytego fragmentu"))
            for rx, reason in ((_DIGITS_AFTER_RE, "Resztka numeru obok zakrytego fragmentu"),
                               (_POSTAL_AFTER_RE, "Kod pocztowy obok zakrytego adresu"),
                               (_CITY_AFTER_RE, "Miejscowość obok zakrytego adresu")):
                a = rx.match(text, t.end())
                if a and (rx is _DIGITS_AFTER_RE or kind == "ADRES"):
                    found.append((a.span(1), reason))
                    if rx is _POSTAL_AFTER_RE:
                        break  # kod z miejscowością już wskazany — bez drugiej pozycji na samą miejscowość
        g = _GLUED_RE.match(text, t.end())
        if g:
            found.append((g.span(1), "Litery doklejone do zakrytego fragmentu"))
        for (s, e), reason in found:
            frag = text[s:e].rstrip(" \t-")
            if frag.strip():
                yield s, s + len(frag), "R3", reason


def _r4(text: str):
    for k in _ID_KEY_RE.finditer(text):
        if _TOKEN_RE.match(text, k.start()):
            continue  # [LYNX-FIRMA-PROOF] „NUMER_010:1999” — słowo-klucz „numer” wewnątrz tokenu
        v = _ID_VALUE_RE.match(text, k.end())
        if not v or sum(c.isdigit() for c in v.group(0)) < 2 or _TOKEN_RE.match(text, v.start()):
            continue
        if _DZU_RE.search(text[max(0, k.start() - 12):k.start()]) or _STRUCT_NR_RE.search(text[max(0, k.start() - 60):k.start()]):
            continue
        if _TOKEN_RE.match(text, _BLANK_RE.match(text, v.end()).end()):
            continue  # [LYNX-FIRMA-PROOF] „2012/S NUMER_004” — resztka obok tokenu to R3, nie R4
        yield v.start(), v.end(), "R4", "Numer lub data w kontekście danych identyfikujących"


def _firm_ok(frag: str) -> bool:
    """R5: forma prawna = firma zawsze (Codex F1: „Centrum Projektowe MODRZEW sp. z o.o.”); bez niej wyłączone tylko
    urzędy publiczne („Centrum”, „Instytut”, „Fundusz” bywają firmami)."""
    if not re.search(rf"[{_UP}]", frag):
        return False
    return bool(re.search(_FORM + r"(?!\w)", frag)) or not _PUBLIC_RE.search(frag)


def _r5(text: str):
    for m in _ROLE_RE.finditer(text):
        s, frag = m.start(1), re.split(r"[ \t]{3,}", m.group(1))[0]  # FIX1: układ w dwóch kolumnach — tylko ta kolumna
        if _LABEL_RE.match(frag):
            continue  # FIX1: „Sprzedawca:   Nabywca:” — po etykiecie kolejna etykieta, nie nazwa
        cut = _TOKEN_RE.search(frag)
        frag = frag[:cut.start()] if cut else frag
        end = _SENTENCE_END_RE.search(frag)  # „RACHMISTRZ. Wczoraj…” → bez następnego zdania; „S.A.” zostaje
        if end:
            frag = frag[:end.start() + 1]
        frag = frag if re.search(_FORM + r"$", frag) else frag.rstrip(" \t.-–(")
        if len(frag) >= 3 and frag[0] not in _LO and _firm_ok(frag):
            yield s, s + len(frag), "R5", "Możliwa nazwa firmy, której silnik nie zakrył"
    for m in _FORM_NAME_RE.finditer(text):
        if not _TOKEN_RE.search(m.group(0)) and _firm_ok(m.group(0)):
            yield m.start(), m.end(), "R5", "Nazwa firmy z formą prawną"


def _patterns(masked: str):
    for label, rx in _LEAK_HIGH:
        for m in rx.finditer(masked):
            yield m.start(), m.end(), f"HIGH {label}", "Wygląda na numer identyfikacyjny"
    for label, rx, _w in _LEAK_MEDIUM:
        for m in rx.finditer(masked):
            yield m.start(), m.end(), f"MEDIUM {label}", "Wygląda na numer lub telefon"


def _map_leaks(text: str, values: list[str]):
    for v in values:
        for m in re.finditer(re.escape(v), text, re.IGNORECASE):
            yield m.start(), m.end(), "MAP_LEAK", "Ta wartość jest zakryta w innym miejscu dokumentu"


_RED = ("HIGH", "MAP_LEAK")


def collect_warnings(text: str, map_values: list[str] | None = None, allowlist: list | None = None) -> list[dict]:
    """Ostrzeżenia dla finalnego tekstu: [{id, start, end, fragment, rule, level, reasons}], posortowane po pozycji.
    Fragmenty nachodzące na siebie → jedna pozycja (wszystkie powody); nic wewnątrz tokenów; allowlista (fragment, reguła) wycisza tylko żółte (S5)."""
    tokens = [m.span() for m in _TOKEN_RE.finditer(text)]
    masked = _TOKEN_RE.sub(lambda m: "#" * len(m.group(0)), text)
    allow = [(a, ANY_YELLOW) if isinstance(a, str) else tuple(a) for a in allowlist or []]
    hits = []
    for src in (_patterns(masked), _map_leaks(masked, map_values or []), _unknown(text, _morf_interps),
                _r2(text), _r3(text), _r4(text), _r5(text)):
        for s, e, rule, reason in src:
            if s < e and not any(ts < e and s < te for ts, te in tokens) and not silenced(text[s:e], rule, allow):
                hits.append((s, e, rule, reason))
    out: list[dict] = []
    for s, e, rule, reason in sorted(hits):
        if out and s < out[-1]["end"]:
            w = out[-1]
            w["end"] = max(w["end"], e)
            w["fragment"] = text[w["start"]:w["end"]]
            if rule not in w["rules"]:
                w["rules"].append(rule)
            if reason not in w["reasons"]:
                w["reasons"].append(reason)
            continue
        out.append({"start": s, "end": e, "fragment": text[s:e], "rules": [rule], "reasons": [reason]})
    for i, w in enumerate(out):
        w["rule"] = w["rules"][0]
        w["level"] = "RED" if any(r.startswith(_RED) for r in w["rules"]) else "YELLOW"
        w["id"] = f"W{i + 1:03d}"
    return out


def shift_warnings(warnings: list[dict], offset: int) -> list[dict]:
    """Pozycje względem tekstu z nagłówkiem PSE (anonymized_preview)."""
    return [{**w, "start": w["start"] + offset, "end": w["end"] + offset} for w in warnings]
