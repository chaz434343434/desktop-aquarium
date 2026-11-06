"""Headless checks for 1.12.0: 6-digit tank codes through the tank server. Uses a pretend server on this computer.
DA_TEST_WORKER=http://127.0.0.1:8799 runs the normal steps against a real copy of the server instead.
Run: python test_v1120.py [screenshot_dir]"""
import json
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-11-10"
import pygame  # noqa: E402

REAL = os.environ.get("DA_TEST_WORKER")
TANKS, KEYS = {}, {}
LOG = []
MODE = ["normal"]
NEXT = [482913]


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def out(self, status, data=None, raw=None):
        body = raw if raw is not None else json.dumps(data or {}).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_any(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        LOG.append((self.command, self.path, raw, self.headers.get("Authorization")))
        if MODE[0] == "500":
            return self.out(500, {})
        if MODE[0] == "busy":
            return self.out(429, {})
        if MODE[0] == "garbage":
            return self.out(200, raw=b"<html>not json")
        if MODE[0] == "list":
            return self.out(200, raw=b"[1,2,3]")
        if MODE[0] == "huge":
            return self.out(200, raw=b'{"code":"' + b"x" * 200000 + b'"}')
        if MODE[0] == "badtank":
            return self.out(200, {"code": "DA1:notatank", "id": "12", "key": "nope"})
        parts = self.path.strip("/").split("/")
        tid = parts[2] if len(parts) > 2 else None
        if self.command == "POST" and len(parts) == 2:
            tid = str(NEXT[0])
            NEXT[0] += 1
            TANKS[tid] = json.loads(raw)["code"]
            KEYS[tid] = f"{int(tid):064x}"
            return self.out(201, {"id": tid, "key": KEYS[tid]})
        if tid not in TANKS:
            return self.out(404, {})
        if self.command == "GET":
            return self.out(200, {"code": TANKS[tid], "updated": 1})
        if self.command == "POST":
            return self.out(200, {"ok": True})
        if self.headers.get("Authorization") != "Bearer " + KEYS[tid]:
            return self.out(403, {})
        if self.command == "PUT":
            TANKS[tid] = json.loads(raw)["code"]
        else:
            del TANKS[tid]
        return self.out(200, {"ok": True})

    do_GET = do_POST = do_PUT = do_DELETE = handle_any


if REAL:
    os.environ["DA_ONLINE_URL"] = REAL
else:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["DA_ONLINE_URL"] = f"http://127.0.0.1:{srv.server_port}"

from purrfin import economy as E  # noqa: E402
from purrfin import share, winutil  # noqa: E402
from purrfin.game import Game, SYNC_EVERY  # noqa: E402

winutil.monitors = lambda: [dict(x=0, y=0, w=1920, h=1040, primary=True)]
clip = [""]
winutil.get_clipboard = lambda: clip[0]
winutil.set_clipboard = lambda t: clip.__setitem__(0, t) or True
pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def new_game(name=None):
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
    g.apply_window(first=True)
    g.toasts.clear()
    g.sync_t = 1e9
    if name:
        g.state["tank_name"] = name
    return g


def settle(g, cond=None, wait=12.0):
    """let the background request finish"""
    end = time.time() + wait
    while time.time() < end:
        g.update(0.01)
        if not g.online.busy and (cond is None or cond()):
            g.update(0.01)
            return True
        time.sleep(0.01)
    return False


def buttons(g):
    found = {}
    orig = g.ui.button

    def spy(scr, rect, label, cb, *a, **kw):
        found.setdefault(label, []).append(cb)
        return orig(scr, rect, label, cb, *a, **kw)
    g.ui.button = spy
    g.draw()
    g.draw()
    g.ui.button = orig
    return found


# ---- nothing leaves the computer until you ask
LOG.clear()
me = new_game("Mr Lee's Tank")
s = me.state
for _ in range(200):
    me.update(0.5)
me.draw()
check("playing sends nothing to the server", not LOG)
check("not shared to begin with", s["online"] is None)

# ---- sharing asks first
me.ui.panel, me.ui.tab = "shop", "mine"
b = buttons(me)
check("My Tank offers sharing", "Share my tank" in b and "Type a code" in b)
b["Share my tank"][0]()
check("the first press only asks", not me.online.busy and s["online"] is None)
if shots:
    os.makedirs(shots, exist_ok=True)
    me.draw()
    me.draw()
    pygame.image.save(me.screen, os.path.join(shots, "share_ask.png"))
b = buttons(me)
b["Sure? Share it"][0]()
settle(me, lambda: s["online"])
check("the second press shares it", s["online"] and len(s["online"]["id"]) == 6)
tid, key = s["online"]["id"], s["online"]["key"]
check("you get told your code", any(tid in t[0] for t in me.toasts))
b = buttons(me)
check("your code replaces the button", "Stop sharing" in b and "Copy" in b and "Share my tank" not in b)
b["Copy"][0]()
check("Copy copies just the digits", clip[0] == tid)
if shots:
    me.toasts.clear()
    me.draw()
    me.draw()
    pygame.image.save(me.screen, os.path.join(shots, "shared.png"))
check("your secret key isn't in your tank code", key not in json.dumps(share.decode(share.encode(s), s["settings"]), default=str)
      and key not in share.encode(s))
me.save()
check("the code is still yours next time", Game(save_path=me.save_path).state["online"]["id"] == tid)

# ---- a friend types the code
fr = new_game("Sam's Tank")
fr.start_code_entry()
fr.text_input("4a8-2 ")
check("the box only takes digits", fr.rename_text == "482")
fr.rename_text = ""
fr.text_input("12345678")
check("and only 6", fr.rename_text == "123456")
fr.rename_text = "123"
fr.finish_rename(True)
check("too short just says so", fr.renaming is None and not fr.online.busy and not fr.visiting)
fr.start_code_entry()
for ch in tid:
    fr.text_input(ch)
fr.draw()
fr.finish_rename(True)
settle(fr, lambda: fr.visiting)
check("typing the code shows their tank", fr.visiting and fr.visiting["tank_name"] == "Mr Lee's Tank" and fr.visit_id == tid)
b = buttons(fr)
check("with Save friend and Report", "Save friend" in b and "Report" in b)
if shots:
    pygame.image.save(fr.screen, os.path.join(shots, "visiting_online.png"))
b["Save friend"][0]()
f = fr.state["friends"][0]
check("the friend keeps the short code", f.get("id") == tid)
check("your friend gets no key", "key" not in f and key not in json.dumps(fr.state["friends"]))
fr.leave_visit()
clip[0] = f" {tid}\n"
fr.visit_from_clipboard()
settle(fr, lambda: fr.visiting)
check("Visit a tank takes a copied short code too", fr.visit_id == tid)
fr.leave_visit()

# ---- friends stay up to date
E.add_fish(s, "sunflower")
E.add_fish(s, "sunflower")
me.tank.sync()
me.sync_t = 0.0
me.update(0.01)
sent = share.encode(s)
settle(me, lambda: s["online"]["sent"] == sent)
check("your tank updates by itself", s["online"]["sent"] == sent)
n = len(LOG)
me.sync_t = 0.0
me.update(0.01)
settle(me)
check("nothing is sent if nothing changed", len(LOG) == n or REAL)
check("it checks every few minutes, not constantly", SYNC_EVERY >= 120)
fr.ui.panel, fr.ui.tab = "shop", "mine"
b = buttons(fr)
check("friends with a short code don't need New code", "New code" not in b)
b["Visit"][0]()
settle(fr, lambda: fr.visiting)
check("visiting a saved friend shows their latest tank", len(fr.tank.fish) == 3 and f["fish"] == 3)
fr.leave_visit()

# ---- the rest of a tank's life
s["bubbles"] = 0
s["earned_run"] = 1e18
me.spawn()
check("sharing survives a Spawning Season", me.state["online"] and me.state["online"]["id"] == tid)
s = me.state
me.ui.panel, me.ui.tab = "shop", "mine"
b = buttons(me)
b["Stop sharing"][0]()
check("Stop sharing asks first", not me.online.busy)
buttons(me)["Sure?"][0]()
settle(me, lambda: s["online"] is None)
check("Stop sharing takes it off", s["online"] is None)
fr.ui.panel, fr.ui.tab = "shop", "mine"
buttons(fr)["Visit"][0]()
settle(fr, lambda: fr.visiting)
check("a friend who stopped sharing still shows your saved copy", fr.visiting and fr.visiting["tank_name"] == "Mr Lee's Tank")
check("and you're told", any("no longer shared" in t[0] for t in fr.toasts))
check("that copy can't be reported", fr.visit_id is None)
fr.leave_visit()
fr.toasts.clear()
fr.visit_online("100001" if not REAL else "999998")
settle(fr)
check("a code nobody has says so", not fr.visiting and any("no tank" in t[0] for t in fr.toasts))

# ---- reset also deletes
a = new_game("Reset Me")
a.share_tank()
settle(a, lambda: a.state["online"])
gone = a.state["online"]["id"]
a.reset_save()
settle(a)
check("Fresh tank takes it off the server too", a.state["online"] is None)
fr.toasts.clear()
fr.visit_online(gone)
settle(fr)
check("so that code stops working", not fr.visiting)

if not REAL:
    # ---- a report
    a = new_game("Rude")
    a.share_tank()
    settle(a, lambda: a.state["online"])
    fr.visit_online(a.state["online"]["id"])
    settle(fr, lambda: fr.visiting)
    b = buttons(fr)
    b["Report"][0]()
    check("Report asks first", fr.visiting)
    LOG.clear()
    buttons(fr)["Sure?"][0]()
    settle(fr)
    check("then reports and takes you home", not fr.visiting and LOG and LOG[-1][1].endswith("/report"))
    a.sync_t = 1e9

    # ---- when things go wrong
    t = new_game("Trouble")
    for mode, what in (("500", "server error"), ("busy", "too many tries"), ("garbage", "not JSON"), ("list", "wrong shape"),
                       ("huge", "enormous reply"), ("badtank", "bad tank and bad id")):
        MODE[0] = mode
        t.toasts.clear()
        t.share_tank()
        settle(t)
        t.visit_online("482913")
        settle(t)
        t.update(0.01)
        t.ui.panel, t.ui.tab = "shop", "mine"
        t.draw()
        check(f"{what}: nothing breaks and you're told", t.state["online"] is None and not t.visiting and t.toasts)
    MODE[0] = "normal"
    t.share_tank()
    settle(t, lambda: t.state["online"])
    good = dict(t.state["online"])
    MODE[0] = "500"
    t.stop_sharing()
    settle(t)
    check("if Stop sharing can't reach the server, you're told it's still shared", t.state["online"] == good
          and any("still shared" in x[0] for x in t.toasts))
    E.add_fish(t.state, "sunflower")
    t.sync_t = 0.0
    t.update(0.01)
    settle(t)
    check("a failed update tries again later, keeping your code", t.state["online"]["id"] == good["id"])
    MODE[0] = "normal"
    TANKS.pop(good["id"])
    t.sync_t = 0.0
    t.update(0.01)
    settle(t, lambda: t.state["online"] is None)
    check("if the server lost your tank, you can share again", t.state["online"] is None)

    # ---- no server at all
    srv.shutdown()
    srv.server_close()
    t = new_game("Alone")
    t.share_tank()
    t.visit_online("482913")
    started = time.time()
    t.update(0.01)
    t.draw()
    check("no connection never freezes the tank", time.time() - started < 0.5)
    settle(t)
    check("no connection just says so", t.state["online"] is None and any("Couldn't reach" in x[0] for x in t.toasts))

    # ---- odd saves
    p = os.path.join(tempfile.mkdtemp(), "s.json")
    g = Game(save_path=p, fresh=True)
    g.save()
    d = json.load(open(p))
    for bad in ("nope", 5, {"id": "12"}, {"id": "123456"}, {"id": "123456", "key": "short"}, {"id": "../x", "key": "a" * 64}):
        d["online"] = bad
        json.dump(d, open(p, "w"))
        check(f"a damaged share entry is dropped: {str(bad)[:24]}", Game(save_path=p).state["online"] is None)
    d["online"] = {"id": "123456", "key": "a" * 64, "sent": "x"}
    d["friends"] = [{"code": "DA1:x", "name": "A", "id": "bad"}, {"code": "DA1:y", "name": "B", "id": "654321"}]
    json.dump(d, open(p, "w"))
    g = Game(save_path=p)
    check("good ones stay", g.state["online"]["id"] == "123456" and "id" not in g.state["friends"][0]
          and g.state["friends"][1]["id"] == "654321")
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
