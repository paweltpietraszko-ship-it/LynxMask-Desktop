"""
osoba_not_person.py — [LYNX-OSOBA-NOT-PERSON] słowa, których pojedynczo nie zakrywamy jako OSOBA (zasada Mobile).

Źródło list: LynxMask Mobile `app/src/main/java/com/lynxmask/app/NameEngine.kt` — OSOBA_DENYLIST (:291–332),
WHITE_LIST_DOCUMENTS (:217), WHITE_LIST_COMMON_WORDS (:244); kalendarz/kraje/miasta — dotychczasowa lista Desktop
(`layers/ner_adapter.py`, port E2b). Kolejne słowa dopisujemy tylko po potwierdzonym fałszywym alarmie (jak Mobile).

- OSOBA_DENYLIST — potwierdzone kolizje: jednowyrazowa OSOBA odrzucana zawsze, także gdy słowo jest formą imienia/nazwiska
  (Morfeusz: „Data” imię, „Osoba”/„Zapłata” nazwisko). Kompromis jak w Mobile, zaakceptowany przez Pawła 21.10.
- WHITE_LISTS — odrzucają tylko słowo spoza słowników imion/nazwisk („Maja”, „Maj” zostają).
- DICTIONARY_PATH_DENYLIST — zbiór ścieżki słownikowej `_apply_dictionary_names` bez zmian (denylista + kalendarz/kraje/miasta).
"""
from __future__ import annotations

import contextvars
import json
import os
import re

OSOBA_DENYLIST: frozenset[str] = frozenset((
    "zamieszkania zameldowania służbowa służbowy wydział wydziału wydzialu wydziatu informacji informacj uzyskanych "
    "niejszej nin icznie sąd sądu rejonowy rejonowa okręgowy okręgowa skarbowy skarbowa sędzia sędziego sędzi urząd "
    "urzędu gminy gmina ulica ulicy adres adresu imię nazwisko pesel numer miejscowość miejscowości rodo data dane "
    "danych nikach osoba osoby osobie osobę osobą osób osobom osobami osobach zapłata zapłaty zapłacie zapłatę zapłatą "
    "zapłat zapłatom zapłatami zapłatach łączna łącznej łączną łączny łączne łącznego łącznemu łącznym łącznych "
    "łącznymi działający działająca działające działającego działającej działającemu działającym działających "
    "działającymi działając musi musisz musimy musicie muszę muszą "
    "zawarta zawarty zawarte").split())  # [LYNX-NAMES-DICT-CLEAN] „Zawarta pomiędzy:” — spaCy persName, 444× w pl-pii

# Białe listy Mobile: kalendarz, kraje, miasta (formy najczęstsze w dokumentach)
_CALENDAR_GEO: frozenset[str] = frozenset((
    "styczeń luty marzec kwiecień maj czerwiec lipiec sierpień wrzesień październik listopad grudzień stycznia lutego "
    "marca kwietnia maja czerwca lipca sierpnia września października listopada grudnia poniedziałek wtorek środa "
    "czwartek piątek sobota niedziela polska niemcy francja włochy hiszpania portugalia irlandia belgia austria "
    "szwajcaria czechy słowacja węgry rumunia bułgaria grecja szwecja norwegia dania finlandia estonia łotwa litwa "
    "białoruś ukraina rosja kanada chiny japonia korea warszawa kraków gdańsk wrocław poznań łódź katowice lublin "
    "białystok rzeszów szczecin bydgoszcz toruń kielce gliwice zabrze bytom olsztyn opole gdynia częstochowa radom "
    "sosnowiec tychy rybnik warszawy krakowa gdańska wrocławia poznania łodzi lublina białegostoku rzeszowa szczecina "
    "bydgoszczy torunia kielc gliwic zabrza bytomia olsztyna opola gdyni częstochowy radomia sosnowca warszawie "
    "krakowie gdańsku wrocławiu poznaniu lublinie białymstoku rzeszowie szczecinie toruniu kielcach gliwicach zabrzu "
    "bytomiu olsztynie opolu górze górę górą zielonej").split())

# Mobile WHITE_LIST_DOCUMENTS (NameEngine.kt:217)
_DOCUMENTS: frozenset[str] = frozenset((
    "umowa aneks załącznik protokół faktura nota rachunek oferta zamówienie zlecenie wniosek podanie pismo decyzja "
    "postanowienie wyrok nakaz zaświadczenie świadectwo certyfikat polisa regulamin statut ustawa kodeks rozporządzenie "
    "dyrektywa uchwała prawo dekret").split())

