"""Procedural massage still life for Advanced Massage Therapy: bamboo massage sticks,
rolled towels and eucalyptus on a warm wooden table, against a deep charcoal-teal
wall lit by soft window light. Rendered as a large plate plus a foreground layer so
a virtual camera can push in, slide and rack focus.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PW, PH = 1700, 3000          # plate size (camera crops 9:16 windows out of it)
TABLE_Y = 1900               # where the wall meets the table top


def _noise(h, w, seed, scales, weights):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    for sc, wt in zip(scales, weights):
        small = rng.normal(0, 1, (max(2, h // sc[0]), max(2, w // sc[1]))).astype(np.float32)
        out += wt * np.asarray(Image.fromarray(small, "F").resize((w, h), Image.BICUBIC))
    return out / np.abs(out).max()


def _shadow(size, box, radius, blur, alpha):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius, fill=int(255 * alpha))
    return m.filter(ImageFilter.GaussianBlur(blur))


def bamboo_stick(length, radius, seed, tone=1.0):
    """Horizontal bamboo stick (RGBA), lit from above."""
    rng = np.random.default_rng(seed)
    L, R = int(length), int(radius)
    Hh = 2 * R + 8
    yy, xx = np.mgrid[0:Hh, 0:L].astype(np.float32)
    v = (yy - Hh / 2) / R                         # -1..1 across the stick
    inside = np.abs(v) <= 1
    nz = np.sqrt(np.clip(1 - v ** 2, 0, 1))      # surface normal z
    light = 0.38 + 0.62 * np.clip(nz * 0.8 - v * 0.45, 0, 1)
    base = np.array([184, 156, 104], np.float32) * tone * np.array([1.0, 1.0 + rng.uniform(-0.04, 0.05), 1.0])
    fib = _noise(Hh, L, seed, [(2, 40), (4, 120)], [1.0, 0.6])
    col = base[None, None, :] * (light + 0.13 * fib)[..., None]
    # specular streak
    spec = np.exp(-((v + 0.45) / 0.16) ** 2) * 0.22
    col += np.array([255, 240, 200], np.float32) * spec[..., None]
    # nodes
    n_nodes = rng.integers(2, 4)
    for k in range(n_nodes):
        nx = L * (k + 1) / (n_nodes + 1) + rng.uniform(-L * 0.06, L * 0.06)
        d = (xx - nx)
        ring = np.exp(-(d / 3.0) ** 2)
        ridge = np.exp(-((d - 5) / 4.0) ** 2) * 0.5
        col = col * (1 - 0.45 * ring[..., None]) + np.array([255, 236, 190], np.float32) * (ridge * light * 0.35)[..., None]
    # slightly darker, rounded ends
    endfade = np.clip(np.minimum(xx, L - 1 - xx) / 6.0, 0, 1)
    a = (inside * endfade).astype(np.float32)
    rgba = np.concatenate([np.clip(col, 0, 255), (a * 255)[..., None]], -1).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    d = ImageDraw.Draw(im)  # cut face at the right end
    d.ellipse((L - 9, Hh / 2 - R, L + 3, Hh / 2 + R), fill=(150, 116, 66, 255))
    d.ellipse((L - 7, Hh / 2 - R * 0.62, L + 1, Hh / 2 + R * 0.62), fill=(214, 186, 132, 255))
    return im


def towel_roll(diam, seed, color=(246, 242, 234)):
    """Rolled towel seen end-on: spiral with terry texture and soft shading."""
    rng = np.random.default_rng(seed)
    D = int(diam)
    yy, xx = np.mgrid[0:D, 0:D].astype(np.float32)
    c = D / 2
    r = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / c
    th = np.arctan2(yy - c, xx - c)
    turns = rng.uniform(3.2, 4.2)
    spiral = np.mod(r * turns - th / (2 * math.pi) + rng.uniform(0, 1), 1.0)
    groove = np.exp(-((spiral - 0.5) / 0.16) ** 2)
    terry = _noise(D, D, seed + 5, [(2, 2), (5, 5)], [1.0, 0.5])
    light = np.clip(1.05 - 0.35 * ((xx - c * 0.7) ** 2 + (yy - c * 0.6) ** 2) / (c * c), 0.55, 1.1)
    col = np.array(color, np.float32)[None, None, :] * (light * (1 - 0.2 * groove) + 0.09 * terry)[..., None]
    edge = np.clip((1 - r) * c / 3, 0, 1)
    rgba = np.concatenate([np.clip(col, 0, 255), (edge * 255)[..., None]], -1).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA").filter(ImageFilter.GaussianBlur(1.1))


def eucalyptus(size, seed):
    rng = np.random.default_rng(seed)
    S = size
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(S * 0.1 + i * S * 0.08, S * 0.85 - i * S * 0.07 + math.sin(i) * 6) for i in range(11)]
    d.line(pts, fill=(96, 112, 96, 255), width=4, joint="curve")
    for i, (x, y) in enumerate(pts[1:], 1):
        for side in (-1, 1):
            r = S * rng.uniform(0.045, 0.07)
            cx, cy = x + side * r * 0.9, y - side * r * 0.3
            g = (int(118 + rng.uniform(-10, 10)), int(150 + rng.uniform(-10, 10)), int(140 + rng.uniform(-10, 10)), 255)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=g)
            d.ellipse((cx - r * 0.6, cy - r * 0.7, cx + r * 0.1, cy - r * 0.1), fill=(160, 186, 176, 200))
    return im


def build_plate(seed=3):
    rng = np.random.default_rng(seed)
    # wall: deep charcoal-teal with a soft window light pool and plaster texture
    yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
    wall_base = np.array([22, 34, 38], np.float32)
    pool = np.exp(-(((xx - PW * 0.62) / 560) ** 2 + ((yy - 1150) / 900) ** 2))
    tex = _noise(PH, PW, seed, [(6, 6), (30, 30), (120, 120)], [0.4, 0.8, 1.0])
    wall = wall_base + np.array([46, 70, 72], np.float32) * pool[..., None] + 4 * tex[..., None]
    # table: warm wood planks in perspective
    th = PH - TABLE_Y
    grain = _noise(th, PW, seed + 2, [(2, 60), (6, 260), (20, 600)], [0.6, 1.0, 0.7])
    planks = (np.mod(np.arange(th)[:, None] / (60 + np.arange(th)[:, None] * 0.35), 1.0) < 0.03).astype(np.float32)
    wood = np.array([118, 78, 48], np.float32) * (1 + 0.16 * grain)[..., None] * (1 - 0.35 * planks)[..., None]
    depth = (np.arange(th, dtype=np.float32) / th)[:, None, None]
    wood = wood * (0.62 + 0.5 * depth)
    img = wall.copy()
    img[TABLE_Y:] = wood
    # soft contact line + warm light across table
    img[TABLE_Y - 3:TABLE_Y + 3] *= 0.6
    plate = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    def drop(obj, x, y, blur=18, off=(16, 22), alpha=0.6):
        sh = Image.new("RGBA", (obj.width, obj.height), (8, 6, 4, 0))
        sh.putalpha(obj.getchannel("A").point(lambda v: int(v * alpha)))
        canvas = Image.new("RGBA", (obj.width + 120, obj.height + 120), (0, 0, 0, 0))
        canvas.paste(sh, (60, 60))
        canvas = canvas.filter(ImageFilter.GaussianBlur(blur))
        plate.alpha_composite(canvas, (int(x - 60 + off[0]), int(y - 60 + off[1])))
        plate.alpha_composite(obj, (int(x), int(y)))

    # rolled towels pyramid (left-centre)
    rolls = [(420, 2235, 300), (720, 2235, 300), (570, 1995, 290)]
    for i, (x, y, d) in enumerate(rolls):
        drop(towel_roll(d, seed + 10 + i), x - d / 2, y - d / 2, blur=24, off=(20, 30), alpha=0.55)
    # eucalyptus sprig over the towels
    # bamboo sticks bundle (right, diagonal), front to back
    sticks = []
    for i in range(7):
        L = rng.uniform(820, 1080)
        R = rng.uniform(26, 36)
        st = bamboo_stick(L, R, seed + 40 + i, tone=rng.uniform(0.92, 1.08))
        st = st.rotate(rng.uniform(18, 26), resample=Image.BICUBIC, expand=True)
        sticks.append((st, 760 + i * 34 + rng.uniform(-10, 10), 2100 + i * 40 + rng.uniform(-14, 14)))
    for st, x, y in sticks:
        drop(st, x, y, blur=14, off=(12, 26), alpha=0.65)
    # warm key light from upper left over the table, cool teal rim from the right
    arr = np.asarray(plate, np.float32)
    key = np.exp(-(((xx - PW * 0.35) / 900) ** 2 + ((yy - 2300) / 900) ** 2))[..., None]
    rim = np.exp(-(((xx - PW) / 500) ** 2))[..., None] * np.exp(-(((yy - 1500) / 1000) ** 2))[..., None]
    arr[..., :3] = arr[..., :3] * (0.82 + 0.38 * key) + np.array([20, 60, 64], np.float32) * rim * 0.6
    vig = 1 - 0.38 * np.clip(((xx - PW / 2) / PW) ** 2 * 2.4 + ((yy - PH * 0.55) / PH) ** 2 * 2.0, 0, 1)
    arr[..., :3] *= vig[..., None]
    plate = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    # foreground: two big defocused bamboo sticks crossing the bottom corner
    fg = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    for i, (ang, x, y) in enumerate([(-28, -120, 2650), (-20, 900, 2820)]):
        st = bamboo_stick(1400, 70, seed + 90 + i, tone=0.8).rotate(ang, resample=Image.BICUBIC, expand=True)
        fg.alpha_composite(st, (x, y - st.height // 2))
    fg = fg.filter(ImageFilter.GaussianBlur(16))
    return plate, fg


if __name__ == "__main__":
    import sys
    p, f = build_plate()
    p.alpha_composite(f)
    p.convert("RGB").resize((PW // 2, PH // 2)).save(sys.argv[1])
