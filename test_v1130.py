"""Headless checks for 1.13.0: paste into the code box, stretch the tank by its edges, money numbers can be
turned off and never show through the Ring Tree. Run: python test_v1130.py [screenshot_dir]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-11-10"
os.environ["DA_ONLINE_URL"] = "http://127.0.0.1:9"     # nothing there: this test never needs an answer
import pygame  # noqa: E402

from purrfin import economy as E, share, winutil  # noqa: E402
from purrfin.game import Game  # noqa: E402

MONS = [dict(x=0, y=0, w=1920, h=1040, primary=True), dict(x=1920, y=0, w=1280, h=984, primary=False)]
winutil.monitors = lambda: [dict(m) for m in MONS]
cursor = [0, 0]
held = [True]
clip = [""]
winutil.cursor_pos = lambda: tuple(cursor)
winutil.left_button_down = lambda: held[0]
winutil.get_clipboard = lambda: clip[0]
winutil.move = lambda *a, **k: None
pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def new_game():
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
    g.relayout()
    g.apply_window(first=True)
    g.toasts.clear()
    return g


def key(g, k, mod=0):
    g.key_down(pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod))


def box(g):
    return g.win_x + g.tank_rect.x, g.win_x + g.tank_rect.right, g.win_y + g.tank_rect.y


def pull(g, side, to):
    left, right, _ = box(g)
    cursor[:] = [right - 5 if side == "right" else left + 5, g.win_y + g.tank_rect.centery]
    held[0] = True
    g.begin_tank_stretch(side)
    cursor[0] = to + (5 if side == "left" else -5)     # the edge goes to `to`
    for _ in range(12):
        g.now += 0.2
        g.update(0.0)
    held[0] = False
    g.update(0.0)
    g.draw()


# ---- paste
g = new_game()
g.start_code_entry()
g.draw()
clip[0] = "my code is 482913 ok"
key(g, pygame.K_v)
check("V on its own does nothing", g.rename_text == "")
key(g, pygame.K_v, pygame.KMOD_LCTRL)
check("Ctrl+V pastes just the 6 digits", g.rename_text == "482913")
g.rename_text = ""
key(g, pygame.K_v, pygame.KMOD_LMETA)
check("so does Cmd+V on a Mac", g.rename_text == "482913")
found = {}
orig = g.ui.button


def spy(scr, rect, label, cb, *a, **kw):
    found[label] = cb
    return orig(scr, rect, label, cb, *a, **kw)


g.ui.button = spy
g.draw()
g.ui.button = orig
check("there's a Paste button too", "Paste" in found and "Remove name" not in found)
g.rename_text = ""
found["Paste"]()
check("and it works", g.rename_text == "482913")
if shots:
    os.makedirs(shots, exist_ok=True)
    g.draw()
    pygame.image.save(g.screen, os.path.join(shots, "paste_box.png"))
for bad in ("hello", "12345", "1234567", "012345", ""):
    g.rename_text = ""
    clip[0] = bad
    g.paste_tank_code()
    check(f"not a code ({bad!r}): stays empty", g.rename_text == "")
clip[0] = None
g.paste_tank_code()
check("an empty clipboard is fine", g.rename_text == "")
o = E.new_state()
o["tank_name"] = "Long Code Tank"
clip[0] = share.encode(o)
g.paste_tank_code()
check("pasting a long code visits it", g.visiting and g.visiting["tank_name"] == "Long Code Tank" and g.renaming is None)
g.leave_visit()
g.start_tank_name()
clip[0] = "482913"
key(g, pygame.K_v, pygame.KMOD_LCTRL)
check("other name boxes are left alone", g.rename_text == "")
g.finish_rename(False)

# ---- the handles
g = new_game()
g.draw()
check("no handles until the mouse is near", not any(t[1][0] == "Stretch the tank" for t in g.ui.tips))
g.ui.set_mouse((g.tank_rect.centerx, g.tank_rect.centery))
g.draw()
zones = [t[0] for t in g.ui.tips if t[1][0] == "Stretch the tank"]
check("one on each side when it is", len(zones) == 2 and zones[0].x == g.ui.tank.x and zones[1].right == g.ui.tank.right)
if shots:
    pygame.image.save(g.screen, os.path.join(shots, "handles.png"))
cursor[:] = [g.win_x + zones[0].centerx, g.win_y + zones[0].centery]
held[0] = True
g.mouse_down(zones[0].center, 1)
check("pressing one starts stretching", g.tank_stretch and g.tank_stretch["side"] == "left")
g.mouse_motion(zones[0].center, (0, 0), (1, 0, 0))
check("and doesn't count as moving the tank", not g.tank_move and not g.tank_press)
held[0] = False
g.mouse_up(zones[0].center, 1)
check("letting go stops", not g.tank_stretch)

# ---- docked bottom right: pull the left edge
g = new_game()
l0, r0, y0 = box(g)
pull(g, "left", l0 - 300)
l1, r1, y1 = box(g)
check("pulling left makes it wider", abs((l0 - 300) - l1) <= g.S and r1 == r0 and y1 == y0)
check("it stays docked", g.tank_pos() is None)
check("the fish tank fits its new size", g.tank.w == g.tank_rect.w // g.S)
check("Options shows it", abs(g.state["settings"]["width"] - (r1 - l1) / 1920) < 0.01)
w_before = g.state["settings"]["width"]
g.relayout()
check("nothing creeps when it's laid out again", box(g) == (l1, r1, y1))
g.save()
g2 = Game(save_path=g.save_path)
g2.apply_window(first=True)
g2.relayout()
check("still that size next time", box(g2) == (l1, r1, y1))
pull(g, "left", l1 + 200)
check("pulling back makes it narrower", abs(box(g)[0] - (l1 + 200)) <= g.S and box(g)[1] == r1)
pull(g, "left", 1900)
check("it can't get too small", box(g)[1] - box(g)[0] >= 480 - g.S)
pull(g, "left", -5000)
check("or wider than the screen", box(g)[0] == 0 and box(g)[1] == 1920)

# ---- moved somewhere: the far edge stays put
g = new_game()
g.state["settings"]["tank_pos"] = [900, 500]
g.relayout()
l0, r0, y0 = box(g)
pull(g, "right", r0 + 250)
l1, r1, y1 = box(g)
check("pulling the right edge keeps the left edge still", l1 == l0 and abs(r1 - (r0 + 250)) <= g.S and y1 == y0)
pull(g, "left", l1 - 100)
l2, r2, y2 = box(g)
check("and the other way round", r2 == r1 and abs(l2 - (l1 - 100)) <= g.S and y2 == y0)
pull(g, "right", 99999)
check("it stops at the edge of the monitor", 1920 - g.S < box(g)[1] <= 1920 and box(g)[0] == l2)

# ---- docked, pulling the edge against the wall of the screen
g = new_game()
l0, r0, y0 = box(g)
pull(g, "right", r0 - 60)
l1, r1, y1 = box(g)
check("pulling the right edge in leaves the left edge still", l1 == l0 and y1 == y0 and (g.compact or abs(r1 - (r0 - 60)) <= g.S))
check("and the tank stays low on the screen", y1 + g.tank_rect.h == 1040)

# ---- no stretching in the wrong moments
g = new_game()
g.visiting = dict(fish=[], tank_name="x")
g.begin_tank_stretch("left")
check("not while visiting", not g.tank_stretch)
g.visiting = None
g.minimized = True
g.begin_tank_stretch("left")
check("not while hidden", not g.tank_stretch)
g.minimized = False
g.ui.panel, g.ui.tab = "shop", "fish"
g.draw()
cursor[:] = [g.win_x + g.tank_rect.x, 900]
held[0] = True
g.begin_tank_stretch("left")
check("a panel closes while you stretch", g.ui.panel is None)
held[0] = False
g.update(0.0)

# ---- numbers
g = new_game()
g.tank.float_text(g.tank.w / 2, 20, "+123")
g.tank.float_text(g.tank.w / 2 + 20, 20, "Lv 5!")
drawn = []
real = g.ui.f_norm.render


def spy_render(text, *a, **k):
    drawn.append(text)
    return real(text, *a, **k)


g.ui.f_norm.render = spy_render
g.draw()
check("money numbers show by default", "+123" in drawn and "Lv 5!" in drawn)
buttons = {}
g.change_setting("money_numbers", False)
drawn.clear()
g.draw()
check("off: no money numbers", "+123" not in drawn)
check("but Lv 5! still shows", "Lv 5!" in drawn)
g.save()
check("the setting is remembered", Game(save_path=g.save_path).state["settings"]["money_numbers"] is False)
g.change_setting("money_numbers", True)
g.ui.f_norm.render = real
g.ui.panel = "settings"
orig = g.ui.button
labels = []
g.ui.button = lambda scr, rect, label, *a, **kw: labels.append(label) or orig(scr, rect, label, *a, **kw)
g.draw()
g.draw()
g.ui.button = orig
check("Options has On and Off for it", labels.count("On") >= 2)

# ---- numbers vs the Ring Tree: look at the actual pixels
g = new_game()
s = g.state
s["pearls"] = 5
g.ui.open_rings()
g.draw()
g.draw()
g.tank.texts.clear()
g.draw()
before = pygame.image.tobytes(g.screen.subsurface(g.ui.panel_rect), "RGB")
r = g.ui.rings
g.ui.f_norm.render = real
old = r.draw_water
r.draw_water = lambda scr, dt: None
for _ in range(20):
    g.tank.float_text(g.tank.w / 2, 15, "+888888888")
g.tank.update = lambda dt: None
g.draw()
inside = g.ui.panel_rect.colliderect(g.ui.tank)
surf = g.screen.copy()
r.draw_water = old
g.tank.texts.clear()
g.draw()
clean = g.screen.copy()
over = pygame.Rect(g.ui.tank).clip(g.ui.panel_rect)
order = []
real_floaters, real_panel = g.ui.draw_floaters, g.ui.draw_panel
g.ui.draw_floaters = lambda scr: order.append("numbers") or real_floaters(scr)
g.ui.draw_panel = lambda scr: order.append("panel") or real_panel(scr)
g.draw()
check("numbers are drawn before the panels, so panels cover them", order == ["numbers", "panel"])
check("and the Ring Tree does sit over the tank", inside and over.w > 0)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
