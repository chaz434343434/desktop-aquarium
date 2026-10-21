"""Headless checks for 1.5.1: holiday items live in their own Shop tab ("Halloween", later "Christmas").
Run: python test_v151.py [screenshot_dir]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-10-21"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def listed(g, tab):
    """titles of the rows a Shop tab draws (whole list, not just what fits on screen)"""
    titles, tabs = [], []
    orig_row, orig_button = g.ui.row, g.ui.button
    g.ui.row = lambda scr, view, y, icon, title, *a, **k: titles.append(title) or orig_row(scr, view, y, icon, title, *a, **k)
    g.ui.button = lambda scr, rect, label, *a, **k: tabs.append(label) or orig_button(scr, rect, label, *a, **k)
    g.ui.panel, g.ui.tab = "shop", tab
    g.draw()
    g.ui.row, g.ui.button = orig_row, orig_button
    return titles, tabs


def shot(g, name):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.draw()
        pygame.image.save(g.screen.subsurface(g.ui.panel_rect), os.path.join(shots, name + ".png"))


g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
s = g.state
E.earn(s, 1e12)
s["upgrades"]["tank"] = 4
g.toasts.clear()

_, tabs = listed(g, "fish")
check("in October the Shop has a Halloween tab", "Halloween" in tabs)
rows, _ = listed(g, "season:halloween")
check("it has the Pumpkin Catfish", any("Pumpkin Catfish" in r for r in rows))
check("the Haunted Lagoon theme", "Haunted Lagoon" in rows)
check("all 4 Halloween toys", {"Jack-o'-Lantern", "Witch's Cauldron", "Fishbone Skeleton", "Candy Corn Pile"} <= set(rows))
check("and all 3 Halloween upgrades",
      sum(any(r.startswith(n) for r in rows) for n in ("Ghostly Glow", "Spooky Bubbles", "Trick-or-Treat")) == 3)
check("and nothing else", len(rows) == 1 + 1 + 4 + 3)
shot(g, "halloween_tab")
fish_rows, _ = listed(g, "fish")
toy_rows, _ = listed(g, "toys")
up_rows, _ = listed(g, "upgrades")
theme_rows, _ = listed(g, "themes")
check("the Catfish tab no longer lists the Pumpkin Catfish", not any("Pumpkin" in r for r in fish_rows))
check("Toys tab: no Halloween toys", not {"Jack-o'-Lantern", "Witch's Cauldron"} & set(toy_rows) and toy_rows)
check("Upgrades tab: no Halloween upgrades", not any(r.startswith("Ghostly") for r in up_rows) and up_rows)
check("Themes tab: no Haunted Lagoon", "Haunted Lagoon" not in theme_rows and "Classic Blue" in theme_rows)

# buy from the tab
g.buy_toy("cauldron")
g.buy_species("pumpkin")
check("buying from it works", E.toy_lv(s, "cauldron") == 1 and any(f["sp"] == "pumpkin" for f in s["fish"]))

# after Halloween
os.environ["DA_DATE"] = "2026-12-01"
_, tabs = listed(g, "fish")
check("after Halloween the tab stays for people who bought Halloween things", "Halloween" in tabs)
rows, _ = listed(g, "season:halloween")
check("but only shows what they had", set(rows) <= {"Witch's Cauldron", "Pumpkin Catfish"} | {r for r in rows if "Pumpkin" in r}
      and "Candy Corn Pile" not in rows)
g2 = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g2.apply_window()
g2.ui.panel, g2.ui.tab = "shop", "season:halloween"
_, tabs = listed(g2, "season:halloween")
check("a new player after Halloween has no Halloween tab", "Halloween" not in tabs)
check("and is sent back to the Catfish tab", g2.ui.tab == "fish")
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
