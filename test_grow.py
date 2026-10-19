"""Headless check: hatched baby catfish start small and grow up (also while the game is closed).
Run: python test_grow.py [screenshot_dir]"""
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
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def shot(g, name, baby):
    if not shots:
        return
    os.makedirs(shots, exist_ok=True)
    a = g.tank.fish[baby["uid"]]
    g.mouse_low = (a.x, a.y)
    g.ui.mouse = tuple(int(v) for v in g.to_screen(a.x, a.y))
    g.draw()
    r = g.tank_rect
    top = max(0, r.y - 200)
    pygame.image.save(g.screen.subsurface((r.x, top, r.w, g.win_h - top)), os.path.join(shots, name + ".png"))


g = Game(save_path=path, fresh=True)
g.apply_window(first=True)
s = g.state
s["upgrades"].update(hatchery=1, tank=3)
E.add_fish(s, "sunflower", shiny=False)
g.tank.sync()
s["eggs"] = [dict(c="golden", left=0, total=1, inc=1)]
g.hatch_ready()
babies = [f for f in s["fish"] if f.get("hatched")]
check("a baby hatched into the tank", len(babies) == 1)
baby = babies[0]
a = g.tank.fish[baby["uid"]]
grown_rate = E.fish_rate(s, dict(baby, grow=0))
check("baby starts as a tiny fry (30% size)", a.size_k() == 0.3)
check("baby earns less while small", abs(E.fish_rate(s, baby) - grown_rate * 0.25) < 1e-9)
small_w = a.rect().w
for _ in range(1200):              # 120 seconds
    g.update(0.1)
check(f"half way: about 65% size (k={a.size_k()})", 0.6 <= a.size_k() <= 0.7)
check("it got bigger", a.rect().w > small_w)
a.x, a.y = g.tank.w * 0.5, 30
shot(g, "growing", baby)

g.save()                            # close the game for 90 seconds
pygame.display.quit()
with open(path, encoding="utf-8") as fh:
    sv = json.load(fh)
left_before = [f for f in sv["fish"] if f.get("hatched")][0]["grow"]
sv["last_time"] -= 90
with open(path, "w", encoding="utf-8") as fh:
    json.dump(sv, fh)
pygame.display.init()
g = Game(save_path=path)
g.apply_window(first=True)
s = g.state
baby = [f for f in s["fish"] if f.get("hatched")][0]
check(f"kept growing while closed ({left_before:.0f}s -> {baby['grow']:.0f}s)", baby["grow"] <= left_before - 89)

g.toasts.clear()
for _ in range(400):
    g.update(0.1)
    if "grow" not in baby:
        break
check("fully grown after the timer", "grow" not in baby and g.tank.fish[baby["uid"]].size_k() == 1.0)
check("'grew up' message shown", any("grew up" in t[0] for t in g.toasts))
check("full-size earnings", abs(E.fish_rate(s, baby) - grown_rate) / grown_rate < 0.2)

# a waiting baby (tank was full) starts growing when it moves in
s["upgrades"]["tank"] = 0
while len(s["fish"]) > E.capacity(s):
    s["fish"].pop()
g.tank.sync()
s["eggs"] = [dict(c="golden", left=0, total=1, inc=1)]
g.hatch_ready()
check("baby waits when the tank is full", len(s["pending"]) == 1)
g.sell_pending() if False else g.rehome(s["fish"][-1]["uid"])
newest = [f for f in s["fish"] if f.get("hatched")][-1]
check("waiting baby starts growing once it moves in", newest.get("grow") == E.GROW_TIME)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