# Mobile WHITE_LIST_COMMON_WORDS (NameEngine.kt:244)
_COMMON_WORDS: frozenset[str] = frozenset((
    "bez przez przed między według wobec około wśród poza ponad pod nad przy dla jako oraz albo lecz jednak czyli więc "
    "zatem gdyż chociaż kodu pocztowego numer ulicy lokalu budynku miejscowości gminy powiatu dzielnicy adres adresu "
    "adresem adresowi adresie adresów adresami adresach adresowy adresowa adresowe adresowego adresowej adresowym "
    "numerem numerowi numerze numerów numerami address bill invoice total date from to due payment not for per page of "
    "and or the amount number vat net gross poland warsaw company name email phone city street country tax ref order "
    "item qty unit price subtotal description terms bank account swift iban issued paid balance note notes attn subject "
    "re dear regards sincerely yours zamieszkania zamieszkały zamieszkała zamieszkałej zamieszkałego zamieszkałemu "
    "zamieszkałe wydziału wydziałem wydziałowi wydziałach sp sł poe pl").split())

WHITE_LISTS: frozenset[str] = _CALENDAR_GEO | _DOCUMENTS | _COMMON_WORDS
DICTIONARY_PATH_DENYLIST: frozenset[str] = OSOBA_DENYLIST | _CALENDAR_GEO


_morf = None


def _morfeusz_name(word: str) -> bool:
    """Czy Morfeusz zna słowo jako imię/nazwisko („Czerwiec”, „Styczeń” — Codex r4). Bez Morfeusza: True (nie odrzucamy)."""
    global _morf
    try:
        if _morf is None:
            import morfeusz2
            _morf = morfeusz2.Morfeusz()
        quals = {q.split("_(")[0] for i in _morf.analyse(word[:1].upper() + word[1:].lower()) for q in i[2][3]}
    except Exception:
        return True
    return bool(quals & {"imię", "nazwisko"})


def reject_single_osoba(entity_text: str, person_forms: frozenset[str]) -> bool:
    """Jednowyrazowa OSOBA, która nie jest osobą: z małej litery (jak regexy Mobile), z OSOBA_DENYLIST (zawsze)
    albo z białych list, gdy nie jest imieniem/nazwiskiem ani w słownikach, ani wg Morfeusza. Wielowyrazowe — False."""
    word = entity_text.strip()
    if not word or len(word.split()) > 1:
        return False
    low = word.lower()
    if word[0].islower() or low in OSOBA_DENYLIST:
        return True
    if len(word) > 1 and word.isupper() and low not in person_forms and not _morfeusz_name(word):
        return True  # [LYNX-OSOBA-PACK4] 1: etykieta WERSALIKAMI („OCZEKIWANE:”); „KOWALSKI” zostaje (Morfeusz: nazwisko)
    return low in WHITE_LISTS and low not in person_forms and not _morfeusz_name(word)


# ── [LYNX-OSOBA-PACK4] 3: patron w nazwie ulicy ──────────────────────────────────────────────────────────────────────
_STREET_CTX_RE = re.compile(r"(?:^|[\s(,;:])(?:ul|al|pl|os|aleja|ulica|plac|osiedle|skwer|rondo|bulwar)\.?[ \t]+"
                            r"(?:\d{1,2}[ \t]+)?(?:[A-ZŁŚŹĆŃĄĘÓŻ][\w-]*\.?[ \t]+){0,3}$", re.IGNORECASE)


def drop_street_osoba(text: str, ner_results: list) -> list:
    """Encje OSOBA zaczynające się w nazwie ulicy (spaCy zwraca „Władysława Stanisława” bez „ul.”) — odrzucone."""
    return [r for r in ner_results if not (r.label == "OSOBA" and inside_street_name(text, r.start))]


def inside_street_name(text: str, start: int) -> bool:
    """Słowo zaczyna się w nazwie ulicy („ul. Władysława Stanisława Reymonta”, „ul. Jana Pawła II”) — to adres, nie osoba."""
    return bool(_STREET_CTX_RE.search(text[text.rfind("\n", 0, start) + 1:start]))


# ── [LYNX-OSOBA-PACK4] krok 2: pojedyncze słowo jest OSOBA tylko z dowodem (zasada OWNERA „udowodnij, że jesteś osobą”) ──
# Bez dowodu słowo nie jest zakrywane, ale trafia do Guarda (`released()` → guard_residue R1): nic, co silnik uznał
# za możliwą osobę, nie przechodzi bez pytania człowieka.
_RELEASED: contextvars.ContextVar[list] = contextvars.ContextVar("osoba_released")
_TITLE_RE = re.compile(r"(?:^|[\s(])(?:[Pp]an(?:a|u|em|i|ią|owie|ów)?|[Pp]\.|[Dd]r\.?|mgr|inż\.|prof\.|adw\.|mec\.|r\.[ \t]?pr\.|"
                       r"[Ss]ędzi\w*|[Kk]s\.|[Śś]p\.)[ \t]+$")
