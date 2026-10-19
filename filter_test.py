"""Balance check for the Canister Filter. Run: python filter_test.py [active] [hours]
Compares a normal run against one where the filter can't be bought, and reports how
much of the player's spending and income the filter accounts for over time."""
import sys

import sim
from purrfin import economy as E
from purrfin.data import UPGRADES_BY_ID, SPECIES

HOURS = float(sys.argv[2]) if len(sys.argv) > 2 else 12
CHECKS = [0.25, 0.5, 1, 2, 4, 8, 12]


def run(no_filter=False):
    s = E.new_state()
    t = 0
    spend = {}
    picks = {}
    log = []
    nxt = 0
    firsts = {}
    while t < HOURS * 3600:
        for f in s["fish"]:
            f["happy"] = 40 + 50 * sim.ACTIVE
            f["full"] = 60
        E.tick_needs(s, sim.STEP)
        E.earn(s, sim.total_income(s) * sim.STEP)
        best = max(s["fish"], key=lambda f: E.fish_rate(s, f))
        E.gain_xp(s, best, sim.PETS_PER_SEC * 1.5 * E.hands_mult(s) * sim.STEP)
        for f in s["fish"]:
            E.gain_xp(s, f, (0.02 + sim.ACTIVE * 0.02 + (0.08 * sim.PLAY_SHARE if s["toys"] else 0)) * sim.STEP)
        for _ in range(20):
            sc = [x for x in sim.options(s) if not (no_filter and x[2] == ("up", "filter"))]
            if not sc or s["bubbles"] < sc[0][1]:
                break
            o = sc[0][2]
            c = sim.cost(s, o)
            E.spend(s, c)
            sim.apply(s, o)
            key = o[1] if o[0] == "up" else o[0]
            spend[key] = spend.get(key, 0) + c
            picks[key] = picks.get(key, 0) + 1
        for sp in s["dex"]:
            firsts.setdefault(sp, t)
        if nxt < len(CHECKS) and t >= CHECKS[nxt] * 3600:
            fl = E.ulv(s, "filter")
            others = E.global_mult(s) / (1 + 0.2 * fl)
            log.append((CHECKS[nxt], fl, 1 + 0.2 * fl, others, sim.total_income(s)))
            nxt += 1
        t += sim.STEP
    return log, spend, picks, firsts, s


def main():
    log, spend, picks, firsts, s = run()
    log2, _, _, firsts2, s2 = run(no_filter=True)
    print(f"active={sim.ACTIVE}")
    print(" time | filter lv | filter x | all other bonus x | income    | income w/o filter | ratio")
    for (h, fl, fm, om, inc), (_, _, _, _, inc2) in zip(log, log2):
        print(f"{h:5.2f}h | {fl:9d} | {fm:8.1f} | {om:17.1f} | {E.fmt(inc):9s} | {E.fmt(inc2):17s} | {inc / inc2:5.2f}x")
    tot = sum(spend.values())
    print("\nshare of all scales spent:")
    for k, v in sorted(spend.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {k:10s} {100 * v / tot:5.1f}%   ({picks[k]} buys)")
    print("\nspecies unlock times   with filter | without")
    for sp in SPECIES:
        a = E.fmt_time(firsts[sp['id']]) if sp['id'] in firsts else "-"
        b = E.fmt_time(firsts2[sp['id']]) if sp['id'] in firsts2 else "-"
        print(f"  {sp['name']:22s} {a:>10s} | {b:>10s}")


if __name__ == "__main__":
    main()
