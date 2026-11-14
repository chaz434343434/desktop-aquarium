"""Entry point: python -m purrfin.main  (or run DesktopAquarium.pyw)"""
import argparse
import atexit
import os
import signal
import sys
import time
import traceback
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SDL_MOUSE_FOCUS_CLICKTHROUGH"] = "1"

import pygame  # noqa: E402

from . import winutil  # noqa: E402
from .game import Game  # noqa: E402

# frames per second:      using it, idle on the desktop
FPS = {"normal": (30, 15), "saver": (20, 10)}

HIDDEN_FPS = 6     # tank hidden with the _ button
COVERED_FPS = 4    # another program is full screen in front (video, slides, a game)


class Pacer:
    def __init__(self):
        self.covered = False
        self.check_t = 0.0

    def fps(self, g, dt):
        self.check_t -= dt
        if self.check_t <= 0:                        # asking Windows is cheap, but once a second is plenty
            self.check_t = 1.0
            self.covered = winutil.fullscreen_app_in_front(g.hwnd)
        if g.minimized:
            return HIDDEN_FPS
        if self.covered:
            return COVERED_FPS
        active, idle = FPS.get(g.state["settings"].get("power", "normal"), FPS["normal"])
        if g.tank_move or g.tank_stretch:
            return max(FPS["normal"])                # being carried: keep up with the mouse
        busy = (g.mouse_low is not None or g.ui.mouse is not None or g.ui.panel or g.ui.closing
                or g.now - g.last_input < 3)
        return active if busy else idle


