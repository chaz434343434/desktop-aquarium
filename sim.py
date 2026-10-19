"""Rough progression simulator for tuning data.py.
Run: python sim.py [active 0..1] [hours]
active = how much the player interacts (share of bubbles popped by hand, petting).
"""
import sys

from purrfin import economy as E
from purrfin.data import SPECIES, TOYS, UPGRADES_BY_ID, TOY_MAX_LEVEL, TOYS_BY_ID

ACTIVE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
HOURS = float(sys.argv[2]) if len(sys.argv) > 2 else 24
PETS_PER_SEC = 0.6 * ACTIVE
PLAY_SHARE = 0.45          # share of time a fish spends playing when toys exist
STEP = 5                   # seconds per sim step


def play_income(s):
    if not s["toys"]:
        return 0.0
    avg = sum(TOYS_BY_ID[t]["pay"] * (1 + 0.5 * (v["lv"] - 1)) for t, v in s["toys"].items()) / len(s["toys"])
    return E.income(s) * PLAY_SHARE / E.PLAY_PULSE * avg


def total_income(s):
    base = E.income(s)
    pops = (ACTIVE + (1 - ACTIVE) * 0.3) * E.pop_value(s) / E.pop_interval(s)
    best = max(s["fish"], key=lambda f: E.fish_rate(s, f))
    pets = PETS_PER_SEC * E.pet_reward(s, best)
    return base + pops + pets + play_income(s)


def apply(s, o):
    """apply option, return undo function"""
    kind, key = o
    if kind == "fish":
        removed = None
        if len(s["fish"]) >= E.capacity(s):
            removed = min(s["fish"], key=lambda f: E.fish_rate(s, f))
            s["fish"].remove(removed)
        f = E.add_fish(s, key)
        newdex = s["dex"][-1] == key and s["dex"].count(key) == 1

        def undo():
            s["fish"].remove(f)
            if removed:
                s["fish"].append(removed)
        return undo
    if kind == "up":
        s["upgrades"][key] = E.ulv(s, key) + 1

        def undo():
            s["upgrades"][key] -= 1
        return undo
    had = key in s["toys"]
    s["toys"].setdefault(key, dict(lv=0, x=0.5))["lv"] += 1

    def undo():
        s["toys"][key]["lv"] -= 1
        if not had:
            del s["toys"][key]
    return undo


def cost(s, o):
    kind, key = o
    if kind == "fish":
        return E.species_cost(s, key)
    if kind == "up":
        return E.upgrade_cost(s, key)
    return E.toy_cost(s, key)


def options(s):
    opts = []
    for sp in SPECIES:
        if E.species_visible(s, sp["tier"]) and E.species_known(s, sp["tier"]):
            opts.append(("fish", sp["id"]))
    for uid, u in UPGRADES_BY_ID.items():
        if E.ulv(s, uid) < u["max"]:
            opts.append(("up", uid))
    unowned = 0
    for t in TOYS:
        if t["id"] not in s["toys"]:
            unowned += 1
            if unowned > 2:
                continue
        if E.toy_lv(s, t["id"]) < TOY_MAX_LEVEL:
            opts.append(("toy", t["id"]))
    base = total_income(s)
    scored = []
    for o in opts:
        c = cost(s, o)
        dex_before = list(s["dex"])
        undo = apply(s, o)
        gain = total_income(s) - base
        undo()
        s["dex"][:] = dex_before
        kind, key = o
        if o == ("up", "tank"):
            gain = max(gain, base * 0.15)      # room for a new fish is worth it
        if kind == "up" and key in ("heater", "feeder", "care", "light", "bubbler"):
            gain = max(gain, base * 0.03)
        if gain <= 0:
            continue
        scored.append((c / gain, c, o))
    scored.sort()
    return scored


def main():
    s = E.new_state()
    firsts = {}
    t = 0
    pearl_t = None
    while t < HOURS * 3600:
        for f in s["fish"]:
            f["happy"] = 40 + 50 * ACTIVE
            f["full"] = 60
        E.tick_needs(s, STEP)
        E.earn(s, total_income(s) * STEP)
        best = max(s["fish"], key=lambda f: E.fish_rate(s, f))
        E.gain_xp(s, best, PETS_PER_SEC * 1.5 * E.hands_mult(s) * STEP)
        for f in s["fish"]:
            E.gain_xp(s, f, (0.02 + ACTIVE * 0.02 + (0.08 * PLAY_SHARE if s["toys"] else 0)) * STEP)
        for _ in range(20):
            sc = options(s)
            if not sc or s["bubbles"] < sc[0][1]:
                break
            o = sc[0][2]
            c = cost(s, o)
            E.spend(s, c)
            apply(s, o)
        for sp in s["dex"]:
            firsts.setdefault(sp, t)
        if pearl_t is None and E.pearls_for(s) >= 5:
            pearl_t = t
        t += STEP
    for sp in SPECIES:
        print(f"{sp['name']:24s} {E.fmt_time(firsts[sp['id']]) if sp['id'] in firsts else '(never)':>10s}")
    print("spawn ready at", E.fmt_time(pearl_t) if pearl_t else "never")
    print("final income", E.fmt(total_income(s)), "fish", len(s["fish"]), "up", s["upgrades"],
          "toys", {k: v["lv"] for k, v in s["toys"].items()})


if __name__ == "__main__":
    main()
