"""
ner_blocklist.py  v1.7
Historia zmian:
  v1.5 — Dynamiczne ładowanie miast, ulic i placówek medycznych z plików JSON.
          SpaCy nie będzie klasyfikował "Gdańsk", "Leśna", "klinika" jako OSOBA/FIRMA.
          Dla każdego wpisu generowany jest wariant ASCII (bez ogonków) — OCR
          często zwraca "Gdansk" zamiast "Gdańsk". Filtr: min 4 znaki, bez cyfr,
          tylko jednoliterowe i wieloliterowe — brak krótkich ryzyk FP.
  v1.4 — Fałszywe pozytywy z dokumentów komorniczych i faktur.
  v1.2 — [BUG-NER-02] Dodano słowa kluczowe dokumentów prawno-administracyjnych
          i komorniczych do _NER_BLOCKLIST. SpaCy klasyfikował je jako OSOBA lub FIRMA,
          przez co trafiały do reverse_map i wywoływały false positive guard MAP_LEAK.
          Potwierdzone przez benchmark: "ORZEKAM" jako FIRMA_005 blokował cały dokument
          przez guard GLOBALNY_PLAIN (doc_00025.png).
          Dodane grupy:
          - Formuły decyzyjne: "orzekam", "pouczenie", "wszczęciu", "wszczął",
            "nakazuję", "uchylam", "oddalam", "uwzględniam", "stwierdzam",
            "zobowiązuję", "pouczam", "informuję", "zawiadamiam"
          - Role procesowe: "zainteresowany", "zainteresowanemu", "zainteresowanej",
            "zainteresowanego", "dłużnik", "dłużnika", "dłużnikowi", "dłużnicy",
            "komornik sądowy", "komornika sądowego", "komornikowi sądowemu"
  v1.3 — Dodano skróty identyfikatorów, rejestrów i dokumentów prawnych:
          Identyfikatory: regon, pesel, iban, pkd, fv
          Rejestry/instytucje: krus, ceidg, bdo, uodo, ops, mops, gops
          Skróty aktowe: km, kmp, sygn, poz, lp, ust, art, par
          Skróty z dokumentów: umw, sko, iod, kw
          Już były (pominięto): nip, zus, nfz, gus, pit, vat, krs, rodo
  v1.1 — [BUG-4] Dodano skróty instytucji do _NER_BLOCKLIST:
          PPK, KNF, RPO, TK, PIP, GUS, NIK, UOKiK — zeby SpaCy
          nie klasyfikowal ich jako FIRMA.

Dane dla ner_layer.py — blocklista instytucji/słów pospolitych
i sufiksy prawne wymuszające klasyfikację FIRMA.

Wydzielone z ner_layer.py żeby plik z logiką nie puchł.
Edycja tutaj nie wymaga znajomości kodu ner_layer.py.
"""

import json as _json
import os as _os
import unicodedata as _ud

_BACKEND_DIR = _os.path.dirname(_os.path.abspath(__file__))


def _strip_pl(s: str) -> str:
    return _ud.normalize("NFD", s).encode("ascii", "ignore").decode()


def _load_geo_file(fname: str, skip_digits: bool = True) -> set:
    """Słowa (min 4 znaki, lowercase) z listy JSON + warianty bez polskich znaków."""
    path = _os.path.join(_BACKEND_DIR, fname)
    if not _os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        items = _json.load(f)
    words: set[str] = set()
    for item in items:
        if isinstance(item, str) and len(item) >= 4 and not (skip_digits and any(ch.isdigit() for ch in item)):
            low = item.lower()
            words.update((low, _strip_pl(low)))
    return words


def _load_geo_words() -> dict:
    """Miasta, ulice i placówki medyczne — osobno, bo filtr OSOBA rozróżnia pochodzenie (LYNX-NER-GEO-EXACT)."""
    return {"city": _load_geo_file("cities.json"), "street": _load_geo_file("street_names.json"),
            "med": _load_geo_file("medical_facilities.json", skip_digits=False)}


_GEO_BY_SOURCE: dict = _load_geo_words()
_GEO_WORDS: set = set().union(*_GEO_BY_SOURCE.values())


