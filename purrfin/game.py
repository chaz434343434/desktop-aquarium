"""Game controller: state, economy ticking, input, window layout, saving."""
import json
import os
import random
import sys
import time

import pygame

from . import economy as E
from . import winutil
from .data import (SPECIES, SPECIES_BY_ID, FOODS, FOODS_BY_ID, TOYS_BY_ID, UPGRADES_BY_ID, CLUTCHES_BY_ID,
                   MYSTERY_FROM_GOLDEN, MYSTERY_FROM_VISITOR,
                   THEMES_BY_ID, SEASONAL_BY_ID, SEASONS, SKULL_POP_MULT, HAUNTED_POP_MULT,
                   RUB_COOLDOWN, RUB_EVERY,
                   TOY_MAX_LEVEL, TANK_NAMES, FISH_NAMES)
from .sound import Sounds
from .updater import Updater
from .version import VERSION
from .tank import Tank, TANK_H
from .ui import UI

KEY = (255, 0, 255)          # transparent colour key - never used in art
WIN_H = 660
STRIP_H = 30


def default_save_path():
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "DesktopAquarium", "save.json")
    old = os.path.join(base, "DesktopPurrfin", "save.json")     # the game's old name
    if not os.path.exists(path) and os.path.exists(old):
        import shutil
        os.makedirs(os.path.dirname(path), exist_ok=True)
        shutil.copy2(old, path)                                 # old save stays put as a backup
    return path


