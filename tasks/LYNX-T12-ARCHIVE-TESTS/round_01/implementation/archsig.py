# Sygnatura katalogu archiwum: nazwa pliku, rozmiar, mtime_ns, sha256 (bez treści).
import hashlib, pathlib, sys
root = pathlib.Path(sys.argv[1])
for p in sorted(root.rglob("*")):
    if p.is_file():
        st = p.stat()
        print(p.relative_to(root).as_posix(), st.st_size, st.st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()[:16])
