"""Headless checks for 1.7.0: fish that want pets, sleepy fish at night, surprise events, dragging food,
tank lights, tank name plaque, photos, tank codes + visiting, calm sounds.
Run: python test_v170.py [screenshot_dir]"""
import os
import sys
import tempfile
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E, share  # noqa: E402
from purrfin.data import CURIOUS_BONUS  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def shot(name, rect=None, surf=None):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.draw()
        g.draw()
        pygame.image.save((surf or g.screen).subsurface(rect) if rect else (surf or g.screen), os.path.join(shots, name + ".png"))


g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
s = g.state
E.earn(s, 1e9)
s["upgrades"].update(tank=4)
for sp in ("bronze", "panda", "pictus"):
    E.add_fish(s, sp)
g.tank.sync()
g.toasts.clear()
g.tank.hour_override = 12
t = g.tank

# ---- fish that want pets
mouse = (60, 30)
g.mouse_low = mouse
t.beg_timer = 0.0
for _ in range(120):
    g.update(1 / 30)
beggar = next((a for a in t.fish.values() if a.beg > 0), None)
check("with the mouse in the tank, a fish comes over wanting pets", beggar is not None)
closest = 999
for _ in range(240):                      # it has up to 9 seconds to get there
    g.update(1 / 30)
    closest = min(closest, abs(beggar.x - mouse[0]))
    if closest < 10:
        break
check(f"it swims right up to the cursor ({closest:.0f} px away)", closest < 10)
beggar.beg = max(beggar.beg, 1.0)
base = E.pet_reward(s, beggar.f)
before = s["bubbles"]
g.last_any_pet = -9
g.pet(beggar)
check(f"petting it then pays {CURIOUS_BONUS}x", abs((s["bubbles"] - before) - base * CURIOUS_BONUS) < 1e-6 * base * 5)
check("and it says 'Loved it!'", any(tx[2] == "Loved it!" for tx in t.texts))
check("it's happy now and stops asking", beggar.beg == 0)
g.mouse_low = None

# ---- sleepy at night
t.hour_override = 23.5
t.night_check = 0
g.update(0.05)
check("at night the tank knows it's night", t.night)
for _ in range(300):
    g.update(0.1)
check("fish snooze (Zzz) at night", any(p.kind == "z" for p in t.parts) or any(a.state == "rest" for a in t.fish.values()))
g.change_setting("light", "day")
t.night_check = 0
g.update(0.05)
check("with Daylight lights on, no sleepy night", not t.night)
g.change_setting("light", "auto")
t.hour_override = 12
t.night_check = 0
g.update(0.05)

# ---- surprise events
iv = E.pop_interval(s)
g.start_event("storm")
check("bubble storm: bubbles come 5x as fast", abs(E.pop_interval(s) - iv / 5) < 1e-9)
check("and shows a timer", "storm" in s["buffs"])
g.start_event("golden")
t.pops.clear()
t.spawn_pop()
check("golden moment: every bubble is golden", t.pops and t.pops[-1].golden)
t.visitor = None
g.start_event("diver")
check("a treasure diver swims in", t.visitor and t.visitor["v"]["id"] == "diver")
s["buffs"].clear()
shot_diver = t.visitor
t.visitor["x"] = t.w / 2
t.visitor["pause"] = 99
inc = E.income(s)
before = s["bubbles"]
g.catch_visitor()
check("catching the diver gives a big gift (15 minutes of income)", s["bubbles"] - before >= inc * 900 * 0.99)
g.event_t = 0
s["chill"] = True
g.tick_events(0.1)
check("no surprises in Chill mode", "storm" not in s["buffs"] and "golden" not in s["buffs"])
s["chill"] = False

# ---- dragging food
g.ui.panel = None
g.draw()
fb = next(r for r, cb in g.ui.hits if "food_press" in str(cb.__code__.co_names) or "food_press" in repr(cb))
press = (int(fb.centerx * g.ui.k), int(fb.centery * g.ui.k))
t.foods.clear()
g.food_cd.clear()
g.mouse_down(press, 1)
target = tuple(int(v) for v in g.to_screen(150, 20))
g.mouse_motion(target, (10, 10), (1, 0, 0))
g.mouse_up(target, 1)
check("dragging food into the tank drops it where you let go",
      t.foods and all(abs(fd.x - 150) <= 7 for fd in t.foods))
