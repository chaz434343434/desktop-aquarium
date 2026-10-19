"""Entry point: python -m purrfin.main  (or run DesktopAquarium.pyw)"""
import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SDL_MOUSE_FOCUS_CLICKTHROUGH"] = "1"

import pygame  # noqa: E402

from . import winutil  # noqa: E402
from .game import Game  # noqa: E402

FPS = 30           # while you're using it
IDLE_FPS = 20      # just sitting on the desktop: fish still swim smoothly, less work for the computer
HIDDEN_FPS = 8     # tank hidden with the _ button


def pick_fps(g):
    if g.minimized:
        return HIDDEN_FPS
    busy = g.mouse_low is not None or g.ui.mouse is not None or g.ui.panel or g.now - g.last_input < 3
    return FPS if busy else IDLE_FPS


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
    ap.add_argument("--demo", action="store_true", help="give a pile of scales and fish (testing)")
    args = ap.parse_args(argv)

    prev_fg = winutil.foreground()
    winutil.set_dpi_aware()
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
    clock = pygame.time.Clock()
    t = 0.0
    script = {}
    if args.shots:
        os.makedirs(args.shots, exist_ok=True)
    while g.running:
        dt = min(0.15, clock.tick(pick_fps(g)) / 1000)
        t += dt
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                g.quit()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 2, 3):
                g.ui.set_mouse(e.pos)
                g.mouse_down(e.pos, e.button)
            elif e.type == pygame.MOUSEBUTTONUP:
                g.mouse_up(e.pos, e.button)
            elif e.type == pygame.MOUSEMOTION:
                g.mouse_motion(e.pos, e.rel, e.buttons)
            elif e.type == pygame.MOUSEWHEEL:
                g.ui.wheel(pygame.mouse.get_pos(), e.y)
            elif e.type == pygame.WINDOWLEAVE:
                g.mouse_leave()
            elif e.type == pygame.KEYDOWN:
                g.key_down(e)
            elif e.type == pygame.TEXTINPUT:
                g.text_input(e.text)
        g.update(dt)
        g.draw()
        if args.shots or args.script:
            run_script(g, t, None, args.shots, script)
        pygame.display.flip()
        if args.seconds and t >= args.seconds:
            g.running = False
    try:
        g.save()
    except OSError:
        pass
    pygame.quit()


if __name__ == "__main__":
    main(sys.argv[1:])
