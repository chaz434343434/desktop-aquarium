"""Headless checks for the compact window the Mac version uses (no see-through windows there):
short around the tank, tall while a panel is open. Run: python test_compact.py [screenshot_dir]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_COMPACT"] = "1"
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


for k in (1.0, 1.5):
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
    g.state["settings"]["uiscale"] = k
    g.layout()
    g.apply_window(first=True)
    E.earn(g.state, 1e5)
    g.toasts.clear()
    g.draw()
    short = g.screen.get_size()
    full_h = int(660 * k)
    check(f"[ui {k}] short window around the tank ({short[0]}x{short[1]})", short[1] < full_h and short[0] < g.mon["w"])
    check(f"[ui {k}] tank sits at the bottom of the window", g.tank_rect.bottom == short[1])
    check(f"[ui {k}] tank fully inside the window", g.screen.get_rect().contains(g.tank_rect))
    check(f"[ui {k}] window bottom on the screen bottom", g.win_y + g.win_h == g.mon["y"] + g.mon["h"])
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.toast("Welcome! Pet Sunny and pop bubbles to collect scales.")
        g.draw()
        pygame.image.save(g.screen, os.path.join(shots, f"compact_short_{k}.png"))
    g.ui.open_tab("fish")
    g.draw()
    g.draw()
    tall = g.screen.get_size()
    check(f"[ui {k}] opening the shop makes it tall ({tall[1]})", tall[1] == min(full_h, g.mon["h"]))
    pr = g.ui.panel_rect
    check(f"[ui {k}] shop panel fits in the window", pr is not None and
          pygame.Rect(0, 0, g.ui.W, g.ui.H).contains(pr))
    if shots:
        pygame.image.save(g.screen, os.path.join(shots, f"compact_tall_{k}.png"))
    g.ui.open_tab("fish")
    g.draw()
    check(f"[ui {k}] closing it shrinks back", g.screen.get_size() == short)
    g.ui.minimize()
    g.draw()
    check(f"[ui {k}] hidden tank = tiny window", g.screen.get_size()[1] <= 50 * k)
    g.ui.restore()
    g.draw()
    check(f"[ui {k}] and back", g.screen.get_size() == short)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
