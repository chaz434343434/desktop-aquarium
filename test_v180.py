"""Headless checks for 1.8.0: Tank Bills + Rings replace the old pearl formula (old saves convert),
more toys and upgrades, the Thanksgiving event and its feasts. Run: python test_v180.py [screenshot_dir]"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-11-05"
import pygame  # noqa: E402

from purrfin import economy as E, sprites  # noqa: E402
from purrfin.data import TOYS, UPGRADES, FEASTS, FEASTS_BY_ID, PEARL_TREE, BILL_TIME  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def new_game():
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
    g.apply_window(first=True)
    g.toasts.clear()
    g.tank.hour_override = 12
    return g


def shot(g, name, rect=None):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.draw()
        g.draw()
        pygame.image.save(g.screen.subsurface(rect or g.ui.panel_rect), os.path.join(shots, name + ".png"))


# ---- the pearl problem
g = new_game()
s = g.state
E.earn(s, 1e30)
check("being rich alone gives no pearls any more (it gave 15,811,388 before)", E.pearls_for(s) == 0)
first = E.bill_info(s)
check("first bill is the Water Bill", first["name"] == "Water Bill")
s["bubbles"] = first["cost"] * 3
got = g.pay_bill()
check("paying a bill spends real scales", abs(s["bubbles"] - first["cost"] * 2) < 1 and got)
check("and earns pearls for the next spawn", E.pearls_for(s) >= 1 and s["pearls"] == 0)
check("the next bill costs 6x more", abs(E.bill_info(s)["cost"] / first["cost"] - 6) < 1e-9)
s["bubbles"] = 1e63
g.pay_all_bills()
total = E.pearls_for(s)
check(f"paying every bill you can afford at 1e63 scales: a sensible {total} pearls", 300 < total < 1500)
check("names keep going", "2" in E.bill_info(s, 25)["name"])
s["bubbles"] = s["earned_run"] = 0.0
before = s["pearls"]
g.spawn()
s = g.state
check("Spawning Season collects them", s["pearls"] == before + total)
check("and the bills start over", s["bills_paid"] == 0 and E.pearls_for(s) == 0)
s["pearls"] = 0
g.spawn()
check("no spawning without paying a bill", g.state["spawns"] == 1)

# ---- on-time bonus, no punishment
s = g.state
s["tree"] = {}
s["bubbles"] = 0.0
E.tick_bills(s, 1)
check("the on-time clock waits until you can afford the bill", s["bill_due"] is None)
s["bubbles"] = 1e20
check("a bill arrives once you can", E.tick_bills(s, 1) is not None and s["bill_due"] == BILL_TIME)
b = E.bill_info(s)
_, p1 = E.pay_bill(s)
check("paid on time: the bonus", p1 == b["pearls"] + b["bonus"])
E.tick_bills(s, 1)
s["bill_due"] = 0.0
b = E.bill_info(s)
scales, fish = s["bubbles"], list(s["fish"])
for _ in range(100):
    E.tick_bills(s, 100)
check("a late bill costs you nothing", s["bubbles"] == scales and s["fish"] == fish)
_, p2 = E.pay_bill(s)
check("it only misses the bonus", p2 == b["pearls"])

# ---- old saves convert
d = tempfile.mkdtemp()
path = os.path.join(d, "s.json")
with open(path, "w") as fh:
    json.dump({"version": 2, "pearls": 100000000, "tree": {"gills": 7, "hatch": 3, "keeptoys": 1}, "bubbles": 5.0,
               "fish": [{"uid": 1, "sp": "sunflower", "name": "Sunny", "lv": 3, "xp": 0, "full": 80, "happy": 70}]}, fh)
g2 = Game(save_path=path)
check(f"100,000,000 old pearls are exchanged down ({g2.state['pearls']})", 100 <= g2.state["pearls"] <= 140)
check("everything bought in the old tree is kept as rings", g2.state["tree"] == {"gills": 7, "hatch": 3, "keeptoys": 1})
check("and those bonuses still work", E.tlv(g2.state, "gills") == 7)
check("the player is told", any("Rings" in t[0] for t in g2.toasts))
g2.apply_window()
g2.save()
g3 = Game(save_path=path)
check("it only converts once", g3.state["pearls"] == g2.state["pearls"] and not g3.migrated)
with open(path, "w") as fh:
    json.dump({"version": 2, "pearls": 12, "fish": [{"uid": 1, "sp": "sunflower", "name": "S", "lv": 1, "xp": 0,
                                                     "full": 80, "happy": 70}]}, fh)
check("small pearl savings are left alone", Game(save_path=path).state["pearls"] == 12)

# ---- rings
g = new_game()
s = g.state
c0 = E.bill_info(s)["cost"]
s["tree"]["thrift"] = 2
check("Thrift Ring: cheaper bills", abs(E.bill_info(s)["cost"] / c0 - 0.81) < 1e-9)
s["tree"] = {}
b0 = E.fish_boost(s)
s["tree"]["fishring"] = 2
check("Fish Ring: fish earn more", abs(E.fish_boost(s) / b0 - 2) < 1e-9)
m0 = E.global_mult(s)
s["tree"]["crown"] = 1
check("Crown Ring: doubles everything", abs(E.global_mult(s) / m0 - 2) < 1e-9)
check("rings all have ids that are unique", len({n["id"] for n in PEARL_TREE}) == len(PEARL_TREE))
s["tree"] = {}

# ---- more toys and upgrades
regular = [t for t in TOYS if not t.get("season")]
costs = [t["cost"] for t in regular]
check(f"toys now reach way up towards the top fish ({E.fmt(costs[-1])})", costs[-1] > 1e63)
for t in TOYS:
    sprites.toy_icon(t["id"], 2)
for u in UPGRADES:
    sprites.upgrade_icon(u["id"], 4)
check("every toy and upgrade has art", True)
m0 = E.global_mult(s)
s["upgrades"]["reefguard"] = 3
check("Reef Guardian: +25% per level", abs(E.global_mult(s) / m0 - 1.75) < 1e-9)
s["upgrades"].pop("reefguard")

# ---- Thanksgiving
check("Thanksgiving is on in November", E.in_season("thanksgiving"))
check("Halloween isn't", not E.in_season("halloween"))
check("the seasons don't overlap", not E.in_season("thanksgiving", __import__("datetime").date(2026, 11, 2))
      and not E.in_season("thanksgiving", __import__("datetime").date(2026, 12, 1)))
check("new players get a Thanksgiving tab, no Halloween tab", E.active_seasons(s) == ["thanksgiving"])
E.earn(s, 1e12)
s["upgrades"]["tank"] = 4
for sp in ("bronze", "panda", "pictus"):
    E.add_fish(s, sp)
g.tank.sync()
g.buy_species("turkey")
tf = next((f for f in s["fish"] if f["sp"] == "turkey"), None)
check("Turkey Catfish", tf is not None)
ta = g.tank.fish[tf["uid"]]
ta.skull_t = 0.01
g.tank.pops.clear()
g.tank.update(0.05)
check("it blows golden bubbles", any(p.golden for p in g.tank.pops))
g.theme_action("harvest")
check("Harvest Cove theme", s["theme"] == "harvest")
for tid in ("cornucopia", "haybale", "windupturkey", "leafpile"):
    g.buy_toy(tid)
check("Thanksgiving toys", E.toy_lv(s, "cornucopia") == 1)
for uid in ("harvestmoon", "seconds", "gravy"):
    g.buy_upgrade(uid)
check("Thanksgiving upgrades", E.ulv(s, "seconds") == 1)
check("Second Helpings: more bites", E.feast_bites(s, FEASTS_BY_ID["roast"]) > FEASTS_BY_ID["roast"]["bites"])
check("Gravy Boat: back sooner", E.feast_cooldown(s, FEASTS_BY_ID["roast"]) < FEASTS_BY_ID["roast"]["cooldown"])

# ---- the big meal
g.toasts.clear()
s["fish"][0]["full"] = 10.0
before = s["bubbles"]
g.serve_feast("roast")
fe = g.tank.feast
check("Whole Turkey is served", fe is not None and s["bubbles"] < before)
check("it gives 2x scales", "double" in s["buffs"])
g.serve_feast("pie")
check("only one feast at a time", g.tank.feast is fe)
for _ in range(150):         # 15 seconds: the slowest fish can take about 10 to cross a wide tank
    g.update(0.1)
check("it sinks to the sand", fe["settled"])
n0 = sum(1 for a in g.tank.fish.values() if abs(a.x - fe["x"]) < 42)
check(f"every fish swims over to eat ({n0}/{len(g.tank.fish)})", n0 == len(g.tank.fish))
check("and they're eating it", fe["bites"] < fe["total"])
if shots:
    os.makedirs(shots, exist_ok=True)
    low = g.tank.draw()
    pygame.image.save(pygame.transform.scale(low, (low.get_width() * 4, low.get_height() * 4)),
                      os.path.join(shots, "feast.png"))
before = s["bubbles"]
full0 = s["fish"][0]["full"]
for _ in range(1500):
    g.update(0.1)
    if not g.tank.feast:
        break
check("until it's all gone", g.tank.feast is None)
check("fish got fed", s["fish"][0]["full"] > 10)
check("and shed scales", s["bubbles"] > before)
g.serve_feast("roast")
check("then the kitchen needs time", g.tank.feast is None)
g.food_cd.clear()
for f in FEASTS:
    sprites.feast_icon(f["id"])
g.ui.panel, g.ui.tab = "shop", "season:thanksgiving"
g.toasts.clear()
shot(g, "thanksgiving_tab")
g.ui.tab = "spawn"
s["bubbles"] = 1e15
shot(g, "bills_tab")
g.ui.scroll[("shop", "spawn")] = 500
shot(g, "rings")
g.ui.scroll[("shop", "spawn")] = 0
g.ui.panel = None
if shots:
    low = g.tank.draw()
    pygame.image.save(pygame.transform.scale(low, (low.get_width() * 4, low.get_height() * 4)),
                      os.path.join(shots, "harvest.png"))
os.environ["DA_DATE"] = "2026-12-05"
g.serve_feast("pie")
check("after Thanksgiving, no more feasts", g.tank.feast is None)
fresh = E.new_state()
check("and new players don't see the tab", E.active_seasons(fresh) == [])
check("people who bought Thanksgiving things find it in Past Events", "thanksgiving" in E.past_seasons(s))
check("and new players don't", E.past_seasons(fresh) == [])
check("but the feasts are gone from it", not E.season_items(s, "thanksgiving")["feasts"])
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
