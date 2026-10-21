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

OSOBA_DENYLIST: frozenset[str] = frozenset((
    "zamieszkania zameldowania służbowa służbowy wydział wydziału wydzialu wydziatu informacji informacj uzyskanych "
    "niejszej nin icznie sąd sądu rejonowy rejonowa okręgowy okręgowa skarbowy skarbowa sędzia sędziego sędzi urząd "
    "urzędu gminy gmina ulica ulicy adres adresu imię nazwisko pesel numer miejscowość miejscowości rodo data dane "
    "danych nikach osoba osoby osobie osobę osobą osób osobom osobami osobach zapłata zapłaty zapłacie zapłatę zapłatą "
    "zapłat zapłatom zapłatami zapłatach łączna łącznej łączną łączny łączne łącznego łącznemu łącznym łącznych "
    "łącznymi działający działająca działające działającego działającej działającemu działającym działających "
    "działającymi działając musi musisz musimy musicie muszę muszą").split())

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
    return low in WHITE_LISTS and low not in person_forms and not _morfeusz_name(word)
