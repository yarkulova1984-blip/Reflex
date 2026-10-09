"""THE PURE ESCAPE — Available Appointments — Thursday, October 15 & Saturday, October 17, 2026
Thursday: 3:00 p.m. · 4:45 p.m. · 6:30 p.m.   Saturday: 12:45 p.m. · 2:00 p.m.

Concept "Thursday or Saturday?": a direct-choice question hook, then each day builds its own
vertical timeline (a fine line with nodes; each time lands on a node while the photos change
behind it), services rise out of the steam, and a light summary carries the logo.
Owner's 6 photos (hand reflexology x 2, sunlit foot, steam + towel, facial reflexology, and the
foot photo with the reflex-map labels already removed).
Living background: steam rolls and drifts (masked flow warp + scrolling wisps), dust glitters
in the sunbeam, warm light breathes; camera push-in / slide / pull-back, cross-defocus.
Palette: espresso + warm white + terracotta + warm gold. Type: Instrument Serif (roman +
italic accents) + Hanken Grotesk (clean grotesque). No script this time.
Music (§46, new): 104 BPM, A-flat major, fingerpicked nylon guitar (Karplus-Strong), upright
bass pluck, brushed snare swishes on 2 & 4, vinyl crackle, harp-like glissandi on reveals.

  python3 production/oct15_pe_thu_sat.py stills [t ...]
  python3 production/oct15_pe_thu_sat.py video
  python3 production/oct15_pe_thu_sat.py poster
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
from oct10_pe_saturday import extend_top  # noqa: E402
from oct16_amt_thanksgiving import (Text, bilinear, ease_in_out, ease_out, letters, line, prog, put,  # noqa: E402
                                    put_c, put_x, rise, sharp_in, wash, wipe)

ROOT = base.ROOT
FONTS = base.FONTS
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
P15 = os.path.join(ROOT, "brand", "photos", "pe-oct15")
P16 = os.path.join(ROOT, "brand", "photos", "amt-oct16")      # generic photos, no clinic branding
OUT_DIR = base.OUT_DIR
NAME = "2026-10-15-pe-available-appointments"
W, H, FPS = 1080, 1920, 30
DURATION = 34.0

WARM = (250, 242, 230)
ESP = (40, 28, 22)
TERRA = (204, 112, 72)
NIGHT = (14, 9, 6)
GOLD_LINE = (214, 168, 104)
base.GOLDS["amber"] = ((250, 220, 168), (222, 166, 92), (160, 106, 46))
base.GOLDS["bronze"] = ((176, 128, 62), (138, 92, 40), (96, 60, 24))

# ---------------------------------------------------------------- facts (owner-provided; verified)
CLINIC = "The Pure Escape"
ADDRESS = "698 Corydon Ave, Winnipeg"
THERAPIST = "Zarina, RCRT"
DAYS = [("Thursday", "OCTOBER 15", [("3:00", "p.m."), ("4:45", "p.m."), ("6:30", "p.m.")]),   # 2026-10-15 is a Thursday
        ("Saturday", "OCTOBER 17", [("12:45", "p.m."), ("2:00", "p.m.")])]                   # 2026-10-17 is a Saturday
SERVICES = [  # same list as Oct 13–14 (owner: "same services")
    ("Reflexology Lymph Drainage", "RLD"),
    ("Foot Reflexology", ""),
    ("Facial Reflexology", "BERGMAN METHOD"),
    ("Spanish Massage", ""),
    ("Ultimate Escape Package", ""),
    ("Combo", "90 MINUTES"),
]


def serif(size, italic=False):
    return ImageFont.truetype(os.path.join(FONTS, "InstrumentSerif-Italic.ttf" if italic else "InstrumentSerif-Regular.ttf"), size)


def grot(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "HankenGrotesk[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def T(txt, fnt, fill, tracking=0, dark=True):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT if dark else None)


# ---------------------------------------------------------------- living photos
# key: (path, headroom, headroom tone, grade, effect)
PHOTOS = {
    "sun": (os.path.join(P15, "foot-sunlit.jpg"), 0.42, "dark", 1.00, "beam"),
    "hdark": (os.path.join(P15, "hands-dark.jpg"), 0.40, "dark", 1.10, None),
    "foot": (os.path.join(P16, "foot-thumb-clean.png"), 0.62, "dark", 0.80, None),
    "hand": (os.path.join(P15, "hand-thumb-walk.jpg"), 0.62, "dark", 0.82, None),
    "facial": (os.path.join(P16, "facial-temple.jpg"), 0.46, "dark", 0.92, None),
    "steam": (os.path.join(P15, "steam-back-towel.jpg"), 0.05, "dark", 1.00, "steam"),
    "hand_l": (os.path.join(P15, "hand-thumb-walk.jpg"), 1.10, "cream", 1.00, None),   # light version for the summary
}


def _noise(h, w, seed, scale):
    rng = np.random.default_rng(seed)
    small = rng.normal(0, 1, (max(2, h // scale), max(2, w // scale))).astype(np.float32)
    return np.asarray(Image.fromarray(small, "F").resize((w, h), Image.BICUBIC), np.float32)


def build_photo(key):
    path, head, tone, grade, fx = PHOTOS[key]
    im = Image.open(path).convert("RGB")
    H0, W0 = im.height, im.width
    im, add = extend_top(im, head, False)
    arr = np.asarray(im, np.float32).copy()
    col = np.array([238, 228, 212] if tone == "cream" else [26, 17, 12], np.float32)
    g = np.clip(1 - np.arange(add + 50, dtype=np.float32) / (add + 50), 0, 1) ** 0.7
    arr[:add + 50] = arr[:add + 50] * (1 - g[:, None, None]) + col * g[:, None, None]
    arr *= np.array([1.03, 0.99, 0.94], np.float32) * grade
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    k = max(W / im.width, H / im.height) * 1.22
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=2.4, percent=65, threshold=2))
    h, w = big.height, big.width
    P = {"arr": np.asarray(big, np.float32), "w": w, "h": h, "fx": fx}
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if fx == "steam":
        # the steam lives in the upper-left two-thirds of the photo, above the back
        sm = np.clip(1 - (yy / h - 0.20) / 0.45, 0, 1) * np.clip(1.15 - xx / w, 0, 1)
        P["mask"] = sm
        P["wisp"] = np.clip(_noise(h * 2, w, 11, 90) * 0.6 + _noise(h * 2, w, 12, 30) * 0.4, 0, None)
    if fx == "beam":
        # warm sunbeam crossing from upper right; dust glitters inside it
        d = ((xx / w - 0.95) * 0.8 + (yy / h - 0.40) * 0.6)
        P["beam"] = np.exp(-(d / 0.10) ** 2) * np.clip(yy / h * 2.0, 0, 1)
    return P


def render_photo(P, t, u, v, z):
    s = max(W / P["w"], H / P["h"])
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * P["w"], cw / 2), P["w"] - cw / 2)
    cy = min(max(v * P["h"], ch / 2), P["h"] - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    ix = np.clip(gx.astype(np.int32), 0, P["w"] - 1)
    iy = np.clip(gy.astype(np.int32), 0, P["h"] - 1)
    if P["fx"] == "steam":
        m = P["mask"][iy, ix]
        gx = gx + m * (9 * np.sin(gy * 0.006 - t * 0.9) + 5 * np.sin(gy * 0.017 + gx * 0.004 - t * 1.6))
        gy = gy + m * (7 * np.sin(gx * 0.005 + t * 0.7) + 30 * t % 1 * 0)   # rolling, no jumps
    img = bilinear(P["arr"], gx, gy)
    if P["fx"] == "steam":
        off = int((t * 38) % P["h"])                      # wisps drift upward
        wy = (iy + off) % P["wisp"].shape[0]
        wv = P["wisp"][wy, ix] * P["mask"][iy, ix]
        img = img + (wv * 26)[..., None] * np.array([1.0, 0.72, 0.48], np.float32)
    if P["fx"] == "beam":
        b = P["beam"][iy, ix]
        pulse = 0.85 + 0.15 * math.sin(t * 0.8)
        img = img * (1 + 0.10 * b[..., None] * pulse)
    return img


SHOTS = [  # (key, start, end, [(t, u, v, z), ...])
    ("sun", 0.0, 3.9, [(0.0, 0.50, 0.50, 1.00), (3.9, 0.50, 0.54, 1.10)]),
    ("hdark", 3.6, 7.6, [(3.6, 0.46, 0.46, 1.06), (7.6, 0.50, 0.48, 1.14)]),
    ("foot", 7.3, 11.2, [(7.3, 0.50, 0.40, 1.02), (11.2, 0.53, 0.42, 1.10)]),
    ("hand", 10.9, 14.3, [(10.9, 0.42, 0.44, 1.08), (14.3, 0.58, 0.44, 1.08)]),
    ("facial", 14.0, 17.4, [(14.0, 0.52, 0.42, 1.10), (17.4, 0.50, 0.40, 1.02)]),
    ("steam", 17.1, 25.7, [(17.1, 0.50, 0.56, 1.16), (25.7, 0.50, 0.50, 1.00)]),
    ("hand_l", 25.4, 34.0, [(25.4, 0.50, 0.53, 1.08), (34.0, 0.50, 0.55, 1.00)]),
]
# timeline nodes: day header time, then each time's arrival
THU_T = [5.1, 6.6, 8.1]
SAT_T = [12.3, 13.9]
TL_X = 168                   # timeline x
TL_Y0 = 580                  # first node baseline
TL_STEP = 160


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
            img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8 * soften)), np.float32)
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    dust = 1.0 if t < 3.9 else 0.45
    for (x, y, spd, ph, a) in A["motes"]:
        mx = x + 20 * math.sin(t * 0.3 + ph)
        my = (y - spd * t) % H
        put(f, A["mote"], mx, my, dust * a * (0.45 + 0.55 * max(0.0, math.sin(t * 1.6 + ph))))
    return f


def build():
    A = {"P": {k: build_photo(k) for k in PHOTOS}}
    rng = np.random.default_rng(15)
    A["grain"] = [rng.normal(0, 2.4, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.24 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    m = Image.new("L", (20, 20), 0)
    ImageDraw.Draw(m).ellipse((8, 8, 12, 12), fill=235)
    mote = Image.new("RGBA", (20, 20), (255, 226, 170, 0))
    mote.putalpha(m.filter(ImageFilter.GaussianBlur(2)))
    A["mote"] = mote
    A["motes"] = [(rng.uniform(300, W), rng.uniform(0, H), rng.uniform(4, 12), rng.uniform(0, 6.28), rng.uniform(0.3, 0.7)) for _ in range(30)]
    logo = Image.open(LOGO).convert("RGBA")     # official file, untouched
    A["logo_big"] = logo.resize((470, round(logo.height * 470 / logo.width)), Image.LANCZOS)
    A["logo"] = logo.resize((300, round(logo.height * 300 / logo.width)), Image.LANCZOS)
    # soft, edgeless light glow so the logo's black line art reads on the dark opening (no plate)
    pad = 260
    gl = Image.new("L", (A["logo"].width + 2 * pad, A["logo"].height + 2 * pad), 0)
    ImageDraw.Draw(gl).ellipse((pad - 40, pad - 30, gl.width - pad + 40, gl.height - pad + 30), fill=200)
    glow = Image.new("RGBA", gl.size, (250, 240, 222, 0))
    glow.putalpha(gl.filter(ImageFilter.GaussianBlur(70)))   # edgeless: fades to zero well inside the canvas
    A["logo_glow"] = glow

    # hook
    A["q1"] = T("Thursday", serif(230), WARM)
    A["q_or"] = T("or", serif(150, True), "amber")
    A["q2"] = T("Saturday?", serif(230), WARM)
    A["q_sub"] = T("5 OPENINGS  ·  THU & SAT", grot(36, 700), "amber", tracking=12)
    # day timelines
    A["day"] = []
    for name, date, times in DAYS:
        A["day"].append({
            "name": T(name, serif(190), WARM),
            "date": T(date, grot(36, 700), "amber", tracking=14),
            "times": [(T(tm, serif(170), "amber"), T(ap, grot(48, 600), WARM, tracking=2)) for tm, ap in times],
        })
    # services
    A["menu"] = T("Treatments", serif(170, True), "amber")
    A["menu_sub"] = T("THURSDAY & SATURDAY", grot(32, 700), WARM, tracking=12)
    A["svc"] = [(T(n, serif(80), WARM), T(sub, grot(28, 700), "amber", tracking=10) if sub else None) for n, sub in SERVICES]
    # summary (light scene)
    A["s_avail"] = T("Available appointments", serif(104, True), ESP, dark=False)
    A["s_day"] = [T(f"{n.upper()}, {d}", grot(30, 800), ESP, tracking=6, dark=False) for n, d, _ in DAYS]
    A["s_t"] = [[(T(tm, serif(92), "bronze", dark=False), T(ap, grot(30, 600), ESP, dark=False)) for tm, ap in times] for _, _, times in DAYS]
    A["s_who"] = T(f"with {THERAPIST}", grot(40, 600), ESP, tracking=2, dark=False)
    A["s_addr"] = T(f"{CLINIC}  ·  {ADDRESS}", grot(32, 500), ESP, tracking=1, dark=False)
    A["s_cta"] = T("DM TO BOOK", grot(56, 800), ESP, tracking=16, dark=False)
    return A


def timeline(f, A, k, t, t_head, nodes, a):
    """Day header + a vertical line growing down through each node; each time lands on its node."""
    D = A["day"][k]
    p = prog(t, t_head, 0.8)
    sharp_in(f, D["name"], TL_X - 30, 360, p, a, scale_from=1.06, blur=14)
    letters(f, D["date"], TL_X - 22, 430, t_head + 0.35, t, a, step=0.03)
    # line grows to the deepest reached node
    reach = TL_Y0 - 70
    for i, tn in enumerate(nodes):
        reach = TL_Y0 - 70 + (i * TL_STEP + 80) * ease_in_out(prog(t, tn - 0.45, 0.45)) if t >= tn - 0.45 else reach
    L = reach - (TL_Y0 - 120)
    if L > 1 and a > 0:
        f.alpha_composite(Image.new("RGBA", (2, int(L)), GOLD_LINE + (int(200 * a),)), (TL_X - 1, int(TL_Y0 - 120)))
    for i, tn in enumerate(nodes):
        if t < tn - 0.1:
            continue
        y = TL_Y0 + i * TL_STEP
        pp = ease_out(prog(t, tn - 0.1, 0.35))
        r = 9 * pp
        if r > 0.5:
            dot = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
            ImageDraw.Draw(dot).ellipse((20 - r, 20 - r, 20 + r, 20 + r), fill=GOLD_LINE + (int(255 * a),))
            put(f, dot, TL_X - 20, y - 58 - 20)
        tm, ap = D["times"][i]
        pr = prog(t, tn, 0.6)
        sharp_in(f, tm, TL_X + 52 + 60 * (1 - ease_out(pr)), y, pr, a, blur=14)
        p2 = ease_out(prog(t, tn + 0.35, 0.4))
        put_x(f, ap, TL_X + 52 + tm.adv + 16, y, p2 * a, dy=14 * (1 - p2))


def frame_at(t, A):
    soften = sum(math.exp(-((t - r) / 0.3) ** 2) for r in THU_T + SAT_T) * 0.6
    f = background(t, A, soften)
    if t < 25.5:
        wash(f, 0, 1250, NIGHT, 0.66, 0.0)
        wash(f, 0, 1150, NIGHT, 0.30, 0.0, 1.0 if 3.6 < t < 17.4 else 0.0)

    # ---- hook 0–3.7: a direct choice question
    if t < 3.9:
        a = 1 - ease_in_out(prog(t, 3.4, 0.4))
        p = ease_out(prog(t, 0.05, 0.8))
        put(f, A["logo_glow"], (W - A["logo_glow"].width) / 2, 110 - 260, p * a)
        put(f, A["logo"], (W - A["logo"].width) / 2, 110 + 10 * (1 - p), p * a)
        sharp_in(f, A["q1"], W / 2 - A["q1"].adv / 2, 560, prog(t, 0.2, 0.7), a, scale_from=1.08, blur=16)
        wipe(f, A["q_or"], W / 2 - A["q_or"].adv / 2, 680, prog(t, 0.75, 0.5), a)
        sharp_in(f, A["q2"], W / 2 - A["q2"].adv / 2, 870, prog(t, 1.05, 0.7), a, scale_from=1.08, blur=16)
        letters(f, A["q_sub"], W / 2 - A["q_sub"].adv / 2, 960, 1.8, t, a, step=0.025)

    # ---- Thursday timeline 3.8–10.5
    if 3.8 <= t < 10.7:
        a = 1 - ease_in_out(prog(t, 10.2, 0.45))
        timeline(f, A, 0, t, 3.9, THU_T, a)
    # ---- Saturday timeline 10.7–17.0
    if 10.6 <= t < 17.2:
        a = 1 - ease_in_out(prog(t, 16.7, 0.45))
        timeline(f, A, 1, t, 10.8, SAT_T, a)

    # ---- services 17.3–25.4: each rises out of its baseline, centred, over the steam
    if 17.2 <= t < 25.6:
        a = ease_out(prog(t, 17.25, 0.4)) * (1 - ease_in_out(prog(t, 25.1, 0.4)))
        wipe(f, A["menu"], W / 2 - A["menu"].adv / 2, 330, prog(t, 17.35, 0.8), a)
        letters(f, A["menu_sub"], W / 2 - A["menu_sub"].adv / 2, 400, 17.7, t, a, step=0.02)
        y = 530
        for i, (nm, sub) in enumerate(A["svc"]):
            t0 = 18.2 + i * 0.6
            rise(f, nm, W / 2 - nm.adv / 2, y, prog(t, t0, 0.55), a)
            if sub is not None:
                letters(f, sub, W / 2 - sub.adv / 2, y + 44, t0 + 0.3, t, a, step=0.02)
                y += 132
            else:
                y += 100

    # ---- summary 25.5–34 (light, logo directly on the scene)
    if t >= 25.5:
        p0 = ease_out(prog(t, 25.55, 0.7))
        wash(f, 0, 1300, (246, 238, 224), 0.72, 0.30, p0)
        wash(f, 1300, 1600, (246, 238, 224), 0.30, 0.0, p0)
        lg = A["logo_big"]
        put(f, lg, (W - lg.width) / 2, 60 + 14 * (1 - p0), p0)
        y = 60 + lg.height + 110
        wipe(f, A["s_avail"], W / 2 - A["s_avail"].adv / 2, y, prog(t, 25.9, 0.9))
        for k in range(2):
            cx = 290 if k == 0 else 790
            dl = A["s_day"][k]
            letters(f, dl, cx - dl.adv / 2, y + 95, 26.4 + k * 0.4, t, step=0.015)
            for j, (tm, ap) in enumerate(A["s_t"][k]):
                by = y + 215 + j * 105
                tot = tm.adv + 10 + ap.adv
                x = cx - tot / 2
                sharp_in(f, tm, x, by, prog(t, 26.9 + k * 0.4 + j * 0.22, 0.5), scale_from=0.9)
                pp = ease_out(prog(t, 27.1 + k * 0.4 + j * 0.22, 0.4))
                put_x(f, ap, x + tm.adv + 10, by, pp, dy=10 * (1 - pp))
        L = 300 * ease_in_out(prog(t, 26.6, 0.6))
        if L > 1:
            f.alpha_composite(Image.new("RGBA", (2, int(L)), (176, 128, 62, 230)), (W // 2 - 1, int(y + 70)))
        line(f, W / 2, y + 470, 420 * ease_in_out(prog(t, 28.3, 0.6)), (176, 128, 62))
        p = ease_out(prog(t, 28.5, 0.5))
        put_c(f, A["s_who"], y + 540, p, dy=14 * (1 - p))
        put_c(f, A["s_addr"], y + 593, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 29.0, 0.6))
        put_c(f, A["s_cta"], y + 700, p, dy=16 * (1 - p))
        L = 330 * ease_in_out(prog(t, 29.3, 0.7)) * (0.86 + 0.14 * math.sin(max(0.0, t - 30.0) * 2.4))
        line(f, W / 2, y + 726, L, (176, 128, 62), p, thick=3)
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


# ---------------------------------------------------------------- music (§46: new direction)
BPM = 104
BEAT = 60 / BPM
BAR = 4 * BEAT
NT = {"Ab1": 51.91, "Db2": 69.30, "Eb2": 77.78, "F2": 87.31, "Ab2": 103.83,
      "Eb3": 155.56, "F3": 174.61, "G3": 196.00, "Ab3": 207.65, "Bb3": 233.08, "C4": 261.63, "Db4": 277.18,
      "Eb4": 311.13, "F4": 349.23, "G4": 392.00, "Ab4": 415.30, "Bb4": 466.16, "C5": 523.25, "Eb5": 622.25, "F5": 698.46,
      "Ab5": 830.61}
CHORDS = [("Ab1", "Ab2", ["Eb3", "Ab3", "C4", "G4"]),      # Abmaj7
          ("F2", "F2", ["F3", "Ab3", "Eb4", "G4"]),        # Fm9
          ("Db2", "Db2", ["F3", "Ab3", "C4", "Eb4"]),      # Dbmaj9
          ("Eb2", "Eb2", ["G3", "Bb3", "C4", "Eb4"])]      # Eb6
SONG = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 2, 0]      # 15 bars ≈ 34.6 s, ends on A-flat
GLISS = [0.2, 3.9, 5.1, 6.6, 8.1, 10.8, 12.3, 13.9, 17.35, 25.6]


def ks(f0, dur, sr, bright=0.6, decay=0.9965, seed=0):
    """Karplus-Strong plucked string, block-vectorised, pitch-corrected by resampling."""
    rng = np.random.default_rng(seed)
    N = int(math.ceil(sr / f0))
    total = int(dur * sr * (sr / N) / f0) + 2 * N
    out = np.zeros(total + 2 * N)
    exc = rng.uniform(-1, 1, N)
    sm = np.convolve(exc, np.ones(5) / 5, mode="same")
    out[:N] = bright * exc + (1 - bright) * sm
    out[N] = decay * 0.5 * (out[0] + out[N - 1])
    start = N + 1
    while start < total:
        end = min(start + N, total)
        out[start:end] = decay * 0.5 * (out[start - N:end - N] + out[start - N - 1:end - N - 1])
        start = end
    y = out[:total]
    ratio = f0 / (sr / N)                 # play faster/slower to hit the exact pitch
    L = int(dur * sr)
    idx = np.arange(L) * ratio
    idx = idx[idx < len(y) - 1]
    res = np.interp(idx, np.arange(len(y)), y)
    env = np.clip((len(res) - np.arange(len(res))) / (0.05 * sr), 0, 1)
    return res * env


def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(104)
    gtr = np.zeros(n)
    bass = np.zeros(n)
    brush = np.zeros(n)
    fx = np.zeros(n)

    def add(buf, at, sig):
        i = int(at * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        m = min(len(sig), n - i)
        buf[i:i + m] += sig[:m]

    seed = [0]

    def pluck(f0, vel, dur=1.6, bright=0.55):
        seed[0] += 1
        return vel * ks(f0, dur, sr, bright=bright, seed=seed[0])

    def swish():
        L = int(0.32 * sr)
        x = rng.normal(0, 1, L)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(L, 1 / sr)
        X *= np.exp(-((np.log(fr + 1) - np.log(3500)) / 0.7) ** 2)
        y = np.fft.irfft(X, L)
        tt = np.arange(L) / sr
        env = np.clip(tt / 0.035, 0, 1) * np.exp(-tt * 9)
        return y / (np.abs(y).max() + 1e-9) * env

    pick = [(0, "b"), (1, 2), (2, 1), (3, 3), (4, "b2"), (5, 2), (6, 1), (7, 0)]   # Travis-style eighths
    for b, ci in enumerate(SONG):
        t0 = b * BAR
        root, b2, voi = CHORDS[ci]
        add(bass, t0, pluck(NT[root] * 2, 0.55, 2.0, bright=0.2))
        add(bass, t0 + 2 * BEAT, pluck(NT[b2] * (1.5 if b2 == root else 2), 0.40, 1.6, bright=0.2))
        for k, what in pick:
            at = t0 + k * BEAT / 2 + (0.014 if k % 2 else 0.0)
            if what == "b":
                add(gtr, at, pluck(NT[voi[0]], 0.30, 1.8, 0.45))
            elif what == "b2":
                add(gtr, at, pluck(NT[voi[1]], 0.26, 1.6, 0.45))
            else:
                add(gtr, at, pluck(NT[voi[what]] * (2 if what == 3 and NT[voi[3]] < 300 else 1), 0.22, 1.4, 0.6))
        if t0 >= 3.5:
            for beat in (1, 3):
                add(brush, t0 + beat * BEAT, 0.22 * swish())
            for k in range(8):
                add(brush, t0 + k * BEAT / 2 + 0.01, 0.05 * swish()[: int(0.08 * sr)])
    # harp-like glissandi on day headers and every time reveal
    scale = [NT["Ab3"], NT["C4"], NT["Eb4"], NT["F4"], NT["Ab4"], NT["C5"], NT["Eb5"], NT["F5"], NT["Ab5"]]
    for at in GLISS:
        for j, f0 in enumerate(scale[::(1 if at < 25 else 1)]):
            add(fx, at - 0.32 + j * 0.035, pluck(f0, 0.12, 1.4, bright=0.75))
    # vinyl crackle: sparse clicks + a little hiss
    crackle = np.zeros(n)
    for at in rng.uniform(0, DURATION, 260):
        L = int(0.002 * sr)
        add(crackle, at, rng.uniform(-1, 1) * rng.uniform(0.05, 0.25) * np.exp(-np.arange(L) / (0.0004 * sr)))
    hiss = rng.normal(0, 1, n)
    X = np.fft.rfft(hiss)
    fr = np.fft.rfftfreq(n, 1 / sr)
    X *= np.clip((fr - 3000) / 4000, 0, 1) * np.exp(-fr / 12000)
    hiss = np.fft.irfft(X, n)
    hiss = hiss / np.abs(hiss).max() * 0.008

    mix = 0.9 * gtr + 0.8 * bass + brush + 0.9 * fx + 0.35 * crackle + hiss
    left = mix + 0.12 * np.roll(gtr, int(0.011 * sr)) + 0.15 * fx
    right = mix + 0.12 * np.roll(gtr, int(0.017 * sr)) + 0.15 * np.roll(fx, int(0.02 * sr))
    st = np.stack([left, right], 1)
    st *= (np.clip((DURATION - t) / 2.0, 0, 1) * np.clip(t / 0.1, 0, 1))[:, None]
    st = st / np.max(np.abs(st)) * 10 ** (-6 / 20)
    data = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def poster(path, PW=1080, PH=1350):
    """Static 4:5 feed post: calm linen headroom for the information, hand reflexology below."""
    im = Image.open(os.path.join(P15, "hand-thumb-walk.jpg")).convert("RGB")
    im, add = extend_top(im, 0.70, True)
    arr = np.asarray(im, np.float32).copy()
    col = np.array([240, 232, 218], np.float32)
    g = np.clip(1 - np.arange(add + 90, dtype=np.float32) / (add + 90), 0, 1) ** 0.55
    arr[:add + 90] = arr[:add + 90] * (1 - g[:, None, None]) + col * g[:, None, None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    s = PW / im.width
    img = im.resize((PW, int(im.height * s)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.2, percent=60, threshold=2))
    img = img.crop((0, 0, PW, PH))
    f = img.convert("RGBA")
    logo = Image.open(LOGO).convert("RGBA")
    lg = logo.resize((250, round(logo.height * 250 / logo.width)), Image.LANCZOS)
    f.alpha_composite(lg, ((PW - lg.width) // 2, 26))
    cx = PW / 2

    def c(tx, by, x=None):
        x = cx if x is None else x
        f.alpha_composite(tx.img, (int(x - tx.adv / 2 - tx.pad), int(by - tx.asc)))
    y = 26 + lg.height + 70
    c(T("Available appointments", serif(80, True), ESP, dark=False), y)
    for k, (name, date, times) in enumerate(DAYS):
        bx = 290 if k == 0 else 790
        c(T(f"{name.upper()}, {date}", grot(25, 800), ESP, tracking=5, dark=False), y + 60, bx)
        for j, (tm, ap) in enumerate(times):
            a1, a2 = T(tm, serif(70), "bronze", dark=False), T(ap, grot(25, 600), ESP, dark=False)
            tot = a1.adv + 8 + a2.adv
            x = bx - tot / 2
            by = y + 140 + j * 72
            f.alpha_composite(a1.img, (int(x - a1.pad), int(by - a1.asc)))
            f.alpha_composite(a2.img, (int(x + a1.adv + 8 - a2.pad), int(by - a2.asc)))
    d = ImageDraw.Draw(f)
    d.line([(cx, y + 36), (cx, y + 300)], fill=(176, 128, 62, 255), width=2)
    c(T("RLD  ·  Foot Reflexology  ·  Facial Reflexology (Bergman Method)", grot(23, 600), ESP, tracking=1, dark=False), y + 345)
    c(T("Spanish Massage  ·  Ultimate Escape Package  ·  Combo (90 min)", grot(23, 600), ESP, tracking=1, dark=False), y + 379)
    c(T(f"with {THERAPIST}  ·  {CLINIC}  ·  {ADDRESS}", grot(24, 700), ESP, tracking=1, dark=False), y + 425)
    c(T("DM TO BOOK", grot(40, 800), ESP, tracking=14, dark=False), y + 495)
    d.line([(cx - 115, y + 512), (cx + 115, y + 512)], fill=(176, 128, 62, 255), width=3)
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
        ts = [float(x) for x in sys.argv[2:]] or [2.9, 6.0, 9.6, 13.0, 15.8, 22.6, 32.0]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(qc, f"pe15-{s:04.1f}s.png"))
        return
    if mode == "audio":
        synth_audio(os.path.join(OUT_DIR, "qc", "pe15.wav"))
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
    Image.fromarray(frame_at(33.5, A)).save(os.path.join(OUT_DIR, f"{NAME}-story.jpg"), quality=93)
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
