"""Headless check: egg timers keep counting down while the game is closed.
Simulates: lay eggs -> close the game -> come back later -> reopen."""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
path = os.path.join(tempfile.mkdtemp(), "save.json")
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def away(minutes):
    """pretend the game was closed this long ago"""
    with open(path, encoding="utf-8") as fh:
        s = json.load(fh)
    s["last_time"] -= minutes * 60
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(s, fh)


g = Game(save_path=path, fresh=True)
g.apply_window(first=True)
s = g.state
E.earn(s, 1e6)
s["upgrades"]["hatchery"] = 4
g.lay_clutch("class")
g.lay_clutch("quick")
big, small = s["eggs"]
big_left, small_left = big["left"], small["left"]
g.save()                                           # close the game
pygame.display.quit()

for mins, label in ((0.5, "30 seconds"), (20, "20 minutes")):
    away(mins)
    pygame.display.init()
    g = Game(save_path=path)                       # open it again
    g.apply_window(first=True)
    b, sm = g.state["eggs"]
    print(f"   after {label}: big egg {big_left:.0f}s -> {b['left']:.0f}s, small {small_left:.0f}s -> {sm['left']:.0f}s")
    check(f"eggs counted down while closed for {label}", b["left"] <= big_left - mins * 60 + 2)
    big_left, small_left = b["left"], sm["left"]
    g.save()
    pygame.display.quit()

check("small egg is ready after being away long enough", small_left == 0)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
