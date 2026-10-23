"""Narrow independent PHOTO-CHAIN probe; synthetic images, isolated real API.
Run: python repro_r2.py AUDIT_WORKTREE OUTPUT_DIRECTORY
Does not touch the running backend or real documents.
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

root, out = map(lambda x: Path(x).resolve(), sys.argv[1:3])
out.mkdir(parents=True, exist_ok=True)
models = out / "models"
models.mkdir(exist_ok=True)
sys.path.insert(0, str(root / "backend"))
import ocr_rapid
import photo_chain
for f in ocr_rapid.MODEL_FILES.values():
    shutil.copyfile(Path.home() / "lynx_models" / "ppocrv6_small" / f, models / f)
shutil.copyfile(Path.home() / "lynx_models/doc_ori/a_marsena.onnx", models / photo_chain.ORI_MODEL)
import os
os.environ["LYNX_OCR_MODEL_DIR"] = str(models)
for f, h in {**ocr_rapid.MODEL_SHA256, photo_chain.ORI_MODEL: photo_chain.ORI_SHA256}.items():
    ocr_rapid.verified_model(f, h)
from PIL import Image, ImageDraw, ImageFont
image = Image.new("RGB", (1400, 1100), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
lines = ["UMOWA NAJMU LOKALU", "Umowa zostala zawarta pomiedzy stronami.",
         "Najemca: Grazyna Jankowska", "E-mail: test.audit@example.org",
         "PESEL: 44051401359", "Strony ustalaja warunki korzystania z lokalu.",
         "Dokument dotyczy najmu mieszkania na czas oznaczony.",
         "W sprawach pozostalych stosuje sie przepisy prawa."]
for i, line in enumerate(lines):
    draw.text((80, 100 + i * 95), line, font=font, fill="black")
jobs, orientation = [], []
for angle in (0, 90, 180, 270):
    p = out / f"synthetic_{angle}.png"
    image.rotate(-angle, expand=True).save(p)
    pred, confidence = photo_chain.classify(photo_chain.decode(p.read_bytes()))
    orientation.append({"rotation": angle, "correct": pred == angle, "confidence": round(confidence, 3)})
    jobs.append(str(p))
blank = out / "blank.png"
Image.new("RGB", (1000, 1000), "white").save(blank)
jobs.append(str(blank))
spec = importlib.util.spec_from_file_location("photo_measure", root / "tasks/LYNX-PHOTO-CHAIN/measure/photo_measure.py")
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)
a = SimpleNamespace(sha="df612f7c6257a25e6de122c478a05d1c41e50353", rapid=True, models=models,
                    env=["LYNX_PHOTO_DICT_MIN=0.60"], protect=[Path("C:/Users/p_pie/Desktop/LynxMask-Desktop/backend")])
items, meta = measure.run_variant(a, measure._cc(), jobs)
checks = []
for i, r in enumerate(items or []):
    if i < 4:
        checks.append({"rotation": i * 90, "code": r["code"], "engine": r["ocr_engine"],
                       "quality": r["ocr_quality"], "blocked": r["blocked"],
                       "email_hidden": "test.audit@example.org" not in r["out"],
                       "pesel_hidden": "44051401359" not in r["out"],
                       "has_tokens": bool(r["originals"]), "secs": round(r["secs"], 2)})
    else:
        checks.append({"blank": True, "code": r["code"], "rejected": r["ocr_rejected"],
                       "empty_output": not r["out"], "no_tokens": not r["originals"],
                       "alternative": r["error_has_alternative"]})
result = {"sha": a.sha, "hashes_verified": True, "orientation": orientation, "run": meta, "checks": checks}
(out / "checks.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
