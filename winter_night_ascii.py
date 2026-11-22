#!/usr/bin/env python3
"""Winter Night - fine ASCII pixel scene for the terminal.

    python winter_night_ascii.py                play it (Ctrl-C to stop)
    python winter_night_ascii.py --seconds 10
    python winter_night_ascii.py --once         one frame
    python winter_night_ascii.py --cols 180 --rows 46 --fps 20

One character per pixel, picked from a fine brightness ramp, so the picture is
made of many small glyphs instead of solid blocks. The grid fills the window,
which keeps the glyphs small.

No trailing newline and one column less than the window width: the console
never scrolls, so the image does not shake.

Layers: sky wash, star field, moon, red planet, big blue planet, horizon haze,
blue grid skyline with lit windows and reflections, three bands of snow field
with sparks and footprints, firework afterglow and shells, falling snow, tree
with gold baubles and a red ribbon, star topper, striped gifts whose lids
bounce, near snow.
"""

import argparse
import math
import os
import random
import shutil
import sys
import time

RESET = "\x1b[0m"
HOME = "\x1b[H"
CLEAR = "\x1b[2J"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
ERASE = "\x1b[K"
FG = [f"\x1b[38;5;{i}m" for i in range(256)]


def _truecolour_table():
    """xterm-256 index -> exact 24-bit foreground sequence.

    cmd.exe only has 16 base colours, so 256-colour codes get approximated to
    the nearest of those (blues turn green, gold turns orange). Real 24-bit
    colour avoids that and keeps the palette the way it was designed.
    """
    levels = (0, 95, 135, 175, 215, 255)
    table = []
    for i in range(256):
        if 16 <= i <= 231:
            n = i - 16
            r, g, b = levels[n // 36], levels[(n % 36) // 6], levels[n % 6]
        elif i >= 232:
            r = g = b = 8 + (i - 232) * 10
        else:
            base = ((0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0), (0, 0, 128),
                    (128, 0, 128), (0, 128, 128), (192, 192, 192), (128, 128, 128),
                    (255, 0, 0), (0, 255, 0), (255, 255, 0), (0, 0, 255),
                    (255, 0, 255), (0, 255, 255), (255, 255, 255))
            r, g, b = base[i]
        table.append(f"\x1b[38;2;{r};{g};{b}m")
    return table


FG24 = _truecolour_table()

RAMP = " .`'^\",:;-~+=ilrczxo*#%@"          # dark -> bright, fine grain

BLACK = 16
SKY_BAND = (16, 16, 17, 17, 18, 18, 19)
DARK_BLUE = (17, 18, 19)
CITY_BODY = (19, 19, 24, 24)
CITY_LINE = (26, 32, 33, 39)
CITY_LIT = (33, 39, 45, 51, 75)
SNOW_FIELD = (18, 19, 25, 25, 26)
SNOW_SPARK = (26, 33, 39, 45, 51, 75, 153)
GREEN_DARK = (22, 28)
GREEN_MID = (34, 40)
GOLD = (178, 184, 220, 226, 227)
RED = (124, 160, 196, 203)
WHITE = (231, 252, 255)
ICE = (153, 189, 195, 231)
PLANET_RED = (124, 125, 131, 160, 167, 196, 203, 210)
PLANET_BLUE = (18, 19, 25, 26, 33, 39, 45, 51, 75)
BROWN = (58, 94, 130)

# xterm-256 index -> perceived brightness, for choosing the glyph
_LEVELS = (0, 95, 135, 175, 215, 255)
BRIGHT = [0] * 256
for _i in range(256):
    if 16 <= _i <= 231:
        _n = _i - 16
        _r, _g, _b = _LEVELS[_n // 36], _LEVELS[(_n % 36) // 6], _LEVELS[_n % 6]
    elif _i >= 232:
        _r = _g = _b = 8 + (_i - 232) * 10
    else:
        _r = _g = _b = 0
    BRIGHT[_i] = int(0.299 * _r + 0.587 * _g + 0.114 * _b)


class Scene:
    def __init__(self, cols, rows, seed=5):
        self.cols, self.rows = cols, rows
        self.W, self.H = cols, rows
        self.rng = random.Random(seed)
        self.horizon = int(self.H * 0.64)
        self.base = [BLACK] * (self.W * self.H)
        self.energy = [0.0] * (self.W * self.H)
        self.ecolour = [0] * (self.W * self.H)
        self.over = {}                                # index -> forced glyph
        self.build_sky()
        self.build_stars()
        self.build_planets()
        self.build_pines()
        self.build_field()
        self.build_tree()
        self.build_gifts()
        self.build_snow()
        self.rockets, self.bursts, self.smoke = [], [], []
        self.fire_timer = 0.0
        self.shoot = None
        self.shoot_timer = self.rng.uniform(3.5, 7.0)
        self._now = 0.0
        for _ in range(2):
            self.launch()

    def pick(self, seq):
        return seq[self.rng.randrange(len(seq))]

    def put(self, x, y, colour):
        if 0 <= x < self.W and 0 <= y < self.H:
            self.base[y * self.W + x] = colour

    # ---- static layers ----

    def build_sky(self):
        for y in range(self.horizon):
            band = min(int(y / max(1, self.horizon) * len(SKY_BAND)), len(SKY_BAND) - 1)
            row = y * self.W
            for x in range(self.W):
                self.base[row + x] = SKY_BAND[band]

    def build_stars(self):
        rng = self.rng
        self.stars = []
        for _ in range(int(self.W * self.H * 0.004)):
            x, y = rng.randrange(self.W), rng.randrange(max(1, int(self.horizon * 0.95)))
            colour = self.pick((231, 252, 255, 153, 195))
            self.stars.append([x, y, rng.uniform(0, 6.283), rng.uniform(1.2, 3.4), colour])
            self.put(x, y, colour)

    def disc(self, cx, cy, r, palette, texture=0.10, edge=None, light=(-0.6, -0.7), rings=0):
        """Smooth shaded ball: bright toward the light, dark terminator, few craters."""
        rng = self.rng
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                d = math.hypot(dx, dy * 1.9)
                if d > r:
                    continue
                nx, ny = dx / max(r, 1), (dy * 1.9) / max(r, 1)
                lum = 0.55 - 0.45 * (nx * light[0] + ny * light[1])
                idx = min(len(palette) - 1, max(0, int(lum * len(palette))))
                self.put(cx + dx, cy + dy, palette[idx])
                if rng.random() < 0.06:
                    self.put(cx + dx, cy + dy, self.pick(palette))
                if edge and d > r - 0.9:
                    self.put(cx + dx, cy + dy, edge)

    def build_planets(self):
        # warm planet, big blue planet, small moon: shaded, low-contrast glyphs
        self.disc(int(self.W * 0.115), int(self.H * 0.29), int(self.H * 0.115),
                  (124, 124, 131, 160, 160, 167, 174), edge=124)
        self.disc(int(self.W * 0.875), int(self.H * 0.25), int(self.H * 0.15),
                  (19, 19, 25, 25, 25, 26, 32), edge=25)
        self.disc(int(self.W * 0.205), int(self.H * 0.075), max(3, int(self.H * 0.05)),
                  (189, 195, 231, 252), edge=195)

    def build_pines(self):
        """Distant pine forest instead of a city: same blue palette, no lights.

        Each pine keeps its own cells and reveal delay so the intro can grow
        them out of the snow one after another.
        """
        rng = self.rng
        self.windows = []
        self.pines = []
        x = -3
        while x < self.W + 3:
            w = rng.randint(4, max(5, int(self.W * 0.030)))
            h = rng.randint(max(4, int(self.horizon * 0.10)), max(5, int(self.horizon * 0.34)))
            base_y = self.horizon + rng.randint(0, 1)
            far = rng.random() < 0.4
            body = self.pick((19, 19, 24, 24)) if not far else self.pick((18, 19))
            line = self.pick((26, 32, 33)) if not far else self.pick((25, 26))
            lit = self.pick((39, 45, 51)) if not far else self.pick((26, 32))
            mid = x + w // 2
            cells = []
            for i in range(h):
                y = base_y - h + i
                if not 0 <= y < self.horizon:
                    continue
                half = max(0, int(round((i / max(1, h - 1)) ** 0.9 * (w / 2.0))))
                for dx in range(-half, half + 1):
                    xx = mid + dx
                    if not 0 <= xx < self.W:
                        continue
                    if abs(dx) == half:
                        colour = line
                    elif abs(dx) == max(0, half - 1) and rng.random() < 0.25:
                        colour = lit
                    else:
                        colour = body
                    cells.append((xx, y, colour, base_y - y, abs(dx), half))
            if 0 <= base_y < self.H - 1:
                cells.append((mid, base_y - h, line, h, 0, 0))
                for dx in (-1, 0, 1):
                    cells.append((mid + dx, base_y, self.pick((24, 19)), 0, abs(dx), 1))
            self.pines.append({"cells": cells, "base": base_y, "h": max(1, h),
                               "delay": 0.0, "dur": rng.uniform(0.75, 1.15)})
            x += w + rng.randint(0, 3)

        # stagger the intro from the outside in, so the forest spreads
        n = max(1, len(self.pines))
        for i, pine in enumerate(self.pines):
            share = abs(i / max(1, n - 1) - 0.5) * 2          # 0 centre, 1 edges
            pine["delay"] = 0.30 + (1 - share) * 0.9 + rng.uniform(0, 0.45)

    def build_field(self):
        rng = self.rng
        rows = self.H - self.horizon
        self.sparks = []
        for y in range(self.horizon, self.H):
            depth = (y - self.horizon) / max(1, rows - 1)
            row = y * self.W
            for x in range(self.W):
                r = rng.random()
                if r < 0.55:
                    self.base[row + x] = self.pick(SNOW_FIELD)
                elif r < 0.68:
                    self.base[row + x] = self.pick(DARK_BLUE)
                if rng.random() < 0.10 + 0.06 * depth:
                    colour = self.pick(SNOW_SPARK)
                    self.base[row + x] = colour
                    if rng.random() < 0.4:
                        self.sparks.append((x, y, rng.uniform(0, 6.283), colour))
        for x, y, phase in self.windows:
            for k in range(1, 4):
                if y + k < self.horizon + 4:
                    self.put(x, self.horizon + k, self.pick((19, 25, 26)))
        # haze band right on the horizon
        for x in range(self.W):
            if rng.random() < 0.55:
                self.put(x, self.horizon - 1, self.pick((25, 25, 26)))
                if rng.random() < 0.4:
                    self.put(x, self.horizon - 2, self.pick((24, 19)))
        self.footprints = []
        fx, fy = 3, self.H - 2
        while fy > self.horizon + 2 and fx < self.W * 0.38:
            self.footprints.append((fx, fy))
            self.put(fx, fy, self.pick((25, 33)))
            fx += 4 if fy % 2 else 3
            fy -= 1

    def build_tree(self):
        rng = self.rng
        self.cx = self.W // 2
        self.top = int(self.H * 0.12)
        self.base_y = int(self.H * 0.74)
        self.half = max(6, int(self.W * 0.14))
        height = max(8, self.base_y - self.top)
        self.tree_top, self.tree_height = self.top, height
        self.lights, self.garland, self.baubles = [], [], []
        self.tree_cells = []
        for r in range(height):
            y = self.top + r
            f = r / max(1, height - 1)
            hw = int(round(self.half * f ** 0.72))
            if r % 6 == 5:
                hw += 1
            band = (r // 6) % 2 == 0
            for dx in range(-hw, hw + 1):
                x = self.cx + dx
                if not 0 <= x < self.W:
                    continue
                if abs(dx) >= hw - 1:
                    colour = self.pick(GREEN_DARK)
                elif band:
                    colour = self.pick((34, 40, 40))
                else:
                    colour = self.pick((28, 34))
                self.tree_cells.append((x, y, colour))
                rr = rng.random()
                if dx and rr < 0.045:
                    self.lights.append((x, y, rng.uniform(0, 6.283)))
                elif rr < 0.07:
                    self.baubles.append((x, y, rng.uniform(0, 6.283),
                                         self.pick(GOLD) if rng.random() < 0.65 else self.pick(RED)))
            if hw > 2:
                gx = self.cx + int(round(hw * 0.55 * math.sin(r * 0.5)))
                self.garland.append((gx, y, rng.uniform(0, 6.283)))
                self.tree_cells.append((gx, y, self.pick(RED)))
                if gx + 1 < self.cx + hw:
                    self.tree_cells.append((gx + 1, y, self.pick((160, 196))))
            if r % 9 == 4 and hw > 1:                 # snow caught on the branches
                for dx in (-hw, hw, -hw + 1, hw - 1):
                    if rng.random() < 0.55:
                        self.tree_cells.append((self.cx + dx, y, self.pick((189, 195, 231))))
        self.trunk_cells = [(self.cx + dx, self.base_y + r, self.pick(BROWN))
                            for r in range(max(2, height // 12)) for dx in (-1, 0, 1)]
        sy = self.top - 1
        self.star_cells = [(self.cx + dx, sy + dy, self.pick(GOLD))
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1)]

    def build_gifts(self):
        rng = self.rng
        self.gifts = []
        specs = [(-1.85, 160, 220), (-1.15, 196, 184), (1.15, 160, 220), (1.85, 203, 220)]
        bw = max(4, int(self.half * 0.42))
        bh = max(2, int(bw * 0.75))
        for off, body, stripe in specs:
            gx = self.cx + int(off * self.half) - bw // 2
            gy = self.base_y + 2 + (1 if abs(off) > 1.5 else 0)
            self.gifts.append([gx, gy, bw, bh, body, stripe, rng.uniform(0, 6.283)])

    def build_snow(self):
        rng = self.rng
        self.snow = []
        for _ in range(int(self.W * self.H * 0.007)):
            self.snow.append([rng.uniform(0, self.W), rng.uniform(0, self.H),
                              rng.uniform(1.5, 5.0), rng.random() * 6.283])

    # ---- fireworks ----

    def launch(self):
        rng = self.rng
        left = self.cx - self.half - 4
        right = self.cx + self.half + 4
        if left > 10 and (rng.random() < 0.5 or right >= self.W - 10):
            x = rng.randint(3, left)
        elif right < self.W - 10:
            x = rng.randint(right, self.W - 4)
        else:
            x = rng.randint(3, self.W - 4)
        self.rockets.append({
            "x": float(x), "y": float(self.horizon - 1),
            "vy": -rng.uniform(self.H * 0.22, self.H * 0.38),
            "target": rng.uniform(self.H * 0.18, self.H * 0.42),
            "colour": self.pick((196, 203, 220, 226, 51, 45, 207, 231, 208, 201, 82, 118, 213)),
            "colour2": self.pick((196, 203, 220, 226, 51, 45, 207, 231, 208, 201, 82, 118, 213)),
            "shape": rng.choice(("peony", "peony", "ring", "willow", "palm", "crackle")),
            "trail": [],
        })

    def explode(self, r):
        rng = self.rng
        shape = r["shape"]
        rmax = {"palm": rng.uniform(0.34, 0.46), "ring": rng.uniform(0.26, 0.30),
                "willow": rng.uniform(0.26, 0.42)}.get(shape, rng.uniform(0.22, 0.40)) * self.H
        rmax = min(rmax, max(8.0, min(r["x"], self.W - r["x"]) * 0.95),
                   max(8.0, r["y"] * 0.95), max(8.0, (self.horizon - r["y"]) * 0.98))
        self.bursts.append({
            "x": r["x"], "y": r["y"], "age": 0.0,
            "life": {"willow": rng.uniform(2.3, 3.0), "palm": rng.uniform(1.9, 2.4)}.get(
                shape, rng.uniform(1.6, 2.2)),
            "rmax": rmax, "c1": r["colour"], "c2": r["colour2"], "shape": shape,
            "phase": rng.uniform(0, 6.283), "seed": rng.randint(0, 9999),
            "droop": {"willow": 0.10, "palm": 0.06}.get(shape, 0.04),
            "drips": [[rng.uniform(0, 6.283), rng.uniform(0.6, 1.0), rng.uniform(0, 6.283)]
                      for _ in range(rng.randint(8, 14))],
            "crackle": shape == "crackle",
        })
        for _ in range(4):
            self.smoke.append([r["x"] + rng.uniform(-3, 3), r["y"] + rng.uniform(-1, 1), 0.0])

    def update(self, dt):
        rng = self.rng
        self._now += dt
        decay = dt * 1.15
        for i, e in enumerate(self.energy):
            if e > 0.0:
                self.energy[i] = max(0.0, e - decay)
        self.fire_timer -= dt
        if self.intro_done() and self.fire_timer <= 0 and len(self.bursts) < 7:
            self.fire_timer = rng.uniform(0.22, 0.5)
            self.launch()
        for r in list(self.rockets):
            r["y"] += r["vy"] * dt
            r["vy"] += self.H * 0.08 * dt
            r["trail"].append((r["x"], r["y"]))
            if len(r["trail"]) > 12:
                r["trail"].pop(0)
            if r["y"] <= r["target"]:
                self.rockets.remove(r)
                self.explode(r)
        for b in list(self.bursts):
            b["age"] += dt
            if b["age"] > b["life"]:
                self.bursts.remove(b)
        for s in list(self.smoke):
            s[2] += dt
            if s[2] > 1.4:
                self.smoke.remove(s)
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = rng.uniform(7.0, 12.0)
            self.shoot = {"x": rng.uniform(0, self.W * 0.6), "y": rng.uniform(0, self.horizon * 0.35),
                          "vx": rng.uniform(self.W * 0.35, self.W * 0.6),
                          "vy": rng.uniform(1.0, 2.5), "age": 0.0}
        if self.shoot:
            self.shoot["age"] += dt
            if self.shoot["age"] > 0.8:
                self.shoot = None
        for flake in self.snow:
            flake[1] += flake[2] * dt * 6
            flake[0] += math.sin(flake[1] * 0.08 + flake[3]) * dt * 1.6
            if flake[1] > self.H:
                flake[1] = -1
                flake[0] = rng.uniform(0, self.W)

    # ---- intro timeline ----

    T_PINES = 0.25          # forest starts rising
    T_TREE = 2.30           # main tree starts growing
    T_TREE_DUR = 1.90
    T_GIFTS = 4.55          # presents pop out of the snow

    @staticmethod
    def _ease(p):
        p = max(0.0, min(1.0, p))
        return 1 - (1 - p) ** 2.2

    @staticmethod
    def _pop(p):
        """Ease-out with a small overshoot, for popping out of the ground."""
        p = max(0.0, min(1.0, p))
        return 1 + 2.7 * (p - 1) ** 3 + 1.7 * (p - 1) ** 2

    def tree_progress(self, t):
        return self._ease((t - self.T_TREE) / self.T_TREE_DUR)

    def gift_progress(self, t, i):
        return self._pop((t - (self.T_GIFTS + i * 0.17)) / 0.62)

    def intro_done(self, t=None):
        return (t if t is not None else self._now) > self.T_GIFTS + 1.6

    # ---- frame ----

    def light(self, x, y, energy, colour):
        if 0 <= x < self.W and 0 <= y < self.H:
            i = y * self.W + x
            if self.energy[i] < energy:
                self.energy[i] = energy
                self.ecolour[i] = colour

    def frame(self, t):
        grid = self.base[:]
        self.over = {}
        W, H = self.W, self.H

        def put(x, y, colour):
            if 0 <= x < W and 0 <= y < H:
                grid[y * W + x] = colour

        for x, y, phase, speed, colour in self.stars:
            if math.sin(t * speed + phase) < -0.45:
                put(x, y, 17)

        for x, y, phase in self.windows:
            if math.sin(t * 1.7 + phase) > 0.25:
                put(x, y, 51)

        for x, y, phase, colour in self.sparks:
            if math.sin(t * 2.4 + phase) > 0.1:
                put(x, y, 75 if colour > 45 else 45)

        # ---- intro: the forest rises out of the snow ----
        for pine in self.pines:
            p = self._ease((t - pine["delay"]) / pine["dur"])
            if p <= 0:
                continue
            reach = p * pine["h"]
            for x, y, colour, dist, ahalf, rowhalf in pine["cells"]:
                if dist <= reach and ahalf <= p * rowhalf + 0.5:
                    put(x, y, colour)

        # ---- intro: the tree grows from the trunk to the tip ----
        tree_p = self.tree_progress(t)
        cutoff = self.base_y - tree_p * self.tree_height
        if tree_p > 0:
            for x, y, colour in self.tree_cells:
                if y >= cutoff:
                    put(x, y, colour)
            for x, y, trunk_colour in self.trunk_cells:
                put(x, y, trunk_colour)
            for x, y, phase in self.lights:
                if y >= cutoff and math.sin(t * 3.4 + phase) > -0.2:
                    put(x, y, 231 if math.sin(t * 1.7 + phase) > 0 else 226)
            for x, y, phase in self.garland:
                if y >= cutoff:
                    put(x, y, 203 if math.sin(t * 2.2 + phase) > 0 else 160)
            for x, y, phase, colour in self.baubles:
                if y >= cutoff and math.sin(t * 2.6 + phase) > -0.6:
                    put(x, y, colour)

        # star topper, once the tip is up
        star_p = max(0.0, min(1.0, (tree_p - 0.86) / 0.14))
        if star_p > 0:
            for x, y, colour in self.star_cells:
                if (x + y) % 2 == 0 or star_p > 0.5:
                    put(x, y, colour if star_p > 0.4 else 226)

        for i, e in enumerate(self.energy):
            if e > 0.08:
                grid[i] = self.ecolour[i] if e > 0.22 else 25
                self.over[i] = "*" if e > 0.6 else "+" if e > 0.34 else "."

        for r in self.rockets:
            x, y = int(r["x"]), int(r["y"])
            put(x, y, 255)
            put(x, y - 1, r["colour"])
            for i, (tx, ty) in enumerate(r["trail"][-5:]):
                put(int(tx), int(ty), 178 if i < 2 else 130)

        for b in self.bursts:
            age, life = b["age"], b["life"]
            p = age / life
            if p > 1:
                continue
            bright = (1 - p) ** 0.7
            radius = b["rmax"] * (1 - (1 - p) ** 2.0)
            n = max(40, int(6.2832 * max(radius, 2.0) / 1.15))
            if b["shape"] == "ring":
                squish, wobble = 0.66, 0.03
            elif b["shape"] == "palm":
                squish, wobble = 0.70, 0.05
            else:
                squish, wobble = 0.62, 0.07
            for i in range(n):
                a = 6.2832 * i / n + b["phase"]
                r = radius * (1.0 + wobble * math.sin(a * 5 + b["phase"] + p * 3))
                if b["shape"] == "palm" and i % 3:
                    continue
                if b["shape"] == "crackle" and p > 0.5 and (i + b["seed"]) % 3:
                    continue
                x = int(b["x"] + math.cos(a) * r)
                y = int(b["y"] + math.sin(a) * r * squish + b["droop"] * H * p * p)
                colour = b["c1"] if i % 10 < 6 else b["c2"]
                e = bright * (0.88 + 0.12 * math.sin(a * 4 + p * 9))
                self.light(x, y, e, colour)
                if e > 0.55:                       # glow around the bright grains
                    self.light(x + 1, y, e * 0.6, colour)
                    self.light(x, y + 1, e * 0.6, colour)
                elif e > 0.3:
                    self.light(x + 1, y, e * 0.42, colour)
            # hot core just after ignition
            if p < 0.35:
                cx, cy = int(b["x"]), int(b["y"])
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        self.light(cx + dx, cy + dy, (0.35 - p) * 2.4, 231)
            if p > 0.2:
                for a, spd, tw in b["drips"]:
                    r = radius * spd
                    x = int(b["x"] + math.cos(a) * r)
                    y = int(b["y"] + math.sin(a) * r * 0.62 + b["droop"] * H * p * p * 1.5)
                    if math.sin(age * 4 + tw) > -0.3:
                        self.light(x, y, bright * 0.5, b["c2"])

        for x, y, age in self.smoke:
            if 1 - age / 1.4 > 0.4:
                put(int(x), int(y), 236)

        if self.shoot:
            a = self.shoot["age"]
            for k in range(10):
                aa = a - k * 0.014
                if aa < 0:
                    break
                put(int(self.shoot["x"] + self.shoot["vx"] * aa),
                    int(self.shoot["y"] + self.shoot["vy"] * aa),
                    231 if k < 3 else 153)

        for x, y, speed, phase in self.snow:
            xi, yi = int(x), int(y)
            if 0 <= xi < W and 0 <= yi < H:
                i = yi * W + xi
                grid[i] = self.pick((252, 195, 189, 255, 153))
                self.over[i] = "." if (xi + yi) % 3 else "'"

        # warm light from the tree and the fireworks spilling onto the snow
        if self.tree_progress(t) > 0.6:
            for gy in range(self.base_y + 1, H):
                drop = 1.0 - (gy - self.base_y) / max(4.0, (H - self.base_y) * 1.6)
                if drop <= 0:
                    break
                for dx in range(-self.half, self.half + 1):
                    x = self.cx + dx
                    if 0 <= x < W and (x + gy) % 3 == 0 and drop > 0.35:
                        put(x, gy, 22 if (x + gy) % 2 else 28)
        glow_rows = 0
        for i, e in enumerate(self.energy):
            if e < 0.45:
                continue
            x, y = i % W, i // W
            if y >= self.horizon - 2:
                continue
            for k, fade in ((1, 0.34), (2, 0.2), (3, 0.1)):
                ty = y + k + (self.horizon - y) // 3
                if ty < H and (e * fade) > 0.2:
                    if 0 <= x < W:
                        put(x, ty, self.ecolour[i] if fade > 0.25 else 25)
            glow_rows += 1
            if glow_rows > 400:
                break

        # gifts: they spring out of the snow, then only the lid bounces
        for gi, (gx, gy, bw, bh, body, stripe, phase) in enumerate(self.gifts):
            rise = self.gift_progress(t, gi)
            if rise <= 0:
                continue
            shift = int(round((1.0 - rise) * (bh + 2)))
            settled = rise >= 0.999
            for x in range(gx, gx + bw):
                if not 0 <= x < W:
                    continue
                for y in range(gy - bh, gy):
                    yy = y + shift
                    if 0 <= yy < H and yy <= gy:
                        grid[yy * W + x] = body if (x - gx) % 4 in (0, 1) else stripe
                if settled and 0 <= gy < H:
                    grid[gy * W + x] = 235
            if settled:
                for x in range(gx, gx + bw):
                    if 0 <= x < W and 0 <= gy + 1 < H:
                        grid[(gy + 1) * W + x] = 236
            lid_y = gy - bh - (1 if (settled and math.sin(t * 1.6 + phase) > 0.5) else 0) + shift
            for x in range(gx - 1, gx + bw + 1):
                if 0 <= x < W and 0 <= lid_y < H and lid_y <= gy:
                    grid[lid_y * W + x] = 226 if (x - gx) % 4 in (0, 1) else body
            if 0 <= lid_y - 1 < H and lid_y - 1 <= gy:      # lit top edge
                for x in range(gx, gx + bw):
                    if 0 <= x < W and grid[(lid_y - 1) * W + x] != BLACK:
                        grid[(lid_y - 1) * W + x] = body
            mid = gx + bw // 2
            for y in range(max(lid_y, 0), min(gy, H)):
                if 0 <= mid < W:
                    grid[y * W + mid] = 231
            if 0 <= lid_y - 1 < H and settled:
                put(mid, lid_y - 1, 220)
                put(mid - 1, lid_y - 1, 220 if bw > 4 else 226)
                put(mid + 1, lid_y - 1, 220 if bw > 4 else 226)

        return grid

    def to_text(self, t, truecolour=True):
        grid = self.frame(t)
        W = self.W
        ramp = RAMP.encode()
        fg = FG24 if truecolour else FG
        lines = []
        for y in range(self.H):
            base = y * W
            parts = []
            prev = -1
            for x in range(W):
                colour = grid[base + x]
                if colour == BLACK:
                    parts.append(" ")
                    prev = -1
                    continue
                if colour != prev:
                    parts.append(fg[colour])
                    prev = colour
                override = self.over.get(base + x)
                if override is not None:
                    parts.append(override)
                else:
                    char = chr(ramp[BRIGHT[colour] * (len(ramp) - 1) // 255])
                    parts.append(char if char != " " else ".")
            parts.append(RESET)
            lines.append("".join(parts) + ERASE)
        return HOME + "\n".join(lines)


def enable_console():
    if os.name == "nt":
        try:
            os.system("chcp 65001 > nul")
        except Exception:
            pass
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(mode)):
                k.SetConsoleMode(h, mode.value | 0x0004)
            k.SetConsoleTitleW("Winter Night")
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--seconds", type=float, default=0.0)
    ap.add_argument("--fps", type=float, default=20)
    ap.add_argument("--cols", type=int, default=0)
    ap.add_argument("--rows", type=int, default=0)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--time", type=float, default=6.0, help="scene time for --once")
    ap.add_argument("--no-truecolor", action="store_true",
                    help="use 256-colour codes instead of 24-bit colour")
    args = ap.parse_args()

    enable_console()
    size = shutil.get_terminal_size((150, 40))
    # one column short and one row short of the window: nothing ever wraps or
    # scrolls, which is what caused the whole screen to shake
    cols = args.cols or max(80, min(size.columns - 1, 190))
    rows = args.rows or max(20, min(size.lines - 2, 54))
    scene = Scene(cols, rows, args.seed)
    truecolour = not args.no_truecolor
    dt = 1.0 / args.fps

    if args.once:
        t = args.time
        for _ in range(int(t / dt)):
            scene.update(dt)
        sys.stdout.write(scene.to_text(t, truecolour))
        return

    t = 0.0
    frames = 0
    start = time.perf_counter()
    sys.stdout.write(CLEAR + HIDE)
    try:
        while True:
            sys.stdout.write(scene.to_text(t, truecolour))
            sys.stdout.flush()
            scene.update(dt)
            t += dt
            frames += 1
            if args.seconds and t >= args.seconds:
                break
            lag = start + (frames + 1) * dt - time.perf_counter()
            if lag > 0:
                time.sleep(lag)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + SHOW + "\n")


if __name__ == "__main__":
    main()
