"""ADVANCED MASSAGE THERAPY — Available Appointments — Friday, October 16, 2026
(+ clinic closed Monday, October 12 — Thanksgiving).

Concept "After the Feast": a Thanksgiving-week story. Feet resting in a dark bed open the Reel
(rest day, clinic closed), then the week "opens" on Friday: the groove enters, and each
appointment time is revealed on its own treatment photo. Owner's 4 photos (reflex-map labels
removed from the foot photo by production/clean_foot_map.py).
Palette: charcoal-brown night + harvest copper-gold + ivory + a rust maple accent.
Type: Fraunces (soft editorial serif, roman + italic) + Urbanist (clean geometric sans).
Music (§46, new): 84 BPM groove in G minor -> B-flat, FM electric piano arpeggios, soft kick +
shaker entering on Friday, warm bass, breeze texture, marimba reveal accents.

  python3 production/oct16_amt_thanksgiving.py stills
  python3 production/oct16_amt_thanksgiving.py video
  python3 production/oct16_amt_thanksgiving.py poster
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
LOGO = os.path.join(ROOT, "brand", "locations", "advanced-massage-therapy-logo.png")
PH_DIR = os.path.join(ROOT, "brand", "photos", "amt-oct16")
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-16-amt-available-appointments"
W, H, FPS = 1080, 1920, 30
DURATION = 30.0

IVORY = (246, 238, 224)
NIGHT = (14, 10, 8)
RUST = (186, 84, 52)
COPPER_LINE = (204, 146, 94)

# ---------------------------------------------------------------- facts (owner-provided; verified)
CLINIC = "Advanced Massage Therapy"
ADDRESS = "2020 Corydon Ave, Winnipeg"
THERAPIST = "Zarina, RCRT"
CLOSED = ("MONDAY", "October 12")           # Thanksgiving Day in Canada, 2026 (second Monday of October)
OPEN_DAY, OPEN_DATE = "FRIDAY", "October 16"
TIMES = [("11:30", "a.m."), ("12:45", "p.m.")]
SERVICES = [  # exactly the owner's list for this post, in professional naming
    ("Foot & Hand Reflexology", ""),
    ("Facial Reflexology", "BERGMAN METHOD"),
    ("Reflexology Lymph Drainage", "RLD"),
    ("Spanish Massage", ""),
]


# ---------------------------------------------------------------- type
def fraunces(size, wght=500, italic=False, soft=100, opsz=144):
    f = ImageFont.truetype(os.path.join(FONTS, "Fraunces-Italic[SOFT,WONK,opsz,wght].ttf" if italic
                                        else "Fraunces[SOFT,WONK,opsz,wght].ttf"), size)
    f.set_variation_by_axes([opsz, wght, soft, 0])
    return f


def urban(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "Urbanist[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


GOLDS = {"copper": ((250, 218, 176), (216, 154, 100), (150, 92, 52))}


def metal(w, h, kind):
    top, mid, bot = [np.array(c, np.float32) for c in GOLDS[kind]]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    k1 = np.clip(y / 0.5, 0, 1)
    k2 = np.clip((y - 0.5) / 0.5, 0, 1)
    col = (top * (1 - k1) + mid * k1) * (1 - k2) + bot * k2
    col = np.broadcast_to(col, (h, w, 3)).copy()
    sheen = np.exp(-(((x - y * 0.35) - 0.3) / 0.1) ** 2) * 0.22
    return col * (1 - sheen) + np.array([255, 240, 214], np.float32) * sheen


class Text:
    def __init__(self, txt, fnt, fill, tracking=0, shadow=NIGHT):
        kw = {"features": ["lnum"]}
        asc, desc = fnt.getmetrics()
        pad = int(fnt.size * 0.4)
        width = (sum(fnt.getlength(c, **kw) for c in txt) + tracking * (len(txt) - 1)) if tracking else fnt.getlength(txt, **kw)
        size = (math.ceil(width) + 2 * pad, asc + desc + pad)
        mask = Image.new("L", size, 0)
        d = ImageDraw.Draw(mask)
        self.xs = []
        if tracking:
            x = pad
            for c in txt:
                self.xs.append(x)
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
        if shadow is not None:
            g = Image.new("RGBA", size, shadow + (0,))
            g.putalpha(mask.filter(ImageFilter.GaussianBlur(max(3, fnt.size // 12))).point(lambda v: int(v * 0.8)))
            g.alpha_composite(layer)
            layer = g
        self.img, self.asc, self.pad, self.adv = layer, asc, pad, width
        self.w, self.h = layer.size
        self.n = len(txt)


def fit(make, size, maxw):
    """Largest font size <= size whose rendered advance fits maxw."""
    t = make(size)
    while t.adv > maxw and size > 20:
        size -= 4
        t = make(size)
    return t


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


def sharp_in(f, tx, x, base, p, a=1.0, scale_from=1.0, blur=12):
    if p <= 0:
        return
    e = ease_out(p)
    img = tx.img
    s = scale_from + (1 - scale_from) * e
    if abs(s - 1) > 0.003:
        img = img.resize((int(tx.w * s), int(tx.h * s)), Image.LANCZOS)
    if e < 0.97:
        img = img.filter(ImageFilter.GaussianBlur(blur * (1 - e)))
    cx = x + tx.adv / 2
    put(f, img, cx - (tx.adv / 2 + tx.pad) * s, base - tx.asc * s, e * a)


def wipe(f, tx, x, base, p, a=1.0, soft=40):
    """Soft-edged left-to-right mask reveal."""
    if p <= 0:
        return
    e = ease_in_out(p)
    edge = -soft + (tx.w + soft) * e
    ramp = np.clip((edge - np.arange(tx.w, dtype=np.float32)) / soft, 0, 1)
    al = np.asarray(tx.img.getchannel("A"), np.float32) * ramp[None, :] * a
    img = tx.img.copy()
    img.putalpha(Image.fromarray(al.astype(np.uint8)))
    put(f, img, x - tx.pad, base - tx.asc)


def rise(f, tx, x, base, p, a=1.0):
    """Text rises out of an invisible baseline mask (vertical scroll reveal)."""
    if p <= 0:
        return
    e = ease_out(p)
    off = (1 - e) * tx.h * 0.9
    img = tx.img
    vis = img.crop((0, 0, tx.w, max(1, int(tx.h - off))))
    # the visible part is the top of the glyphs, drawn shifted down so it emerges from the baseline
    put(f, vis, x - tx.pad, base - tx.asc + off, a)


def letters(f, tx, x, base, t0, t, a=1.0, step=0.045, dur=0.35):
    """Letter-by-letter fade + small rise (only for tracked texts)."""
    for i, lx in enumerate(tx.xs):
        p = ease_out(prog(t, t0 + i * step, dur))
        if p <= 0:
            continue
        x0 = int(lx)
        x1 = int(tx.xs[i + 1]) if i + 1 < len(tx.xs) else tx.w
        put(f, tx.img.crop((x0, 0, x1, tx.h)), x - tx.pad + x0, base - tx.asc + 14 * (1 - p), p * a)


def line(f, x0, y, length, color, a=1.0, thick=2, centered=True):
    if length > 1 and a > 0:
        x = x0 - length / 2 if centered else x0
        f.alpha_composite(Image.new("RGBA", (int(length), thick), color + (int(255 * a),)), (int(x), int(y)))


def leaf_icon(size, color):
    """Fine-line autumn leaf: lobed outline, midrib and side veins (consistent 3 px line style)."""
    s = 4
    S = size * s
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    pts = []
    for k in range(361):
        th = math.radians(k)
        r = 0.30 + 0.10 * abs(math.cos(2.5 * th)) ** 0.6 + 0.06 * math.cos(th - math.pi / 2)
        pts.append((c + S * r * math.cos(th - math.pi / 2) * 0.95, c * 0.92 + S * r * math.sin(th - math.pi / 2) * 0.95 * -1))
    d.line(pts, fill=color + (255,), width=3 * s)
    d.line([(c, c * 0.92 + S * 0.36), (c, c * 0.92 - S * 0.30)], fill=color + (255,), width=3 * s)   # midrib
    d.line([(c, c * 0.92 + S * 0.36), (c - S * 0.03, S * 0.98)], fill=color + (255,), width=3 * s)    # stem
    for ang in (-50, 50, -20, 20):
        th = math.radians(ang)
        d.line([(c, c * 0.92 + S * 0.08), (c + S * 0.28 * math.sin(th), c * 0.92 + S * 0.08 - S * 0.28 * math.cos(th))],
               fill=color + (255,), width=2 * s)
    return im.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- living photos
def extend_top(im, frac):
    add = int(im.height * frac)
    strip = im.crop((0, 0, im.width, max(8, int(im.height * 0.10))))
    strip = strip.transpose(Image.FLIP_TOP_BOTTOM).resize((im.width, add), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30))
    shade = np.linspace(0.30, 0.9, add)
    arr = np.asarray(strip, np.float32) * shade[:, None, None].astype(np.float32)
    out = Image.new("RGB", (im.width, im.height + add))
    out.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (0, 0))
    out.paste(im, (0, add))
    seam = 60
    band = out.crop((0, add - seam, im.width, add + seam)).filter(ImageFilter.GaussianBlur(14))
    m = Image.fromarray((255 - np.abs(np.linspace(-255, 255, 2 * seam))).clip(0, 255).astype(np.uint8)[:, None].repeat(im.width, 1))
    out.paste(band, (0, add - seam), m)
    return out, add


# key: (file, headroom fraction, warm grade, sway box (u0, v0, u1, v1) in source coords or None)
PHOTOS = {
    "bed": ("feet-bed-dark.jpg", 0.78, 1.00, None),
    "foot": ("foot-thumb-clean.png", 0.55, 0.92, None),
    "jaw": ("facial-jaw.jpg", 0.30, 0.96, None),
    "temple": ("facial-temple.jpg", 0.45, 0.96, None),
}


def build_photo(key):
    fn, head, grade, _ = PHOTOS[key]
    im = Image.open(os.path.join(PH_DIR, fn)).convert("RGB")
    im, add = extend_top(im, head)
    k = max(W / im.width, H / im.height) * 1.25
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=2.5, percent=60, threshold=2))
    arr = np.asarray(big, np.float32)
    # harvest grade: warm the mids, deepen the shadows slightly
    arr = arr * np.array([1.03, 0.99, 0.93], np.float32) * grade
    yy, xx = np.mgrid[0:big.height, 0:big.width].astype(np.float32)
    return {"arr": arr, "w": big.width, "h": big.height, "X": xx, "Y": yy}


def bilinear(arr, sx, sy):
    h, w = arr.shape[:2]
    sx = np.clip(sx, 0, w - 1.001)
    sy = np.clip(sy, 0, h - 1.001)
    x0, y0 = sx.astype(np.int32), sy.astype(np.int32)
    fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
    return (arr[y0, x0] * (1 - fx) + arr[y0, x0 + 1] * fx) * (1 - fy) + (arr[y0 + 1, x0] * (1 - fx) + arr[y0 + 1, x0 + 1] * fx) * fy


def render_photo(P, t, u, v, z, breathe=0.0):
    """Crop window (centre u, v in 0..1 of the plate, zoom z). `breathe` adds a very slow,
    tiny vertical lift around the lower part of the frame (a resting body breathing)."""
    s = max(W / P["w"], H / P["h"])
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * P["w"], cw / 2), P["w"] - cw / 2)
    cy = min(max(v * P["h"], ch / 2), P["h"] - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    if breathe:
        wy = np.clip((np.linspace(0, 1, H, dtype=np.float32) - 0.45) / 0.55, 0, 1)[:, None]
        gy = gy + breathe * wy * 3.0 * math.sin(2 * math.pi * t / 4.2)
    return bilinear(P["arr"], gx, gy)


# ---------------------------------------------------------------- timeline
# shots: (key, start, end, [(t, u, v, z), ...], breathe)
SHOTS = [
    ("bed", 0.0, 8.2, [(0.0, 0.50, 0.60, 1.00), (8.2, 0.52, 0.62, 1.12)], 1.0),           # slow push-in, feet resting
    ("foot", 7.9, 15.8, [(7.9, 0.50, 0.55, 1.00), (10.9, 0.50, 0.57, 1.04), (15.8, 0.53, 0.58, 1.12)], 0.0),  # push toward the thumb
    ("jaw", 15.5, 20.2, [(15.5, 0.62, 0.50, 1.10), (20.2, 0.42, 0.50, 1.10)], 0.0),        # lateral slide
    ("temple", 19.9, 24.7, [(19.9, 0.52, 0.60, 1.18), (24.7, 0.50, 0.56, 1.02)], 0.0),     # pull-back
    ("bed", 24.4, 30.0, [(24.4, 0.50, 0.50, 1.06), (30.0, 0.50, 0.46, 0.96)], 1.0),        # gentle pull-back
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
    key, s, e, keys, br = SHOTS[i]
    return render_photo(A["P"][key], t, *cam(keys, t), breathe=br)


def background(t, A, soften=0.0):
    act = [i for i, (_, s, e, _, _) in enumerate(SHOTS) if s - 1e-3 <= t <= e]
    if len(act) >= 2:
        i1, i2 = act[-2], act[-1]
        p = (t - SHOTS[i2][1]) / max(1e-3, SHOTS[i1][2] - SHOTS[i2][1])
        a = Image.fromarray(np.clip(shot_img(A, i1, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14 * p))
        b = Image.fromarray(np.clip(shot_img(A, i2, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14 * (1 - p)))
        img = np.asarray(Image.blend(a, b, ease_in_out(p)), np.float32)
    else:
        img = shot_img(A, act[0], t)
        if soften > 0.01:
            img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10 * soften)), np.float32)
    # drifting warm light pool (slow, from upper left) + vignette + grain
    lx = W * (0.25 + 0.15 * math.sin(t * 0.21))
    ly = H * (0.30 + 0.06 * math.sin(t * 0.17 + 1))
    pool = np.exp(-(((A["xx"] - lx) / 520) ** 2 + ((A["yy"] - ly) / 640) ** 2))[..., None]
    img = img * A["vig"] * (1 + 0.10 * pool) + pool * np.array([40, 22, 6], np.float32) * 0.5 + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, spd, ph, a) in A["motes"]:   # dust motes catching the warm light
        mx = x + 18 * math.sin(t * 0.3 + ph)
        my = (y - spd * t) % H
        put(f, A["mote"], mx, my, a * (0.5 + 0.5 * math.sin(t * 1.3 + ph)))
    return f


def wash(f, y0, y1, color, a0, a1, a=1.0):
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
    rng = np.random.default_rng(16)
    A["grain"] = [rng.normal(0, 2.6, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["xx"], A["yy"] = xx, yy
    A["vig"] = (1 - 0.26 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    m = Image.new("L", (24, 24), 0)
    ImageDraw.Draw(m).ellipse((9, 9, 15, 15), fill=220)
    mote = Image.new("RGBA", (24, 24), (255, 214, 160, 0))
    mote.putalpha(m.filter(ImageFilter.GaussianBlur(3)))
    A["mote"] = mote
    A["motes"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(5, 14), rng.uniform(0, 6.28), rng.uniform(0.25, 0.6)) for _ in range(22)]

    logo = Image.open(LOGO).convert("RGBA")   # official file, untouched; placed directly on the dark scene
    A["logo"] = logo.resize((300, round(logo.height * 300 / logo.width)), Image.LANCZOS)
    A["logo_big"] = logo.resize((500, round(logo.height * 500 / logo.width)), Image.LANCZOS)
    A["leaf"] = leaf_icon(96, COPPER_LINE)
    A["leaf_s"] = leaf_icon(46, COPPER_LINE)

    # hook
    A["after"] = Text("After Thanksgiving weekend,", fraunces(62, 400, italic=True), IVORY)
    A["feet"] = fit(lambda s: Text("YOUR FEET", fraunces(s, 650), "copper", tracking=4), 200, 940)
    A["pause"] = Text("deserve a pause.", fraunces(104, 350, italic=True), IVORY)
    # closed Monday
    A["mon"] = Text(f"{CLOSED[0]}  ·  {CLOSED[1].upper()}", urban(40, 600), IVORY, tracking=10)
    A["closed"] = Text("Clinic closed", fraunces(140, 500), IVORY)
    A["happy"] = Text("Happy Thanksgiving", fraunces(86, 400, italic=True), "copper")
    # Friday date
    A["two"] = Text("JUST 2 OPENINGS", urban(36, 700), "copper", tracking=14)
    A["friday"] = Text(OPEN_DAY, fraunces(200, 600), IVORY, tracking=8)
    A["oct16"] = Text(OPEN_DATE.upper(), urban(62, 500), IVORY, tracking=22)
    # times
    A["lbl"] = Text(f"{OPEN_DAY}, {OPEN_DATE.upper()}", urban(36, 600), IVORY, tracking=10)
    A["t"] = [(Text(tm, fraunces(300, 600), "copper"), Text(ap, urban(76, 500), IVORY, tracking=2)) for tm, ap in TIMES]
    A["first"] = Text("first opening", fraunces(66, 400, italic=True), IVORY)
    A["second"] = Text("and one more", fraunces(66, 400, italic=True), IVORY)
    # services
    A["pick"] = Text("Pick your treatment", fraunces(96, 400, italic=True), "copper")
    A["svc"] = [(fit(lambda s, n=n: Text(n, fraunces(s, 500), IVORY), 68, 800),
                 Text(sub, urban(28, 700), "copper", tracking=8) if sub else None) for n, sub in SERVICES]
    # summary
    A["s_avail"] = Text("Available appointments", fraunces(84, 400, italic=True), "copper")
    A["s_day"] = Text(f"{OPEN_DAY}, {OPEN_DATE.upper()}", urban(44, 600), IVORY, tracking=10)
    A["s_t"] = [(Text(tm, fraunces(132, 600), "copper"), Text(ap, urban(46, 500), IVORY, tracking=2)) for tm, ap in TIMES]
    A["s_who"] = Text(f"with {THERAPIST}", urban(42, 500), IVORY, tracking=2)
    A["s_addr"] = Text(ADDRESS, urban(36, 500), IVORY, tracking=2)
    A["s_closed"] = Text(f"Closed Monday, {CLOSED[1]} — Happy Thanksgiving", fraunces(40, 400, italic=True), IVORY)
    A["s_cta"] = Text("DM TO BOOK", urban(56, 700), IVORY, tracking=16)
    return A


def frame_at(t, A):
    soften = math.exp(-((t - 11.45) / 0.4) ** 2) + math.exp(-((t - 16.15) / 0.35) ** 2) * 0.8   # times appear "from nowhere"
    f = background(t, A, soften)
    if t < 8.0 or t > 24.5:
        wash(f, 0, 1150, NIGHT, 0.55, 0.0)
    elif t < 15.7:
        wash(f, 0, 1050, NIGHT, 0.82, 0.0)          # bright foot photo: deep top shade for ivory type
        wash(f, 1500, H, NIGHT, 0.0, 0.35)
    elif t < 20.0:
        wash(f, 0, 950, NIGHT, 0.45, 0.0)
    else:
        wash(f, 0, 700, NIGHT, 0.85, 0.75)
        wash(f, 700, 1250, NIGHT, 0.75, 0.0)

    # logo top-centre through the opening (directly on the dark scene)
    if t < 8.0:
        p = ease_out(prog(t, 0.1, 0.8)) * (1 - ease_in_out(prog(t, 7.5, 0.4)))
        lg = A["logo"]
        put(f, lg, (W - lg.width) / 2, 96 + 10 * (1 - p), p)

    # ---- hook 0–3.6
    if t < 3.8:
        a = 1 - ease_in_out(prog(t, 3.3, 0.4))
        wipe(f, A["after"], W / 2 - A["after"].adv / 2, 470, prog(t, 0.15, 0.8), a)
        sharp_in(f, A["feet"], W / 2 - A["feet"].adv / 2, 660, prog(t, 0.75, 0.7), a, scale_from=1.12)
        wipe(f, A["pause"], W / 2 - A["pause"].adv / 2, 790, prog(t, 1.45, 0.9), a)

    # ---- closed Monday 3.7–8.0
    if 3.6 <= t < 8.1:
        a = 1 - ease_in_out(prog(t, 7.55, 0.4))
        p = ease_out(prog(t, 3.7, 0.6))
        put(f, A["leaf"], W / 2 - 48, 330 + 14 * (1 - p), p * a)
        letters(f, A["mon"], W / 2 - A["mon"].adv / 2, 520, 3.85, t, a, step=0.03)
        wipe(f, A["closed"], W / 2 - A["closed"].adv / 2, 690, prog(t, 4.35, 0.9), a)
        line(f, W / 2, 730, 380 * ease_in_out(prog(t, 5.0, 0.7)), COPPER_LINE, a)
        p = ease_out(prog(t, 5.4, 0.7))
        put_c(f, A["happy"], 830, p * a, dy=20 * (1 - p))

    # ---- Friday date 8.2–11.2 (groove enters on the bar at 8.57)
    if 8.2 <= t < 11.4:
        a = 1 - ease_in_out(prog(t, 10.95, 0.35))
        letters(f, A["two"], W / 2 - A["two"].adv / 2, 400, 8.25, t, a, step=0.025)
        rise(f, A["friday"], W / 2 - A["friday"].adv / 2, 640, prog(t, 8.55, 0.7), a)
        line(f, W / 2, 680, 520 * ease_in_out(prog(t, 8.9, 0.6)), COPPER_LINE, a)
        letters(f, A["oct16"], W / 2 - A["oct16"].adv / 2, 770, 9.05, t, a, step=0.04)

    # ---- time 1: 11:30 a.m. — camera pushes toward the thumb technique (11.3–15.6)
    if 11.3 <= t < 15.8:
        a = 1 - ease_in_out(prog(t, 15.3, 0.4))
        p = ease_out(prog(t, 11.3, 0.5))
        put_c(f, A["first"], 250, p * a, dy=12 * (1 - p))
        tm, ap = A["t"][0]
        tot = tm.adv + 22 + ap.adv
        x = W / 2 - tot / 2
        sharp_in(f, tm, x, 520, prog(t, 11.45, 0.7), a, blur=16)
        p = ease_out(prog(t, 11.95, 0.5))
        put_x(f, ap, x + tm.adv + 22, 520, p * a, dx=-26 * (1 - p))
        line(f, W / 2, 560, 520 * ease_in_out(prog(t, 12.2, 0.8)), COPPER_LINE, a)
        p = ease_out(prog(t, 12.5, 0.6))
        put_c(f, A["lbl"], 615, p * a, dy=16 * (1 - p))

    # ---- time 2: 12:45 p.m. — lateral slide over the facial photo, left-aligned type (15.9–20.0)
    if 15.8 <= t < 20.1:
        a = 1 - ease_in_out(prog(t, 19.6, 0.4))
        X = 96
        p = ease_out(prog(t, 15.9, 0.5))
        put_x(f, A["lbl"], X, 330, p * a, dx=-30 * (1 - p))
        wipe(f, A["second"], X, 430, prog(t, 16.0, 0.6), a)
        tm, ap = A["t"][1]
        p = prog(t, 16.15, 0.7)
        sharp_in(f, tm, X - 40 * (1 - ease_out(p)), 700, p, a, blur=16)
        p = ease_out(prog(t, 16.6, 0.5))
        put_x(f, ap, X + 8, 800, p * a, dy=18 * (1 - p))
        line(f, X, 838, 300 * ease_in_out(prog(t, 16.9, 0.7)), COPPER_LINE, a, centered=False)

    # ---- services 20.1–24.6: header, then each line wipes in under the previous one
    if 20.0 <= t < 24.8:
        a = ease_out(prog(t, 20.1, 0.4)) * (1 - ease_in_out(prog(t, 24.25, 0.4)))
        X = 120
        wipe(f, A["pick"], X - 10, 300, prog(t, 20.15, 0.7), a)
        y = 440
        for i, (nm, sub) in enumerate(A["svc"]):
            t0 = 20.6 + i * 0.7
            p = ease_out(prog(t, t0, 0.35))
            put(f, A["leaf_s"], X - 64, y - 44 + 10 * (1 - p), p * a * 0.95)
            wipe(f, nm, X, y, prog(t, t0, 0.6), a)
            if sub is not None:
                letters(f, sub, X + 2, y + 44, t0 + 0.35, t, a, step=0.02)
                y += 150
            else:
                y += 112

    # ---- summary 24.6–30 (feet resting again, pull-back)
    if t >= 24.6:
        p0 = ease_out(prog(t, 24.65, 0.7))
        wash(f, 0, 1050, NIGHT, 0.25, 0.45, p0)
        wash(f, 1050, 1450, NIGHT, 0.45, 0.0, p0)
        lg = A["logo_big"]
        put(f, lg, (W - lg.width) / 2, 60 + 14 * (1 - p0), p0)
        y = 60 + lg.height + 100
        wipe(f, A["s_avail"], W / 2 - A["s_avail"].adv / 2, y, prog(t, 25.0, 0.8))
        letters(f, A["s_day"], W / 2 - A["s_day"].adv / 2, y + 80, 25.45, t, step=0.02)
        for k, (tm, ap) in enumerate(A["s_t"]):
            tot = tm.adv + 16 + ap.adv
            x = W / 2 - tot / 2
            yy = y + 225 + k * 135
            sharp_in(f, tm, x, yy, prog(t, 25.9 + k * 0.35, 0.6))
            p = ease_out(prog(t, 26.2 + k * 0.35, 0.4))
            put_x(f, ap, x + tm.adv + 16, yy, p, dx=-20 * (1 - p))
        line(f, W / 2, y + 400, 360 * ease_in_out(prog(t, 26.8, 0.6)), COPPER_LINE)
        p = ease_out(prog(t, 27.0, 0.5))
        put_c(f, A["s_who"], y + 465, p, dy=14 * (1 - p))
        put_c(f, A["s_addr"], y + 518, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 27.3, 0.5))
        put_c(f, A["s_closed"], y + 578, p * 0.92, dy=14 * (1 - p))
        p = ease_out(prog(t, 27.7, 0.6))
        put_c(f, A["s_cta"], y + 665, p, dy=16 * (1 - p))
        L = 330 * ease_in_out(prog(t, 28.0, 0.7)) * (0.86 + 0.14 * math.sin(max(0.0, t - 28.7) * 2.6))
        line(f, W / 2, y + 691, L, COPPER_LINE, p, thick=3)
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


# ---------------------------------------------------------------- music (§46: new direction)
BPM = 84
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORDS = [  # (bass root Hz, electric-piano voicing Hz)
    (98.00, [196.00, 233.08, 293.66, 349.23, 440.00]),    # Gm9
    (77.78, [155.56, 196.00, 233.08, 293.66, 392.00]),    # Ebmaj7
    (116.54, [174.61, 233.08, 261.63, 293.66, 349.23]),   # Bb add9
    (110.00, [220.00, 261.63, 349.23, 392.00, 440.00]),   # F/A (add9)
]
SONG = [0, 1, 2, 3, 0, 1, 2, 3, 1, 3, 2]                  # ends on B-flat (warm resolve)
MARIMBA = [(0.75, 587.33), (3.7, 698.46), (4.35, 587.33), (8.57, 783.99), (11.45, 932.33), (16.15, 1046.50),
           (20.6, 587.33), (21.3, 698.46), (22.0, 783.99), (22.7, 932.33), (25.9, 783.99), (26.25, 932.33), (27.7, 1174.66)]


def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(84)
    ep = np.zeros(n)
    bass = np.zeros(n)
    drums = np.zeros(n)

    def add(buf, at, sig):
        i = int(at * sr)
        if i >= n:
            return
        m = min(len(sig), n - i)
        buf[i:i + m] += sig[:m]

    def ep_note(f0, vel, dur=1.6):
        tt = np.arange(int(dur * sr)) / sr
        idx = 1.6 * np.exp(-tt * 7) + 0.25
        env = np.exp(-tt * 2.0) * np.clip(tt / 0.004, 0, 1)
        tine = np.sin(2 * np.pi * f0 * tt + idx * np.sin(2 * np.pi * f0 * tt))
        bark = 0.25 * np.sin(2 * np.pi * f0 * 14 * tt) * np.exp(-tt * 40)
        return vel * env * (tine + bark)

    def kick():
        tt = np.arange(int(0.45 * sr)) / sr
        fr = 48 + 70 * np.exp(-tt * 26)
        ph = 2 * np.pi * np.cumsum(fr) / sr
        return np.sin(ph) * np.exp(-tt * 8.5) * np.clip(tt / 0.002, 0, 1)

    def shaker():
        L = int(0.09 * sr)
        x = rng.normal(0, 1, L)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(L, 1 / sr)
        X *= np.clip((fr - 5000) / 3000, 0, 1)
        y = np.fft.irfft(X, L)
        tt = np.arange(L) / sr
        return y / (np.abs(y).max() + 1e-9) * np.exp(-tt * 45) * np.clip(tt / 0.006, 0, 1)

    K = kick()
    for b, ci in enumerate(SONG):
        t0 = b * BAR
        root, voi = CHORDS[ci]
        # bass: root on 1, fifth-ish pickup on the "and" of 3
        tt = np.arange(int(BAR * sr)) / sr
        benv = np.clip(tt / 0.02, 0, 1) * np.exp(-tt * 0.9)
        add(bass, t0, benv * (np.sin(2 * np.pi * root * tt) + 0.25 * np.sin(2 * np.pi * 2 * root * tt)))
        # electric piano: soft chord on 1, then an eighth-note arpeggio
        for f0 in voi:
            add(ep, t0, ep_note(f0, 0.10))
        for k, idx in enumerate([0, 2, 1, 3, 2, 4, 3, 2]):
            add(ep, t0 + k * BEAT / 2 + (0.012 if k % 2 else 0), ep_note(voi[idx], 0.16 if k % 2 == 0 else 0.11, 1.2))
        # groove from Friday (bar 3) onward: kick on 1 and 3, shaker on the off-beats
        if 3 <= b:
            for beat in (0, 2):
                add(drums, t0 + beat * BEAT, 0.55 * K)
            for k in range(8):
                add(drums, t0 + k * BEAT / 2 + BEAT / 4, (0.07 if k % 2 else 0.045) * shaker())
    # breeze texture: band-limited noise with slow swells
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    X *= np.exp(-((np.log(fr + 1) - np.log(600)) / 0.8) ** 2)
    breeze = np.fft.irfft(X, n)
    breeze = breeze / np.abs(breeze).max() * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t + 1)) * 0.06

    mar = np.zeros(n)
    for at, f0 in MARIMBA:
        tt = np.arange(int(1.4 * sr)) / sr
        env = np.exp(-tt * 6) * np.clip(tt / 0.002, 0, 1)
        add(mar, at, env * (np.sin(2 * np.pi * f0 * tt) + 0.22 * np.sin(2 * np.pi * f0 * 3.93 * tt) * np.exp(-tt * 14)))

    out = 0.55 * ep + 0.32 * bass + 0.42 * drums + breeze + 0.30 * mar
    # gentle stereo: EP slightly left/right alternating, drums centre
    left = out + 0.06 * np.roll(ep, int(0.011 * sr))
    right = out + 0.06 * np.roll(ep, int(0.017 * sr))
    st = np.stack([left, right], 1)
    st *= (np.clip((DURATION - t) / 2.0, 0, 1) * np.clip(t / 0.25, 0, 1))[:, None]
    st = st / np.max(np.abs(st)) * 10 ** (-6 / 20)
    data = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def poster(path, PW=1080, PH=1350):
    """Static 4:5 feed post: feet resting in the dark bed, all information in the dark headroom."""
    im = Image.open(os.path.join(PH_DIR, "feet-bed-dark.jpg")).convert("RGB")
    im, add = extend_top(im, 0.95)
    k = PW / im.width
    big = im.resize((PW, int(im.height * k)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.5, percent=60, threshold=2))
    big = big.crop((0, big.height - PH - 170, PW, big.height - 170))   # feet sit lower, heels run off the edge
    arr = np.asarray(big, np.float32) * np.array([1.03, 0.99, 0.93], np.float32)
    yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
    arr *= (1 - 0.26 * np.clip(((xx - PW / 2) / PW) ** 2 * 2.4 + ((yy - PH / 2) / PH) ** 2 * 2.0, 0, 1))[..., None]
    pool = np.exp(-(((xx - PW * 0.3) / 520) ** 2 + ((yy - PH * 0.25) / 600) ** 2))[..., None]
    arr = arr * (1 + 0.08 * pool) + pool * np.array([40, 22, 6], np.float32) * 0.5
    f = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    g = np.linspace(0.45, 0.0, 760, dtype=np.float32)[:, None].repeat(PW, 1)
    sh = Image.new("RGBA", (PW, 760), NIGHT + (0,))
    sh.putalpha(Image.fromarray((g * 255).astype(np.uint8)))
    f.alpha_composite(sh, (0, 0))
    logo = Image.open(LOGO).convert("RGBA")
    lg = logo.resize((300, round(logo.height * 300 / logo.width)), Image.LANCZOS)
    f.alpha_composite(lg, ((PW - lg.width) // 2, 34))
    cx = PW / 2

    def c(tx, base):
        f.alpha_composite(tx.img, (int(cx - tx.adv / 2 - tx.pad), int(base - tx.asc)))
    y = 34 + lg.height + 80
    c(Text("Available appointments", fraunces(70, 400, italic=True), "copper"), y)
    c(Text(f"{OPEN_DAY}, {OPEN_DATE.upper()}", urban(38, 600), IVORY, tracking=10), y + 64)
    parts = [(Text(tm, fraunces(112, 600), "copper"), Text(ap, urban(40, 500), IVORY, tracking=2)) for tm, ap in TIMES]
    gap = 70
    tot = sum(tm.adv + 12 + ap.adv for tm, ap in parts) + gap
    x = cx - tot / 2
    for tm, ap in parts:
        f.alpha_composite(tm.img, (int(x - tm.pad), int(y + 190 - tm.asc)))
        f.alpha_composite(ap.img, (int(x + tm.adv + 12 - ap.pad), int(y + 190 - ap.asc)))
        x += tm.adv + 12 + ap.adv + gap
    d = ImageDraw.Draw(f)
    d.line([(cx - 190, y + 222), (cx + 190, y + 222)], fill=COPPER_LINE + (255,), width=2)
    c(Text(f"with {THERAPIST}  ·  {ADDRESS}", urban(31, 500), IVORY, tracking=1), y + 272)
    c(Text(f"Closed Monday, {CLOSED[1]} — Happy Thanksgiving", fraunces(34, 400, italic=True), IVORY), y + 318)
    c(Text("DM TO BOOK", urban(44, 700), IVORY, tracking=14), y + 392)
    d.line([(cx - 130, y + 410), (cx + 130, y + 410)], fill=COPPER_LINE + (255,), width=3)
    f.convert("RGB").save(path, quality=95)


def main(mode):
    os.makedirs(OUT_DIR, exist_ok=True)
    if mode == "poster":
        poster(os.path.join(OUT_DIR, f"{NAME}-post-4x5.jpg"))
        return
    if mode == "stills":
        A = build()
        qc = os.path.join(OUT_DIR, "qc")
        os.makedirs(qc, exist_ok=True)
        ts = [float(x) for x in sys.argv[2:]] or [2.9, 6.6, 10.4, 14.0, 18.6, 23.6, 29.0]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(qc, f"amt16-{s:04.1f}s.png"))
        return
    if mode == "audio":
        synth_audio(os.path.join(OUT_DIR, "qc", "amt16.wav"))
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
    Image.fromarray(frame_at(2.9, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    Image.fromarray(frame_at(29.5, A)).save(os.path.join(OUT_DIR, f"{NAME}-story.jpg"), quality=93)
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
