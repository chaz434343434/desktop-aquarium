"""Pure game-economy formulas. No pygame here, so sim.py can use it too."""
import datetime
import math
import os
import random
import time

from .data import (SPECIES, SPECIES_BY_ID, FOODS_BY_ID, TOYS, TOYS_BY_ID, UPGRADES_BY_ID, CLUTCHES_BY_ID,
                   THEMES_BY_ID, SHINY_CHANCE, PEARL_TREE_BY_ID, GOLDEN_EGG_SHINY,
                   TANK_CAPACITY, TOY_LEVEL_GROWTH, COPY_GROWTH, FISH_NAMES,
                   SPAWN_MIN, PEARL_BONUS, SEASONS, SEASONAL_BY_ID, RUB_BASE)

SAVE_VERSION = 2


def default_settings():
    return dict(width=0.30, align="right", scale=3, opacity=245, sound=True,
                volume=0.5, topmost=True, monitor=-1, daynight=True, panel_pos=None, nametags=True, brightness=0,
                autoupdate=True, uiscale=1.0, power="normal")


def new_state(keep=None):
    s = dict(
        version=SAVE_VERSION, bubbles=0.0, earned_run=0.0, earned_total=0.0,
        pearls=0, spawns=0, fish=[], next_uid=1, upgrades={}, toys={}, dex=[], jar=0.0, eggs=[],
        themes=["classic"], theme="classic", shinies=[], tree={}, pending=[], spots={}, mystery=0, seasonal_owned=[],
        buffs={}, chill=False, settings=default_settings(), last_time=time.time(),
        stats=dict(pets=0, pops=0, fed=0, playtime=0.0),
    )
    if keep:
        for k in ("pearls", "spawns", "dex", "settings", "stats", "earned_total", "themes", "theme", "shinies",
                  "tree", "spots", "mystery", "seasonal_owned"):
            if k in keep:
                s[k] = keep[k]
        # pearl tree perks that shape a new season
        hs = tlv(s, "headstart")
        if hs:
            s["upgrades"]["tank"] = hs
            s["bubbles"] = 1000.0 * 20 ** (hs - 1)
        if tlv(s, "seasoned"):
            s["upgrades"]["filter"] = 3 * tlv(s, "seasoned")
        if tlv(s, "keeptoys"):
            s["toys"] = {k: dict(v) for k, v in keep.get("toys", {}).items()}
    add_fish(s, "sunflower", name="Sunny", shiny=False)
    return s


# ---------------------------------------------------------------- pearl tree
def tlv(s, nid):
    return s.get("tree", {}).get(nid, 0)


def tree_cost(s, nid):
    n = PEARL_TREE_BY_ID[nid]
    return n["cost"] + n["grow"] * tlv(s, nid)


def tree_state(s, nid):
    """'max' | 'locked' | 'ok' | 'poor'"""
    n = PEARL_TREE_BY_ID[nid]
    if tlv(s, nid) >= n["max"]:
        return "max"
    if n["req"] and tlv(s, n["req"]) < 1:
        return "locked"
    return "ok" if s["pearls"] >= tree_cost(s, nid) else "poor"


def tree_buy(s, nid):
    if tree_state(s, nid) != "ok":
        return False
    s["pearls"] -= tree_cost(s, nid)
    s.setdefault("tree", {})[nid] = tlv(s, nid) + 1
    return True


def random_look(seed=None):
    """(tone, hue, pattern seed, length) - small differences so every fish is recognisable"""
    r = random.Random(seed) if seed is not None else random
    return [r.randint(-2, 2), r.randint(-1, 1), r.randint(0, 3), r.choice((-1, 0, 0, 1))]


