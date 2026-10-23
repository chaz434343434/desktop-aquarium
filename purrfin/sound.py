"""Tiny synthesized sound effects (no numpy, no asset files)."""
import array
import math
import random
import threading

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


# ---------------------------------------------------------------- calm background sounds
AMB_RATE = 11025      # made at half rate (it's soft, low sound) and doubled up: half the work


def _water(seconds=14):
    """gentle brown-noise water with slow swells and the odd soft bubble; loops without a click"""
    r = random.Random(7)
    n = int(AMB_RATE * seconds)
    out = [0.0] * n
    v = 0.0
    for i in range(n):
        v = v * 0.996 + r.uniform(-1, 1) * 0.035
        swell = 0.6 + 0.4 * math.sin(2 * math.pi * i / n * 3)          # 3 slow swells per loop
        out[i] = v * swell * 0.9
    for _ in range(int(seconds * 1.6)):                                  # bubbles
        start, f0 = r.randrange(0, n - 600), r.uniform(500, 1100)
        ln = r.randint(250, 550)
        for j in range(ln):
            k = j / ln
            out[start + j] += math.sin(2 * math.pi * (f0 + 700 * k) * j / AMB_RATE) * (1 - k) ** 2 * 0.12
    fade = AMB_RATE                                                      # cross-fade the end into the start
    for j in range(fade):
        k = j / fade
        out[j] = out[j] * k + out[n - fade + j] * (1 - k)
    return out[:n - fade]


def _music(seconds=32):
    """slow, soft pentatonic tune over quiet chords"""
    r = random.Random(11)
    n = int(AMB_RATE * seconds)
    out = [0.0] * n
    scale = [261.6, 293.7, 329.6, 392.0, 440.0, 523.3, 587.3, 659.3]
    chords = [(130.8, 196.0), (110.0, 164.8), (146.8, 220.0), (98.0, 146.8)]
    beat = 60 / 64
    bar = int(AMB_RATE * beat * 4)

    def note(start, freq, length, vol):
        ln = min(int(length * AMB_RATE), n - start)
        w = 2 * math.pi * freq / AMB_RATE
        for j in range(ln):
            k = j / ln
            env = min(1.0, j / (AMB_RATE * 0.04)) * (1 - k) ** 1.6
            out[start + j] += (math.sin(w * j) + 0.25 * math.sin(2 * w * j)) * env * vol

    for b in range(n // bar):
        root, fifth = chords[b % len(chords)]
        note(b * bar, root, beat * 4.2, 0.10)
        note(b * bar, fifth, beat * 4.2, 0.07)
        for step in range(4):
            if r.random() < 0.7:
                note(b * bar + int(step * AMB_RATE * beat), r.choice(scale), beat * 1.8, 0.13)
    tail = AMB_RATE // 2                                                  # soft loop seam
    for j in range(tail):
        out[n - tail + j] *= 1 - j / tail
    return out


def _to_sound(samples, vol):
    buf = array.array("h")
    for v in samples:
        x = int(max(-1.0, min(1.0, v)) * 32767 * vol)
        buf.append(x)
        buf.append(x)                                                    # 11025 -> 22050
    return pygame.mixer.Sound(buffer=buf.tobytes())


class Ambience:
    """Options > Calm sounds: off / water / water + music. Made once in the background, then looped."""

    def __init__(self, sounds):
        self.sounds = sounds
        self.raw = {}               # name -> samples (made in a thread)
        self.snd = {}               # name -> pygame Sound (made on the main thread)
        self.busy = False
        self.playing = None
        self.ch = {}

    def wanted(self):
        st = self.sounds.settings
        if not self.sounds.ok or not st.get("sound", True):
            return "off"
        return st.get("ambience", "off")

    def _make(self, names):
        for name in names:
            if name not in self.raw:
                self.raw[name] = _water() if name == "water" else _music()
        self.busy = False

    def tick(self):
        """call every frame: starts, stops and re-volumes the loops to match the settings"""
        mode = self.wanted()
        need = [] if mode == "off" else (["water"] if mode == "water" else ["water", "music"])
        missing = [x for x in need if x not in self.raw]
        if missing:
            if not self.busy:
                self.busy = True
                threading.Thread(target=self._make, args=(missing,), daemon=True).start()
            return
        for name in need:
            if name not in self.snd:
                self.snd[name] = _to_sound(self.raw[name], 0.6 if name == "water" else 0.5)
        vol = self.sounds.settings.get("volume", 0.5)
        for name in ("water", "music"):
            ch = self.ch.get(name)
            if name in need:
                if ch is None or not ch.get_busy():
                    ch = self.snd[name].play(loops=-1)
                    self.ch[name] = ch
                if ch:
                    ch.set_volume(vol * (0.5 if name == "water" else 0.35))
            elif ch is not None:
                ch.stop()
                self.ch[name] = None
