"""THE PURE ESCAPE — Available Appointments — Tuesday, October 13 & Wednesday, October 14, 2026
(the same four times both days: 11:00 a.m. · 12:45 p.m. · 2:30 p.m. · 3:45 p.m.).

Concept "Two Days, Eight Openings": a typographic countdown hook, then both days side by side,
then each time gets its own hero reveal and flies into a growing 2 x 2 time grid. Owner's
3 photos: eucalyptus + amber dropper on linen, a candlelit still life, facial reflexology.
Living background: candle flames flicker (masked glow), the plant and the eucalyptus leaves
sway (masked local warps), warm light pool drifts, motes; camera push-in / slide / pull-back.
Palette: cream + charcoal + deep sage + antique gold. Type: Plus Jakarta Sans (bold + light,
one modern sans family) + Mrs Saint Delafield (script accent, sparingly).
Music (§46, new): 96 BPM, F-sharp major, kalimba ostinato, handpan bass, finger-snaps on 2 & 4,
reverse swells into every time reveal, soft room tone.

  python3 production/oct13_pe_two_days.py stills [t ...]
  python3 production/oct13_pe_two_days.py video
  python3 production/oct13_pe_two_days.py poster
"""
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oct16_amt_thanksgiving as base  # noqa: E402
from oct10_pe_saturday import extend_top, flicker  # noqa: E402
from oct16_amt_thanksgiving import (Text, bilinear, ease_in_out, ease_out, letters, line, prog, put,  # noqa: E402
                                    put_c, put_x, sharp_in, wash, wipe)

ROOT = base.ROOT
FONTS = base.FONTS
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
PH_DIR = os.path.join(ROOT, "brand", "photos", "pe-oct13")
OUT_DIR = base.OUT_DIR
NAME = "2026-10-13-pe-available-appointments"
W, H, FPS = 1080, 1920, 30
DURATION = 32.0

CREAM = (247, 241, 230)
CHAR = (38, 34, 30)
SAGE = (66, 92, 68)
IVORY = (250, 245, 236)
DUSK = (24, 18, 12)
GOLD_LINE = (176, 136, 70)
base.GOLDS["antique"] = ((176, 134, 66), (138, 98, 42), (96, 64, 26))   # bronze-gold: legible on cream
base.GOLDS["light"] = ((246, 226, 182), (218, 182, 116), (166, 126, 62))

# ---------------------------------------------------------------- facts (owner-provided; verified)
CLINIC = "The Pure Escape"
ADDRESS = "698 Corydon Ave, Winnipeg"
THERAPIST = "Zarina, RCRT"
DAYS = [("TUESDAY", "October 13"), ("WEDNESDAY", "October 14")]     # 2026: Tue 13, Wed 14 — verified
TIMES = [("11:00", "a.m."), ("12:45", "p.m."), ("2:30", "p.m."), ("3:45", "p.m.")]   # same times both days
SERVICES = [  # exactly the owner's list for this post, professional naming
    ("Reflexology Lymph Drainage", "RLD"),
    ("Foot Reflexology", ""),
    ("Facial Reflexology", "BERGMAN METHOD"),
    ("Spanish Massage", ""),
    ("Ultimate Escape Package", ""),
    ("Combo", "90 MINUTES"),
]


