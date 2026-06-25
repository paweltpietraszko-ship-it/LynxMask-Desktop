"""
pipeline_core.py  v0.2
Centralna alokacja tokenów — TokenAllocator, PipelineState, ConflictResolver.
Warstwy przetwarzania: layers/identity.py, layers/...
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


def _canonical(value: str) -> str:
    return re.sub(r"[\s\-\.]", "", value).lower()


class TokenAllocator:
    """
    Jeden obiekt alokacji tokenów na cały pipeline.

    Gwarantuje:
    - unikalność token_id w przestrzeni (token_type, numer)
    - deduplikację po canonical value w obrębie token_type
    - ochronę spanów (brak kolizji pozycyjnych)
    - bezpieczne pre-rejestrowanie tokenów z NER/trie bez inkrementacji licznika
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._canonical_to_token: dict[tuple[str, str], str] = {}
        self._spans: list[tuple[int, int, str]] = []
        self._reverse: dict[str, str] = {}

    def allocate(
        self, token_type: str, value: str, start: int, end: int
    ) -> str | None:
        """
        Tworzy nowy token dla (value, start, end).
        Zwraca None jeśli span zajęty.
        Zwraca istniejący token_id jeśli canonical value już widziana (dedup).
        """
        if self.is_occupied(start, end, overlap="partial"):
            return None

        canon = _canonical(value)
        key = (canon, token_type)

        if key in self._canonical_to_token:
            existing = self._canonical_to_token[key]
            self._spans.append((start, end, existing))
            return existing

        self._counters[token_type] = self._counters.get(token_type, 0) + 1
        tid = f"{token_type}_{self._counters[token_type]:03d}"

        self._reverse[tid] = value
        self._canonical_to_token[key] = tid
        self._spans.append((start, end, tid))
        return tid

    def register(
        self, token_id: str, value: str, start: int, end: int
    ) -> None:
        """
        Rejestruje istniejący token (z trie lub NER adaptera).
        Podnosi podłogę licznika — przyszłe allocate() nie kolidują numerycznie.
        """
        parts = token_id.rsplit("_", 1)
        if len(parts) == 2:
            token_type, num_str = parts
            try:
                num = int(num_str)
                current = self._counters.get(token_type, 0)
                self._counters[token_type] = max(current, num)
            except ValueError:
                token_type = parts[0]

            canon = _canonical(value)
            key = (canon, token_type)
            self._canonical_to_token.setdefault(key, token_id)

        self._reverse.setdefault(token_id, value)
        self._spans.append((start, end, token_id))

    def is_occupied(
        self, start: int, end: int, overlap: str = "partial"
    ) -> bool:
        """
        overlap="partial" — True przy jakimkolwiek nakładaniu spanów.
        overlap="full"    — True tylko gdy identyczny span (start==s, end==e).
        """
        for s, e, _ in self._spans:
            if overlap == "partial":
                if s < end and e > start:
                    return True
            else:
                if s == start and e == end:
                    return True
        return False

    def reset_spans(self) -> None:
        """Czyści zarejestrowane spany między warstwami.
        Liczniki i deduplication (canonical_to_token, reverse) pozostają.
        Potrzebne bo każda warstwa modyfikuje tekst — stare spany mają błędne
        współrzędne w nowym tekście i mogą blokować dopasowania kolejnej warstwy."""
        self._spans.clear()

    @property
    def reverse_map(self) -> dict[str, str]:
        return dict(self._reverse)


# ─────────────────────────────────────────────────────────────────────────────
# PipelineState
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineState:
    text: str
    allocator: TokenAllocator
    ner_results: dict = field(default_factory=dict)
    ner_variants: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# ConflictResolver
# ─────────────────────────────────────────────────────────────────────────────

ENTITY_PRIORITY: dict[str, int] = {
    "EMAIL": 100, "PESEL": 95, "IBAN": 95,
    "NIP": 90, "REGON": 85, "DOWOD": 85, "PASZPORT": 85,
    "TELEFON": 80, "ADRES": 75, "SYGNATURA": 75,
    "OSOBA": 70, "FIRMA": 70, "INSTYTUCJA": 70,
    "NUMER": 50,
}


