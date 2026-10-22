"""S5 na żywym silniku: preview → Zawsze jawne → preview → cofnij → clear. Tekst syntetyczny."""
import json, sys, urllib.request, urllib.error, uuid
sys.stdout.reconfigure(encoding="utf-8")
tok = open(sys.argv[1], encoding="utf-8").read().strip()
H = {"X-Api-Token": tok}

def req(path, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://127.0.0.1:8765" + path, data=data, method=method or ("POST" if data else "GET"),
                               headers={**H, **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as f:
            return f.status, json.load(f)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:120]

def preview(t):
    b = uuid.uuid4().hex
    body = f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"t.txt\"\r\nContent-Type: text/plain\r\n\r\n".encode() + t.encode() + f"\r\n--{b}--\r\n".encode()
    r = urllib.request.Request("http://127.0.0.1:8765/preview", data=body, method="POST", headers={**H, "Content-Type": f"multipart/form-data; boundary={b}"})
    return [(w["fragment"], w["rules"], w["level"]) for w in json.load(urllib.request.urlopen(r, timeout=120))["guard_warnings"]]

T = "Świadek Śludkowskiego nie stawił się. Dostawę wykonała firma Kwarcowe Ogrody."
w0 = preview(T); print("przed:", w0)
y = [w for w in w0 if w[2] == "YELLOW"][0]
print("add:", req("/profile/guard-allowlist", {"value": y[0], "rules": y[1]}))
print("add RED:", req("/profile/guard-allowlist", {"value": "12345678901", "rules": ["HIGH PESEL"]}))
print("lista:", req("/profile/guard-allowlist"))
print("po Zawsze jawne:", preview(T))
print("DELETE stary:", req("/profile/guard-allowlist/" + urllib.parse.quote(y[0]), method="DELETE")[0])
for r in y[1]:
    print("remove:", req("/profile/guard-allowlist/remove", {"value": y[0], "rule": r}))
print("po cofnij:", preview(T))
print("clear:", req("/profile/guard-allowlist/clear", {}), "lista:", req("/profile/guard-allowlist"))
