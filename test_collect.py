"""Headless check: clicking the Scale Jar and the egg nest pays out; laying clutches works.
Run: python test_collect.py"""
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
E.earn(s, 1e6)
s["upgrades"].update(jar=2, hatchery=4)
g.tank.sync()

ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


# jar fills while the game runs
for _ in range(600):
    g.update(0.1)
check("jar fills", s["jar"] > 0)
before = s["bubbles"]
jar = s["jar"]
jx, jy = g.tank.jar_pos()
g.mouse_down(tuple(int(v) for v in g.to_screen(jx, jy - 5)), 1)
g.mouse_up(tuple(int(v) for v in g.to_screen(jx, jy - 5)), 1)
check("clicking jar collects it", s["jar"] == 0 and s["bubbles"] >= before + jar * 0.99)

# eggs
check("hatchery has 2 slots at Lv4", E.egg_slots(s) == 2)
g.lay_clutch("quick")
g.lay_clutch("class")
check("two clutches laid", len(s["eggs"]) == 2)
g.lay_clutch("quick")
check("third clutch refused (nest full)", len(s["eggs"]) == 2)
for e in s["eggs"]:
    e["left"] = 0
    e["c"] = "golden"          # golden clutches never hatch empty, so the checks below are reliable
lv_before = s["fish"][0]["lv"]
before = s["bubbles"]
nx, ny = g.tank.nest_pos()
g.mouse_down(tuple(int(v) for v in g.to_screen(nx, ny - 4)), 1)
g.mouse_up(tuple(int(v) for v in g.to_screen(nx, ny - 4)), 1)
check("clicking nest hatches ready eggs", not s["eggs"] and s["bubbles"] > before)
check("hatching levels up the fish", s["fish"][0]["lv"] > lv_before)
check("baby fry appear", len(g.tank.fry) > 0)

# away summary after 5+ min idle
g.last_input = g.now - 400
g.note_input()
check("welcome-back summary after 5 min away", g.welcome is not None)

# new toys spawn and pay
for t in ("apple", "waterfall", "volcano", "fountain", "lilypad"):
    s["toys"][t] = dict(lv=1)
g.tank.sync()
earned = s["earned_total"]
for _ in range(1200):
    g.update(0.1)
check("tank runs with new toys", s["earned_total"] > earned)
g.draw()
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