_ROLE_RE = re.compile(r"(?i)\b(?:Sprzedawc|Nabywc|Kupując|Sprzedając|Kontrahent|Usługodawc|Usługobiorc|Zleceniobiorc|Zleceniodawc|"
                      r"Wykonawc|Dostawc|Odbiorc|Zamawiając|Najemc|Wynajmując|Pracodawc|Pracowni|Płatnik|Pozwan|Pow[óo]d|"
                      r"Wnioskodawc|Uczestni|Świad|Pełnomocni|Dłużni|Wierzyciel|Klient|Właściciel|Nadawc|Adresat|Podpis|"
                      r"Nazwisk|Imię i nazwisk|Zgłaszając|Ubezpieczon|Poszkodowan|Kierując|Sprawc|Oskarżon|Obwinion|"
                      r"Spadkodawc|Spadkobierc|Darczyńc|Obdarowan|Poręczyciel|Protokolant|Przewodnicząc|Prezes|Dyrektor|"
                      r"Kierownik|Opiekun|Lekarz|Pacjent|Uczeń|Uczni|Student|Profesor|Doktor|Mecenas|Ksiądz|Radc|Adwokat|Notariusz|"
                      r"Komornik)\w*[ \t]*:?[ \t]*$")
_CAP = r"(?:[A-ZŁŚŹĆŃĄĘÓŻ][a-ząćęłńóśźż]+|OSOBA_\d{3})"
_SEP = r"(?:[ \t]*,[ \t]*|[ \t]+(?:i|oraz|a|lub)[ \t]+)"
_BEFORE_RE = re.compile(r"(?:^|[\s(])([A-ZŁŚŹĆŃĄĘÓŻ][a-ząćęłńóśźż]+|[A-ZŁŚŹĆŃĄĘÓŻ]\.|OSOBA_\d{3})[ \t]+$")
_AFTER_RE = re.compile(r"[ \t]+([A-ZŁŚŹĆŃĄĘÓŻ][a-ząćęłńóśźż]+|OSOBA_\d{3})")
_REL_ADJ_RE = re.compile(r"(?:[scd]k|dzk)(?:i|a|ie|iego|iej|iemu|im|imi|ą|ich)$")
_RESTORE = {"a": "aą", "c": "cć", "e": "eę", "l": "lł", "n": "nń", "o": "oó", "s": "sś", "z": "zżź"}
_FIRST: frozenset[str] | None = None


def start_run() -> None:
    """Nowy dokument: pusty rejestr słów odrzuconych z braku dowodu (wołane na początku pipeline)."""
    _RELEASED.set([])


def released() -> list[str]:
    return list(dict.fromkeys(_RELEASED.get([])))


def first_names() -> frozenset[str]:
    global _FIRST
    if _FIRST is None:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "names_inflected.json"), encoding="utf-8") as f:
                _FIRST = frozenset(x for b, fs in json.load(f).items() for x in [b, *fs])
        except Exception:
            _FIRST = frozenset()
    return _FIRST


def _variants(word: str, cap: int = 64) -> list[str]:
    out = [""]
    for ch in word:
        opts = _RESTORE.get(ch.lower(), ch.lower())
        out = [p + (o.upper() if ch.isupper() else o) for p in out for o in opts][:cap]
    return out


def _common_or_person(word: str) -> tuple[bool | None, bool | None, bool | None]:
    """(słowo ma znaczenie pospolite, Morfeusz zna je jako imię/nazwisko, jako nazwę geograficzną); bez Morfeusza (None, None, None).
    Przymiotnik na -ski/-cki nie jest „pospolity” („kowalski”); słowo bez ogonków sprawdzane w wariantach z ogonkami."""
    global _morf
    try:
        if _morf is None:
            import morfeusz2
            _morf = morfeusz2.Morfeusz()
        w = word[:1].upper() + word[1:].lower()
        folded = not re.search(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]", w)
        common = person = geo = False
        for i, cand in enumerate([w] + ([v for v in _variants(w) if v != w] if folded else [])):
            for it in _morf.analyse(cand):
                _form, lemma, tag, quals, _q = it[2]
                q = {x.split("_(")[0] for x in quals}
                if i == 0 and q & {"imię", "nazwisko"}:
                    person = True
                if i == 0 and "nazwa_geograficzna" in q:
                    geo = True
                pos = tag.split(":")[0]
                if pos == "ign" or not lemma[:1].islower() or (pos == "adj" and _REL_ADJ_RE.search(cand.lower())):
                    continue
                common = True
        return common, person, geo
    except Exception:
        return None, None, None


def _strong(w: str) -> bool:
    if w.startswith("OSOBA_"):
        return True
    common, person, _geo = _common_or_person(w)
    return bool(person) and common is False


