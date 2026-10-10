"""THE PURE ESCAPE — Educational Reel: Reflexology Lymph Drainage (RLD) — v2 (rules §47)
Female voiceover (Kokoro TTS, production/rld_voice.py) over light music; realistic photo feet
with a living reflex map (pulsing points, numbers drawing on, flowing lines, skin presses);
blurred treatment / room backgrounds that move (candle flicker, plant sway, sunbeam, drift).

Palette: ivory + aqua glow + champagne gold over warm photography. Type: Newsreader (editorial
serif, roman + italic) + Mulish (clean sans). Music (§46, new): 66 BPM, D minor -> F, harp
arpeggios (Karplus-Strong), cello drone, flowing-water texture, soft glass bells on the presses;
music ducks under the voice.

  python3 production/rld_voice.py          # voice lines -> production/rld_audio/
  python3 production/rld_reel_v2.py stills [t ...]
  python3 production/rld_reel_v2.py video
"""
import json
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oct16_amt_thanksgiving as base  # noqa: E402
from oct10_pe_saturday import extend_top, flicker  # noqa: E402
from oct15_pe_thu_sat import ks  # noqa: E402
from oct16_amt_thanksgiving import (Text, bilinear, ease_in_out, ease_out, letters, line, prog, put,  # noqa: E402
                                    put_c, put_x, rise, sharp_in, wash, wipe)

ROOT = base.ROOT
FONTS = base.FONTS
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
PH = os.path.join(ROOT, "brand", "photos")
AUD = os.path.join(ROOT, "production", "rld_audio")
OUT_DIR = base.OUT_DIR
NAME = "2026-10-rld-reflexology-lymph-drainage-v2"
W, H, FPS = 1080, 1920, 30

IVORY = (250, 246, 238)
AQUA = (132, 230, 216)
CHAR = (36, 32, 30)
NIGHT = (10, 9, 8)
GOLD_LINE = (220, 188, 132)
base.GOLDS["champ"] = ((250, 234, 204), (222, 192, 140), (164, 128, 80))

# ---------------------------------------------------------------- timing from the voice
LINES = [l for l in __import__("rld_voice").LINES]
_d = json.load(open(os.path.join(AUD, "durations.json")))
DUR_L = _d["durations"]
LEAD, GAP, TAIL = 0.35, 0.32, 1.6
STARTS = []
_t = LEAD
for d in DUR_L:
    STARTS.append(_t)
    _t += d + GAP
DURATION = round(_t - GAP + TAIL, 2)


def wt(i, word):
    """Approximate time when `word` is spoken in line i (proportional to character position)."""
    s = LINES[i]
    k = s.lower().find(word.lower())
    k = max(0, k)
    return STARTS[i] + DUR_L[i] * (k / max(1, len(s))) * 0.97


def L(i):          # line start / end
    return STARTS[i], STARTS[i] + DUR_L[i]


def news(size, wght=500, italic=False, opsz=72):
    f = ImageFont.truetype(os.path.join(FONTS, "Newsreader-Italic[opsz,wght].ttf" if italic else "Newsreader[opsz,wght].ttf"), size)
    f.set_variation_by_axes([opsz, wght])
    return f


