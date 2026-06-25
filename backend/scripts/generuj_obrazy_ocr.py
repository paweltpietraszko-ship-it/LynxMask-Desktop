"""
generuj_obrazy_ocr.py  v2.0
============================
Generuje testowe obrazy PNG z losowymi danymi i losową degradacją.
Każde uruchomienie daje inne dokumenty — do testowania pipeline OCR LynxMask.

Wymagania: pip install Pillow numpy
Uruchomienie: python generuj_obrazy_ocr.py [--seed N] [--count N]
  --seed   N  ziarno losowości (domyślnie: losowe)
  --count  N  liczba obrazów do wygenerowania (domyślnie: 7)

Obrazy zapisywane w ./ocr_testy/
Każdy plik ma w nazwie seed i kategorię degradacji.
"""

import os
import sys
import random
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── Argumenty ─────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--seed",  type=int, default=None)
parser.add_argument("--count", type=int, default=7)
args = parser.parse_args()

SEED = args.seed if args.seed is not None else random.randint(1000, 9999)
RNG  = random.Random(SEED)
COUNT = args.count

OUTPUT_DIR = Path("ocr_testy")
OUTPUT_DIR.mkdir(exist_ok=True)

print(f"Seed: {SEED}  (użyj --seed {SEED} by odtworzyć ten zestaw)")

# ── Fonty ─────────────────────────────────────────────────────────────────────