def _list_neighbor(text: str, start: int, end: int) -> bool:
    """Element wyliczenia („Walczak i Ostrowski”, „Sęk, Domagała, Grzelik”) obok mocnego nazwiska albo tokenu osoby."""
    line_end = text.find("\n", end)
    before = text[text.rfind("\n", 0, start) + 1:start]
    after = text[end:line_end if line_end >= 0 else len(text)]
    if any(_strong(m.group(0)) for m in re.finditer(rf"{_CAP}(?={_SEP}(?:{_CAP}{_SEP}){{0,3}}$)", before)):
        return True
    m = re.match(rf"(?:{_SEP}({_CAP})){{1,4}}", after)
    return bool(m) and any(_strong(w) for w in re.findall(_CAP, m.group(0)))


def single_osoba_evidence(text: str, start: int, end: int, person_words=(), person_forms=frozenset()) -> bool:
    """Czy pojedyncze słowo text[start:end] ma dowód osoby: tytuł/Pan/Pani, rola w linii, imię/inicjał/token osoby obok,
    element listy z mocnym nazwiskiem, to samo słowo w pełnym imieniu i nazwisku dokumentu (`person_words`), albo
    nazwisko bez znaczenia pospolitego (Morfeusz). Brak dowodu → False i słowo trafia do rejestru dla Guarda.
    Błąd Morfeusza → True (zakrywamy jak dotąd)."""
    word = text[start:end]
    low = word.lower()
    if re.fullmatch(r"[\d\s.,:/-]+", word):
        return True  # sama liczba (kwota, numer) wzięta przez NER za osobę — zakrywamy jak dotąd; „Kont0” (OCR) ocenia krok 2
    if in_city_name(text, start, end):
        return False  # człon miejscowości („Jelenia Góra”, „Tomaszów Mazowiecki”) — nie osoba i nie pytanie (samo miasto jawne)
    before = text[text.rfind("\n", 0, start) + 1:start]
    names = first_names()
    m = _BEFORE_RE.search(before)
    n = _AFTER_RE.match(text, end)
    if (_TITLE_RE.search(before[-14:]) or _ROLE_RE.search(before)
            or (m and (m.group(1).startswith("OSOBA_") or m.group(1).endswith(".") or m.group(1).lower() in names))
            or (n and (n.group(1).startswith("OSOBA_") or (n.group(1).lower() in names and low not in names)))
            or any(_same_stem(p.lower(), low) for p in person_words) or _list_neighbor(text, start, end)):
        return True
    common, person, geo = _common_or_person(word)
    if common is None or (not common and (person or low in person_forms)):
        return True
    if geo and not person:
        return False  # wyłącznie nazwa miejsca (np. „Tomaszów”) — samo miasto jawne, bez pytania (polityka OWNERA)
    _RELEASED.get([]).append(word)  # [krok 2] bez dowodu: nie zakrywamy, Guard zapyta
    return False


def in_city_name(text: str, start: int, end: int) -> bool:
    """[LYNX-OSOBA-PACK4] 3: słowo jest członem nazwy wieloczłonowej miejscowości z bazy SIMC (`layers.address._CITY_FORMS`)."""
    from layers.address import _CITY_FORMS  # w funkcji — bez cyklu importów przy starcie
    word = text[start:end]
    prev = re.search(r"([A-ZŁŚŹĆŃĄĘÓŻ][\w-]+)[ \t]+$", text[max(0, start - 40):start])
    nxt = re.match(r"[ \t]+([A-ZŁŚŹĆŃĄĘÓŻ][\w-]+)", text[end:end + 40])
    return bool((prev and f"{prev.group(1)} {word}" in _CITY_FORMS) or (nxt and f"{word} {nxt.group(1)}" in _CITY_FORMS))


def _same_stem(a: str, b: str) -> bool:
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return k >= max(3, min(len(a), len(b)) - 3)


def person_words_of(values) -> list[str]:
    """Słowa (≥3 litery) z wielowyrazowych wartości osób — dowód „ta sama osoba wcześniej w pełnym imieniu i nazwisku”."""
    return [w for v in values if len(v.split()) > 1 for w in re.findall(r"[^\W\d_]{3,}", v)]


def filter_single_osoba(text: str, ner_results: list, person_forms=frozenset()) -> list:
    """Krok 2 dla encji NER: jednowyrazowa OSOBA zostaje tylko z dowodem."""
    pw = person_words_of([r.text for r in ner_results if r.label == "OSOBA"])
    return [r for r in ner_results if r.label != "OSOBA" or len(r.text.split()) > 1
            or single_osoba_evidence(text, r.start, r.start + len(r.text.rstrip(",.;:!? ")), pw, person_forms)]
