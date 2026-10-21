"""The aquarium: fish actors, food, bubbles, toys, plants. Low-res coordinates."""
import math
import random
import time

import pygame

from . import sprites
from .data import SPECIES_BY_ID, TOYS, TOYS_BY_ID, CLUTCHES_BY_ID, THEMES_BY_ID, VISITORS, VISIT_EVERY, SKULL_POP_EVERY
from . import economy as E
from .sprites import lerp, dark, light

TANK_H = 64          # low-res height of the whole tank incl. rim and stand
RIM = 3              # rim rows
STAND = 4            # stand rows
SAND = 7             # sand rows
WATER_TOP = RIM + 1


class Particle:
    __slots__ = ("kind", "x", "y", "vx", "vy", "life", "max", "col", "text")

    def __init__(self, kind, x, y, vx=0, vy=0, life=1.0, col=(255, 255, 255), text=""):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.life = self.max = life
        self.col, self.text = col, text


class Food:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x, self.y = x, y
        self.vx = random.uniform(-2, 2)
        self.float_t = 1.0 if kind["id"] == "flakes" else 0.0
        self.life = 30.0
        self.claimed = None
        self.settled = False


class PopBubble:
    def __init__(self, x, y, golden=False, skull=False):
        self.x, self.y = x, y
        self.golden = golden
        self.skull = skull          # from the Pumpkin Catfish: worth 3x
        self.r = 4 if golden else 3
        self.vy = random.uniform(-5, -3.5)
        self.phase = random.uniform(0, 6.28)
        self.surface_t = 0.0
        self.age = 0.0


class ToyActor:
    def __init__(self, tid, state):
        self.tid = tid
        self.st = state           # {"lv":..,"x":frac}
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.timer = random.uniform(10, 30)
        self.open = 0.0
        self.roll = 0.0


class FishActor:
    def __init__(self, f, tank):
        self.f = f
        self.tank = tank
        self.sp = SPECIES_BY_ID[f["sp"]]
        lo, hi = self.zone()
        self.x = random.uniform(10, tank.w - 10)
        self.y = random.uniform(lo, hi)
        self.vx = self.vy = 0.0
        self.tx, self.ty = self.x, self.y
        self.facing = random.random() < 0.5
        self.state = "wander"
        self.timer = random.uniform(0, 3)
        self.anim = random.uniform(0, 2)
        self.phase = random.uniform(0, 6.28)
        self.pet_t = 0.0
        self.toy = None
        self.food = None
        self.levelfx = 0.0
        self.think_t = random.uniform(0, 4)
        self.shed = 0.0
        self.shed_t = random.uniform(2, 8)
        self.play_acc = 0.0
        self.skull_t = random.uniform(*SKULL_POP_EVERY)

    @property
    def inverted(self):
        return self.sp["habitat"] == "inverted"

    def zone(self):
        t = self.tank
        H = self.sp["size"][1]
        hab = self.sp["habitat"]
        if hab == "bottom":
            return t.sand_y - 14, t.sand_y - H / 2 - 1
        if hab == "mid":
            return WATER_TOP + 6, t.sand_y - 10
        if hab == "inverted":
            return WATER_TOP + 4, WATER_TOP + 20
        return WATER_TOP + 5, t.sand_y - H / 2 - 1          # glass grazers

    def size_k(self):
        """drawing scale: hatched babies start at 30% size and grow to 100%"""
        g = E.growth(self.f)
        return 1.0 if g >= 1 else round((0.3 + 0.7 * g) * 10) / 10

    def rect(self):
        L, H = self.sp["size"]
        k = self.size_k()
        L, H = max(3, L * k), max(2, H * k)
        return pygame.Rect(int(self.x - L / 2 - 2), int(self.y - H / 2 - 2), int(L + 4), int(H + 4))

    def pick_target(self):
        lo, hi = self.zone()
        t = self.tank
        self.tx = random.uniform(8, t.w - 8)
        if random.random() < 0.6:   # short hops look more natural
            self.tx = min(t.w - 8, max(8, self.x + random.uniform(-45, 45)))
        self.ty = random.uniform(lo, hi)

    def think(self):
        t = self.tank
        r = random.random()
        hab = self.sp["habitat"]
        self.toy = None
        if t.mouse and r < 0.12 and abs(t.mouse[0] - self.x) < 40:
            self.state = "curious"
            self.timer = random.uniform(2, 4)
        elif r < 0.6 and t.toys:
            self.toy = random.choice(list(t.toys.values()))
            self.state = "play"
            self.timer = random.uniform(5, 10)
            self.play_acc = 0.0
        elif r < (0.65 if hab == "glass" else 0.5):
            self.state = "rest"
            self.timer = random.uniform(3, 9 if hab == "glass" else 6)
            if hab == "bottom":
                self.ty = self.zone()[1]
        else:
            self.state = "wander"
            self.timer = random.uniform(3, 7)
            self.pick_target()

    def update(self, dt):
        t = self.tank
        sp = self.sp
        speed = sp["speed"] * (1.25 if "frenzy" in t.state["buffs"] else 1.0)
        self.anim += dt * (2.0 + (abs(self.vx) + abs(self.vy)) * 0.35)
        self.levelfx = max(0.0, self.levelfx - dt)
        self.think_t -= dt

        # food first
        if self.food is not None and (self.food not in t.foods):
            self.food = None
        if self.food is None and self.f["full"] < 96 and t.foods and self.pet_t <= 0:
            best = None
            for fd in t.foods:
                if fd.claimed and fd.claimed is not self:
                    continue
                d = abs(fd.x - self.x) + abs(fd.y - self.y)
                if best is None or d < best[0]:
                    best = (d, fd)
            if best:
                self.food = best[1]
                best[1].claimed = self
        if self.pet_t > 0:
            self.pet_t -= dt
            self.tx, self.ty = self.x, self.y
            self.anim += dt * 6
            spd = 0
        elif self.food is not None:
            self.tx, self.ty = self.food.x, self.food.y
            spd = speed * 1.7
            if abs(self.food.x - self.x) < 3 and abs(self.food.y - self.y) < 3:
                t.on_eat(self, self.food)
                self.food = None
                self.state = "rest"
                self.timer = 1.5
        else:
            self.timer -= dt
            if self.timer <= 0:
                self.think()
            spd = speed
            if self.state == "rest":
                spd = speed * 0.3
                self.tx = self.x
                if sp["habitat"] != "bottom":
                    self.ty = self.y
            elif self.state == "play" and self.toy:
                toy = self.toy
                ang = self.anim * 0.8 + self.phase
                self.tx = toy.x + math.cos(ang) * 8
                self.ty = min(self.zone()[1], max(WATER_TOP + 3, toy.y - 6 + math.sin(ang) * 3))
                spd = speed * 1.1
                if toy.tid == "ball" and abs(self.x - toy.x) < 4 and abs(self.y - toy.y) < 5:
                    toy.vx += (1 if self.facing else -1) * 14
                t.state_play(self, dt)
            elif self.state == "curious" and t.mouse:
                lo, hi = self.zone()
                self.tx = t.mouse[0] + (-10 if self.x < t.mouse[0] else 10)
                self.ty = min(hi, max(lo, t.mouse[1]))
            elif abs(self.tx - self.x) + abs(self.ty - self.y) < 2:
                self.pick_target()

        # steering
        dx, dy = self.tx - self.x, self.ty - self.y
        d = math.hypot(dx, dy)
        if d > 0.5 and spd > 0:
            k = min(1.0, d / 6)
            want_x, want_y = dx / d * spd * k, dy / d * spd * k * 0.7
        else:
            want_x = want_y = 0.0
        a = min(1.0, dt * 2.4)
        self.vx += (want_x - self.vx) * a
        self.vy += (want_y - self.vy) * a
        self.x += self.vx * dt
        self.y += self.vy * dt
        lo, hi = self.zone()
        self.x = min(t.w - 6, max(6, self.x))
        self.y = min(max(hi, t.sand_y - 3), max(WATER_TOP + 3, self.y))
        if self.vx > 1.0:
            self.facing = True
        elif self.vx < -1.0:
            self.facing = False
        if self.pet_t > 0 and t.mouse:
            self.facing = t.mouse[0] > self.x

        # small breath bubbles
        if random.random() < dt * 0.08:
            L = sp["size"][0]
            t.add_decor_bubble(self.x + (L / 2 if self.facing else -L / 2), self.y - 1)

    def draw(self, surf, time):
        shiny, look = self.f.get("shiny", False), E.fish_look(self.f)
        frames = sprites.fish_frames(self.f["sp"], shiny, look)[(self.facing, self.inverted)]
        img = frames[int(self.anim) % len(frames)]
        ax, ay = sprites.fish_anchor(self.f["sp"], self.facing, self.inverted, shiny, look)
        bob = math.sin(time * 2 + self.phase) * 0.5 if self.state != "rest" else 0
        wig = math.sin(time * 40) * 0.6 if self.pet_t > 0 else 0
        k = self.size_k()
        if k < 1:
            img = sprites.scaled(img, k)
            ax, ay = ax * k, ay * k
        surf.blit(img, (int(self.x - ax + wig), int(self.y - ay + bob)))


