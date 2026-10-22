"""Headless checks for 1.3.2: Auto-Nest on/off, removing eggs, the Hatchery / My Tank HUD buttons,
and baby earnings on the 'tank is full' popup. Run: python test_v132.py [screenshot_dir]"""
import os
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


def shot(name, rect=None):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.draw()
        g.draw()
        pygame.image.save(g.screen.subsurface(rect or g.ui.panel_rect), os.path.join(shots, name + ".png"))


E.earn(s, 1e8)
s["upgrades"].update(hatchery=4, autonest=1, tank=1)
g.tank.sync()
g.toasts.clear()

# ---- auto-nest can be paused so you can switch eggs
g.lay_clutch("quick")
g.lay_clutch("quick")
for e in s["eggs"]:
    e["left"] = 0
g.toggle_autonest()
check("Auto-Nest can be switched off", s.get("autonest_off"))
g.hatch_ready()
check("with it off, the nest is empty after hatching", not s["eggs"])
g.lay_clutch("golden")
check("so you can lay a different egg", [e["c"] for e in s["eggs"]] == ["golden"])
g.toggle_autonest()
s["eggs"][0]["left"] = 0
g.hatch_ready()
check("switched back on, it re-lays the egg you picked", [e["c"] for e in s["eggs"]] == ["golden"])

# ---- remove an egg (two clicks), mystery eggs go back to the stash
s["mystery"] = 1
g.lay_clutch("mystery")
mys = [e for e in s["eggs"] if e["c"] == "mystery"][0]
g.remove_egg(mys)
check("removing a Mystery Egg returns it to the stash", s["mystery"] == 1 and mys not in s["eggs"])
gold = s["eggs"][0]
g.remove_egg(gold)
check("removing a normal egg empties its slot", not s["eggs"])

# ---- HUD buttons
g.ui.panel = None
g.draw()
g.ui.open_tab("hatchery")
check("Hatchery button opens Shop > Hatchery", g.ui.panel == "shop" and g.ui.tab == "hatchery")
g.ui.open_tab("hatchery")
check("pressing it again closes it", g.ui.panel is None)
g.ui.open_tab("mine")
check("My Tank button opens Shop > My Tank", g.ui.panel == "shop" and g.ui.tab == "mine")
g.ui.open_tab("fish")
check("Shop button switches back to the shop", g.ui.panel == "shop" and g.ui.tab == "fish")
g.ui.open_tab("fish")
check("and closes it when pressed again", g.ui.panel is None)
s["upgrades"]["hatchery"] = 0
g.draw()
labels_without = len(g.ui.hits)
s["upgrades"]["hatchery"] = 4
g.draw()
check("Hatchery button only shows once the Hatchery is built", len(g.ui.hits) > labels_without)
r = g.tank_rect
shot("hud", pygame.Rect(max(0, r.right - 900), r.y - 80, min(900, r.right), 80))

g.lay_clutch("class")
g.toggle_autonest()
g.ui.panel, g.ui.tab = "shop", "hatchery"
shot("hatchery_tab")
g.toggle_autonest()

# ---- baby popup shows earnings
while len(s["fish"]) < E.capacity(s):
    E.add_fish(s, "sunflower", shiny=False)
g.tank.sync()
s["pending"] = []          # earlier random Small Egg hatches can leave a baby waiting too
s["eggs"] = [dict(c="golden", left=0, total=1, inc=1)]
g.hatch_ready()
check("baby waiting (tank full)", len(s["pending"]) == 1)
g.draw()
g.draw()
b = s["pending"][0]
grown = E.fish_rate(s, dict(b, grow=0)) * E.global_mult(s)
check(f"baby's grown earnings are shown (+{E.fmt(grown)}/s)", grown > 0 and g.ui.panel == "baby")
shot("baby_popup")
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
