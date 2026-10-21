"""Headless checks for 1.6.1: fish earn a real share again (bubble power boosts fish, bubbles unchanged),
and buff timers never go off the edge of the window. Run: python test_v161.py [screenshot_dir]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


# ---- economy
s = E.new_state()
check("a new game: no boost yet (early pacing unchanged)", E.fish_boost(s) < 1.5)
base_pop = E.pop_value(s)
s["upgrades"].update(magnet=50, polish=30, bubbler=15, lucky=12)
for sp in ("bronze", "panda", "pictus"):
    E.add_fish(s, sp)
check("bubbles still use the plain fish rate (not boosted)",
      abs(E.pop_value(s) - max(3.0, E.base_income(s) * 12) * E.bubble_power(s)) < 1e-6 * E.pop_value(s))
check("bubble values unchanged from before",
      abs(E.pop_value(s) - max(3.0, E.base_income(s) * 12) * (1 + 0.35 * 50) * (1 + 30)) < 1e-6 * E.pop_value(s))
boost = E.fish_boost(s)
check(f"late game, bubble power boosts fish a lot (x{boost:.0f})", boost > 100)
fish = E.income(s)
bubbles = E.pop_value(s) * (1 + 9 * E.golden_chance(s)) / E.pop_interval(s)
share = fish / (fish + bubbles)
check(f"fish are about a third of what you'd get popping every bubble ({share * 100:.0f}%)", 0.25 < share < 0.45)

# ---- timers on screen
g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
st = g.state
E.earn(st, 1e9)
st["upgrades"].update(rub=1, hatchery=2, jar=2)
for sp in ("bronze", "panda"):
    E.add_fish(st, sp)
st["buffs"] = {"double": 88.0, "frenzy": 26.0, "bliss": 45.0}
st["eggs"] = [dict(c="quick", left=0, total=60, inc=1.0)]
g.toasts.clear()
drawn = []
orig = g.ui.box
g.ui.box = lambda scr, rect, *a, **k: drawn.append(pygame.Rect(rect)) or orig(scr, rect, *a, **k)
g.draw()
g.ui.box = orig
area = pygame.Rect(0, 0, g.ui.W, g.ui.H)
off = [r for r in drawn if not area.contains(r)]
check("nothing in the HUD is drawn off the window (timers included)", not off)
if shots:
    os.makedirs(shots, exist_ok=True)
    r = g.tank_rect
    top = max(0, r.y - 110)
    pygame.image.save(g.screen.subsurface(pygame.Rect(0, top, g.win_w, r.y + 40 - top)), os.path.join(shots, "hud_timers.png"))
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
