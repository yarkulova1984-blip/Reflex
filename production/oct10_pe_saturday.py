"""THE PURE ESCAPE — Available Appointment — Saturday, October 10, 2026 — 10:30 a.m.

Concept "Saturday Light": ivory + deep green + refined gold (benchmark: the owner's reference
posters, re-designed originally). A bright treatment room opens and closes the Reel; the
services scroll through a candlelit sequence, one photo per service.
Living background: candle flames flicker (masked glow), flowers sway (masked local warp),
golden motes drift, camera push-in / slide / pull-back, cross-defocus between photos.
Type: Gilda Display (editorial serif) + Tenor Sans (minimal sans) + Alex Brush (script accent).

  python3 production/oct10_pe_saturday.py stills
  python3 production/oct10_pe_saturday.py video
"""
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
P_PE = os.path.join(ROOT, "brand", "photos", "pe-facial")
P_AMT = os.path.join(ROOT, "brand", "photos", "amt")   # generic photos without clinic branding
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-10-pe-available-appointment"
W, H, FPS = 1080, 1920, 30
DURATION = 30.0

GREEN = (22, 62, 40)
IVORY = (250, 244, 232)
NIGHT = (10, 12, 8)

# ---------------------------------------------------------------- facts (owner-provided; verified)
CLINIC = "The Pure Escape"
ADDRESS = "698 Corydon Ave, Winnipeg"
THERAPIST = "Zarina, RCRT"
DAY, MONTH, DAYNUM = "SATURDAY", "October", "10"
TIME, AMPM = "10:30", "a.m."
SERVICES = [  # (name, sub-line) — names corrected from the reference posters
    ("Facial Reflexology", "BERGMAN METHOD"),
    ("Hand Reflexology", "WITH CHANEL SKINCARE"),
    ("Foot Reflexology", ""),
    ("Reflexology Lymph Drainage", "RLD"),
    ("Spanish Massage", ""),
    ("Ultimate Escape Package", ""),
]


# ---------------------------------------------------------------- type
def gilda(size):
    return ImageFont.truetype(os.path.join(FONTS, "GildaDisplay-Regular.ttf"), size)


def tenor(size):
    return ImageFont.truetype(os.path.join(FONTS, "TenorSans-Regular.ttf"), size)


def brush(size):
    return ImageFont.truetype(os.path.join(FONTS, "AlexBrush-Regular.ttf"), size)


GOLDS = {  # top, mid, bottom of the metallic gradient
    "gold": ((240, 214, 160), (206, 166, 98), (158, 116, 58)),      # for dark scenes
    "deepgold": ((214, 176, 108), (176, 132, 62), (128, 90, 36)),  # for bright ivory scenes
}


def metal(w, h, kind):
    top, mid, bot = [np.array(c, np.float32) for c in GOLDS[kind]]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    k1 = np.clip(y / 0.5, 0, 1)
    k2 = np.clip((y - 0.5) / 0.5, 0, 1)
    col = (top * (1 - k1) + mid * k1) * (1 - k2) + bot * k2
    col = np.broadcast_to(col, (h, w, 3)).copy()
    sheen = np.exp(-(((x - y * 0.35) - 0.3) / 0.1) ** 2) * 0.22
    return col * (1 - sheen) + np.array([255, 244, 214], np.float32) * sheen


