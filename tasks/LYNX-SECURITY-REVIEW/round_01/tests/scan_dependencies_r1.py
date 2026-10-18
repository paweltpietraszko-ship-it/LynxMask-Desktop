"""Inventory/advisory scanner, no installs or fixes. --online sends ONLY names/versions to OSV.
Example: python scan_dependencies_r1.py --online --out <new-json-file>
Python covers the specified runtime roots and installed non-extra requirements;
Cargo covers registry packages in Cargo.lock, including other-platform entries.
"""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import tomllib

from packaging.requirements import Requirement

ROOTS = ["fastapi", "uvicorn", "spacy", "pl-core-news-lg", "torch", "transformers",
         "cryptography", "PyMuPDF", "python-docx", "Pillow", "pytesseract",
         "pyahocorasick", "morfeusz2", "python-multipart", "requests"]
parser = argparse.ArgumentParser()
parser.add_argument("--online", action="store_true")
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[4]
queue, seen, absent = list(ROOTS), {}, []
while queue:
    name = queue.pop()
    normalized = name.lower().replace("_", "-")
    if normalized in seen:
        continue
    try:
        dist = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        absent.append(name)
        continue
    seen[normalized] = {"name": dist.metadata["Name"], "version": dist.version}
    for text in dist.requires or []:
        requirement = Requirement(text)
        if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
            queue.append(requirement.name)
crates = tomllib.loads((repo / "frontend/src-tauri/Cargo.lock").read_text())["package"]
packages = [{"ecosystem": "PyPI", **p} for p in seen.values()]
packages += [{"ecosystem": "crates.io", "name": p["name"], "version": p["version"]}
             for p in crates if str(p.get("source", "")).startswith("registry+")]
results, completed, failures = [], 0, []
if args.online:
    import requests
    for offset in range(0, len(packages), 100):
        chunk = packages[offset:offset + 100]
        try:
            response = requests.post("https://api.osv.dev/v1/querybatch", timeout=45,
                json={"queries": [{"package": {"ecosystem": p["ecosystem"], "name": p["name"]},
                                   "version": p["version"]} for p in chunk]})
            response.raise_for_status()
            for package, row in zip(chunk, response.json()["results"]):
                if row.get("vulns"):
                    results.append({**package, "ids": [v["id"] for v in row["vulns"]]})
            completed += len(chunk)
        except Exception as exc:
            failures.append(type(exc).__name__)
report = {"source": "OSV querybatch" if args.online else "LOCAL_INVENTORY_ONLY",
          "python_roots": ROOTS, "python_missing_roots": sorted(set(absent)),
          "python_packages": len(seen), "cargo_registry_packages": len(packages) - len(seen),
          "queried": completed, "failures": failures, "matches": results, "inventory": packages}
args.out.parent.mkdir(parents=True, exist_ok=True)
with args.out.open("x", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
print(json.dumps({key: value for key, value in report.items() if key not in ("inventory", "matches")}))
