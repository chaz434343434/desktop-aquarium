"""Headless checks for 1.10.0: the saved friends list. Run: python test_v1100.py [screenshot_dir]"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin import share  # noqa: E402
from purrfin import winutil  # noqa: E402
from purrfin.game import Game  # noqa: E402

winutil.monitors = lambda: [dict(x=0, y=0, w=1920, h=1040, primary=True)]
pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def new_game():
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
    g.apply_window(first=True)
    g.toasts.clear()
    return g


def buttons(g):
    """{label: (rect, callback)} of everything clickable with a label on the current screen"""
    found = {}
    orig = g.ui.button

    def spy(scr, rect, label, cb, *a, **kw):
        found.setdefault(label, []).append((pygame.Rect(rect), cb))
        return orig(scr, rect, label, cb, *a, **kw)
    g.ui.button = spy
    g.draw()
    g.draw()
    g.ui.button = orig
    return found


def friend_code(name, fish=3):
    o = E.new_state()
    o["tank_name"] = name
    o["upgrades"]["tank"] = 4
    for _ in range(fish - 1):
        E.add_fish(o, "sunflower")
    return share.encode(o)


clip = [""]
winutil.get_clipboard = lambda: clip[0]

g = new_game()
s = g.state
check("a new player has an empty list", s["friends"] == [])
g.ui.panel, g.ui.tab = "shop", "mine"
g.draw()
g.draw()

# ---- saving from a visit
code = friend_code("Mr Lee's Tank", 3)
clip[0] = "here you go! " + code + " enjoy"
g.visit_from_clipboard()
b = buttons(g)
check("visiting offers Save friend", "Save friend" in b)
b["Save friend"][0][1]()
f = s["friends"][0] if s["friends"] else {}
check("it saves the tank", f.get("name") == "Mr Lee's Tank" and f.get("fish") == 3)
check("it keeps only the code, not the words around it", f.get("code") == code)
check("the button goes away once saved", "Save friend" not in buttons(g) and "Update friend" not in buttons(g))
g.save_friend()
check("saving twice doesn't double it", len(s["friends"]) == 1)
g.leave_visit()
check("your own tank isn't changed by any of this", len(g.tank.fish) == 1 and g.state is s)

# ---- no code needed the second time
g.ui.panel, g.ui.tab = "shop", "mine"
clip[0] = "nothing useful"
b = buttons(g)
check("My Tank lists them with Visit", "Visit" in b and "Remove" in b)
b["Visit"][0][1]()
check("Visit works with no code on the clipboard", g.visiting and len(g.tank.fish) == 3 and g.visiting["tank_name"] == "Mr Lee's Tank")
g.leave_visit()

# ---- a tank with no name
g.visit(friend_code("", 2))
g.save_friend()
check("a tank with no name gets one", s["friends"][1]["name"] == "Friend 1")
g.leave_visit()
g.visit(friend_code("", 4))
g.save_friend()
check("and the next one a different one", s["friends"][2]["name"] == "Friend 2")
g.leave_visit()

# ---- a newer code
newer = friend_code("Mr Lee's Tank", 6)
g.visit(newer)
b = buttons(g)
check("a newer code from the same tank offers Update", "Update friend" in b and "Save friend" not in b)
b["Update friend"][0][1]()
check("Update replaces it, it doesn't add another", len(s["friends"]) == 3 and s["friends"][0]["fish"] == 6 and s["friends"][0]["code"] == newer)
g.leave_visit()
f = s["friends"][1]
old = f["code"]
clip[0] = "not a code"
g.friend_new_code(f)
check("New code with no code copied changes nothing", f["code"] == old)
clip[0] = friend_code("Now Named", 5)
g.friend_new_code(f)
check("New code updates that friend and keeps their name", f["fish"] == 5 and f["name"] == "Friend 1" and f["tank"] == "Now Named")

# ---- rename, remove
g.rename_friend(f)
g.rename_text = "Sam"
g.finish_rename(True)
check("rename works", f["name"] == "Sam" and g.renaming is None)
g.rename_friend(f)
g.rename_text = "   "
g.finish_rename(True)
check("an empty name is ignored", f["name"] == "Sam")
g.ui.panel, g.ui.tab = "shop", "mine"
b = buttons(g)
n = len(s["friends"])
b["Remove"][0][1]()
check("Remove asks first", len(s["friends"]) == n)
b = buttons(g)
check("with a Sure? button", "Sure?" in b)
b["Sure?"][0][1]()
check("then removes that one", len(s["friends"]) == n - 1 and s["friends"][0]["name"] != "x")
check("the right one went", all(x["name"] != "Mr Lee's Tank" for x in s["friends"]))

# ---- however it was pasted, the same tank is the same code
for pasted in (code + "\n", "hi " + code + " bye now", code[:40] + "\n" + code[40:]):
    check(f"cleaned up: {pasted[:8]!r}...", share.clean_code(pasted) == code)

# ---- limits
g.visit(friend_code("Mr Lee's Tank", 3))
g.save_friend()
g.leave_visit()
while len(s["friends"]) < share.MAX_FRIENDS:
    s["friends"].append(dict(name=f"F{len(s['friends'])}", tank=f"F{len(s['friends'])}", code="DA1:x", fish=1, saved=1))
g.visit(friend_code("One Too Many", 2))
g.save_friend()
check("the list has a limit", len(s["friends"]) == share.MAX_FRIENDS)
g.leave_visit()
g.ui.panel, g.ui.tab = "shop", "mine"
g.draw()
del s["friends"][4:]
if shots:
    os.makedirs(shots, exist_ok=True)
    s["friends"][0].update(name="A Very Long Friend Nam")
    g.toasts.clear()
    g.draw()
    g.draw()
    pygame.image.save(g.screen, os.path.join(shots, "friends.png"))
    g.visit(friend_code("Mr Lee's Other Tank", 3))
    g.draw()
    g.draw()
    pygame.image.save(g.screen, os.path.join(shots, "visiting.png"))
    g.leave_visit()

# ---- a saved friend whose code no longer works can't break anything
s["friends"].append(dict(name="Broken", tank="", code="DA1:!!!notreal", fish=1, saved=0))
fish = len(g.tank.fish)
g.visit_friend(s["friends"][-1])
check("a bad saved code just says no", not g.visiting and len(g.tank.fish) == fish)
g.ui.panel, g.ui.tab = "shop", "mine"
g.draw()
s["friends"].pop()

# ---- friends stay with you, and stay private
s["earned_run"] = 1e18
keep = [dict(x) for x in s["friends"]]
g.spawn()
check("the list survives a Spawning Season", g.state["friends"] == keep)
check("your tank code doesn't give your friends list away", "friends" not in json.dumps(share.decode(share.encode(g.state), g.state["settings"]).get("friends_x", "")) and not share.decode(share.encode(g.state), g.state["settings"])["friends"])
g.save()
g2 = Game(save_path=g.save_path)
check("and survives closing the game", g2.state["friends"] == keep)

# ---- old saves and damaged saves
path = os.path.join(tempfile.mkdtemp(), "s.json")
g3 = Game(save_path=path, fresh=True)
g3.save()
d = json.load(open(path))
del d["friends"]
json.dump(d, open(path, "w"))
g3 = Game(save_path=path)
check("an old save starts with an empty list", g3.state["friends"] == [])
d["friends"] = ["junk", 5, {"name": "no code"}, {"code": "not a tank"}, {"code": code, "name": 7, "fish": "many", "saved": None}]
json.dump(d, open(path, "w"))
g3 = Game(save_path=path)
fr = g3.state["friends"]
check("damaged entries are dropped, good ones are tidied", len(fr) == 1 and fr[0]["code"] == code and fr[0]["fish"] == 0 and isinstance(fr[0]["name"], str))
g3.apply_window(first=True)
g3.ui.panel, g3.ui.tab = "shop", "mine"
g3.draw()
d["friends"] = "nope"
json.dump(d, open(path, "w"))
check("a list that isn't a list is ignored", Game(save_path=path).state["friends"] == [])

# ---- fits at any UI size, on a small screen and a narrow tank
winutil.monitors = lambda: [dict(x=0, y=0, w=1024, h=720, primary=True)]
for k in (1.0, 1.5, 2.0):
    g = new_game()
    g.state["settings"]["uiscale"] = k
    g.state["settings"]["width"] = 0.2
    g.layout()
    g.apply_window()
    g.state["friends"] = [dict(name="W" * 22, tank="", code=code, fish=80, saved=1790000000)]
    g.ui.panel, g.ui.tab = "shop", "mine"
    b = buttons(g)
    p = g.ui.panel_rect
    rects = [b[x][0][0] for x in ("Visit", "New code", "Rename", "Remove")]
    check(f"at {int(k * 100)}% the row's buttons stay on the panel", all(p.x <= r.x and r.right <= p.right for r in rects))
    check(f"at {int(k * 100)}% the name doesn't run into them", g.ui.f_norm.size(g.ui.clip_text("W" * 22, g.ui.f_norm, rects[-1].x - p.x - 40))[0] <= rects[-1].x - p.x - 40)
    g.visit(code)
    b = buttons(g)
    check(f"at {int(k * 100)}% the visit bar keeps its buttons", "Back to my tank" in b)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
