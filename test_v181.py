"""Headless checks for holiday items since 1.11.0: a holiday's button and shop only exist during the holiday, there's
no Past Events, and whatever is on a save stays and keeps working. Run: python test_v181.py [screenshot_dir]"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-11-10"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def listed(g, tab):
    """(row titles, button labels) a Shop tab draws"""
    titles, labels = [], []
    orig_row, orig_button = g.ui.row, g.ui.button
    g.ui.row = lambda scr, view, y, icon, title, *a, **k: titles.append(title) or orig_row(scr, view, y, icon, title, *a, **k)
    g.ui.button = lambda scr, rect, label, *a, **k: labels.append(label) or orig_button(scr, rect, label, *a, **k)
    g.ui.panel, g.ui.tab = "shop", tab
    g.draw()
    g.ui.row, g.ui.button = orig_row, orig_button
    return titles, labels


# ---- a player who has never had anything from Halloween
g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
E.earn(g.state, 1e15)
g.state["upgrades"]["tank"] = 4
_, labels = listed(g, "fish")
check("no Halloween button", "Halloween" not in labels)
check("no Past Events button", "Past Events" not in labels)
check("this month's holiday still has its button", "Thanksgiving" in labels)
all_rows = []
for tab in ("fish", "toys", "upgrades", "themes", "season:thanksgiving"):
    all_rows += listed(g, tab)[0]
check("no Halloween items anywhere", not {"Haunted Lagoon", "Witch's Cauldron", "Pumpkin Catfish"} & set(all_rows)
      and not any(r.startswith(("Pumpkin Catfish", "Ghostly Glow")) for r in all_rows))
g.buy_species("pumpkin")
g.buy_toy("cauldron")
g.buy_upgrade("spooky")
g.theme_action("haunted")
check("and they can't buy them", not any(f["sp"] == "pumpkin" for f in g.state["fish"])
      and not E.toy_lv(g.state, "cauldron") and not E.ulv(g.state, "spooky") and "haunted" not in g.state["themes"])

# ---- an old save with Halloween things in use, and things from the old log it no longer has
path = os.path.join(tempfile.mkdtemp(), "s.json")
fish = [{"uid": 1, "sp": "sunflower", "name": "Sunny", "lv": 3, "xp": 0, "full": 80, "happy": 70},
        {"uid": 2, "sp": "pumpkin", "name": "Boo", "lv": 9, "xp": 0, "full": 80, "happy": 70}]
with open(path, "w") as fh:
    json.dump({"version": 3, "bubbles": 1e15, "earned_run": 1e15, "earned_total": 1e15, "fish": fish,
               "toys": {"cauldron": {"lv": 4, "x": 0.5}}, "upgrades": {"spooky": 3, "tank": 4},
               "themes": ["classic", "haunted"], "theme": "haunted", "seasonal_owned": ["candycorn", "ghostglow"],
               "bills_paid": 4, "bill_pearls": 6, "bill_due": 5.0, "pearls": 2}, fh)
g = Game(save_path=path)
g.apply_window(first=True)
s = g.state
check("pearls waiting from paid bills are paid out", s["pearls"] == 8)
check("the bill leftovers are gone from the save", not {"bills_paid", "bill_pearls", "bill_due"} & set(s))
check("the Pumpkin Catfish in the tank stays", any(f["name"] == "Boo" and f["lv"] == 9 for f in s["fish"]))
check("it still swims", any(a.f["sp"] == "pumpkin" for a in g.tank.fish.values()))
check("the toy stays, level and all", E.toy_lv(s, "cauldron") == 4 and "cauldron" in g.tank.toys)
check("the upgrade keeps working", E.ulv(s, "spooky") == 3)
check("the theme stays on", s["theme"] == "haunted")
_, labels = listed(g, "fish")
check("no Halloween or Past Events button for them either", "Halloween" not in labels and "Past Events" not in labels)
check("Rings and Spawning are there", "Rings" in labels and "Spawning" in labels and "Bills" not in labels)
rows, _ = listed(g, "toys")
check("a toy they still have is with the other toys", "Witch's Cauldron" in rows)
check("one they only had once isn't", "Candy Corn Pile" not in rows)
rows, _ = listed(g, "upgrades")
check("same for upgrades", any(r.startswith("Spooky Bubbles") for r in rows) and not any(r.startswith("Ghostly") for r in rows))
rows, _ = listed(g, "themes")
check("the theme is with the other themes", "Haunted Lagoon" in rows)
g.theme_action("classic")
g.theme_action("haunted")
check("so it can be switched off and back on", s["theme"] == "haunted")
lv = E.toy_lv(s, "cauldron")
E.earn(s, 1e20)
g.buy_toy("cauldron")
check("a toy they still have can level up", E.toy_lv(s, "cauldron") == lv + 1)
g.buy_toy("candycorn")
check("one they only had once can't be bought", not E.toy_lv(s, "candycorn"))

# ---- a Spawning Season clears it, and it can't come back until the holiday does
s["earned_run"] = 1e18
g.spawn()
s = g.state
check("Spawning Season clears the fish, toys and upgrades", not E.ulv(s, "spooky") and not E.toy_lv(s, "cauldron")
      and not any(f["sp"] == "pumpkin" for f in s["fish"]))
check("the theme is kept, like every theme", "haunted" in s["themes"])
os.environ["DA_DATE"] = "2027-03-01"
E.earn(s, 1e15)
s["upgrades"]["tank"] = 4
rows, _ = listed(g, "toys")
check("in March they're not for sale", "Witch's Cauldron" not in rows)
g.buy_species("pumpkin")
g.buy_toy("cauldron")
g.buy_upgrade("spooky")
check("and can't be bought", not any(f["sp"] == "pumpkin" for f in s["fish"]) and not E.toy_lv(s, "cauldron") and not E.ulv(s, "spooky"))

# ---- next Halloween it's a normal holiday again
os.environ["DA_DATE"] = "2027-10-10"
_, labels = listed(g, "fish")
check("next October the Halloween button is back", "Halloween" in labels)
g.buy_toy("cauldron")
check("and it's all for sale", E.toy_lv(s, "cauldron") == 1)
rows, _ = listed(g, "toys")
check("during the holiday it lives in the holiday's tab", "Witch's Cauldron" not in rows)

# ---- with every tab showing, none of them sits on the close button, at any size
os.environ["DA_DATE"] = "2026-11-10"
for k in (1.0, 1.5, 2.0):
    s["settings"]["uiscale"] = k
    g.layout()
    g.apply_window()
    rects = {}
    orig_button = g.ui.button
    g.ui.button = lambda scr, rect, label, *a, **kw: rects.__setitem__(label, pygame.Rect(rect)) or orig_button(scr, rect, label, *a, **kw)
    g.ui.panel, g.ui.tab = "shop", "fish"
    g.draw()
    g.ui.button = orig_button
    check(f"at {int(k * 100)}% the tabs stop before the close button",
          "Thanksgiving" in rects and rects["Spawning"].right <= rects["x"].x)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