def fish_look(f):
    """full look tuple for drawing, including whiskers that grow with age (every 10 levels, up to +3)"""
    if not f.get("look"):
        f["look"] = random_look(f.get("uid", 0) * 7919)
    return tuple(f["look"]) + (min(3, f["lv"] // 10),)


def shiny_chance(s):
    return SHINY_CHANCE + 0.005 * ulv(s, "lucky") + 0.01 * tlv(s, "shiny") + 0.01 * ulv(s, "bait")


def add_fish(s, sp_id, name=None, shiny=None):
    f = make_fish(s, sp_id, name, shiny)
    s["fish"].append(f)
    if sp_id in SEASONAL_BY_ID:
        if sp_id not in s.setdefault("seasonal_owned", []):
            s["seasonal_owned"].append(sp_id)      # remembered forever, even after Spawning Season
    elif sp_id not in s["dex"]:
        s["dex"].append(sp_id)
    return f


# ---------------------------------------------------------------- seasons
def today():
    """the computer's date; tests can set DA_DATE=YYYY-MM-DD"""
    fake = os.environ.get("DA_DATE")
    if fake:
        return datetime.date.fromisoformat(fake)
    return datetime.date.today()


def in_season(season, day=None):
    d = day or today()
    se = SEASONS[season]
    md = (d.month, d.day)
    if se["start"] <= se["end"]:
        return se["start"] <= md <= se["end"]
    return md >= se["start"] or md <= se["end"]          # seasons that wrap past New Year


def seasonal_fish_buyable(s, sp_id):
    """'ok' | 'owned' (one per tank) | 'season' (not its season and you never had one)"""
    sp = SEASONAL_BY_ID[sp_id]
    if owned_count(s, sp_id):
        return "owned"
    if in_season(sp["season"]) or sp_id in s.get("seasonal_owned", []):
        return "ok"
    return "season"


def theme_visible(s, tid):
    th = THEMES_BY_ID[tid]
    return not th.get("season") or tid in s.get("themes", []) or in_season(th["season"])


def theme_cost(s, tid):
    th = THEMES_BY_ID[tid]
    if th.get("cost_secs"):
        return max(th["cost"], income(s) * th["cost_secs"])
    return th["cost"]


def best_regular_rate(s):
    rates = [SPECIES_BY_ID[f["sp"]]["rate"] for f in s["fish"] if f["sp"] not in SEASONAL_BY_ID]
    return max(rates, default=1.0)


def rub_secs(s):
    return RUB_BASE + ulv(s, "rub")


def make_fish(s, sp_id, name=None, shiny=None):
    """a new fish dict (not yet in the tank)"""
    taken = {f["name"] for f in s["fish"]}
    if name is None:
        pool = [n for n in FISH_NAMES if n not in taken] or FISH_NAMES
        name = random.choice(pool)
    if shiny is None:
        shiny = random.random() < shiny_chance(s)
    f = dict(uid=s["next_uid"], sp=sp_id, name=name, lv=1, xp=0.0, full=80.0, happy=70.0, shiny=bool(shiny),
             look=random_look(s["next_uid"]))
    if shiny and sp_id not in s.setdefault("shinies", []):
        s["shinies"].append(sp_id)
    s["next_uid"] += 1
    return f


# ---------------------------------------------------------------- levels
def ulv(s, uid):
    return s["upgrades"].get(uid, 0)


def toy_lv(s, tid):
    t = s["toys"].get(tid)
    return t["lv"] if t else 0


def capacity(s):
    return TANK_CAPACITY[ulv(s, "tank")] + 2 * ulv(s, "infinity")


def owned_count(s, sp_id):
    return sum(1 for f in s["fish"] if f["sp"] == sp_id)


# ---------------------------------------------------------------- costs
def species_cost(s, sp_id):
    sp = SPECIES_BY_ID[sp_id]
    if sp_id in SEASONAL_BY_ID:
        return max(sp["cost_min"], income(s) * sp["cost_secs"])
    return sp["cost"] * COPY_GROWTH ** owned_count(s, sp_id)


def upgrade_cost(s, uid):
    u = UPGRADES_BY_ID[uid]
    if u.get("cost_secs"):                       # seasonal: priced from your income, so useful at any stage
        return max(u["base"], income(s) * u["cost_secs"]) * u["growth"] ** ulv(s, uid)
    return u["base"] * u["growth"] ** ulv(s, uid)


def seasonal_ok(s, item):
    """seasonal toy/upgrade: for sale in its season, or any time once you've owned one"""
    return (not item.get("season") or in_season(item["season"])
            or item["id"] in s.get("seasonal_owned", []))


def remember_seasonal(s, item):
    if item.get("season") and item["id"] not in s.setdefault("seasonal_owned", []):
        s["seasonal_owned"].append(item["id"])


def toy_cost(s, tid):
    t = TOYS_BY_ID[tid]
    if t.get("cost_secs"):
        return max(t["cost"], income(s) * t["cost_secs"]) * TOY_LEVEL_GROWTH ** toy_lv(s, tid)
    return t["cost"] * TOY_LEVEL_GROWTH ** toy_lv(s, tid)


def food_cost(s, fid):
    f = FOODS_BY_ID[fid]
    if f["secs"] == 0:
        return 0
    return max(f["min"], income(s) * f["secs"])


def rehome_refund(s, fish):
    sp = SPECIES_BY_ID[fish["sp"]]
    if fish["sp"] in SEASONAL_BY_ID:
        return sp["cost_min"]
    return sp["cost"] * COPY_GROWTH ** max(0, owned_count(s, fish["sp"]) - 1) * 0.3


# ---------------------------------------------------------------- output
def xp_needed(lv):
    return 12 * lv ** 2.3


def level_mult(lv):
    return 1 + 0.15 * (lv - 1)


def happy_mult(s, h):
    if "bliss" in s["buffs"]:
        h = 100
    return 1 + 0.4 * h / 100          # happiness is only ever a bonus


def hunger_mult(full):
    return 1.0 if full > 0 else 0.7   # starving fish slow down, but idle play stays fine


GROW_TIME = 240.0          # seconds for a hatched baby to grow from fry to full size


def growth(f):
    """0.0 = just hatched (tiny fry) .. 1.0 = fully grown"""
    if not f.get("grow"):
        return 1.0
    return max(0.0, 1.0 - f["grow"] / GROW_TIME)


def start_growing(f):
    f["grow"] = GROW_TIME


def tick_growth(s, dt):
    """returns the fish that just finished growing up"""
    done = []
    for f in s["fish"]:
        if f.get("grow"):
            f["grow"] = max(0.0, f["grow"] - dt)
            if f["grow"] <= 0:
                del f["grow"]
                done.append(f)
    return done


def fish_rate(s, f):
    sp = SPECIES_BY_ID[f["sp"]]
    shiny = 2.0 if f.get("shiny") else 1.0
    young = 0.25 + 0.75 * growth(f)      # babies earn more as they grow
    base = sp["rate"] * sp["best_mult"] * best_regular_rate(s) if sp.get("season") else sp["rate"]
    return (base * level_mult(f["lv"]) * happy_mult(s, f["happy"]) * hunger_mult(f["full"]) * shiny
            * young)


def toy_bonus(s):
    return sum(TOYS_BY_ID[t]["bonus"] * v["lv"] for t, v in s["toys"].items()) / 100


def global_mult(s):
    m = (1 + 0.2 * ulv(s, "filter"))
    m *= 1 + 0.15 * ulv(s, "conditioner")
    m *= 1 + 0.08 * ulv(s, "plants")
    m *= 1 + 0.5 * ulv(s, "abyss")
    m *= 1 + 0.02 * len(s["fish"]) * ulv(s, "school")
    m *= 1 + toy_bonus(s)
    m *= 1 + 0.03 * len(s["dex"])
    m *= 1 + sum(THEMES_BY_ID[t]["bonus"] for t in s.get("themes", []) if t in THEMES_BY_ID) / 100
    m *= 1 + PEARL_BONUS * tlv(s, "gills")
    m *= 1 + 0.10 * ulv(s, "ghostglow")
    if "double" in s["buffs"]:
        m *= 2
    return m


_draw_cache = None      # while a frame is being drawn nothing changes, so income is worked out once


def cache_on():
    global _draw_cache
    _draw_cache = {}


def cache_off():
    global _draw_cache
    _draw_cache = None


def income(s):
    if _draw_cache is not None and id(s) in _draw_cache:
        return _draw_cache[id(s)]
    g = global_mult(s)
    v = sum(fish_rate(s, f) for f in s["fish"]) * g
    if _draw_cache is not None:
        _draw_cache[id(s)] = v
    return v


def pop_value(s):
    return (max(3.0, income(s) * 12) * (1 + 0.35 * ulv(s, "magnet")) * (1 + 0.25 * tlv(s, "lucky"))
            * (1 + ulv(s, "polish")) * (1 + 0.4 * ulv(s, "spooky")))


def pop_interval(s):
    t = 6.0 * 0.88 ** ulv(s, "bubbler")
    if toy_lv(s, "airstone"):
        t /= 1 + 0.05 * toy_lv(s, "airstone") + 0.15
    if "frenzy" in s["buffs"]:
        t /= 4
    return t


def golden_chance(s):
    return 0.03 + 0.015 * ulv(s, "lucky") + 0.01 * tlv(s, "lucky")


# ---------------------------------------------------------------- scale jar
def jar_rate(s):
    """scales/sec the jar fills with (a bonus on top of normal income)"""
    lv = ulv(s, "jar")
    return (income(s) * (0.4 + 0.05 * lv) * (1 + 0.1 * tlv(s, "deepjar")) * (1 + 0.25 * ulv(s, "timecrystal"))
            if lv else 0.0)


def jar_minutes(s):
    return 20 + 6 * ulv(s, "jar") + 20 * tlv(s, "deepjar")


def jar_cap(s):
    return jar_rate(s) * 60 * jar_minutes(s)


def tick_jar(s, dt):
    if ulv(s, "jar"):
        s["jar"] = min(jar_cap(s), s.get("jar", 0.0) + jar_rate(s) * dt)


def collect_jar(s):
    amt = s.get("jar", 0.0)
    s["jar"] = 0.0
    if amt > 0:
        earn(s, amt)
    return amt


# ---------------------------------------------------------------- hatchery
def egg_slots(s):
    lv = ulv(s, "hatchery")
    return 0 if lv == 0 else 1 + (lv - 1) // 3 + tlv(s, "brood")


def hatch_speed(s):
    return 0.92 ** max(0, ulv(s, "hatchery") - 1) * 0.9 ** tlv(s, "hatch") * 0.9 ** ulv(s, "timecrystal")


def hatch_bonus(s):
    return 1 + 0.1 * max(0, ulv(s, "hatchery") - 1)


def clutch_time(s, cid):
    return CLUTCHES_BY_ID[cid]["mins"] * 60 * hatch_speed(s)


def clutch_reward(s, egg):
    """scales gifted when this clutch hatches"""
    c = CLUTCHES_BY_ID[egg["c"]]
    return max(egg.get("inc", 0), income(s)) * c["gift"] * hatch_bonus(s)


def clutch_levels(s, cid):
    return CLUTCHES_BY_ID[cid]["levels"] * hatch_bonus(s)


def lay(s, cid):
    """laying eggs is free; only limited by nest slots (Mystery Eggs come from your stash)"""
    if len(s["eggs"]) >= egg_slots(s):
        return False
    if cid == "mystery":
        if s.get("mystery", 0) <= 0:
            return False
        s["mystery"] -= 1
    t = clutch_time(s, cid)
    s["eggs"].append(dict(c=cid, left=t, total=t, inc=income(s)))
    return True


def add_levels(s, f, n):
    """give fish `f` n levels of progress (fractions become XP). returns levels gained"""
    whole = int(n)
    f["lv"] += whole
    return whole + gain_xp(s, f, (n - whole) * xp_needed(f["lv"]))


def tick_eggs(s, dt):
    for e in s["eggs"]:
        e["left"] = max(0.0, e["left"] - dt)


def clutch_odds(s, cid):
    """(chance nothing hatches, chance a baby catfish hatches)"""
    c = CLUTCHES_BY_ID[cid]
    fl = tlv(s, "fertile")
    return c["empty"] * (1 - 0.15 * fl), min(1.0, c["baby"] + 0.08 * fl)


def pick_baby_species(s, cid):
    """a species already in the tank; higher tiers are rarer (golden clutches less so)"""
    owned = sorted({f["sp"] for f in s["fish"] if f["sp"] not in SEASONAL_BY_ID})
    if not owned:
        return None
    power = 0.7 if cid == "golden" else 1.4
    weights = [1 / (SPECIES_BY_ID[sp]["tier"] + 1) ** power for sp in owned]
    return random.choices(owned, weights=weights)[0]


def nursery(s, key, n=1):
    st = s["stats"]
    st[key] = st.get(key, 0) + n


def add_baby(s, sp, shiny=None):
    """a hatchling: straight into the tank (growing) or waiting for room"""
    baby = make_fish(s, sp, shiny=shiny)
    baby["hatched"] = True
    if sp not in s["dex"]:
        s["dex"].append(sp)
    if len(s["fish"]) < capacity(s):
        start_growing(baby)
        s["fish"].append(baby)
    else:
        s.setdefault("pending", []).append(baby)
    nursery(s, "babies")
    if baby.get("shiny"):
        nursery(s, "shiny_babies")
    return baby


def hatch_mystery(s, egg):
    """anything can come out of a Mystery Egg"""
    nursery(s, "mystery_hatched")
    r = random.random()
    if r < 0.20:
        nursery(s, "empty_eggs")
        return dict(amt=0.0, empty=True, baby=None, mystery="empty")
    if r < 0.45:
        amt = max(egg.get("inc", 0), income(s)) * 1800 * hatch_bonus(s)
        earn(s, amt)
        return dict(amt=amt, empty=False, baby=None, mystery="scales")
    if r < 0.65:
        for f in s["fish"]:
            add_levels(s, f, 2.0 * hatch_bonus(s))
        return dict(amt=0.0, empty=False, baby=None, mystery="levels")
    if r < 0.88:
        sp = pick_baby_species(s, "golden")
        if sp:
            return dict(amt=0.0, empty=False, baby=add_baby(s, sp, shiny=random.random() < 0.25), mystery="baby")
    # rare: a species you haven't discovered yet (the next one up)
    best = max((SPECIES_BY_ID[x]["tier"] for x in s["dex"]), default=0)
    nxt = [sp for sp in SPECIES if sp["tier"] == best + 1]
    if nxt:
        return dict(amt=0.0, empty=False, baby=add_baby(s, nxt[0]["id"]), mystery="rare")
    sp = pick_baby_species(s, "golden")
    return dict(amt=0.0, empty=False, baby=add_baby(s, sp, shiny=True) if sp else None, mystery="baby")


def hatch(s, egg):
    """returns dict(amt, empty, baby). A baby that doesn't fit waits in s['pending']."""
    s["eggs"].remove(egg)
    nursery(s, "eggs_hatched")
    if egg["c"] == "mystery":
        return hatch_mystery(s, egg)
    p_empty, p_baby = clutch_odds(s, egg["c"])
    if random.random() < p_empty:
        nursery(s, "empty_eggs")
        return dict(amt=0.0, empty=True, baby=None)
    amt = clutch_reward(s, egg)
    lv = clutch_levels(s, egg["c"])
    earn(s, amt)
    for f in s["fish"]:
        add_levels(s, f, lv)
    baby = None
    if random.random() < p_baby:
        sp = pick_baby_species(s, egg["c"])
        if sp:
            shiny = None
            if egg["c"] == "golden":       # Golden Eggs: much better shiny odds
                shiny = random.random() < min(0.5, shiny_chance(s) * GOLDEN_EGG_SHINY)
            baby = add_baby(s, sp, shiny=shiny)
    return dict(amt=amt, empty=False, baby=baby)


def upgrade_visible(s, uid):
    """far-off late-game upgrades stay hidden until you're within reach of them"""
    u = UPGRADES_BY_ID[uid]
    if u.get("season"):
        return ulv(s, uid) > 0 or seasonal_ok(s, u)
    return ulv(s, uid) > 0 or u["base"] <= max(s["earned_total"], s["bubbles"]) * 50


def sell_value(s, f):
    return rehome_refund(s, f)


def hands_mult(s):
    return 1 + 0.3 * ulv(s, "hands")


def pet_reward(s, f):
    return max(1.0, fish_rate(s, f) * global_mult(s) * 2.5 * hands_mult(s))


def drain_mult(s):
    return 0.88 ** ulv(s, "heater")


FULL_DRAIN = 100 / 1800     # empty in 30 min
HAPPY_DRAIN = 100 / 2700    # empty in 45 min


PUMP_EFF = 0.15             # toy payout bonus per Current Pump level
PLAY_PULSE = 2.0            # seconds of play per payout


def toy_play_value(s, f, tid):
    """scales paid out each time fish `f` finishes a play pulse with toy `tid`"""
    t = TOYS_BY_ID[tid]
    lv = max(1, toy_lv(s, tid))
    pump = (1 + PUMP_EFF * ulv(s, "pump")) * (1 + 0.25 * tlv(s, "playful")) * (1 + 0.5 * ulv(s, "current"))
    return max(1.0, fish_rate(s, f) * global_mult(s) * t["pay"] * (1 + 0.5 * (lv - 1)) * pump)


def passive_xp(s):
    return 0.06 * ulv(s, "light")


def offline_terms(s):
    pct = 0.2 + 0.1 * ulv(s, "care")
    hours = min(12, 2 + 1.25 * ulv(s, "care"))
    return pct, hours


def pearls_for(s):
    if s["earned_run"] < SPAWN_MIN:
        return 0
    return int(5 * math.sqrt(s["earned_run"] / SPAWN_MIN))


# ---------------------------------------------------------------- mutations
MAX_SCALES = 1e300       # numbers stop just short of where the computer's maths gives up (~1.8e308)


def earn(s, amt):
    s["bubbles"] = min(MAX_SCALES, s["bubbles"] + amt)
    s["earned_run"] = min(MAX_SCALES, s["earned_run"] + amt)
    s["earned_total"] = min(MAX_SCALES, s["earned_total"] + amt)


def spend(s, amt):
    if s["bubbles"] + 1e-9 < amt:
        return False
    s["bubbles"] -= amt
    return True


def gain_xp(s, f, amt):
    """returns number of levels gained"""
    f["xp"] += amt
    ups = 0
    while f["xp"] >= xp_needed(f["lv"]):
        f["xp"] -= xp_needed(f["lv"])
        f["lv"] += 1
        ups += 1
    return ups


def tick_needs(s, dt):
    """drain/regen needs and passive xp. returns list of (fish, levels gained)."""
    ups = []
    for name in list(s["buffs"]):
        s["buffs"][name] -= dt
        if s["buffs"][name] <= 0:
            del s["buffs"][name]
    pxp = passive_xp(s)
    dm = drain_mult(s)
    for f in s["fish"]:
        if not s["chill"]:
            f["full"] = max(0.0, f["full"] - FULL_DRAIN * dm * dt)
            f["happy"] = max(0.0, f["happy"] - HAPPY_DRAIN * dm * dt)
        if pxp:
            n = gain_xp(s, f, pxp * dt)
            if n:
                ups.append((f, n))
    return ups


def apply_offline(s, now=None):
    """credit earnings while closed. returns (seconds, amount)."""
    now = now or time.time()
    away = max(0.0, now - s.get("last_time", now))
    # eggs and the jar keep going for every second the game was closed, even short breaks
    tick_jar(s, away)
    tick_eggs(s, away)
    tick_growth(s, away)                 # babies keep growing while the game is closed
    if away < 60:
        return away, 0.0
    pct, hours = offline_terms(s)
    secs = min(away, hours * 3600)
    # assume fish were looked after by the sitter at their current state
    amt = income(s) * secs * pct
    earn(s, amt)
    if not s["chill"]:
        dm = drain_mult(s)
        floor = 35.0 if ulv(s, "feeder") else 0.0
        for f in s["fish"]:
            f["full"] = max(min(f["full"], floor), f["full"] - FULL_DRAIN * dm * away)
            f["happy"] = max(0.0, f["happy"] - HAPPY_DRAIN * dm * away * 0.5)
    for b in list(s["buffs"]):
        s["buffs"][b] -= away
        if s["buffs"][b] <= 0:
            del s["buffs"][b]
    return away, amt


def species_visible(s, i):
    """shop shows owned/discovered species, plus the next two tiers."""
    best = max((SPECIES_BY_ID[x]["tier"] for x in s["dex"]), default=0)
    return i <= best + 2


def species_known(s, i):
    best = max((SPECIES_BY_ID[x]["tier"] for x in s["dex"]), default=0)
    return i <= best + 1


def _units():
    """short names for 10^3 ... 10^303: K, M, B, T, Qa ... Dc (decillion), Vg (vigintillion),
    Tg (trigintillion) ... Ng (nonagintillion), Ce (centillion)"""
    ones = ["", "U", "D", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No"]
    tens = ["", "Dc", "Vg", "Tg", "Qag", "Qig", "Sxg", "Spg", "Og", "Ng"]
    out = ["K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No"]       # 10^3 .. 10^30
    for n in range(10, 100):                                               # n-illion, 10^(3n+3)
        o, t = n % 10, n // 10
        out.append(tens[t] if o == 0 else ones[o] + (tens[t].lower() if t > 1 else "d"))
    out.append("Ce")                                                       # centillion, 10^303
    return out


UNITS = _units()


def fmt(n):
    if n < 1000:
        if n < 10 and n != int(n):
            return f"{n:.1f}"
        return f"{int(n)}"
    if n != n or n == float("inf"):
        return "MAX"
    e = int(math.log10(n) // 3)
    if e > len(UNITS):
        return f"{n:.2e}".replace("e+", "e")
    v = n / 1000 ** e
    if v >= 999.5 and e < len(UNITS):          # 999.7K would round to "1000K": show 1.00M instead
        e, v = e + 1, v / 1000
    s = f"{v:.2f}" if v < 10 else f"{v:.1f}" if v < 100 else f"{int(v)}"
    return s + UNITS[e - 1]


def fmt_time(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m {sec % 60:02d}s"
    return f"{sec // 3600}h {sec % 3600 // 60:02d}m"


