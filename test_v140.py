"""Headless checks for 1.4.0: Belly Rubs ability, Halloween theme + Pumpkin Catfish (seasonal).
Run: python test_v140.py [screenshot_dir]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-10-19"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.data import RUB_COOLDOWN, SKULL_POP_MULT, HAUNTED_POP_MULT  # noqa: E402
from purrfin.game import Game  # noqa: E402
from purrfin.tank import PopBubble  # noqa: E402

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


def shot(name, rect=None):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.draw()
        g.draw()
        pygame.image.save(g.screen.subsurface(rect or g.ui.panel_rect), os.path.join(shots, name + ".png"))


def step(t):
    g.now += t
    g.tick_rub(t)


def wiggle(actor, n, dt=0.05):
    """hold the button on a fish and rub it back and forth"""
    pos = tuple(int(v) for v in g.to_screen(actor.x, actor.y))
    g.mouse_down(pos, 1)
    for i in range(n):
        step(dt)
        p2 = (pos[0] + (6 if i % 2 else -6), pos[1])
        g.mouse_motion(p2, (12, 0), (1, 0, 0))
    g.mouse_up(pos, 1)


g.toasts.clear()
a = next(iter(g.tank.fish.values()))
a.x, a.y = 60, 30
# ---- no ability: holding + wiggling is still just one pet
before = s["stats"]["pets"]
wiggle(a, 40)
check("without Belly Rubs, rubbing = 1 pet", s["stats"]["pets"] - before == 1)

# ---- Belly Rubs Lv 1: 3 seconds of rubbing
E.earn(s, 1e4)
g.buy_upgrade("rub")
check("Belly Rubs can be bought early (150 scales)", E.ulv(s, "rub") == 1 and E.rub_secs(s) == 3)
g.rub_button()
check("button arms it", g.rub == "armed")
step(30)
check("armed waits until you start rubbing", g.rub == "armed")
before = s["stats"]["pets"]
wiggle(a, 40)              # 2 seconds of rubbing
got = s["stats"]["pets"] - before
check(f"rubbing pays many times ({got} pets in 2s)", got >= 20)
check("still active after 2s of a 3s rub", g.rub == "active")
step(1.1)
check("ends after 3 seconds and rests", g.rub == "cooldown")
before = s["stats"]["pets"]
wiggle(a, 20)
check("while resting, rubbing is 1 pet again", s["stats"]["pets"] - before == 1)
g.rub_button()
check("button can't restart it while resting", g.rub == "cooldown")
step(RUB_COOLDOWN + 0.1)
check("ready again after the rest", g.rub == "ready")
s["upgrades"]["rub"] = 13
check("Lv 13 rubs for 15s", E.rub_secs(s) == 15)
g.ui.panel = None
r = g.tank_rect
shot("hud_rub", pygame.Rect(max(0, r.right - 1000), r.y - 80, min(1000, r.right), 80))

# ---- Halloween: in season, both are for sale
s["upgrades"]["rub"] = 1
for sp in ("bronze", "panda", "oto"):
    E.add_fish(s, sp)
g.tank.sync()
check("it's Halloween season on Oct 19", E.in_season("halloween"))
check("not on July 1", not E.in_season("halloween", __import__("datetime").date(2026, 7, 1)))
check("Nov 2 is the last day", E.in_season("halloween", __import__("datetime").date(2026, 11, 2))
      and not E.in_season("halloween", __import__("datetime").date(2026, 11, 3)))
check("Pumpkin Catfish for sale", E.seasonal_fish_buyable(s, "pumpkin") == "ok")
check("Haunted Lagoon for sale", E.theme_visible(s, "haunted"))
E.earn(s, 1e9)
s["upgrades"]["tank"] = 4
g.buy_species("pumpkin")
pf = next((f for f in s["fish"] if f["sp"] == "pumpkin"), None)
check("bought a Pumpkin Catfish", pf is not None)
best = max(E.SPECIES_BY_ID[f["sp"]]["rate"] for f in s["fish"] if f["sp"] != "pumpkin")
check("it earns 2x your best catfish", abs(E.fish_rate(s, dict(pf, shiny=False, lv=1, happy=0, full=80))
                                           - 2 * best * E.happy_mult(s, 0)) < 1e-9)
check("not counted in the Fishdex", "pumpkin" not in s["dex"])
n = len(s["fish"])
g.buy_species("pumpkin")
check("only one per tank", len(s["fish"]) == n)
check("babies never hatch as pumpkins", all(E.pick_baby_species(s, "golden") != "pumpkin" for _ in range(300)))
g.theme_action("haunted")
check("Haunted Lagoon bought and in use", "haunted" in s["themes"] and s["theme"] == "haunted")
check("worth +10% scales", E.THEMES_BY_ID["haunted"]["bonus"] == 10)
plain = PopBubble(10, 20)
skull = PopBubble(10, 20, skull=True)
check("pop-bubbles are worth 2x in the Haunted Lagoon", g.pop_mult(plain) == HAUNTED_POP_MULT == 2)
check("Pumpkin skull bubbles are worth 3x", g.pop_mult(skull) == SKULL_POP_MULT == 3)
pa = g.tank.fish[pf["uid"]]
pa.skull_t = 0.01
g.tank.update(0.05)
check("the Pumpkin Catfish blows skull bubbles", any(p.skull for p in g.tank.pops))
before = s["bubbles"]
g.pop(next(p for p in g.tank.pops if p.skull))
check("popping a skull pays 3x", abs((s["bubbles"] - before) - E.pop_value(s) * 3) < 1e-6 * s["bubbles"])
g.tank.ghost_timer = 0
for _ in range(80):
    g.tank.update(0.05)
for _ in range(6):
    g.tank.spawn_pop()
    g.tank.add_decor_bubble(40, 40, big=True)
g.tank.hour_override = 12
if shots:
    g.draw()
    low = g.tank.draw()
    pygame.image.save(pygame.transform.scale(low, (low.get_width() * 4, low.get_height() * 4)),
                      os.path.join(shots, "haunted_tank.png"))
g.ui.panel, g.ui.tab = "shop", "fish"
shot("shop_fish")
g.ui.tab = "themes"
shot("shop_themes")

# ---- after Halloween: hidden for newcomers, but kept for people who got them
os.environ["DA_DATE"] = "2026-07-01"
fresh = E.new_state()
check("off-season, a new player can't see the pumpkin", E.seasonal_fish_buyable(fresh, "pumpkin") == "season")
check("off-season, a new player can't see the theme", not E.theme_visible(fresh, "haunted"))
keep = E.new_state(keep=s)
check("after Spawning Season the pumpkin can be bought again off-season",
      E.seasonal_fish_buyable(keep, "pumpkin") == "ok")
check("and the theme is still yours", "haunted" in keep["themes"] and E.theme_visible(keep, "haunted"))
n = len(s["fish"])
g.sell_value = None
s["fish"] = [f for f in s["fish"] if f["sp"] != "pumpkin"]
check("the old owner can rebuy it off-season", E.seasonal_fish_buyable(s, "pumpkin") == "ok")
g2 = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g2.state["bubbles"] = 1e12
g2.buy_species("pumpkin")
check("a new player off-season is told no", not any(f["sp"] == "pumpkin" for f in g2.state["fish"]))
g2.theme_action("haunted")
check("and can't buy the theme", "haunted" not in g2.state["themes"])
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
