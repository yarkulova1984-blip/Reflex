"""Procedural sunlit-garden background: defocused pink and white peonies, foliage,
sun bloom, light rays and bokeh. Built as depth layers so a video can drift them
at different speeds (parallax).
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920


def _rgba(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def _blur_alpha_layer(color_img, blur):
    """Blur an RGBA layer without dark fringes (premultiply, blur, un-premultiply)."""
    a = np.asarray(color_img, np.float32) / 255.0
    rgb, al = a[..., :3] * a[..., 3:4], a[..., 3:4]
    pre = Image.fromarray((np.concatenate([rgb, al], -1) * 255).astype(np.uint8), "RGBA")
    pre = pre.filter(ImageFilter.GaussianBlur(blur))
    b = np.asarray(pre, np.float32) / 255.0
    al = b[..., 3:4]
    rgb = np.where(al > 1e-4, b[..., :3] / np.maximum(al, 1e-4), 0)
    return Image.fromarray((np.concatenate([np.clip(rgb, 0, 1), al], -1) * 255).astype(np.uint8), "RGBA")


def peony(diameter, base, edge, center, seed, petals_scale=1.0):
    """A ruffled peony head drawn from layered petals; meant to be shown defocused."""
    rng = np.random.default_rng(seed)
    s = 2
    D = int(diameter * s)
    im = _rgba((D, D))
    d = ImageDraw.Draw(im)
    c = D / 2
    rings = [(1.0, 11), (0.86, 10), (0.72, 9), (0.58, 8), (0.44, 7), (0.30, 6), (0.18, 5)]
    for ri, (rr, n) in enumerate(rings):
        R = rr * D / 2 * petals_scale
        for k in range(n):
            ang = 2 * math.pi * (k + rng.uniform(-0.25, 0.25)) / n + ri * 0.4
            pl = R * rng.uniform(0.45, 0.85)       # petal length
            pw = R * rng.uniform(0.38, 0.55)       # petal half-width
            jit = rng.uniform(0.4, 0.7)
            cx = c + math.cos(ang) * (R - pl * jit)
            cy = c + math.sin(ang) * (R - pl * jit) * 0.92
            pts = []
            for i in range(48):
                t = 2 * math.pi * i / 48
                ruffle = 1 + 0.08 * math.sin(t * rng.integers(5, 9) + rng.uniform(0, 6))
                x = math.cos(t) * pl * 0.5 * ruffle
                y = math.sin(t) * pw * 0.5 * ruffle * (1.0 if math.cos(t) > 0 else 0.8)
                pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
            mix = ri / (len(rings) - 1)
            col = tuple(int(edge[j] * (1 - mix) + center[j] * mix + rng.uniform(-8, 8)) for j in range(3))
            d.polygon(pts, fill=col + (255,))
            # soft lighter rim on each petal for cupped depth
            d.line(pts + [pts[0]], fill=tuple(min(255, v + 18) for v in col) + (200,), width=max(2, int(3 * s)))
    # radial shading: deeper tone near the centre, light falling from upper right
    yy, xx = np.mgrid[0:D, 0:D].astype(np.float32)
    r = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / (D / 2)
    light = np.clip(1.0 + 0.18 * ((xx - c) / D * 1.0 - (yy - c) / D * 1.4), 0.8, 1.15)
    arr = np.asarray(im, np.float32)
    shade = (0.82 + 0.18 * np.clip(r, 0, 1))[..., None] * light[..., None]
    arr[..., :3] = np.clip(arr[..., :3] * shade, 0, 255)
    out = Image.fromarray(arr.astype(np.uint8), "RGBA").resize((diameter, diameter), Image.LANCZOS)
    return out


def _gradient(stops, h, w):
    ys = np.linspace(0, 1, h, dtype=np.float32)
    cols = np.zeros((h, 3), np.float32)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = (ys >= p0) & (ys <= p1)
        u = ((ys[m] - p0) / (p1 - p0))[:, None]
        cols[m] = np.array(c0) * (1 - u) + np.array(c1) * u
    return np.repeat(cols[:, None, :], w, 1)


def build_garden(seed=8, pad=160):
    """Return dict of depth layers (RGBA, larger than the frame by `pad` for drift)."""
    rng = np.random.default_rng(seed)
    LW, LH = W + 2 * pad, H + 2 * pad
    L = {"pad": pad}

    # far: sunlit canopy and lawn, very defocused
    base = _gradient([(0, (250, 238, 204)), (0.2, (214, 214, 156)), (0.45, (128, 156, 92)),
                      (0.75, (82, 114, 64)), (1, (58, 88, 50))], LH, LW)
    far = Image.fromarray(base.astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(far)
    greens = [(86, 122, 64), (118, 150, 80), (58, 90, 50), (150, 168, 100), (100, 134, 62)]
    for _ in range(170):
        x, y = rng.uniform(0, LW), rng.uniform(0.12, 1.0) * LH
        r = rng.uniform(80, 260)
        g = greens[rng.integers(len(greens))]
        d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=g + (int(rng.uniform(110, 210)),))
    for _ in range(40):  # sky gaps through leaves
        x, y = rng.uniform(0, LW), rng.uniform(0, 0.45) * LH
        r = rng.uniform(60, 200)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 246, 215, int(rng.uniform(120, 220))))
    L["far"] = far.filter(ImageFilter.GaussianBlur(70))

    # mid: peony bushes, defocused (pink and white), kept to the sides and lower part
    mid = _rgba((LW, LH))
    pinks = [((238, 156, 180), (246, 190, 204), (204, 92, 128)),
             ((232, 140, 168), (244, 178, 196), (196, 80, 120)),
             ((250, 238, 232), (255, 248, 244), (236, 214, 206)),   # white peony
             ((252, 244, 238), (255, 252, 248), (238, 222, 210))]
    md = ImageDraw.Draw(mid)
    for _ in range(900):  # foliage texture: many small irregular leaves around the bushes
        x = rng.choice([rng.uniform(-0.05, 0.4), rng.uniform(0.6, 1.05)]) * LW
        y = rng.uniform(0.4, 1.05) * LH
        if rng.random() < 0.25:
            x = rng.uniform(0.15, 0.85) * LW
            y = rng.uniform(0.82, 1.05) * LH
        r = rng.uniform(22, 64)
        a = rng.uniform(0, math.pi)
        g = greens[rng.integers(len(greens))]
        k = rng.uniform(0.55, 1.05)
        pts = [(x + math.cos(t) * r * math.cos(a) - math.sin(t) * r * 0.42 * math.sin(a),
                y + math.cos(t) * r * math.sin(a) + math.sin(t) * r * 0.42 * math.cos(a))
               for t in np.linspace(0, 2 * math.pi, 16)]
        md.polygon(pts, fill=tuple(int(min(255, v * k)) for v in g) + (int(rng.uniform(150, 240)),))
    spots = []
    for _ in range(26):
        side = rng.random()
        x = (rng.uniform(-0.05, 0.36) if side < 0.5 else rng.uniform(0.64, 1.05)) * LW
        y = rng.uniform(0.42, 1.02) * LH
        if rng.random() < 0.25:
            x, y = rng.uniform(0.2, 0.8) * LW, rng.uniform(0.86, 1.02) * LH
        spots.append((x, y))
    for i, (x, y) in enumerate(sorted(spots, key=lambda p: p[1])):
        base_c, edge_c, center_c = pinks[rng.choice(4, p=[0.33, 0.27, 0.22, 0.18])]
        dia = int(rng.uniform(170, 300) * (0.8 + 0.5 * y / LH))
        fl = peony(dia, base_c, edge_c, center_c, seed * 100 + i)
        mid.alpha_composite(fl, (int(x - dia / 2), int(y - dia / 2)))
    L["mid"] = _blur_alpha_layer(mid, 19)

    # near: two large blooms in the foreground corners, strongly defocused
    near = _rgba((LW, LH))
    fl = peony(760, *pinks[0], seed=seed * 7 + 1)
    near.alpha_composite(fl, (-260, LH - 600))
    fl = peony(680, *pinks[2], seed=seed * 7 + 2)
    near.alpha_composite(fl, (LW - 400, LH - 520))
    nd = ImageDraw.Draw(near)
    for (x, y, r) in [(160, LH - 760, 150), (LW - 160, LH - 700, 140), (LW - 60, LH - 820, 110)]:
        nd.ellipse((x - r, y - r * 0.5, x + r, y + r * 0.5), fill=(84, 118, 70, 220))
    L["near"] = _blur_alpha_layer(near, 34)

    # bokeh: specular highlights through foliage (added with screen blend)
    bok = Image.new("RGB", (LW, LH), (0, 0, 0))
    bd = ImageDraw.Draw(bok)
    for _ in range(46):
        x, y = rng.uniform(0, LW), (rng.uniform(0, 0.55) ** 1.3) * LH
        r = rng.uniform(14, 62)
        v = rng.uniform(0.18, 0.5)
        col = (int(255 * v), int(238 * v), int(196 * v))
        bd.ellipse((x - r, y - r, x + r, y + r), fill=col)
        rim = tuple(min(255, int(c * 1.25)) for c in col)
        bd.ellipse((x - r, y - r, x + r, y + r), outline=rim, width=max(2, int(r * 0.08)))
    L["bokeh"] = np.asarray(bok.filter(ImageFilter.GaussianBlur(2.2)), np.float32) / 255.0

    # sun bloom + rays (polar), precomputed coordinates for cheap per-frame animation
    sx, sy = 900, 230
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = xx - sx, yy - sy
    L["theta"] = (np.arctan2(dy, dx) + math.pi) / (2 * math.pi)
    rr = np.sqrt(dx * dx + dy * dy)
    L["glow"] = (np.exp(-rr / 130) * 0.8 + np.exp(-rr / 480) * 0.35)[..., None]
    L["rayfall"] = (np.exp(-rr / 900) * np.clip(rr / 120, 0, 1))[..., None]
    n = 720
    raw = rng.normal(0, 1, n)
    k = np.exp(-np.linspace(-3, 3, 31) ** 2)
    sm = np.convolve(np.concatenate([raw, raw[:12]]), k / k.sum(), mode="same")[:n]
    L["raynoise"] = np.clip((sm - sm.mean()) / sm.std() * 0.35 + 0.25, 0, 1).astype(np.float32)
    L["grain"] = [rng.normal(0, 3.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    return L


def render_bg(t, L, intro=1.0):
    """Compose the garden at time t. intro ramps the sun from 0 to 1."""
    p = L["pad"]
    f = Image.new("RGBA", (W, H))
    # parallax drift: far moves least, near moves most (slow push toward the sun)
    def crop(layer, k):
        ox = p + int(-k * 26 * math.sin(t * 0.18))
        oy = p + int(-k * 40 * t / 18.0)
        return layer.crop((ox, oy, ox + W, oy + H))
    f.alpha_composite(crop(L["far"], 0.3))
    f.alpha_composite(crop(L["mid"], 0.7))
    f.alpha_composite(crop(L["near"], 1.4))
    img = np.asarray(f.convert("RGB"), np.float32) / 255.0

    shift = int(t * 6) % len(L["raynoise"])
    idx = ((L["theta"] * len(L["raynoise"])).astype(np.int32) + shift) % len(L["raynoise"])
    rays = L["raynoise"][idx][..., None] * L["rayfall"] * 0.24
    light = np.clip(L["glow"] * 1.0 + rays, 0, 1) * intro
    warm = np.array([1.0, 0.93, 0.78], np.float32)
    img = 1 - (1 - img) * (1 - light * warm)
    bx = p + int(-0.9 * 26 * math.sin(t * 0.18))
    by = p + int(-0.9 * 40 * t / 18.0)
    bok = L["bokeh"][by:by + H, bx:bx + W] * (0.6 + 0.4 * math.sin(t * 0.7)) * intro
    img = 1 - (1 - img) * (1 - bok)
    img = img * 255 + L["grain"][int(t * 15) % 3]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


if __name__ == "__main__":
    import sys
    L = build_garden()
    render_bg(2.0, L).convert("RGB").save(sys.argv[1] if len(sys.argv) > 1 else "garden.png")