class Text:
    def __init__(self, txt, fnt, fill, tracking=0, shadow=None, halo=None):
        kw = {"features": ["lnum"]}
        asc, desc = fnt.getmetrics()
        pad = int(fnt.size * 0.4)
        width = (sum(fnt.getlength(c, **kw) for c in txt) + tracking * (len(txt) - 1)) if tracking else fnt.getlength(txt, **kw)
        size = (math.ceil(width) + 2 * pad, asc + desc + pad)
        mask = Image.new("L", size, 0)
        d = ImageDraw.Draw(mask)
        if tracking:
            x = pad
            for c in txt:
                d.text((x, asc), c, font=fnt, fill=255, anchor="ls", **kw)
                x += fnt.getlength(c, **kw) + tracking
        else:
            d.text((pad, asc), txt, font=fnt, fill=255, anchor="ls", **kw)
        if fill in GOLDS:
            arr = np.concatenate([metal(size[0], size[1], fill), np.asarray(mask, np.float32)[..., None]], -1)
            layer = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        else:
            layer = Image.new("RGBA", size, fill + (0,))
            layer.putalpha(mask)
        for col, amt in ((shadow, 0.75), (halo, 0.9)):
            if col is not None:
                g = Image.new("RGBA", size, col + (0,))
                g.putalpha(mask.filter(ImageFilter.GaussianBlur(max(3, fnt.size // 12))).point(lambda v: int(v * amt)))
                g.alpha_composite(layer)
                layer = g
        self.img, self.asc, self.pad, self.adv = layer, asc, pad, width
        self.w, self.h = layer.size


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    p = min(max(p, 0.0), 1.0)
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def prog(t, s, d):
    return min(max((t - s) / d, 0.0), 1.0)


def with_alpha(img, a):
    if a >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


def put(f, img, x, y, a=1.0):
    if a > 0.003:
        f.alpha_composite(with_alpha(img, a), (int(round(x)), int(round(y))))


def put_x(f, tx, x, base, a=1.0, dx=0.0, dy=0.0):
    put(f, tx.img, x - tx.pad + dx, base - tx.asc + dy, a)


def put_c(f, tx, base, a=1.0, dx=0.0, dy=0.0, cx=W / 2):
    put_x(f, tx, cx - tx.adv / 2, base, a, dx, dy)


def sharp_in(f, tx, x, base, p, a=1.0, scale_from=1.0):
    if p <= 0:
        return
    e = ease_out(p)
    img = tx.img
    s = scale_from + (1 - scale_from) * e
    if abs(s - 1) > 0.003:
        img = img.resize((int(tx.w * s), int(tx.h * s)), Image.LANCZOS)
    if e < 0.97:
        img = img.filter(ImageFilter.GaussianBlur(12 * (1 - e)))
    cx = x + tx.adv / 2
    put(f, img, cx - (tx.adv / 2 + tx.pad) * s, base - tx.asc * s, e * a)


def write_on(f, tx, x, base, p, a=1.0):
    if p <= 0:
        return
    vis = int(tx.w * ease_in_out(p))
    if vis > 0:
        put(f, tx.img.crop((0, 0, vis, tx.h)), x - tx.pad, base - tx.asc, a)


def line(f, cx, y, length, color, a=1.0, thick=2):
    if length > 1 and a > 0:
        f.alpha_composite(Image.new("RGBA", (int(length), thick), color + (int(255 * a),)), (int(cx - length / 2), int(y)))


def sprig(size, color):
    """Fine botanical line ornament (two leaves on a curved stem)."""
    s = 4
    im = Image.new("RGBA", (size * s, size * s // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w, h = im.size
    pts = [(w * 0.05 + w * 0.9 * u, h * 0.62 - math.sin(u * math.pi) * h * 0.18) for u in np.linspace(0, 1, 40)]
    d.line(pts, fill=color + (255,), width=3 * s // 2)
    for u, side in ((0.35, -1), (0.55, 1), (0.75, -1)):
        x, y = w * 0.05 + w * 0.9 * u, h * 0.62 - math.sin(u * math.pi) * h * 0.18
        lw, lh = w * 0.13, h * 0.22
        leaf = Image.new("RGBA", (int(lw * 2), int(lh * 2)), (0, 0, 0, 0))
        ImageDraw.Draw(leaf).ellipse((lw * 0.5, lh * 0.5, lw * 1.5, lh * 1.5), outline=color + (255,), width=3 * s // 2)
        leaf = leaf.rotate(35 * side, resample=Image.BICUBIC)
        im.alpha_composite(leaf, (int(x - lw), int(y - lh + side * lh * 0.35)))
    return im.resize((size, size // 2), Image.LANCZOS)


# ---------------------------------------------------------------- living photos
def extend_top(im, frac, bright=False):
    add = int(im.height * frac)
    if add <= 0:
        return im
    strip = im.crop((0, 0, im.width, max(8, int(im.height * 0.10))))
    strip = strip.transpose(Image.FLIP_TOP_BOTTOM).resize((im.width, add), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30))
    shade = np.linspace(1.0, 1.0, add) if bright else np.linspace(0.35, 0.9, add)
    arr = np.asarray(strip, np.float32) * shade[:, None, None].astype(np.float32)
    out = Image.new("RGB", (im.width, im.height + add))
    out.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (0, 0))
    out.paste(im, (0, add))
    seam = 70
    band = out.crop((0, add - seam, im.width, add + seam)).filter(ImageFilter.GaussianBlur(14))
    m = Image.fromarray((255 - np.abs(np.linspace(-255, 255, 2 * seam))).clip(0, 255).astype(np.uint8)[:, None].repeat(im.width, 1))
    out.paste(band, (0, add - seam), m)
    return out, add


# (key, file, crop_top, headroom, bright, flames[(u, v, r)], sway box (u0, v0, u1, v1) in source coords)
PHOTOS = {
    "room": (os.path.join(P_PE, "01-facial-bright.png"), 0.0, 0.40, True,
             [(0.178, 0.405, 0.03), (0.115, 0.447, 0.025), (0.955, 0.49, 0.03)], (0.0, 0.24, 0.42, 0.42)),
    "facial": (os.path.join(P_PE, "13-forehead-oil.png"), 0.0, 0.42, False, [(0.683, 0.21, 0.035)], None),
    "hand": (os.path.join(P_PE, "16-hand-cream.png"), 0.0, 0.42, False, [(0.715, 0.205, 0.035), (0.83, 0.12, 0.025)], None),
    "foot": (os.path.join(P_AMT, "reflexology-thumb.jpg"), 0.0, 0.40, False,
             [(0.16, 0.16, 0.05), (0.41, 0.15, 0.05), (0.65, 0.15, 0.05)], None),
    "rld": (os.path.join(P_AMT, "foot-hold.jpg"), 0.0, 0.25, False, [(0.73, 0.40, 0.04), (0.79, 0.40, 0.035)], None),
    "spanish": (os.path.join(P_AMT, "room-towels.jpg"), 0.0, 0.18, False,
                [(0.725, 0.385, 0.03), (0.86, 0.43, 0.03), (0.50, 0.43, 0.02)], (0.0, 0.0, 0.45, 0.45)),
    "package": (os.path.join(P_PE, "07-chanel-still-life.png"), 0.0, 0.32, False, [(0.79, 0.37, 0.04)], (0.10, 0.0, 0.62, 0.22)),
}


# extra clean-up per photo: blur AI-baked lettering / shirt prints; crop baked captions
CLEAN = {
    "room": {"interp": [(0.0, 0.005, 0.66, 0.245), (0.60, 0.005, 1.0, 0.193), (0.58, 0.188, 0.78, 0.216)]},
    "facial": {"blur": [((0.0, 0.0, 0.40, 0.17), 0.55)]},
    "hand": {"blur": [((0.0, 0.0, 0.40, 0.17), 0.55)]},
    "package": {"crop_bottom": 0.16},
}


def blur_box(im, box, keep):
    x0, y0, x1, y1 = [int(v) for v in (box[0] * im.width, box[1] * im.height, box[2] * im.width, box[3] * im.height)]
    reg = im.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(45 if keep < 1 else 140))
    reg = Image.fromarray(np.clip(np.asarray(reg, np.float32) * keep, 0, 255).astype(np.uint8))
    m = Image.new("L", reg.size, 0)
    m.paste(255, (30, 30, reg.width - 30, reg.height - 30))
    im = im.copy()
    im.paste(reg, (x0, y0), m.filter(ImageFilter.GaussianBlur(28)))
    return im


def interp_box(im, box):
    """Remove AI-baked lettering from a plain wall: rebuild each column by blending the clean
    rows just above and below the lettering, plus a little texture."""
    arr = np.asarray(im, np.float32).copy()
    x0, y0, x1, y1 = [int(v) for v in (box[0] * im.width, box[1] * im.height, box[2] * im.width, box[3] * im.height)]
    top = arr[max(0, y0 - 3):y0 + 3, x0:x1].mean(0)
    bot = arr[y1 - 3:y1 + 3, x0:x1].mean(0)
    top = np.asarray(Image.fromarray(top[None].astype(np.uint8)).resize((x1 - x0, 1)).filter(ImageFilter.GaussianBlur(6)), np.float32)[0]
    bot = np.asarray(Image.fromarray(bot[None].astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32)[0]
    u = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
    fill = top[None] * (1 - u) + bot[None] * u
    fill += np.random.default_rng(1).normal(0, 1.2, fill.shape)
    patch = Image.fromarray(np.clip(fill, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))
    m = Image.new("L", patch.size, 255).filter(ImageFilter.GaussianBlur(0))
    mm = np.ones((patch.height, patch.width), np.float32)
    fx = np.minimum(np.arange(patch.width), patch.width - 1 - np.arange(patch.width)) / 12.0
    mm *= np.clip(fx, 0, 1)[None, :]
    out = Image.fromarray(arr.astype(np.uint8))
    out.paste(patch, (x0, y0), Image.fromarray((mm * 255).astype(np.uint8)))
    return out


def build_photo(key):
    path, crop_top, head, bright, flames, sway = PHOTOS[key]
    im = Image.open(path).convert("RGB")
    for box, keep in CLEAN.get(key, {}).get("blur", []):
        im = blur_box(im, box, keep)
    for box in CLEAN.get(key, {}).get("interp", []):
        im = interp_box(im, box)
    if CLEAN.get(key, {}).get("crop_bottom"):
        im = im.crop((0, 0, im.width, int(im.height * (1 - CLEAN[key]["crop_bottom"]))))
    H0, W0 = im.height, im.width
    if crop_top:
        im = im.crop((0, int(H0 * crop_top), W0, H0))
    im, add = extend_top(im, head, bright) if head else (im, 0)
    k = max(W / im.width, H / im.height) * 1.3
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=2.5, percent=55, threshold=2))

    def to_big(u, v):  # source (0..1 of original) -> big pixel coords
        y = v * H0 - H0 * crop_top + add
        return u * W0 * k, y * k

    P = {"arr": np.asarray(big, np.float32), "w": big.width, "h": big.height}
    yy, xx = np.mgrid[0:big.height, 0:big.width].astype(np.float32)
    glow = np.zeros((big.height, big.width), np.float32)
    seeds = []
    for i, (u, v, r) in enumerate(flames):
        cx, cy = to_big(u, v)
        rr = r * W0 * k
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rr ** 2)))
        glow += g
        seeds.append(i * 1.7)
    P["glow"] = np.clip(glow, 0, 1)[..., None]
    P["flame_seed"] = seeds
    if sway:
        x0, y0 = to_big(sway[0], sway[1])
        x1, y1 = to_big(sway[2], sway[3])
        m = Image.new("L", (big.width, big.height), 0)
        ImageDraw.Draw(m).rectangle((x0, y0, x1, y1), fill=255)
        P["sway"] = np.asarray(m.filter(ImageFilter.GaussianBlur(60)), np.float32) / 255
    else:
        P["sway"] = None
    P["X"], P["Y"] = xx, yy
    return P


def bilinear(arr, sx, sy):
    h, w = arr.shape[:2]
    sx = np.clip(sx, 0, w - 1.001)
    sy = np.clip(sy, 0, h - 1.001)
    x0, y0 = sx.astype(np.int32), sy.astype(np.int32)
    fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
    return (arr[y0, x0] * (1 - fx) + arr[y0, x0 + 1] * fx) * (1 - fy) + (arr[y0 + 1, x0] * (1 - fx) + arr[y0 + 1, x0 + 1] * fx) * fy


def flicker(t, seed):
    return (0.55 * math.sin(7.3 * t + seed) + 0.3 * math.sin(13.1 * t + 2 * seed) + 0.25 * math.sin(3.1 * t + seed * 0.5)) / 1.1


def render_photo(P, t, u, v, z):
    """Crop window (u, v centre in 0..1 of the big plate, zoom z) with live sway + flame flicker."""
    s = max(W / P["w"], H / P["h"])
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * P["w"], cw / 2), P["w"] - cw / 2)
    cy = min(max(v * P["h"], ch / 2), P["h"] - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    if P["sway"] is not None:
        ix = np.clip(gx.astype(np.int32), 0, P["w"] - 1)
        iy = np.clip(gy.astype(np.int32), 0, P["h"] - 1)
        wgt = P["sway"][iy, ix]
        gx = gx + wgt * (4.0 * np.sin(1.1 * t + gy * 0.006) + 2.0 * np.sin(2.3 * t + gx * 0.01))
        gy = gy + wgt * (2.0 * np.sin(1.4 * t + gx * 0.007))
    img = bilinear(P["arr"], gx, gy)
    if P["flame_seed"]:
        ix = np.clip(gx.astype(np.int32), 0, P["w"] - 1)
        iy = np.clip(gy.astype(np.int32), 0, P["h"] - 1)
        g = P["glow"][iy, ix]
        f = sum(flicker(t, sd) for sd in P["flame_seed"]) / len(P["flame_seed"])
        img = img * (1 + g * 0.22 * f) + g * np.array([255, 190, 110], np.float32) * (0.10 + 0.06 * f)
    return img


# ---------------------------------------------------------------- timeline
# shots: (key, start, end, [(t, u, v, z), ...])
SHOTS = [
    ("room", 0.0, 11.2, [(0.0, 0.50, 0.44, 1.00), (6.8, 0.46, 0.45, 1.05), (11.2, 0.28, 0.46, 1.16)]),   # slow push toward the flowers
    ("facial", 10.9, 13.2, [(10.9, 0.50, 0.60, 1.04), (13.2, 0.50, 0.62, 1.10)]),
    ("hand", 12.9, 15.2, [(12.9, 0.44, 0.60, 1.06), (15.2, 0.56, 0.60, 1.06)]),
    ("foot", 14.9, 17.2, [(14.9, 0.50, 0.66, 1.10), (17.2, 0.52, 0.62, 1.02)]),
    ("rld", 16.9, 19.2, [(16.9, 0.42, 0.56, 1.08), (19.2, 0.58, 0.56, 1.08)]),
    ("spanish", 18.9, 21.2, [(18.9, 0.50, 0.58, 1.12), (21.2, 0.50, 0.56, 1.02)]),
    ("package", 20.9, 23.4, [(20.9, 0.50, 0.50, 1.02), (23.4, 0.50, 0.52, 1.10)]),
    ("room", 23.1, 30.0, [(23.1, 0.50, 0.44, 1.12), (30.0, 0.50, 0.42, 1.00)]),                         # gentle pull-back
]


def cam(keys, t):
    if t <= keys[0][0]:
        return keys[0][1:]
    for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            e = ease_in_out((t - t0) / (t1 - t0))
            return tuple(x + (y - x) * e for x, y in zip(a, b))
    return keys[-1][1:]


def shot_img(A, i, t):
    key, s, e, keys = SHOTS[i]
    return render_photo(A["P"][key], t, *cam(keys, t))


def background(t, A, soften=0.0):
    act = [i for i, (_, s, e, _) in enumerate(SHOTS) if s - 1e-3 <= t <= e]
    if len(act) >= 2:
        i1, i2 = act[-2], act[-1]
        p = (t - SHOTS[i2][1]) / max(1e-3, SHOTS[i1][2] - SHOTS[i2][1])
        a = Image.fromarray(np.clip(shot_img(A, i1, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12 * p))
        b = Image.fromarray(np.clip(shot_img(A, i2, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12 * (1 - p)))
        img = np.asarray(Image.blend(a, b, ease_in_out(p)), np.float32)
    else:
        img = shot_img(A, act[0], t)
        if soften > 0.01:
            img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9 * soften)), np.float32)
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, spd, ph, a) in A["motes"]:   # drifting golden motes
        mx = x + 20 * math.sin(t * 0.35 + ph)
        my = (y - spd * t) % H
        put(f, A["mote"], mx, my, a * (0.55 + 0.45 * math.sin(t * 1.4 + ph)))
    return f


