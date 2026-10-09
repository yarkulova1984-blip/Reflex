"""ADVANCED MASSAGE THERAPY — Available Appointments — Friday, October 16, 2026 — v2 "Dew"
(+ clinic closed Monday, October 12 — Thanksgiving). Replaces v1 ("After the Feast") at the
owner's request: flowers, more professional, new music, official logo.

Owner's 2 photos: a dewy pink double tulip macro and pink ranunculus with buds, both on black.
Living background: petals breathe (masked local warp), dew drops twinkle (highlight map with
moving phase), ranunculus buds sway on their stems, soft blush/champagne bokeh drifts in the
foreground, out-of-focus petals pass across the lens as transitions; camera push-in / slide /
pull-back / wide-to-detail.
Palette: black + blush + ivory + champagne gold, sage accent. Type: Libre Caslon Display
(editorial serif) + Figtree (clean sans) + Ephesis (script accent, used sparingly).
Music (§46, new): felt-piano waltz in 3/4, 72 BPM, D-flat major, soft string swells from Friday,
rain/dew texture with water-drop plinks, glass pings on the reveals.

  python3 production/oct16_amt_v2_flowers.py stills [t ...]
  python3 production/oct16_amt_v2_flowers.py video
  python3 production/oct16_amt_v2_flowers.py poster
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
import oct16_amt_thanksgiving as base  # noqa: E402  (shared type/motion helpers)
from oct16_amt_thanksgiving import (Text, bilinear, ease_in_out, ease_out, extend_top, letters, line,  # noqa: E402
                                    prog, put, put_c, put_x, sharp_in, wash, wipe, with_alpha)

ROOT = base.ROOT
FONTS = base.FONTS
LOGO = base.LOGO
PH_DIR = base.PH_DIR
OUT_DIR = base.OUT_DIR
NAME = "2026-10-16-amt-available-appointments-v2"
W, H, FPS = 1080, 1920, 30
DURATION = 30.0

IVORY = (248, 242, 232)
BLUSH = (236, 190, 196)
SAGE = (164, 186, 150)
NIGHT = (6, 4, 6)
GOLD_LINE = (214, 184, 132)
base.GOLDS["champagne"] = ((248, 232, 200), (218, 188, 136), (158, 124, 78))

CLINIC, ADDRESS, THERAPIST = base.CLINIC, base.ADDRESS, base.THERAPIST
CLOSED, OPEN_DAY, OPEN_DATE, TIMES, SERVICES = base.CLOSED, base.OPEN_DAY, base.OPEN_DATE, base.TIMES, base.SERVICES


def caslon(size):
    return ImageFont.truetype(os.path.join(FONTS, "LibreCaslonDisplay-Regular.ttf"), size)


def fig(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "Figtree[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def eph(size):
    return ImageFont.truetype(os.path.join(FONTS, "Ephesis-Regular.ttf"), size)


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT)


def track_in(f, tx_list, x_center, base_y, p, a=1.0):
    """Tracking reveal: pre-rendered texts with decreasing tracking; pick by progress."""
    e = ease_out(p)
    if e <= 0:
        return
    i = min(len(tx_list) - 1, int(e * (len(tx_list) - 1) + 0.5))
    tx = tx_list[i]
    put_c(f, tx, base_y, e * a, cx=x_center)


def put_r(f, tx, xr, base_y, a=1.0, dx=0.0, dy=0.0):
    put_x(f, tx, xr - tx.adv, base_y, a, dx, dy)


# ---------------------------------------------------------------- living flower plates
PHOTOS = {  # key: (file, headroom fraction, sway kind)
    "tulip": ("tulip-macro-dew.jpg", 0.40, "petals"),
    "ranun": ("ranunculus-buds.jpg", 0.42, "buds"),
}


def _blurL(a, r):
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(r)), np.float32)


def build_photo(key):
    fn, head, kind = PHOTOS[key]
    im = Image.open(os.path.join(PH_DIR, fn)).convert("RGB")
    H0 = im.height
    im, add = extend_top(im, head)
    k = max(W / im.width, H / im.height) * 1.22
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=2))
    arr = np.asarray(big, np.float32)
    h, w = arr.shape[:2]
    lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
    sat = arr.max(-1) - arr.min(-1)
    # flower mask (pink petals), used for the breathing warp
    pink = ((arr[..., 0] > arr[..., 1] + 18) & (lum > 60)).astype(np.float32) * 255
    flower = _blurL(pink, 40) / 255
    # dew / highlight map: small bright spots relative to their surroundings
    spec = np.clip(lum - _blurL(lum, 5) - 14, 0, 60) / 60
    spec = _blurL(spec * 255, 1.2) / 255
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(7 if key == "tulip" else 9)
    phase = _blurL(rng.uniform(0, 255, (h, w)), 6) / 255 * 6.28 * 3
    # bud/stem sway weight: lower part of the ranunculus photo (stems + buds)
    stem = np.zeros((h, w), np.float32)
    if kind == "buds":
        y0 = (add + H0 * 0.58) * k
        stem = np.clip((yy - y0) / (h * 0.12), 0, 1)
    return {"arr": arr, "w": w, "h": h, "flower": flower, "spec": spec, "phase": phase, "stem": stem,
            "kind": kind, "X": xx, "Y": yy}


def render_photo(P, t, u, v, z):
    s = max(W / P["w"], H / P["h"])
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * P["w"], cw / 2), P["w"] - cw / 2)
    cy = min(max(v * P["h"], ch / 2), P["h"] - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    ix = np.clip(gx.astype(np.int32), 0, P["w"] - 1)
    iy = np.clip(gy.astype(np.int32), 0, P["h"] - 1)
    fl = P["flower"][iy, ix]
    # petals breathe: a slow, small radial-ish warp inside the flower mask
    dx = fl * (3.2 * np.sin(0.9 * t + gy * 0.004) + 1.4 * np.sin(1.7 * t + gx * 0.006))
    dy = fl * (2.6 * np.sin(0.75 * t + gx * 0.005 + 1.0))
    if P["kind"] == "buds":
        st = P["stem"][iy, ix]
        dx = dx + st * (7.0 * np.sin(1.25 * t + gy * 0.0025) + 3.0 * np.sin(2.1 * t + gx * 0.004))
    img = bilinear(P["arr"], gx + dx, gy + dy)
    # dew twinkle: highlights pulse with a per-drop phase
    sp = P["spec"][iy, ix]
    ph = P["phase"][iy, ix]
    tw = np.clip(np.sin(2.2 * t + ph), 0, 1) ** 3
    img = img + (sp * tw)[..., None] * np.array([120, 112, 104], np.float32)
    return img


# shots: (key, start, end, [(t, u, v, z), ...])
SHOTS = [
    ("tulip", 0.0, 7.7, [(0.0, 0.52, 0.47, 1.00), (7.7, 0.56, 0.52, 1.12)]),          # slow push-in into the bloom
    ("ranun", 7.4, 15.2, [(7.4, 0.50, 0.40, 1.04), (10.8, 0.52, 0.41, 1.06), (15.2, 0.60, 0.44, 1.20)]),  # push toward the big bloom
    ("tulip", 14.9, 19.6, [(14.9, 0.40, 0.58, 1.14), (19.6, 0.62, 0.56, 1.14)]),      # lateral slide over the lower petals
    ("ranun", 19.3, 24.1, [(19.3, 0.50, 0.40, 1.10), (24.1, 0.50, 0.36, 1.00)]),      # pull-back over the swaying buds
    ("tulip", 23.8, 30.0, [(23.8, 0.54, 0.62, 1.10), (30.0, 0.52, 0.58, 1.00)]),      # gentle pull-back
]
PASSES = [7.55, 15.05, 19.45, 23.95]   # out-of-focus petal crossing the lens at each cut


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
        a = Image.fromarray(np.clip(shot_img(A, i1, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(16 * p))
        b = Image.fromarray(np.clip(shot_img(A, i2, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(16 * (1 - p)))
        img = np.asarray(Image.blend(a, b, ease_in_out(p)), np.float32)
    else:
        img = shot_img(A, act[0], t)
        if soften > 0.01:
            img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(11 * soften)), np.float32)
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # foreground bokeh (depth layer, slower near the edges)
    for (x, y, r, spd, ph, a, kind) in A["bokeh"]:
        bx = (x + spd * 0.6 * t + 14 * math.sin(t * 0.4 + ph)) % (W + 200) - 100
        by = (y - spd * t) % (H + 200) - 100
        put(f, A["bk"][kind][r], bx - r, by - r, a * (0.65 + 0.35 * math.sin(t * 0.9 + ph)))
    # out-of-focus petal passing across the lens at each cut
    for tp in PASSES:
        p = (t - (tp - 0.55)) / 1.1
        if 0 <= p <= 1:
            e = ease_in_out(p)
            pet = A["petal"]
            x = W + 200 - (W + pet.width + 400) * e
            put(f, pet, x, H * 0.18 + 240 * math.sin(p * math.pi) - pet.height / 4, 0.92 * math.sin(p * math.pi))
    return f


def build():
    A = {"P": {k: build_photo(k) for k in PHOTOS}}
    rng = np.random.default_rng(21)
    A["grain"] = [rng.normal(0, 2.2, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.30 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    A["bk"] = {}
    for kind, col in (("blush", (240, 184, 192)), ("gold", (244, 220, 170))):
        A["bk"][kind] = {}
        for r in (18, 30, 46, 64):
            m = Image.new("L", (2 * r, 2 * r), 0)
            ImageDraw.Draw(m).ellipse((r * 0.25, r * 0.25, r * 1.75, r * 1.75), fill=150)
            im = Image.new("RGBA", (2 * r, 2 * r), col + (0,))
            im.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.22)))
            A["bk"][kind][r] = im
    A["bokeh"] = [(rng.uniform(0, W), rng.uniform(0, H), int(rng.choice([18, 30, 46, 64])), rng.uniform(8, 26),
                   rng.uniform(0, 6.28), rng.uniform(0.10, 0.28), rng.choice(["blush", "gold"])) for _ in range(16)]
    # out-of-focus foreground petal (soft rose ellipse with a lighter edge)
    pw, ph = 1500, 1000
    m = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(m).ellipse((150, 150, pw - 150, ph - 150), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(90))
    gy = np.linspace(0, 1, ph, dtype=np.float32)[:, None, None]
    col = np.array([150, 64, 86], np.float32) * (1 - gy) + np.array([92, 30, 48], np.float32) * gy
    col = np.broadcast_to(col, (ph, pw, 3))
    petal = Image.fromarray(np.concatenate([col, np.asarray(m, np.float32)[..., None]], -1).astype(np.uint8), "RGBA")
    A["petal"] = petal.rotate(-18, resample=Image.BICUBIC, expand=True)

    logo = Image.open(LOGO).convert("RGBA")   # official file, untouched, directly on the dark scene
    A["logo"] = logo.resize((290, round(logo.height * 290 / logo.width)), Image.LANCZOS)
    A["logo_big"] = logo.resize((480, round(logo.height * 480 / logo.width)), Image.LANCZOS)

    # hook
    A["just"] = [T("JUST TWO", caslon(170), IVORY, tracking=tr) for tr in (60, 44, 30, 18, 8, 2)]
    A["openings"] = T("openings this", eph(132), BLUSH)
    A["friday_h"] = T("FRIDAY", caslon(190), "champagne", tracking=6)
    # closed Monday
    A["mon"] = T(f"{CLOSED[0]}, {CLOSED[1].upper()}", fig(40, 600), IVORY, tracking=10)
    A["closed"] = T("Clinic closed", caslon(132), IVORY)
    A["happy"] = T("Happy Thanksgiving", eph(110), BLUSH)
    # date (right-aligned)
    A["fri"] = T("Friday", caslon(210), IVORY)
    A["oct"] = T(OPEN_DATE, eph(140), "champagne")
    A["two"] = T("2 OPENINGS", fig(36, 700), SAGE, tracking=12)
    # times
    A["first"] = T("FIRST OPENING", fig(36, 600), IVORY, tracking=12)
    A["second"] = T("SECOND OPENING", fig(36, 600), IVORY, tracking=12)
    A["t"] = [(T(tm, caslon(330), "champagne"), T(ap, fig(76, 500), IVORY, tracking=2)) for tm, ap in TIMES]
    # services
    A["menu"] = T("Treatments", eph(150), "champagne")
    A["menu_sub"] = T("AVAILABLE FRIDAY", fig(30, 700), SAGE, tracking=12)
    A["svc"] = [(base.fit(lambda s, n=n: T(n, caslon(s), IVORY), 74, 900),
                 T(sub, fig(28, 700), "champagne", tracking=10) if sub else None) for n, sub in SERVICES]
    # summary
    A["s_avail"] = T("Available appointments", eph(118), "champagne")
    A["s_day"] = T(f"{OPEN_DAY}, {OPEN_DATE.upper()}", fig(44, 600), IVORY, tracking=10)
    A["s_t"] = [(T(tm, caslon(124), "champagne"), T(ap, fig(42, 500), IVORY, tracking=2)) for tm, ap in TIMES]
    A["s_who"] = T(f"with {THERAPIST}", fig(42, 500), IVORY, tracking=2)
    A["s_addr"] = T(f"{CLINIC}  ·  {ADDRESS}", fig(31, 500), IVORY, tracking=1)
    A["s_closed"] = T(f"Closed Monday, {CLOSED[1]}  ·  Happy Thanksgiving", fig(30, 500), BLUSH, tracking=1)
    A["s_cta"] = T("DM TO BOOK", fig(56, 700), IVORY, tracking=16)
    return A


def frame_at(t, A):
    soften = math.exp(-((t - 11.35) / 0.4) ** 2) + 0.8 * math.exp(-((t - 15.95) / 0.35) ** 2)   # times "from nowhere"
    f = background(t, A, soften)
    wash(f, 0, 1150, NIGHT, 0.62, 0.0)
    if 19.4 < t < 24.0:
        a = ease_out(prog(t, 19.4, 0.4)) * (1 - ease_in_out(prog(t, 23.6, 0.4)))
        wash(f, 0, 950, NIGHT, 0.45, 0.45, a)
        wash(f, 950, 1350, NIGHT, 0.45, 0.0, a)

    if t < 7.6:   # logo through the opening
        p = ease_out(prog(t, 0.1, 0.8)) * (1 - ease_in_out(prog(t, 7.1, 0.4)))
        lg = A["logo"]
        put(f, lg, (W - lg.width) / 2, 90 + 10 * (1 - p), p)

    # ---- hook 0–3.7: tracking reveal, script write-on, gold blur->sharp from small
    if t < 3.9:
        a = 1 - ease_in_out(prog(t, 3.4, 0.4))
        track_in(f, A["just"], W / 2, 450, prog(t, 0.1, 0.9), a)
        wipe(f, A["openings"], W / 2 - A["openings"].adv / 2, 575, prog(t, 0.8, 0.9), a)
        sharp_in(f, A["friday_h"], W / 2 - A["friday_h"].adv / 2, 745, prog(t, 1.35, 0.8), a, scale_from=0.86, blur=16)
        line(f, W / 2, 785, 300 * ease_in_out(prog(t, 2.0, 0.6)), GOLD_LINE, a)

    # ---- closed Monday 3.7–7.5
    if 3.7 <= t < 7.6:
        a = 1 - ease_in_out(prog(t, 7.1, 0.4))
        letters(f, A["mon"], W / 2 - A["mon"].adv / 2, 440, 3.8, t, a, step=0.03)
        p = prog(t, 4.25, 0.8)
        sharp_in(f, A["closed"], W / 2 - A["closed"].adv / 2, 600, p, a, blur=10)
        line(f, W / 2, 642, 340 * ease_in_out(prog(t, 4.9, 0.6)), GOLD_LINE, a)
        wipe(f, A["happy"], W / 2 - A["happy"].adv / 2, 750, prog(t, 5.2, 0.9), a)

    # ---- Friday date 7.8–10.9: right-aligned, slides in from the right
    if 7.8 <= t < 11.0:
        a = 1 - ease_in_out(prog(t, 10.55, 0.4))
        XR = W - 96
        letters(f, A["two"], XR - A["two"].adv, 380, 7.85, t, a, step=0.03)
        p = prog(t, 8.05, 0.8)
        e = ease_out(p)
        sharp_in(f, A["fri"], XR - A["fri"].adv + 90 * (1 - e), 600, p, a, blur=12)
        p = prog(t, 8.6, 0.9)
        wipe(f, A["oct"], XR - A["oct"].adv, 760, p, a)
        L = 420 * ease_in_out(prog(t, 9.1, 0.7))
        line(f, XR - L, 800, L, GOLD_LINE, a, centered=False)

    # ---- 11:30 a.m. 11.1–15.0: "from nowhere", scale up from small; camera pushes into the bloom
    if 11.1 <= t < 15.1:
        a = 1 - ease_in_out(prog(t, 14.65, 0.4))
        p = ease_out(prog(t, 11.15, 0.5))
        put_c(f, A["first"], 360, p * a, dy=12 * (1 - p))
        tm, ap = A["t"][0]
        tot = tm.adv + 20 + ap.adv
        x = W / 2 - tot / 2
        sharp_in(f, tm, x, 680, prog(t, 11.35, 0.8), a, scale_from=0.82, blur=18)
        p = ease_out(prog(t, 11.9, 0.5))
        put_x(f, ap, x + tm.adv + 20, 680, p * a, dy=18 * (1 - p))
        line(f, W / 2, 730, 560 * ease_in_out(prog(t, 12.1, 0.8)), GOLD_LINE, a)

    # ---- 12:45 p.m. 15.4–19.4: left-aligned, slides in from the left over the lower petals
    if 15.3 <= t < 19.5:
        a = 1 - ease_in_out(prog(t, 19.05, 0.4))
        X = 96
        p = ease_out(prog(t, 15.4, 0.5))
        put_x(f, A["second"], X, 360, p * a, dx=-30 * (1 - p))
        tm, ap = A["t"][1]
        p = prog(t, 15.95, 0.8)
        sharp_in(f, tm, X - 70 * (1 - ease_out(p)), 680, p, a, blur=16)
        p = ease_out(prog(t, 16.45, 0.5))
        put_x(f, ap, X + tm.adv + 20, 680, p * a, dx=-24 * (1 - p))
        L = 520 * ease_in_out(prog(t, 16.7, 0.8))
        line(f, X, 730, L, GOLD_LINE, a, centered=False)

    # ---- services 19.5–23.9: each one slides in from the right, blur -> sharp
    if 19.5 <= t < 24.0:
        a = ease_out(prog(t, 19.5, 0.4)) * (1 - ease_in_out(prog(t, 23.5, 0.4)))
        wipe(f, A["menu"], W / 2 - A["menu"].adv / 2, 330, prog(t, 19.55, 0.8), a)
        letters(f, A["menu_sub"], W / 2 - A["menu_sub"].adv / 2, 395, 19.8, t, a, step=0.02)
        y = 535
        for i, (nm, sub) in enumerate(A["svc"]):
            t0 = 20.15 + i * 0.6
            p = prog(t, t0, 0.6)
            e = ease_out(p)
            sharp_in(f, nm, W / 2 - nm.adv / 2 + 70 * (1 - e), y, p, a, blur=10)
            if sub is not None:
                pp = ease_out(prog(t, t0 + 0.3, 0.5))
                put_c(f, sub, y + 46, pp * a)
                y += 150
            else:
                y += 112

    # ---- summary 24.0–30
    if t >= 24.0:
        p0 = ease_out(prog(t, 24.05, 0.7))
        wash(f, 0, 1080, NIGHT, 0.35, 0.50, p0)
        wash(f, 1080, 1500, NIGHT, 0.50, 0.0, p0)
        lg = A["logo_big"]
        put(f, lg, (W - lg.width) / 2, 70 + 14 * (1 - p0), p0)
        y = 70 + lg.height + 120
        wipe(f, A["s_avail"], W / 2 - A["s_avail"].adv / 2, y, prog(t, 24.4, 0.9))
        letters(f, A["s_day"], W / 2 - A["s_day"].adv / 2, y + 85, 24.9, t, step=0.02)
        parts = A["s_t"]
        gap = 64
        tot = sum(tm.adv + 12 + ap.adv for tm, ap in parts) + gap
        x = W / 2 - tot / 2
        for k, (tm, ap) in enumerate(parts):
            sharp_in(f, tm, x, y + 235, prog(t, 25.4 + k * 0.35, 0.6), scale_from=0.9)
            p = ease_out(prog(t, 25.7 + k * 0.35, 0.4))
            put_x(f, ap, x + tm.adv + 12, y + 235, p, dy=12 * (1 - p))
            x += tm.adv + 12 + ap.adv + gap
        line(f, W / 2, y + 280, 380 * ease_in_out(prog(t, 26.2, 0.6)), GOLD_LINE)
        p = ease_out(prog(t, 26.4, 0.5))
        put_c(f, A["s_who"], y + 350, p, dy=14 * (1 - p))
        put_c(f, A["s_addr"], y + 405, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 26.8, 0.5))
        put_c(f, A["s_closed"], y + 458, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 27.2, 0.6))
        put_c(f, A["s_cta"], y + 560, p, dy=16 * (1 - p))
        L = 330 * ease_in_out(prog(t, 27.5, 0.7)) * (0.86 + 0.14 * math.sin(max(0.0, t - 28.2) * 2.4))
        line(f, W / 2, y + 586, L, GOLD_LINE, p, thick=3)
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


# ---------------------------------------------------------------- music (§46: new direction)
BPM = 72
BEAT = 60 / BPM          # 0.833 s
BAR = 3 * BEAT           # waltz, 2.5 s
N = {"Db2": 69.30, "Ab2": 103.83, "Bb1": 58.27, "F2": 87.31, "Gb2": 92.50, "Eb2": 77.78, "Ab1": 51.91,
     "Db3": 138.59, "F3": 174.61, "Ab3": 207.65, "C4": 261.63, "Bb2": 116.54, "Db4": 277.18, "Eb4": 311.13,
     "Gb3": 185.00, "Bb3": 233.08, "Eb3": 155.56, "C3": 130.81, "Gb4": 369.99, "F4": 349.23, "Ab4": 415.30,
     "Bb4": 466.16, "C5": 523.25, "Db5": 554.37, "Eb5": 622.25, "F5": 698.46, "Ab5": 830.61}
CHORDS = [  # (bass, upper dyad/triad) per bar — Dbmaj9, Bbm9, Gbmaj7, Absus->Ab
    ("Db2", ["Ab3", "C4", "F3"]),
    ("Bb1", ["Db4", "F3", "Ab3"]),
    ("Gb2", ["Bb3", "Db4", "F3"]),
    ("Ab2", ["C4", "Eb4", "Ab3"]),
]
SONG = [0, 1, 2, 3, 0, 1, 2, 3, 2, 3, 0, 0]       # 12 bars = 30 s, ends home on D-flat
MELODY = [  # (bar, beat, note, length in beats) — a simple, singable waltz line
    (0, 0, "F5", 2), (0, 2, "Eb5", 1), (1, 0, "Db5", 2), (1, 2, "C5", 1), (2, 0, "Bb4", 3), (3, 0, "C5", 2), (3, 2, "Eb5", 1),
    (4, 0, "F5", 2), (4, 2, "Ab5", 1), (5, 0, "F5", 2), (5, 2, "Eb5", 1), (6, 0, "Db5", 3), (7, 0, "Eb5", 3),
    (8, 0, "Db5", 2), (8, 2, "Bb4", 1), (9, 0, "C5", 2), (9, 2, "Eb5", 1), (10, 0, "F5", 3), (11, 0, "Db5", 3),
]
PINGS = [(1.35, 2793.8), (4.25, 2217.5), (8.05, 2489.0), (11.35, 2793.8), (15.95, 3322.4), (20.15, 2217.5),
         (20.75, 2489.0), (21.35, 2793.8), (21.95, 3322.4), (25.4, 2793.8), (25.75, 3322.4), (27.2, 2217.5)]


def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(72)
    out = np.zeros(n)
    strings = np.zeros(n)

    def add(buf, at, sig):
        i = int(at * sr)
        if i >= n or i + len(sig) <= 0:
            return
        m = min(len(sig), n - i)
        buf[i:i + m] += sig[:m]

    def piano(f0, vel, dur=3.0):
        tt = np.arange(int(dur * sr)) / sr
        s = np.zeros_like(tt)
        for k in range(1, 9):
            fk = k * f0 * math.sqrt(1 + 0.00035 * k * k)
            s += (1 / k ** 1.6) * np.exp(-tt * (0.9 + 0.75 * k)) * np.sin(2 * np.pi * fk * tt + k)
        felt = np.exp(-tt * 60) * rng.normal(0, 1, len(tt)) * 0.02   # soft hammer thump
        env = np.clip(tt / 0.006, 0, 1) * np.clip((dur - tt) / 0.3, 0, 1)
        return vel * env * (s + felt)

    for b, ci in enumerate(SONG):
        t0 = b * BAR
        bass, upper = CHORDS[ci]
        add(out, t0, piano(N[bass], 0.30, 2.6))
        add(out, t0 + 0.01, piano(N[bass] * 2, 0.10, 2.4))
        for beat in (1, 2):
            for j, nn in enumerate(upper):
                add(out, t0 + beat * BEAT + 0.008 * j, piano(N[nn], 0.085, 1.4))
        # strings swell from Friday (bar 3) onward: slow attack, soft saw-ish timbre
        if b >= 3:
            tt = np.arange(int((BAR + 1.2) * sr)) / sr
            env = np.clip(tt / 1.1, 0, 1) * np.clip((BAR + 1.2 - tt) / 1.0, 0, 1)
            for nn in [bass] + upper:
                f0 = N[nn] * (2 if nn == bass else 1)
                sig = sum((0.6 / k) * np.sin(2 * np.pi * k * f0 * tt + 0.3 * np.sin(2 * np.pi * 5.2 * tt)) for k in range(1, 5))
                add(strings, t0 - 0.3, 0.035 * env * sig)
    for bar, beat, nn, ln in MELODY:
        add(out, bar * BAR + beat * BEAT + 0.02, piano(N[nn], 0.20, ln * BEAT + 1.6))
    # rain / dew texture: band-passed noise + sparse water-drop plinks
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    X *= np.exp(-((np.log(fr + 1) - np.log(4200)) / 0.7) ** 2)
    rain = np.fft.irfft(X, n)
    rain = rain / np.abs(rain).max() * 0.035
    drops = np.zeros(n)
    for at in np.sort(rng.uniform(0, DURATION, 46)):
        f0 = rng.uniform(1400, 2600)
        tt = np.arange(int(0.12 * sr)) / sr
        fsw = f0 * (1 + 0.5 * np.exp(-tt * 60))
        add(drops, at, rng.uniform(0.02, 0.05) * np.sin(2 * np.pi * np.cumsum(fsw) / sr) * np.exp(-tt * 38))
    pings = np.zeros(n)
    for at, f0 in PINGS:
        tt = np.arange(int(2.4 * sr)) / sr
        env = np.exp(-tt * 2.6) * np.clip(tt / 0.002, 0, 1)
        add(pings, at, env * (np.sin(2 * np.pi * f0 * tt) + 0.3 * np.sin(2 * np.pi * f0 * 2.32 * tt) * np.exp(-tt * 4)))
    mix = out + strings + rain + drops + 0.06 * pings
    # simple stereo: piano centre, strings slightly wide, drops panned randomly via delay
    left = mix + 0.5 * np.roll(strings, int(0.009 * sr)) + 0.6 * np.roll(drops, int(0.004 * sr))
    right = mix + 0.5 * np.roll(strings, int(0.015 * sr)) + 0.6 * drops
    st = np.stack([left, right], 1)
    st *= (np.clip((DURATION - t) / 2.2, 0, 1) * np.clip(t / 0.2, 0, 1))[:, None]
    st = st / np.max(np.abs(st)) * 10 ** (-6 / 20)
    data = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def poster(path, PW=1080, PH=1350):
    """Static 4:5 feed post on the dewy tulip, information over the dark headroom."""
    P = build_photo("tulip")
    s = PW / P["w"]
    img = Image.fromarray(np.clip(P["arr"], 0, 255).astype(np.uint8)).resize((PW, int(P["h"] * s)), Image.LANCZOS)
    top = int(img.height * 0.14)
    img = img.crop((0, top, PW, top + PH))
    f = img.convert("RGBA")
    g = np.concatenate([np.linspace(0.62, 0.48, 760), np.linspace(0.48, 0.0, 240)]).astype(np.float32)[:, None].repeat(PW, 1)
    sh = Image.new("RGBA", (PW, 1000), NIGHT + (0,))
    sh.putalpha(Image.fromarray((g * 255).astype(np.uint8)))
    f.alpha_composite(sh, (0, 0))
    logo = Image.open(LOGO).convert("RGBA")
    lg = logo.resize((290, round(logo.height * 290 / logo.width)), Image.LANCZOS)
    f.alpha_composite(lg, ((PW - lg.width) // 2, 36))
    cx = PW / 2

    def c(tx, by):
        f.alpha_composite(tx.img, (int(cx - tx.adv / 2 - tx.pad), int(by - tx.asc)))
    y = 36 + lg.height + 95
    c(T("Available appointments", eph(96), "champagne"), y)
    c(T(f"{OPEN_DAY}, {OPEN_DATE.upper()}", fig(38, 600), IVORY, tracking=10), y + 68)
    parts = [(T(tm, caslon(118), "champagne"), T(ap, fig(40, 500), IVORY, tracking=2)) for tm, ap in TIMES]
    gap = 64
    tot = sum(tm.adv + 12 + ap.adv for tm, ap in parts) + gap
    x = cx - tot / 2
    for tm, ap in parts:
        f.alpha_composite(tm.img, (int(x - tm.pad), int(y + 200 - tm.asc)))
        f.alpha_composite(ap.img, (int(x + tm.adv + 12 - ap.pad), int(y + 200 - ap.asc)))
        x += tm.adv + 12 + ap.adv + gap
    d = ImageDraw.Draw(f)
    d.line([(cx - 190, y + 238), (cx + 190, y + 238)], fill=GOLD_LINE + (255,), width=2)
    c(T("Foot & Hand Reflexology  ·  Facial Reflexology (Bergman Method)", fig(27, 500), IVORY, tracking=1), y + 288)
    c(T("Reflexology Lymph Drainage (RLD)  ·  Spanish Massage", fig(27, 500), IVORY, tracking=1), y + 328)
    c(T(f"with {THERAPIST}  ·  {ADDRESS}", fig(30, 600), IVORY, tracking=1), y + 386)
    c(T(f"Closed Monday, {CLOSED[1]}  ·  Happy Thanksgiving", fig(27, 500), BLUSH, tracking=1), y + 430)
    c(T("DM TO BOOK", fig(46, 700), IVORY, tracking=14), y + 510)
    d.line([(cx - 130, y + 530), (cx + 130, y + 530)], fill=GOLD_LINE + (255,), width=3)
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
        ts = [float(x) for x in sys.argv[2:]] or [2.9, 6.4, 10.3, 13.8, 18.4, 23.2, 29.0]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(qc, f"v2-{s:04.1f}s.png"))
        return
    if mode == "audio":
        synth_audio(os.path.join(OUT_DIR, "qc", "v2.wav"))
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
