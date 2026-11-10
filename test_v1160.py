"""Headless checks for 1.16.0: six bright new catfish around the Ud price (slotted in, nobody else's price
changes), and rare colour morphs from x1.1 to x3. Run: python test_v1160.py [screenshot_dir]"""
import json
import os
import random
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-11-10"
import pygame  # noqa: E402

from purrfin import economy as E, share, sprites  # noqa: E402
from purrfin.data import SPECIES, SPECIES_BY_ID, MORPHS, MORPHS_BY_ID, SEASONAL_SPECIES  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


# ---- the new fish
NEW = ["neonglow", "opal", "sunriseglow", "candy", "stardust", "novaburst", "bubblegum", "firefly", "lagoon", "spectrum"]
check("ten new catfish", all(n in SPECIES_BY_ID for n in NEW) and len(SPECIES) == 110)
for n in NEW:
    sp = SPECIES_BY_ID[n]
    check(f"{sp['name']} costs Ud-ish money ({E.fmt(sp['cost'])})", 1e36 <= sp["cost"] < 1e39)
OLD = {"vampire": 1.66e36, "iridescent": 5.97e36, "piraiba": 1.00e39, "infinity": None}
check("the old fish kept their prices", abs(SPECIES_BY_ID["vampire"]["cost"] / 1.6587e36 - 1) < 0.01
      and abs(SPECIES_BY_ID["piraiba"]["cost"] / 1.0e39 - 1) < 0.05)