def _load_person_forms() -> frozenset:
    """[LYNX-T01] Wszystkie formy imion i nazwisk (lowercase) — potwierdzenie OSOBA przed filtrami geo."""
    forms: set[str] = set()
    for fname in ("names_inflected.json", "surnames_top1000.json"):
        path = _os.path.join(_BACKEND_DIR, fname)
        if not _os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for base, variants in _json.load(f).items():
                forms.add(base.lower())
                forms.update(v.lower() for v in variants)
    return frozenset(forms)


_PERSON_FORMS: frozenset = _load_person_forms()

# dowodem że to firma, nie osoba.
_LEGAL_SUFFIXES: tuple = (
    "sp. z o.o.", "sp.z o.o.", "spółka z o.o.",
    "sp z o.o.", "sp z o.o", "sp. z o.o",
    "sp z o o",
    "sp. k.", "sp.k.", "spółka komandytowa",
    "sp. j.", "sp.j.", "spółka jawna",
    "s.a.", "s.a", "spółka akcyjna",
    "s.k.a.", "spółka komandytowo-akcyjna",
    "p.s.a.", "prosta spółka akcyjna",
    "sp. p.", "spółka partnerska",
    "s.c.", "spółka cywilna",
    "fundacja", "stowarzyszenie", "spółdzielnia",
    "ltd.", "ltd", "gmbh", "s.r.o.", "a.s.", "b.v.", "n.v.",
)

_LEGAL_SUFFIXES_LOWER: tuple = tuple(s.lower() for s in _LEGAL_SUFFIXES)


# ── Blocklista ────────────────────────────────────────────────────────────────