t.foods.clear()
g.food_cd.clear()
g.mouse_down(press, 1)
g.mouse_up(press, 1)
check("a normal click still feeds like before", bool(t.foods))

# ---- lights
g.change_setting("light", "moon")
tint = t.tint_surface()
check("Moonlight lights tint the water blue", tint is not None and tint.get_at((5, 5))[2] > tint.get_at((5, 5))[0])
g.change_setting("light", "day")
check("Daylight: no tint", t.tint_surface() is None)
g.change_setting("light", "auto")

# ---- tank name
g.start_tank_name()
g.rename_text = ""
g.text_input("Mr. Fin's Reef")
g.key_down(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
check("naming the tank", s["tank_name"] == "Mr. Fin's Reef" and g.renaming is None)
check("the name survives Spawning Season", E.new_state(keep=s)["tank_name"] == "Mr. Fin's Reef")
g.ui.panel, g.ui.tab = "shop", "mine"
shot("my_tank_tools", g.ui.panel_rect)
g.ui.panel = None
g.draw()
r = g.tank_rect
shot("plaque", pygame.Rect(r.x, max(0, r.y - 70), r.w, r.bottom - max(0, r.y - 70)))

# ---- photo
g.change_setting("light", "sunset")
import purrfin.winutil as W  # noqa: E402
pics = tempfile.mkdtemp()
W.pictures_dir = lambda: pics
path = g.take_photo()
check("Take photo saves a picture in Pictures > Desktop Aquarium", path and os.path.exists(path)
      and os.path.dirname(path).endswith("Desktop Aquarium"))
img = pygame.image.load(path)
check(f"it's a proper picture ({img.get_width()}x{img.get_height()})", img.get_width() == t.w * 4)
if shots:
    pygame.image.save(img, os.path.join(shots, "photo.png"))
g.change_setting("light", "auto")

# ---- tank codes + visiting
code = share.encode(s)
check(f"a tank code is short enough to send ({len(code)} characters)", code.startswith("DA1:") and len(code) < 2000)
vs = share.decode("hey look at my tank!! " + code + " cool right", s["settings"])
check("a code pasted with other text around it still works", len(vs["fish"]) == len(s["fish"]))
check("the name comes along", vs["tank_name"] == "Mr. Fin's Reef")
for bad in ("", "DA1:", "DA1:@@@@", "DA1:" + "A" * 50, "hello"):
    try:
        share.decode(bad, s["settings"])
        check(f"junk is refused: {bad[:12]!r}", False)
    except ValueError:
        pass
check("junk codes are refused", True)
mine_fish = len(s["fish"])
before = s["bubbles"]
g.visit(code)
check("visiting shows the friend's tank", g.visiting and len(g.tank.fish) == len(vs["fish"]))
a = next(iter(g.tank.fish.values()))
g.mouse_down(tuple(int(v) for v in g.to_screen(a.x, a.y)), 1)
check("you can't pet or change anything there", s["stats"]["pets"] == 1)
for _ in range(60):
    g.update(0.05)
check("your own game keeps going in the meantime", s["bubbles"] > before and len(s["fish"]) == mine_fish)
g.draw()
r = g.tank_rect
shot("visiting", pygame.Rect(r.x, max(0, r.y - 50), r.w, r.bottom - max(0, r.y - 50)))
g.leave_visit()
check("Back to my tank", not g.visiting and len(g.tank.fish) == mine_fish)
g.visit(code)
n = len(s["fish"])
g.buy_species("bronze")
check("buying something while visiting takes you home first (no crash)",
      not g.visiting and len(s["fish"]) == n + 1 and len(g.tank.fish) == n + 1)

# ---- calm sounds
g.change_setting("ambience", "music")
t0 = time.time()
while time.time() - t0 < 30 and not (g.ambience.snd.get("water") and g.ambience.snd.get("music")):
    g.update(0.05)
    time.sleep(0.05)
check(f"calm sounds are made and start playing ({time.time() - t0:.1f}s to make)",
      g.ambience.snd.get("water") and g.ambience.snd.get("music"))
g.change_setting("ambience", "off")
g.update(0.05)
check("and switch off again", not any(ch and ch.get_busy() for ch in g.ambience.ch.values()))
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
