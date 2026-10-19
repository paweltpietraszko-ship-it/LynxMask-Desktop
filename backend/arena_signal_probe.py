"""
arena_signal_probe.py — LYNX-ARENA-SIGNALS-PILOT: rzeczywiste spany 4 detektorów → te same kandydatury do R1 i R2.

Eksperyment offline (czysty tekst, BEZ OCR), NIE ścieżka produktu: pipeline/API go nie importują.
Źródła (każde osobno, na ORYGINALNYM tekście, świeży stan):
  identity / contact / address — apply_*_layer z lokalnym podsłuchem TokenAllocator.allocate (start, end, kind);
  SPACY_DIRECT — spacy_ner.detect_entities(original) bez ner_adapter (bez propagacji i poprawek OCR).
Pochodzenie offsetu jest dowodzone, nie zgadywane: zapis allocate odtworzony na oryginale musi dać dokładnie
tekst wyjściowy warstwy; SpaCy: oryginał[start:end] == zwrócony tekst. Inaczej status źródła MAPPING_ERROR,
a powtórzenie wartości pominięte przez deduplikację wrappera → ADAPTER_UNSUPPORTED. Takie źródło nie daje
NO_CANDIDATE, jego typy gold wypadają z mianownika, a Areny dla próby nie są uruchamiane (NOT_RUN).
Gold przychodzi z zewnątrz (test/CLI), nigdy nie trafia do Areny. Raport: tylko liczniki i id syntetyków.
CLI: py -3 arena_signal_probe.py < próby.jsonl   ({"id", "text", "gold": [{"start","end","kind","parent"?}]})
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import arena_sim  # noqa: E402
import arena_v02  # noqa: E402
from pipeline_core import PipelineState, TokenAllocator  # noqa: E402

KINDS = arena_sim.KINDS
EVIDENCE = ["OBSERVED_DETECTOR"]  # tylko pochodzenie, nie potwierdzenie semantyki
SPACY = "SPACY_DIRECT"
SOURCE_KINDS = {"identity": {"NUMER"}, "contact": {"EMAIL", "NUMER"}, "address": {"ADRES"},
                SPACY: {"OSOBA", "FIRMA"}}
VARIANTS = ("strict", "structured")


class _Recorder(TokenAllocator):
    """Lokalny podsłuch: zapisuje udane przydziały [start, end) w kolejności wywołań."""

    def __init__(self) -> None:
        super().__init__()
        self.hits: list[tuple[int, int, str, str, str]] = []

    def allocate(self, token_type: str, value: str, start: int, end: int) -> str | None:
        tid = super().allocate(token_type, value, start, end)
        if tid is not None:
            self.hits.append((start, end, token_type, value, tid))
        return tid


def _layers() -> dict:
    from layers.address import apply_address_layer
    from layers.contact import apply_contact_layer
    from layers.identity import apply_identity_layer
    return {"identity": apply_identity_layer, "contact": apply_contact_layer, "address": apply_address_layer}


def _bounds_ok(text: str, start: object, end: object, kind: object) -> bool:
    return type(start) is int and type(end) is int and 0 <= start < end <= len(text) and kind in KINDS


def _candidate(start: int, end: int, kind: str, source: str) -> dict:
    return {"start": start, "end": end, "kind": kind, "source": source, "evidence": list(EVIDENCE)}


def _source(status: str, cands: list | None = None, ms: float = 0.0, canonical: int = 0) -> dict:
    return {"status": status, "candidates": cands or [], "ms": ms, "canonical_differs": canonical}


def _check_layer(text: str, hits: list, out: str, name: str) -> dict:
    """Odtwarza podmiany z zapisu allocate na oryginale; każda inna zmiana tekstu = MAPPING_ERROR."""
    if any(not _bounds_ok(text, s, e, k) for s, e, k, _, _ in hits):
        return _source("MAPPING_ERROR")
    ordered = sorted(hits, key=lambda h: h[0])
    if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        return _source("MAPPING_ERROR")
    replay = text
    for s, e, _, _, tid in reversed(ordered):
        replay = replay[:s] + tid + replay[e:]
    if replay != out:
        return _source("MAPPING_ERROR")
    cands = [_candidate(s, e, k, name) for s, e, k, _, _ in ordered]
    return _source("OK", cands, canonical=sum(1 for s, e, _, v, _ in ordered if text[s:e] != v))


def layer_source(name: str, apply_fn, text: str) -> dict:
    t0 = time.perf_counter()
    recorder = _Recorder()
    state = PipelineState(text=text, allocator=recorder)
    try:
        apply_fn(state)
    except Exception:  # noqa: BLE001 — bez treści wyjątku (może zawierać tekst wejścia)
        return _source("DETECTOR_ERROR", ms=(time.perf_counter() - t0) * 1000)
    result = _check_layer(text, recorder.hits, state.text, name)
    result["ms"] = (time.perf_counter() - t0) * 1000
    return result


def _whole_word_at(text: str, start: int, end: int) -> bool:
    return not arena_sim._inside_word(text, start) and not arena_sim._inside_word(text, end)


def _dedup_skipped(text: str, results: list) -> bool:
    """Wrapper zwraca jedną encję na wartość: inne wystąpienie całym wyrazem poza spanami → nieobsługiwane."""
    low, spans = text.lower(), [(r.start, r.end) for r in results]
    for r in results:
        value, pos = r.text.lower(), low.find(r.text.lower())
        while pos >= 0:
            end = pos + len(value)
            if _whole_word_at(text, pos, end) and not any(s < end and pos < e for s, e in spans):
                return True
            pos = low.find(value, pos + 1)
    return False


def spacy_source(text: str) -> dict:
    t0 = time.perf_counter()
    try:
        import spacy_ner
        spacy_ner._get_nlp()
    except Exception:  # noqa: BLE001
        return _source("MODEL_UNAVAILABLE")
    try:
        results = spacy_ner.detect_entities(text)
    except Exception:  # noqa: BLE001
        return _source("DETECTOR_ERROR", ms=(time.perf_counter() - t0) * 1000)
    ms = (time.perf_counter() - t0) * 1000
    for r in results:  # skrócony text wielowierszowej OSOBA z pozostawionym end → MAPPING_ERROR, nie FN
        if not _bounds_ok(text, r.start, r.end, r.label) or text[r.start:r.end] != r.text:
            return _source("MAPPING_ERROR", ms=ms)
    if _dedup_skipped(text, results):
        return _source("ADAPTER_UNSUPPORTED", ms=ms)
    cands = [_candidate(r.start, r.end, r.label, SPACY) for r in results]
    return _source("OK", cands, ms=ms)


def collect(text: str, layers: dict | None = None, spacy_fn=None) -> dict:
    """Źródła w stałej kolejności; candidates — deterministyczna lista tylko z źródeł OK."""
    sources = {name: layer_source(name, fn, text) for name, fn in (layers or _layers()).items()}
    sources[SPACY] = (spacy_fn or spacy_source)(text)
    cands = [c for s in sources.values() if s["status"] == "OK" for c in s["candidates"]]
    cands.sort(key=lambda c: (c["start"], c["end"], c["kind"], c["source"]))
    return {"sources": sources, "candidates": cands}


def _overlap(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def count_conflicts(cands: list) -> int:
    """Pary nakładających się kandydatów o różnych (start, end, kind)."""
    keys = sorted({(c["start"], c["end"], c["kind"]) for c in cands})
    spans = [{"start": s, "end": e} for s, e, _ in keys]
    return sum(1 for i, a in enumerate(spans) for b in spans[i + 1:] if _overlap(a, b))


def _detection_status(g: dict, cands: list) -> str:
    if any((c["start"], c["end"], c["kind"]) == (g["start"], g["end"], g["kind"]) for c in cands):
        return "EXACT_CANDIDATE"
    if any((c["start"], c["end"]) == (g["start"], g["end"]) for c in cands):
        return "WRONG_KIND"
    return "BAD_SPAN" if any(_overlap(c, g) for c in cands) else "NO_CANDIDATE"


def classify_gold(gold: list, cands: list, blocked: dict) -> list[str]:
    """Status detekcji per gold. Zagnieżdżone (parent) przy dokładnym rodzicu = COVERED_BY_PARENT, nie FN/FP."""
    base = [_detection_status(g, cands) for g in gold]
    out = []
    for g, status in zip(gold, base):
        parent = g.get("parent")
        if g["kind"] in blocked:
            out.append("SOURCE_" + blocked[g["kind"]])
        elif status != "EXACT_CANDIDATE" and parent is not None and base[parent] == "EXACT_CANDIDATE":
            out.append("COVERED_BY_PARENT")
        else:
            out.append(status)
    return out


def _blocked_kinds(sources: dict) -> dict:
    blocked: dict[str, str] = {}
    for name, src in sources.items():
        if src["status"] != "OK":
            for kind in sorted(SOURCE_KINDS[name]):
                blocked.setdefault(kind, src["status"])
    return blocked


def invariant_failures(text: str, tokens: list, masked: str) -> list[str]:
    """N1 poza spanami 1:1, N2 granice wyrazu, N3 roundtrip mapą, N4 original == oryginał[start:end]."""
    failed, rebuilt, restored, pos = set(), "", "", 0
    for t in sorted(tokens, key=lambda t: t["start"]):
        if t["original"] != text[t["start"]:t["end"]]:
            failed.add("N4")
        if not _whole_word_at(text, t["start"], t["end"]):
            failed.add("N2")
        rebuilt += text[pos:t["start"]] + t["token"]
        restored += text[pos:t["start"]] + t["original"]
        pos = t["end"]
    if rebuilt + text[pos:] != masked:
        failed.add("N1")
    if restored + text[pos:] != text:
        failed.add("N3")
    return sorted(failed)


def _render_counts(text: str, gold: list, tokens: list) -> dict:
    """fn: żaden znak gold nie zakryty; fn_partial: część niepustych znaków widoczna; split: zakryty kilkoma tokenami."""
    hidden = {i for t in tokens for i in range(t["start"], t["end"])}
    fn = partial = split = 0
    for g in gold:
        chars = [i for i in range(g["start"], g["end"]) if not text[i].isspace()]
        visible = [i for i in chars if i not in hidden]
        if visible and len(visible) == len(chars):
            fn += 1
        elif visible:
            partial += 1
        elif not any(t["start"] <= g["start"] and g["end"] <= t["end"] for t in tokens):
            split += 1
    fp = overmask = 0
    for t in tokens:
        hits = [g for g in gold if _overlap(t, g)]
        if not hits:
            fp += 1
        elif not any(g["start"] <= t["start"] and t["end"] <= g["end"] for g in hits):
            overmask += 1
    return {"fn": fn, "fn_partial": partial, "split": split, "fp": fp, "overmask": overmask}


def judge_variant(text: str, gold: list, statuses: list, result: dict) -> dict:
    exact = [g for g, s in zip(gold, statuses) if s == "EXACT_CANDIDATE"]
    if result["status"] != "RENDERED":
        return {"status": "STOP", "reason": result["reason_code"], "arbiter_stop": len(exact)}
    kept = {(t["start"], t["end"], t["kind"]) for t in result["tokens"]}
    counted = [g for g, s in zip(gold, statuses) if not s.startswith("SOURCE_")]
    report = {"status": "RENDERED", "reason": None,
              "arbiter_discarded": sum(1 for g in exact if (g["start"], g["end"], g["kind"]) not in kept),
              "invariants": invariant_failures(text, result["tokens"], result["masked"])}
    report.update(_render_counts(text, counted, result["tokens"]))
    report["guard_flags"] = len(result["guard_flags"])
    return report


def run_variants(text: str, cands: list) -> tuple[dict, dict, bool]:
    """Ta sama, niezmienna lista do R1=strict i R2=structured (kopia JSON, by Arena nie mogła jej zmienić)."""
    frozen = json.dumps(cands, sort_keys=True)
    results, ms = {}, {}
    for variant in VARIANTS:
        payload = {"text": text, "base_candidates": json.loads(frozen), "mode": "full", "policy": variant}
        t0 = time.perf_counter()
        results[variant] = arena_v02.run_case(payload)
        ms[variant] = (time.perf_counter() - t0) * 1000
    return results, ms, json.dumps(cands, sort_keys=True) == frozen


def validate_sample(sample: object) -> None:
    if not isinstance(sample, dict) or not isinstance(sample.get("text"), str) or not isinstance(sample.get("gold"), list):
        raise ValueError("INVALID_SAMPLE")
    for g in sample["gold"]:
        parent = g.get("parent") if isinstance(g, dict) else None
        if not isinstance(g, dict) or not _bounds_ok(sample["text"], g.get("start"), g.get("end"), g.get("kind")) \
                or (parent is not None and (type(parent) is not int or not 0 <= parent < len(sample["gold"]))):
            raise ValueError("INVALID_GOLD")


def probe(sample: dict, layers: dict | None = None, spacy_fn=None) -> dict:
    validate_sample(sample)
    text, gold = sample["text"], sample["gold"]
    got = collect(text, layers, spacy_fn)
    blocked = _blocked_kinds(got["sources"])
    statuses = classify_gold(gold, got["candidates"], blocked)
    report = {"id": str(sample.get("id", "")), "gold": statuses, "conflicts": count_conflicts(got["candidates"]),
              "sources": {n: {k: v for k, v in s.items() if k != "candidates"} | {"n": len(s["candidates"])}
                          for n, s in got["sources"].items()},
              "candidates": got["candidates"], "variants": {}, "variant_ms": {}}
    if blocked:
        report["variants"] = {v: {"status": "NOT_RUN", "reason": "SOURCE_NOT_OK"} for v in VARIANTS}
        return report
    results, report["variant_ms"], report["same_input"] = run_variants(text, got["candidates"])
    report["variants"] = {v: judge_variant(text, gold, statuses, results[v]) for v in VARIANTS}
    return report


def _variant_totals(reports: list, variant: str) -> dict:
    tot: Counter = Counter()
    for r in reports:
        v = r["variants"][variant]
        tot["status:" + v["status"]] += 1
        if v.get("reason"):
            tot["reason:" + v["reason"]] += 1
        for key in ("arbiter_stop", "arbiter_discarded", "fn", "fn_partial", "split", "fp", "overmask",
                    "guard_flags"):
            tot[key] += v.get(key, 0)
        tot["invariant_failures"] += len(v.get("invariants", []))
        tot["ms"] += r["variant_ms"].get(variant, 0.0)
    return dict(sorted(tot.items()))


def aggregate(reports: list) -> dict:
    """Wyłącznie liczniki i id — bez tekstu, wartości i offsetów."""
    gold, by_kind, src, src_ms = Counter(), Counter(), Counter(), Counter()
    for r in reports:
        gold.update(r["gold"])
        for name, s in r["sources"].items():
            src[f"{name}:{s['status']}"] += 1
            src_ms[name] += s["ms"]
            src[f"{name}:canonical_differs"] += s["canonical_differs"]
        by_kind.update(f"{k}:{s}" for k, s in zip(r.get("gold_kinds", []), r["gold"]))
    return {"samples": len(reports), "ids": [r["id"] for r in reports],
            "gold": dict(sorted(gold.items())), "gold_by_kind": dict(sorted(by_kind.items())),
            "sources": dict(sorted(src.items())), "source_ms": {k: round(v, 1) for k, v in sorted(src_ms.items())},
            "conflicts": sum(r["conflicts"] for r in reports),
            "per_sample": {r["id"]: {"gold": r["gold"], "variants": {v: [x["status"], x.get("reason")]
                                                                     for v, x in r["variants"].items()}}
                           for r in reports},
            "variants": {v: _variant_totals(reports, v) for v in VARIANTS}}


def run_samples(samples: list, **kw) -> dict:
    reports = []
    for sample in samples:
        report = probe(sample, **kw)
        report["gold_kinds"] = [g["kind"] for g in sample["gold"]]
        reports.append(report)
    return aggregate(reports)


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        samples = [json.loads(line) for line in sys.stdin if line.strip()]
        out = run_samples(samples)
    except (ValueError, TypeError, KeyError):
        out = {"error": "INVALID_INPUT"}
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0 if "error" not in out else 2


if __name__ == "__main__":
    raise SystemExit(main())
