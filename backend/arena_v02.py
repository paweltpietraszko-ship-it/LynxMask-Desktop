"""
Arena v0.2: eksperyment R1 vs R2 na IDENTYCZNYCH kandydatach.
R1 = niezmienione arena_sim.run_case (audytowana v0.1.2).
R2 = ograniczona reguła zawierania: FIRMA>OSOBA, ADRES>OSOBA, EMAIL>OSOBA,
tylko gdy SZERSZY oryginalny fragment ma widoczny dowod strukturalny.
Nie jest silnikiem produkcyjnym ani ocena bezpieczenstwa. Bez API, LLM i gold.
CLI: python arena_v02.py; JSONL stdin/stdout, policy = strict|structured|both.
"""
from __future__ import annotations

import json
import re
import sys

import arena_sim as old

LEGAL = re.compile(r"(?:sp\.\s*z\s*o\.o\.?|s\.a\.?|sp\.\s*j\.?)$", re.I)
STREET = re.compile(r"^ul\.[ \t]+", re.I)
BUILDING = re.compile(r"^\d[\w/-]*$", re.U)


def proof(text: str, big: dict, small: dict) -> bool:
    """Weryfikuje strukture oryginalnego wycinka, nie ufa self-reported evidence."""
    if small["kind"] != "OSOBA":
        return False
    value = text[big["start"]:big["end"]]
    if big["kind"] == "FIRMA":
        return bool(LEGAL.search(value.strip()))
    if big["kind"] == "ADRES":
        words = value.split()
        return bool(STREET.match(value) and len(words) >= 3 and BUILDING.fullmatch(words[-1]))
    if big["kind"] == "EMAIL":
        parts = value.split("@")
        return len(parts) == 2 and bool(parts[0]) and bool(
            re.fullmatch(r"[^\s@]+[.,][^\s@.,]{2,}", parts[1])
        )
    return False


def decide(text: str, candidates: list[dict], trace: list) -> list[dict]:
    """R2: nigdy nie dopuszczaj przecinajacych sie wynikowych spanow."""
    merged: dict[tuple, dict] = {}
    for candidate in sorted(candidates, key=lambda x: (x["start"], x["end"], x["kind"])):
        key = (candidate["start"], candidate["end"], candidate["kind"])
        if key not in merged:
            merged[key] = dict(candidate, evidence=set(candidate["evidence"]))
        else:
            merged[key]["evidence"].update(candidate["evidence"])
            merged[key]["origin"] = "base+anchor"
    items = list(merged.values())
    dropped = set()
    for index, left in enumerate(items):
        for right in items[index + 1:]:
            if not (left["start"] < right["end"] and right["start"] < left["end"]):
                continue
            if left["kind"] == right["kind"]:
                loser = old._contained_loser(left, right)
            else:
                if left["start"] <= right["start"] and right["end"] <= left["end"]:
                    big, small = left, right
                elif right["start"] <= left["start"] and left["end"] <= right["end"]:
                    big, small = right, left
                else:
                    raise old.Stop("AMBIGUOUS")
                if not proof(text, big, small):
                    raise old.Stop("AMBIGUOUS")
                loser = id(small)
            dropped.add(loser)
    kept = [c for c in items if id(c) not in dropped]
    for c in kept:
        if old._inside_word(text, c["start"]) or old._inside_word(text, c["end"]):
            raise old.Stop("WORD_BOUNDARY")
    for c in items:
        trace.append({"phase": "arbiter", "kind": c["kind"], "start": c["start"],
                      "end": c["end"], "decision": "dropped" if id(c) in dropped else "kept"})
    return kept


def structured(case: object) -> dict:
    trace = []
    try:
        if not isinstance(case, dict) or not isinstance(case.get("text"), str) or case.get("mode", "full") != "full":
            raise old.Stop("INVALID_INPUT")
        text = case["text"]
        if old.TOKEN_RE.search(text):
            raise old.Stop("TOKEN_INJECTION")
        base = old._base(text, case.get("base_candidates", []), trace)
        spans = decide(text, base + old._anchors(text, base, trace), trace)
        masked, tokens = old._apply(text, spans)
        trace.sort(key=lambda x: (x["start"], x["end"], x["phase"], x["kind"] or ""))
        return {"status": "RENDERED", "masked": masked, "tokens": tokens,
                "trace": trace, "reason_code": None, "guard_flags": old._guard(masked)}
    except old.Stop as exc:
        code = exc.code
    except Exception:
        code = "INTERNAL_ERROR"
    return {"status": "STOP", "masked": None, "tokens": [], "trace": [],
            "reason_code": code, "guard_flags": []}


def run_case(case: object) -> dict:
    if not isinstance(case, dict) or case.get("policy", "both") not in ("both", "strict", "structured"):
        return structured(None)
    policy = case.get("policy", "both")
    payload = {k: v for k, v in case.items() if k != "policy"}
    if policy == "strict":
        return old.run_case(payload)
    if policy == "structured":
        return structured(payload)
    strict = old.run_case(payload)
    flexible = structured(payload)
    comparable = ("status", "masked", "tokens", "reason_code", "guard_flags")
    return {"version": "0.2", "strict": strict, "structured": flexible,
            "changed": any(strict[key] != flexible[key] for key in comparable)}


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except ValueError:
            case = None
        sys.stdout.write(json.dumps(run_case(case), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
