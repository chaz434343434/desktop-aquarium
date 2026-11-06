"""Headless checks for 1.9.0: the Ring Tree (hidden branches, its own big screen) and carrying the tank
anywhere on the desktop. Run: python test_v190.py [screenshot_dir]"""
import itertools
import math
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-11-10"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin import ringtree as RT  # noqa: E402
from purrfin import winutil  # noqa: E402
from purrfin.data import PEARL_TREE, PEARL_TREE_BY_ID  # noqa: E402
from purrfin.game import Game  # noqa: E402

winutil.monitors = lambda: [dict(x=0, y=0, w=1920, h=1040, primary=True)]    # the same screen on any machine
pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def shot(g, name):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.toasts.clear()
        g.update(0.05)
        g.draw()
        pygame.image.save(g.screen, os.path.join(shots, name + ".png"))


def new_game():
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
    g.apply_window(first=True)
    return g


def press(g, rect_pos):
    """a real click, through the same path the mouse takes"""
    k = g.ui.k
    p = (int(rect_pos[0] * k), int(rect_pos[1] * k))
    g.mouse_motion(p, (0, 0), (0, 0, 0))
    g.mouse_down(p, 1)
    g.mouse_up(p, 1)


# ---- the shape of the tree
ids = [n["id"] for n in PEARL_TREE]
check("42 rings", len(PEARL_TREE) == 42)
check("ids are unique", len(set(ids)) == len(ids))
check("every link goes to a real ring", all(n["req"] in (None, *ids) for n in PEARL_TREE))
check("six branches", set(RT.KIDS[None]) == set(RT.BRANCHES) and len(RT.BRANCHES) == 6)
check("it really branches", sum(1 for k in RT.KIDS if k and len(RT.KIDS[k]) > 1) >= 6)
pts = RT.LAYOUT
closest = min(math.dist(pts[a], pts[b]) for a, b in itertools.combinations(ids, 2))
check(f"no two rings overlap (closest {closest:.0f}px)", closest > 2 * RT.R + 20)
g = new_game()
labels = {i: g.ui.f_small.size(PEARL_TREE_BY_ID[i]["name"].replace(" Ring", ""))[0] for i in ids}
clash = []
for a, b in itertools.combinations(ids, 2):
    if abs(pts[a][0] - pts[b][0]) < (labels[a] + labels[b]) / 2 + 6 and abs(pts[a][1] - pts[b][1]) < 2 * RT.R + 24:
        clash.append((a, b))
check(f"names don't run into each other at full zoom {clash[:3]}", not clash)