def _find_font(names, size):
    dirs = [
        Path("C:/Windows/Fonts"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation"),
    ]
    for d in dirs:
        for name in names:
            p = d / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()

F_REG  = lambda s: _find_font(["arial.ttf","Arial.ttf","DejaVuSans.ttf","calibri.ttf","Calibri.ttf"], s)
F_BOLD = lambda s: _find_font(["arialbd.ttf","ArialBD.ttf","DejaVuSans-Bold.ttf","calibrib.ttf","Calibrib.ttf"], s)
F_MONO = lambda s: _find_font(["cour.ttf","Cour.ttf","DejaVuSansMono.ttf","lucon.ttf","Lucon.ttf"], s)

# ── Generatory danych ─────────────────────────────────────────────────────────

IMIONA   = ["Anna","Katarzyna","Marek","Piotr","Tomasz","Agnieszka","Janusz",
             "Krzysztof","Monika","Paweł","Ewa","Zbigniew","Dorota","Michał"]
NAZWISKA = ["Kowalski","Wiśniewska","Nowak","Wójcik","Kowalczyk","Kamińska",
             "Lewandowski","Zielińska","Szymański","Woźniak","Dąbrowski","Mazur"]
ULICE    = ["Długa","Zielona","Słoneczna","Lipowa","Kwiatowa","Polna",
             "Leśna","Wiejska","Krótka","Ogrodowa","Nowa","Główna"]
MIASTA   = [("Gdańsk","80"),("Warszawa","00"),("Kraków","30"),
             ("Wrocław","50"),("Poznań","60"),("Łódź","90"),("Katowice","40")]
FIRMY    = ["Towarzystwo Ubezpieczeń Wzajemnych","Powszechny Zakład Ubezpieczeń S.A.",
             "Bank PKO BP S.A.","Urząd Dzielnicy","Zakład Ubezpieczeń Społecznych",
             "Urząd Skarbowy","Sąd Rejonowy","Kancelaria Prawna"]
WYDZIALY = ["Wydział Likwidacji Szkód","Wydział Obsługi Klienta",
             "Dział Windykacji","Wydział Spraw Cywilnych","Sekretariat"]
TEMATY   = [
    ("ZGŁOSZENIE SZKODY MAJĄTKOWEJ",
     "Niniejszym zgłaszam szkodę w mieniu powstałą wskutek zalania lokalu.\n"
     "Proszę o przeprowadzenie oględzin przez rzeczoznawcę majątkowego.\n"
     "Wszelką korespondencję proszę kierować na podany adres zamieszkania."),
    ("WNIOSEK O WYDANIE ZAŚWIADCZENIA",
     "Zwracam się z prośbą o wydanie zaświadczenia potwierdzającego\n"
     "okres zameldowania pod wskazanym adresem. Dokument niezbędny\n"
     "do przedłożenia w instytucji finansowej w celu weryfikacji."),
    ("WEZWANIE DO ZAPŁATY",
     "Wzywam do uregulowania zaległej należności w terminie 14 dni.\n"
     "Brak reakcji spowoduje skierowanie sprawy na drogę sądową.\n"
     "Należność wraz z odsetkami wynosi kwotę wskazaną powyżej."),
    ("UMOWA NAJMU LOKALU",
     "Strony zawierają umowę najmu lokalu mieszkalnego na czas określony.\n"
     "Najemca zobowiązuje się do terminowego regulowania czynszu.\n"
     "Wszelkie zmiany umowy wymagają formy pisemnej pod rygorem nieważności."),
    ("PEŁNOMOCNICTWO",
     "Udzielam pełnomocnictwa do reprezentowania mnie przed wszelkimi\n"
     "organami administracji publicznej oraz instytucjami finansowymi.\n"
     "Pełnomocnictwo obejmuje prawo do składania oświadczeń woli."),
]

def losowy_pesel(rng):
    r = [rng.randint(0,9) for _ in range(11)]
    return "".join(map(str,r))

def losowy_nip(rng):
    a,b,c,d = rng.randint(100,999),rng.randint(100,999),rng.randint(10,99),rng.randint(10,99)
    return f"{a}-{b}-{c}-{d}"

def losowy_iban(rng):
    grupy = [f"{rng.randint(1000,9999)}" for _ in range(6)]
    ctrl = rng.randint(10,99)
    return f"PL{ctrl} " + " ".join(grupy)

def losowa_osoba(rng):
    imie    = rng.choice(IMIONA)
    nazwisko = rng.choice(NAZWISKA)
    # Fleksja — uproszczona
    if nazwisko.endswith("ski"): nazwisko_d = nazwisko[:-1]+"iego"
    elif nazwisko.endswith("ska"): nazwisko_d = nazwisko[:-1]+"iej"
    else: nazwisko_d = nazwiska = nazwisko
    return imie, nazwisko

def losowy_adres(rng):
    ulica = rng.choice(ULICE)
    nr    = rng.randint(1, 120)
    lok   = f"/{rng.randint(1,20)}" if rng.random() > 0.4 else ""
    miasto, kod_prefix = rng.choice(MIASTA)
    kod   = f"{kod_prefix}-{rng.randint(100,999)}"
    return f"ul. {ulica} {nr}{lok}", f"{kod} {miasto}", miasto

def generuj_dokument(rng):
    imie, nazwisko = losowa_osoba(rng)
    adres_ul, adres_kod, miasto = losowy_adres(rng)
    pesel   = losowy_pesel(rng)
    nip     = losowy_nip(rng)
    iban    = losowy_iban(rng)
    firma   = rng.choice(FIRMY)
    wydzial = rng.choice(WYDZIALY)
    adres2_ul, adres2_kod, _ = losowy_adres(rng)
    dzien   = rng.randint(1,28)
    miesiac = rng.randint(1,12)
    temat, tresc = rng.choice(TEMATY)

    miesiac_nazwa = ["stycznia","lutego","marca","kwietnia","maja","czerwca",
                     "lipca","sierpnia","września","października","listopada","grudnia"][miesiac-1]

    return f"""{miasto}, dnia {dzien} {miesiac_nazwa} 2026 r.

{imie} {nazwisko}
{adres_ul}
{adres_kod}
PESEL: {pesel}
NIP: {nip}

{firma}
{wydzial}
{adres2_ul}
{adres2_kod}

{temat}

{tresc}

Numer rachunku bankowego:
IBAN: {iban}

Z poważaniem,

...................................
(podpis)"""

# ── Renderowanie ──────────────────────────────────────────────────────────────

W, H   = 794, 1123
MARGIN = 60
LINE_H = 24

def render_doc(img, tekst, font_size=14, text_color=(15,15,15), x=MARGIN):
    draw   = ImageDraw.Draw(img)
    f_reg  = F_REG(font_size)
    f_bold = F_BOLD(font_size+1)
    f_mono = F_MONO(font_size-1)
    y = MARGIN
    for line in tekst.split("\n"):
        s = line.strip()
        if s.isupper() and len(s) > 5:
            font = f_bold
        elif s.startswith(("PESEL","NIP","IBAN")):
            font = f_mono
        else:
            font = f_reg
        draw.text((x, y), line, font=font, fill=text_color)
        y += LINE_H
    return img

# ── Degradacja ────────────────────────────────────────────────────────────────

def add_noise(img, sigma, rng):
    px = img.load()
    for py in range(img.height):
        for px2 in range(img.width):
            r,g,b = px[px2,py]
            n = int(sum(rng.uniform(-1,1) for _ in range(4)) * sigma * 2)
            px[px2,py] = (max(0,min(255,r+n)), max(0,min(255,g+n)), max(0,min(255,b+n)))
    return img

def add_shadow(img, strength, side, rng):
    overlay = Image.new("RGB", img.size, (0,0,0))
    draw    = ImageDraw.Draw(overlay)
    w, h    = img.size
    steps   = w//3 if side in ("left","right") else h//3
    for i in range(steps):
        alpha = int(255 * strength * (1 - i/steps))
        if side == "right": draw.line([(w-steps+i,0),(w-steps+i,h)], fill=(alpha,alpha,alpha))
        elif side == "left": draw.line([(i,0),(i,h)], fill=(alpha,alpha,alpha))
        elif side == "bottom": draw.line([(0,h-steps+i),(w,h-steps+i)], fill=(alpha,alpha,alpha))
    return Image.blend(img, overlay, 0.5)

def apply_perspective(img, top_shrink, left_shrink):
    try:
        import numpy as np
        w, h = img.size
        dx_t = int(w * top_shrink / 2)
        dx_l = int(h * left_shrink / 2)
        src = [(0,0),(w,0),(w,h),(0,h)]
        dst = [(dx_t,dx_l),(w-dx_t,dx_l),(w,h-dx_l),(0,h-dx_l)]
        A = []
        for s,t in zip(src,dst):
            A += [[t[0],t[1],1,0,0,0,-s[0]*t[0],-s[0]*t[1]],
                  [0,0,0,t[0],t[1],1,-s[1]*t[0],-s[1]*t[1]]]
        A = np.array(A, dtype=float)
        B = np.array(src).reshape(8).astype(float)
        coeffs = np.linalg.lstsq(A, B, rcond=None)[0]
        return img.transform(img.size, Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    except ImportError:
        return img

# ── Kategorie degradacji ──────────────────────────────────────────────────────

KATEGORIE = {
    "czysty": {
        "opis": "druk czysty",
        "bg": (255,255,255),
        "noise": (0, 1),
        "rotate": (0, 0.5),
        "blur": 0,
        "brightness": (0.99, 1.0),
        "contrast": (0.99, 1.0),
        "perspective_top": 0,
        "perspective_left": 0,
        "shadow": None,
    },
    "lekka": {
        "opis": "lekka degradacja",
        "bg": (253,252,248),
        "noise": (1, 3),
        "rotate": (0.5, 2),
        "blur": 0,
        "brightness": (0.93, 0.97),
        "contrast": (0.94, 0.98),
        "perspective_top": 0.01,
        "perspective_left": 0,
        "shadow": None,
    },
    "telefon_dobre": {
        "opis": "telefon dobre warunki",
        "bg": (251,249,243),
        "noise": (3, 5),
        "rotate": (1, 3),
        "blur": 0,
        "brightness": (0.88, 0.94),
        "contrast": (0.90, 0.96),
        "perspective_top": 0.02,
        "perspective_left": 0.01,
        "shadow": ("right", 0.05, 0.09),
    },
    "telefon_srednie": {
        "opis": "telefon średnie warunki",
        "bg": (249,246,238),
        "noise": (6, 9),
        "rotate": (3, 6),
        "blur": 0.6,
        "brightness": (0.82, 0.90),
        "contrast": (0.84, 0.92),
        "perspective_top": 0.05,
        "perspective_left": 0.02,
        "shadow": ("right", 0.12, 0.18),
    },
    "telefon_zle": {
        "opis": "telefon złe warunki",
        "bg": (244,240,228),
        "noise": (9, 13),
        "rotate": (6, 11),
        "blur": 1.1,
        "brightness": (0.78, 0.88),
        "contrast": (0.78, 0.86),
        "perspective_top": 0.09,
        "perspective_left": 0.03,
        "shadow": ("right", 0.16, 0.22),
    },
    "stary_dokument": {
        "opis": "stary zeskanowany dokument",
        "bg": (245,238,210),
        "noise": (2, 4),
        "rotate": (0, 1),
        "blur": 0.4,
        "brightness": (0.88, 0.94),
        "contrast": (0.82, 0.90),
        "perspective_top": 0,
        "perspective_left": 0,
        "shadow": None,
    },
    "recznie": {
        "opis": "pismo odręczne",
        "bg": (254,252,246),
        "noise": (2, 4),
        "rotate": (0, 1),
        "blur": 0,
        "brightness": (0.93, 0.97),
        "contrast": (0.90, 0.96),
        "perspective_top": 0,
        "perspective_left": 0,
        "shadow": None,
    },
}

def generuj_obraz(kategoria_nazwa, rng, seed, idx):
    kat   = KATEGORIE[kategoria_nazwa]
    tekst = generuj_dokument(rng)
    bg    = kat["bg"]

    if kategoria_nazwa == "recznie":
        img = _render_recznie(tekst, bg, rng)
    elif kategoria_nazwa == "stary_dokument":
        img = Image.new("RGB", (W,H), bg)
        img = render_doc(img, tekst, text_color=(55,48,32))
        img = _dodaj_plamy(img, rng)
    else:
        img = Image.new("RGB", (W,H), bg)
        img = render_doc(img, tekst)

    # Degradacja
    noise_lo, noise_hi = kat["noise"]
    sigma = rng.uniform(noise_lo, noise_hi)
    if sigma > 0.5:
        img = add_noise(img, sigma, rng)

    rot = rng.uniform(*kat["rotate"])
    if abs(rot) > 0.2:
        img = img.rotate(rot, fillcolor=bg, expand=False)

    img = apply_perspective(img, kat["perspective_top"], kat["perspective_left"])

    if kat["shadow"]:
        side, lo, hi = kat["shadow"]
        img = add_shadow(img, rng.uniform(lo, hi), side, rng)

    if kat["blur"] > 0:
        blur = rng.uniform(kat["blur"] * 0.7, kat["blur"] * 1.3)
        img  = img.filter(ImageFilter.GaussianBlur(radius=blur))

    br = rng.uniform(*kat["brightness"])
    ct = rng.uniform(*kat["contrast"])
    img = ImageEnhance.Brightness(img).enhance(br)
    img = ImageEnhance.Contrast(img).enhance(ct)

    fname = f"{idx:02d}_{kategoria_nazwa}_s{seed}.png"
    img.save(OUTPUT_DIR / fname)
    print(f"  {fname}  [{kat['opis']}]")
    return fname

def _render_recznie(tekst, bg, rng):
    img = Image.new("RGB", (W,H), bg)
    f   = F_REG(15)
    y   = MARGIN
    for line in tekst.split("\n"):
        x = MARGIN
        for ch in line:
            ci = Image.new("RGBA", (20,26), (0,0,0,0))
            cd = ImageDraw.Draw(ci)
            r_ = max(0, 12 + rng.randint(-6,6))
            g_ = max(0, 18 + rng.randint(-6,6))
            b_ = max(0, 85 + rng.randint(-18,18))
            cd.text((2,2), ch, font=f, fill=(r_,g_,b_,255))
            ci = ci.rotate(rng.uniform(-3,3), expand=False)
            dy = rng.randint(-2,2)
            img.paste(ci, (x, y+dy), ci)
            bb = f.getbbox(ch)
            x += (bb[2]-bb[0]+1) if bb else 9
            if x > W - MARGIN: break
        y += LINE_H
    return img

def _dodaj_plamy(img, rng):
    draw = ImageDraw.Draw(img)
    for _ in range(rng.randint(10, 25)):
        bx = rng.randint(MARGIN, W-MARGIN)
        by = rng.randint(MARGIN, H-MARGIN)
        r  = rng.randint(1,4)
        draw.ellipse([(bx-r,by-r),(bx+r,by+r)],
                     fill=(rng.randint(20,55),rng.randint(15,45),rng.randint(10,30)))
    # Ziarnisty szum
    px = img.load()
    for py in range(0, img.height, 2):
        for px2 in range(0, img.width, 2):
            if rng.random() < 0.03:
                v = rng.randint(140,200)
                px[px2,py] = (v, v-8, v-22)
    return img

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Rozkład kategorii — tyle samo każdej przy count=7,
    # przy innych wartościach losowo z wagami
    WAGI = {
        "czysty":          1,
        "lekka":           1,
        "telefon_dobre":   2,
        "telefon_srednie": 2,
        "telefon_zle":     1,
        "stary_dokument":  1,
        "recznie":         1,
    }

    if COUNT == 7:
        kolejnosc = ["czysty","lekka","telefon_dobre","telefon_srednie",
                     "telefon_zle","stary_dokument","recznie"]
    else:
        pula = []
        for k,w in WAGI.items():
            pula.extend([k]*w)
        kolejnosc = [RNG.choice(pula) for _ in range(COUNT)]

    print(f"Generuję {COUNT} obrazów w: {OUTPUT_DIR.resolve()}\n")
    for i, kat in enumerate(kolejnosc, 1):
        generuj_obraz(kat, RNG, SEED, i)

    print(f"\nGotowe. Wgraj przez przycisk OCR i przysyłaj logi.")
    print(f"Seed do odtworzenia: {SEED}")
