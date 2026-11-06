"""Headless checks for 1.15.0: opening and closing menus doesn't rebuild the window (a rebuilt window starts out
black), and panels slide open and shut. Run: python test_v1150.py"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-11-10"
import pygame  # noqa: E402

from purrfin import economy as E, winutil  # noqa: E402
from purrfin.game import Game, KEY  # noqa: E402

winutil.monitors = lambda: [dict(x=0, y=0, w=1920, h=1040, primary=True)]
pygame.init()
ok = True
COMPACT = bool(os.environ.get("DA_COMPACT"))


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


rebuilds = [0]
real_set_mode = pygame.display.set_mode


def counting(*a, **k):
    rebuilds[0] += 1
    return real_set_mode(*a, **k)


pygame.display.set_mode = counting
moves = []
winutil.move = lambda h, *a: moves.append(a)
alphas = []
winutil.set_alpha = lambda h, key, a: alphas.append(a)


def new_game():
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
    g.relayout()
    g.apply_window(first=True)
    g.toasts.clear()
    g.draw()
    g.present()
    return g


# ---- no flash: the window isn't rebuilt or moved for normal menus
g = new_game()
for panel, tab in (("shop", "fish"), (None, None), ("settings", None), (None, None), ("dex", None), ("shop", "mine"),
                   ("shop", "spawn"), (None, None)):
    n, m, size = rebuilds[0], len(moves), g.screen.get_size()
    g.ui.panel = panel
    if tab:
        g.ui.tab = tab
    g.draw()
    g.present()
    g.draw()
    g.present()
    if not COMPACT:
        check(f"{panel or 'closing'}: the window isn't rebuilt or moved",
              rebuilds[0] == n and len(moves) == m and g.screen.get_size() == size)
    else:
        check(f"{panel or 'closing'}: Mac window fits what's open", True)
if not COMPACT:
    n = rebuilds[0]
    g.ui.minimize()
    g.draw()
    g.present()
    g.ui.restore()
    g.draw()
    g.present()
    check("hiding and showing the tank doesn't rebuild it either", rebuilds[0] == n)
    n = rebuilds[0]
    g.start_tank_name()
    g.draw()
    g.finish_rename(False)
    g.draw()
    check("nor do pop-up boxes", rebuilds[0] == n)
    r = g.ui.panel_rect
    g.ui.panel, g.ui.tab = "shop", "fish"
    g.draw()
    check("the Shop still fits", g.ui.panel_rect.w == 800 and g.ui.panel_rect.h >= 300 and g.ui.panel_rect.y >= 0)
    g.ui.panel = None
    g.draw()

# ---- a menu dragged somewhere gets the whole width, without showing black
if not COMPACT:
    g = new_game()
    g.ui.panel, g.ui.tab = "shop", "fish"
    g.draw()
    g.present()
    narrow = g.win_w
    check("a menu that hasn't been moved keeps the normal window", narrow < 1920)
    alphas.clear()
    grip = g.ui.grip_rect.center
    before_screen = g.win_x + g.ui.panel_rect.x
    g.mouse_down(grip, 1)
    check("grabbing it gives it the whole width", g.win_w == 1920)
    check("hidden until it's drawn", alphas and alphas[0] == 0 and g.reveal)
    g.draw()
    check("the menu hasn't jumped on screen", g.win_x + g.ui.panel_rect.x == before_screen)
    g.present()
    check("then shown", alphas[-1] == g.state["settings"]["opacity"] and not g.reveal)
    g.mouse_up(grip, 1)
    g.state["settings"]["panel_pos"] = [300, 20]
    n, m = rebuilds[0], len(moves)
    for panel in (None, "settings", None, "dex", None):
        g.ui.panel = panel
        g.draw()
        g.present()
        g.draw()
        g.present()
    check("after that, opening and closing menus never rebuilds it", rebuilds[0] == n and len(moves) == m)
    g.ui.set_mouse(None)
    g.draw()
    g.present()
    g.draw()
    check("and it still only redraws the tank's part when idle", g.update_rect is not None and g.update_rect.h < g.win_h)
    g.present()
    g.ui.reset_panel_pos()
    g.draw()
    g.present()
    check("resetting the menu's spot makes the window small again", g.win_w == narrow)

# ---- when the window really must change size (the Ring Tree), it's hidden until it has a picture
g = new_game()
g.state["pearls"] = 3
alphas.clear()
n = rebuilds[0]
g.ui.open_rings()
g.draw()
check("the Ring Tree does need a bigger window", rebuilds[0] == n + 1)
check("so it's see-through until drawn", alphas and alphas[0] == 0 and g.reveal)
check("not shown black in between", g.state["settings"]["opacity"] not in alphas)
g.present()
check("and appears once its picture is ready", alphas[-1] == g.state["settings"]["opacity"] and not g.reveal)
g.ui.open_rings()
g.draw()
g.present()
check("the same on the way back", alphas[-1] == g.state["settings"]["opacity"] and not g.reveal)

# ---- only the tank's part is redrawn when nothing is open
if not COMPACT:
    g = new_game()
    g.ui.set_mouse(None)
    g.draw()
    g.present()
    g.draw()
    check("idle: only part of the window is sent to the screen", g.update_rect is not None
          and g.update_rect.h < g.win_h and g.update_rect.contains(g.tank_rect))
    g.present()
    hud_top = int(g.ui.hud_top() * g.ui.k)
    check("buttons are in that part", g.update_rect.top <= hud_top)
    g.toast("one")
    g.toast("two")
    g.toast("three")
    g.toast("four")
    g.draw()
    check("so are messages", g.update_rect.top <= hud_top - 4 * 34)
    g.toasts.clear()
    g.ui.set_mouse((g.tank_rect.centerx, g.tank_rect.centery))
    g.draw()
    check("with the mouse over it, tips can go anywhere", g.update_rect is None)
    g.ui.set_mouse(None)
    g.ui.panel, g.ui.tab = "shop", "fish"
    g.draw()
    check("a menu sends everything", g.update_rect is None)
    g.ui.panel = None
    g.draw()
    g.draw()
    panel_area = g.screen.get_at((g.ui.tank.right - 400, 40))[:3]
    check("nothing is left behind where the menu was", panel_area == KEY)

# ---- the slide
now = [100.0]
g = new_game()
ui = g.ui
ui.animate = True
ui.clock = lambda: now[0]
BG_AT = (0, 0)


def filled(rect):
    """how far the panel reaches, by looking at the pixels down its middle"""
    x = rect.centerx
    return sum(1 for y in range(rect.y, min(rect.bottom, g.screen.get_height())) if g.screen.get_at((x, y))[:3] != KEY)


ui.panel, ui.tab = "shop", "themes"
g.draw()
rr = ui.panel_rect.copy()
if not COMPACT:
    check("it starts closed", filled(rr) < rr.h * 0.1)
heights = []
for dt in (0.03, 0.03, 0.03, 0.03, 0.04):
    now[0] += dt
    g.draw()
    heights.append(filled(rr))
if not COMPACT:
    check(f"it slides out smoothly {heights}", heights == sorted(heights) and heights[0] < heights[-1])
    check("and ends fully open", heights[-1] == rr.h)
    check("it comes from the buttons upward", g.screen.get_at((rr.centerx, rr.bottom - 3))[:3] != KEY)
hit_before = [h for h in ui.hits if rr.contains(h[0])]
check("its buttons work straight away", hit_before)
now[0] += 1
g.draw()
ui.panel = None
g.draw()
check("closing: the buttons are gone at once", not [h for h in ui.hits if h[0].h == 30 and rr.contains(h[0])])
check("it's sliding away", ui.closing is not None)
shut = []
for dt in (0.0, 0.03, 0.03, 0.03, 0.05):
    now[0] += dt
    g.draw()
    shut.append(filled(rr))
if not COMPACT:
    check(f"it slides back in {shut}", shut == sorted(shut, reverse=True) and shut[-1] == 0)
check("and is finished", ui.closing is None)
g.draw()

# reopening halfway through a close is fine
ui.panel = "dex"
g.draw()
now[0] += 1
g.draw()
ui.panel = None
g.draw()
now[0] += 0.02
ui.panel = "settings"
g.draw()
check("reopening mid-slide just opens", ui.closing is None and ui.panel_rect)
now[0] += 1
g.draw()
look = ui.panel_rect.copy()
ui.panel = "shop"
ui.tab = "fish"
g.draw()
if not COMPACT:
    check("going straight from one menu to another doesn't slide", filled(ui.panel_rect) == ui.panel_rect.h)
now[0] += 1

# the Ring Tree slides too, and keeps its big window until it's gone
g2 = new_game()
g2.state["pearls"] = 3
g2.ui.animate = True
g2.ui.clock = lambda: now[0]
g2.ui.open_rings()
g2.draw()
now[0] += 1
g2.draw()
big = g2.win_h
g2.ui.open_rings()
g2.draw()
check("the Ring Tree's window stays big while it slides shut", g2.win_h == big and g2.ui.closing)
now[0] += 1
g2.draw()
g2.draw()
check("then goes back", g2.win_h < big and not g2.ui.closing)

# things that end a panel some other way
g3 = new_game()
g3.ui.animate = True
g3.ui.clock = lambda: now[0]
g3.ui.panel, g3.ui.tab = "shop", "fish"
g3.draw()
now[0] += 1
g3.draw()
g3.ui.minimize()
g3.draw()
check("hiding the tank drops the panel straight away", g3.ui.closing is None)
g3.ui.restore()
g3.draw()
g3.ui.panel, g3.ui.tab = "shop", "fish"
g3.draw()
now[0] += 1
g3.draw()
g3.ui.panel = None
E.earn(g3.state, 1)
g3.draw()
g3.state["settings"]["uiscale"] = 1.5
g3.relayout()
g3.draw()
now[0] += 1
g3.draw()
check("changing the UI size mid-slide is fine", g3.ui.closing is None)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