def run_script(g, t, shots, shot_dir, state):
    """automated smoke test: drive the UI and grab screenshots"""
    steps = state.setdefault("steps", [
        (1.5, "shot", "tank"),
        (1.8, "hatch", None),
        (2.0, "petfish", None),
        (2.4, "popbubble", None),
        (2.6, "food", "flakes"),
        (3.5, "shot", "fed"),
        (4.0, "open", ("shop", "fish")), (4.5, "shot", "shop_fish"),
        (5.0, "open", ("shop", "toys")), (5.5, "shot", "shop_toys"),
        (6.0, "open", ("shop", "upgrades")), (6.5, "shot", "shop_upgrades"),
        (7.0, "open", ("shop", "mine")), (7.5, "shot", "shop_mine"),
        (8.0, "open", ("shop", "spawn")), (8.5, "shot", "shop_spawn"),
        (9.0, "open", ("dex", None)), (9.5, "shot", "dex"),
        (10.0, "open", ("settings", None)), (10.5, "shot", "settings"),
        (10.7, "open", ("shop", "hatchery")), (10.9, "shot", "shop_hatchery"),
        (11.0, "close", None), (11.2, "hover", None), (11.6, "shot", "hover"),
    ])
    while steps and steps[0][0] <= t:
        _, kind, arg = steps.pop(0)
        if kind == "shot" and shot_dir:
            ext = os.environ.get("DA_SHOT_EXT", "png")       # tests can pick bmp
            pygame.image.save(g.screen, os.path.join(shot_dir, f"{arg}.{ext}"))
        elif kind == "open":
            g.ui.panel, tab = arg
            if tab:
                g.ui.tab = tab
        elif kind == "close":
            g.ui.panel = None
        elif kind == "hatch":
            g.hatch_ready()
        elif kind == "food":
            g.use_food(arg)
        elif kind in ("petfish", "hover"):
            a = next(iter(g.tank.fish.values()))
            pos = tuple(int(v) for v in g.to_screen(a.x, a.y))
            pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
            if kind == "petfish":
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
                for i in range(6):
                    p2 = (pos[0] + (8 if i % 2 else -8), pos[1])
                    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=p2, rel=(16, 0), buttons=(1, 0, 0)))
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))
        elif kind == "popbubble":
            g.tank.spawn_pop(40, 30)
            p = g.tank.pops[-1]
            pos = tuple(int(v) for v in g.to_screen(p.x, p.y))
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=None, help="monitor index to show on (0 = primary)")
    ap.add_argument("--save", default=None, help="save file path")
    ap.add_argument("--fresh", action="store_true", help="ignore existing save")
    ap.add_argument("--seconds", type=float, default=0, help="auto-quit after N seconds (testing)")
    ap.add_argument("--shots", default=None, help="run UI smoke script and save screenshots here")
    ap.add_argument("--script", action="store_true", help="run the UI smoke script without screenshots")
    ap.add_argument("--stress-resize", action="store_true", help="test: keep resizing the window")
    ap.add_argument("--demo", action="store_true", help="give a pile of scales and fish (testing)")
    args = ap.parse_args(argv)

    # one copy at a time: opening it again (double-clicking the shortcut five times...) just brings
    # the running game back on screen instead of starting another one on the same save
    from .game import default_save_path
    if not winutil.single_instance(args.save or default_save_path()):
        winutil.wake_running_copy()
        return
    prev_fg = winutil.foreground()
    winutil.set_dpi_aware()
    winutil.set_low_priority()
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    g = Game(save_path=args.save, monitor=args.monitor, fresh=args.fresh)
    if args.demo:
        from . import economy as E
        s = g.state
        E.earn(s, 5e7)
        s["upgrades"].update(tank=5, filter=8, hands=4, light=3, feeder=1, jar=3, hatchery=4,
                             conditioner=8, plants=4)
        for sp in ("bronze", "panda", "oto", "pictus", "bristlenose", "upside"):
            E.add_fish(s, sp)
        for t in ("ball", "airstone", "cave", "apple", "lilypad", "waterfall", "volcano", "log", "statue",
                  "geyser", "fountain", "duck", "shells", "bamboo", "bottle", "desk", "snail", "crystal", "lighthouse", "fossil", "conch"):
            s["toys"][t] = dict(lv=2)
        s["jar"] = E.jar_cap(s) * 0.7
        s["eggs"] = [dict(c="class", left=0, total=2000, inc=E.income(s)),
                     dict(c="quick", left=200, total=400, inc=E.income(s))]
        g.tank.build_static()
        s["buffs"]["double"] = 120
        g.tank.sync()
    g.apply_window(first=True)
    if prev_fg:
        winutil.restore_foreground(prev_fg)
    # ---- save however the game ends: the x button, Alt+F4, Task Manager, Windows shutting down,
    # the computer going to sleep, Ctrl+C, a crash... (only a hard kill or power cut can't be caught;
    # the 30-second autosave covers those)
    done = {"saved": False}

    def final_save():
        if not done["saved"]:
            done["saved"] = g.save_now("closing")

    atexit.register(final_save)

    def on_signal(sig, frame):
        g.running = False

    for name in ("SIGTERM", "SIGINT", "SIGBREAK", "SIGHUP"):
        if hasattr(signal, name):
            try:
                signal.signal(getattr(signal, name), on_signal)
            except (ValueError, OSError):
                pass
    crash_after = float(os.environ.get("DA_CRASH_AFTER", "0"))      # tests only
    try:
        run_loop(g, args, crash_after)
    except Exception:
        try:
            with open(os.path.join(os.path.dirname(g.save_path), "crash.log"), "a", encoding="utf-8") as fh:
                fh.write(f"---- {time.ctime()}\n{traceback.format_exc()}\n")
        except OSError:
            pass
        final_save()
        if getattr(sys, "frozen", False):
            sys.exit(1)        # the built game: saved + logged, close quietly instead of an error box
        raise
    finally:
        final_save()
        pygame.quit()


HOLD_SECS = 0.6       # a finger held still this long counts as a right-click


