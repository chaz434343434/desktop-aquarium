"""Mac smoke test of the BUILT app with a real window (GitHub Mac runner).
Runs the game through its screenshot script and grabs the whole desktop with `screencapture`
a few times, so we can see where the window sits and that panels open.
Usage: python build_assets/mac_smoke.py out/shots"""
import os
import subprocess
import sys
import tempfile
import time

shots = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "out/shots")
os.makedirs(shots, exist_ok=True)
exe = os.path.join("dist", "Desktop Aquarium.app", "Contents", "MacOS", "Desktop Aquarium")
save = os.path.join(tempfile.mkdtemp(), "save.json")
env = dict(os.environ, DA_UPDATE_API="http://127.0.0.1:9/none")     # don't ask the real GitHub
env.pop("SDL_VIDEODRIVER", None)
p = subprocess.Popen([exe, "--fresh", "--demo", "--save", save, "--seconds", "16",
                      "--shots", os.path.join(shots, "game")], env=env)
t0 = time.time()
caps = os.environ.get("DA_CAPS", "3.0,4.7,9.7,13.0")   # tank / shop open / options open / closed again
for at in [float(x) for x in caps.split(",") if x]:
    time.sleep(max(0, at - (time.time() - t0)))
    subprocess.run(["screencapture", "-x", os.path.join(shots, f"desktop_{at:04.1f}s.png")])
code = p.wait(timeout=60)
ok = code == 0 and os.path.exists(save)
got = sorted(os.listdir(os.path.join(shots, "game"))) if os.path.isdir(os.path.join(shots, "game")) else []
print("exit code", code, "| save written", os.path.exists(save), "| game shots", got)
ok &= len(got) >= 8
if not ok:
    # find out why: the same game from source with Python's crash tracer, and macOS's crash report
    print("---- source run with faulthandler")
    r = subprocess.run([sys.executable, "-X", "faulthandler", "-m", "purrfin.main", "--fresh", "--seconds", "5",
                        "--save", save + ".src"], env=env, capture_output=True, text=True, timeout=120)
    print("exit", r.returncode)
    print((r.stdout + r.stderr)[-4000:])
    import glob
    reps = sorted(glob.glob(os.path.expanduser("~/Library/Logs/DiagnosticReports/*.ips")), key=os.path.getmtime)
    for rep in reps[-2:]:
        print("---- crash report", rep)
        txt = open(rep, errors="replace").read()
        try:
            import json
            head, body = txt.split(chr(10), 1)
            d = json.loads(body)
            print("exception:", d.get("exception"), "| termination:", d.get("termination", {}).get("indicator"))
            th = next(t for t in d["threads"] if t.get("triggered"))
            imgs = d.get("usedImages", [])
            for fr in th["frames"][:25]:
                im = imgs[fr["imageIndex"]].get("name", "?") if fr.get("imageIndex") is not None else "?"
                print("  ", im, fr.get("symbol", hex(fr.get("imageOffset", 0))))
        except Exception as e:
            print("(raw)", txt[:3000], e)
print("SMOKE PASS" if ok else "SMOKE FAIL")
sys.exit(0 if ok else 1)
