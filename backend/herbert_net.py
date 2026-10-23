"""
herbert_net.py — [LYNX-HERBERT-NET] HerBERT jako ostatnia siatka bezpieczeństwa, tuż przed Output Guardem.

Model `lexedit/herbert-polish-legal-ner` (CC BY 4.0, ONNX kwantyzowany, lokalnie z SHA256) czyta tekst już zamaskowany i zgłasza
osoby (PER → OSOBA) i organizacje (ORG → FIRMA). Zakrywamy wyłącznie spany w całości jawne, po dotychczasowym odsiewie
`ner_layer._filter_institutions` (instytucje publiczne, nagłówki, akronimy…). Siatka niczego nie cofa ani nie zmienia: spany
przecinające istniejący token są pomijane i liczone (PARTIAL_FIRMA_UNFIXED). Tokeny tylko w mapie dokumentu (jak warstwy regex),
numer powyżej najwyższego w dokumencie i profilu — bez zapisu do profilu.
Przełącznik LYNX_HERBERT = off (domyślnie) | PER | ORG | PER,ORG. Off: bez wczytania modelu, wynik bez zmian.
Awaria przy włączonej siatce → wyjątek → pipeline robi S3 fail-closed. Logi tylko kody i liczby (S5).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from types import SimpleNamespace

logger = logging.getLogger("lynxmask.herbert_net")

TYPES = {"PER": "OSOBA", "ORG": "FIRMA"}
MODEL_SHA256 = {
    "onnx/model_quantized.onnx": "5ed91aabec29e07d2d5c7f370a5463283d4d88acbf44dd1ceedd0bca67330b50",
    "tokenizer.json": "2e045c82c9ea8b5bc54162d92d5c72141492df88eff098f3e5436e499d1e29fb",
    "config.json": "10d72599fc1b58425c7dc8e24c4a84cdc69b9defcdd032549d968fa527461991",
}
MIN_SCORE = float(os.environ.get("LYNX_HERBERT_MIN", "0.7"))   # kalibracja na zbiorze znanym 21.10 (0.3–0.9)
WINDOW = 800      # znaków na okno modelu (zakładka OVERLAP); okno > 512 subtokenów jest dzielone, nigdy obcinane
OVERLAP = 200
_TOKEN_RE = re.compile(r"\b[A-Z][A-Z_]+_\d{3}(?!\d)")   # S2
_model = None


def enabled() -> set[str]:
    raw = os.environ.get("LYNX_HERBERT", "off").strip().upper()
    return set() if raw in ("", "OFF") else {t.strip() for t in raw.split(",") if t.strip() in TYPES}


def model_dir() -> Path:
    return Path(os.environ.get("LYNX_HERBERT_MODEL_DIR", Path(__file__).resolve().parent / "models" / "herbert"))


def _load():
    global _model
    if _model is None:
        import json
        import onnxruntime as ort
        from tokenizers import Tokenizer
        import ocr_rapid
        for name, sha in MODEL_SHA256.items():   # brak / niezgodność → wyjątek (nigdy niezweryfikowane wagi)
            if hashlib.sha256((model_dir() / name).read_bytes()).hexdigest() != sha:
                raise ValueError("niezgodny SHA256 modelu HerBERT")
        ocr_rapid.disable_onnx_telemetry()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = ocr_rapid.THREADS
        cfg = json.loads((model_dir() / "config.json").read_text(encoding="utf-8"))
        _model = SimpleNamespace(
            tok=Tokenizer.from_file(str(model_dir() / "tokenizer.json")),
            sess=ort.InferenceSession(str(model_dir() / "onnx/model_quantized.onnx"), opts, providers=["CPUExecutionProvider"]),
            labels={int(k): v for k, v in cfg["id2label"].items()})
    return _model


def _predict(chunk: str) -> list[tuple[int, int, str, float]]:
    """Spany (start, koniec, typ, średnia pewność) w jednym oknie ≤ 512 subtokenów."""
    import numpy as np
    m = _load()
    enc = m.tok.encode(chunk)
    if len(enc.ids) > 512:   # okno za długie dla modelu → dzielimy, zamiast obcinać
        cut = chunk.rfind(" ", 0, len(chunk) // 2) + 1 or len(chunk) // 2
        return _predict(chunk[:cut]) + [(s + cut, e + cut, t, p) for s, e, t, p in _predict(chunk[cut:])]
    names = {i.name for i in m.sess.get_inputs()}
    feeds = {"input_ids": np.array([enc.ids], np.int64), "attention_mask": np.ones((1, len(enc.ids)), np.int64)}
    if "token_type_ids" in names:
        feeds["token_type_ids"] = np.zeros((1, len(enc.ids)), np.int64)
    logits = m.sess.run(None, feeds)[0][0]
    probs = np.exp(logits - logits.max(-1, keepdims=True))
    probs /= probs.sum(-1, keepdims=True)
    spans, cur = [], None
    for i, (s, e) in enumerate(enc.offsets):
        tag, _, kind = m.labels[int(probs[i].argmax())].partition("-")
        if s == e or kind not in TYPES or (tag == "B" or cur is None or cur[2] != kind):
            if cur:
                spans.append(cur)
            cur = [s, e, kind, [float(probs[i].max())]] if (s != e and kind in TYPES) else None
        else:
            cur[1] = e
            cur[3].append(float(probs[i].max()))
    if cur:
        spans.append(cur)
    return [(s, e, k, sum(p) / len(p)) for s, e, k, p in spans]


def detect(text: str) -> list[tuple[int, int, str, float]]:
    """Spany w całym tekście — okna z zakładką, bez duplikatów."""
    found, start = {}, 0
    while start < len(text):
        for s, e, k, p in _predict(text[start:start + WINDOW]):
            found[(start + s, start + e, k)] = max(p, found.get((start + s, start + e, k), 0.0))
        if start + WINDOW >= len(text):
            break
        start = text.rfind(" ", start, start + WINDOW - OVERLAP) + 1 or start + WINDOW - OVERLAP
    return [(s, e, k, p) for (s, e, k), p in sorted(found.items())]


def _next_token(prefix: str, reverse_map: dict, anon_map) -> str:
    known = list(reverse_map) + list(getattr(anon_map, "data", {}).get("entities", {}) if anon_map else [])
    nums = [int(t.rsplit("_", 1)[1]) for t in known if t.startswith(prefix + "_") and t.rsplit("_", 1)[1].isdigit()]
    return f"{prefix}_{max(nums, default=0) + 1:03d}"


def apply_net(text: str, reverse_map: dict, anon_map=None) -> tuple[str, dict]:
    """Dokłada zakrycia na jawnych spanach; off → (text, reverse_map) bez zmian i bez modelu."""
    kinds = enabled()
    if not kinds:
        return text, reverse_map
    from ner_layer import _filter_institutions
    from osoba_not_person import single_osoba_evidence
    tokens = [m.span() for m in _TOKEN_RE.finditer(text)]
    values, partial = {}, 0
    for s, e, kind, score in detect(text):
        value = text[s:e].strip(" ,;:()\"'„”")   # kropki zostają („z o.o.”, „S.A.”)
        if kind not in kinds or score < MIN_SCORE or len(value) < 2:
            continue
        if any(a < e and s < b for a, b in tokens):   # przecina istniejący token — nie zmieniamy starych decyzji
            partial += 1
            continue
        at = text.find(value, s)
        if kind == "PER" and " " not in value and at >= 0 and not single_osoba_evidence(text, at, at + len(value)):
            continue  # [LYNX-OSOBA-PACK4] krok 2: pojedyncze słowo bez dowodu → nie zakrywamy, trafia do Guarda
        if _filter_institutions([SimpleNamespace(text=value, label=TYPES[kind])]):
            values.setdefault(value, TYPES[kind])
    assigned: dict[str, str] = {}
    for value, prefix in sorted(values.items(), key=lambda v: text.find(v[0])):   # numery w kolejności w tekście
        assigned[value] = next((t for t, v in reverse_map.items() if v == value and t.startswith(prefix + "_")), None) \
            or _next_token(prefix, {**reverse_map, **{t: v for v, t in assigned.items()}}, anon_map)
    added = 0
    for value, token in sorted(assigned.items(), key=lambda v: -len(v[0])):   # podmiana: dłuższe najpierw
        text, n = re.subn(r"(?<![\w_])" + re.escape(value) + r"(?![\w])", token, text)
        if n:
            reverse_map[token] = value
            added += 1
    logger.info("[HERBERT] typy=%s dołożone=%d przecinające_token=%d", ",".join(sorted(kinds)), added, partial)
    return text, reverse_map
