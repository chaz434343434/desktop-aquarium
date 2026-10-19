"""Headless check for day/night, visitors, renaming, shiny fish and tank themes.
Run: python test_features.py [screenshot_dir]"""
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
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def shot(name):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.draw()
        r = g.tank_rect
        top = max(0, r.y - 420)
        pygame.image.save(g.screen.subsurface((max(0, r.x - 500), top, min(g.win_w, r.w + 500), g.win_h - top)),
                          os.path.join(shots, name + ".png"))


E.earn(s, 1e7)
for sp in ("bronze", "panda", "pictus"):
    E.add_fish(s, sp, shiny=False)
g.tank.sync()

# ---- day / night
g.tank.hour_override = 12
check("noon has no tint", g.tank.tint_surface() is None)
g.tank.hour_override = 23
d = g.tank.daylight()
check("night tints the water dark blue", d and d[1] > 80 and d[0][2] > d[0][0])
g.tank.hour_override = 17.5
d = g.tank.daylight()
check("late afternoon is warm", d and d[0][0] > d[0][2])
shot("night") if not g.tank.hour_override == 23 else None
g.tank.hour_override = 22
shot("night")
g.change_setting("daynight", False)
check("'always day' turns tint off", g.tank.tint_surface() is None)
g.change_setting("daynight", True)
g.tank.hour_override = 12

# ---- visitors
g.tank.visit_timer = 0
g.update(0.05)
v = g.tank.visitor
check("a visitor shows up", v is not None)
for _ in range(60):
    g.update(0.05)
v = g.tank.visitor
v["x"] = g.tank.w / 2
v["pause"] = 99
shot("visitor")
before = s["bubbles"]
g.mouse_down(tuple(int(c) for c in g.to_screen(v["x"], v["y"] - 3)), 1)
check("clicking the visitor gives scales", s["bubbles"] > before and g.tank.visitor is None)

# ---- shiny
f = E.add_fish(s, "panda", shiny=True)
g.tank.sync()
check("shiny earns double", abs(E.fish_rate(s, f) - 2 * E.fish_rate(s, dict(f, shiny=False))) < 1e-9)
check("shiny recorded in fishdex", "panda" in s["shinies"])
E.earn(s, 1e7)
s["upgrades"]["tank"] = 6
import random  # noqa: E402
random.seed(1)
shinies = sum(E.add_fish(dict(s, fish=[], next_uid=1, shinies=[], dex=[]), "bronze")["shiny"] for _ in range(4000))
check(f"shiny chance about 4% ({shinies / 40:.1f}%)", 2.5 < shinies / 40 < 5.5)
a = g.tank.fish[f["uid"]]
a.x, a.y = g.tank.w * 0.5, 30

# ---- rename via right-click + typing
g.tank.fish_at = lambda x, y: a
g.mouse_down(tuple(int(c) for c in g.to_screen(a.x, a.y)), 3)
check("right-click opens rename", g.renaming is f)
for _ in range(20):
    g.key_down(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
g.text_input("Mr. Whiskers!")
shot("rename")
g.key_down(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
check("typed name saved", f["name"] == "Mr. Whiskers!" and g.renaming is None)
g.start_rename(f)
g.text_input("zzzz")
g.key_down(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
check("Esc cancels rename", f["name"] == "Mr. Whiskers!")
g.start_rename(f)
g.text_input("x" * 40)
check("names capped at 14 chars", len(g.rename_text) <= 14)
g.finish_rename(False)

# ---- themes
inc0 = E.income(s)
E.earn(s, 1e9)
g.theme_action("blackwater")
check("buying a theme equips it", s["theme"] == "blackwater" and "blackwater" in s["themes"])
check("themes give +5%", abs(E.income(s) / inc0 - 1.05) < 0.01)
g.ui.panel, g.ui.tab = "shop", "themes"
shot("themes")
g.ui.panel = None
g.theme_action("classic")
check("switching back is free", s["theme"] == "classic")
keep = E.new_state(keep=dict(s))
check("themes + shinies survive Spawning Season", "blackwater" in keep["themes"] and "panda" in keep["shinies"])

g.tank.fish_at = type(g.tank).fish_at.__get__(g.tank)
g.ui.panel = "dex"
shot("dex")
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