def crossing(p1, p2, p3, p4):
    def side(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return side(p1, p2, p3) * side(p1, p2, p4) < 0 and side(p3, p4, p1) * side(p3, p4, p2) < 0


edges = [((0, 0) if not n["req"] else pts[n["req"]], pts[n["id"]]) for n in PEARL_TREE]
check("branches never cross", not any(crossing(*a, *b) for a, b in itertools.combinations(edges, 2)))

# ---- what a new player can see
s = g.state
vis = [i for i in ids if E.tree_visible(s, i)]
check("a new player sees only the six first rings", set(vis) == set(RT.BRANCHES))
check("no Rings button before they've earned anything", "Rings" not in [t for t in []] and not s["pearls"])

g.ui.open_rings()
g.draw()
g.draw()
check("the tree has its own big screen", g.ui.panel_rect.w >= 900 and g.ui.panel_rect.h >= 500)
check("the window opened up for it", g.win_h > 660)
titles = [t[1][0] for t in g.ui.tips if t[1]]
check("only found rings can be hovered", set(titles) == {PEARL_TREE_BY_ID[i]["name"] for i in vis})
shot(g, "tree_new")

# ---- buying uncovers the next rings
s["pearls"] = 40
x, y = g.ui.rings.at("gills")
g.draw()
press(g, (int(x), int(y)))
check("clicking a ring selects it", g.ui.rings.sel == "gills")
g.draw()
buy = [(r, cb) for r, cb in g.ui.hits if r.w > 200 and r.h == 36]
check("its card has a Buy button", len(buy) == 1)
press(g, buy[0][0].center)
check("buying takes the pearls and gives the level", E.tlv(s, "gills") == 1 and s["pearls"] == 39)
check("the rings beyond it appear", E.tree_visible(s, "playful") and E.tree_visible(s, "thrift"))
check("but not the ones past those", not E.tree_visible(s, "friends") and not E.tree_visible(s, "grace"))
check("other branches stay as they were", not E.tree_visible(s, "fertile"))
for _ in range(20):
    g.update(0.05)
    g.draw()
shot(g, "tree_some")

# ---- all of it found: everything has to fit, and every card has room for its words
s["tree"] = {n["id"]: n["max"] if i % 3 == 0 else (1 if i % 3 == 1 else 0) for i, n in enumerate(PEARL_TREE)}
for n in PEARL_TREE:                     # (make sure the whole tree is uncovered)
    s["tree"][n["id"]] = max(s["tree"][n["id"]], 1)
g.ui.rings.fit()
g.ui.rings.pan, g.ui.rings.goal = list(g.ui.rings.goal), None
g.draw()
xs = [g.ui.rings.at(i) for i in ids]
check("Fit shows the whole tree at once", all(g.ui.rings.canvas.collidepoint(p) for p in xs))
g.ui.rings.sel = "gills"
shot(g, "tree_full")
w = RT.CARD_W - 28
for n in PEARL_TREE:
    words = 72 + 30 * len(g.ui.wrap(n["name"], g.ui.f_big, w)) + 4 + 22 * len(g.ui.wrap(n["desc"], g.ui.f_norm, w)) + 8 + 18
    if words > 560 - 48 - 28:
        check(f"{n['name']} card fits", False)
    if n["name"] and g.ui.f_big.size(max(g.ui.wrap(n["name"], g.ui.f_big, w), key=len))[0] > w:
        check(f"{n['name']} title fits", False)
s["tree"] = {"gills": 1}
g.ui.rings.opened()
g.draw()

# ---- moving around in it
g.ui.rings.fit()
g.ui.rings.pan, g.ui.rings.goal = list(g.ui.rings.goal), None
g.draw()
c = g.ui.rings.canvas
empty = None
for ex, ey in ((c.x + 12, c.y + 12), (c.right - 12, c.y + 12), (c.x + 12, c.bottom - 12), (c.right - 12, c.bottom - 12)):
    if not any(r.collidepoint((ex, ey)) for r, _ in g.ui.hits):
        empty = (ex, ey)
        break
before = list(g.ui.rings.pan)
k = g.ui.k
g.mouse_down((int(empty[0] * k), int(empty[1] * k)), 1)
g.mouse_motion((int(empty[0] * k) + 30, int(empty[1] * k) + 10), (30, 10), (1, 0, 0))
check("dragging the water looks around", g.ui.rings.pan != before)
g.mouse_up((0, 0), 1)
z = g.ui.rings.zoom
g.ui.wheel(tuple(c.center), -1)
check("scrolling zooms", g.ui.rings.zoom != z)
g.ui.rings.pan = [99999.0, 99999.0]
g.draw()
xs = [pts[i][0] * g.ui.rings.zoom for i in ids if E.tree_visible(s, i)] + [0]
check("you can't wander off past what you've found", g.ui.rings.pan[0] <= -min(xs) + 1)
g.ui.open_rings()
g.draw()
check("closing it shrinks the window again", g.win_h <= 660 and g.ui.panel is None)

# ---- an old save keeps its rings
g = new_game()
s = g.state
s["tree"] = {"gills": 10, "playful": 5, "friends": 5, "hatch": 2, "fishring": 3, "headstart": 1, "crown": 2}
s["pearls"] = 7
check("old rings stay, with everything they had uncovered",
      all(E.tree_visible(s, i) for i in ("friends", "fishring", "crown", "ocean", "giftbag", "bargain")))
check("old rings keep their levels", E.tlv(s, "gills") == 10 and E.tlv(s, "crown") == 2)
g.draw()
labels = []
orig = g.ui.button
g.ui.button = lambda scr, rect, label, *a, **kw: labels.append(label) or orig(scr, rect, label, *a, **kw)
g.draw()
g.ui.button = orig
check("the HUD has a Rings button once you have pearls", "Rings" in labels)
g.ui.panel, g.ui.tab = "shop", "spawn"
g.toasts.clear()
s["earned_run"] = 1e17
owed = E.pearls_for(s)
g.draw()
g.draw()
g.spawn()
g.draw()
check("a Spawning Season goes straight to the tree", g.ui.panel == "rings")
check("and pays the pearls", g.state["pearls"] == 7 + owed)

# ---- every ring does something
f = E.new_state()
E.earn(f, 1e30)
f["upgrades"]["rub"] = 3
f["upgrades"]["jar"] = 1
E.add_fish(f, "sunflower", shiny=True)
f["toys"]["castle"] = dict(lv=1)
f["dex"] = ["sunflower"] * 5
FOOD = next(fd["id"] for fd in __import__("purrfin.data", fromlist=["FOODS"]).FOODS if fd["secs"])
UP = "filter"
TOY = "castle" if "castle" in E.TOYS_BY_ID else next(iter(E.TOYS_BY_ID))
FISH = next(sp["id"] for sp in E.SPECIES_BY_ID.values() if not sp.get("season") and sp["cost"])
FEAST = next(iter(__import__("purrfin.data", fromlist=["FEASTS"]).FEASTS))
SHINY = next(x for x in f["fish"] if x.get("shiny"))
PROBES = {
    "bargain": lambda z: E.toy_cost(z, TOY), "giftbag": None,
    "pearldiver": lambda z: E.pearls_for(z), "grace": lambda z: E.pearls_for(z), "thrift": lambda z: E.next_pearls_at(z), "early": lambda z: E.pearls_for(z), "nursery": lambda z: E.hatch_bonus(z), "yolk": None,
    "prompt": lambda z: E.pearls_for(z), "savings": None, "buddy": None,
    "growth": lambda z: E.passive_xp(z), "ocean": lambda z: E.capacity(z),
    "shimmer": lambda z: E.fish_rate(z, SHINY), "froth": lambda z: E.pop_interval(z),
    "overflow": lambda z: E.offline_terms(z), "tender": lambda z: E.drain_mult(z),
    "snack": lambda z: E.food_cost(z, FOOD), "pantry": lambda z: E.feast_cooldown(z, FEAST),
    "gentle": lambda z: E.hands_mult(z), "scratch": lambda z: E.rub_cooldown(z),
    "longscratch": lambda z: E.rub_secs(z), "curious": None, "stargazer": lambda z: E.global_mult(z), "wish": lambda z: E.pearls_for(z),
    "hunter": lambda z: E.upgrade_cost(z, UP), "breeder": lambda z: E.species_cost(z, FISH),
}
for nid, fn in PROBES.items():
    if fn is None:
        continue
    a = fn(f)
    f["tree"] = {nid: 1}
    b = fn(f)
    f["tree"] = {}
    check(f"{nid} changes something", a != b)
k = dict(pearls=0, tree={"headstart": 1, "seasoned": 1, "savings": 2, "keeptoys": 1, "buddy": 2}, spawns=1, settings=E.default_settings(),
         dex=[], stats=dict(pets=0, pops=0, fed=0, playtime=0.0), earned_total=0.0, themes=["classic"], theme="classic", shinies=[], toys={})
n = E.new_state(keep=k)
check("savings: a richer start", n["bubbles"] == 1000.0 * 100)
check("buddy: extra catfish at the start", len(n["fish"]) == 3)
check("wish: extra pearls, checked below", True)
g = new_game()
g.state["earned_run"] = 1e17
plain = E.pearls_for(g.state)
g.state["tree"] = {"wish": 2}
g.spawn()
check("wish: +2 per level at a Spawning Season", g.state["pearls"] == plain + 4)

# ---- small screen + big UI: every Shop tab stays on the panel and clear of the close button
winutil.monitors = lambda: [dict(x=0, y=0, w=1024, h=720, primary=True)]
for k in (1.0, 1.5, 2.0):
    g = new_game()
    s = g.state
    s["settings"]["uiscale"] = k
    s["pearls"] = 5
    g.layout()
    g.apply_window()
    g.ui.panel, g.ui.tab = "shop", "fish"
    rects = {}
    orig_button = g.ui.button
    g.ui.button = lambda scr, rect, label, *a, **kw: rects.__setitem__(label, pygame.Rect(rect)) or orig_button(scr, rect, label, *a, **kw)
    g.draw()
    g.draw()
    g.ui.button = orig_button
    tabs = [rects[t] for t in ("Catfish", "Toys", "Upgrades", "Hatchery", "Themes", "Thanksgiving", "My Tank", "Spawning")]
    x = rects["x"]
    p = g.ui.panel_rect
    check(f"small screen at {int(k * 100)}%: tabs clear the close button", not any(t.colliderect(pygame.Rect(p.right - 40, p.y + 8, 30, 30)) for t in tabs))
    check(f"small screen at {int(k * 100)}%: tabs stay on the panel", all(p.contains(t) for t in tabs))
    check(f"small screen at {int(k * 100)}%: tabs don't overlap", not any(a.colliderect(b) for a, b in itertools.combinations(tabs, 2)))
    g.ui.open_rings()
    g.draw()
    g.draw()
    check(f"small screen at {int(k * 100)}%: the Ring Tree still opens", g.ui.rings.canvas.w > 100 and g.ui.rings.canvas.h > 100)

# ---- carrying the tank (with two pretend monitors and a pretend mouse)
MONS = [dict(x=0, y=0, w=1920, h=1040, primary=True), dict(x=1920, y=-200, w=1280, h=984, primary=False)]
real = winutil.monitors, winutil.cursor_pos, winutil.left_button_down
FULL = None
cursor = [1800, 900]
held = [True]
moves = []
real_move = winutil.move
winutil.monitors = lambda: [dict(m) for m in MONS]
winutil.cursor_pos = lambda: tuple(cursor)
winutil.left_button_down = lambda: held[0]
winutil.move = lambda h, x, y, w, hh, t=True: moves.append((x, y, w, hh))

g = new_game()
g.relayout()
r0 = g.win_x + g.tank_rect.x, g.win_y + g.tank_rect.y
check("starts docked at the bottom right", r0[0] + g.tank_rect.w == 1920 and r0[1] + g.tank_rect.h == 1040)
g.draw()


def screen_tank(g):
    return g.win_x + g.tank_rect.x, g.win_y + g.tank_rect.y


def carry(g, to, start=None):
    start = start or (screen_tank(g)[0] + g.tank_rect.w // 2, screen_tank(g)[1] + 100)
    cursor[:] = start
    held[0] = True
    g.begin_tank_move()
    cursor[:] = to
    g.update(0.016)
    g.draw()
    g.update(0.016)
    held[0] = False
    g.update(0.016)
    g.draw()
    g.draw()


# press on water: a small wobble is a click, a real drag picks it up
a = g.tank_rect
wx, wy = a.x + a.w // 2, a.y + a.h // 2
g.tank.fish.clear()
g.tank.toys.clear() if hasattr(g.tank.toys, "clear") else None
g.tank.pops.clear()
cursor[:] = g.win_x + wx, g.win_y + wy
held[0] = True
g.mouse_down((wx, wy), 1)
check("pressing empty water doesn't lift it yet", g.tank_press and not g.tank_move)
cursor[0] += 3
g.mouse_motion((wx + 3, wy), (3, 0), (1, 0, 0))
check("nor does a tiny wobble", not g.tank_move)
cursor[0] += 30
g.mouse_motion((wx + 33, wy), (30, 0), (1, 0, 0))
check("a real drag from the water picks it up", bool(g.tank_move))
held[0] = False
g.mouse_up((wx + 33, wy), 1)
check("letting go drops it", not g.tank_move)

g = new_game()
g.relayout()
g.draw()
w0, h0 = g.win_w, g.win_h
n0 = len(moves)
cursor[:] = g.win_x + g.tank_rect.centerx, g.win_y + g.tank_rect.y + 50
held[0] = True
g.begin_tank_move()
grab = g.tank_move[:]
cursor[:] = 900, 500
g.update(0.016)
check("the window follows the mouse", len(moves) > n0 and screen_tank(g)[0] == 900 - grab[0])
check("up and down too", screen_tank(g)[1] == 500 - grab[1])
check("without resizing while it's carried", (g.win_w, g.win_h) == (w0, h0))
held[0] = False
g.update(0.016)
g.draw()
mid = screen_tank(g)
check("it stays where it's dropped", mid == (900 - grab[0], 500 - grab[1]))
shot(g, "tank_middle")
g.save()
g2 = Game(save_path=g.save_path)
g2.apply_window(first=True)
g2.relayout()
check("and is still there next time", screen_tank(g2) == mid)

# corners of the screen stay reachable
carry(g, (5, 5))
check(f"the top keeps the buttons on screen (win {g.win_y}, tank {g.tank_rect.y}, hud {g.ui.hud_top()})",
      g.win_y >= 0 and g.tank_rect.y >= 2 * 34 + 8 - 8)
check("at the top, panels open below the tank", g.ui_below or g.win_y + g.win_h <= 1040)
g.ui.panel, g.ui.tab = "shop", "fish"
g.draw()
g.draw()
check("the Shop opens below it", g.ui_below and g.ui.panel_rect.y >= g.ui.tank.bottom)
check("and fits on the screen", g.win_y + g.win_h <= 1040 and g.ui.panel_rect.bottom <= g.ui.H and g.ui.panel_rect.h > 200)
shot(g, "tank_top_shop")
g.toast("hello")
g.ui.panel = None
g.draw()
g.draw()
check("messages stay on screen too", g.compact or (g.ui_below and g.win_h > g.tank_rect.bottom))
g.ui.open_rings()
g.draw()
g.draw()
check("the Ring Tree still opens big at the top", g.ui.panel_rect.h >= 500 and g.win_y == 0)
g.ui.open_rings()
g.draw()

carry(g, (1919, 1039), start=(screen_tank(g)[0] + g.tank_rect.w // 2, screen_tank(g)[1] + 100))
check("the bottom right corner works", screen_tank(g)[0] + g.tank_rect.w <= 1920 and screen_tank(g)[1] + g.tank_rect.h <= 1040)

carry(g, (2500, 300))
check("it can go to another monitor", g.mon["x"] == 1920)
x, y = screen_tank(g)
check("and stays on that monitor", 1920 <= x and x + g.tank_rect.w <= 3200 and -200 <= y and y + g.tank_rect.h <= 784)
check("the tank fits itself to that monitor", g.tank.w == g.tank_rect.w // g.S)
MONS.pop()
g.relayout()
x, y = screen_tank(g)
check("if that monitor is unplugged it comes back", 0 <= x and x + g.tank_rect.w <= 1920 and 0 <= y and y + g.tank_rect.h <= 1040)
MONS.append(dict(x=1920, y=-200, w=1280, h=984, primary=False))

g.change_setting("align", "left")
check("the Left/Center/Right buttons dock it again (on the monitor it's on)", g.tank_pos() is None
      and screen_tank(g)[0] == g.mon["x"] and screen_tank(g)[1] + g.tank_rect.h == g.mon["y"] + g.mon["h"])

# you can still do everything else without lifting it by accident
g = new_game()
g.relayout()
g.draw()
a = g.tank.spawn_pop(g.tank.w / 2, 20)
g.tank.pops.clear()
fish = next(iter(g.tank.fish.values()))
p = g.to_screen(fish.x, fish.y)
held[0] = True
cursor[:] = g.win_x + p[0], g.win_y + p[1]
pets = g.state["stats"]["pets"]
g.mouse_down((int(p[0]), int(p[1])), 1)
check("clicking a fish still pets it", g.state["stats"]["pets"] == pets + 1 and not g.tank_press)
g.mouse_motion((int(p[0]) + 40, int(p[1])), (40, 0), (1, 0, 0))
check("and dragging from a fish doesn't lift the tank", not g.tank_move)
held[0] = False
g.mouse_up((int(p[0]), int(p[1])), 1)
g.draw()
g.ui.set_mouse(g.ui.tank_grip.center)
g.draw()
rect = next((r for r, cb in g.ui.hits if r == g.ui.tank_grip), None)
check("the handle shows up when the mouse is near", rect is not None)
cursor[:] = g.win_x + rect.centerx, g.win_y + rect.centery
held[0] = True
g.mouse_down(rect.center, 1)
check("and lifts the tank straight away", bool(g.tank_move))
held[0] = False
g.mouse_up(rect.center, 1)
g.visiting = dict(fish=[], tank_name="x")
cursor[:] = 500, 500
g.begin_tank_move()
check("no carrying while visiting a friend's tank", not g.tank_move)
g.visiting = None

winutil.monitors, winutil.cursor_pos, winutil.left_button_down = real
winutil.move = real_move
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