def mul(size, wght=600):
    f = ImageFont.truetype(os.path.join(FONTS, "Mulish[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def T(txt, fnt, fill, tracking=0, dark=True):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT if dark else None)


# ---------------------------------------------------------------- photos
# key: (path, headroom, blur, grade, flames[(u,v,r)], sway[(u0,v0,u1,v1)])
PHOTOS = {
    "soles": (os.path.join(PH, "rld", "soles-pair.png"), 0.30, 0, 1.0,
              [(0.83, 0.083, 0.035), (0.50, 0.50, 0.03), (0.935, 0.54, 0.03)], [(0.0, 0.0, 0.42, 0.28)]),
    "thumb": (os.path.join(PH, "amt-oct16", "foot-thumb-clean.png"), 0.55, 0, 0.95, [], []),
    "workblur": (os.path.join(PH, "amt", "reflexology-thumb.jpg"), 0.15, 9, 0.85,
                 [(0.10, 0.11, 0.04), (0.24, 0.11, 0.04), (0.37, 0.11, 0.04)], []),
    "candles": (os.path.join(PH, "pe-oct13", "candles-towels.jpg"), 0.10, 0, 0.92,
                [(0.730, 0.612, 0.022), (0.948, 0.678, 0.022), (0.876, 0.745, 0.020), (0.460, 0.818, 0.020)],
                [(0.50, 0.0, 1.0, 0.37)]),
    "sun": (os.path.join(PH, "pe-oct15", "foot-sunlit.jpg"), 0.45, 3, 1.0, [], []),
    "hand": (os.path.join(PH, "pe-oct15", "hand-thumb-walk.jpg"), 0.70, 0, 0.92, [], []),
    "room": (os.path.join(PH, "amt", "room-towels.jpg"), 0.05, 7, 0.80,
             [(0.725, 0.385, 0.03), (0.86, 0.43, 0.03), (0.50, 0.43, 0.02)], [(0.0, 0.0, 0.45, 0.45)]),
}
# reflex map points in source-pixel coords of soles-pair.png (941 x 1672). Viewer's left = client's RIGHT foot.
SOLE_PTS = {
    "toes": [(255, 428), (172, 455), (114, 490), (99, 504), (686, 428), (770, 455), (828, 492), (842, 503)],
    "thymus": [(392, 565), (548, 565)],
    "diaphragm": [[(28, 690), (120, 704), (230, 708), (340, 694), (450, 662)], [(491, 662), (601, 694), (711, 708), (821, 704), (913, 690)]],
    "spleen": [(842, 790)],
    "kidney": [(255, 890), (686, 890)],
}
HAND_PTS = {"fingers": [(286, 338), (338, 352)], "back": [(320, 470)], "wrist": [(545, 585)]}   # hand-thumb-walk.jpg 736 x 736


def build_photo(key):
    path, head, blur, grade, flames, sways = PHOTOS[key]
    im = Image.open(path).convert("RGB")
    H0, W0 = im.height, im.width
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    im, add = extend_top(im, head, False) if head else (im, 0)
    if head:
        arr = np.asarray(im, np.float32).copy()
        g = np.clip(1 - np.arange(add + 50, dtype=np.float32) / (add + 50), 0, 1) ** 0.8
        arr[:add + 50] = arr[:add + 50] * (1 - 0.55 * g[:, None, None]) + np.array([20, 16, 13], np.float32) * 0.55 * g[:, None, None]
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    k = max(W / im.width, H / im.height) * 1.12
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    if not blur:
        big = big.filter(ImageFilter.UnsharpMask(radius=2.2, percent=60, threshold=2))
    h, w = big.height, big.width
    arr = np.asarray(big, np.float32) * np.array([1.02, 1.0, 0.97], np.float32) * grade

    def to_big(x, y):          # source pixel -> plate pixel
        return x * k, (y + add) * k
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    glow = np.zeros((h, w), np.float32)
    for (u, v, r) in flames:
        cx, cy = to_big(u * W0, v * H0)
        rr = r * W0 * k
        glow += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rr ** 2)))
    sway = np.zeros((h, w), np.float32)
    for (u0, v0, u1, v1) in sways:
        x0, y0 = to_big(u0 * W0, v0 * H0)
        x1, y1 = to_big(u1 * W0, v1 * H0)
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).rectangle((x0, y0, x1, y1), fill=255)
        sway += np.asarray(m.filter(ImageFilter.GaussianBlur(50)), np.float32) / 255
    return {"arr": arr, "w": w, "h": h, "k": k, "add": add, "glow": np.clip(glow, 0, 1), "nfl": len(flames),
            "sway": sway if sways else None, "to_big": to_big}


def window(P, u, v, z):
    s = max(W / P["w"], H / P["h"])
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * P["w"], cw / 2), P["w"] - cw / 2)
    cy = min(max(v * P["h"], ch / 2), P["h"] - ch / 2)
    return cx - cw / 2, cy - ch / 2, cw / W        # x0, y0, plate pixels per screen pixel


def to_screen(P, cam_, x, y):
    """Source-photo pixel -> screen pixel for the current camera."""
    x0, y0, sc = window(P, *cam_)
    bx, by = P["to_big"](x, y)
    return (bx - x0) / sc, (by - y0) / sc


def render_photo(P, t, cam_, presses=()):
    x0, y0, sc = window(P, *cam_)
    gx = x0 + np.arange(W, dtype=np.float32)[None, :].repeat(H, 0) * sc
    gy = y0 + np.arange(H, dtype=np.float32)[:, None].repeat(W, 1) * sc
    ix = np.clip(gx.astype(np.int32), 0, P["w"] - 1)
    iy = np.clip(gy.astype(np.int32), 0, P["h"] - 1)
    if P["sway"] is not None:
        wgt = P["sway"][iy, ix]
        gx = gx + wgt * (4.0 * np.sin(1.0 * t + gy * 0.005) + 1.8 * np.sin(2.1 * t + gx * 0.009))
        gy = gy + wgt * (2.0 * np.sin(1.3 * t + gx * 0.006))
    shade = None
    for (sx, sy, amt, rad) in presses:             # skin press: pinch toward the contact point + soft shade
        if amt <= 0.01:
            continue
        bx, by = x0 + sx * sc, y0 + sy * sc
        dx, dy = gx - bx, gy - by
        r2 = (dx * dx + dy * dy) / (rad * rad)
        f = np.exp(-r2) * amt
        gx = gx + dx * f * 0.22
        gy = gy + dy * f * 0.22
        sh = 1 - 0.10 * f
        shade = sh if shade is None else shade * sh
    img = bilinear(P["arr"], gx, gy)
    if shade is not None:
        img *= shade[..., None]
    if P["nfl"]:
        g = P["glow"][iy, ix][..., None]
        fl = sum(flicker(t, 1.7 * i) for i in range(P["nfl"])) / P["nfl"]
        img = img * (1 + g * 0.24 * fl) + g * np.array([255, 186, 104], np.float32) * (0.10 + 0.07 * fl)
    return img