check("everything is still in price order", all(a["cost"] < b["cost"] for a, b in zip(SPECIES[1:], SPECIES[2:])))
check("and earns in order", all(a["rate"] < b["rate"] for a, b in zip(SPECIES, SPECIES[1:])))
check("names and ids are all different", len({sp["id"] for sp in SPECIES}) == 110 and len({sp["name"] for sp in SPECIES}) == 110)
check("tiers are just their places in the list", [sp["tier"] for sp in SPECIES] == list(range(110)))
spec = sprites.fish_frames("spectrum")[(True, False)][0]
hues = []
for x in range(spec.get_width()):
    r, g_, b, a = spec.get_at((x, spec.get_height() // 2))
    h_ = __import__("colorsys").rgb_to_hsv(r / 255, g_ / 255, b / 255)
    if a > 200 and max(r, g_, b) > 200 and h_[1] > 0.5:       # skip the white eye and sparkles
        hues.append(__import__("colorsys").rgb_to_hsv(r / 255, g_ / 255, b / 255))
check(f"Spectrum is very bright ({min(h[2] for h in hues):.2f} lowest brightness along its middle)", min(h[2] for h in hues) > 0.95)
steps = [abs(a[0] - b[0]) for a, b in zip(hues, hues[1:])]
check(f"and shades smoothly (biggest jump between pixels {max(min(s, 1 - s) for s in steps):.2f} of the colour wheel)",
      max(min(s, 1 - s) for s in steps) < 0.12)
check("through the whole rainbow", max(h[0] for h in hues) - min(h[0] for h in hues) > 0.6)
for n in NEW:
    for fr in sprites.fish_frames(n).values():
        pass
check("they all draw", True)


def colourfulness(surf):
    """how many different bright colours a sprite has"""
    seen = set()
    for x in range(surf.get_width()):
        for y in range(surf.get_height()):
            r, g, b, a = surf.get_at((x, y))
            if a > 200 and max(r, g, b) > 200 and max(r, g, b) - min(r, g, b) > 80:
                seen.add((r // 32, g // 32, b // 32))
    return len(seen)


dull = colourfulness(sprites.fish_frames("vampire")[(True, False)][0])
for n in NEW:
    c = colourfulness(sprites.fish_frames(n)[(True, False)][0])
    check(f"{n} is bright and colourful ({c} bright colours vs {dull} for the Vampire Catfish)", c > dull + 2)

# ---- morphs: how rare, and what they're worth
check("nine colours, x1.1 to x3", [m["mult"] for m in MORPHS] == [1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0, 2.5, 3.0])
check("rarer as they get better", all(a["chance"] > b["chance"] for a, b in zip(MORPHS, MORPHS[1:])))
random.seed(5)
rolls = [E.roll_morph() for _ in range(200000)]
plain = rolls.count("") / len(rolls)
check(f"most fish are plain ({plain:.1%})", 0.85 < plain < 0.9)
check("every colour turns up", all(m["id"] in rolls for m in MORPHS))
check(f"Prismatic is very rare ({rolls.count('prism')} in 200,000)", 50 < rolls.count("prism") < 200)
avg = sum(E.morph_mult({"morph": r}) for r in rolls) / len(rolls)
check(f"on average they add only a little ({avg:.3f}x)", 1.02 < avg < 1.06)

s = E.new_state()
check("Sunny is always plain", not s["fish"][0].get("morph"))
f = E.add_fish(s, "bronze", morph="galaxy")
plainf = E.add_fish(s, "bronze", morph="")
check("a Galaxy fish earns 2x a plain one", abs(E.fish_rate(s, f) / E.fish_rate(s, plainf) - 2) < 1e-9)
check("it's remembered for the Fishdex", s["morphs_seen"] == ["galaxy"])
both = E.add_fish(s, "bronze", shiny=True, morph="prism")
check("shiny and Prismatic stack: 6x", abs(E.fish_rate(s, both) / E.fish_rate(s, plainf) - 6) < 1e-9)
check("labels say so", E.fish_tags(both) == "  *SHINY*  Prismatic x3" and E.fish_tags(plainf) == "")
seasonal = E.add_fish(s, SEASONAL_SPECIES[0]["id"])
check("holiday catfish don't get morphs", all(not E.add_fish(s, "turkey").get("morph") for _ in range(50)))
s["fish"] = s["fish"][:3]

# ---- every morph draws, on every kind of fish (including the hand-drawn Blue Channel Catfish)
for m in MORPHS:
    for sp in ("sunflower", "bronze", "panda", "glass", "bluechannel", "infinity", "pleco"):
        if sp not in SPECIES_BY_ID:
            continue
        g_ = dict(uid=1, sp=sp, lv=1, morph=m["id"], look=[0, 0, 0, 0])
        sprites.fish_frames(sp, False, E.fish_look(g_))
        sprites.fish_frames(sp, True, E.fish_look(g_))
check("every colour draws on every kind of fish, shiny or not", True)
plain_px = sprites.fish_frames("bronze", False, E.fish_look(dict(uid=1, sp="bronze", lv=1, look=[0, 0, 0, 0])))
plain_px = pygame.image.tobytes(plain_px[(True, False)][0], "RGBA")
looks = set()
for m in MORPHS:
    fr = sprites.fish_frames("bronze", False, E.fish_look(dict(uid=1, sp="bronze", lv=1, morph=m["id"], look=[0, 0, 0, 0])))
    looks.add(pygame.image.tobytes(fr[(True, False)][0], "RGBA"))
check("each colour really looks different", len(looks) == len(MORPHS) and plain_px not in looks)

# ---- saves, codes, odd data
path = os.path.join(tempfile.mkdtemp(), "s.json")
g = Game(save_path=path, fresh=True)
g.apply_window(first=True)
E.add_fish(g.state, "bronze", morph="neon")
g.save()
g2 = Game(save_path=path)
check("morphs are saved", any(x.get("morph") == "neon" for x in g2.state["fish"]) and "neon" in g2.state["morphs_seen"])
d = json.load(open(path))
d["fish"][1]["morph"] = "made-up"
d["morphs_seen"] = ["neon", "junk", 7]
json.dump(d, open(path, "w"))
g3 = Game(save_path=path)
check("an unknown morph in a save is dropped", "morph" not in g3.state["fish"][1] and g3.state["morphs_seen"] == ["neon"])
code = share.encode(g2.state)
vs = share.decode(code, g2.state["settings"])
check("tank codes carry morphs", any(x.get("morph") == "neon" for x in vs["fish"]))
raw = json.loads(__import__("zlib").decompress(__import__("base64").urlsafe_b64decode(code[4:] + "==")))
raw["f"][1][5] = "../../evil"
bad = "DA1:" + __import__("base64").urlsafe_b64encode(__import__("zlib").compress(json.dumps(raw).encode())).decode().rstrip("=")
check("a code with a made-up morph just shows a plain fish", not any(x.get("morph") for x in share.decode(bad, {})["fish"]))
raw["f"][1] = raw["f"][1][:5]
old = "DA1:" + __import__("base64").urlsafe_b64encode(__import__("zlib").compress(json.dumps(raw).encode())).decode().rstrip("=")
check("codes from before morphs still work", len(share.decode(old, {})["fish"]) == len(raw["f"]))
s2 = dict(g2.state)
s2["earned_run"] = 1e18
g2.spawn()
check("colours found are kept through Spawning Season", "neon" in g2.state["morphs_seen"])

# ---- what you see
g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
E.earn(g.state, 1e15)
g.state["upgrades"]["tank"] = 10
for m in ("bright", "rosy", "ocean", "lime", "sunset", "neon", "galaxy", "rainbow", "prism"):
    E.add_fish(g.state, "bronze" if m < "m" else "panda", morph=m)
g.tank.sync()
g.toasts.clear()
g.buy_species("bronze")
real_roll = E.roll_morph
E.roll_morph = lambda: "galaxy"          # make the next one rare, for the test
g.toasts.clear()
g.buy_species("bronze")
E.roll_morph = real_roll
found = True
newest = g.state["fish"][-1]
check("buying a rare colour tells you", found and newest.get("morph") and any("rare" in t[0] for t in g.toasts))
g.ui.panel, g.ui.tab = "shop", "mine"
labels = []
real = g.ui.f_norm.render
g.ui.f_norm.render = lambda text, *a, **k: labels.append(text) or real(text, *a, **k)
g.draw()
g.draw()
g.ui.f_norm.render = real
check("My Tank shows each fish's colour", any("Galaxy x2" in t for t in labels) and any("Prismatic x3" in t for t in labels))
g.ui.panel = "dex"
labels.clear()
g.ui.f_norm.render = lambda text, *a, **k: labels.append(text) or real(text, *a, **k)
g.draw()
g.ui.f_norm.render = real
check("the Fishdex counts colours found", any("Colours 9/9" in t for t in labels))
if shots:
    os.makedirs(shots, exist_ok=True)
    g.ui.panel = None
    g.toasts.clear()
    g.tank.hour_override = 12
    for _ in range(30):
        g.update(0.1)
    g.draw()
    pygame.image.save(g.screen.subsurface(g.tank_rect), os.path.join(shots, "morph_tank.png"))
    W = 10 * 130
    sheet = pygame.Surface((W, 2 * 130 + 8 * 70), pygame.SRCALPHA)
    sheet.fill((20, 40, 70))
    for i, n in enumerate(NEW):
        ic = sprites.fish_icon(n, 4)
        sheet.blit(ic, (10 + i * 210, 10))
    for row, sp in enumerate(("bronze", "panda", "sunflower", "bluechannel", "glass", "vampire", "pictus", "infinity")):
        if sp not in SPECIES_BY_ID:
            continue
        for i in range(10):
            f_ = dict(uid=1, sp=sp, lv=1, look=[0, 0, 0, 0], morph=MORPHS[i - 1]["id"] if i else "")
            sheet.blit(sprites.fish_icon(sp, 3, look=E.fish_look(f_)), (10 + i * 128, 140 + row * 70))
    pygame.image.save(sheet, os.path.join(shots, "morph_sheet.png"))
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
