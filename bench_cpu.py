"""CPU benchmark: runs the real game (python -m purrfin.main) on the top monitor with a busy
late-game save for N seconds and reports its CPU use and frame cost.
Usage: python bench_cpu.py [seconds] [label]
The teacher's laptop (older Ryzen 5 ThinkPad) is roughly 2-3x slower than the dev PC,
so multiply the CPU % here by ~3 to picture it there."""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"          # only for building the save below
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from purrfin import economy as E  # noqa: E402
from purrfin.data import SPECIES, TOYS  # noqa: E402

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 20
label = sys.argv[2] if len(sys.argv) > 2 else ""
s = E.new_state()
E.earn(s, 1e30)
s["upgrades"].update(tank=8, plants=12, conditioner=25, jar=5, hatchery=6, bubbler=15)
for sp in SPECIES[:20]:
    E.add_fish(s, sp["id"])
for t in TOYS[:30]:
    s["toys"][t["id"]] = dict(lv=3)
s["settings"]["monitor"] = 2
if len(sys.argv) > 3:
    s["settings"]["power"] = sys.argv[3]
tmp = tempfile.mkdtemp()
save = os.path.join(tmp, "save.json")
with open(save, "w") as fh:
    json.dump(s, fh)

env = dict(os.environ)
env.pop("SDL_VIDEODRIVER")
env.pop("SDL_AUDIODRIVER")
env["DA_UPDATE_API"] = "http://127.0.0.1:9/none"
p = subprocess.Popen([sys.executable, "-m", "purrfin.main", "--save", save, "--seconds", str(secs + 4)],
                     cwd=ROOT, env=env)


class FT(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]


def cpu_seconds(handle):
    c, e, k, u = FT(), FT(), FT(), FT()
    ctypes.windll.kernel32.GetProcessTimes(int(handle), ctypes.byref(c), ctypes.byref(e), ctypes.byref(k),
                                           ctypes.byref(u))
    return ((k.hi << 32 | k.lo) + (u.hi << 32 | u.lo)) / 1e7


def dwm_handle():
    """Windows' desktop compositor: it re-blends see-through windows over everything else"""
    out = subprocess.run(["tasklist", "/fi", "imagename eq dwm.exe", "/fo", "csv", "/nh"],
                         capture_output=True, text=True).stdout
    try:
        pid = int(out.split('","')[1])
        return ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)     # QUERY_LIMITED_INFORMATION
    except Exception:
        return None


dwm = dwm_handle()
time.sleep(4)                       # skip start-up
c0, d0, t0 = cpu_seconds(p._handle), cpu_seconds(dwm) if dwm else 0, time.time()
time.sleep(secs)
c1, d1, t1 = cpu_seconds(p._handle), cpu_seconds(dwm) if dwm else 0, time.time()
p.wait()
pct = (c1 - c0) / (t1 - t0) * 100
dpct = (d1 - d0) / (t1 - t0) * 100
print(f"{label:12s} game CPU {pct:5.1f}% of one core here  (~{min(100, pct * 3):.0f}% on a ~3x slower laptop)"
      f"  | Windows compositor (dwm) {dpct:4.1f}%")