# ---------------------------------------------------------------- shots
def build_shots():
    s = STARTS
    e = [a + d for a, d in zip(STARTS, DUR_L)]
    return [
        ("soles", 0.0, e[0] + 0.3, [(0.0, 0.50, 0.30, 1.00), (e[0] + 0.3, 0.50, 0.34, 1.05)]),
        ("workblur", s[1] - 0.3, e[1] + 0.3, [(s[1] - 0.3, 0.50, 0.55, 1.05), (e[1] + 0.3, 0.46, 0.50, 1.14)]),
        ("thumb", s[2] - 0.3, e[2] + 0.3, [(s[2] - 0.3, 0.50, 0.60, 1.05), (e[2] + 0.3, 0.53, 0.66, 1.16)]),
        ("candles", s[3] - 0.3, e[3] + 0.3, [(s[3] - 0.3, 0.52, 0.46, 1.04), (e[3] + 0.3, 0.62, 0.52, 1.16)]),
        ("sun", s[4] - 0.3, e[4] + 0.3, [(s[4] - 0.3, 0.46, 0.56, 1.06), (e[4] + 0.3, 0.56, 0.56, 1.06)]),
        ("soles", s[5] - 0.3, e[5] + 0.4, [(s[5] - 0.3, 0.50, 0.62, 1.00), (e[5] + 0.4, 0.50, 0.63, 1.04)]),
        ("hand", s[6] - 0.3, e[6] + 0.3, [(s[6] - 0.3, 0.50, 0.66, 1.04), (e[6] + 0.3, 0.52, 0.68, 1.10)]),
        ("room", s[7] - 0.3, e[7] + 0.3, [(s[7] - 0.3, 0.50, 0.50, 1.10), (e[7] + 0.3, 0.50, 0.48, 1.00)]),
        ("candles", s[8] - 0.3, DURATION, [(s[8] - 0.3, 0.50, 0.40, 1.10), (DURATION, 0.50, 0.36, 1.00)]),
    ]


SHOTS = build_shots()


def cam(keys, t):
    if t <= keys[0][0]:
        return keys[0][1:]
    for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            e = ease_in_out((t - t0) / (t1 - t0))
            return tuple(x + (y - x) * e for x, y in zip(a, b))
    return keys[-1][1:]


def active(t):
    return [i for i, (_, s, e, _) in enumerate(SHOTS) if s - 1e-3 <= t <= e]


def presses_for(i, t, A):
    """Press (dimple) list in plate pixels for shot i at time t."""
    key = SHOTS[i][0]
    P = A["P"][key]
    out = []
    if key == "thumb":      # the thumb 'walks': three presses along a short path under the thumb tip
        for j, (x, y) in enumerate([(420, 455), (440, 480), (455, 505)]):
            ph = (t * 1.1 + j * 0.33) % 1.0
            amt = math.sin(ph * math.pi) ** 2
            bx, by = P["to_big"](x, y)
            out.append((bx - window(P, *cam(SHOTS[i][3], t))[0], by - window(P, *cam(SHOTS[i][3], t))[1], amt, 26 * P["k"]))
    if key == "soles" and i == 5:
        for name, t0 in A["map_times"].items():
            pts = SOLE_PTS[name] if name != "diaphragm" else [p for path in SOLE_PTS[name] for p in path[1::2]]
            amt = math.exp(-((t - t0 - 0.35) / 0.35) ** 2)
            for (x, y) in pts:
                bx, by = P["to_big"](x, y)
                x0, y0, _ = window(P, *cam(SHOTS[i][3], t))
                out.append((bx - x0, by - y0, amt * 0.9, 22 * P["k"]))
    if key == "hand":
        for name, t0 in A["hand_times"].items():
            amt = math.exp(-((t - t0 - 0.35) / 0.35) ** 2)
            for (x, y) in HAND_PTS[name]:
                bx, by = P["to_big"](x, y)
                x0, y0, _ = window(P, *cam(SHOTS[i][3], t))
                out.append((bx - x0, by - y0, amt * 0.9, 22 * P["k"]))
    # convert plate-relative offsets back into absolute plate pixels for render_photo
    x0, y0, sc = window(P, *cam(SHOTS[i][3], t))
    return [((ox) / sc, (oy) / sc, a, r) for (ox, oy, a, r) in out]


def shot_img(A, i, t):
    key, s, e, keys = SHOTS[i]
    return render_photo(A["P"][key], t, cam(keys, t), presses_for(i, t, A))


def background(t, A):
    act = active(t)
    if len(act) >= 2:
        i1, i2 = act[-2], act[-1]
        p = (t - SHOTS[i2][1]) / max(1e-3, SHOTS[i1][2] - SHOTS[i2][1])
        a = Image.fromarray(np.clip(shot_img(A, i1, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12 * p))
        b = Image.fromarray(np.clip(shot_img(A, i2, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12 * (1 - p)))
        img = np.asarray(Image.blend(a, b, ease_in_out(p)), np.float32)
    else:
        img = shot_img(A, act[0], t)
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, spd, ph, a) in A["motes"]:
        put(f, A["mote"], x + 16 * math.sin(t * 0.3 + ph), (y - spd * t) % H, a * (0.45 + 0.55 * max(0.0, math.sin(t * 1.4 + ph))))
    return f, act


# ---------------------------------------------------------------- living graphics
def glow_dot(r, color, core=True):
    S = int(r * 6)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse((S / 2 - r * 1.6, S / 2 - r * 1.6, S / 2 + r * 1.6, S / 2 + r * 1.6), fill=150)
    halo = Image.new("RGBA", (S, S), color + (0,))
    halo.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.9)))
    if core:
        d = ImageDraw.Draw(halo)
        d.ellipse((S / 2 - r * 0.55, S / 2 - r * 0.55, S / 2 + r * 0.55, S / 2 + r * 0.55), fill=(255, 255, 255, 235))
    return halo


