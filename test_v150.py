"""Headless checks for 1.5.0: Blue Channel Catfish (hand-drawn), 60 species, number names to centillion,
Halloween toys + upgrades, click-only bubbles, Bugs & Support. Run: python test_v150.py [screenshot_dir]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-10-21"
import pygame  # noqa: E402

from purrfin import economy as E, sprites  # noqa: E402
from purrfin.data import SPECIES, TOYS, UPGRADES, TOY_MAX_LEVEL  # noqa: E402
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


g.toasts.clear()
# ---- species
check("at least 60 catfish", len(SPECIES) >= 60)
check("Blue Channel Catfish comes right after the Galaxy Catfish", SPECIES[40]["id"] == "bluechannel")
costs = [sp["cost"] for sp in SPECIES]
check("every catfish costs more than the one before", all(b > a for a, b in zip(costs, costs[1:])))
rates = [sp["rate"] for sp in SPECIES]
check("and earns more", all(b > a for a, b in zip(rates, rates[1:])))
fr = sprites.fish_frames("bluechannel")
check("Blue Channel has a 4-step swim cycle in every direction", all(len(v) == 4 for v in fr.values()))
check("drawn at the friend's size (31x21)", fr[(True, False)][0].get_size() == (31, 21))
check("facing left is the mirror image",
      fr[(False, False)][0].get_at((0, 10)) == fr[(True, False)][0].get_at((30, 10)))
shiny = sprites.fish_frames("bluechannel", shiny=True)[(True, False)][0]
check("a shiny one has different colours", shiny.get_at((20, 9)) != fr[(True, False)][0].get_at((20, 9)))
looked = sprites.fish_frames("bluechannel", look=(2, 1, 0, 0, 0))[(True, False)][0]
check("each fish gets its own shade", looked.get_at((20, 9)) != fr[(True, False)][0].get_at((20, 9)))
for sp in SPECIES:
    sprites.fish_frames(sp["id"])
    sprites.fish_icon(sp["id"], 3)
check("every catfish draws", True)

# ---- numbers
check("number names reach centillion", E.fmt(1e303) == "1.00Ce" and E.fmt(1e63) == "1.00Vg")
check("old names unchanged", E.fmt(1.5e36) == "1.50Ud" and E.fmt(2e48) == "2.00Qid")
E.earn(s, 1e305)
E.earn(s, 1e305)
check("scales can't overflow", s["bubbles"] == E.MAX_SCALES)
s["bubbles"] = s["earned_total"] = s["earned_run"] = 0.0

# ---- bubbles: one click each
E.earn(s, 1e6)
g.tank.pops.clear()
p = PopBubble(60, 30)
g.tank.pops.append(p)
a_pos = tuple(int(v) for v in g.to_screen(20, 40))
b_pos = tuple(int(v) for v in g.to_screen(p.x, p.y))
for f in g.tank.fish.values():
    f.x, f.y = 200, 50
g.mouse_down(a_pos, 1)
g.mouse_motion(b_pos, (40, -10), (1, 0, 0))
g.mouse_up(b_pos, 1)
check("sweeping over a bubble with the button held does NOT pop it", p in g.tank.pops)
g.mouse_down(b_pos, 1)
g.mouse_up(b_pos, 1)
check("clicking it does", p not in g.tank.pops)

# ---- Halloween toys and upgrades
E.earn(s, 1e12)
s["upgrades"]["tank"] = 4
for tid in ("jackolantern", "cauldron", "skeleton", "candycorn"):
    g.buy_toy(tid)
check("all 4 Halloween toys bought", all(E.toy_lv(s, t) == 1 for t in ("jackolantern", "cauldron", "skeleton", "candycorn")))
inc0 = E.global_mult(s)
g.buy_upgrade("ghostglow")
check("Ghostly Glow: +10% scales", abs(E.global_mult(s) / inc0 - 1.10) < 1e-9)
pv0 = E.pop_value(s)
g.buy_upgrade("spooky")
check("Spooky Bubbles: bubbles +40%", abs(E.pop_value(s) / pv0 - 1.4) < 1e-9)
g.buy_upgrade("treats")
check("Trick-or-Treat bought", E.ulv(s, "treats") == 1)
check("Halloween items are remembered", {"cauldron", "spooky"} <= set(s["seasonal_owned"]))
ca = g.tank.toys["cauldron"]
ca.timer = 0
n = sum(1 for q in g.tank.pops if q.skull)
g.tank.update(0.05)
check("the cauldron burps up skull bubbles", sum(1 for q in g.tank.pops if q.skull) > n)
for tid in ("jackolantern", "cauldron", "skeleton", "candycorn"):
    sprites.toy_icon(tid, 2)
for u in UPGRADES:
    sprites.upgrade_icon(u["id"], 4)
check("every toy and upgrade has art", True)

E.add_fish(s, "bluechannel")
g.tank.sync()
g.tank.hour_override = 12
if shots:
    os.makedirs(shots, exist_ok=True)
    for _ in range(30):
        g.tank.update(0.05)
    low = g.tank.draw()
    pygame.image.save(pygame.transform.scale(low, (low.get_width() * 4, low.get_height() * 4)),
                      os.path.join(shots, "tank.png"))
g.ui.panel, g.ui.tab = "shop", "toys"
shot("toys")
g.ui.tab = "upgrades"
shot("upgrades")

# off-season
os.environ["DA_DATE"] = "2026-07-01"
fresh = E.new_state()
check("off-season, a new player can't see Halloween upgrades", not E.upgrade_visible(fresh, "spooky"))
check("or buy Halloween toys", not E.seasonal_ok(fresh, {"id": "cauldron", "season": "halloween"}))
keep = E.new_state(keep=s)
check("after Spawning Season, ones you had can be bought again off-season",
      E.upgrade_visible(keep, "spooky") and E.seasonal_ok(keep, E.TOYS_BY_ID["cauldron"]))
g2 = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
E.earn(g2.state, 1e15)
g2.buy_toy("cauldron")
g2.buy_upgrade("ghostglow")
check("a new player off-season is told no", not E.toy_lv(g2.state, "cauldron") and not E.ulv(g2.state, "ghostglow"))
os.environ["DA_DATE"] = "2026-10-21"

# ---- bugs & support
import webbrowser  # noqa: E402
opened = []
webbrowser.open = lambda url: opened.append(url) or True
g.report("bug")
check("Report a bug opens a GitHub issue with the version filled in",
      opened and "issues/new" in opened[0] and "Version" in opened[0])
g.ui.panel = "settings"
g.ui.scroll[("settings", g.ui.tab)] = 230
shot("options")
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