_NER_BLOCKLIST: set = {
    "bank",
    "zus",
    "ue",
    "nfz",
    "pip",
    "krs",
    "nip",
    "pit",
    "vat",
    "sad",
    "urzad",
    "spolka",
    "firma",
    "ustawa",
    "kodeks",
    "rodo",
    "zleceniodawca",
    "zleceniobiorca",
    "strony",
    "strona",
    "zarząd",
    "zarządu",
    "zarządowi",
    "prezes",
    "prezesa",
    "ze",
    "do",
    "na",
    "po",
    "od",
    "przy",
    "przez",
    "nad",
    "pod",
    "każdej",
    "każdego",
    "każdemu",
    "każdy",
    "każdą",
    "zgodnie",
    "zgodny",
    "zgodna",
    "zgodnych",
    "pracownik",
    "pracodawca",
    "pracownicy",
    "pracodawcy",
    "pracownikowi",
    "pracownika",
    "pracodawcę",
    "stron",
    "stronie",
    "kodeksu",
    "pracy",
    "kodeksem",
    "kodeksowi",
    "umowa",
    "umowie",
    "umowy",
    "umowę",
    "umową",
    "postanowienie",
    "postanowienia",
    "przepis",
    "przepisy",
    "przepisami",
    "wynagrodzenie",
    "wynagrodzenia",
    "wynagrodzeniu",
    "egzemplarz",
    "egzemplarzy",
    "egzemplarzach",
    "egzemplarzem",
    "nieokreślony",
    "nieokreśloną",
    "nieokreślonego",
    "stanowisko",
    "stanowiska",
    "etat",
    "tygodniowo",
    "siedziba",
    "siedziby",
    "siedzibie",
    "urlop",
    "urlopu",
    "urlopowi",
    "roboczych",
    "rocznie",
    "jednobrzmiących",
    "jednobrzmiący",
    "pracodawcą",
    "zleceniobiorcy",
    "zleceniobiorcę",
    "zleceniodawcy",
    "zleceniodawcę",
    "wykonawca",
    "wykonawcy",
    "wykonawcę",
    "zamawiający",
    "zamawiającego",
    "zamawiającemu",
    "najemca",
    "wynajmujący",
    "dzierżawca",
    "sprzedawca",
    "kupujący",
    "nabywca",
    "sąd najwyższy",
    "sądu najwyższego",
    "sądowi najwyższemu",
    "sąd rejonowy",
    "sądu rejonowego",
    "sądowi rejonowemu",
    "sąd okręgowy",
    "sądu okręgowego",
    "sądowi okręgowemu",
    "sąd apelacyjny",
    "sądu apelacyjnego",
    "sąd administracyjny",
    "naczelny sąd administracyjny",
    "wojewódzki sąd administracyjny",
    "trybunał konstytucyjny",
    "trybunał sprawiedliwości unii europejskiej",
    "zakład ubezpieczeń społecznych",
    "kasa rolniczego ubezpieczenia społecznego",
    "państwowa inspekcja pracy",
    "urząd skarbowy",
    "urząd celno-skarbowy",
    "urząd ochrony danych osobowych",
    "urząd ochrony konkurencji i konsumentów",
    "urząd zamówień publicznych",
    "główny urząd statystyczny",
    "główny urząd nadzoru budowlanego",
    "komisja nadzoru finansowego",
    "rzecznik praw obywatelskich",
    "rzecznik praw dziecka",
    "rzecznik małych i średnich przedsiębiorców",
    "narodowy bank polski",
    "bank gospodarstwa krajowego",
    "polska agencja nadzoru audytowego",
    "agencja restrukturyzacji i modernizacji rolnictwa",
    "pracownicze plany kapitałowe",
    "rada ministrów",
    "sejm rzeczypospolitej polskiej",
    "senat rzeczypospolitej polskiej",
    "kancelaria prezesa rady ministrów",
    "ministerstwo finansów",
    "ministerstwo sprawiedliwości",
    "ministerstwo pracy i polityki społecznej",
    "ministerstwo rodziny i polityki społecznej",
    "europejski trybunał praw człowieka",
    "europejski trybunał sprawiedliwości",
    "urząd pracy",
    "powiatowy urząd pracy",
    "wojewódzki urząd pracy",
    "anny jagiellonki",
    "jana pawła",
    "jana pawła ii",
    "stefana batorego",
    "kazimierza wielkiego",
    "bolesława chrobrego",
    "władysława jagiełły",
    "tadeusza kościuszki",
    "józefa piłsudskiego",
    "romualda traugutta",
    "stefana żeromskiego",
    "adama mickiewicza",
    "juliusza słowackiego",
    "stanisława wyspiańskiego",
    "henryka sienkiewicza",
    "bolesława prusa",
    "marii curie",
    "marii skłodowskiej",
    "marii skłodowskiej-curie",
    "mikołaja kopernika",
    "fryderyka chopina",
    "ludwika waryńskiego",
    "zakładu ubezpieczeń społecznych",
    "zakładowi ubezpieczeń społecznych",
    "zakładem ubezpieczeń społecznych",
    "pracowniczych planach kapitałowych",
    "pracowniczymi planami kapitałowymi",
    "reprezentowany/a",
    "reprezen",
    "reprezentowaną",
    "reprezentowany",
    "sąd właściwy",
    "sądu właściwego",
    "sądem właściwym",
    "sądowi właściwemu",
    "auftragsnummer",
    "warenausgangnr",
    "wanessa",
    # [BUG-NER-02] Formuły decyzyjne i procesowe — SpaCy klasyfikuje je jako OSOBA/FIRMA
    # Potwierdzone przez benchmark: "ORZEKAM" jako FIRMA_005 → guard MAP_LEAK blokada
    # Formuły decyzyjne dokumentów administracyjnych i sądowych
    "orzekam",
    "nakazuję",
    "nakazuje",
    "uchylam",
    "oddalam",
    "uwzględniam",
    "uwzgledniamy",
    "stwierdzam",
    "zobowiązuję",
    "zobowiazuje",
    "pouczam",
    "informuję",
    "informuje",
    "zawiadamiam",
    "zawiadamia",
    "wszczął",
    "wszczal",
    "wszczęciu",
    "wszczecia",
    "pouczenie",
    "pouczenia",
    # Role procesowe (uzupełnienie — formy odmiany których nie ma wyżej)
    "zainteresowany",
    "zainteresowanemu",
    "zainteresowanej",
    "zainteresowanego",
    "zainteresowaną",
    "dłużnik",
    "dluznik",
    "dłużnika",
    "dluznika",
    "dłużnikowi",
    "dluznikowi",
    "dłużnicy",
    "dluznikow",
    "komornik sądowy",
    "komornika sądowego",
    "komornikowi sądowemu",
    "komornik sadowy",
    "komornika sadowego",
    # [BUG-4] Skróty instytucji — nie powinny trafiać jako FIRMA
    "ppk",
    "knf",
    "rpo",
    "tk",
    "pip",
    "gus",
    "nik",
    "uokik",
    # [v1.3] Identyfikatory prawne i podatkowe
    "regon",
    "pesel",
    "iban",
    "pkd",
    "fv",
    # [v1.3] Rejestry i instytucje pomocnicze
    "krus",
    "ceidg",
    "bdo",
    "uodo",
    "ops",
    "mops",
    "gops",
    # [v1.3] Skróty aktowe i pozycje dokumentu
    "km",
    "kmp",
    "sygn",
    "poz",
    "lp",
    "ust",
    "art",
    "par",
    # [v1.3] Skróty z dokumentów biurowych i umów
    "umw",
    "sko",
    "iod",
    "kw",
    # [BUG-NER-FP] Widziane w UI: OSOBA_006="KONTROLNA", OSOBA_007="Encje"
    # SpaCy błędnie klasyfikuje te słowa jako OSOBA/FIRMA
    "kontrolna",
    "kontrolny",
    "kontrolne",
    "kontrolnych",
    "kontrolnego",
    "encje",
    "encja",
    "encji",
    # [BUG-NER-FP-INSTRUKCJE] PSE-2026-0756: słowa z UI/instrukcji klasyfikowane jako encje
    "guard",
    "guardem",
    "guardu",
    "guardzie",
    "wkleić",
    "wklej",
    "wklejam",
    "wklejanie",
    "share",
    "dluzn",
    "red",
    # PSE-2026-0820: nagłówek sekcji UI klasyfikowany jako OSOBA
    "emaile",
    "email",
    "emailów",
    "emailami",
    # [v1.4] Fałszywe pozytywy z dokumentów komorniczych i faktur
    # SpaCy klasyfikował te słowa jako OSOBA lub FIRMA
    # Terminy medyczne i administracyjne — nie są PII
    "kartoteka",
    "kartoteki",
    "kartotece",
    "kartoteką",
    "historia",
    "historii",
    "historię",
    "historią",
    "skierowanie",
    "skierowania",
    "skierowaniu",
    "wynik",
    "wyniki",
    "wyników",
    "zaświadczenie",
    "zaswiadczenie",
    "zaświadczenia",
    "zaswiadczenia",
    "polisa",
    "polisy",
    "polisę",
    "polisą",
    "recepta",
    "recepty",
    "receptę",
    "receptą",
    "doreczone",
    "doręczone",
    "wplate",
    "wpłatę",
    "wpłata",
    "wplata",
    "platnosc",
    "płatność",
    "platnosci",
    "płatności",
    "odebral",
    "odebrał",
    "odebrala",
    "odebrała",
    "dostarczono",
    "doreczono",
    "doręczono",
}


