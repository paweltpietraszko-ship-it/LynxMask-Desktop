# HerBERT legal NER (ONNX) na pełnym tekście dokumentu — tylko pomiar, poza produktem.
# Użycie: py -3 herbert_run.py <plik.pdf|docx|txt>   -> drukuje encje PER/ORG/LOC/ID z offsetami, czas
import json, os, sys, time
from pathlib import Path
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

# Model poza repo: https://huggingface.co/lexedit/herbert-polish-legal-ner (config, tokenizer, onnx/model_quantized.onnx)
M = Path(os.environ.get("HERBERT_DIR", Path.home() / "lynx_models" / "herbert-polish-legal-ner"))
PER_THRESHOLD = 0.2
cfg = json.load(open(M / "config.json", encoding="utf-8"))
id2label = {int(k): v for k, v in cfg["id2label"].items()}
label2id = cfg["label2id"]
tok = Tokenizer.from_file(str(M / "tokenizer.json"))
sess = ort.InferenceSession(str(M / "onnx" / "model_quantized.onnx"), providers=["CPUExecutionProvider"])
in_names = {i.name for i in sess.get_inputs()}


def softmax(x):
    e = np.exp(x - x.max(-1, keepdims=True))
    return e / e.sum(-1, keepdims=True)


def predict_chunk(text):
    enc = tok.encode(text)
    ids = enc.ids[:512]
    offsets = enc.offsets[:512]
    feeds = {"input_ids": np.array([ids], dtype=np.int64), "attention_mask": np.ones((1, len(ids)), dtype=np.int64)}
    if "token_type_ids" in in_names:
        feeds["token_type_ids"] = np.zeros((1, len(ids)), dtype=np.int64)
    probs = softmax(sess.run(None, feeds)[0][0])
    best = probs.argmax(-1)
    per_b, per_i = label2id["B-PER"], label2id["I-PER"]
    spans, cur = [], None
    for i, (s, e) in enumerate(offsets):
        if s == e:
            if cur:
                spans.append(cur); cur = None
            continue
        label = id2label[int(best[i])]
        if label == "O" and probs[i, per_b] + probs[i, per_i] >= PER_THRESHOLD:
            label = "I-PER" if (cur and cur[2] == "PER") else "B-PER"
        if label == "O":
            if cur:
                spans.append(cur); cur = None
            continue
        tag, et = label.split("-", 1)
        if tag == "B" or cur is None or cur[2] != et:
            if cur:
                spans.append(cur)
            cur = [s, e, et]
        else:
            cur[1] = e
    if cur:
        spans.append(cur)
    return spans


def chunks(text, size=900):
    """Kawałki po liniach (~size znaków), z zakładką jednej linii, żeby nazwisko na granicy nie zginęło."""
    lines, pos = [], 0
    for ln in text.splitlines(keepends=True):
        lines.append((pos, ln)); pos += len(ln)
    i = 0
    while i < len(lines):
        start, buf, j = lines[i][0], "", i
        while j < len(lines) and len(buf) + len(lines[j][1]) <= size or j == i:
            buf += lines[j][1]; j += 1
            if j >= len(lines):
                break
        yield start, buf
        if j >= len(lines):
            break
        i = max(j - 1, i + 1)


def predict(text):
    seen, out = set(), []
    for base, chunk in chunks(text):
        for s, e, t in predict_chunk(chunk):
            key = (base + s, base + e, t)
            if key not in seen:
                seen.add(key); out.append(key)
    return sorted(out)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    from document_processor import _extract_text
    p = Path(sys.argv[1])
    text = _extract_text(p.read_bytes(), p.name)[0]
    t0 = time.time()
    ents = predict(text)
    dt = time.time() - t0
    print(f"# znaki {len(text)} czas {dt:.1f}s encje {len(ents)}")
    for s, e, t in ents:
        print(t, s, e, repr(text[s:e]))