class Game:
    def __init__(self, save_path=None, monitor=None, fresh=False):
        self.save_path = save_path or default_save_path()
        self.state = None
        if not fresh:
            self.state = self.load()
        self.toasts = []
        self.now = 0.0
        self.welcome = None
        if self.state is None:
            self.state = E.new_state()
            self.toast("Welcome! Pet Sunny and pop bubbles to collect scales. Feed with the flakes button.", (255, 220, 120), 9)
        else:
            away, amt = E.apply_offline(self.state)
            if amt > 0:
                self.welcome = (away, amt)
        self.monitor_override = monitor
        self.sounds = Sounds(self.state["settings"])
        self.food_cd = {}
        self.last_pet = {}
        self.last_any_pet = -9.0
        self.rub = "ready"            # Fin Scratches ability: ready | armed | active | cooldown
        self.rub_t = 0.0              # seconds left of rubbing / of cooldown
        self.renaming = None      # fish dict being renamed
        self.rename_text = ""
        self.prev_fg = None
        self.last_input = 0.0
        self.input_earned = 0.0
        self.drag_toy = None
        self.drag_spot = None         # [key, start_x, moved] while holding the jar / nest
        self.mouse_low = None
        self.save_timer = 30.0
        self.rate_hist = []
        self.updater = Updater()
        self.update_told = False
        self.manual_check = False     # the player pressed "Check for updates" and wants an answer
        self.feeder_timer = 10.0
        self.hwnd = None
        self.screen = None
        self.running = True
        self.minimized = False
        # Mac (no see-through windows): the window hugs the tank, and grows taller while a panel is open
        self.compact = winutil.COMPACT or bool(os.environ.get("DA_COMPACT"))
        # every platform: the window only covers the tank + buttons until a panel opens. A smaller window
        # is much cheaper for Windows to draw over other programs (a full-width one made Chrome lag).
        self.compact_tall = False
        self.layout()
        self.tank = Tank(self, self.tank_rect.w // self.S)
        self.ui = UI(self)

    # ------------------------------------------------------------ persistence
    def load(self):
        try:
            with open(self.save_path, "r", encoding="utf-8") as fh:
                s = json.load(fh)
        except (OSError, ValueError):
            return None
        base = E.new_state()
        for k, v in base.items():
            s.setdefault(k, v)
        for k, v in E.default_settings().items():
            s["settings"].setdefault(k, v)
        if s.get("version", 1) < 2:          # v2: smaller default tank, currency is scales
            s["settings"]["width"] = 0.30
            s["version"] = 2
        s["fish"] = [f for f in s["fish"] if f.get("sp") in SPECIES_BY_ID]
        for f in s["fish"]:
            # fish renamed before name tags existed: any name that isn't a built-in default counts as named
            if "named" not in f and f.get("name") not in FISH_NAMES:
                f["named"] = True
        if not s["fish"]:
            E.add_fish(s, "sunflower", "Sunny")
        return s

    def save(self):
        self.state["last_time"] = time.time()
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        tmp = self.save_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh)
        os.replace(tmp, self.save_path)

    # ------------------------------------------------------------ window
    def layout(self):
        st = self.state["settings"]
        mons = winutil.monitors()
        idx = self.monitor_override if self.monitor_override is not None else st.get("monitor", -1)
        if idx is None or idx < 0 or idx >= len(mons):
            idx = 0
        m = mons[idx]
        self.mon = m
        self.S = int(st["scale"])
        self.win_w = m["w"]
        ui_k = float(st.get("uiscale", 1.0))
        self.win_h = min(int(WIN_H * max(1.0, ui_k)), m["h"])     # bigger UI needs a taller window
        self.win_x = m["x"]
        self.win_y = m["y"] + m["h"] - self.win_h
        tw = max(480, int(m["w"] * st["width"]))
        if self.compact:
            # Mac: the window can't be see-through, so the tank fills it edge to edge (no empty box
            # beside it). That means it's at least as wide as the row of buttons above it.
            tw = max(tw, int(800 * max(1.0, ui_k)))
        tw = min(tw, m["w"]) // self.S * self.S
        th = TANK_H * self.S
        if st["align"] == "left":
            tx = 0
        elif st["align"] == "center":
            tx = (m["w"] - tw) // 2
        else:
            tx = m["w"] - tw
        if self.compact or self.minimized or not self.compact_tall:
            k = max(1.0, ui_k)
            if self.minimized:
                self.win_h = min(self.win_h, int(50 * k))
            elif not self.compact_tall and self.compact:   # Mac: just the tank and its two rows of buttons
                self.win_h = min(self.win_h, th + int((2 * STRIP_H + 10) * k))
            elif not self.compact_tall:            # tank + buttons + room for a few messages
                self.win_h = min(self.win_h, th + int((2 * STRIP_H + 16 + 124) * k))
            if self.compact:                       # exactly the tank's width, even with the shop open
                self.win_w = min(m["w"], tw)
            else:                                  # see-through anyway: just room for the HUD row
                self.win_w = min(m["w"], max(tw, int(1000 * k)))
            if st["align"] == "left":
                wx = 0
            elif st["align"] == "center":
                wx = (m["w"] - self.win_w) // 2
            else:
                wx = m["w"] - self.win_w
            tx -= wx
            self.win_x = m["x"] + wx
            self.win_y = m["y"] + m["h"] - self.win_h
        self.tank_rect = pygame.Rect(tx, self.win_h - th, tw, th)

    def apply_window(self, first=False):
        st = self.state["settings"]
        if first:
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{self.win_x},{self.win_y}"
        size = (self.win_w, self.win_h)
        if self.screen is None or self.screen.get_size() != size:
            if self.screen is None:
                from . import sprites
                pygame.display.set_icon(pygame.transform.scale(sprites.fish_icon("sunflower", 1), (32, 18)))
            self.screen = pygame.display.set_mode(size, pygame.NOFRAME)
            pygame.display.set_caption("Desktop Aquarium")
            self.hwnd = pygame.display.get_wm_info().get("window")
            winutil.style_overlay(self.hwnd, KEY, st["opacity"], st["topmost"])
        winutil.move(self.hwnd, self.win_x, self.win_y, self.win_w, self.win_h, st["topmost"])
        winutil.set_alpha(self.hwnd, KEY, st["opacity"])

    def relayout(self):
        self.layout()
        self.apply_window()
        if self.tank.w != self.tank_rect.w // self.S:
            self.tank.resize(self.tank_rect.w // self.S)

    def fit_compact(self):
        """the window is tall while a panel or popup is open, short (just the tank + buttons) otherwise"""
        if self.screen is None:
            return
        ui = self.ui
        tall = bool(ui.panel or self.renaming or ui.update_prompt or self.welcome or self.state.get("pending"))
        if tall != self.compact_tall or self.minimized != getattr(self, "_was_min", False):
            self.compact_tall = tall
            self._was_min = self.minimized
            self.relayout()

    def to_low(self, pos):
        r = self.tank_rect
        if not r.collidepoint(pos):
            return None
        return ((pos[0] - r.x) / self.S, (pos[1] - r.y) / self.S)

    def to_screen(self, x, y):
        return self.tank_rect.x + x * self.S, self.tank_rect.y + y * self.S

    # ------------------------------------------------------------ messages
    def toast(self, text, col=(240, 240, 250), dur=4.0):
        self.toasts.append([text, col, dur])
        self.toasts = self.toasts[-4:]

    # ------------------------------------------------------------ tick
    def update(self, dt):
        self.now += dt
        s = self.state
        s["stats"]["playtime"] += dt
        E.earn(s, E.income(s) * dt)
        self.show_shedding(dt)
        if s.get("pending") and len(s["fish"]) < E.capacity(s):
            self.place_pending()
        E.tick_jar(s, dt)
        E.tick_eggs(s, dt)
        for e in s["eggs"]:
            if e["left"] <= 0 and not e.get("told"):
                e["told"] = True
                self.toast(f"{CLUTCHES_BY_ID[e['c']]['name']} is ready to hatch! Click the nest.", (255, 230, 150), 6)
        self.rate_hist.append((self.now, s["earned_total"]))
        while len(self.rate_hist) > 2 and self.now - self.rate_hist[0][0] > 10:
            self.rate_hist.pop(0)
        for f, n in E.tick_needs(s, dt):
            self.level_up(f, n)
        for f in E.tick_growth(s, dt):
            self.grew_up(f)
        self.auto_feed(dt)
        self.tick_rub(dt)
        self.tick_updater()
        self.tank.mouse = self.mouse_low
        self.tank.update(dt)
        for t in self.toasts:
            t[2] -= dt
        self.toasts = [t for t in self.toasts if t[2] > 0]
        self.save_timer -= dt
        if self.save_timer <= 0:
            self.save_timer = 30.0
            try:
                self.save()
            except OSError:
                pass

    def real_rate(self):
        """everything earned per second over the last ~10s (toys, bubbles, petting included)"""
        h = self.rate_hist
        if len(h) < 2 or h[-1][0] - h[0][0] < 1:
            return E.income(self.state)
        return max(E.income(self.state), (h[-1][1] - h[0][1]) / (h[-1][0] - h[0][0]))

    def show_shedding(self, dt):
        """income is credited every frame; every few seconds each fish shows what it made"""
        g = E.global_mult(self.state)
        for a in self.tank.fish.values():
            a.shed += E.fish_rate(self.state, a.f) * g * dt
            a.shed_t -= dt
            if a.shed_t <= 0:
                a.shed_t = random.uniform(5, 8)
                if a.shed >= 1:
                    self.tank.float_text(a.x, a.y - 5, "+" + E.fmt(a.shed), (255, 214, 90))
                    self.tank.burst(a.x, a.y, (255, 214, 90), 2)
                a.shed = 0.0

    def auto_pop(self, p):
        """bubbles left at the surface collect themselves at 30% value"""
        val = E.pop_value(self.state) * (10 if p.golden else 1) * self.pop_mult(p) * 0.3
        E.earn(self.state, val)
        self.tank.float_text(p.x, p.y + 2, "+" + E.fmt(val), (190, 225, 250))

    def report(self, kind):
        """Options > Bugs & Support: opens a pre-filled GitHub issue in the web browser"""
        import platform
        import urllib.parse
        import webbrowser
        from .version import UPDATE_REPO
        s = self.state
        info = (f"Version {VERSION} on {platform.system()} {platform.release()} ({platform.machine()})\n"
                f"Fish: {len(s['fish'])}, scales: {E.fmt(s['bubbles'])}, playtime: {E.fmt_time(s['stats']['playtime'])}")
        if kind == "bug":
            title = "Bug: "
            body = ("**What happened?**\n\n\n**What did you do just before?**\n\n\n"
                    "(A screenshot helps a lot - you can paste one right here.)\n\n---\n" + info)
        else:
            title = "Help: "
            body = "**What do you need help with?**\n\n\n---\n" + info
        url = (f"https://github.com/{UPDATE_REPO}/issues/new?"
               + urllib.parse.urlencode({"title": title, "body": body}))
        try:
            webbrowser.open(url)
            self.toast("Opened GitHub in your browser. Write what happened and press Create!", (200, 220, 255), 6)
        except Exception:
            self.toast(f"Couldn't open the browser. Go to github.com/{UPDATE_REPO}/issues", (255, 170, 150), 8)

    def check_updates(self):
        """the Options button"""
        if not self.updater.enabled:
            return self.toast("Update checking isn't set up in this copy.", (255, 200, 150), 4)
        self.updater.check(force=True)
        self.manual_check = True
        self.toast("Checking for updates...", (200, 220, 255), 2)

    def tick_updater(self):
        u = self.updater
        if self.manual_check and u.state != "checking":
            self.manual_check = False
            if u.state == "none":
                self.toast(f"You're up to date! (v{VERSION})", (150, 230, 160), 4)
            elif u.state == "offline":
                self.toast("Couldn't reach GitHub. Check the internet and try again.", (255, 170, 150), 5)
            elif u.state == "available":
                self.update_told = True
                self.ui.update_prompt = True
        if self.now > 5 and self.state["settings"].get("autoupdate", True):
            u.check()
        if u.state == "available" and os.environ.get("DA_AUTO_INSTALL"):     # end-to-end update test
            self.start_update()
        if u.state == "available" and not self.update_told:
            self.update_told = True
            self.toast(f"A new version ({u.latest['tag']}) is out! Click Update! to get it.", (255, 220, 120), 8)
        elif u.state == "ready":
            self.toast("Update downloaded - restarting...", (255, 220, 120), 3)
            try:
                self.save()
            except OSError:
                pass
            if u.finish():
                self.running = False
        elif u.state == "error":
            u.state = "available"
            self.ui.update_prompt = False
            self.toast("The update didn't download. Try again later.", (255, 150, 150), 5)

    def start_update(self):
        if not self.updater.install():
            msg = self.updater.error or "Updates install from the downloaded app. Get the new version from GitHub."
            self.toast(msg, (255, 200, 150), 6)

    def auto_feed(self, dt):
        lv = E.ulv(self.state, "feeder")
        if not lv:
            return
        self.feeder_timer -= dt
        if self.feeder_timer > 0:
            return
        self.feeder_timer = max(8, 40 - 7 * lv)
        hungry = [a for a in self.tank.fish.values() if a.f["full"] < 25 + 6 * lv]
        if hungry and len(self.tank.foods) < 10:
            a = min(hungry, key=lambda a: a.f["full"])
            self.tank.drop_food(FOODS_BY_ID["flakes"], a.x)

    def level_up(self, f, n):
        a = self.tank.fish.get(f["uid"])
        if a:
            a.levelfx = 2.0
            self.tank.float_text(a.x, a.y - 8, f"Lv {f['lv']}!", (255, 230, 110))
        self.toast(f"{f['name']} reached Lv {f['lv']}!", (255, 230, 110))
        self.sounds.play("level", 0.3, self.now)

    # ------------------------------------------------------------ fish events
    def fish_ate(self, actor, kind):
        f = actor.f
        mult = 1
        if kind.get("pleco_bonus") and actor.sp["shape"] == "pleco":
            mult = kind["pleco_bonus"]
        f["full"] = min(100.0, f["full"] + kind["full"] * mult)
        f["happy"] = min(100.0, f["happy"] + kind["happy"] * mult)
        n = E.gain_xp(self.state, f, kind["xp"] * mult)
        if kind.get("levelup"):
            f["xp"] = 0
            f["lv"] += kind["levelup"]
            n += kind["levelup"]
        if n:
            self.level_up(f, n)
        self.state["stats"]["fed"] += 1
        if kind["id"] != "flakes":
            self.tank.heart(actor.x, actor.y)
        self.sounds.play("plop", 0.15, self.now)

    def fish_played(self, actor, dt):
        f = actor.f
        f["happy"] = min(100.0, f["happy"] + 1.5 * dt)
        n = E.gain_xp(self.state, f, 0.08 * dt * (1 + f["lv"] * 0.05))
        if n:
            self.level_up(f, n)
        actor.play_acc += dt
        toy = actor.toy
        if toy and actor.play_acc >= E.PLAY_PULSE:
            actor.play_acc = 0.0
            val = E.toy_play_value(self.state, f, toy.tid)
            E.earn(self.state, val)
            ty = toy.y - (4 if toy.tid == "ball" else 10)
            self.tank.float_text(toy.x, ty, "+" + E.fmt(val), (255, 214, 90))
            self.tank.burst(toy.x, ty, (255, 214, 90), 4)
            self.sounds.play("pet", 0.25, self.now)

    PET_COOLDOWN = 0.2          # max 5 pet payouts per second, however fast you click

    # ---- Fin Scratches (id 'rub'): press the button, then the first scratch on a fish starts the timer
    def rub_button(self):
        if self.rub == "ready":
            self.rub = "armed"
            self.toast(f"Hold the mouse on a fish and wiggle to scratch! You get {E.rub_secs(self.state)} seconds.",
                       (255, 190, 220), 4)
        elif self.rub == "armed":
            self.rub = "ready"
        elif self.rub == "cooldown":
            self.deny(f"Scratches are recharging. Ready in {int(self.rub_t) + 1}s.")

    def tick_rub(self, dt):
        if self.rub in ("active", "cooldown"):
            self.rub_t -= dt
            if self.rub_t <= 0:
                if self.rub == "active":
                    self.rub, self.rub_t = "cooldown", float(RUB_COOLDOWN)
                    self.toast("Your fish are happy and relaxed. Scratches recharge in a minute.", (255, 190, 220), 3)
                else:
                    self.rub, self.rub_t = "ready", 0.0
        if self.rub != "ready" and not E.ulv(self.state, "rub"):      # spawned: the upgrade is gone
            self.rub, self.rub_t = "ready", 0.0

    def rubbing(self, actor):
        """mouse held and moving over a fish"""
        if self.rub == "armed":
            self.rub, self.rub_t = "active", float(E.rub_secs(self.state))
        if self.rub == "active" and self.now - self.last_any_pet >= RUB_EVERY:
            self.pet(actor, rub=True)

    def pet(self, actor, rub=False):
        if not rub and self.now - self.last_any_pet < self.PET_COOLDOWN:
            return
        self.last_any_pet = self.now
        s = self.state
        f = actor.f
        hm = E.hands_mult(s)
        reward = E.pet_reward(s, f)
        E.earn(s, reward)
        f["happy"] = min(100.0, f["happy"] + 6 * (1 + 0.1 * E.ulv(s, "hands")))
        n = E.gain_xp(s, f, 1.5 * hm)
        actor.pet_t = 0.6
        s["stats"]["pets"] += 1
        self.tank.heart(actor.x, actor.y - 2)
        self.tank.float_text(actor.x, actor.y - 6, "+" + E.fmt(reward), (255, 190, 220))
        if actor.sp.get("purrs") or actor.sp["id"] == "sunflower":
            self.sounds.play("purr", 0.55, self.now)
        else:
            self.sounds.play("pet", 0.12, self.now)
        if n:
            self.level_up(f, n)

    def pop(self, p):
        s = self.state
        val = E.pop_value(s) * (10 if p.golden else 1) * self.pop_mult(p)
        E.earn(s, val)
        s["stats"]["pops"] += 1
        self.tank.pops.remove(p)
        self.tank.burst(p.x, p.y, (255, 230, 120) if p.golden else (210, 240, 255), 10 if p.golden else 6)
        self.tank.float_text(p.x, p.y - 4, "+" + E.fmt(val), (255, 230, 120) if p.golden else (210, 240, 255))
        self.sounds.play("golden" if p.golden else "pop", 0, self.now)
        if p.golden and random.random() < MYSTERY_FROM_GOLDEN:
            self.found_mystery(p.x, p.y)

    def pop_mult(self, p):
        if p.skull:
            return SKULL_POP_MULT
        return HAUNTED_POP_MULT if self.state.get("theme") == "haunted" else 1

    def found_mystery(self, x, y):
        s = self.state
        s["mystery"] = s.get("mystery", 0) + 1
        self.tank.float_text(x, y - 10, "Mystery Egg!", (200, 160, 255))
        self.tank.burst(x, y, (200, 160, 255), 12)
        hint = "Lay it in Shop > Hatchery." if E.ulv(s, "hatchery") else "Build the Hatchery to hatch it!"
        self.toast(f"You found a Mystery Egg! {hint}", (210, 180, 255), 6)

    # ------------------------------------------------------------ input
    def note_input(self):
        """if the player was gone 5+ minutes, greet them with what the tank made"""
        s = self.state
        if self.now - self.last_input > 300 and not self.welcome:
            self.welcome = (self.now - self.last_input, s["earned_total"] - self.input_earned)
        self.last_input = self.now
        self.input_earned = s["earned_total"]

    def mouse_down(self, pos, button):
        self.note_input()
        if self.ui.click(pos, button):
            return
        low = self.to_low(pos)
        if low is None or self.minimized:
            return
        if button == 3:
            a = self.tank.fish_at(*low)
            if a:
                self.start_rename(a.f)
            return
        if button != 1:
            return
        p = self.tank.pop_at(*low)
        if p:
            self.pop(p)
            return
        if self.tank.visitor_at(*low):
            self.catch_visitor()
            return
        if self.tank.jar_at(*low):
            self.drag_spot = ["jar", low[0], False]
            return
        if self.tank.nest_at(*low):
            self.drag_spot = ["nest", low[0], False]
            return
        a = self.tank.fish_at(*low)
        if a and self.rub in ("armed", "active"):
            self.rubbing(a)
            return
        if a:                       # petting is click-only: one click = one pet (wiggling needs Fin Scratches)
            if self.now - self.last_pet.get(a.f["uid"], -9) > 0.25:
                self.last_pet[a.f["uid"]] = self.now
                self.pet(a)
            return
        t = self.tank.toy_at(*low)
        if t:
            self.drag_toy = t
            return

    def mouse_up(self, pos, button):
        self.ui.drag = None
        if self.drag_spot:
            key, _, moved = self.drag_spot
            self.drag_spot = None
            if moved:
                self.sounds.play("plop", 0, self.now)
            elif key == "jar":
                self.collect_jar()
            elif any(e["left"] <= 0 for e in self.state["eggs"]):
                self.hatch_ready()
            else:
                self.ui.panel, self.ui.tab = "shop", "hatchery"
        if self.drag_toy:
            self.drag_toy = None
            self.sounds.play("plop", 0, self.now)

    def mouse_motion(self, pos, rel, buttons):
        if self.ui.over_panel(pos) or self.to_low(pos):
            self.note_input()
        self.ui.set_mouse(pos)
        if self.ui.drag:
            if buttons[0]:
                self.ui.drag_to(pos)
                return
            self.ui.drag = None
        low = self.to_low(pos)
        self.mouse_low = low if not self.minimized else None
        if low is None:
            return
        if buttons[0]:
            if self.rub in ("armed", "active") and not (self.drag_spot or self.drag_toy):
                a = self.tank.fish_at(*low)
                if a:
                    self.rubbing(a)
        if self.drag_spot and buttons[0]:
            if self.drag_spot[2] or abs(low[0] - self.drag_spot[1]) > 2:
                self.drag_spot[2] = True
                self.tank.move_spot(self.drag_spot[0], low[0])
        if self.drag_toy and buttons[0]:
            t = self.drag_toy
            t.x = min(self.tank.w - 8, max(8, low[0]))
            t.st["x"] = t.x / self.tank.w

    def mouse_leave(self):
        self.mouse_low = None
        self.ui.mouse = None

    # ------------------------------------------------------------ actions
    def can_afford(self, c):
        return self.state["bubbles"] + 1e-9 >= c

    def deny(self, msg):
        self.toast(msg, (255, 150, 150), 2.5)
        self.sounds.play("nope", 0.2, self.now)

    def buy_species(self, sp_id):
        s = self.state
        if sp_id in SEASONAL_BY_ID:
            why = E.seasonal_fish_buyable(s, sp_id)
            if why == "owned":
                return self.deny("You already have one! Only one per tank.")
            if why == "season":
                return self.deny(f"Only for sale at {SEASONS[SEASONAL_BY_ID[sp_id]['season']]['name']}.")
        if len(s["fish"]) >= E.capacity(s):
            return self.deny("Tank is full! Upgrade the tank or rehome a fish.")
        c = E.species_cost(s, sp_id)
        if not E.spend(s, c):
            return self.deny("Not enough scales.")
        new = s["dex"] and sp_id not in s["dex"] and sp_id not in SEASONAL_BY_ID
        f = E.add_fish(s, sp_id)
        self.tank.sync()
        a = self.tank.fish[f["uid"]]
        a.y = 6
        a.levelfx = 2.0
        name = SPECIES_BY_ID[sp_id]["name"]
        self.toast(f"{f['name']} the {name} joined the tank!" + ("  New species! +3%" if new else ""),
                   (150, 230, 160), 5)
        if f.get("shiny"):
            self.toast(f"*** WOW, a SHINY {name}! It earns 2x scales! ***", (255, 150, 230), 8)
            self.tank.burst(a.x, a.y, (255, 200, 240), 20)
            self.sounds.play("golden", 0, self.now)
        else:
            self.sounds.play("buy", 0, self.now)

    def buy_upgrade(self, uid):
        s = self.state
        u = UPGRADES_BY_ID[uid]
        if E.ulv(s, uid) >= u["max"]:
            return
        if not E.seasonal_ok(s, u):
            return self.deny(f"Only for sale at {SEASONS[u['season']]['name']}.")
        if not E.spend(s, E.upgrade_cost(s, uid)):
            return self.deny("Not enough scales.")
        E.remember_seasonal(s, u)
        s["upgrades"][uid] = E.ulv(s, uid) + 1
        if uid == "infinity":
            self.toast(f"Infinity Tank! Room for {E.capacity(s)} catfish.", (150, 230, 160), 5)
            self.place_pending()
        if uid == "tank":
            self.toast(f"Upgraded to {TANK_NAMES[E.ulv(s, 'tank')]}! Room for {E.capacity(s)} fish.", (150, 230, 160), 5)
            self.place_pending()
        elif uid in ("conditioner", "plants"):
            self.tank.build_static()
        elif uid == "jar" and E.ulv(s, "jar") == 1:
            self.toast("Scale Jar placed! It fills while you're away - click it to collect.", (255, 214, 90), 6)
        elif uid == "hatchery" and E.ulv(s, "hatchery") == 1:
            self.toast("Hatchery built! Lay an egg in Shop > Hatchery.", (255, 214, 90), 6)
        self.sounds.play("buy", 0, self.now)

    # ------------------------------------------------------------ jar & hatchery
    def collect_jar(self):
        amt = E.collect_jar(self.state)
        if amt < 1:
            self.toast("The Scale Jar is still filling up.", (200, 200, 230), 2.5)
            return 0
        jx, jy = self.tank.jar_pos()
        self.tank.float_text(jx + 6, jy - 14, "+" + E.fmt(amt), (255, 214, 90))
        self.tank.burst(jx, jy - 10, (255, 214, 90), 14)
        self.sounds.play("golden", 0, self.now)
        return amt

    def hatch_ready(self):
        s = self.state
        ready = [e for e in s["eggs"] if e["left"] <= 0]
        total = 0.0
        nx, ny = self.tank.nest_pos()
        levels = 0.0
        lv_before = {f["uid"]: f["lv"] for f in s["fish"]}
        empties = 0
        babies = []
        relay = [e["c"] for e in ready if e["c"] != "mystery"]
        for e in ready:
            out = E.hatch(s, e)
            if out.get("mystery"):
                self.mystery_message(out)
            if out["empty"]:
                empties += 1
                continue
            levels += E.clutch_levels(s, e["c"])
            total += out["amt"]
            if out["baby"]:
                babies.append(out["baby"])
            for _ in range(3):
                self.tank.burst(nx, ny - 6, CLUTCHES_BY_ID[e["c"]]["color"], 6)
            self.tank.spawn_fry(nx, ny - 4, {"quick": 5, "class": 9, "golden": 14}.get(e["c"], 6),
                                CLUTCHES_BY_ID[e["c"]]["color"])
        if empties:
            self.toast("No fry came out of " + ("an egg" if empties == 1 else f"{empties} eggs") +
                       " this time. Better luck next egg!", (200, 200, 230), 5)
        if ready and E.ulv(s, "autonest") and not s.get("autonest_off"):
            laid = 0
            for cid in relay:
                if E.lay(s, cid):
                    laid += 1
            if laid:
                self.toast(f"Auto-Nest laid {laid} new egg{'s' if laid > 1 else ''}.", (200, 220, 255), 4)
        self.tank.sync()
        for b in babies:
            name = SPECIES_BY_ID[b["sp"]]["name"]
            if b in s["fish"]:
                a = self.tank.fish.get(b["uid"])
                if a:
                    a.x, a.y, a.levelfx = nx, ny - 6, 2.0
                self.toast(f"A baby {name} hatched! Say hi to {b['name']}." +
                           ("  It's SHINY!" if b.get("shiny") else ""), (150, 230, 160), 6)
            else:
                self.toast(f"A baby {name} hatched, but the tank is full!", (255, 200, 150), 6)
        if babies:
            self.sounds.play("golden", 0, self.now)
        if total > 0:
            for f in s["fish"]:
                a = self.tank.fish.get(f["uid"])
                if a and f["lv"] > lv_before.get(f["uid"], f["lv"]):
                    a.levelfx = 2.0
            self.tank.float_text(nx - 4, ny - 12, "+" + E.fmt(total), (255, 214, 90))
            grow = f"every fish +{levels:.1f} levels" if levels >= 1 else "every fish got XP"
            self.toast(f"Hatched {len(ready)} egg{'s' if len(ready) > 1 else ''}! +{E.fmt(total)} scales, {grow}",
                       (255, 230, 150), 6)
            self.sounds.play("level", 0, self.now)
        return total

    def mystery_message(self, out):
        b = out.get("baby")
        msg = {"empty": ("The Mystery Egg was empty... spooky!", (200, 200, 230)),
               "scales": (f"The Mystery Egg was full of scales! +{E.fmt(out['amt'])}", (255, 214, 90)),
               "levels": ("The Mystery Egg made every fish grow 2 levels!", (150, 230, 160))}.get(out["mystery"])
        if out["mystery"] == "rare" and b:
            msg = (f"WOW! The Mystery Egg hatched a brand new species: {SPECIES_BY_ID[b['sp']]['name']}!",
                   (255, 150, 230))
        elif out["mystery"] == "baby" and b:
            msg = (f"The Mystery Egg hatched a baby {SPECIES_BY_ID[b['sp']]['name']}!" +
                   ("  It's SHINY!" if b.get("shiny") else ""), (210, 180, 255))
        if msg:
            self.toast(msg[0], msg[1], 7)

    def toggle_autonest(self):
        s = self.state
        s["autonest_off"] = not s.get("autonest_off")
        self.toast("Auto-Nest paused - pick any egg you like." if s["autonest_off"] else
                   "Auto-Nest is back on.", (200, 220, 255), 4)

    def remove_egg(self, egg):
        """take an egg out of the nest (to swap it for a different one)"""
        s = self.state
        if egg not in s["eggs"]:
            return
        s["eggs"].remove(egg)
        if egg["c"] == "mystery":
            s["mystery"] = s.get("mystery", 0) + 1
            self.toast("Mystery Egg put back in your stash.", (210, 180, 255), 3)
        else:
            self.toast(f"{CLUTCHES_BY_ID[egg['c']]['name']} removed from the nest.", (200, 200, 230), 3)

    def collect_all(self):
        got = 0
        if E.ulv(self.state, "jar") and self.state["jar"] >= 1:
            got += self.collect_jar()
        if any(e["left"] <= 0 for e in self.state["eggs"]):
            got += self.hatch_ready() + 1
        if not got:
            self.toast("Nothing to collect yet.", (200, 200, 230), 2)

    # ------------------------------------------------------------ visitors
    def visitor_arrived(self, kind):
        self.toast(f"A {kind['name']} is visiting! Click it for a gift.", (170, 230, 255), 6)
        self.sounds.play("pet", 0, self.now)

    def catch_visitor(self):
        v = self.tank.visitor
        if not v:
            return
        kind = v["v"]
        amt = (max(25.0, E.income(self.state) * kind["secs"]) * (1 + 0.5 * E.tlv(self.state, "friends"))
               * (1 + E.ulv(self.state, "bait")) * (1 + 0.6 * E.ulv(self.state, "treats")))
        E.earn(self.state, amt)
        st = self.state["stats"]
        st["visitors"] = st.get("visitors", 0) + 1
        self.tank.float_text(v["x"], v["y"] - 8, "+" + E.fmt(amt), (255, 214, 90))
        self.tank.burst(v["x"], v["y"] - 3, (255, 230, 150), 12)
        self.tank.visitor = None
        self.toast(f"The {kind['name']} left you a gift: +{E.fmt(amt)} scales!", (255, 230, 150), 5)
        if random.random() < MYSTERY_FROM_VISITOR:
            self.found_mystery(v["x"], v["y"])
        self.sounds.play("golden", 0, self.now)

    # ------------------------------------------------------------ renaming (needs keyboard focus)
    NAME_MAX = 14

    def start_rename(self, f):
        self.renaming = f
        self.rename_text = f["name"]
        self.prev_fg = winutil.foreground()
        winutil.set_activatable(self.hwnd, True)
        pygame.key.start_text_input()

    def finish_rename(self, save):
        f = self.renaming
        if f is None:
            return
        name = self.rename_text.strip()
        if save and name:
            f["name"] = name
            f["named"] = True
            self.toast(f"Say hi to {name}!", (150, 230, 160), 3)
        elif save:                    # saved with an empty box = remove the name tag
            self.clear_name(f)
        self.renaming = None
        pygame.key.stop_text_input()
        winutil.set_activatable(self.hwnd, False)
        if self.prev_fg and self.prev_fg != self.hwnd:
            winutil.restore_foreground(self.prev_fg)
        self.prev_fg = None

    def clear_name(self, f):
        """take a fish's custom name away (it gets a normal random name back, no tag)"""
        taken = {x["name"] for x in self.state["fish"] if x is not f}
        pool = [n for n in FISH_NAMES if n not in taken] or FISH_NAMES
        f["name"] = random.choice(pool)
        f["named"] = False
        self.toast("Name tag removed.", (200, 200, 230), 3)

    def remove_name(self):
        self.rename_text = ""
        self.finish_rename(True)

    def key_down(self, e):
        if self.renaming is None:
            if e.key == pygame.K_ESCAPE:
                self.ui.panel = None
            return
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.finish_rename(True)
        elif e.key == pygame.K_ESCAPE:
            self.finish_rename(False)
        elif e.key == pygame.K_BACKSPACE:
            self.rename_text = self.rename_text[:-1]

    def text_input(self, txt):
        if self.renaming is None:
            return
        from .pixfont import _GLYPHS
        for ch in txt:
            if ch in _GLYPHS and len(self.rename_text) < self.NAME_MAX:
                self.rename_text += ch

    # ------------------------------------------------------------ themes
    def theme_action(self, tid):
        s = self.state
        th = THEMES_BY_ID[tid]
        if tid not in s["themes"]:
            if not E.theme_visible(s, tid):
                return self.deny(f"Only for sale at {SEASONS[th['season']]['name']}.")
            if not E.spend(s, E.theme_cost(s, tid)):
                return self.deny("Not enough scales.")
            s["themes"].append(tid)
            self.toast(f"Unlocked {th['name']}! +{th['bonus']}% scales forever.", (150, 230, 160), 5)
            self.sounds.play("buy", 0, self.now)
        s["theme"] = tid
        self.tank.build_static()

    def lay_clutch(self, cid):
        s = self.state
        if len(s["eggs"]) >= E.egg_slots(s):
            return self.deny("All nest slots are full. Upgrade the Hatchery for more.")
        if not E.lay(s, cid):
            return self.deny("You don't have a Mystery Egg.")
        self.toast(f"{CLUTCHES_BY_ID[cid]['name']} laid! Hatches in {E.fmt_time(E.clutch_time(s, cid))}.",
                   (255, 230, 150), 4)
        self.sounds.play("plop", 0, self.now)

    def buy_toy(self, tid):
        s = self.state
        if E.toy_lv(s, tid) >= TOY_MAX_LEVEL:
            return
        if not E.seasonal_ok(s, TOYS_BY_ID[tid]):
            return self.deny(f"Only for sale at {SEASONS[TOYS_BY_ID[tid]['season']]['name']}.")
        if not E.spend(s, E.toy_cost(s, tid)):
            return self.deny("Not enough scales.")
        E.remember_seasonal(s, TOYS_BY_ID[tid])
        if tid in s["toys"]:
            s["toys"][tid]["lv"] += 1
        else:
            s["toys"][tid] = dict(lv=1)
            self.toast(f"New toy: {TOYS_BY_ID[tid]['name']}! (drag it to move it)", (150, 230, 160), 5)
        self.tank.sync()
        self.sounds.play("buy", 0, self.now)

    def rehome(self, uid):
        """sell a fish from the tank"""
        s = self.state
        if len(s["fish"]) <= 1 and not s.get("pending"):
            return
        f = next((x for x in s["fish"] if x["uid"] == uid), None)
        if not f:
            return
        refund = E.sell_value(s, f)
        s["fish"].remove(f)
        E.earn(s, refund)
        self.toast(f"Sold {f['name']} to a good home. (+{E.fmt(refund)})", (200, 200, 230))
        self.place_pending()
        self.tank.sync()

    def grew_up(self, f):
        a = self.tank.fish.get(f["uid"])
        if a:
            a.levelfx = 2.5
            self.tank.burst(a.x, a.y, (255, 240, 150), 14)
            self.tank.float_text(a.x, a.y - 8, "All grown up!", (150, 230, 160))
        self.toast(f"{f['name']} grew up into a big {SPECIES_BY_ID[f['sp']]['name']}!", (150, 230, 160), 5)
        self.sounds.play("level", 0.3, self.now)

    def place_pending(self):
        """move waiting hatchlings into the tank while there's room"""
        s = self.state
        while s.get("pending") and len(s["fish"]) < E.capacity(s):
            b = s["pending"].pop(0)
            E.start_growing(b)
            s["fish"].append(b)
            a_x, a_y = self.tank.nest_pos()
            self.tank.sync()
            a = self.tank.fish.get(b["uid"])
            if a:
                a.x, a.y = a_x, a_y - 6
            self.toast(f"{b['name']} the baby {SPECIES_BY_ID[b['sp']]['name']} moved into the tank!",
                       (150, 230, 160), 5)
        self.tank.sync()

    def sell_pending(self):
        """sell the hatchling that has no room"""
        s = self.state
        if not s.get("pending"):
            return
        b = s["pending"][0]
        val = E.sell_value(s, b)
        s["pending"].pop(0)
        E.earn(s, val)
        self.toast(f"Sold the baby {SPECIES_BY_ID[b['sp']]['name']}. (+{E.fmt(val)})", (200, 200, 230))
        self.sounds.play("buy", 0, self.now)

    # ------------------------------------------------------------ pearl tree
    def buy_tree(self, nid):
        from .data import PEARL_TREE_BY_ID
        st = E.tree_state(self.state, nid)
        if st == "locked":
            n = PEARL_TREE_BY_ID[nid]
            return self.deny(f"Unlock {PEARL_TREE_BY_ID[n['req']]['name']} first.")
        if st == "poor":
            return self.deny("Not enough pearls. Spawn again to earn more!")
        if E.tree_buy(self.state, nid):
            self.toast(f"{PEARL_TREE_BY_ID[nid]['name']} is now Lv {E.tlv(self.state, nid)}!", (230, 220, 255), 4)
            self.sounds.play("level", 0, self.now)

    def use_food(self, fid):
        s = self.state
        kind = FOODS_BY_ID[fid]
        if s["earned_total"] < kind["unlock"]:
            return
        if self.now < self.food_cd.get(fid, 0):
            return
        c = E.food_cost(s, fid)
        if not E.spend(s, c):
            return self.deny("Not enough scales.")
        self.food_cd[fid] = self.now + kind["cooldown"]
        self.tank.drop_food(kind)
        if kind.get("buff"):
            name, dur = kind["buff"]
            s["buffs"][name] = s["buffs"].get(name, 0) + dur
            self.toast(f"{kind['name']}: {kind['desc'].split('.')[0]}!", (255, 220, 120))
        self.sounds.play("plop", 0, self.now)

    def toggle_chill(self):
        s = self.state
        s["chill"] = not s["chill"]
        self.toast("Chill mode ON: needs paused, no pop-bubbles." if s["chill"] else "Chill mode OFF.",
                   (170, 210, 255))

    def spawn(self):
        s = self.state
        pearls = E.pearls_for(s)
        if pearls <= 0:
            return
        keep = dict(s)
        keep["pearls"] = s["pearls"] + pearls
        keep["spawns"] = s["spawns"] + 1
        self.state = E.new_state(keep=keep)
        self.state["chill"] = s["chill"]
        self.tank.state = self.state
        self.tank.foods.clear()
        self.tank.pops.clear()
        self.sounds.settings = self.state["settings"]
        self.tank.sync()
        self.save()
        self.toast(f"Spawning Season! +{pearls} pearls. Spend them in Shop > Pearls.", (230, 220, 255), 8)
        self.sounds.play("level", 0, self.now)

    def reset_save(self):
        settings = self.state["settings"]
        self.state = E.new_state()
        self.state["settings"] = settings
        self.tank.state = self.state
        self.tank.sync()
        self.save()
        self.toast("Fresh tank. Hi again, Sunny!", (255, 220, 120))

    def change_setting(self, key, value):
        self.state["settings"][key] = value
        if key in ("width", "align", "scale", "monitor", "uiscale"):
            self.relayout()
        elif key in ("opacity", "topmost"):
            winutil.style_overlay(self.hwnd, KEY, self.state["settings"]["opacity"], self.state["settings"]["topmost"])

    def quit(self):
        self.running = False

    # ------------------------------------------------------------ draw
    def draw(self):
        E.cache_on()
        try:
            self._draw()
        finally:
            E.cache_off()

    def _draw(self):
        self.fit_compact()
        scr = self.screen
        scr.fill((18, 22, 34) if self.compact else KEY)
        r = self.tank_rect
        if not self.minimized:
            low = self.tank.draw()
            scr.blit(pygame.transform.scale(low, (r.w, r.h)), r.topleft)
        self.ui.draw(scr)