def ring(f, x, y, r, color, a, width=3):
    if a <= 0.01 or r < 1:
        return
    S = int(r * 2 + 12)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((6, 6, S - 6, S - 6), outline=color + (int(255 * a),), width=width)
    f.alpha_composite(im.filter(ImageFilter.GaussianBlur(0.8)), (int(x - S / 2), int(y - S / 2)))


def point(f, A, x, y, t, t0, num=None):
    """A living reflex point: appears with a press ripple, then pulses softly; number badge draws on."""
    if t < t0:
        return
    p = ease_out(prog(t, t0, 0.5))
    pulse = 0.82 + 0.18 * math.sin((t - t0) * 3.2)
    d = A["dot"]
    s = p * pulse
    img = d.resize((max(1, int(d.width * s)), max(1, int(d.height * s))), Image.LANCZOS)
    put(f, img, x - img.width / 2, y - img.height / 2, p)
    for k in range(2):                       # press ripples
        rp = prog(t, t0 + k * 0.25, 1.1)
        if 0 < rp < 1:
            ring(f, x, y, 14 + 46 * ease_out(rp), AQUA, (1 - rp) * 0.8, 2)
    if num is not None:
        nb = A["num"][num]
        pn = ease_out(prog(t, t0 + 0.25, 0.4))
        put(f, nb, x + 16 - nb.width / 2 + 18, y - 52 - nb.height / 2 + 10 * (1 - pn), pn)