def jak(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "PlusJakartaSans[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def script(size):
    return ImageFont.truetype(os.path.join(FONTS, "MrsSaintDelafield-Regular.ttf"), size)


def T(txt, fnt, fill, tracking=0, dark=False):
    return Text(txt, fnt, fill, tracking=tracking, shadow=DUSK if dark else None)


# ---------------------------------------------------------------- living photos
# key: (file, headroom, bright headroom?, flames[(u, v, r)], sway boxes [(u0, v0, u1, v1, amp)])
PHOTOS = {
    "euca": ("eucalyptus-oil.jpg", 0.62, "cream", [], [(0.0, 0.06, 0.58, 0.97, 1.0)]),
    "candle": ("candles-towels.jpg", 0.12, True,
               [(0.730, 0.612, 0.022), (0.948, 0.678, 0.022), (0.876, 0.745, 0.020), (0.460, 0.818, 0.020)],
               [(0.50, 0.0, 1.0, 0.37, 1.3)]),
    "facial": ("facial-hands.jpg", 0.62, "dusk", [], []),
}


def build_photo(key):
    fn, head, bright, flames, sways = PHOTOS[key]
    im = Image.open(os.path.join(PH_DIR, fn)).convert("RGB")
    H0, W0 = im.height, im.width
    im, add = extend_top(im, head, bright is True)
    if bright in ("cream", "dusk"):
        # clean negative space: fade the mirrored headroom into a calm linen / warm-dusk tone
        col = np.array([238, 230, 216] if bright == "cream" else [52, 34, 22], np.float32)
        arr = np.asarray(im, np.float32).copy()
        g = np.clip(1 - np.arange(add + 60, dtype=np.float32) / (add + 60), 0, 1) ** 0.6
        gv = g[:, None, None]
        arr[:add + 60] = arr[:add + 60] * (1 - gv) + col * gv
        noise = np.random.default_rng(5).normal(0, 1.6, arr[:add + 60].shape)
        arr[:add + 60] += noise * gv
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    k = max(W / im.width, H / im.height) * 1.25
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=2.4, percent=60, threshold=2))
    h, w = big.height, big.width

    def to_big(u, v):
        return u * W0 * k, (v * H0 + add) * k

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    glow = np.zeros((h, w), np.float32)
    for (u, v, r) in flames:
        cx, cy = to_big(u, v)
        rr = r * W0 * k
        glow += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rr ** 2)))
    sway = np.zeros((h, w), np.float32)
    for (u0, v0, u1, v1, amp) in sways:
        x0, y0 = to_big(u0, v0)
        x1, y1 = to_big(u1, v1)
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).rectangle((x0, y0, x1, y1), fill=255)
        sway += amp * np.asarray(m.filter(ImageFilter.GaussianBlur(50)), np.float32) / 255
    return {"arr": np.asarray(big, np.float32), "w": w, "h": h, "glow": np.clip(glow, 0, 1),
            "nfl": len(flames), "sway": sway if sways else None}


def render_photo(P, t, u, v, z):
    s = max(W / P["w"], H / P["h"])
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * P["w"], cw / 2), P["w"] - cw / 2)
    cy = min(max(v * P["h"], ch / 2), P["h"] - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    ix = np.clip(gx.astype(np.int32), 0, P["w"] - 1)
    iy = np.clip(gy.astype(np.int32), 0, P["h"] - 1)
    if P["sway"] is not None:
        wgt = P["sway"][iy, ix]
        gx = gx + wgt * (4.2 * np.sin(1.05 * t + gy * 0.005) + 1.8 * np.sin(2.2 * t + gx * 0.009))
        gy = gy + wgt * (2.2 * np.sin(1.3 * t + gx * 0.006))
    img = bilinear(P["arr"], gx, gy)
    if P["nfl"]:
        g = P["glow"][iy, ix][..., None]
        f = sum(flicker(t, 1.7 * i) for i in range(P["nfl"])) / P["nfl"]
        img = img * (1 + g * 0.24 * f) + g * np.array([255, 186, 104], np.float32) * (0.10 + 0.07 * f)
    return img


# shots: (key, start, end, [(t, u, v, z), ...])
SHOTS = [
    ("euca", 0.0, 3.7, [(0.0, 0.50, 0.40, 1.00), (3.7, 0.52, 0.44, 1.06)]),                 # push toward the bottle
    ("candle", 3.4, 12.4, [(3.4, 0.50, 0.44, 1.00), (7.4, 0.52, 0.47, 1.06), (12.4, 0.66, 0.55, 1.24)]),  # push to the candles
    ("facial", 12.1, 17.6, [(12.1, 0.44, 0.38, 1.08), (17.6, 0.56, 0.38, 1.08)]),           # lateral slide
    ("euca", 17.3, 25.4, [(17.3, 0.46, 0.38, 1.08), (25.4, 0.50, 0.36, 1.00)]),            # pull-back
    ("candle", 25.1, 32.0, [(25.1, 0.52, 0.48, 1.12), (32.0, 0.50, 0.44, 1.00)]),          # pull-back to the room
]
# time reveals: (start, hero position y) — each time is a hero, then flies to its grid slot
REVEALS = [7.6, 10.0, 12.6, 15.0]
HERO_Y = 820
SLOTS = [(300, 350), (780, 350), (300, 440), (780, 440)]     # 2 x 2 grid (centre x, baseline y)


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
        a = Image.fromarray(np.clip(shot_img(A, i1, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14 * p))
        b = Image.fromarray(np.clip(shot_img(A, i2, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14 * (1 - p)))
        img = np.asarray(Image.blend(a, b, ease_in_out(p)), np.float32)
    else:
        img = shot_img(A, act[0], t)
        if soften > 0.01:
            img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9 * soften)), np.float32)
    lx = W * (0.70 + 0.12 * math.sin(t * 0.19))
    ly = H * (0.22 + 0.05 * math.sin(t * 0.23 + 1))
    pool = np.exp(-(((A["xx"] - lx) / 560) ** 2 + ((A["yy"] - ly) / 700) ** 2))[..., None]
    img = img * A["vig"] * (1 + 0.07 * pool) + pool * np.array([34, 22, 6], np.float32) * 0.4 + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, spd, ph, a) in A["motes"]:
        mx = x + 16 * math.sin(t * 0.33 + ph)
        my = (y - spd * t) % H
        put(f, A["mote"], mx, my, a * (0.5 + 0.5 * math.sin(t * 1.2 + ph)))
    return f