class ConflictResolver:
    """
    Polityka rozwiązywania konfliktów spanów.

    resolve(existing_type, new_type, overlap_mode) → bool
      True  — nowa encja wygrywa (zastępuje istniejącą)
      False — istniejąca encja wygrywa (nowa odrzucona)

    overlap_mode:
      "identical" — identyczny span: wyższy priorytet wygrywa
      "full"      — nowa encja w całości wewnątrz istniejącej: zewnętrzna wygrywa
      "partial"   — częściowe nakładanie: ta która zaczęła się pierwsza wygrywa
    """

    def __init__(self, priority: dict[str, int] = ENTITY_PRIORITY) -> None:
        self._priority = priority

    def _p(self, entity_type: str) -> int:
        return self._priority.get(entity_type, 0)

    def resolve(
        self, existing_type: str, new_type: str, overlap_mode: str
    ) -> bool:
        if overlap_mode == "identical":
            return self._p(new_type) > self._p(existing_type)
        elif overlap_mode == "full":
            return False
        elif overlap_mode == "partial":
            return False
        else:
            raise ValueError(f"Nieznany overlap_mode: {overlap_mode!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Testy
# ─────────────────────────────────────────────────────────────────────────────

def test_token_uniqueness() -> bool:
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))
            failed += 1

    print("=== test_token_uniqueness ===\n")

    print("A. Telefon vs Dowód:")
    a = TokenAllocator()
    t_dowod = a.allocate("NUMER", "ABC123456", 0, 9)
    t_tel   = a.allocate("NUMER", "512345678", 20, 29)
    check("A1 — dowód zamaskowany", t_dowod is not None)
    check("A2 — telefon zamaskowany", t_tel is not None)
    check("A3 — różne tokeny", t_dowod != t_tel, f"oba = {t_dowod}")
    check("A4 — reverse_map spójny",
          a.reverse_map.get(t_dowod) == "ABC123456"
          and a.reverse_map.get(t_tel) == "512345678")

    print("\nB. Sygnatura vs KW:")
    b = TokenAllocator()
    t_syg = b.allocate("NUMER", "I Ns 6221/2016", 0, 14)
    t_kw  = b.allocate("NUMER", "KA1K/00075119/1", 20, 35)
    check("B1 — sygnatura zamaskowana", t_syg is not None)
    check("B2 — KW zamaskowana", t_kw is not None)
    check("B3 — różne tokeny", t_syg != t_kw, f"t_syg={t_syg} t_kw={t_kw}")

    print("\nC. Podobne nazwiska (register):")
    c = TokenAllocator()
    c.register("OSOBA_001", "Jan Kowalski",  0, 12)
    c.register("OSOBA_002", "Jan Kowalczyk", 20, 33)
    rm = c.reverse_map
    check("C1 — Kowalski w mapie",  rm.get("OSOBA_001") == "Jan Kowalski")
    check("C2 — Kowalczyk w mapie", rm.get("OSOBA_002") == "Jan Kowalczyk")
    check("C3 — różne token_id",    "OSOBA_001" != "OSOBA_002")

    print("\nD. register nie koliduje z allocate:")
    d = TokenAllocator()
    d.register("NUMER_001", "ABC123456",   0, 9)
    d.register("NUMER_002", "Km 123/2024", 15, 26)
    t_new = d.allocate("NUMER", "512345678", 30, 39)
    check("D1 — nowy token != NUMER_001", t_new != "NUMER_001", f"t_new = {t_new}")
    check("D2 — nowy token != NUMER_002", t_new != "NUMER_002", f"t_new = {t_new}")
    check("D3 — nowy token = NUMER_003",  t_new == "NUMER_003", f"t_new = {t_new}")

    print("\nE. Deduplication (ten sam NIP, różny format):")
    e = TokenAllocator()
    t1 = e.allocate("NUMER", "855-019-31-23", 0, 13)
    t2 = e.allocate("NUMER", "855 019 31 23", 20, 33)
    check("E1 — oba zamaskowane", t1 is not None and t2 is not None)
    check("E2 — ten sam token",   t1 == t2, f"t1={t1} t2={t2}")
    check("E3 — jeden wpis w reverse_map", len(e.reverse_map) == 1,
          f"len={len(e.reverse_map)}")
    check("E4 — oba spany zajęte",
          e.is_occupied(0, 13) and e.is_occupied(20, 33))

    print("\nF. Span occupancy:")
    f = TokenAllocator()
    f.allocate("NUMER", "12345678", 10, 18)
    check("F1 — partial overlap → None",
          f.allocate("NUMER", "99999999", 15, 23) is None)
    check("F2 — full overlap → None",
          f.allocate("NUMER", "99999999", 10, 18) is None)
    check("F3 — brak overlap → OK",
          f.allocate("NUMER", "99999999", 20, 28) is not None)
    check("F4 — is_occupied partial",  f.is_occupied(15, 23, "partial") is True)
    check("F5 — is_occupied full match", f.is_occupied(10, 18, "full") is True)
    check("F6 — is_occupied full mismatch", f.is_occupied(10, 17, "full") is False)

    print("\nG. Ortogonalność typów:")
    g = TokenAllocator()
    g.register("NUMER_003", "ABC123456", 0, 9)
    t_adres = g.allocate("ADRES", "ul. Kwiatowa 1", 20, 34)
    t_numer = g.allocate("NUMER", "512345678", 40, 49)
    check("G1 — ADRES startuje od 001", t_adres == "ADRES_001",
          f"t_adres = {t_adres}")
    check("G2 — NUMER startuje za 003", t_numer == "NUMER_004",
          f"t_numer = {t_numer}")

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