def draw_path(f, pts, p, color, a=1.0, width=4):
    """Glowing line drawn on along pts (screen coords) up to fraction p, with a travelling spark."""
    if p <= 0:
        return
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    want = total * min(1.0, p)
    out, acc = [pts[0]], 0.0
    for i, sl in enumerate(seg):
        if acc + sl >= want:
            r = (want - acc) / sl
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * r, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * r))
            break
        out.append(pts[i + 1])
        acc += sl
    xs = [q[0] for q in out]
    ys = [q[1] for q in out]
    x0, y0 = int(min(xs)) - 20, int(min(ys)) - 20
    im = Image.new("RGBA", (int(max(xs)) - x0 + 40, int(max(ys)) - y0 + 40), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    rel = [(q[0] - x0, q[1] - y0) for q in out]
    if len(rel) >= 2:
        dd.line(rel, fill=color + (int(110 * a),), width=width * 3, joint="curve")
        im = im.filter(ImageFilter.GaussianBlur(4))
        ImageDraw.Draw(im).line(rel, fill=(235, 255, 250, int(230 * a)), width=max(1, width - 2), joint="curve")
    f.alpha_composite(im, (x0, y0))


def flow_particles(f, A, t, a):
    """Soft aqua particles drifting upward along gentle S-curves (the idea of lymph flow)."""
    for (x0, ph, spd, amp, sz) in A["flow"]:
        y = H - ((t * spd + ph * 300) % (H + 200)) + 100
        x = x0 + amp * math.sin(y * 0.006 + ph)
        put(f, A["fdot"][sz], x, y, a * (0.35 + 0.35 * math.sin(t * 2 + ph)))


def icon(kind, size, color):
    """Simple consistent line icons (3 px)."""
    s = 4
    S = size * s
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (255,)
    w = 3 * s
    if kind == "drop":
        d.polygon([(S * 0.5, S * 0.12), (S * 0.78, S * 0.58), (S * 0.22, S * 0.58)], outline=c)
        d.arc((S * 0.22, S * 0.36, S * 0.78, S * 0.9), 0, 180, fill=c, width=w)
        d.line([(S * 0.5, S * 0.12), (S * 0.25, S * 0.55)], fill=c, width=w)
        d.line([(S * 0.5, S * 0.12), (S * 0.75, S * 0.55)], fill=c, width=w)
    elif kind == "cell":
        d.ellipse((S * 0.18, S * 0.18, S * 0.82, S * 0.82), outline=c, width=w)
        d.ellipse((S * 0.40, S * 0.40, S * 0.60, S * 0.60), outline=c, width=w)
    elif kind == "wave":
        pts = [(S * (0.1 + 0.8 * k / 30), S * 0.5 + S * 0.18 * math.sin(k / 30 * 2 * math.pi * 1.5)) for k in range(31)]
        d.line(pts, fill=c, width=w, joint="curve")
    elif kind == "dot":
        d.ellipse((S * 0.38, S * 0.38, S * 0.62, S * 0.62), fill=c)
    return im.resize((size, size), Image.LANCZOS)


def build():
    A = {"P": {k: build_photo(k) for k in PHOTOS}}
    rng = np.random.default_rng(47)
    A["grain"] = [rng.normal(0, 2.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.22 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    m = Image.new("L", (20, 20), 0)
    ImageDraw.Draw(m).ellipse((8, 8, 12, 12), fill=220)
    mote = Image.new("RGBA", (20, 20), (255, 234, 196, 0))
    mote.putalpha(m.filter(ImageFilter.GaussianBlur(2)))
    A["mote"] = mote
    A["motes"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(4, 11), rng.uniform(0, 6.28), rng.uniform(0.2, 0.45)) for _ in range(16)]
    A["dot"] = glow_dot(13, AQUA)
    A["fdot"] = {k: glow_dot(k, AQUA, core=False) for k in (4, 6, 9)}
    A["flow"] = [(rng.uniform(80, W - 80), rng.uniform(0, 6.28), rng.uniform(60, 130), rng.uniform(20, 70), int(rng.choice([4, 6, 9]))) for _ in range(34)]
    A["num"] = {}
    for n in range(1, 6):
        S = 52
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        dd.ellipse((3, 3, S - 3, S - 3), fill=(18, 40, 38, 210), outline=AQUA + (255,), width=2)
        fnt = mul(28, 800)
        dd.text((S / 2, S / 2 + 1), str(n), font=fnt, fill=IVORY + (255,), anchor="mm")
        A["num"][n] = im
    A["icons"] = {k: icon(k, 64, GOLD_LINE) for k in ("drop", "cell", "wave", "dot")}
    logo = Image.open(LOGO).convert("RGBA")
    A["logo"] = logo.resize((460, round(logo.height * 460 / logo.width)), Image.LANCZOS)

    # map timing synced to the words
    A["map_times"] = {"toes": wt(5, "spaces"), "thymus": wt(5, "thymus"), "diaphragm": wt(5, "diaphragm"),
                      "spleen": wt(5, "spleen"), "kidney": wt(5, "kidney")}
    A["hand_times"] = {"fingers": wt(6, "between"), "back": wt(6, "back"), "wrist": wt(6, "wrist")}

    # ---- texts
    A["h_small"] = T("YOUR LYMPHATIC SYSTEM HAS", mul(34, 800), IVORY, tracking=8)
    A["h_big"] = base.fit(lambda s: T("NO PUMP", news(s, 600, opsz=72), "champ"), 230, 940)
    A["h_q"] = T("so what keeps it moving?", news(84, 400, italic=True), AQUA)
    A["w_carries"] = T("LYMPH CARRIES", mul(32, 800), IVORY, tracking=8)
    A["w_fluid"] = T("extra fluid", news(110, 500), IVORY)
    A["w_cells"] = T("& immune cells", news(110, 500, italic=True), "champ")
    A["w_moves"] = T("IT MOVES WITH", mul(32, 800), IVORY, tracking=8)
    A["w_trio"] = [T(w, news(76, 500), AQUA) for w in ("muscles", "breath", "gentle touch")]
    A["r_1"] = T("Reflexology", news(150, 500), IVORY)
    A["r_2"] = T("Lymph Drainage", news(150, 500, italic=True), "champ")
    A["r_3"] = T("RLD", mul(70, 800), AQUA, tracking=26)
    A["r_4"] = T("a gentle technique for the feet & hands", mul(36, 600), IVORY, tracking=1)
    A["f_1"] = T("deeply relaxing", news(130, 400, italic=True), "champ")
    A["f_2"] = T("lighter-feeling legs", news(96, 500), IVORY)
    A["f_3"] = T("Research on RLD is promising, but still early.", mul(32, 600), IVORY, tracking=1)
    A["who_h"] = T("Loved by", news(120, 400, italic=True), "champ")
    A["who"] = [T(w, news(60, 500), IVORY) for w in ("people on their feet all day", "frequent flyers", "anyone with tired, heavy legs")]
    A["map_h"] = T("THE SOLE · REFLEXOLOGY MAP", mul(30, 800), IVORY, tracking=8)
    A["map_l"] = [T(w, mul(30, 700), CHAR, dark=False) for w in
                  ("1  Between the toes", "2  Thymus", "3  Diaphragm line", "4  Spleen (left foot)", "5  Kidneys")]
    A["hand_h"] = T("THE HANDS · SAME PATTERN", mul(30, 800), IVORY, tracking=8)
    A["hand_l"] = [T(w, news(64, 500), IVORY) for w in ("Between the fingers", "Back of the hand", "Wrist")]
    A["c_h1"] = T("Check with your doctor first", news(84, 500, italic=True), "champ")
    A["c_h2"] = T("IF YOU HAVE:", mul(32, 800), IVORY, tracking=8)
    A["c_items"] = [T(w, mul(50, 600), IVORY) for w in
                    ("a fever", "a blood clot", "heart or kidney problems", "cancer treatment", "early pregnancy")]
    A["c_note"] = T("Reflexology supports medical care, never replaces it.", news(46, 400, italic=True), AQUA)
    A["e_dm"] = T("DM “LYMPH”", news(150, 600), CHAR, dark=False)
    A["e_book"] = T("TO BOOK YOUR SESSION", mul(34, 800), CHAR, tracking=10, dark=False)
    A["e_who"] = T("Zarina, RCRT  ·  The Pure Escape", mul(36, 700), CHAR, tracking=1, dark=False)
    A["e_addr"] = T("698 Corydon Ave, Winnipeg", mul(34, 600), CHAR, tracking=1, dark=False)
    A["e_ig"] = T("@yourspanish_massage", mul(34, 700), (120, 92, 52), tracking=1, dark=False)
    return A


def fade(t, s, e, fi=0.45, fo=0.4):
    return ease_out(prog(t, s, fi)) * (1 - ease_in_out(prog(t, e - fo, fo)))


def frame_at(t, A):
    f, act = background(t, A)
    sh = SHOTS
    cur = act[-1]
    E = [a + d for a, d in zip(STARTS, DUR_L)]

    # ---------- 1 · hook
    s, e = 0.0, E[0] + 0.3
    if t < e:
        wash(f, 0, 1100, NIGHT, 0.55, 0.0)
        a = fade(t, s, e, 0.2)
        letters(f, A["h_small"], W / 2 - A["h_small"].adv / 2, 330, 0.25, t, a, step=0.02)
        sharp_in(f, A["h_big"], W / 2 - A["h_big"].adv / 2, 560, prog(t, 0.55, 0.7), a, scale_from=1.12, blur=18)
        wipe(f, A["h_q"], W / 2 - A["h_q"].adv / 2, 680, prog(t, wt(0, "So what"), 0.9), a)
        flow_particles(f, A, t, a * 0.6)

    # ---------- 2 · what is lymph (blurred reflexologist at work + flow)
    s, e = STARTS[1] - 0.2, E[1] + 0.3
    if s <= t < e:
        wash(f, 0, H, NIGHT, 0.35, 0.35)
        a = fade(t, s, e)
        flow_particles(f, A, t, a)
        letters(f, A["w_carries"], 120, 520, STARTS[1], t, a, step=0.02)
        wipe(f, A["w_fluid"], 120, 650, prog(t, wt(1, "extra"), 0.6), a)
        wipe(f, A["w_cells"], 120, 770, prog(t, wt(1, "immune"), 0.6), a)
        letters(f, A["w_moves"], 120, 1010, wt(1, "It moves"), t, a, step=0.02)
        y = 1120
        for k, wd in enumerate(("muscles", "breath", "gentle")):
            tw = wt(1, wd)
            p = ease_out(prog(t, tw, 0.5))
            put(f, A["icons"]["wave" if k == 1 else "dot"], 120, y + k * 100 - 52, p * a)
            sharp_in(f, A["w_trio"][k], 200, y + k * 100, prog(t, tw, 0.5), a, blur=8)

    # ---------- 3 · what is RLD (real thumb walking, presses)
    s, e = STARTS[2] - 0.2, E[2] + 0.3
    if s <= t < e:
        wash(f, 0, 1050, NIGHT, 0.65, 0.0)
        a = fade(t, s, e)
        sharp_in(f, A["r_1"], W / 2 - A["r_1"].adv / 2, 330, prog(t, STARTS[2], 0.6), a, blur=10)
        wipe(f, A["r_2"], W / 2 - A["r_2"].adv / 2, 470, prog(t, STARTS[2] + 0.5, 0.8), a)
        letters(f, A["r_3"], W / 2 - A["r_3"].adv / 2, 590, wt(2, "or R L D"), t, a, step=0.08)
        wipe(f, A["r_4"], W / 2 - A["r_4"].adv / 2, 680, prog(t, wt(2, "gentle"), 0.8), a)
        # contact glow under the thumb (follows the press path)
        P = A["P"]["thumb"]
        cm = cam(sh[2][3], t)
        for j, (x, y) in enumerate([(420, 455), (440, 480), (455, 505)]):
            ph = (t * 1.1 + j * 0.33) % 1.0
            sx, sy = to_screen(P, cm, x, y)
            ring(f, sx, sy, 10 + 40 * ph, AQUA, (1 - ph) * 0.55 * a, 2)

    # ---------- 4 · how it may feel (candlelit room)
    s, e = STARTS[3] - 0.2, E[3] + 0.3
    if s <= t < e:
        wash(f, 0, 1150, NIGHT, 0.55, 0.0)
        a = fade(t, s, e)
        sharp_in(f, A["f_1"], W / 2 - A["f_1"].adv / 2, 400, prog(t, wt(3, "deeply"), 0.7), a, blur=12)
        wipe(f, A["f_2"], W / 2 - A["f_2"].adv / 2, 540, prog(t, wt(3, "legs"), 0.8), a)
        line(f, W / 2, 600, 300 * ease_in_out(prog(t, wt(3, "legs") + 0.4, 0.6)), GOLD_LINE, a)
        p = ease_out(prog(t, wt(3, "Research"), 0.6))
        put_c(f, A["f_3"], 680, p * a, dy=12 * (1 - p))

    # ---------- 5 · who it suits (sunlit foot)
    s, e = STARTS[4] - 0.2, E[4] + 0.3
    if s <= t < e:
        wash(f, 0, 1300, NIGHT, 0.62, 0.0)
        a = fade(t, s, e)
        wipe(f, A["who_h"], 110, 360, prog(t, STARTS[4], 0.8), a)
        for k, wd in enumerate(("people on", "frequent", "anyone")):
            tw = wt(4, wd)
            p = prog(t, tw, 0.55)
            put(f, A["icons"]["dot"], 92, 470 + k * 110 - 50, ease_out(p) * a)
            sharp_in(f, A["who"][k], 170 + 40 * (1 - ease_out(p)), 470 + k * 110, p, a, blur=8)

    # ---------- 6 · the sole map
    if cur == 5 or (len(act) > 1 and 5 in act):
        i = 5
        s, e = STARTS[5] - 0.2, E[5] + 0.4
        a = fade(t, s, e, 0.4, 0.35)
        P = A["P"]["soles"]
        cm = cam(sh[i][3], t)
        wash(f, 0, 300, NIGHT, 0.55 * a, 0.0)
        letters(f, A["map_h"], W / 2 - A["map_h"].adv / 2, 120, STARTS[5], t, a, step=0.015)
        mt = A["map_times"]
        # 1 between the toes
        for j, (x, y) in enumerate(SOLE_PTS["toes"]):
            sx, sy = to_screen(P, cm, x, y)
            point(f, A, sx, sy, t, mt["toes"] + 0.06 * j, 1 if j == 0 else None)
        for (x, y), n in zip(SOLE_PTS["thymus"], (2, None)):
            sx, sy = to_screen(P, cm, x, y)
            point(f, A, sx, sy, t, mt["thymus"], n)
        for k, path in enumerate(SOLE_PTS["diaphragm"]):
            pts = [to_screen(P, cm, x, y) for x, y in path]
            draw_path(f, pts, ease_in_out(prog(t, mt["diaphragm"], 0.9)), AQUA, a)
            if k == 0:
                point(f, A, *pts[2], t, mt["diaphragm"] + 0.3, 3)
        sx, sy = to_screen(P, cm, *SOLE_PTS["spleen"][0])
        point(f, A, sx, sy, t, mt["spleen"], 4)
        for (x, y), n in zip(SOLE_PTS["kidney"], (5, None)):
            sx, sy = to_screen(P, cm, x, y)
            point(f, A, sx, sy, t, mt["kidney"], n)
        # legend over the towel
        wash(f, 1560, H, (246, 242, 234), 0.0, 0.85, a)
        for k, (nm, key) in enumerate(zip(A["map_l"], ("toes", "thymus", "diaphragm", "spleen", "kidney"))):
            col, row = (0, k) if k < 3 else (1, k - 3)
            x = 90 + col * 520
            y = 1700 + row * 56
            p = ease_out(prog(t, mt[key], 0.5))
            put_x(f, nm, x, y, p * a, dy=10 * (1 - p))

    # ---------- 7 · hands
    s, e = STARTS[6] - 0.2, E[6] + 0.3
    if s <= t < e:
        a = fade(t, s, e)
        P = A["P"]["hand"]
        cm = cam(sh[6][3], t)
        wash(f, 0, 900, NIGHT, 0.6, 0.0)
        letters(f, A["hand_h"], W / 2 - A["hand_h"].adv / 2, 300, STARTS[6], t, a, step=0.015)
        ht = A["hand_times"]
        for (x, y) in HAND_PTS["fingers"]:
            point(f, A, *to_screen(P, cm, x, y), t, ht["fingers"])
        point(f, A, *to_screen(P, cm, *HAND_PTS["back"][0]), t, ht["back"])
        wx, wy = to_screen(P, cm, *HAND_PTS["wrist"][0])
        draw_path(f, [(wx - 110, wy - 40), (wx, wy), (wx + 110, wy + 40)], ease_in_out(prog(t, ht["wrist"], 0.7)), AQUA, a)
        for k, key in enumerate(("fingers", "back", "wrist")):
            p = ease_out(prog(t, ht[key], 0.5))
            put_c(f, A["hand_l"][k], 430 + k * 90, p * a, dy=12 * (1 - p))

    # ---------- 8 · safety
    s, e = STARTS[7] - 0.2, E[7] + 0.3
    if s <= t < e:
        wash(f, 0, H, NIGHT, 0.55, 0.55)
        a = fade(t, s, e)
        wipe(f, A["c_h1"], W / 2 - A["c_h1"].adv / 2, 420, prog(t, STARTS[7], 0.8), a)
        letters(f, A["c_h2"], W / 2 - A["c_h2"].adv / 2, 500, STARTS[7] + 0.5, t, a, step=0.02)
        for k, wd in enumerate(("fever", "blood clot", "heart or", "cancer", "early")):
            tw = wt(7, wd) - 0.15
            p = ease_out(prog(t, tw, 0.45))
            put(f, A["icons"]["dot"], W / 2 - 300, 640 + k * 92 - 46, p * a)
            put_x(f, A["c_items"][k], W / 2 - 230, 640 + k * 92, p * a, dx=-24 * (1 - p))
        p = ease_out(prog(t, wt(7, "Reflexology supports"), 0.6))
        put_c(f, A["c_note"], 1180, p * a, dy=12 * (1 - p))

    # ---------- 9 · CTA (light, logo)
    s = STARTS[8] - 0.2
    if t >= s:
        a = ease_out(prog(t, s, 0.6))
        wash(f, 0, 1250, (246, 240, 228), 0.82 * a, 0.55 * a)
        wash(f, 1250, 1500, (246, 240, 228), 0.55 * a, 0.0)
        lg = A["logo"]
        put(f, lg, (W - lg.width) / 2, 110 + 12 * (1 - a), a)
        y = 110 + lg.height + 200
        sharp_in(f, A["e_dm"], W / 2 - A["e_dm"].adv / 2, y, prog(t, wt(8, "DM"), 0.6), 1.0, blur=12)
        letters(f, A["e_book"], W / 2 - A["e_book"].adv / 2, y + 70, wt(8, "DM") + 0.3, t, step=0.015)
        line(f, W / 2, y + 100, 360 * ease_in_out(prog(t, wt(8, "LYMPH"), 0.6)), (176, 136, 70))
        p = ease_out(prog(t, E[8] - 0.4, 0.5))
        put_c(f, A["e_who"], y + 175, p, dy=12 * (1 - p))
        put_c(f, A["e_addr"], y + 228, p, dy=12 * (1 - p))
        p = ease_out(prog(t, E[8], 0.5))
        put_c(f, A["e_ig"], y + 290, p, dy=12 * (1 - p))
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


# ---------------------------------------------------------------- audio: voice + ducked music (§46 new)
BPM = 66
BAR = 4 * 60 / BPM
NOTE = {"D2": 73.42, "A2": 110.0, "Bb1": 58.27, "F2": 87.31, "C2": 65.41, "G2": 98.0,
        "D3": 146.83, "F3": 174.61, "A3": 220.0, "C4": 261.63, "E4": 329.63, "Bb3": 233.08, "D4": 293.66,
        "G3": 196.0, "E3": 164.81, "F4": 349.23, "A4": 440.0, "C5": 523.25}
PROG = [("D2", ["D3", "F3", "A3", "C4", "E4"]),      # Dm9
        ("Bb1", ["D3", "F3", "A3", "Bb3", "D4"]),    # Bbmaj7
        ("F2", ["F3", "A3", "C4", "E4", "G3"]),      # Fmaj9
        ("C2", ["E3", "G3", "C4", "D4", "E4"])]      # C add9


def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(66)
    voice = np.zeros(n)
    for i, st in enumerate(STARTS):
        v, vsr = sf.read(os.path.join(AUD, f"line{i + 1}.wav"))
        if v.ndim > 1:
            v = v.mean(1)
        if vsr != sr:
            v = np.interp(np.arange(int(len(v) * sr / vsr)) * vsr / sr, np.arange(len(v)), v)
        a0 = int(st * sr)
        m = min(len(v), n - a0)
        voice[a0:a0 + m] += v[:m]
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.92

    music = np.zeros(n)

    def add(buf, at, sig):
        i = int(at * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        m = min(len(sig), n - i)
        buf[i:i + m] += sig[:m]

    nb = int(DURATION / BAR) + 1
    seed = 0
    for b in range(nb):
        root, voi = PROG[b % 4]
        t0 = b * BAR
        # cello drone: warm saw-ish additive with slow vibrato, overlapping bars
        L = int((BAR + 1.5) * sr)
        tt = np.arange(L) / sr
        f0 = NOTE[root] * 2
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.0 * tt)
        ph = 2 * np.pi * f0 * np.cumsum(vib) / sr
        cello = sum((0.5 / k) * np.sin(k * ph) for k in range(1, 7))
        env = np.clip(tt / 0.9, 0, 1) * np.clip((BAR + 1.5 - tt) / 1.2, 0, 1)
        add(music, t0 - 0.3, 0.16 * cello * env)
        # harp arpeggio: up and back, eighth notes
        order = [0, 1, 2, 3, 4, 3, 2, 1]
        for k, idx in enumerate(order):
            seed += 1
            add(music, t0 + k * BAR / 8, 0.20 * ks(NOTE[voi[idx]] * 2, 2.2, sr, bright=0.7, seed=seed))
    # flowing water: band-passed noise with slow swells + soft bubbles
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    X *= np.exp(-((np.log(fr + 1) - np.log(1400)) / 0.9) ** 2)
    water = np.fft.irfft(X, n)
    water = water / np.abs(water).max() * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t)) * 0.10
    for at in rng.uniform(0, DURATION, 70):
        L = int(0.07 * sr)
        tt = np.arange(L) / sr
        fb = rng.uniform(600, 1400) * (1 + 1.5 * tt / 0.07)
        add(water, at, 0.025 * np.sin(2 * np.pi * np.cumsum(fb) / sr) * np.exp(-tt * 50))
    # soft glass bells on map presses / reveals
    bells = np.zeros(n)
    A_times = [0.55] + [STARTS[i] for i in range(1, 9)]
    A_times += [wt(5, w) for w in ("spaces", "thymus", "diaphragm", "spleen", "kidney")] + [wt(6, w) for w in ("between", "back", "wrist")]
    for j, at in enumerate(A_times):
        f0 = [1046.5, 1174.66, 1396.91, 1567.98, 1760.0][j % 5]
        L = int(2.0 * sr)
        tt = np.arange(L) / sr
        add(bells, at, np.exp(-tt * 3.0) * np.clip(tt / 0.002, 0, 1) * (np.sin(2 * np.pi * f0 * tt) + 0.25 * np.sin(2 * np.pi * f0 * 2.76 * tt) * np.exp(-tt * 6)))
    music = music + water + 0.05 * bells
    music = music / (np.abs(music).max() + 1e-9)
    # ducking: music sits ~-20 dB under the voice, rises a little in pauses
    env = np.abs(voice)
    k = int(0.25 * sr)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    gain = 0.20 - 0.10 * env
    mix_l = voice + music * gain + 0.02 * np.roll(music, int(0.012 * sr)) * gain
    mix_r = voice + music * gain
    st = np.stack([mix_l, mix_r], 1)
    st *= (np.clip((DURATION - t) / 1.4, 0, 1) * np.clip(t / 0.1, 0, 1))[:, None]
    st = st / np.max(np.abs(st)) * 10 ** (-1.5 / 20)
    data = (st * 32767).astype(np.int16)
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
        ts = [float(x) for x in sys.argv[2:]] or [STARTS[0] + 3.0, STARTS[1] + 5.5, STARTS[2] + 5.0, STARTS[3] + 5.0,
                                                    STARTS[4] + 5.0, STARTS[5] + 6.5, STARTS[6] + 3.4, STARTS[7] + 11.5, DURATION - 0.5]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(qc, f"rld-{s:05.2f}s.png"))
        print(ts)
        return
    if mode == "audio":
        synth_audio(os.path.join(OUT_DIR, "qc", "rld.wav"))
        return
    tmp = os.path.join(OUT_DIR, f".{NAME}.render.mp4")
    wav = os.path.join(OUT_DIR, f".{NAME}.wav")
    synth_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=9",
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
    Image.fromarray(frame_at(STARTS[0] + 3.0, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4, DURATION)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