def wash(f, y0, y1, color, a0, a1, a):
    if a <= 0:
        return
    h = int(y1 - y0)
    col = np.linspace(a0, a1, h, dtype=np.float32)[:, None] * a
    m = Image.fromarray((np.repeat(col, W, 1) * 255).astype(np.uint8), "L")
    s = Image.new("RGBA", (W, h), color + (0,))
    s.putalpha(m)
    f.alpha_composite(s, (0, int(y0)))


def build():
    A = {"P": {k: build_photo(k) for k in PHOTOS}}
    rng = np.random.default_rng(10)
    A["grain"] = [rng.normal(0, 2.4, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.22 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    m = Image.new("L", (26, 26), 0)
    ImageDraw.Draw(m).ellipse((9, 9, 17, 17), fill=230)
    mote = Image.new("RGBA", (26, 26), (255, 226, 170, 0))
    mote.putalpha(m.filter(ImageFilter.GaussianBlur(3)))
    A["mote"] = mote
    A["motes"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(6, 18), rng.uniform(0, 6.28), rng.uniform(0.3, 0.7)) for _ in range(28)]

    logo = Image.open(LOGO).convert("RGBA")
    A["logo"] = logo.resize((380, round(logo.height * 380 / logo.width)), Image.LANCZOS)
    A["logo_big"] = logo.resize((440, round(logo.height * 440 / logo.width)), Image.LANCZOS)
    A["sprig"] = sprig(220, (176, 132, 62))

    # bright scenes: deep green + deep gold, ivory halo for crispness
    A["your"] = Text("Your", brush(150), GREEN, halo=IVORY)
    A["saturday"] = Text("SATURDAY", gilda(150), GREEN, tracking=10, halo=IVORY)
    A["reset"] = Text("reset is waiting", brush(110), (150, 108, 44), halo=IVORY)
    A["day"] = Text(f"{DAY}", tenor(44), GREEN, tracking=20, halo=IVORY)
    A["date"] = Text(f"{MONTH} {DAYNUM}", gilda(140), GREEN, halo=IVORY)
    A["one"] = Text("ONE OPENING", tenor(38), GREEN, tracking=14, halo=IVORY)
    A["time"] = Text(TIME, gilda(290), "deepgold", shadow=GREEN)
    A["ampm"] = Text(AMPM, tenor(70), GREEN, tracking=4, halo=IVORY)
    # candlelit scenes: ivory + gold, soft dark shadow
    A["choose"] = Text("Choose your", brush(96), IVORY, shadow=NIGHT)
    A["treat"] = Text("TREATMENT", tenor(40), "gold", tracking=16, shadow=NIGHT)
    A["svc"] = [(Text(n, gilda(74), IVORY, shadow=NIGHT), Text(n, gilda(74), "gold", shadow=NIGHT),
                 Text(sub, tenor(28), "gold", tracking=8, shadow=NIGHT) if sub else None) for n, sub in SERVICES]
    # summary (bright)
    A["s_avail"] = Text("Available appointment", brush(104), GREEN, halo=IVORY)
    A["s_date"] = Text(f"Saturday, {MONTH} {DAYNUM}", gilda(70), GREEN, halo=IVORY)
    A["s_time"] = Text(f"{TIME} {AMPM}", gilda(130), "deepgold", shadow=GREEN)
    A["s_who"] = Text(f"with {THERAPIST}", tenor(40), GREEN, tracking=3, halo=IVORY)
    A["s_addr"] = Text(f"{CLINIC}  ·  {ADDRESS}", tenor(32), GREEN, tracking=2, halo=IVORY)
    A["s_cta"] = Text("DM TO BOOK", tenor(52), GREEN, tracking=16, halo=IVORY)
    return A


def frame_at(t, A):
    soften = math.exp(-((t - 7.6) / 0.45) ** 2)        # the time appears "from nowhere"
    f = background(t, A, soften)
    bright_scene = t < 11.0 or t > 23.3
    if bright_scene:
        wash(f, 0, 1000, IVORY, 0.78, 0.25, 1.0)
        wash(f, 1000, 1250, IVORY, 0.25, 0.0, 1.0)        # soft ivory light behind the type
    else:
        wash(f, 0, 1000, NIGHT, 0.72, 0.0, 1.0)

    # logo top-left on the bright opening (directly on the scene, no plate)
    if t < 11.0:
        p = ease_out(prog(t, 0.2, 0.8)) * (1 - ease_in_out(prog(t, 10.5, 0.4)))
        put(f, A["logo"], 70, 150 + 10 * (1 - p), p)

    # ---- hook 0–3.9
    if t < 4.0:
        a = 1 - ease_in_out(prog(t, 3.55, 0.4))
        write_on(f, A["your"], 150, 500, prog(t, 0.3, 0.8), a)
        sharp_in(f, A["saturday"], W / 2 - A["saturday"].adv / 2, 660, prog(t, 0.8, 0.8), a, scale_from=1.12)
        write_on(f, A["reset"], W / 2 - A["reset"].adv / 2 + 80, 790, prog(t, 1.5, 1.0), a)
        put(f, A["sprig"], W / 2 - 110, 830, ease_out(prog(t, 2.2, 0.6)) * a)

    # ---- date 3.8–7.0 : vertical scroll up into place
    if 3.8 <= t < 7.1:
        a = 1 - ease_in_out(prog(t, 6.7, 0.4))
        p = ease_out(prog(t, 3.9, 0.8))
        put_c(f, A["day"], 560, p * a, dy=60 * (1 - p))
        p = ease_out(prog(t, 4.2, 0.8))
        put_c(f, A["date"], 700, p * a, dy=80 * (1 - p))
        line(f, W / 2, 740, 260 * ease_in_out(prog(t, 4.9, 0.6)), (176, 132, 62), a)

    # ---- time hero 7.1–10.9 (camera keeps moving toward the flowers)
    if 7.1 <= t < 11.0:
        a = 1 - ease_in_out(prog(t, 10.55, 0.4))
        p = ease_out(prog(t, 7.25, 0.6))
        put_c(f, A["one"], 470, p * a, dy=14 * (1 - p))
        tm, am = A["time"], A["ampm"]
        tot = tm.adv + 24 + am.adv
        x = W / 2 - tot / 2
        sharp_in(f, tm, x, 760, prog(t, 7.45, 0.7), a)
        p = ease_out(prog(t, 8.0, 0.5))
        put_x(f, am, x + tm.adv + 24, 760, p * a, dx=-30 * (1 - p))
        line(f, W / 2, 810, 460 * ease_in_out(prog(t, 8.2, 0.8)), (176, 132, 62), a)

    # ---- services 11.0–23.3: vertical scrolling list, current item gold, one photo per service
    if 11.0 <= t < 23.4:
        a_all = ease_out(prog(t, 11.0, 0.5)) * (1 - ease_in_out(prog(t, 22.9, 0.4)))
        write_on(f, A["choose"], W / 2 - A["choose"].adv / 2, 380, prog(t, 11.1, 0.8), a_all)
        put_c(f, A["treat"], 440, a_all)
        step = 2.0
        pos = min(max((t - 11.4) / step, 0), len(SERVICES) - 1)
        idx_f = ease_in_out(pos - math.floor(pos)) + math.floor(pos) if pos < len(SERVICES) - 1 else pos
        for i, (dim, gold, sub) in enumerate(A["svc"]):
            y = 640 + (i - idx_f) * 130
            if y < 520 or y > 1000:
                continue
            dist = abs(i - idx_f)
            al = max(0.0, 1 - dist * 0.8) * a_all
            put_c(f, dim, y, al * (1 - max(0.0, 1 - dist)))
            put_c(f, gold, y, al * max(0.0, 1 - dist))
            if sub is not None and dist < 0.5:
                put_c(f, sub, y + 52, a_all * (1 - dist * 2))

    # ---- summary 23.3–30 (bright, pull-back)
    if t >= 23.3:
        p0 = ease_out(prog(t, 23.4, 0.7))
        lg = A["logo_big"]
        put(f, lg, (W - lg.width) / 2, 190 + 16 * (1 - p0), p0)
        y = 190 + lg.height + 100
        write_on(f, A["s_avail"], W / 2 - A["s_avail"].adv / 2, y, prog(t, 23.9, 0.9))
        p = ease_out(prog(t, 24.6, 0.5))
        put_c(f, A["s_date"], y + 85, p, dy=16 * (1 - p))
        sharp_in(f, A["s_time"], W / 2 - A["s_time"].adv / 2, y + 215, prog(t, 25.0, 0.6))
        line(f, W / 2, y + 245, 320 * ease_in_out(prog(t, 25.4, 0.6)), (176, 132, 62))
        p = ease_out(prog(t, 25.6, 0.5))
        put_c(f, A["s_who"], y + 305, p, dy=14 * (1 - p))
        put_c(f, A["s_addr"], y + 352, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 26.3, 0.6))
        put_c(f, A["s_cta"], y + 445, p, dy=16 * (1 - p))
        L = 300 * ease_in_out(prog(t, 26.6, 0.7)) * (0.85 + 0.15 * math.sin(max(0.0, t - 27.3) * 2.6))
        line(f, W / 2, y + 470, L, (176, 132, 62), p, thick=3)
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    out = np.zeros(n)

    def pad(freqs, start, end, gain):
        env = np.clip((t - start) / 2.4, 0, 1) * np.clip((end - t) / 2.4, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.35, 0.35):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.18 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.12 * np.sin(2 * np.pi * 0.1 * t)
        return gain * env * s / len(freqs)

    def bell(at, f0, g):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 1.6) * np.clip(tt / 0.008, 0, 1)
        out[idx] += g * env * (np.sin(2 * np.pi * f0 * tt) + 0.33 * np.sin(2 * np.pi * f0 * 2.76 * tt) + 0.1 * np.sin(2 * np.pi * f0 * 5.4 * tt))

    out += pad([164.81, 246.94, 311.13, 369.99, 415.30], -2, 12.0, 0.10)   # E maj9
    out += pad([138.59, 207.65, 246.94, 311.13, 329.63], 10.0, 24.0, 0.10)  # C# min9
    out += pad([164.81, 246.94, 311.13, 369.99, 415.30], 22.0, DURATION + 2, 0.10)
    for at, f0 in [(0.8, 830.6), (3.9, 987.8), (7.45, 1244.5), (11.4, 830.6), (13.4, 932.3), (15.4, 987.8),
                   (17.4, 1108.7), (19.4, 1244.5), (21.4, 1318.5), (25.0, 1244.5), (26.3, 987.8)]:
        bell(at, f0, 0.06)
    out *= np.clip((DURATION - t) / 1.5, 0, 1) * np.clip(t / 0.3, 0, 1)
    out = out / np.max(np.abs(out)) * 10 ** (-6 / 20)
    data = (np.stack([out, out], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def main(mode):
    os.makedirs(OUT_DIR, exist_ok=True)
    if mode == "stills":
        A = build()
        qc = os.path.join(OUT_DIR, "qc")
        os.makedirs(qc, exist_ok=True)
        for ts in [2.8, 5.8, 9.4, 12.2, 14.2, 16.2, 18.2, 20.2, 22.2, 28.5]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"sat-{ts:04.1f}s.png"))
        return
    tmp = os.path.join(OUT_DIR, f".{NAME}.render.mp4")
    wav = os.path.join(OUT_DIR, f".{NAME}.wav")
    synth_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4, initializer=_init) as pool:
        for buf in pool.imap(_render, range(int(DURATION * FPS)), chunksize=4):
            proc.stdin.write(buf)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    mp4 = os.path.join(OUT_DIR, f"{NAME}.mp4")
    os.replace(tmp, mp4)
    A = build()
    Image.fromarray(frame_at(2.8, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
