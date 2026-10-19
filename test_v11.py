"""Headless checks for 1.1: remove names, move the jar/nest, baby catfish from eggs (+ the
full-tank sell choice) and the Pearl Tree. Run: python test_v11.py [screenshot_dir]"""
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
s = g.state
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def shot(name):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.update(0.01)
        g.draw()
        g.draw()
        r = g.tank_rect
        top = max(0, r.y - 520)
        x0 = max(0, r.right - 900)
        pygame.image.save(g.screen.subsurface((x0, top, r.right - x0, g.win_h - top)),
                          os.path.join(shots, name + ".png"))


def at(x, y):
    return tuple(int(v) for v in g.to_screen(x, y))


# ---------------------------------------------------------------- remove a name
f = s["fish"][0]
g.start_rename(f)
g.rename_text = ""
g.text_input("Bubba")
g.finish_rename(True)
check("naming works", f["name"] == "Bubba" and f["named"])
g.start_rename(f)
g.remove_name()
check("Remove name takes the tag away", not f["named"] and f["name"] != "Bubba")
g.start_rename(f)
g.rename_text = "Bubba"
g.finish_rename(True)
g.start_rename(f)
g.rename_text = ""
g.finish_rename(True)
check("saving an empty name also removes it", not f["named"])

# ---------------------------------------------------------------- move the jar and nest
E.earn(s, 1e9)
s["upgrades"].update(jar=2, hatchery=4, tank=1)
g.tank.sync()
for _ in range(100):
    g.update(0.1)
jx, jy = g.tank.jar_pos()
g.mouse_down(at(jx, jy - 5), 1)
g.mouse_motion(at(jx + 60, jy - 5), (60, 0), (1, 0, 0))
g.mouse_up(at(jx + 60, jy - 5), 1)
nx_, _ = g.tank.jar_pos()
check("dragging the jar moves it", abs(nx_ - (jx + 60)) <= 1)
check("dragging doesn't collect it", s["jar"] > 0)
jx, jy = g.tank.jar_pos()
before = s["bubbles"]
g.mouse_down(at(jx, jy - 5), 1)
g.mouse_up(at(jx, jy - 5), 1)
check("a plain click still collects", s["jar"] == 0 and s["bubbles"] > before)
nx, ny = g.tank.nest_pos()
g.mouse_down(at(nx, ny - 4), 1)
g.mouse_motion(at(nx - 50, ny - 4), (-50, 0), (1, 0, 0))
g.mouse_up(at(nx - 50, ny - 4), 1)
check("dragging the nest moves it", abs(g.tank.nest_pos()[0] - (nx - 50)) <= 1)
check("jar/nest spots are saved", "jar" in s["spots"] and "nest" in s["spots"])

# ---------------------------------------------------------------- egg odds
random.seed(3)
ss = E.new_state()
for sp in ("bronze", "pictus", "redtail"):
    E.add_fish(ss, sp, shiny=False)
ss["upgrades"]["tank"] = 14
counts = {"empty": 0, "baby": 0}
species = {}
for _ in range(3000):
    ss["eggs"] = [dict(c="quick", left=0, total=1, inc=1)]
    out = E.hatch(ss, ss["eggs"][0])
    if out["empty"]:
        counts["empty"] += 1
    if out["baby"]:
        counts["baby"] += 1
        species[out["baby"]["sp"]] = species.get(out["baby"]["sp"], 0) + 1
        ss["fish"] = [x for x in ss["fish"] if x is not out["baby"]]
check(f"quick clutches are sometimes empty ({counts['empty'] / 30:.0f}%)", 25 < counts["empty"] / 30 < 45)
check(f"quick clutches sometimes give a baby ({counts['baby'] / 30:.0f}%)", 10 < counts["baby"] / 30 < 25)
check(f"higher tiers are rarer {species}",
      species.get("sunflower", 0) > species.get("pictus", 0) > species.get("redtail", 0))
ss["eggs"] = [dict(c="golden", left=0, total=1, inc=1)]
out = E.hatch(ss, ss["eggs"][0])
check("golden clutches always give a baby", out["baby"] is not None and not out["empty"])

# ---------------------------------------------------------------- full tank -> must choose
s["upgrades"]["tank"] = 0
while len(s["fish"]) < E.capacity(s):
    E.add_fish(s, "sunflower", shiny=False)
g.tank.sync()
s["eggs"] = [dict(c="golden", left=0, total=1, inc=E.income(s))]
n_before = len(s["fish"])
g.hatch_ready()
check("baby waits when the tank is full", len(s["pending"]) == 1 and len(s["fish"]) == n_before)
g.draw()
g.draw()
check("the 'baby hatched' popup is forced open", g.ui.panel == "baby")
g.ui.open("shop")
g.draw()
g.draw()
check("you can't close it without choosing", g.ui.panel == "baby")
shot("baby_popup")
victim = s["fish"][-1]
g.rehome(victim["uid"])
check("selling a fish lets the baby in", not s["pending"] and any(x.get("hatched") for x in s["fish"]))
g.draw()
g.draw()
check("popup closes once it's sorted", g.ui.panel != "baby")
s["eggs"] = [dict(c="golden", left=0, total=1, inc=E.income(s))]
g.hatch_ready()
before = s["bubbles"]
n_before = len(s["fish"])
g.sell_pending()
check("or sell the baby instead", not s["pending"] and len(s["fish"]) == n_before and s["bubbles"] > before)

# ---------------------------------------------------------------- pearl tree
s["pearls"] = 40
inc0 = E.income(s)
g.buy_tree("playful")
check("locked nodes can't be bought", E.tlv(s, "playful") == 0)
g.buy_tree("gills")
check("Golden Gills Lv1 = +10% scales", abs(E.income(s) / inc0 - 1.10) < 0.01 and s["pearls"] == 39)
g.buy_tree("gills")
check("second level costs more", s["pearls"] == 37)
g.buy_tree("playful")
check("unlocked child node can be bought", E.tlv(s, "playful") == 1)
t0 = E.clutch_time(s, "class")
g.buy_tree("hatch")
check("Quick Hatch speeds eggs up", E.clutch_time(s, "class") < t0)
g.buy_tree("headstart")
g.buy_tree("keeptoys")
s["toys"]["apple"] = dict(lv=3)
s["earned_run"] = 1e18
g.ui.panel, g.ui.tab = "shop", "spawn"
shot("pearl_tree")
g.spawn()
s = g.state
check("tree survives Spawning Season", E.tlv(s, "gills") == 2 and E.tlv(s, "playful") == 1)
check("pearls earned from the season", s["pearls"] > 0)
check("Toy Box keeps your toys", s["toys"].get("apple", {}).get("lv") == 3)
check("Head Start gives a bigger tank + scales", s["upgrades"].get("tank") == 1 and s["bubbles"] >= 1000)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
