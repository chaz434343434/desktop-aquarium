"""Debug helper (Mac CI): launch the built app with small differences, twice each, and report crashes."""
import os
import subprocess
import tempfile

exe = os.path.join("dist", "Desktop Aquarium.app", "Contents", "MacOS", "Desktop Aquarium")
env = dict(os.environ, DA_UPDATE_API="http://127.0.0.1:9/none")
tmpd = tempfile.mkdtemp()
absout = os.path.abspath("out/m")
cases = {
    "exact smoke":         ["--fresh", "--demo", "--save", f"{tmpd}/a.json", "--seconds", "16", "--shots", f"{absout}/a"],
    "save in /tmp":        ["--fresh", "--demo", "--save", "/tmp/b.json", "--seconds", "16", "--shots", f"{absout}/b"],
    "shots in /tmp":       ["--fresh", "--demo", "--save", f"{tmpd}/c.json", "--seconds", "16", "--shots", "/tmp/c"],
    "6 seconds":           ["--fresh", "--demo", "--save", f"{tmpd}/d.json", "--seconds", "6", "--shots", f"{absout}/d"],
    "no demo":             ["--fresh", "--save", f"{tmpd}/e.json", "--seconds", "16", "--shots", f"{absout}/e"],
    "no shots":            ["--fresh", "--demo", "--save", f"{tmpd}/f.json", "--seconds", "16"],
    "no save arg":         ["--fresh", "--demo", "--seconds", "16", "--shots", f"{absout}/g"],
}
for name, args in cases.items():
    codes = []
    for i in range(2):
        codes.append(subprocess.call([exe] + args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    print(f"{name:20s} exit codes {codes}", flush=True)
