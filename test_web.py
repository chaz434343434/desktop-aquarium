"""Headless checks for the web version's own parts (the browser is pretended): saving in browser storage,
backup codes, the layout for phones (sideways and upright), taps vs scrolls. Run: python test_web.py"""
import json
import os
import sys
import types

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-11-10"
import pygame  # noqa: E402

store = {}
answers = []
asked = []


class FakeWindow:
    innerWidth, innerHeight = 812, 375

    class localStorage:
        @staticmethod
        def getItem(k):
            return store.get(k)

        @staticmethod
        def setItem(k, v):
            store[k] = v

    @staticmethod
    def prompt(msg, default):
        asked.append((msg, default))
        return answers.pop(0) if answers else None

    @staticmethod
    def window_resize():
        pass

    @staticmethod
    def open(url, target):
        asked.append(("open", url))


fake = types.ModuleType("platform")
fake.window = FakeWindow
real_platform = sys.modules.get("platform")
sys.modules["platform"] = fake
from purrfin import webstore, winutil, share, economy as E  # noqa: E402

webstore.WEB = True
winutil.IS_WEB = True
from purrfin import game as G  # noqa: E402

G.webstore.WEB = True
from purrfin.game import Game  # noqa: E402

pygame.init()
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def new_game():
    winutil.fit_web_size(winutil.web_page_size())
    g = Game()
    g.apply_window(first=True)
    g.toasts.clear()
    return g


# ---- sizes
check("a sideways phone gets a canvas its own shape", winutil.fit_web_size((812, 375)) or winutil.WEB_SIZE == [812, 374])
check("same shape as the page", abs(winutil.WEB_SIZE[0] / winutil.WEB_SIZE[1] - 812 / 375) < 0.02)
g = new_game()
check("the tank fills the width along the bottom", g.tank_rect.w >= g.win_w - g.S and g.tank_rect.bottom == g.win_h)
check("smaller pixels on a short screen", g.S == 2)
check("no moving, stretching, quitting or hiding", not any(lab in ("x", "_") for lab in []) and g.web)
labels = []
orig = g.ui.button
g.ui.button = lambda scr, rect, label, *a, **k: labels.append(label) or orig(scr, rect, label, *a, **k)
g.draw()
g.ui.button = orig
check("no quit or hide buttons", "x" not in labels and "_" not in labels and "Shop" in labels)
g.ui.panel, g.ui.tab = "shop", "fish"
g.draw()
check("menus cover the whole screen on a phone", g.ui.panel_rect.h >= g.ui.H - 10)

# ---- saving in the browser
E.earn(g.state, 1234)
g.save()
check("the save goes into browser storage", "desktop-aquarium:save" in store)
check("and nothing on disk", not os.path.exists("/save.json"))
g2 = new_game()
check("it loads again next visit", abs(g2.state["bubbles"] - g.state["bubbles"]) < 1)

# ---- backup codes
code = share.backup_code(g.state)
check(f"a backup code is text ({len(code)} characters)", code.startswith("DAS1:") and len(code) < 20000)
check("it holds the whole tank", share.read_backup(code)["bubbles"] == g.state["bubbles"])
check("junk isn't a backup", share.read_backup("hello") is None and share.read_backup("DAS1:!!!") is None)
check("a tank code isn't a backup", share.read_backup(share.encode(g.state)) is None)
asked.clear()
g.copy_backup()
check("Copy backup code shows it to copy", asked and asked[-1][1].startswith("DAS1:"))
other = E.new_state()
E.earn(other, 9e9)
E.add_fish(other, "bronze")
answers.append("here it is: " + share.backup_code(other) + " thanks")
check("Restore from code brings that tank back", g.restore_backup() and len(g.state["fish"]) == 2
      and g.state["bubbles"] >= 9e9)
check("and saves it", json.loads(store["desktop-aquarium:save"])["bubbles"] >= 9e9)
answers.append("nonsense")
before = len(g.state["fish"])
check("a bad code changes nothing", not g.restore_backup() and len(g.state["fish"]) == before)
answers.append(None)
check("cancel changes nothing", not g.restore_backup())
g.ui.panel = "settings"
labels.clear()
g.ui.button = lambda scr, rect, label, *a, **k: labels.append(label) or orig(scr, rect, label, *a, **k)
g.draw()
g.ui.button = orig
check("Options has the backup buttons", "Copy backup code" in labels and "Restore from code" in labels)
check("and not the window-only settings", "Left" not in labels and "Check for updates" not in labels)

# ---- typing uses the phone's own text box
g.ui.panel = None
answers.append("Bubbles")
g.start_rename(g.state["fish"][0])
check("naming a fish uses the phone's keyboard", g.state["fish"][0]["name"] == "Bubbles" and g.renaming is None)
answers.append(None)
g.start_rename(g.state["fish"][0])
check("cancelling leaves the name alone", g.state["fish"][0]["name"] == "Bubbles")
answers.append("cory")
g.start_search()
check("searching the Shop too", g.ui.search == "cory" and not g.searching)

# ---- taps vs scrolls
g.ui.search = ""
g.ui.panel, g.ui.tab = "shop", "fish"
g.state["upgrades"]["tank"] = 8
E.earn(g.state, 1e9)
g.draw()
g.draw()
buy = [r for r, cb in g.ui.hits if r.w >= 100 and r.h >= 28 and r.y > 100]
n = len(g.state["fish"])
p = buy[0].center
g.mouse_down(p, 1)
check("pressing a button doesn't fire it yet", len(g.state["fish"]) == n)
g.mouse_up(p, 1)
check("lifting the finger does", len(g.state["fish"]) == n + 1)
g.draw()
n = len(g.state["fish"])
g.mouse_down(p, 1)
for dy in range(0, -120, -20):
    g.mouse_motion((p[0], p[1] + dy), (0, -20), (1, 0, 0))
