"""Headless check of Options > UI size (100/150/200%): clicks, dragging and scrolling still
land in the right place, and the window grows to fit. Run: python test_uiscale.py [shot_dir]"""
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
E.earn(g.state, 5e5)
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def screen_pt(ui_pt, k):
    return (int(ui_pt[0] * k) + 1, int(ui_pt[1] * k) + 1)


base_h = g.win_h
for k in (1.0, 1.5, 2.0):
    g.change_setting("uiscale", k)
    g.toasts.clear()
    g.ui.panel, g.ui.tab = "shop", "fish"
    g.state["settings"]["panel_pos"] = None
    g.draw()
    g.draw()
    tag = f"{int(k * 100)}%"
    check(f"{tag}: window is tall enough ({g.win_h}px)", g.win_h >= min(int(base_h * k), g.mon["h"]))
    pr = g.ui.panel_rect
    check(f"{tag}: shop panel fits on screen", pr.y >= 0 and pr.right * k <= g.win_w + 1)
    if shots:
        os.makedirs(shots, exist_ok=True)
        top = int(max(0, pr.y - 10) * k)
        pygame.image.save(g.screen.subsurface((0, top, g.win_w, g.win_h - top)),
                          os.path.join(shots, f"ui_{int(k * 100)}.png"))
    # drag the panel by its grip (screen coordinates in, UI coordinates inside)
    grip = g.ui.grip_rect.center
    g.mouse_down(screen_pt(grip, k), 1)
    g.mouse_motion(screen_pt((grip[0] - 100, grip[1]), k), (-100, 0), (1, 0, 0))
    g.mouse_up(screen_pt((grip[0] - 100, grip[1]), k), 1)
    g.draw()
    check(f"{tag}: dragging the panel follows the mouse",
          abs(g.ui.panel_rect.x - (pr.x - 100)) <= 2 or (g.compact and g.ui.panel_rect.x <= pr.x and g.ui.panel_rect.x >= 0))
    # scroll the Fishdex (40 catfish, always long enough to scroll) with the wheel
    g.ui.panel = "dex"
    g.draw()
    g.ui.wheel(screen_pt(g.ui.panel_rect.center, k), -2)
    check(f"{tag}: mouse wheel scrolls the panel", g.ui.scroll.get(("dex", g.ui.tab), 0) > 0)
    # click the red close button
    pr = g.ui.panel_rect
    g.mouse_down(screen_pt((pr.right - 25, pr.y + 23), k), 1)
    check(f"{tag}: clicking the close button closes the panel", g.ui.panel is None)
    g.ui.scroll.clear()

print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
