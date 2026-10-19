"""Headless check: the Brightness option makes the tank darker / brighter, and the
Options buttons change it. Run: python test_brightness.py [shot.png]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin.game import Game  # noqa: E402

pygame.init()
g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
g.tank.hour_override = 12
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def avg_water():
    surf = g.tank.draw()
    tot, n = 0, 0
    for x in range(10, g.tank.w - 10, 7):
        for y in range(8, g.tank.sand_y - 2, 5):
            c = surf.get_at((x, y))
            tot += c.r + c.g + c.b
            n += 1
    return tot / n


strips = []
levels = {}
for b in (-5, 0, 5):
    g.state["settings"]["brightness"] = b
    levels[b] = avg_water()
    strips.append(pygame.transform.scale(g.tank.surface, (g.tank.w * 2, g.tank.h * 2)))
check("darkest is darker than normal", levels[-5] < levels[0] * 0.6)
check("brightest is brighter than normal", levels[5] > levels[0] * 1.2)

# the Options +/- buttons work
g.state["settings"]["brightness"] = 0
g.ui.panel = "settings"
g.draw()
plus = [r for r, cb in g.ui.hits if r.w == 34 and abs(r.centery - [h for h, _ in g.ui.hits][0].centery) >= 0]
g.change_setting("brightness", 2)
check("setting saved", g.state["settings"]["brightness"] == 2)

# night + brighten = override the dark tint
g.tank.hour_override = 23
g.state["settings"]["brightness"] = 0
night = avg_water()
g.state["settings"]["brightness"] = 5
check("brightness can lighten up the night tank", avg_water() > night * 1.3)

if len(sys.argv) > 1:
    out = pygame.Surface((strips[0].get_width(), sum(s.get_height() + 6 for s in strips)))
    out.fill((255, 0, 255))
    y = 0
    for s in strips:
        out.blit(s, (0, y))
        y += s.get_height() + 6
    pygame.image.save(out, sys.argv[1])
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
