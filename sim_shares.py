"""Where does the money come from? Runs sim.py's player and prints, at a few points in the game,
how much of the income comes from fish, bubbles, toys and petting.
Run: python sim_shares.py [hours] [active 0..1]"""
import os
import sys

sys.argv = [sys.argv[0], sys.argv[2] if len(sys.argv) > 2 else "0.5", sys.argv[1] if len(sys.argv) > 1 else "120"]
import sim  # noqa: E402
from purrfin import economy as E  # noqa: E402

sim.STEP = int(os.environ.get("SIM_STEP", "60"))


def shares(s):
    fish = E.fish_income(s) if hasattr(E, "fish_income") else E.income(s)
    pops = (sim.ACTIVE + (1 - sim.ACTIVE) * 0.3) * E.pop_value(s) / E.pop_interval(s)
    pops *= 1 + 9 * E.golden_chance(s)
    best = max(s["fish"], key=lambda f: E.fish_rate(s, f))
    pets = sim.PETS_PER_SEC * E.pet_reward(s, best)
    toys = sim.play_income(s)
    tot = fish + pops + pets + toys
    return {k: v / tot for k, v in (("fish", fish), ("bubbles", pops), ("toys", toys), ("pets", pets))}, tot


def main():
    s = E.new_state()
    marks = [0.25, 1, 3, 6, 12, 24, 48, 96, 150, 200]
    t = 0
    firsts = {}
    while t < sim.HOURS * 3600:
        for f in s["fish"]:
            f["happy"] = 40 + 50 * sim.ACTIVE
            f["full"] = 60
        E.tick_needs(s, sim.STEP)
        E.earn(s, sim.total_income(s) * sim.STEP)
        for f in s["fish"]:
            E.gain_xp(s, f, (0.02 + sim.ACTIVE * 0.02 + 0.08 * sim.PLAY_SHARE) * sim.STEP)
        for _ in range(20):
            sc = sim.options(s)
            if not sc or s["bubbles"] < sc[0][1]:
                break
            o = sc[0][2]
            E.spend(s, sim.cost(s, o))
            sim.apply(s, o)
        for sp in s["dex"]:
            firsts.setdefault(sp, t)
        if marks and t >= marks[0] * 3600:
            sh, tot = shares(s)
            print(f"{marks.pop(0):6.2f}h  species {len(s['dex']):3d}  income {E.fmt(tot):>8s}/s   " +
                  "  ".join(f"{k} {v * 100:5.1f}%" for k, v in sh.items()), flush=True)
        t += sim.STEP
    print("species reached:", len(s["dex"]))


if __name__ == "__main__":
    main()