def build():
    A = {"P": {k: build_photo(k) for k in PHOTOS}}
    rng = np.random.default_rng(13)
    A["grain"] = [rng.normal(0, 2.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["xx"], A["yy"] = xx, yy
    A["vig"] = (1 - 0.18 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    m = Image.new("L", (22, 22), 0)
    ImageDraw.Draw(m).ellipse((8, 8, 14, 14), fill=210)
    mote = Image.new("RGBA", (22, 22), (255, 232, 190, 0))
    mote.putalpha(m.filter(ImageFilter.GaussianBlur(3)))
    A["mote"] = mote
    A["motes"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(5, 13), rng.uniform(0, 6.28), rng.uniform(0.25, 0.55)) for _ in range(20)]

    logo = Image.open(LOGO).convert("RGBA")     # official file, untouched, directly on the light scene
    A["logo"] = logo.resize((330, round(logo.height * 330 / logo.width)), Image.LANCZOS)
    A["logo_big"] = logo.resize((470, round(logo.height * 470 / logo.width)), Image.LANCZOS)

    # hook (light scene)
    A["twodays"] = T("TWO DAYS.", jak(118, 800), CHAR, tracking=4)
    A["eight"] = T("EIGHT", jak(300, 800), "antique", tracking=2)
    A["openings"] = T("openings", script(190), SAGE)
    # days
    A["same"] = T("same four times, both days", script(104), SAGE)
    A["days"] = [(T(d, jak(50, 800), CHAR, tracking=10), T(dt, jak(70, 300), CHAR)) for d, dt in DAYS]
    # times
    A["idx"] = [T(f"0{i + 1}  /  04", jak(34, 700), CHAR, tracking=8) for i in range(4)]
    A["idx_d"] = [T(f"0{i + 1}  /  04", jak(34, 700), IVORY, tracking=8, dark=True) for i in range(4)]
    A["hero"] = [(T(tm, jak(300, 500), "antique"), T(ap, jak(80, 500), CHAR)) for tm, ap in TIMES]
    A["hero_d"] = [(T(tm, jak(300, 500), "light", dark=True), T(ap, jak(80, 500), IVORY, dark=True)) for tm, ap in TIMES]
    A["slot"] = [(T(tm, jak(76, 600), "antique"), T(ap, jak(30, 600), CHAR)) for tm, ap in TIMES]
    A["slot_d"] = [(T(tm, jak(76, 500), "light", dark=True), T(ap, jak(30, 600), IVORY, dark=True)) for tm, ap in TIMES]
    A["tw"] = T("TUESDAY & WEDNESDAY", jak(32, 800), CHAR, tracking=10)
    A["tw_d"] = T("TUESDAY & WEDNESDAY", jak(32, 800), IVORY, tracking=10, dark=True)
    # services (light)
    A["menu"] = T("Treatments", script(170), SAGE)
    A["svc"] = [(T(n, jak(56, 600), CHAR), T(sub, jak(26, 800), "antique", tracking=8) if sub else None,
                 T(f"0{i + 1}", jak(26, 800), "antique", tracking=2)) for i, (n, sub) in enumerate(SERVICES)]
    # summary (light)
    A["s_avail"] = T("Available appointments", script(140), SAGE)
    A["s_days"] = T("TUESDAY, OCTOBER 13  &  WEDNESDAY, OCTOBER 14", jak(30, 800), CHAR, tracking=4)
    A["s_t"] = [(T(tm, jak(96, 600), "antique"), T(ap, jak(34, 600), CHAR)) for tm, ap in TIMES]
    A["s_who"] = T(f"with {THERAPIST}", jak(40, 600), CHAR, tracking=2)
    A["s_addr"] = T(f"{CLINIC}  ·  {ADDRESS}", jak(32, 500), CHAR, tracking=1)
    A["s_cta"] = T("DM TO BOOK", jak(54, 800), CHAR, tracking=16)
    return A


def time_block(f, A, i, t, dark):
    """Hero reveal of time i, then a flight into its grid slot. Slots stay until the section ends."""
    t0 = REVEALS[i]
    hero = (A["hero_d"] if dark else A["hero"])[i]
    slot = (A["slot_d"] if dark else A["slot"])[i]
    fly = ease_in_out(prog(t, t0 + 1.75, 0.55))
    tm, ap = hero
    if fly < 1:
        # hero: blur -> sharp from slightly large, a.m./p.m. slides in, index above
        a = 1 - fly
        tot = tm.adv + 22 + ap.adv
        x = W / 2 - tot / 2
        s = 1 - 0.75 * fly
        cy = HERO_Y + (SLOTS[i][1] - HERO_Y) * fly
        cx = W / 2 + (SLOTS[i][0] - W / 2) * fly
        if fly <= 0.001:
            sharp_in(f, tm, x, HERO_Y, prog(t, t0, 0.65), scale_from=1.08, blur=18)
            p = ease_out(prog(t, t0 + 0.45, 0.45))
            put_x(f, ap, x + tm.adv + 22, HERO_Y, p, dx=-26 * (1 - p))
            idx = (A["idx_d"] if dark else A["idx"])[i]
            p = ease_out(prog(t, t0 + 0.1, 0.4))
            put_c(f, idx, HERO_Y - 280, p * (1 - fly))
            line(f, W / 2, HERO_Y + 50, 420 * ease_in_out(prog(t, t0 + 0.6, 0.6)), GOLD_LINE)
        else:
            img = Image.new("RGBA", (int(tot + 2 * tm.pad + 40), tm.h), (0, 0, 0, 0))
            img.alpha_composite(tm.img, (0, 0))
            img.alpha_composite(ap.img, (int(tm.adv + 22), int(tm.asc - ap.asc)))
            img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
            put(f, img, cx - (tot / 2 + tm.pad) * s, cy - tm.asc * s, a)
    # slot (fades in as the hero lands)
    if fly > 0.6:
        st, sa = slot
        tot = st.adv + 10 + sa.adv
        x = SLOTS[i][0] - tot / 2
        p = min(1.0, (fly - 0.6) / 0.4)
        put_x(f, st, x, SLOTS[i][1], p)
        put_x(f, sa, x + st.adv + 10, SLOTS[i][1], p)


def frame_at(t, A):
    soften = sum(math.exp(-((t - r) / 0.35) ** 2) for r in REVEALS) * 0.9   # times appear "from nowhere"
    f = background(t, A, soften)
    dark = 12.4 < t < 17.5           # the facial photo is warm and dark: ivory type
    if dark:
        wash(f, 0, 1200, DUSK, 0.55, 0.0)
    elif 17.4 <= t < 25.4:
        wash(f, 0, 1200, CREAM, 0.62, 0.0)
    else:
        wash(f, 0, 1150, CREAM, 0.70, 0.0)

    if t < 7.4:   # logo top-left on the light opening, directly on the scene
        p = ease_out(prog(t, 0.1, 0.8)) * (1 - ease_in_out(prog(t, 7.0, 0.4)))
        put(f, A["logo"], 64, 70 + 10 * (1 - p), p)

    # ---- hook 0–3.6: countdown typography
    if t < 3.8:
        a = 1 - ease_in_out(prog(t, 3.35, 0.4))
        letters(f, A["twodays"], W / 2 - A["twodays"].adv / 2, 430, 0.15, t, a, step=0.04)
        sharp_in(f, A["eight"], W / 2 - A["eight"].adv / 2, 720, prog(t, 0.75, 0.7), a, scale_from=0.8, blur=20)
        wipe(f, A["openings"], W / 2 - A["openings"].adv / 2 + 60, 850, prog(t, 1.4, 0.9), a)

    # ---- both days 3.7–7.4: two columns with a fine gold divider
    if 3.6 <= t < 7.5:
        a = 1 - ease_in_out(prog(t, 7.05, 0.4))
        for k, (d, dt) in enumerate(A["days"]):
            cx = 290 if k == 0 else 790
            t0 = 3.75 + k * 0.45
            p = ease_out(prog(t, t0, 0.6))
            put_c(f, d, 560, p * a, dy=30 * (1 - p), cx=cx)
            p = ease_out(prog(t, t0 + 0.2, 0.6))
            put_c(f, dt, 650, p * a, dy=30 * (1 - p), cx=cx)
        L = 150 * ease_in_out(prog(t, 4.2, 0.6))
        if L > 1:
            f.alpha_composite(Image.new("RGBA", (2, int(L)), GOLD_LINE + (int(255 * a),)), (W // 2 - 1, int(605 - L / 2)))
        wipe(f, A["same"], W / 2 - A["same"].adv / 2, 820, prog(t, 4.9, 1.0), a)

    # ---- four time reveals 7.6–17.2, each flying into the grid
    if 7.5 <= t < 17.6:
        a_out = 1 - ease_in_out(prog(t, 17.1, 0.4))
        if a_out > 0:
            sub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            tw = A["tw_d"] if dark else A["tw"]
            p = ease_out(prog(t, 7.55, 0.5))
            put_c(sub, tw, 250, p)
            for i in range(4):
                if t >= REVEALS[i]:
                    time_block(sub, A, i, t, dark)
            put(f, sub, 0, 0, a_out)

    # ---- services 17.6–25.3: header + numbered list, each line wipes in
    if 17.5 <= t < 25.5:
        a = ease_out(prog(t, 17.55, 0.4)) * (1 - ease_in_out(prog(t, 25.0, 0.4)))
        X = 150
        wipe(f, A["menu"], X - 20, 330, prog(t, 17.6, 0.9), a)
        letters(f, A["tw"], X, 400, 17.9, t, a, step=0.02)
        y = 500
        for i, (nm, sub, ix) in enumerate(A["svc"]):
            t0 = 18.3 + i * 0.55
            p = ease_out(prog(t, t0, 0.4))
            put_x(f, ix, X - 70, y - 4, p * a, dy=10 * (1 - p))
            wipe(f, nm, X, y, prog(t, t0 + 0.05, 0.6), a)
            if sub is not None:
                letters(f, sub, X + 2, y + 42, t0 + 0.35, t, a, step=0.02)
                y += 120
            else:
                y += 90

    # ---- summary 25.4–32
    if t >= 25.4:
        p0 = ease_out(prog(t, 25.45, 0.7))
        wash(f, 0, 1350, CREAM, 0.30, 0.0, p0)
        lg = A["logo_big"]
        put(f, lg, (W - lg.width) / 2, 70 + 14 * (1 - p0), p0)
        y = 70 + lg.height + 120
        wipe(f, A["s_avail"], W / 2 - A["s_avail"].adv / 2, y, prog(t, 25.8, 0.9))
        letters(f, A["s_days"], W / 2 - A["s_days"].adv / 2, y + 75, 26.3, t, step=0.012)
        for k, (tm, ap) in enumerate(A["s_t"]):
            cx = 300 if k % 2 == 0 else 780
            by = y + 210 + (k // 2) * 118
            tot = tm.adv + 10 + ap.adv
            x = cx - tot / 2
            sharp_in(f, tm, x, by, prog(t, 26.8 + k * 0.25, 0.55), scale_from=0.9)
            p = ease_out(prog(t, 27.0 + k * 0.25, 0.4))
            put_x(f, ap, x + tm.adv + 10, by, p, dy=10 * (1 - p))
        line(f, W / 2, y + 380, 420 * ease_in_out(prog(t, 28.0, 0.6)), GOLD_LINE)
        p = ease_out(prog(t, 28.2, 0.5))
        put_c(f, A["s_who"], y + 445, p, dy=14 * (1 - p))
        put_c(f, A["s_addr"], y + 498, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 28.7, 0.6))
        put_c(f, A["s_cta"], y + 600, p, dy=16 * (1 - p))
        L = 330 * ease_in_out(prog(t, 29.0, 0.7)) * (0.86 + 0.14 * math.sin(max(0.0, t - 29.7) * 2.4))
        line(f, W / 2, y + 626, L, GOLD_LINE, p, thick=3)
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


# ---------------------------------------------------------------- music (§46: new direction)
BPM = 96
BEAT = 60 / BPM          # 0.625 s
BAR = 4 * BEAT           # 2.5 s
F = {"F#3": 185.00, "C#4": 277.18, "D#4": 311.13, "F#4": 369.99, "G#4": 415.30, "A#4": 466.16, "B4": 493.88,
     "C#5": 554.37, "D#5": 622.25, "F#5": 739.99, "G#5": 830.61, "A#5": 932.33, "C#6": 1108.73,
     "D#2": 77.78, "B1": 61.74, "F#2": 92.50, "C#2": 69.30}
CHORDS = [("D#2", ["D#4", "F#4", "A#4", "C#5"]),     # D#m7
          ("B1", ["D#4", "F#4", "A#4", "B4"]),       # Bmaj7
          ("F#2", ["F#4", "A#4", "C#5", "G#5"]),     # F#add9
          ("C#2", ["C#4", "F#4", "G#4", "C#5"])]     # C#sus4
SONG = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 2]      # 13 bars = 32.5 s, ends on F#
ACCENT = [(0.75, "A#5"), (3.75, "F#5"), (7.6, "C#6"), (10.0, "A#5"), (12.6, "C#6"), (15.0, "G#5"),
          (18.3, "F#5"), (18.85, "G#5"), (19.4, "A#5"), (19.95, "C#6"), (26.8, "A#5"), (28.7, "F#5")]


def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(96)
    kal = np.zeros(n)
    low = np.zeros(n)
    perc = np.zeros(n)
    fx = np.zeros(n)

    def add(buf, at, sig):
        i = int(at * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        m = min(len(sig), n - i)
        buf[i:i + m] += sig[:m]

    def kalimba(f0, vel, dur=1.6):
        tt = np.arange(int(dur * sr)) / sr
        env = np.exp(-tt * 3.2) * np.clip(tt / 0.002, 0, 1)
        tine = np.sin(2 * np.pi * f0 * tt) + 0.35 * np.sin(2 * np.pi * f0 * 5.95 * tt) * np.exp(-tt * 18)
        click = rng.normal(0, 1, len(tt)) * np.exp(-tt * 400) * 0.15
        return vel * env * (tine + click)

    def handpan(f0, vel, dur=2.2):
        tt = np.arange(int(dur * sr)) / sr
        env = np.exp(-tt * 1.8) * np.clip(tt / 0.006, 0, 1)
        fb = f0 * (1 + 0.012 * np.exp(-tt * 12))
        ph = 2 * np.pi * np.cumsum(fb) / sr
        return vel * env * (np.sin(ph) + 0.45 * np.sin(2 * ph) * np.exp(-tt * 3) + 0.2 * np.sin(3 * ph) * np.exp(-tt * 5))

    def snap():
        L = int(0.12 * sr)
        x = rng.normal(0, 1, L)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(L, 1 / sr)
        X *= np.exp(-((fr - 2300) / 900) ** 2)
        y = np.fft.irfft(X, L)
        tt = np.arange(L) / sr
        return y / (np.abs(y).max() + 1e-9) * np.exp(-tt * 55)

    pattern = [0, 2, 1, 3, 2, 1, 3, 2]   # eighth-note kalimba ostinato
    for b, ci in enumerate(SONG):
        t0 = b * BAR
        bass, voi = CHORDS[ci]
        add(low, t0, handpan(F[bass] * 2, 0.55))
        add(low, t0 + 1.5 * BEAT, handpan(F[bass] * 3, 0.22))
        for k, idx in enumerate(pattern):
            sw = 0.018 if k % 2 else 0.0     # gentle swing
            add(kal, t0 + k * BEAT / 2 + sw, kalimba(F[voi[idx]], 0.20 if k % 2 == 0 else 0.13))
        if t0 + 0.01 >= 3.7:                 # snaps from the days scene on: beats 2 and 4
            for beat in (1, 3):
                add(perc, t0 + beat * BEAT, 0.16 * snap())
    for at, nn in ACCENT:
        add(kal, at, kalimba(F[nn], 0.32, 2.2))
    # reverse swells into every time reveal (and into the summary)
    for at in REVEALS + [25.4]:
        L = int(0.9 * sr)
        x = rng.normal(0, 1, L)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(L, 1 / sr)
        X *= np.exp(-((np.log(fr + 1) - np.log(3000)) / 0.9) ** 2)
        y = np.fft.irfft(X, L)
        y = y / np.abs(y).max() * np.linspace(0, 1, L) ** 2.5
        add(fx, at - 0.9, 0.12 * y)
    # soft room tone
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    X *= 1 / np.sqrt(np.maximum(fr, 40)) * np.exp(-fr / 5000)
    room = np.fft.irfft(X, n)
    room = room / np.abs(room).max() * 0.02

    mix = 0.9 * kal + 0.75 * low + perc + fx + room
    left = mix + 0.15 * np.roll(kal, int(0.012 * sr))
    right = mix + 0.15 * np.roll(kal, int(0.019 * sr)) + 0.2 * np.roll(perc, int(0.008 * sr))
    st = np.stack([left, right], 1)
    st *= (np.clip((DURATION - t) / 2.0, 0, 1) * np.clip(t / 0.15, 0, 1))[:, None]
    st = st / np.max(np.abs(st)) * 10 ** (-6 / 20)
    data = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def poster(path, PW=1080, PH=1350):
    """Static 4:5 feed post on the candlelit still life (logo on the light wall)."""
    im = Image.open(os.path.join(PH_DIR, "candles-towels.jpg")).convert("RGB")
    im, add = extend_top(im, 0.10, True)
    s = PW / im.width
    img = im.resize((PW, int(im.height * s)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.4, percent=60, threshold=2))
    img = img.crop((0, img.height - PH - 120, PW, img.height - 120))
    f = img.convert("RGBA")
    g = np.concatenate([np.linspace(0.62, 0.50, 760), np.linspace(0.50, 0.0, 220)]).astype(np.float32)[:, None].repeat(PW, 1)
    sh = Image.new("RGBA", (PW, len(g)), CREAM + (0,))
    sh.putalpha(Image.fromarray((g * 255).astype(np.uint8)))
    f.alpha_composite(sh, (0, 0))
    logo = Image.open(LOGO).convert("RGBA")
    lg = logo.resize((300, round(logo.height * 300 / logo.width)), Image.LANCZOS)
    f.alpha_composite(lg, ((PW - lg.width) // 2, 30))
    cx = PW / 2

    def c(tx, by):
        f.alpha_composite(tx.img, (int(cx - tx.adv / 2 - tx.pad), int(by - tx.asc)))
    y = 30 + lg.height + 82
    c(T("Available appointments", script(112), SAGE), y)
    c(T("TUESDAY, OCTOBER 13  &  WEDNESDAY, OCTOBER 14", jak(27, 800), CHAR, tracking=4), y + 74)
    parts = [(T(tm, jak(80, 400), "antique"), T(ap, jak(30, 600), CHAR)) for tm, ap in TIMES]
    for k, (tm, ap) in enumerate(parts):
        bx = 300 if k % 2 == 0 else 780
        by = y + 160 + (k // 2) * 96
        tot = tm.adv + 10 + ap.adv
        x = bx - tot / 2
        f.alpha_composite(tm.img, (int(x - tm.pad), int(by - tm.asc)))
        f.alpha_composite(ap.img, (int(x + tm.adv + 10 - ap.pad), int(by - ap.asc)))
    d = ImageDraw.Draw(f)
    d.line([(cx - 200, y + 300), (cx + 200, y + 300)], fill=GOLD_LINE + (255,), width=2)
    c(T("RLD  ·  Foot Reflexology  ·  Facial Reflexology (Bergman Method)", jak(25, 600), CHAR, tracking=1), y + 348)
    c(T("Spanish Massage  ·  Ultimate Escape Package  ·  Combo (90 min)", jak(25, 600), CHAR, tracking=1), y + 386)
    c(T(f"with {THERAPIST}  ·  {CLINIC}  ·  {ADDRESS}", jak(25, 700), CHAR, tracking=1), y + 440)
    c(T("DM TO BOOK", jak(44, 800), CHAR, tracking=14), y + 520)
    d.line([(cx - 130, y + 540), (cx + 130, y + 540)], fill=GOLD_LINE + (255,), width=3)
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
        ts = [float(x) for x in sys.argv[2:]] or [2.9, 6.4, 8.8, 9.6, 14.4, 16.9, 24.6, 31.0]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(qc, f"pe13-{s:04.1f}s.png"))
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
    Image.fromarray(frame_at(31.5, A)).save(os.path.join(OUT_DIR, f"{NAME}-story.jpg"), quality=93)
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