# [LYNX-NER-GEO-EXACT] Forma imienia/nazwiska obecna w geo wyłącznie jako nazwa ulicy („ul. Kowalskiego”) —
# nie miasto, nie placówka, nie ręczny wpis. Tylko dla tych form filtr nie odrzuca encji OSOBA; blocklista bez zmian.
_STREET_ONLY_PERSON_FORMS: frozenset = frozenset(
    (_GEO_BY_SOURCE["street"] & _PERSON_FORMS) - _GEO_BY_SOURCE["city"] - _GEO_BY_SOURCE["med"] - _NER_BLOCKLIST
)

# Połącz z dynamicznie załadowanymi słowami geo i medycznymi
_NER_BLOCKLIST = _NER_BLOCKLIST | _GEO_WORDS

# Prefiksy blocklista — obliczane raz przy imporcie.
# Tylko jednowyrazowe wpisy — wielowyrazowe instytucje (np. "kancelaria
# prezesa rady ministrów") generowałyby prefiksy blokujące całe rodziny
# słów ("kancelar" blokuje każdą kancelarię). Wielowyrazowe chronione
# przez exact match w _NER_BLOCKLIST.
_NER_BLOCKLIST_PREFIXES: frozenset[str] = frozenset(
    b[:8].lower() for b in _NER_BLOCKLIST
    if len(b) >= 6 and " " not in b
)
