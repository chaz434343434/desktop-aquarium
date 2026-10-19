"""Headless checks for Mystery Eggs, Golden Egg shinies, Auto-Nest, the nursery tracker,
and that every upgrade/toy has art. Run: python test_eggs2.py [screenshot.png]"""
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin import game as G  # noqa: E402
from purrfin import sprites  # noqa: E402
from purrfin.data import UPGRADES, TOYS  # noqa: E402

pygame.init()
g = G.Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
s = g.state
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


# ---- every upgrade and toy can be drawn (a missing icon would crash the shop)
bad = []
for u in UPGRADES:
    try:
        sprites.upgrade_icon(u["id"], 4)
    except Exception as e:
        bad.append(u["id"])
for t in TOYS:
    try:
        sprites.toy_icon(t["id"], 2)
    except Exception:
        bad.append(t["id"])
check(f"every upgrade and toy has art {bad}", not bad)

# ---- mystery eggs drop from visitors / golden bubbles
s["upgrades"].update(hatchery=4, tank=8)
E.add_fish(s, "bronze", shiny=False)
g.tank.sync()
G.MYSTERY_FROM_VISITOR = 1.0
g.tank.visit_timer = 0
g.update(0.05)
g.catch_visitor()
check("a visitor dropped a Mystery Egg", s["mystery"] == 1)
G.MYSTERY_FROM_GOLDEN = 1.0
g.tank.spawn_pop(30, 30, golden=True)
g.pop(g.tank.pops[-1])
check("a golden bubble dropped a Mystery Egg", s["mystery"] == 2)
g.lay_clutch("mystery")
check("laying uses one from your stash", s["mystery"] == 1 and s["eggs"][-1]["c"] == "mystery")
s["mystery"] = 0
n = len(s["eggs"])
g.lay_clutch("mystery")
check("can't lay one you don't have", len(s["eggs"]) == n)

# ---- mystery outcomes
random.seed(7)
kinds = {}
for _ in range(2000):
    t = E.new_state()
    E.add_fish(t, "bronze", shiny=False)
    t["upgrades"]["tank"] = 14
    t["eggs"] = [dict(c="mystery", left=0, total=1, inc=1)]
    out = E.hatch(t, t["eggs"][0])
    kinds[out["mystery"]] = kinds.get(out["mystery"], 0) + 1
    if out["mystery"] == "rare":
        assert out["baby"]["sp"] == "panda", out["baby"]["sp"]     # next species after bronze
print("   outcomes:", kinds)
check("all five outcomes happen", set(kinds) == {"empty", "scales", "levels", "baby", "rare"})
check("rare new species is the rarest", kinds["rare"] < kinds["baby"] and kinds["rare"] < kinds["scales"])

# ---- golden egg babies are shinier
def shiny_rate(cid, n=3000):
    hits = babies = 0
    for _ in range(n):
        t = E.new_state()
        t["upgrades"]["tank"] = 14
        t["eggs"] = [dict(c=cid, left=0, total=1, inc=1)]
        out = E.hatch(t, t["eggs"][0])
        if out.get("baby"):
            babies += 1
            hits += out["baby"]["shiny"]
    return hits / max(1, babies)


gold, big = shiny_rate("golden"), shiny_rate("class")
check(f"Golden Egg babies shiny {gold:.0%} vs Big Blue Egg {big:.0%}", gold > 3 * big and 0.15 < gold < 0.26)

# ---- auto-nest
s["eggs"] = [dict(c="golden", left=0, total=1, inc=E.income(s)), dict(c="quick", left=0, total=1, inc=1)]
s["upgrades"]["autonest"] = 1
g.hatch_ready()
check("Auto-Nest re-lays the same eggs", sorted(e["c"] for e in s["eggs"]) == ["golden", "quick"]
      and all(e["left"] > 0 for e in s["eggs"]))
s["upgrades"]["autonest"] = 0
for e in s["eggs"]:
    e["left"] = 0
g.hatch_ready()
check("without Auto-Nest the nest stays empty", not s["eggs"])

# ---- nursery tracker
st = s["stats"]
check(f"nursery counts eggs ({st.get('eggs_hatched')}) and babies ({st.get('babies')})",
      st.get("eggs_hatched", 0) >= 4 and st.get("babies", 0) >= 2)

if len(sys.argv) > 1:
    s["mystery"] = 2
    g.lay_clutch("class")
    g.lay_clutch("mystery")
    s["upgrades"]["autonest"] = 1
    g.toasts.clear()
    s["pending"] = []
    g.ui.panel, g.ui.tab = "shop", "hatchery"
    g.draw()
    g.draw()
    pygame.image.save(g.screen.subsurface(g.ui.panel_rect), sys.argv[1])
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
