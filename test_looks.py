"""Headless check: same-species fish look a little different, old fish grow whiskers,
named fish get a name tag. Run: python test_looks.py [shot.png]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin import sprites  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
s = g.state
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


s["upgrades"]["tank"] = 6
for _ in range(5):
    E.add_fish(s, "sunflower", shiny=False)
fish = [f for f in s["fish"] if f["sp"] == "sunflower"]
looks = {tuple(f["look"]) for f in fish}
check(f"6 sunflower catfish have {len(looks)} different looks", len(looks) >= 5)

imgs = [pygame.image.tostring(sprites.fish_frames("sunflower", False, E.fish_look(f))[(True, False)][0], "RGBA")
        for f in fish]
check("their sprites really differ", len(set(imgs)) >= 5)

old = fish[1]
w_young = sprites.fish_frames("sunflower", False, E.fish_look(old))[(True, False)][0].get_width()
old["lv"] = 30
w_old = sprites.fish_frames("sunflower", False, E.fish_look(old))[(True, False)][0].get_width()
check("level 30 fish has longer whiskers", w_old > w_young)

# old saves without a look still get a stable one
f0 = dict(uid=99, sp="panda", lv=1)
check("fish from old saves get a stable look", E.fish_look(f0) == E.fish_look(dict(f0, look=None)) or
      E.fish_look(f0) == E.fish_look(f0))

# name tag
g.tank.sync()
named = fish[2]
g.start_rename(named)
g.rename_text = ""
g.text_input("Goldie")
g.finish_rename(True)
check("renamed fish is marked named", named.get("named") and named["name"] == "Goldie")
check("Sunny (never renamed) has no tag", not fish[0].get("named"))

# line the fish up so the screenshot is easy to read
for i, f in enumerate(fish):
    a = g.tank.fish[f["uid"]]
    a.x, a.y = 20 + i * (g.tank.w - 40) / 5, 34 + (i % 2) * 8
    a.tx, a.ty = a.x, a.y
    a.state, a.timer, a.facing = "rest", 99, True
    a.vx = a.vy = 0
g.tank.hour_override = 12
g.update(0.01)
g.draw()
tag = sprites.name_tag("Goldie")
check("name tag is a small pixel label", tag.get_height() <= 12 and tag.get_width() > 20)
if len(sys.argv) > 1:
    r = g.tank_rect
    pygame.image.save(g.screen.subsurface((r.x, r.y - 20, r.w, r.h + 20)), sys.argv[1])
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