def test_conflict_resolver() -> bool:
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))
            failed += 1

    print("=== test_conflict_resolver ===\n")
    cr = ConflictResolver()

    print("1. EMAIL vs OSOBA (identical span):")
    result = cr.resolve("OSOBA", "EMAIL", "identical")
    check("EMAIL (100) > OSOBA (70) — EMAIL wygrywa", result is True,
          f"resolve={result}")
    check("OSOBA nie zastępuje EMAIL",
          cr.resolve("EMAIL", "OSOBA", "identical") is False)

    print("\n2. NUMER vs PESEL (identical span):")
    result = cr.resolve("NUMER", "PESEL", "identical")
    check("PESEL (95) > NUMER (50) — PESEL wygrywa", result is True,
          f"resolve={result}")
    check("NUMER nie zastępuje PESEL",
          cr.resolve("PESEL", "NUMER", "identical") is False)

    print("\n3. Full overlap (nowa wewnątrz istniejącej):")
    check("NUMER inside ADRES — ADRES wygrywa",
          cr.resolve("ADRES", "NUMER", "full") is False)
    check("PESEL inside ADRES — ADRES wygrywa (outer wins)",
          cr.resolve("ADRES", "PESEL", "full") is False)

    print("\n4. Partial overlap (pierwsza zarejestrowana wygrywa):")
    check("OSOBA/FIRMA partial — OSOBA wygrywa",
          cr.resolve("OSOBA", "FIRMA", "partial") is False)
    check("NUMER/EMAIL partial — NUMER wygrywa (pierwsza)",
          cr.resolve("NUMER", "EMAIL", "partial") is False)

    print("\n5. Remis priorytetow (PESEL == IBAN == 95):")
    check("PESEL vs IBAN identical — remis, istniejaca wygrywa",
          cr.resolve("PESEL", "IBAN", "identical") is False)

    print("\n6. Nieznany overlap_mode:")
    try:
        cr.resolve("NUMER", "PESEL", "unknown")
        check("ValueError nie zostal rzucony", False)
    except ValueError:
        check("ValueError rzucony poprawnie", True)

    print(f"\n{'=' * 42}")
    print(f"Wynik: {passed} PASS  {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    import sys
    print()
    ok1 = test_token_uniqueness()
    print()
    ok2 = test_conflict_resolver()
    sys.exit(0 if ok1 and ok2 else 1)
