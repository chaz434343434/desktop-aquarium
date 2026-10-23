"""Robot player: clicks, drags, scrolls and types at random all over the game, opens every panel and
tab, buys things, hatches eggs, spawns, saves and reloads - and reports every error it runs into.
Run: python fuzz.py [steps] [seed]      (DA_COMPACT=1 for the Mac-style window)"""
import os
import random
import sys
import tempfile
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.data import SPECIES, TOYS, UPGRADES, CLUTCHES  # noqa: E402
from purrfin.game import Game  # noqa: E402

STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 1
rng = random.Random(SEED)
pygame.init()
errors = {}


def record(where, exc):
    key = (where, type(exc).__name__, str(exc)[:120])
    if key not in errors:
        errors[key] = traceback.format_exc()
    else:
        errors[key + ("n",)] = None


save = os.path.join(tempfile.mkdtemp(), "save.json")
g = Game(save_path=save, fresh=True)
g.apply_window(first=True)
TABS = ["fish", "toys", "upgrades", "hatchery", "themes", "mine", "spawn", "season:halloween"]
KEYS = [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE, pygame.K_a, pygame.K_TAB]


def rand_pos():
    if rng.random() < 0.7 and g.ui.panel_rect is not None:      # mostly inside the open panel
        r = g.ui.panel_rect
        x, y = rng.randint(r.x, r.right), rng.randint(r.y, r.bottom)
        return int(x * g.ui.k), int(y * g.ui.k)
    if rng.random() < 0.5:                                       # the HUD / tank area
        r = g.tank_rect
        return rng.randint(r.x, r.right - 1), rng.randint(max(0, r.y - 80), r.bottom - 1)
    return rng.randint(0, g.win_w - 1), rng.randint(0, g.win_h - 1)


def action():
    s = g.state
    a = rng.random()
    if a < 0.30:
        p = rand_pos()
        g.ui.set_mouse(p)
        b = rng.choice((1, 1, 1, 3))
        g.mouse_down(p, b)
        if rng.random() < 0.3:
            q = (p[0] + rng.randint(-200, 200), p[1] + rng.randint(-150, 150))
            g.mouse_motion(q, (q[0] - p[0], q[1] - p[1]), (1, 0, 0))
            p = q
        g.mouse_up(p, b)
    elif a < 0.38:
        p = rand_pos()
        g.mouse_motion(p, (rng.randint(-9, 9), rng.randint(-9, 9)), (0, 0, 0))
    elif a < 0.43:
        g.ui.wheel(rand_pos(), rng.choice((-3, -1, 1, 3)))
    elif a < 0.50:
        g.ui.panel = rng.choice(["shop", "shop", "dex", "settings", None])
        if g.ui.panel == "shop":
            g.ui.tab = rng.choice(TABS)
    elif a < 0.55:
        g.key_down(pygame.event.Event(pygame.KEYDOWN, key=rng.choice(KEYS)))
        if rng.random() < 0.5:
            g.text_input(rng.choice(["a", "Fish ", "x", "123", "!", "é"]))
    elif a < 0.62:      # money + buying, the way a player would
        E.earn(s, max(100.0, s["bubbles"]) * rng.choice((0.5, 2, 10)))
        kind = rng.random()
        if kind < 0.4:
            g.buy_species(rng.choice(SPECIES[:min(len(SPECIES), 10 + len(s["dex"]))])["id"])
        elif kind < 0.7:
            g.buy_toy(rng.choice(TOYS)["id"])
        else:
            g.buy_upgrade(rng.choice(UPGRADES)["id"])
    elif a < 0.66:
        if E.ulv(s, "hatchery"):
            g.lay_clutch(rng.choice([c["id"] for c in CLUTCHES]))
            for e in s["eggs"]:
                e["left"] = 0 if rng.random() < 0.5 else e["left"]
            g.hatch_ready()
    elif a < 0.68:
        s["mystery"] = s.get("mystery", 0) + 1
    elif a < 0.70:
        if s["fish"]:
            g.start_rename(rng.choice(s["fish"]))
    elif a < 0.72:
        g.rub_button()
    elif a < 0.73:
        g.use_food(rng.choice(["flakes", "pellets", "bloodworms"]))
    elif a < 0.74:
        valid = {"width": [0.2, 0.3, 0.45, 0.7, 1.0], "uiscale": [1.0, 1.5, 2.0], "scale": [2, 3, 4],
                 "align": ["left", "center", "right"], "brightness": [-5, 0, 5], "power": ["normal", "saver"],
                 "daynight": [True, False], "nametags": [True, False], "topmost": [True, False]}
        key = rng.choice(list(valid))
        g.change_setting(key, rng.choice(valid[key]))
    elif a < 0.745:
        if E.pearls_for(s) > 0 or rng.random() < 0.3:
            g.spawn()
    elif a < 0.75:
        g.save()
        g2 = Game(save_path=save)                   # reload the save in a second game
        g2.apply_window()
    elif a < 0.76:
        g.ui.minimize() if rng.random() < 0.5 else g.ui.restore()
    elif a < 0.77:
        g.toggle_chill()
    else:
        pass


for i in range(STEPS):
    try:
        action()
    except Exception as e:
        record("action", e)
    try:
        dt = rng.choice((0.016, 0.033, 0.1, 0.3, 2.0, 30.0))
        g.update(dt)
        g.draw()
    except Exception as e:
        record("update/draw", e)
    if g.state["settings"].get("uiscale") not in (1.0, 1.5, 2.0):
        g.state["settings"]["uiscale"] = 1.0
    if not g.running:
        g.running = True

real = {k: v for k, v in errors.items() if v is not None}
print(f"steps {STEPS} seed {SEED}: {len(real)} different errors, species {len(g.state['dex'])}, "
      f"fish {len(g.state['fish'])}, scales {E.fmt(g.state['bubbles'])}")
for k, tb in real.items():
    print("=" * 70)
    print(k)
    print(tb[-1500:])
sys.exit(1 if real else 0)
