"""Procedural golden-hour poppy field with wheat ears moving in the wind.

Design goals (owner feedback): looks like a living photograph, not a heavy blur.
- Sky with drifting clouds and a low sun (open space for type).
- Ground of dense grass/wheat that ripples with a travelling wind wave (remap).
- Detailed poppy heads (backlit translucent petals, black basal blotches,
  stamens, seed pod) and wheat ears as pre-rendered sprites that sway per frame.
- Light depth of field only: far layer soft, mid sharp, foreground slightly soft.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
HORIZON = 1170


def _noise(h, w, seed, scales, weights):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    for sc, wt in zip(scales, weights):
        small = rng.normal(0, 1, (max(2, h // sc), max(2, w // sc))).astype(np.float32)
        out += wt * np.asarray(Image.fromarray(small, "F").resize((w, h), Image.BICUBIC))
    return out / np.abs(out).max()


def _premul_blur(img, r):
    a = np.asarray(img, np.float32) / 255.0
    pre = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)
    b = np.asarray(Image.fromarray((pre * 255).astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0
    al = b[..., 3:4]
    rgb = np.where(al > 1e-4, b[..., :3] / np.maximum(al, 1e-4), 0)
    return Image.fromarray((np.concatenate([np.clip(rgb, 0, 1), al], -1) * 255).astype(np.uint8), "RGBA")


# ---------------------------------------------------------------- sprites
def poppy_sprite(rng, size=220):
    """Side-lit poppy head seen slightly from the side; returns RGBA (size x size)."""
    S = size
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    cx, cy = S / 2, S * 0.55
    rgba = np.zeros((S, S, 4), np.float32)
    petals = [  # (angle of petal axis, length, width, brightness) back petals first
        (-2.35, 0.47, 0.40, 1.15), (-0.80, 0.47, 0.40, 1.12), (-1.57, 0.44, 0.42, 1.18),
        (-2.75, 0.40, 0.36, 0.95), (-0.40, 0.40, 0.36, 0.95), (1.57, 0.30, 0.46, 0.85),
    ]
    vein = _noise(S, S, int(rng.integers(1e6)), (2, 5), (1.0, 0.5))
    for ang, ln, wd, br in petals:
        ang += rng.uniform(-0.18, 0.18)
        L, Wd = ln * S, wd * S
        px, py = xx - cx, (yy - cy) * 1.25
        u = px * math.cos(ang) + py * math.sin(ang)          # along petal
        v = -px * math.sin(ang) + py * math.cos(ang)         # across petal
        un = u / L
        theta = np.arctan2(v, np.maximum(u, 1e-3))
        ruffle = 1 + 0.07 * np.sin(theta * rng.uniform(7, 11) + rng.uniform(0, 6))
        width_at = Wd * np.sqrt(np.clip(un, 0, 1)) * (1.15 - 0.35 * un) * ruffle
        inside = (un > 0) & (un < 1.0 * ruffle) & (np.abs(v) < width_at)
        edge = np.clip(1 - np.maximum(np.abs(v) / np.maximum(width_at, 1), un / ruffle), 0, 1)
        alpha = np.clip(edge * 6, 0, 1) * inside
        # colour: dark crimson base -> scarlet -> glowing orange rim (backlight)
        c_base = np.array([120, 8, 22], np.float32)
        c_mid = np.array([222, 34, 26], np.float32)
        c_rim = np.array([255, 104, 58], np.float32)
        k1 = np.clip(un / 0.45, 0, 1)[..., None]
        k2 = np.clip((un - 0.45) / 0.55, 0, 1)[..., None]
        col = c_base * (1 - k1) + c_mid * k1
        col = col * (1 - k2) + c_rim * k2 * 0.85 + col * k2 * 0.15
        rim = np.clip(1 - edge * 5, 0, 1)[..., None] * 0.35
        col = col * (1 - rim) + np.array([255, 150, 90], np.float32) * rim
        col *= (br + 0.08 * vein[..., None] + 0.05 * np.sin(theta * 30)[..., None])
        # black basal blotch
        blotch = np.clip(1 - un / 0.18, 0, 1)[..., None] ** 1.5
        col = col * (1 - blotch) + np.array([28, 12, 20], np.float32) * blotch
        a = alpha[..., None]
        rgba[..., :3] = rgba[..., :3] * (1 - a) + col * a
        rgba[..., 3:] = np.maximum(rgba[..., 3:], a * 255)
    img = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    r = S * 0.075
    for i in range(26):  # stamens
        a = 2 * math.pi * i / 26
        sx, sy = cx + math.cos(a) * r * 1.5, cy - S * 0.02 + math.sin(a) * r * 0.9
        d.ellipse((sx - 2.2, sy - 2.2, sx + 2.2, sy + 2.2), fill=(30, 22, 34, 255))
    d.ellipse((cx - r, cy - S * 0.02 - r * 0.8, cx + r, cy - S * 0.02 + r * 0.8), fill=(118, 136, 82, 255))
    d.ellipse((cx - r * 0.7, cy - S * 0.02 - r * 0.55, cx + r * 0.7, cy - S * 0.02 + r * 0.2), fill=(150, 166, 104, 255))
    return img


def bud_sprite(rng, size=90):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    d.ellipse((c - size * .18, c - size * .30, c + size * .18, c + size * .30), fill=(96, 122, 70, 255))
    d.ellipse((c - size * .10, c - size * .26, c + size * .06, c + size * .05), fill=(150, 170, 104, 255))
    for i in range(40):  # fine hairs
        a = rng.uniform(0, 6.28)
        d.line((c + math.cos(a) * size * .17, c + math.sin(a) * size * .29,
                c + math.cos(a) * size * .23, c + math.sin(a) * size * .35), fill=(200, 210, 170, 120), width=1)
    return im


def wheat_sprite(rng, length=170):
    """Ear pointing UP, origin at bottom-centre."""
    Wd = 70
    im = Image.new("RGBA", (Wd, length), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = Wd / 2
    n = 16
    for i in range(n):
        u = i / (n - 1)
        y = length - 10 - u * (length * 0.55)
        for side in (-1, 1):
            gx = c + side * 4.2 * (1 - 0.3 * u)
            gw, gh = 4.0 * (1 - 0.3 * u), 8.5 * (1 - 0.25 * u)
            base = (int(214 + rng.uniform(-10, 10)), int(176 + rng.uniform(-10, 10)), int(98 + rng.uniform(-8, 8)), 255)
            d.ellipse((gx - gw, y - gh, gx + gw, y + gh), fill=base, outline=(150, 118, 60, 255))
            d.ellipse((gx - gw * .5, y - gh * .85, gx + gw * .2, y - gh * .1), fill=(250, 228, 168, 255))
            d.line((gx, y - gh, gx + side * 6, y - gh - length * 0.32), fill=(238, 210, 150, 190), width=1)
    d.line((c, length, c, length * 0.4), fill=(200, 170, 100, 255), width=2)
    return im


# ---------------------------------------------------------------- build
def build(seed=4):
    rng = np.random.default_rng(seed)
    F = {}
    # sky
    ys = np.linspace(0, 1, HORIZON + 60, dtype=np.float32)
    stops = [(0, (196, 212, 226)), (0.45, (236, 228, 218)), (0.8, (250, 214, 176)), (1, (255, 198, 140))]
    sky = np.zeros((len(ys), 3), np.float32)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = (ys >= p0) & (ys <= p1)
        u = ((ys[m] - p0) / (p1 - p0))[:, None]
        sky[m] = np.array(c0) * (1 - u) + np.array(c1) * u
    F["sky"] = np.repeat(sky[:, None, :], W, 1)
    cl = _noise(HORIZON + 60, W + 800, seed + 1, (30, 90, 260), (0.35, 0.8, 1.0))
    cl = np.clip((cl - 0.05) * 2.2, 0, 1)
    vert = np.clip(1 - np.abs(np.linspace(0, 1, HORIZON + 60) - 0.55) / 0.45, 0, 1)[:, None]
    F["clouds"] = (cl * vert).astype(np.float32)
    sx, sy = 800, HORIZON - 40
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt((xx - sx) ** 2 + ((yy - sy) * 1.25) ** 2)
    F["sun"] = (np.exp(-r / 60) * 0.95 + np.exp(-r / 380) * 0.55)[..., None].astype(np.float32)

    # ground: dense grass + far poppies, rippled by a remap each frame
    GH = H - HORIZON + 40
    g = Image.new("RGBA", (W + 120, GH), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    gd.rectangle((0, 40, W + 120, GH), fill=(150, 132, 70, 255))
    for x in range(-40, W + 160, 14):  # far tree line / hedge
        h = rng.uniform(20, 56)
        gd.ellipse((x - 26, 42 - h, x + 26, 42 + h * 0.35), fill=(118, 124, 94, 255))
    for _ in range(26000):
        yv = rng.uniform(0, 1) ** 1.35
        y = 40 + yv * (GH - 40)
        x = rng.uniform(0, W + 120)
        depth = yv
        L = 3 + depth * 46
        if rng.random() < 0.16 * (1 - 0.5 * depth):
            s = 0.9 + depth * 7
            gd.ellipse((x - s, y - L * 0.6 - s * 0.7, x + s, y - L * 0.6 + s * 0.7),
                       fill=(int(rng.uniform(200, 236)), int(rng.uniform(30, 62)), int(rng.uniform(24, 40)), 255))
        else:
            tone = rng.random()
            col = (int(150 + 80 * tone), int(140 + 50 * tone), int(70 + 40 * tone), 255) if rng.random() < 0.6 else \
                  (int(90 + 50 * tone), int(112 + 40 * tone), int(56 + 20 * tone), 255)
            gd.line((x, y, x + rng.uniform(-3, 3) * (1 + depth * 2), y - L), fill=col, width=max(1, int(1 + depth * 2.2)))
    g = g.filter(ImageFilter.GaussianBlur(0.6))
    garr = np.asarray(g, np.float32)
    haze = np.exp(-np.arange(GH) / 90.0)[:, None, None] * 0.55
    garr[..., :3] = garr[..., :3] * (1 - haze) + np.array([250, 214, 170]) * haze
    F["ground"] = garr
    F["gy"], F["gx"] = np.mgrid[0:GH, 0:W]

    # animated plants
    els = []
    pop_sprites = [poppy_sprite(rng) for _ in range(10)]
    bud_sprites = [bud_sprite(rng) for _ in range(3)]
    for _ in range(300):
        depth = rng.uniform(0, 1) ** 0.75
        base = HORIZON + 50 + depth * (H - HORIZON + 60)
        x = rng.uniform(-40, W + 40)
        kind = rng.choice(["wheat", "poppy", "bud"], p=[0.48, 0.42, 0.10])
        sc = 0.22 + 0.85 * depth
        hgt = (45 + 300 * depth) * rng.uniform(0.75, 1.2)
        els.append(["mid", kind, x, base, hgt, rng.uniform(0, 6.28), sc, rng.integers(10)])
    for _ in range(9):
        x = rng.uniform(-60, W + 60)
        kind = rng.choice(["wheat", "poppy"], p=[0.55, 0.45])
        els.append(["near", kind, x, H + rng.uniform(60, 160), rng.uniform(330, 470), rng.uniform(0, 6.28), 1.45, rng.integers(10)])
    els.sort(key=lambda e: e[3])
    # pre-scale sprites per element
    for e in els:
        kind, sc = e[1], e[6]
        if kind == "poppy":
            sp = pop_sprites[e[7]]
            s = int(sp.width * sc * 0.62)
            sq = rng.uniform(0.7, 1.0)  # some heads turned slightly away
            hd = sp.resize((max(4, int(s * sq)), max(4, s)), Image.LANCZOS)
            e.append(hd.rotate(rng.uniform(-28, 28), resample=Image.BICUBIC, expand=True))
        elif kind == "bud":
            sp = bud_sprites[e[7] % 3]
            s = int(sp.width * sc * 0.8)
            e.append(sp.resize((max(3, s), max(3, s)), Image.LANCZOS))
        else:
            sp = wheat_sprite(rng)
            e.append(sp.resize((max(3, int(sp.width * sc)), max(6, int(sp.height * sc))), Image.LANCZOS))
    F["els"] = els
    F["grain"] = [rng.normal(0, 3.2, (H, W, 1)).astype(np.float32) for _ in range(3)]
    return F


def wind(t, x, phase=0.0):
    return (math.sin(1.3 * t - x * 0.0065 + phase * 0.3) * 0.75
            + 0.35 * math.sin(0.47 * t - x * 0.0021) * math.sin(0.83 * t + phase))


def render(t, F, sun_amt=1.0):
    # sky + clouds
    off = int(t * 12) % 800
    cl = F["clouds"][:, off:off + W][..., None]
    sky = F["sky"] * (1 - 0.06 * cl) + np.array([255, 248, 240], np.float32) * cl * 0.10
    # ground ripple (travelling wave remap)
    GH = F["ground"].shape[0]
    gy, gx = F["gy"], F["gx"]
    depth = gy / GH
    dx = (np.sin(1.3 * t - gx * 0.0065) * 0.75 + 0.35 * np.sin(0.47 * t - gx * 0.0021) * math.sin(0.83 * t)) * (1 + 7 * depth)
    sx = np.clip((gx + 60 + dx).astype(np.int32), 0, W + 119)
    ground = F["ground"][gy, sx]
    frame = np.zeros((H, W, 3), np.float32)
    frame[:HORIZON + 60] = sky
    top = HORIZON - 40
    a = ground[..., 3:4] / 255.0
    frame[top:] = frame[top:] * (1 - a) + ground[..., :3] * a
    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    # plants: stems on a 2x canvas, sprites composited after downscale
    SS = 2
    y0 = HORIZON
    stems = {k: Image.new("RGBA", (W * SS, (H - y0) * SS), (0, 0, 0, 0)) for k in ("mid", "near")}
    sd = {k: ImageDraw.Draw(v) for k, v in stems.items()}
    heads = {"mid": [], "near": []}
    for e in F["els"]:
        layer, kind, x, base, hgt, ph, sc, _, sp = e
        amp = (0.10 + 0.06 * (layer == "near")) * (0.6 if kind == "poppy" else 1.0)
        ang = amp * wind(t, x, ph) + 0.02 * math.sin(3.0 * t + ph)
        pts = []
        for i in range(9):
            u = i / 8
            pts.append(((x + math.sin(ang) * hgt * u * u) * SS, (base - hgt * u * math.cos(ang * u) - y0) * SS))
        col = (106, 124, 66, 255) if kind != "wheat" else (196, 170, 104, 255)
        sd[layer].line(pts, fill=col, width=max(2, int(2.6 * sc * SS)), joint="curve")
        tipx, tipy = pts[-1][0] / SS, pts[-1][1] / SS + y0
        if kind == "wheat":
            rot = sp.rotate(-math.degrees(ang * 1.6), resample=Image.BICUBIC, expand=True)
            heads[layer].append((rot, tipx - rot.width / 2 + math.sin(ang * 1.6) * sp.height * 0.5,
                                 tipy - rot.height / 2 - sp.height * 0.45))
        elif kind == "bud":
            heads[layer].append((sp, tipx - sp.width / 2 + sp.width * 0.25, tipy - sp.height * 0.35))
        else:
            heads[layer].append((sp, tipx - sp.width / 2, tipy - sp.height * 0.6))
    for layer, blur in (("mid", 0), ("near", 5)):
        st = stems[layer].resize((W, H - y0), Image.LANCZOS)
        lay = Image.new("RGBA", (W, H - y0), (0, 0, 0, 0))
        lay.alpha_composite(st)
        for sp, px, py in heads[layer]:
            ix, iy = int(px), int(py - y0)
            if -sp.width < ix < W and -sp.height < iy < H - y0:
                lay.alpha_composite(sp, (max(ix, 0), max(iy, 0)), (max(-ix, 0), max(-iy, 0)))
        if blur:
            lay = _premul_blur(lay, blur)
        img.alpha_composite(lay, (0, y0))

    arr = np.asarray(img.convert("RGB"), np.float32) / 255.0
    light = np.clip(F["sun"] * sun_amt, 0, 1)
    arr = 1 - (1 - arr) * (1 - light * np.array([1.0, 0.84, 0.58], np.float32) * 0.85)
    arr = arr * np.array([1.03, 0.99, 0.93], np.float32) + 0.012
    out = arr * 255 + F["grain"][int(t * 15) % 3]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


if __name__ == "__main__":
    import sys
    import time
    t0 = time.time()
    F = build()
    print("build", time.time() - t0)
    t0 = time.time()
    render(2.0, F).convert("RGB").save(sys.argv[1])
    print("frame", time.time() - t0)