def handle_event(g, e):
    if e.type == pygame.QUIT:
        g.quit()
    elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 2, 3):
        g.ui.set_mouse(e.pos)
        g.mouse_down(e.pos, e.button)
        if g.web and e.button == 1:
            g.hold = [e.pos, g.now, False]
    elif e.type == pygame.MOUSEBUTTONUP:
        g.mouse_up(e.pos, e.button)
        g.hold = None
        if g.web and getattr(e, "touch", False):
            g.mouse_leave()                        # no mouse to hover with: hide the tips again
    elif e.type == pygame.MOUSEMOTION:
        g.mouse_motion(e.pos, e.rel, e.buttons)
        if g.hold and abs(e.pos[0] - g.hold[0][0]) + abs(e.pos[1] - g.hold[0][1]) > 12:
            g.hold = None                          # it's a drag, not a hold
    elif e.type == pygame.MOUSEWHEEL:
        g.ui.wheel(pygame.mouse.get_pos(), e.y)
    elif e.type == pygame.WINDOWLEAVE:
        g.mouse_leave()
    elif e.type == pygame.KEYDOWN:
        g.key_down(e)
    elif e.type == pygame.TEXTINPUT:
        g.text_input(e.text)


async def run_web():
    """the browser version (built with pygbag): same game, but the page needs control back every frame"""
    import asyncio
    pygame.init()
    page = winutil.web_page_size()
    if page:
        winutil.fit_web_size(page)
    g = Game()
    g.apply_window(first=True)
    clock = pygame.time.Clock()
    saved_t = 0.0
    turn_t = 0.0
    try:                                             # add ?debug to the address to log taps to the console
        import platform as _pf
        debug = "debug" in str(_pf.window.location.search)

        def log(msg):
            _pf.window.console.log(msg)
    except Exception:
        debug = False

        def log(msg):
            pass
    while True:
        dt = min(0.3, clock.tick(30) / 1000)
        turn_t += dt
        if turn_t >= 0.5:                            # the phone was turned round: fit the new shape
            turn_t = 0.0
            page = winutil.web_page_size()
            if page and winutil.fit_web_size(page):
                g.relayout()
        for e in pygame.event.get():
            if e.type != pygame.QUIT:                # closing the tab is the only way to quit
                if debug and e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.FINGERDOWN,
                                        pygame.FINGERUP):
                    log(f"{pygame.event.event_name(e.type)} {getattr(e, 'pos', '')} b={getattr(e, 'button', '')} "
                        f"touch={getattr(e, 'touch', '')} press={'yes' if g.ui.press else 'no'} panel={g.ui.panel}")
                handle_event(g, e)
                if debug and e.type == pygame.MOUSEBUTTONDOWN:
                    log(f"  after down: press={g.ui.press and (g.ui.press['rect'], g.ui.press['moved'])}")
        g.update(dt)
        if g.hold and not g.hold[2] and g.now - g.hold[1] >= HOLD_SECS and not g.ui.press:
            g.hold[2] = True                       # held long enough on the tank: same as a right-click there
            g.mouse_down(g.hold[0], 3)
        g.draw()
        g.present()
        saved_t += dt
        if saved_t >= 10:                            # a tab can be closed any moment: save often
            saved_t = 0.0
            g.save()
        await asyncio.sleep(0)


def run_loop(g, args, crash_after=0.0):
    clock = pygame.time.Clock()
    pacer = Pacer()
    stress = [0.0, 0]
    dt = 0.0
    t = 0.0
    script = {}
    if args.shots:
        os.makedirs(args.shots, exist_ok=True)
    while g.running:
        dt = min(0.3, clock.tick(pacer.fps(g, dt)) / 1000)
        t += dt
        if crash_after and t >= crash_after:
            raise RuntimeError("test crash (DA_CRASH_AFTER)")
        for e in pygame.event.get():
            handle_event(g, e)
        g.update(dt)
        g.draw()
        if args.shots or args.script:
            run_script(g, t, None, args.shots, script)
        if args.stress_resize:              # test: change the window size again and again
            stress[0] += dt
            if stress[0] >= 0.25:
                stress[0] = 0.0
                stress[1] += 1
                if stress[1] % 3 == 0:
                    g.ui.open_tab("fish")
                else:
                    g.change_setting("width", 0.30 if stress[1] % 2 else 0.45)
        g.present()
        if args.seconds and t >= args.seconds:
            g.running = False


if __name__ == "__main__":
    main(sys.argv[1:])
