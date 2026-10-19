"""Tiny synthesized sound effects (no numpy, no asset files)."""
import array
import math
import random

import pygame

RATE = 22050


def _tone(dur, fn, vol=0.5):
    n = int(RATE * dur)
    buf = array.array("h", (int(max(-1, min(1, fn(i / RATE, i / n))) * 32767 * vol) for i in range(n)))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _pop(t, k):
    f = 700 + 1300 * k
    return math.sin(2 * math.pi * f * t) * (1 - k) ** 3


def _plop(t, k):
    f = 380 - 220 * k
    return math.sin(2 * math.pi * f * t) * (1 - k) ** 2


_rng = random.Random(3)


def _purr(t, k):
    am = 0.5 + 0.5 * math.sin(2 * math.pi * 24 * t)
    env = math.sin(math.pi * k)
    return (_rng.uniform(-1, 1) * 0.5 + math.sin(2 * math.pi * 55 * t) * 0.5) * am * env


def _chime(t, k):
    f = 660 if k < 0.45 else 990
    return math.sin(2 * math.pi * f * t) * (1 - (k % 0.5) * 2) ** 2 * 0.8


def _level(t, k):
    notes = [523, 659, 784, 1046]
    f = notes[min(3, int(k * 4))]
    return math.sin(2 * math.pi * f * t) * (1 - (k * 4 % 1)) * 0.7


def _golden(t, k):
    return (math.sin(2 * math.pi * (900 + 900 * k) * t) * 0.5 + math.sin(2 * math.pi * 1800 * t) * 0.3) * (1 - k)


def _nope(t, k):
    return math.sin(2 * math.pi * 160 * t) * (1 - k) * 0.6


class Sounds:
    def __init__(self, settings):
        self.settings = settings
        self.ok = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            self.snd = dict(
                pop=_tone(0.07, _pop, 0.35), plop=_tone(0.1, _plop, 0.4), purr=_tone(0.6, _purr, 0.35),
                buy=_tone(0.3, _chime, 0.3), level=_tone(0.45, _level, 0.3), golden=_tone(0.25, _golden, 0.35),
                nope=_tone(0.12, _nope, 0.3), pet=_tone(0.05, lambda t, k: math.sin(2 * math.pi * (500 + 200 * k) * t) * (1 - k), 0.15),
            )
            self.ok = True
        except Exception:
            self.ok = False
        self.cool = {}

    def play(self, name, cooldown=0.0, now=0.0):
        if not self.ok or not self.settings.get("sound", True):
            return
        if cooldown and now - self.cool.get(name, -99) < cooldown:
            return
        self.cool[name] = now
        s = self.snd.get(name)
        if s:
            s.set_volume(self.settings.get("volume", 0.5))
            s.play()
