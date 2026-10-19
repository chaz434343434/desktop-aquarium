"""Try species-cost curves against the school-day sim.
Run: python tune_school.py
Each species tier i costs SPECIES_COST0 * product of per-tier growth factors."""
import io
import sys
from contextlib import redirect_stdout

from purrfin import data

sys.argv = ["x", "7", "15"]
import sim_school  # noqa: E402

KEY = ["Glass Catfish", "Clown Pleco", "Striped Raphael", "Albino Bristlenose", "Royal Pleco",
       "Redtail Catfish", "Golden Sunflower", "Moonlight Catfish"]


def set_curve(early, mid, late, split1=7, split2=13):
    cost = data.SPECIES_COST0
    for i, sp in enumerate(data.SPECIES):
        if i == 0:
            sp["cost"] = 10
            continue
        if i > 1:
            cost *= early if i <= split1 else mid if i <= split2 else late
        sp["cost"] = cost


def run():
    buf = io.StringIO()
    with redirect_stdout(buf):
        sim_school.main()
    out = {}
    for line in buf.getvalue().splitlines():
        for k in KEY:
            if line.strip().startswith(k):
                out[k] = line.strip()[len(k):].strip()
    return out


if __name__ == "__main__":
    curves = [(float(a), float(b), float(c)) for a, b, c in (x.split(",") for x in sys.argv_curves)] \
        if hasattr(sys, "argv_curves") else [(9, 9, 9), (8, 11, 8), (8, 12, 7), (9, 12, 6)]
    for e, m, l in curves:
        set_curve(e, m, l)
        r = run()
        print(f"{e:g}/{m:g}/{l:g}: " + " | ".join(f"{k.split()[0]} {r.get(k)}" for k in KEY), flush=True)
