"""School-day pacing sim: a short play burst, then 45 min of class with the game left running,
then ~6 min of play, repeat. Run: python sim_school.py [hours] [first_session_min]
The player only buys things while 'at the desk'. Jar and eggs are simulated for real."""
import sys

from purrfin import economy as E
from purrfin.data import SPECIES, TOYS, UPGRADES_BY_ID, TOY_MAX_LEVEL, TOYS_BY_ID, CLUTCHES

HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 7
FIRST = float(sys.argv[2]) if len(sys.argv) > 2 else 15
AWAY = 45 * 60
DESK = 6 * 60
STEP = 5
PLAY_SHARE = 0.45


def play_income(s):
    if not s["toys"]:
        return 0.0
    pump = 1 + E.PUMP_EFF * E.ulv(s, "pump")
    avg = sum(TOYS_BY_ID[t]["pay"] * (1 + 0.5 * (v["lv"] - 1)) for t, v in s["toys"].items()) / len(s["toys"])
    return E.income(s) * PLAY_SHARE / E.PLAY_PULSE * avg * pump


def live_income(s, active):
    """what actually flows in per second right now"""
    base = E.income(s)
    pops = (active + (1 - active) * 0.3) * E.pop_value(s) / E.pop_interval(s)
    best = max(s["fish"], key=lambda f: E.fish_rate(s, f))
    pets = 0.6 * active * E.pet_reward(s, best)
    return base + pops + pets + play_income(s)


def value_income(s):
    """income used to score purchases: average over a play+class cycle, incl. jar & eggs"""
    v = live_income(s, 0.12) + E.jar_rate(s) * 0.85
    if E.egg_slots(s):
        c = CLUTCHES[1]
        v += E.egg_slots(s) * E.income(s) * c["gift"] / (c["mins"] * 60 * E.hatch_speed(s)) * E.hatch_bonus(s)
        v += E.egg_slots(s) * E.income(s) * 0.05 * E.hatch_bonus(s)   # rough value of the level-ups
    return v


def apply(s, o):
    kind, key = o
    if kind == "fish":
        removed = None
        if len(s["fish"]) >= E.capacity(s):
            removed = min(s["fish"], key=lambda f: E.fish_rate(s, f))
            s["fish"].remove(removed)
        dex = list(s["dex"])
        f = E.add_fish(s, key)

        def undo():
            s["fish"].remove(f)
            s["dex"][:] = dex
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
    return E.species_cost(s, key) if kind == "fish" else E.upgrade_cost(s, key) if kind == "up" else E.toy_cost(s, key)


def best_option(s):
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
    base = value_income(s)
    best = None
    for o in opts:
        c = cost(s, o)
        undo = apply(s, o)
        gain = value_income(s) - base
        undo()
        if o == ("up", "tank"):
            gain = max(gain, base * 0.15)
        if o[0] == "up" and o[1] in ("heater", "feeder", "care", "light", "bubbler", "lucky", "hands", "magnet"):
            gain = max(gain, base * 0.02)
        if gain <= 0:
            continue
        sc = c / gain
        if best is None or sc < best[0]:
            best = (sc, c, o)
    return best


def shop(s):
    for _ in range(60):
        b = best_option(s)
        if not b or s["bubbles"] < b[1]:
            return
        E.spend(s, b[1])
        apply(s, b[2])


def lay_eggs(s, leaving):
    while len(s["eggs"]) < E.egg_slots(s):
        cid = "class" if leaving else "quick"
        if leaving and E.ulv(s, "hatchery") >= 4 and len(s["eggs"]) == E.egg_slots(s) - 1:
            cid = "golden"
        E.lay(s, cid)


def main():
    s = E.new_state()
    firsts = {}
    t = 0
    sessions = []
    # schedule: (start, end, at_desk)
    sched = [(0, FIRST * 60, True)]
    while sched[-1][1] < HOURS * 3600:
        a = sched[-1][1]
        sched.append((a, a + AWAY, False))
        sched.append((a + AWAY, a + AWAY + DESK, True))
    for start, end, desk in sched:
        if desk:
            E.collect_jar(s)
            for e in [e for e in s["eggs"] if e["left"] <= 0]:
                E.hatch(s, e)
        bought_before = len(s["dex"])
        t = start
        while t < end and t < HOURS * 3600:
            act = 0.8 if desk else 0.0
            for f in s["fish"]:
                f["happy"] = 80 if desk else max(30, f["happy"] - 0.01 * STEP)
                f["full"] = 60
            E.tick_needs(s, STEP)
            E.earn(s, live_income(s, act) * STEP)
            E.tick_jar(s, STEP)
            E.tick_eggs(s, STEP)
            best = max(s["fish"], key=lambda f: E.fish_rate(s, f))
            E.gain_xp(s, best, 0.6 * act * 1.5 * E.hands_mult(s) * STEP)
            for f in s["fish"]:
                E.gain_xp(s, f, (0.02 + (0.036 if s["toys"] else 0)) * STEP)
            if desk:
                for e in [e for e in s["eggs"] if e["left"] <= 0]:
                    E.hatch(s, e)
                s["pending"] = []
                shop(s)
                lay_eggs(s, leaving=False)
            for sp in s["dex"]:
                firsts.setdefault(sp, t)
            t += STEP
        if desk:
            lay_eggs(s, leaving=True)
            sessions.append((start / 3600, len(s["dex"]), E.fmt(live_income(s, 0)), E.fmt(s["bubbles"])))
    print("species unlocks:")
    for sp in SPECIES:
        print(f"  {sp['name']:22s} {E.fmt_time(firsts[sp['id']]) if sp['id'] in firsts else '(not yet)':>10s}")
    print("\ndesk sessions (hour, species owned, idle income/s):")
    for h, n, inc, b in sessions:
        print(f"  {h:4.2f}h  species {n:2d}  income {inc}/s")
    print("final upgrades", s["upgrades"])
    print("toys", {k: v["lv"] for k, v in s["toys"].items()})


if __name__ == "__main__":
    main()
