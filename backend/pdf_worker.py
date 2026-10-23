"""
pdf_worker.py — [LYNX-PDF-CRASH] PDF (odczyt i eksport) w osobnym, krótkotrwałym procesie.

PyMuPDF i Morfeusz 2 to moduły SWIG ze wspólnym rejestrem typów: po załadowaniu PyMuPDF iterator wyników Morfeusza
jest owijany klasą `SwigPyIterator` z PyMuPDF i `morfeusz2.analyse()` kończy się „access violation” — pada cały proces
silnika (Guard R1 i krok 2 OSOBA wołają Morfeusza przy każdym dokumencie). Dlatego PyMuPDF nigdy nie jest importowany
w procesie silnika: silnik woła `extract_text` / `export_pdf`, które uruchamiają ten plik jako osobny proces.
Treść dokumentu przechodzi wyłącznie przez stdin/stdout (bez plików tymczasowych — S5); stderr bez treści.
Moduł importowany przez silnik nie importuje PyMuPDF (tylko w `_main`).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

_PDF_COMB = 1 << 24  # flaga Ff „comb” pola tekstowego AcroForm: jeden znak na kratkę
_TIMEOUT_S = 120


def _pdf_page_text(page) -> str:
    """[LYNX-ZUS-BOXED-IDS] Tekst strony PDF. PESEL/NIP z pola kratkowego AcroForm get_text() podaje cyfrą na linię;
    taki ciąg zastępujemy wartością pola — granice wyłącznie z pola, nigdy z sąsiednich linii. Gdy wygląd pola
    nie daje dokładnie tych znaków albo ciąg występuje więcej razy niż pól z tą wartością — tekst bez zmian."""
    text = page.get_text()
    boxed: dict[str, int] = {}
    for w in page.widgets():
        value = w.field_value if isinstance(w.field_value, str) else ""
        if w.field_flags & _PDF_COMB and len(value) in (10, 11) and value.isascii() and value.isdigit():
            per_char = "\n".join(value) + "\n"
            if page.get_text(clip=w.rect) == per_char:
                boxed[per_char] = boxed.get(per_char, 0) + 1
    for per_char, n_fields in sorted(boxed.items(), key=lambda kv: -len(kv[0])):  # PESEL przed NIP-em, który może być jego początkiem
        pattern = re.compile(r"(?<![^\n])" + re.escape(per_char))  # od początku linii
        if len(pattern.findall(text)) == n_fields:
            text = pattern.sub(per_char.replace("\n", "") + "\n", text)
    return text


def _run(mode: str, payload: bytes) -> bytes:
    proc = subprocess.run([sys.executable, os.path.abspath(__file__), mode], input=payload, capture_output=True,
                          timeout=_TIMEOUT_S, cwd=os.path.dirname(os.path.abspath(__file__)))
    if proc.returncode != 0:
        # stderr procesu PDF zawiera wyłącznie typ błędu (bez treści dokumentu)
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip()[-200:] or f"kod {proc.returncode}")
    return proc.stdout


def extract_text(content: bytes) -> str:
    """Tekst PDF (wszystkie strony) z osobnego procesu."""
    return _run("extract", content).decode("utf-8")


def export_pdf(text: str, filename: str = "dokument") -> bytes:
    """PDF z tekstu (export_pdf.generate_pdf) z osobnego procesu."""
    return _run("export", json.dumps({"text": text, "filename": filename}).encode("utf-8"))


def _main(mode: str) -> int:
    data = sys.stdin.buffer.read()
    try:
        if mode == "extract":
            import fitz
            with fitz.open(stream=data, filetype="pdf") as doc:
                sys.stdout.buffer.write("\n".join(_pdf_page_text(page) for page in doc).encode("utf-8"))
        elif mode == "export":
            from export_pdf import generate_pdf
            req = json.loads(data.decode("utf-8"))
            sys.stdout.buffer.write(generate_pdf(req["text"], req.get("filename", "dokument")))
        else:
            sys.stderr.write("nieznany tryb\n")
            return 2
    except Exception as e:  # S5: tylko typ błędu
        sys.stderr.write(type(e).__name__ + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1] if len(sys.argv) > 1 else ""))
