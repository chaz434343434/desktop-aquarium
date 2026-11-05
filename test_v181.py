"""Headless checks for 1.8.1: holiday tabs only during the holiday; a log of what you've bought
(Past Events) to use or buy again; nothing shows for players who never had it; in-use things are kept.
Run: python test_v181.py [screenshot_dir]"""
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
shots = sys.argv[1] if len(sys.argv) > 1 else None
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
check("no Past Events button for someone who never had anything", "Past Events" not in labels)
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

# ---- an old save with Halloween things in use, no log entries for some of them
path = os.path.join(tempfile.mkdtemp(), "s.json")
fish = [{"uid": 1, "sp": "sunflower", "name": "Sunny", "lv": 3, "xp": 0, "full": 80, "happy": 70},
        {"uid": 2, "sp": "pumpkin", "name": "Boo", "lv": 9, "xp": 0, "full": 80, "happy": 70}]
with open(path, "w") as fh:
    json.dump({"version": 3, "bubbles": 1e15, "earned_run": 1e15, "earned_total": 1e15, "fish": fish,
               "toys": {"cauldron": {"lv": 4, "x": 0.5}}, "upgrades": {"spooky": 3, "tank": 4},
               "themes": ["classic", "haunted"], "theme": "haunted", "seasonal_owned": []}, fh)
g = Game(save_path=path)
g.apply_window(first=True)
s = g.state
check("the Pumpkin Catfish in the tank stays", any(f["name"] == "Boo" and f["lv"] == 9 for f in s["fish"]))
check("it still swims", any(a.f["sp"] == "pumpkin" for a in g.tank.fish.values()))
check("the toy stays, level and all", E.toy_lv(s, "cauldron") == 4 and "cauldron" in g.tank.toys)
check("the upgrade keeps working", E.ulv(s, "spooky") == 3)
check("the theme stays on", s["theme"] == "haunted")
check("the log picked them all up", {"pumpkin", "cauldron", "spooky", "haunted"} <= set(s["seasonal_owned"]))
_, labels = listed(g, "fish")
check("no Halloween button for them either", "Halloween" not in labels)
check("but they get Past Events", "Past Events" in labels)
rows, labels = listed(g, "past")
check("it lists what they've had", {"Witch's Cauldron", "Haunted Lagoon"} <= set(rows)
      and any("Pumpkin" in r for r in rows) and any(r.startswith("Spooky Bubbles") for r in rows))
check("and only that", "Candy Corn Pile" not in rows and not any(r.startswith("Ghostly") for r in rows))
check("not this month's holiday", not any("Turkey" in r for r in rows))
if shots:
    os.makedirs(shots, exist_ok=True)
    g.toasts.clear()
    g.draw()
    g.draw()
    pygame.image.save(g.screen.subsurface(g.ui.panel_rect), os.path.join(shots, "past_events.png"))

# ---- with every tab showing, none of them sits on the close button, at any size
for k in (1.0, 1.5, 2.0):
    s["settings"]["uiscale"] = k
    g.layout()
    g.apply_window()
    rects = {}
    orig_button = g.ui.button
    g.ui.button = lambda scr, rect, label, *a, **kw: rects.__setitem__(label, pygame.Rect(rect)) or orig_button(scr, rect, label, *a, **kw)
    g.ui.panel, g.ui.tab = "shop", "past"
    g.draw()
    g.ui.button = orig_button
    check(f"at {int(k * 100)}% the tabs stop before the close button",
          "Past Events" in rects and "Thanksgiving" in rects and rects["Bills"].right <= rects["x"].x)
s["settings"]["uiscale"] = 1.0
g.layout()
g.apply_window()

# ---- they can use it and buy it again, after a new season, in any month
s["bill_pearls"] = 3
g.spawn()
s = g.state
check("Spawning Season clears the upgrades and fish", not E.ulv(s, "spooky") and not any(f["sp"] == "pumpkin" for f in s["fish"]))
check("the log survives", "pumpkin" in s["seasonal_owned"])
os.environ["DA_DATE"] = "2027-03-01"
E.earn(s, 1e15)
s["upgrades"]["tank"] = 4
rows, labels = listed(g, "past")
check("in March it's all still in Past Events", any("Pumpkin" in r for r in rows) and "Witch's Cauldron" in rows)
g.buy_species("pumpkin")
g.buy_toy("cauldron")
g.buy_upgrade("spooky")
check("bought again", any(f["sp"] == "pumpkin" for f in s["fish"]) and E.toy_lv(s, "cauldron") == 1 and E.ulv(s, "spooky") == 1)
g.theme_action("classic")
g.theme_action("haunted")
check("the theme can be switched back on", s["theme"] == "haunted")

# ---- next Halloween it's a normal holiday again
os.environ["DA_DATE"] = "2027-10-10"
_, labels = listed(g, "fish")
check("next October the Halloween button is back", "Halloween" in labels)
check("and Past Events steps aside", "Past Events" not in labels or "halloween" not in E.past_seasons(s))
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
