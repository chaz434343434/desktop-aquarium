"""Checks a running copy of the tank server. Start one with:  npx wrangler dev --port 8799
then run:  python test_worker.py [http://127.0.0.1:8799]    (add --limits to also check the rate limit)
Never point this at the real server without a reason: it creates and deletes tanks."""
import json
import ssl
import sys
import urllib.error
import urllib.request

import certifi

CTX = ssl.create_default_context(cafile=certifi.where())

args = [a for a in sys.argv[1:] if not a.startswith("--")]
URL = args[0] if args else "http://127.0.0.1:8799"
ok = True
CODE = "DA1:" + "abcDEF123_-" * 20


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def call(method, path, body=None, key=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(URL + path, data=data, method=method, headers={"User-Agent": "DesktopAquariumTest"})
    if data is not None:
        req.add_header("content-type", "application/json")
    if key:
        req.add_header("authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


st, a = call("POST", "/v1/tanks", {"code": CODE})
check("sharing gives a 6-digit code and a key", st == 201 and len(a["id"]) == 6 and a["id"].isdigit() and len(a["key"]) == 64)
tid, key = a["id"], a["key"]
st, g = call("GET", f"/v1/tanks/{tid}")
check("anyone can look it up", st == 200 and g["code"] == CODE and "key" not in g and "key_hash" not in g)
st, _ = call("GET", "/v1/tanks/000001")
check("a code that can't exist is not found", st == 404)
st, _ = call("GET", "/v1/tanks/abc%27%20OR%201=1")
check("junk in the code is not found", st == 404)
st, _ = call("POST", "/v1/tanks", {"code": "not a tank"})
check("it refuses things that aren't tanks", st == 400)
st, _ = call("POST", "/v1/tanks", {"code": "DA1:<script>"})
check("or that have strange characters", st == 400)
st, _ = call("POST", "/v1/tanks", {"code": "DA1:" + "a" * 20000})
check("or are too big", st == 400)
st, _ = call("POST", "/v1/tanks", raw=b"{nonsense")
check("or aren't even JSON", st == 400)
newer = CODE + "NEW"
st, _ = call("PUT", f"/v1/tanks/{tid}", {"code": newer})
check("no key: can't change it", st == 403)
st, _ = call("PUT", f"/v1/tanks/{tid}", {"code": newer}, key="0" * 64)
check("wrong key: can't change it", st == 403)
st, _ = call("DELETE", f"/v1/tanks/{tid}", key="0" * 64)
check("wrong key: can't delete it", st == 403)
st, _ = call("PUT", f"/v1/tanks/{tid}", {"code": newer}, key=key)
check("the right key can", st == 200 and call("GET", f"/v1/tanks/{tid}")[1]["code"] == newer)
st, _ = call("POST", f"/v1/tanks/{tid}/report")
check("a report is taken", st == 200)
for _ in range(3):
    call("POST", f"/v1/tanks/{tid}/report")
check("one person reporting over and over doesn't hide a tank", call("GET", f"/v1/tanks/{tid}")[0] == 200)
if "--local" in sys.argv:          # only a local copy lets a test pretend to be different people
    for n in range(4):
        req = urllib.request.Request(f"{URL}/v1/tanks/{tid}/report", method="POST", data=b"",
                                     headers={"CF-Connecting-IP": f"10.0.0.{n + 1}"})
        urllib.request.urlopen(req, timeout=20, context=CTX).read()
    check("5 different people reporting hides it", call("GET", f"/v1/tanks/{tid}")[0] == 404)
    check("the owner can still update it", call("PUT", f"/v1/tanks/{tid}", {"code": newer}, key=key)[0] == 200)
st, _ = call("DELETE", f"/v1/tanks/{tid}", key=key)
check("the owner can delete it", st == 200 and call("GET", f"/v1/tanks/{tid}")[0] == 404)
st, _ = call("PUT", f"/v1/tanks/{tid}", {"code": newer}, key=key)
check("after that it's gone for good", st == 404)
st, _ = call("GET", "/nothing/here")
check("other addresses are not found", st == 404)
if "--limits" in sys.argv:
    codes = [call("GET", f"/v1/tanks/{100000 + i}")[0] for i in range(70)]
    check(f"walking through codes gets cut off ({codes.count(429)} of 70 refused)", 429 in codes)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
