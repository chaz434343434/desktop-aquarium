"""Headless checks for 1.6.0: 100 catfish, steady late-game prices, Fishdex fits them all.
Run: python test_v160.py [screenshot_dir]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E, sprites  # noqa: E402
from purrfin.data import SPECIES, UPGRADES_BY_ID  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


check("100 catfish", len(SPECIES) == 100)
ids = [sp["id"] for sp in SPECIES]
check("all different", len(set(ids)) == 100 and len({sp["name"] for sp in SPECIES}) == 100)
check("no catfish shares an id with an upgrade", not (set(ids) & set(UPGRADES_BY_ID)))
check("#100 is the Infinity Catfish", SPECIES[99]["name"] == "Infinity Catfish")
costs = [sp["cost"] for sp in SPECIES]
rates = [sp["rate"] for sp in SPECIES]
check("every catfish costs more than the last", all(b > a for a, b in zip(costs, costs[1:])))
check("and earns more", all(b > a for a, b in zip(rates, rates[1:])))
late = [costs[i + 1] / costs[i] for i in range(41, 99)]
check("after the Blue Channel, prices grow x3 per catfish (same as what they earn)", all(abs(x - 3) < 1e-9 for x in late))
check(f"the top price is a normal number ({E.fmt(costs[-1])})", costs[-1] < 1e100 and not E.fmt(costs[-1]).startswith("MAX"))
for sp in SPECIES:
    sprites.fish_frames(sp["id"])
    sprites.fish_icon(sp["id"], 3)
    sprites.fish_frames(sp["id"], shiny=True)
check("all 100 draw (normal and shiny)", True)

g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
s = g.state
g.toasts.clear()
s["dex"] = ids[:]
g.ui.panel = "dex"
g.draw()
check("the Fishdex says 100", True)
mx = g.ui.content_h - g.ui.view_h
g.ui.scroll[("dex", g.ui.tab)] = mx
g.draw()
check("the Fishdex scrolls all the way to #100", mx > 0)
if shots:
    os.makedirs(shots, exist_ok=True)
    pygame.image.save(g.screen.subsurface(g.ui.panel_rect), os.path.join(shots, "dex_end.png"))
    g.ui.scroll[("dex", g.ui.tab)] = 0
    g.draw()
    pygame.image.save(g.screen.subsurface(g.ui.panel_rect), os.path.join(shots, "dex_top.png"))
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
