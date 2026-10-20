"""Headless check: panels can be dragged by their grip bar, position is remembered,
and fish stats still show (beside the panel) while a panel is open.
Run: python test_panels.py [shot.png]"""
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
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


g.ui.open("shop")
g.update(0.03)
g.draw()
pr = g.ui.panel_rect.copy()
grip = g.ui.grip_rect.center
g.mouse_down(grip, 1)
check("grabbing the grip starts a drag", g.ui.drag is not None)
target = (grip[0] - 600, grip[1] + 40)
g.mouse_motion(target, (-600, 40), (1, 0, 0))
g.mouse_up(target, 1)
g.update(0.03)
g.draw()
moved = g.ui.panel_rect
check("panel moved left", moved.x < pr.x - 300 or (g.compact and moved.y != pr.y))     # Mac: no room sideways
check("panel stays on screen", g.screen.get_rect().contains(moved))
check("position saved in settings", g.state["settings"].get("panel_pos") is not None)

# switching panels keeps the spot
g.ui.open("dex")
g.update(0.03)
g.draw()
check("fishdex opens at the same spot", g.ui.panel_rect.topleft == moved.topleft)

# hover a fish while the panel is open -> tooltip still drawn, not overlapping the panel
a = next(iter(g.tank.fish.values()))
pos = tuple(int(v) for v in g.to_screen(a.x, a.y))
g.mouse_motion(pos, (0, 0), (0, 0, 0))
g.tank.fish_at = lambda x, y: a          # pin the hover target (fish keep swimming)
drawn = []
orig_box = g.ui.box


def spy(scr, rect, *args, **kw):
    drawn.append(pygame.Rect(rect))
    return orig_box(scr, rect, *args, **kw)


g.ui.box = spy
g.draw()
g.ui.box = orig_box
tip = [r for r in drawn if r.size == (300, 150)]
check("fish stats shown with panel open", bool(tip))
check("fish stats don't overlap the panel", tip and (g.compact or not tip[0].colliderect(g.ui.panel_rect)))

g.ui.reset_panel_pos()
g.draw()
check("reset puts panel back by the tank", g.ui.panel_rect.right >= g.tank_rect.right - 10)
if len(sys.argv) > 1:
    g.ui.panel = "dex"
    g.state["settings"]["panel_pos"] = [700, 60]
    g.mouse_motion(pos, (0, 0), (0, 0, 0))
    g.draw()
    pygame.image.save(g.screen, sys.argv[1])
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
