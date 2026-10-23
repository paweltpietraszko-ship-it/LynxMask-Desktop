"""Generator `backend/person_surnames_pesel_20260120.json` (LYNX-OSOBA-REDESIGN, brief §4) — odtwarzalny, bez sieci w aplikacji.

Źródło: dane.gov.pl zbiór 1681 „Nazwiska osób żyjących występujące w rejestrze PESEL” (Ministerstwo Cyfryzacji, licencja CC0),
zasoby 1148808 (męskie) i 1148811 (żeńskie), stan danych 2026-01-20; pobranie CSV:
  https://api.dane.gov.pl/resources/1148808,nazwiska-meskie-stan-na-2026-01-20/csv
  https://api.dane.gov.pl/resources/1148811,nazwiska-zenskie-stan-na-2026-01-20/csv
Kolumny `Nazwisko aktualne, Liczba`. Normalizacja: małe litery, suma M+K dla tej samej pisowni, tylko jednowyrazowe, ≥ MIN osób.
Biała lista: 316 słów zatwierdzonych przez OWNERA 23.10 (`tasks/LYNX-OSOBA-REDESIGN/evidence_2026-10-23/biala_lista_pesel_zatwierdzona.csv`).

Użycie: python build_pesel_surnames.py <m.csv> <f.csv> <biala_lista.csv> <wyjście.json>
"""
import csv
import hashlib
import json
import sys

MIN = 100
MONTHS = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad",
          "grudzień"]


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(m_csv: str, f_csv: str, white_csv: str, out: str) -> None:
    counts: dict[str, int] = {}
    for path in (m_csv, f_csv):
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row["Nazwisko aktualne"].strip().lower()
                if name and " " not in name:
                    counts[name] = counts.get(name, 0) + int(row["Liczba"])
    with open(white_csv, encoding="utf-8-sig") as f:
        white = sorted({r["slowo"].strip().lower() for r in csv.DictReader(f, delimiter=";") if r["slowo"].strip()})
    data = {
        "meta": {
            "source": "dane.gov.pl dataset 1681, resources 1148808 (M) + 1148811 (K)",
            "data_date": "2026-01-20",
            "license": "CC0 1.0",
            "min_bearers": MIN,
            "sha256_sources": {"m": sha256(m_csv), "f": sha256(f_csv), "whitelist": sha256(white_csv)},
            "whitelist_note": "316 słów zatwierdzonych przez OWNERA 2026-10-23 (100–999 osób, użycie małą literą w pismach)",
        },
        "surnames": {k: v for k, v in sorted(counts.items()) if v >= MIN},
        "whitelist": white,
        "months": MONTHS,
    }
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"nazwisk >={MIN}: {len(data['surnames'])}, biala lista: {len(white)}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