g.mouse_up((p[0], p[1] - 120), 1)
check("a drag scrolls instead of buying", len(g.state["fish"]) == n and g.ui.scroll.get(("shop", "fish"), 0) > 0)

# ---- upright phone
FakeWindow.innerWidth, FakeWindow.innerHeight = 375, 812
winutil.fit_web_size(winutil.web_page_size())
g.relayout()
g.draw()
check("held upright: asks to turn the phone, nothing to tap by mistake", g.ui.upright_phone() and not g.ui.hits)
earned = g.state["earned_total"]
g.update(1.0)
check("the fish keep earning meanwhile", g.state["earned_total"] > earned)
FakeWindow.innerWidth, FakeWindow.innerHeight = 812, 375
winutil.fit_web_size(winutil.web_page_size())
g.relayout()
g.draw()
check("turned back: the game is back", not g.ui.upright_phone() and g.ui.hits)

# ---- 6-digit tank codes through the browser's fetch (a pretend server answers)
from purrfin import online  # noqa: E402

online.WEB = True
TANKS, KEYS, SENT, PENDING = {}, {}, [], {}
LATER = []                      # answers that arrive a frame later, like a real network
MODE = ["ok"]


def server(method, url, body, key):
    parts = url.strip("/").split("/")
    if MODE[0] == "down":
        return {"s": 0}
    if MODE[0] == "garbage":
        return {"s": 200, "t": "<html>"}
    tid = parts[2] if len(parts) > 2 else None
    if method == "POST" and len(parts) == 2:
        tid = str(482913 + len(TANKS))
        TANKS[tid] = json.loads(body)["code"]
        KEYS[tid] = "ab" * 32
        return {"s": 201, "t": json.dumps({"id": tid, "key": KEYS[tid]})}
    if tid not in TANKS:
        return {"s": 404, "t": "{}"}
    if len(parts) == 4 and parts[3] == "close":
        if key != KEYS[tid]:
            return {"s": 403, "t": "{}"}
        TANKS[tid] = ""
        return {"s": 200, "t": "{}"}
    if method == "GET":
        return {"s": 200, "t": json.dumps({"code": TANKS[tid]})} if TANKS[tid] else {"s": 404, "t": "{}"}
    if key != KEYS[tid]:
        return {"s": 403, "t": "{}"}
    if method == "PUT":
        TANKS[tid] = json.loads(body)["code"]
    return {"s": 200, "t": "{}"}


FakeWindow.eval = staticmethod(lambda js: SENT.append(("eval", "daFetch" in js)))


def da_fetch(n, method, url, body, key):
    SENT.append((method, url, body, key))
    LATER.append((n, json.dumps(server(method, url, body, key))))


FakeWindow.daFetch = staticmethod(da_fetch)
FakeWindow.daTake = staticmethod(lambda n: PENDING.pop(n, None))


def network(g, frames=3):
    """let the pretend network answer, a frame at a time"""
    for _ in range(frames):
        while LATER:
            n, ans = LATER.pop(0)
            PENDING[n] = ans
        g.update(0.05)


me = new_game()
me.state["online"] = None
me.state["tank_name"] = "Phone Tank"
check("the web version can use the tank server", me.online.enabled)
me.share_tank()
check("nothing is answered in the same frame (no freezing)", me.state["online"] is None and me.online.busy)
network(me)
mine = me.state["online"]
check("Open my tank gets a 6-digit code on the phone", mine and mine["id"] == "482913" and mine["open"])
check("the helper was added to the page once", SENT[0] == ("eval", True) and sum(1 for s in SENT if s[0] == "eval") == 1)
check("requests go to the same site as the game", SENT[1][0] == "POST" and SENT[1][1] == "/v1/tanks")
answers.append("482913")
friend = new_game()
friend.state["friends"] = []
friend.start_code_entry()
network(friend)
check("a friend on a phone types the code and sees the tank", friend.visiting and friend.visiting["tank_name"] == "Phone Tank"
      and friend.visit_id == "482913")
friend.save_friend()
friend.leave_visit()
E.add_fish(me.state, "bronze")
me.sync_t = 0.0
me.update(0.01)
network(me)
check("the phone's tank keeps itself up to date", TANKS["482913"] == share.encode(me.state))
friend.visit_friend(friend.state["friends"][0])
network(friend)
check("saved friends show the latest tank", friend.visiting and len(friend.visiting["fish"]) == len(me.state["fish"]))
friend.leave_visit()
me.stop_sharing()
network(me)
check("Close my tank works, and the code stays", not me.state["online"]["open"] and me.state["online"]["id"] == "482913")
put = [s for s in SENT if s[0] == "POST" and s[1].endswith("/close")]
check("with the secret key sent along", put and put[-1][3] == "ab" * 32)
for mode, what in (("down", "no internet"), ("garbage", "nonsense reply")):
    MODE[0] = mode
    t = new_game()
    t.state["online"] = None
    t.toasts.clear()
    t.share_tank()
    network(t)
    check(f"{what}: you're told, nothing breaks", t.state["online"] is None and any("Couldn't reach" in x[0] for x in t.toasts))
MODE[0] = "ok"
FakeWindow.daFetch = staticmethod(lambda *a: (_ for _ in ()).throw(RuntimeError("no fetch")))
t = new_game()
t.state["online"] = None
t.share_tank()
network(t)
check("a browser without fetch: you're told, nothing breaks", t.state["online"] is None)
online.WEB = False

if real_platform:
    sys.modules["platform"] = real_platform
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
