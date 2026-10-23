"""Leaves the game running for hours of game time (real Game.update at 15 frames a second, drawing
regularly) with eggs, visitors, toys and lots of fish, and checks nothing keeps piling up.
Run: python check_longrun.py [hours]"""
import gc
import os
import sys
import tempfile
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from purrfin import economy as E, sprites  # noqa: E402
from purrfin.data import SPECIES, TOYS  # noqa: E402
from purrfin.game import Game  # noqa: E402

HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 4
pygame.init()
g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
s = g.state
E.earn(s, 1e40)
s["upgrades"].update(tank=12, hatchery=7, autonest=1, jar=5, bubbler=15, feeder=5, light=10)
for sp in SPECIES[:30]:
    E.add_fish(s, sp["id"])
for t in TOYS[:35]:
    s["toys"][t["id"]] = dict(lv=5)
g.tank.sync()
for c in ("quick", "quick", "class"):
    g.lay_clutch(c)


def sizes():
    t = g.tank
    return dict(parts=len(t.parts), texts=len(t.texts), decor=len(t.decor), pops=len(t.pops), fry=len(t.fry),
                rings=len(t.rings), toasts=len(g.toasts), rate_hist=len(g.rate_hist), fish=len(s["fish"]),
                pending=len(s.get("pending", [])), sprite_cache=len(sprites._cache), scaled=len(sprites._scaled),
                font=sum(len(f._cache) for f in (g.ui.f_small, g.ui.f_norm, g.ui.f_big)), objects=len(gc.get_objects()))


dt = 1 / 15
steps = int(HOURS * 3600 / dt)
t0 = time.time()
snap = []
for i in range(steps):
    g.update(dt)
    if i % 45 == 0:                       # draw 3x a second of game time (enough to exercise drawing)
        g.draw()
    if i % 450 == 0:                      # the player comes by now and then
        g.mouse_down(tuple(int(v) for v in g.to_screen(40, 30)), 1)
        g.mouse_up(tuple(int(v) for v in g.to_screen(40, 30)), 1)
        if s.get("pending"):
            g.rehome(s["pending"][0]["uid"]) if hasattr(g, "rehome") else None
            s["pending"] = []
    if i % (steps // 8) == 0:
        gc.collect()
        snap.append((round(i * dt / 3600, 2), sizes()))
gc.collect()
snap.append((HOURS, sizes()))
print(f"{HOURS}h of game time in {time.time() - t0:.0f}s real time")
keys = list(snap[0][1])
print("hours  " + " ".join(f"{k[:9]:>9s}" for k in keys))
for h, sz in snap:
    print(f"{h:5.2f}  " + " ".join(f"{sz[k]:9d}" for k in keys))
first, last = snap[1][1], snap[-1][1]
grow = {k: (first[k], last[k]) for k in keys if last[k] > max(first[k] * 1.5, first[k] + 200)}
print("KEEPS GROWING:", grow if grow else "nothing")