class Tank:
    def __init__(self, game, w):
        self.game = game
        self.state = game.state
        self.w = int(w)
        self.h = TANK_H
        self.sand_y = self.h - STAND - SAND
        self.time = 0.0
        self.fish = {}
        self.foods = []
        self.decor = []
        self.pops = []
        self.parts = []
        self.texts = []           # (x, y, text, color, life) drawn hi-res
        self.toys = {}
        self.fry = []             # [x, y, vx, vy, life, colour] baby fish from hatched eggs
        self.rings = []           # [x, y, life] bubble rings from the conch
        self.visitor = None       # dict(v=..., x, y, right, pause)
        self.visit_timer = random.uniform(90, 180)
        self.hour_override = None # for screenshots / tests
        self._tint = None
        self._tint_key = None
        self.mouse = None
        self.pop_timer = 3.0
        self.ghost = None         # Haunted Lagoon: [x, y, dir, life]
        self.ghost_timer = random.uniform(20, 40)
        self.lanterns = []
        self.surface = pygame.Surface((self.w, self.h))
        self.build_static()
        self.sync()

    # ------------------------------------------------------------ setup
    def resize(self, w):
        old = self.w
        self.w = int(w)
        self.surface = pygame.Surface((self.w, self.h))
        for a in self.fish.values():
            a.x = a.x / old * self.w
            a.tx = min(a.tx, self.w - 8)
        self.build_static()
        self.sync()

    def build_static(self):
        rng = random.Random(7)
        w, h = self.w, self.h
        bg = pygame.Surface((w, h))
        clear = E.ulv(self.state, "conditioner") / 25        # water gets clearer & brighter
        th = THEMES_BY_ID.get(self.state.get("theme", "classic"), THEMES_BY_ID["classic"])
        top = lerp(th["water"][0], light(th["water"][0], 0.35), clear)
        bot = lerp(th["water"][1], light(th["water"][1], 0.3), clear)
        bands = 7
        for y in range(WATER_TOP, self.sand_y + 1):
            k = (y - WATER_TOP) / (self.sand_y - WATER_TOP)
            k = int(k * bands) / bands
            pygame.draw.line(bg, lerp(top, bot, k), (0, y), (w, y))
        # light rays
        ray = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(max(2, w // 70)):
            x0 = rng.uniform(0, w)
            pygame.draw.polygon(ray, (255, 255, 230, 14),
                                [(x0, WATER_TOP), (x0 + 10, WATER_TOP), (x0 - 12, self.sand_y), (x0 - 30, self.sand_y)])
        bg.blit(ray, (0, 0))
        # far rocks
        x = 0
        while x < w:
            rw = rng.randint(14, 34)
            rh = rng.randint(4, 10)
            pygame.draw.ellipse(bg, lerp(th["rock"], bot, 0.25), (x, self.sand_y - rh + 2, rw, rh * 2))
            x += rw - rng.randint(0, 6)
        # sand
        for y in range(self.sand_y, h - STAND):
            k = (y - self.sand_y) / SAND
            pygame.draw.line(bg, lerp(th["sand"][0], th["sand"][1], k), (0, y), (w, y))
        for _ in range(w // 3):
            px, py = rng.randint(0, w - 1), rng.randint(self.sand_y + 1, h - STAND - 1)
            bg.set_at((px, py), rng.choice([(150, 120, 80), (240, 222, 180), (120, 110, 100), (200, 170, 120)]))
        for x in range(0, w, 3):  # wavy sand edge
            if rng.random() < 0.5:
                bg.set_at((x, self.sand_y - 1), dark(th["sand"][0], 0.95))
        self.lanterns = []
        if th["id"] == "haunted":
            self.build_haunted(bg, rng)
        # frame
        pygame.draw.rect(bg, (26, 28, 36), (0, 0, w, RIM))
        pygame.draw.line(bg, (78, 82, 96), (0, 1), (w, 1))
        pygame.draw.rect(bg, (96, 66, 42), (0, h - STAND, w, STAND))
        pygame.draw.line(bg, (130, 92, 60), (0, h - STAND), (w, h - STAND))
        pygame.draw.line(bg, (62, 42, 28), (0, h - 1), (w, h - 1))
        for y in range(RIM, h - STAND):
            bg.set_at((0, y), (26, 28, 36))
            bg.set_at((w - 1, y), (26, 28, 36))
            bg.set_at((1, y), (120, 180, 210))
        self.static = bg
        # plants
        self.plants = []
        n = int(max(6, w // 14) * (1 + 0.35 * E.ulv(self.state, "plants")))
        for i in range(n):
            x = rng.uniform(4, w - 4)
            hgt = rng.uniform(10, self.sand_y - WATER_TOP - 6)
            col = rng.choice(th["plants"])
            back = rng.random() < 0.75
            if not back:
                hgt *= 0.5
            self.plants.append(dict(x=x, h=hgt, col=col if back else light(col, 0.15),
                                    phase=rng.uniform(0, 6), back=back, leaf=rng.random() < 0.5))

    def build_haunted(self, bg, rng):
        w, sy = self.w, self.sand_y
        # crescent moon shining through the water
        mx, my = w - 18, WATER_TOP + 8
        pygame.draw.circle(bg, (250, 240, 190), (mx, my), 5)
        pygame.draw.circle(bg, bg.get_at((mx + 6, my - 5))[:3], (mx + 2, my - 1), 4)
        # cobwebs in the top corners
        for cx, d in ((2, 1), (w - 3, -1)):
            for i in range(9):
                bg.set_at((cx + d * i, WATER_TOP + i // 3), (200, 200, 215))
                bg.set_at((cx + d * (i // 3), WATER_TOP + i), (200, 200, 215))
            for r in (3, 6):
                for j in range(r + 1):
                    bg.set_at((cx + d * j, WATER_TOP + r - j), (170, 170, 190))
        # gravestones
        x = rng.uniform(10, 30)
        while x < w - 12:
            gw, gh = rng.choice(((5, 7), (6, 8), (4, 6)))
            gx = int(x)
            col = rng.choice(((120, 118, 130), (100, 98, 112), (140, 138, 148)))
            pygame.draw.rect(bg, col, (gx, sy - gh + 1, gw, gh))
            pygame.draw.rect(bg, col, (gx + 1, sy - gh, gw - 2, 1))
            cx = gx + gw // 2
            pygame.draw.line(bg, dark(col, 0.7), (cx, sy - gh + 2), (cx, sy - gh + 4))
            pygame.draw.line(bg, dark(col, 0.7), (cx - 1, sy - gh + 3), (cx + 1, sy - gh + 3))
            x += rng.uniform(40, 90)
        # jack-o'-lanterns (their faces flicker, so they're drawn every frame)
        x = rng.uniform(25, 60)
        while x < w - 10:
            self.lanterns.append((int(x), sy + 2))
            x += rng.uniform(55, 110)

    def draw_lanterns(self, s, t):
        for i, (x, y) in enumerate(self.lanterns):
            pygame.draw.ellipse(s, (226, 116, 24), (x - 3, y - 4, 7, 5))
            s.set_at((x - 1, y - 4), (196, 96, 20))
            s.set_at((x + 1, y - 4), (196, 96, 20))
            s.set_at((x, y - 5), (70, 120, 40))
            glow = lerp((255, 190, 50), (255, 245, 160), 0.5 + 0.5 * math.sin(t * 9 + i * 2.1))
            for dx, dy in ((-2, -3), (1, -3), (-2, -1), (-1, -1), (0, -1), (1, -1)):
                s.set_at((x + dx + (1 if dx >= 0 else 0), y + dy), glow)

    def haunted(self):
        return self.state.get("theme") == "haunted"

    def sync(self):
        """match actors to state (fish list, toys)"""
        uids = {f["uid"] for f in self.state["fish"]}
        for uid in list(self.fish):
            if uid not in uids:
                del self.fish[uid]
        for f in self.state["fish"]:
            if f["uid"] not in self.fish:
                self.fish[f["uid"]] = FishActor(f, self)
            else:
                self.fish[f["uid"]].f = f
        for tid in list(self.toys):
            if tid not in self.state["toys"]:
                del self.toys[tid]
        order = [t["id"] for t in TOYS]
        for tid, st in self.state["toys"].items():
            if tid not in self.toys:
                if "x" not in st:
                    if TOYS_BY_ID[tid].get("season"):      # seasonal ones would all bunch up at the end
                        same = [t["id"] for t in TOYS if t.get("season") == TOYS_BY_ID[tid]["season"]]
                        st["x"] = 0.14 + 0.24 * same.index(tid)
                    else:
                        st["x"] = (order.index(tid) + 0.5) / len(order) * 0.9 + 0.05
                a = ToyActor(tid, st)
                self.toys[tid] = a
            a = self.toys[tid]
            a.st = st
            if tid == "ball":
                if a.y == 0:
                    a.x, a.y = st["x"] * self.w, WATER_TOP + 3
            elif tid in ("lilypad", "duck"):
                a.x, a.y = st["x"] * self.w, WATER_TOP + 3
            else:
                a.x = st["x"] * self.w
                a.y = self.sand_y + 1

    # ------------------------------------------------------------ spawning
    def add_decor_bubble(self, x, y, big=False, skull=False):
        if len(self.decor) < 160:
            self.decor.append([x, y, random.uniform(-14, -8), random.uniform(0, 6), 2 if skull else 1 if big else 0])

    def spawn_skull(self, a):
        if len(self.pops) < 14:
            self.pops.append(PopBubble(a.x, a.y - 3, skull=True))

    def spawn_pop(self, x=None, y=None, golden=None):
        if len(self.pops) >= 12:
            return
        if x is None:
            if self.fish and random.random() < 0.7:
                a = random.choice(list(self.fish.values()))
                x, y = a.x, a.y - 3
            else:
                x, y = random.uniform(10, self.w - 10), self.sand_y - 4
        if golden is None:
            golden = random.random() < E.golden_chance(self.state)
        self.pops.append(PopBubble(x, y, golden))

    def drop_food(self, kind, x=None):
        if x is None:
            # aim near hungry fish
            if self.fish:
                a = min(self.fish.values(), key=lambda a: a.f["full"])
                x = a.x + random.uniform(-10, 10)
            else:
                x = random.uniform(10, self.w - 10)
        n = 6 if kind["id"] == "flakes" else 3 if kind["id"] in ("pellets", "bloodworms", "brine") else 1
        if kind["id"] in ("seeds", "kelp", "shrimp"):
            n = 2
        for i in range(n):
            self.foods.append(Food(kind, min(self.w - 4, max(4, x + random.uniform(-6, 6))),
                                   WATER_TOP + 1 + random.uniform(0, 2)))

    def spawn_fry(self, x, y, n, col):
        for _ in range(n):
            self.fry.append([x + random.uniform(-4, 4), y + random.uniform(-2, 2), random.uniform(-12, 12),
                             random.uniform(-8, -2), random.uniform(60, 110), col])

    def burst(self, x, y, col, n=6, kind="spark"):
        for _ in range(n):
            a = random.uniform(0, 6.28)
            s = random.uniform(8, 20)
            self.parts.append(Particle(kind, x, y, math.cos(a) * s, math.sin(a) * s - 5,
                                       random.uniform(0.4, 0.8), col))

    def heart(self, x, y):
        self.parts.append(Particle("heart", x + random.uniform(-3, 3), y - 4, random.uniform(-2, 2), -10,
                                   1.1, (255, 110, 150)))

    def float_text(self, x, y, text, col=(255, 255, 255)):
        self.texts.append([x, y, text, col, 1.4])

    # ------------------------------------------------------------ hooks (game sets these)
    def on_eat(self, actor, food):
        if food in self.foods:
            self.foods.remove(food)
        self.game.fish_ate(actor, food.kind)

    def state_play(self, actor, dt):
        self.game.fish_played(actor, dt)

    # ------------------------------------------------------------ queries
    def fish_at(self, x, y):
        best = None
        for a in self.fish.values():
            if a.rect().collidepoint(x, y):
                d = abs(a.x - x) + abs(a.y - y)
                if best is None or d < best[0]:
                    best = (d, a)
        return best[1] if best else None

    def pop_at(self, x, y):
        for p in reversed(self.pops):
            if (p.x - x) ** 2 + (p.y - y) ** 2 <= (p.r + 2.5) ** 2:
                return p
        return None

    # ------------------------------------------------------------ visitors
    def update_visitor(self, dt):
        v = self.visitor
        if v is None:
            self.visit_timer -= dt
            if self.visit_timer <= 0 and self.fish:
                self.visit_timer = (random.uniform(*VISIT_EVERY) / (1 + 0.15 * E.tlv(self.state, "friends"))
                                    / (1 + 0.2 * E.ulv(self.state, "treats")))
                kind = random.choices(VISITORS, weights=[x["weight"] for x in VISITORS])[0]
                right = random.random() < 0.5
                y = self.sand_y - 1 if kind["where"] == "sand" else random.uniform(WATER_TOP + 10, self.sand_y - 12)
                self.visitor = dict(v=kind, x=-8.0 if right else self.w + 8.0, y=y, base_y=y, right=right,
                                    pause=0.0)
                self.game.visitor_arrived(kind)
            return
        if v["pause"] > 0:
            v["pause"] -= dt
        else:
            v["x"] += v["v"]["speed"] * dt * (1 if v["right"] else -1)
            if v["v"]["where"] == "sand" and random.random() < dt * 0.3:
                v["pause"] = random.uniform(1, 3)
        if v["v"]["where"] == "mid":
            v["y"] = v["base_y"] + math.sin(self.time * 1.2) * 2
        if v["x"] < -12 or v["x"] > self.w + 12:
            self.visitor = None

    def visitor_at(self, x, y):
        v = self.visitor
        return v is not None and abs(v["x"] - x) <= 8 and v["y"] - 8 <= y <= v["y"] + 3

    # ------------------------------------------------------------ day / night
    def daylight(self):
        """(rgb, alpha) tint for the current real-world time of day"""
        if not self.state["settings"].get("daynight", True):
            return None
        if self.hour_override is not None:
            h = self.hour_override
        else:
            lt = time.localtime()
            h = lt.tm_hour + lt.tm_min / 60
        keys = [(0, (10, 20, 60), 105), (5, (10, 20, 60), 105), (6.5, (255, 170, 130), 40),
                (8, (255, 255, 255), 0), (15, (255, 255, 255), 0), (17, (255, 190, 110), 35),
                (19, (140, 80, 150), 55), (20.5, (20, 30, 80), 95), (24, (10, 20, 60), 105)]
        for (h0, c0, a0), (h1, c1, a1) in zip(keys, keys[1:]):
            if h0 <= h <= h1:
                k = (h - h0) / (h1 - h0)
                return lerp(c0, c1, k), int(a0 + (a1 - a0) * k)
        return None

    BRIGHT_STEPS = 5

    def apply_brightness(self, s):
        """player's brightness override (-5 darkest .. +5 brightest), on top of day/night"""
        b = int(self.state["settings"].get("brightness", 0))
        if not b:
            return
        area = pygame.Rect(1, WATER_TOP, self.w - 2, self.h - STAND - WATER_TOP)
        if b > 0:
            k = 14 * b
            s.fill((k, k, k), area, special_flags=pygame.BLEND_RGB_ADD)
        else:
            v = int(255 * (1 - 0.12 * -b))
            s.fill((v, v, v), area, special_flags=pygame.BLEND_RGB_MULT)

    def tint_surface(self):
        d = self.daylight()
        if not d or d[1] <= 0:
            return None
        key = (d[0], d[1] // 3, self.w)
        if key != self._tint_key:
            self._tint_key = key
            surf = pygame.Surface((self.w - 2, self.h - STAND - WATER_TOP), pygame.SRCALPHA)
            surf.fill((*d[0], d[1]))
            self._tint = surf
        return self._tint

    def spot_x(self, key, default):
        """saved x position (fraction of tank width) for the jar / nest"""
        f = self.state.get("spots", {}).get(key)
        return int(f * self.w) if f is not None else default

    def move_spot(self, key, x):
        self.state.setdefault("spots", {})[key] = min(self.w - 10, max(8, x)) / self.w

    def jar_pos(self):
        return self.spot_x("jar", 9), self.sand_y + 1

    def nest_pos(self):
        return self.spot_x("nest", self.w - 14), self.sand_y + 1

    def jar_at(self, x, y):
        if not E.ulv(self.state, "jar"):
            return False
        jx, jy = self.jar_pos()
        return jx - 6 <= x <= jx + 6 and jy - 15 <= y <= jy + 1

    def nest_at(self, x, y):
        if not E.ulv(self.state, "hatchery"):
            return False
        nx, ny = self.nest_pos()
        return nx - 10 <= x <= nx + 10 and ny - 9 <= y <= ny + 2

    def toy_at(self, x, y):
        for a in self.toys.values():
            w, h = sprites.TOY_SIZE[a.tid]
            r = pygame.Rect(int(a.x - w / 2), int(a.y - h), w, h)
            if a.tid == "ball":
                r = pygame.Rect(int(a.x - 4), int(a.y - 7), 8, 8)
            if r.collidepoint(x, y):
                return a
        return None

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        s = self.state
        # pop bubbles spawn
        if not s["chill"]:
            self.pop_timer -= dt
            if self.pop_timer <= 0:
                self.spawn_pop()
                from .economy import pop_interval
                self.pop_timer = pop_interval(s) * random.uniform(0.7, 1.3)

        for a in list(self.fish.values()):
            a.update(dt)
            if a.sp.get("season") == "halloween":
                if random.random() < dt * 0.8:
                    self.add_decor_bubble(a.x + random.uniform(-2, 2), a.y - 3, skull=True)
                a.skull_t -= dt
                if a.skull_t <= 0:
                    a.skull_t = random.uniform(*SKULL_POP_EVERY)
                    if not s["chill"]:
                        self.spawn_skull(a)
        if self.haunted():
            self.ghost_timer -= dt
            if self.ghost is None and self.ghost_timer <= 0:
                d = random.choice((-1, 1))
                self.ghost = [self.w + 6 if d < 0 else -6, random.uniform(WATER_TOP + 8, self.sand_y - 14), d, 0.0]
            if self.ghost:
                gh = self.ghost
                gh[3] += dt
                gh[0] += gh[2] * 7 * dt
                if gh[0] < -10 or gh[0] > self.w + 10:
                    self.ghost = None
                    self.ghost_timer = random.uniform(40, 90)
        else:
            self.ghost = None

        # food
        for fd in list(self.foods):
            fd.life -= dt
            if fd.float_t > 0:
                fd.float_t -= dt
                fd.x += fd.vx * dt
            elif not fd.settled:
                fd.y += fd.kind["sink"] * dt
                fd.x += math.sin(self.time * 2 + id(fd) % 7) * dt * 1.5
                if fd.y >= self.sand_y:
                    fd.y = self.sand_y
                    fd.settled = True
            if fd.life <= 0:
                self.foods.remove(fd)

        # decor bubbles
        for b in list(self.decor):
            b[1] += b[2] * dt
            b[3] += dt * 3
            if b[1] < WATER_TOP + 1:
                self.decor.remove(b)
        # pop bubbles
        for p in list(self.pops):
            p.age += dt
            p.phase += dt * 2
            if p.y > WATER_TOP + p.r + 1:
                p.y += p.vy * dt
                p.x += math.sin(p.phase) * dt * 4
            else:
                p.surface_t += dt
                p.x += math.sin(p.phase) * dt * 2
                if p.surface_t > 6:
                    self.pops.remove(p)
                    self.burst(p.x, p.y, (200, 235, 255), 4)
                    self.game.auto_pop(p)

        # toys
        for a in self.toys.values():
            a.timer -= dt
            lv = a.st["lv"]
            if a.tid == "ball":
                a.x += a.vx * dt
                a.vx *= 0.98 ** (dt * 60)
                if a.x < 6 or a.x > self.w - 6:
                    a.vx = -a.vx
                    a.x = min(self.w - 6, max(6, a.x))
                a.y = WATER_TOP + 3 + math.sin(self.time * 1.5) * 0.6
                a.st["x"] = a.x / self.w
            elif a.tid == "marimo":
                a.vx = math.sin(self.time * 0.1 + 1.3) * 2
                a.x = min(self.w - 8, max(8, a.x + a.vx * dt))
                a.roll += a.vx * dt
                a.st["x"] = a.x / self.w
            elif a.tid == "airstone":
                if random.random() < dt * 9:
                    self.add_decor_bubble(a.x + random.uniform(-1, 1), a.y - 4, random.random() < 0.3)
            elif a.tid in ("chest", "clam"):
                if a.open > 0:
                    a.open -= dt
                if a.timer <= 0 and not s["chill"]:
                    a.open = 2.0
                    if a.tid == "chest":
                        a.timer = max(25, 100 - 6 * lv)
                        for _ in range(2 + lv // 3):
                            self.spawn_pop(a.x + random.uniform(-4, 4), a.y - 8, golden=False)
                    else:
                        a.timer = max(30, 90 - 5 * lv)
                        self.spawn_pop(a.x, a.y - 6, golden=random.random() < 0.15 + 0.02 * lv)
            elif a.tid == "ship":
                if random.random() < dt * 0.5:
                    self.add_decor_bubble(a.x + random.uniform(-8, 8), a.y - 8)
            elif a.tid == "volcano":
                if a.timer <= 0:
                    a.timer = max(20, 60 - 3 * lv)
                    for _ in range(14):
                        self.add_decor_bubble(a.x + random.uniform(-2, 2), a.y - 10 - random.uniform(0, 4),
                                              random.random() < 0.5)
                    if not s["chill"]:
                        for _ in range(1 + lv // 4):
                            self.spawn_pop(a.x + random.uniform(-3, 3), a.y - 12)
            elif a.tid == "conch":
                if a.timer <= 0:
                    a.timer = random.uniform(4, 8)
                    self.rings.append([a.x + 7, a.y - 6, 0.0])
            elif a.tid == "lighthouse" or a.tid == "bottle":
                pass
            elif a.tid == "cauldron":
                if random.random() < dt * 4:
                    self.add_decor_bubble(a.x + random.uniform(-3, 3), a.y - 7, random.random() < 0.3)
                if a.timer <= 0:
                    a.timer = max(25, 70 - 4 * lv)
                    if not s["chill"] and len(self.pops) < 14:
                        self.pops.append(PopBubble(a.x, a.y - 8, skull=True))
            elif a.tid == "skeleton":
                a.open = max(0.0, a.open - dt)
                if a.timer <= 0 and any(abs(f.x - a.x) < 12 for f in self.fish.values()):
                    a.timer = random.uniform(2, 5)
                    a.open = 0.6
            elif a.tid in ("geyser", "fountain", "waterfall"):
                if random.random() < dt * (6 if a.tid == "geyser" else 3):
                    self.add_decor_bubble(a.x + random.uniform(-3, 3), a.y - (6 if a.tid == "geyser" else 3))
                if a.tid == "geyser" and a.timer <= 0:
                    a.timer = max(25, 50 - 2 * lv)
                    if not s["chill"]:
                        self.spawn_pop(a.x, a.y - 8)

        # baby fry dart around, then grow up and swim off (fade)
        for f in list(self.fry):
            f[4] -= dt
            if random.random() < dt * 1.5:
                f[2] += random.uniform(-10, 10)
                f[3] += random.uniform(-6, 6)
            f[2] = max(-14, min(14, f[2]))
            f[3] = max(-6, min(6, f[3]))
            f[0] += f[2] * dt
            f[1] += f[3] * dt
            if f[0] < 4 or f[0] > self.w - 4:
                f[2] = -f[2]
            if f[1] < WATER_TOP + 3 or f[1] > self.sand_y - 2:
                f[3] = -f[3]
            f[0] = min(self.w - 4, max(4, f[0]))
            f[1] = min(self.sand_y - 2, max(WATER_TOP + 3, f[1]))
            if f[4] <= 0:
                self.fry.remove(f)
        self.update_visitor(dt)
        for r in list(self.rings):
            r[2] += dt
            r[1] -= dt * 9
            if r[1] < WATER_TOP + 3:
                self.rings.remove(r)
        # particles
        for p in list(self.parts):
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.kind == "spark":
                p.vy += 30 * dt
            if p.life <= 0:
                self.parts.remove(p)
        for tx in list(self.texts):
            tx[4] -= dt
            tx[1] -= dt * 6
            if tx[4] <= 0:
                self.texts.remove(tx)

    # ------------------------------------------------------------ draw
    def draw(self):
        s = self.surface
        t = self.time
        self.refresh_layers(t)
        s.blit(self._back, (0, 0))
        if self.lanterns:
            self.draw_lanterns(s, t)
        for a in self.toys.values():
            if a.tid not in ("ball",):
                extra = a.open if a.tid in ("chest", "clam", "skeleton") else a.roll
                sprites.draw_toy(s, a.tid, a.x, a.y, t, extra)
        st = self.state
        if E.ulv(st, "jar"):
            cap = E.jar_cap(st)
            sprites.draw_jar(s, *self.jar_pos(), min(1.0, st["jar"] / cap) if cap > 0 else 0, t)
        if E.ulv(st, "hatchery"):
            eggs = [(CLUTCHES_BY_ID[e["c"]]["color"], e["left"] <= 0) for e in st["eggs"]]
            sprites.draw_nest(s, *self.nest_pos(), eggs, t)
        for fd in self.foods:
            c = fd.kind["color"]
            s.set_at((int(fd.x), int(fd.y)), c)
            if fd.kind["id"] not in ("flakes", "brine"):
                s.set_at((int(fd.x) + 1, int(fd.y)), dark(c, 0.75))
                if fd.kind["id"] in ("algae", "golden"):
                    s.set_at((int(fd.x), int(fd.y) - 1), light(c, 0.3))
        for a in sorted(self.fish.values(), key=lambda a: a.sp["size"][0], reverse=True):
            a.draw(s, t)
            if a.f["full"] < 25 and (int(t * 1.5 + a.phase) % 3 == 0):
                self.draw_thought(s, a)
        ball = self.toys.get("ball")
        if ball:
            sprites.draw_toy(s, "ball", ball.x, ball.y + 3, t)
        s.blit(self._front, (0, 0))
        spooky = self.haunted()
        for b in self.decor:
            x = int(b[0] + math.sin(b[3]) * 0.8)
            if b[4] == 2 or (b[4] and spooky):
                self.draw_mini_skull(s, x, int(b[1]))
            elif b[4]:
                pygame.draw.circle(s, (190, 230, 250), (x, int(b[1])), 1)
            else:
                s.set_at((x, int(b[1])), (190, 230, 250))
        for f in self.fry:
            if f[4] > 3 or int(t * 8) % 2:
                x, y = int(f[0]), int(f[1])
                d = 1 if f[2] >= 0 else -1
                s.set_at((x, y), f[5])
                s.set_at((x - d, y), dark(f[5], 0.8))
                s.set_at((x - 2 * d, y + (int(t * 10) % 2)), dark(f[5], 0.7))
                s.set_at((x + d, y), (30, 30, 40))
        for r in self.rings:
            w = 4 + min(6, int(r[2] * 2))
            pygame.draw.ellipse(s, (210, 240, 255), (int(r[0] - w / 2), int(r[1]), w, 3), 1)
        for p in self.pops:
            self.draw_pop(s, p, t)
        if self.ghost:
            self.draw_ghost(s, t)
        for p in self.parts:
            k = p.life / p.max
            if p.kind == "heart":
                x, y = int(p.x), int(p.y)
                c = lerp((120, 160, 190), p.col, min(1, k * 2))
                for dx, dy in ((0, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (1, 3)):
                    s.set_at((x + dx - 1, y + dy), c)
            else:
                s.set_at((int(p.x), int(p.y)), p.col)
        v = self.visitor
        if v:
            sprites.draw_visitor(s, v["v"]["id"], v["x"], v["y"], v["right"], t)
            if int(t * 2) % 2:
                s.set_at((int(v["x"]), int(v["y"]) - 9), (255, 240, 140))
        for a in self.fish.values():
            if a.f.get("shiny") and int(t * 3 + a.phase) % 2 == 0:
                L = a.sp["size"][0]
                ang = t * 3 + a.phase
                s.set_at((int(a.x + math.cos(ang) * L / 2), int(a.y - 3 + math.sin(ang * 1.7) * 2)), (255, 255, 230))
        for a in self.fish.values():
            if a.levelfx > 0:
                for i in range(4):
                    ang = t * 5 + i * 1.57
                    s.set_at((int(a.x + math.cos(ang) * 7), int(a.y + math.sin(ang) * 4)), (255, 240, 120))
        tint = self.tint_surface()
        if tint:
            s.blit(tint, (1, WATER_TOP))
        self.apply_brightness(s)
        if self.state["settings"].get("nametags", True):
            for a in self.fish.values():
                if a.f.get("named"):
                    tag = sprites.name_tag(a.f["name"])
                    H = a.sp["size"][1]
                    x = int(min(self.w - tag.get_width() - 2, max(2, a.x - tag.get_width() / 2)))
                    y = int(max(WATER_TOP + 1, a.y - H / 2 - tag.get_height() - (4 if a.inverted else 6)))
                    s.blit(tag, (x, y))
        s.set_clip(None)
        return s

    LAYER_EVERY = 0.1        # plants sway slowly: redraw them 10x a second, not every frame

    def refresh_layers(self, t):
        """background + back plants + surface ripples, and the front plants, cached between redraws"""
        if (getattr(self, "_back", None) is not None and self._back.get_size() == self.static.get_size()
                and self._layer_src is self.static
                and 0 <= t - self._layer_t < self.LAYER_EVERY * (4 if self.state["settings"].get("power") == "saver" else 1)):
            return
        self._layer_t = t
        self._layer_src = self.static
        back = self.static.copy()
        for x in range(2, self.w - 2):
            back.set_at((x, WATER_TOP), (170, 220, 240) if int(x * 0.5 + t * 6) % 7 == 0 else (110, 190, 220))
        front = pygame.Surface(self.static.get_size(), pygame.SRCALPHA)
        for p in self.plants:
            self.draw_plant(back if p.get("back") else front, p, t)
        self._back, self._front = back, front

    def draw_plant(self, s, p, t):
        segs = max(3, int(p["h"] / 3))
        x, y = p["x"], self.sand_y + 1
        col = p["col"]
        for k in range(segs):
            sway = math.sin(t * 0.9 + p["phase"] + k * 0.35) * (k / segs) * 1.6
            nx = p["x"] + sway * (k / 2)
            ny = y - 3
            pygame.draw.line(s, col if k % 2 else dark(col, 0.85), (int(x), int(y)), (int(nx), int(ny)))
            if p["leaf"] and k % 3 == 1:
                s.set_at((int(nx) + (1 if k % 2 else -1), int(ny)), light(col, 0.2))
            x, y = nx, ny

    SKULL = [" XXX ", "XXXXX", "X.X.X", "XXXXX", " X X "]

    MINI_SKULL = [" XXX ", "X.X.X", " XXX ", " X X "]

    def draw_mini_skull(self, s, x, y):
        for j, row in enumerate(self.MINI_SKULL):
            for i, ch in enumerate(row):
                if ch != " ":
                    s.set_at((x - 2 + i, y - 1 + j), (235, 232, 240) if ch == "X" else (50, 30, 70))

    def draw_skull(self, s, x, y, col, eye):
        for j, row in enumerate(self.SKULL):
            for i, ch in enumerate(row):
                if ch == "X":
                    s.set_at((x - 2 + i, y - 2 + j), col)
                elif ch == ".":
                    s.set_at((x - 2 + i, y - 2 + j), eye)

    def draw_ghost(self, s, t):
        x0, y0, d, life = self.ghost
        y0 += math.sin(life * 2) * 2
        surf = pygame.Surface((9, 10), pygame.SRCALPHA)
        body = (240, 240, 255, 150)
        pygame.draw.circle(surf, body, (4, 4), 4)
        pygame.draw.rect(surf, body, (0, 4, 9, 4))
        for i in range(0, 9, 2):
            surf.set_at((i, 8 + (i // 2 + int(t * 4)) % 2), body)
        surf.set_at((3 if d > 0 else 2, 3), (40, 30, 60, 220))
        surf.set_at((6 if d > 0 else 5, 3), (40, 30, 60, 220))
        s.blit(surf, (int(x0) - 4, int(y0) - 5))

    def draw_pop(self, s, p, t):
        x, y = int(p.x), int(p.y)
        if p.skull or (self.haunted() and not p.golden):
            ring = (255, 160, 60) if p.skull else (200, 170, 240)
            pygame.draw.circle(s, ring, (x, y), p.r + 1, 1)
            self.draw_skull(s, x, y, (240, 238, 245), (230, 110, 20) if p.skull else (70, 30, 90))
            if p.surface_t > 5 and int(t * 8) % 2:
                s.set_at((x, y - p.r - 2), (255, 255, 255))
            return
        if p.golden:
            ring = lerp((250, 200, 60), (255, 245, 180), 0.5 + 0.5 * math.sin(t * 6))
            pygame.draw.circle(s, (120, 150, 140), (x, y), p.r)
            pygame.draw.circle(s, ring, (x, y), p.r, 1)
            s.set_at((x - 1, y - 1), (255, 255, 230))
            s.set_at((x, y), (255, 220, 90))
        else:
            pygame.draw.circle(s, (210, 240, 255), (x, y), p.r, 1)
            s.set_at((x - 1, y - 1), (255, 255, 255))
            s.set_at((x - 2, y), (255, 255, 255))
        if p.surface_t > 5 and int(t * 8) % 2:
            s.set_at((x, y - p.r - 1), (255, 255, 255))

    def draw_thought(self, s, a):
        x, y = int(a.x), int(a.y - a.sp["size"][1] / 2 - 7)
        y = max(WATER_TOP + 2, y)
        pygame.draw.rect(s, (245, 245, 250), (x - 3, y - 2, 7, 5))
        s.set_at((x - 1, y + 3), (245, 245, 250))
        s.set_at((x - 2, y + 4), (245, 245, 250))
        s.set_at((x, y), (230, 160, 70))
        s.set_at((x + 1, y), (200, 120, 50))
        s.set_at((x - 1, y - 1), (230, 160, 70))
