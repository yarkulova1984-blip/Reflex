"""Available Appointments — Wednesday, October 7, 2026 — v2 "Window Light".

Concept: a warm plaster wall in a treatment room. Morning sun comes through an arched
window, and soft leaf shadows sway across the light. Dust drifts in the beam. Bold sans,
an elegant script accent and amber highlights give the type hierarchy. Circled icons
introduce the services.

  python3 production/oct7_v2_window_light.py stills
  python3 production/oct7_v2_window_light.py video
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")
LOGO = os.path.join(ROOT, "brand", "the-pure-escape-logo.png")
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-07-available-appointments-v2"

W, H, FPS = 1080, 1920, 30
DURATION = 25.0
X0 = 96

GREEN = (27, 64, 44)
AMBER = (196, 122, 44)
CREAM = (250, 243, 230)
INK = (40, 38, 34)

# ---------------------------------------------------------------- facts (never edit without the owner)
DAY, MONTH, DAYNUM = "WEDNESDAY", "OCTOBER", "7"
TIMES = [("11:00", "a.m."), ("12:45", "p.m."), ("2:30", "p.m.")]
SERVICES = [  # (bold part, regular part, sub-line, icon)
    ("Foot", " Reflexology", None, "foot"),
    ("Hand", " Reflexology", None, "hand"),
    ("Facial", " Reflexology", "Bergman Method", "face"),
    ("Spanish", " Massage", None, "hands"),
    ("Ultimate Escape", " Package", None, "spark"),
]
THERAPIST = "Zarina, RCRT"
ADDRESS = "698 Corydon Ave"


# ---------------------------------------------------------------- type
def jost(size, weight="Medium"):
    f = ImageFont.truetype(os.path.join(FONTS, "Jost[wght].ttf"), size)
    f.set_variation_by_name(weight)
    return f


def script(size):
    return ImageFont.truetype(os.path.join(FONTS, "GreatVibes-Regular.ttf"), size)


class Text:
    def __init__(self, txt, fnt, fill, tracking=0):
        asc, desc = fnt.getmetrics()
        pad = int(fnt.size * 0.25)  # room for script swashes
        width = (sum(fnt.getlength(c) for c in txt) + tracking * (len(txt) - 1)) if tracking else fnt.getlength(txt)
        self.img = Image.new("RGBA", (math.ceil(width) + 2 * pad, asc + desc + pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        if tracking:
            x = pad
            for c in txt:
                d.text((x, asc), c, font=fnt, fill=fill, anchor="ls")
                x += fnt.getlength(c) + tracking
        else:
            d.text((pad, asc), txt, font=fnt, fill=fill, anchor="ls")
        self.asc, self.pad = asc, pad
        self.adv = width
        self.w, self.h = self.img.size


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    p = min(max(p, 0.0), 1.0)
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def prog(t, start, dur):
    return min(max((t - start) / dur, 0.0), 1.0)


def with_alpha(img, a):
    if a >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


def put(frame, img, x, y, alpha=1.0):
    if alpha > 0.003:
        frame.alpha_composite(with_alpha(img, alpha), (int(round(x)), int(round(y))))


def put_text(frame, tx, x, baseline, alpha=1.0, dx=0.0, dy=0.0):
    put(frame, tx.img, x - tx.pad + dx, baseline - tx.asc + dy, alpha)


def rise_text(frame, tx, x, baseline, p, alpha=1.0, dy=0.0):
    """Mask reveal: text rises into its own line box."""
    if p <= 0:
        return
    if p >= 1:
        return put_text(frame, tx, x, baseline, alpha, dy=dy)
    top = baseline - tx.asc
    off = (1 - ease_out(p)) * tx.h * 0.9
    vis = int(tx.h - off)
    if vis > 0:
        put(frame, tx.img.crop((0, 0, tx.w, vis)), x - tx.pad, top + off + dy, alpha)


def wipe_text(frame, tx, x, baseline, p, alpha=1.0, dy=0.0):
    """Left-to-right reveal, like a pen writing."""
    if p <= 0:
        return
    vis = int(tx.w * ease_in_out(p))
    if vis > 0:
        put(frame, tx.img.crop((0, 0, vis, tx.h)), x - tx.pad, baseline - tx.asc + dy, alpha)


def rect(frame, x, y, w, h, color, alpha=1.0):
    if w > 0.5 and h > 0.5 and alpha > 0:
        frame.alpha_composite(Image.new("RGBA", (int(w), int(h)), color + (int(255 * alpha),)), (int(x), int(y)))


# ---------------------------------------------------------------- icons (4x supersampled)
def _canvas(size):
    s = size * 4
    return Image.new("RGBA", (s, s), (0, 0, 0, 0)), s


def _done(im, size):
    return im.resize((size, size), Image.LANCZOS)


def ring(size, color, p, width=3):
    im, s = _canvas(size)
    if p > 0:
        ImageDraw.Draw(im).arc((6, 6, s - 6, s - 6), -90, -90 + 360 * ease_out(p), fill=color, width=width * 4)
    return _done(im, size)


def icon(kind, size, color):
    im, s = _canvas(size)
    d = ImageDraw.Draw(im)
    c = color + (255,)
    if kind == "foot":
        sole = []
        for i in range(80):  # right footprint: wide ball, narrow waist, round heel
            a = 2 * math.pi * i / 80
            y = math.cos(a)                      # +1 top (ball), -1 bottom (heel)
            half = 0.15 + 0.03 * y - 0.045 * math.exp(-((y + 0.15) / 0.3) ** 2)
            x = math.sin(a) * half + (0.02 if math.sin(a) > 0 else 0) * (y > 0)
            sole.append((s * (0.50 + x), s * (0.60 - 0.30 * y)))
        d.polygon(sole, fill=c)
        for dx, dy, r in [(-0.12, .19, .062), (-0.015, .15, .046), (.065, .155, .040), (.13, .18, .034), (.185, .225, .029)]:
            cx, cy = s * (0.5 + dx), s * dy
            d.ellipse((cx - s * r, cy - s * r * 1.15, cx + s * r, cy + s * r * 1.15), fill=c)
    elif kind == "hand":
        d.rounded_rectangle((s * .30, s * .44, s * .70, s * .86), radius=s * .1, fill=c)
        for i, (x, top) in enumerate([(.31, .20), (.41, .14), (.51, .16), (.61, .24)]):
            d.rounded_rectangle((s * x, s * top, s * (x + .085), s * .55), radius=s * .045, fill=c)
        thumb = [(s * .32, s * .60), (s * .18, s * .44), (s * .14, s * .38), (s * .20, s * .34), (s * .36, s * .50)]
        d.polygon(thumb, fill=c)
        d.ellipse((s * .12, s * .32, s * .22, s * .42), fill=c)
    elif kind == "face":
        lw = int(s * .075)
        d.ellipse((s * .22, s * .12, s * .78, s * .88), outline=c, width=lw)
        for x in (.38, .62):
            d.arc((s * (x - .09), s * .38, s * (x + .09), s * .52), 20, 160, fill=c, width=lw)
        d.arc((s * .39, s * .55, s * .61, s * .71), 30, 150, fill=c, width=lw)
    elif kind == "hands":  # lotus: calm / body treatment
        lw = int(s * .065)
        base = (s * .5, s * .78)
        for ang, ln, wd in [(0, .50, .17), (-38, .42, .14), (38, .42, .14), (-72, .33, .11), (72, .33, .11)]:
            a = math.radians(ang - 90)
            pts = []
            for k in range(41):
                u = k / 40
                along = u * ln * s
                side = math.sin(math.pi * u) ** 0.9 * wd * s
                pts.append((along, side))
            poly = [(x, y) for x, y in pts] + [(x, -y) for x, y in pts[::-1]]
            poly = [(base[0] + x * math.cos(a) - y * math.sin(a), base[1] + x * math.sin(a) + y * math.cos(a)) for x, y in poly]
            d.line(poly + [poly[0]], fill=c, width=lw, joint="curve")
        d.line((s * .2, s * .84, s * .8, s * .84), fill=c, width=lw)
    elif kind == "spark":
        def star(cx, cy, r):
            pts = []
            for i in range(8):
                a = math.pi / 4 * i - math.pi / 2
                rr = r if i % 2 == 0 else r * 0.28
                pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
            d.polygon(pts, fill=c)
        star(s * .44, s * .56, s * .30)
        star(s * .74, s * .28, s * .14)
    elif kind == "calendar":
        lw = int(s * .07)
        d.rounded_rectangle((s * .14, s * .22, s * .86, s * .86), radius=s * .1, outline=c, width=lw)
        d.line((s * .14, s * .42, s * .86, s * .42), fill=c, width=lw)
        for x in (.34, .66):
            d.line((s * x, s * .12, s * x, s * .30), fill=c, width=lw)
    elif kind == "clock":
        lw = int(s * .07)
        d.ellipse((s * .14, s * .14, s * .86, s * .86), outline=c, width=lw)
        d.line((s * .5, s * .5, s * .5, s * .28), fill=c, width=lw)
        d.line((s * .5, s * .5, s * .66, s * .56), fill=c, width=lw)
    elif kind == "pin":
        lw = int(s * .07)
        cx, cy, r = s * .5, s * .40, s * .26
        d.arc((cx - r, cy - r, cx + r, cy + r), 140, 400, fill=c, width=lw)
        for a in (140, 40):
            p = (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
            d.line((p, (cx, s * .92)), fill=c, width=lw)
        rr = s * .08
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=c, width=lw)
    return _done(im, size)


def brush_stroke(length, thick, color):
    """Tapered hand-drawn underline."""
    s = 4
    im = Image.new("RGBA", (int(length * s) + 40, int(thick * 3 * s) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    n = 120
    top, bot = [], []
    for i in range(n + 1):
        u = i / n
        x = 20 + u * length * s
        y = 20 + thick * 1.5 * s - math.sin(u * math.pi * 0.9) * thick * 0.9 * s
        w = thick * s * (0.25 + 0.75 * math.sin(math.pi * min(1, u * 1.15)) ** 0.6)
        top.append((x, y - w / 2))
        bot.append((x, y + w / 2))
    d.polygon(top + bot[::-1], fill=color + (255,))
    return im.resize((im.width // s, im.height // s), Image.LANCZOS)


# ---------------------------------------------------------------- background: window light on plaster
def fractal_noise(h, w, seed, scales=(3, 8, 24, 80, 260), weights=(1, .7, .45, .3, .2)):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    for sc, wt in zip(scales, weights):
        small = rng.normal(0, 1, (max(2, h // sc), max(2, w // sc))).astype(np.float32)
        im = Image.fromarray(small, "F").resize((w, h), Image.BICUBIC)
        out += wt * np.asarray(im)
    return out / np.abs(out).max()


def branch_shadow(seed, size, sway):
    rng = np.random.default_rng(seed)
    Wb, Hb = size
    im = Image.new("L", (Wb, Hb), 0)
    d = ImageDraw.Draw(im)
    for b in range(5):
        x0, y0 = rng.uniform(0.35, 1.05) * Wb, rng.uniform(-0.05, 0.75) * Hb
        ang = math.radians(rng.uniform(120, 220) + sway * (8 + 4 * b))
        L = rng.uniform(0.35, 0.65) * Hb
        pts = []
        for i in range(40):
            u = i / 39
            a = ang + 0.5 * u * (1 if b % 2 else -1)
            pts.append((x0 + math.cos(a) * L * u, y0 + math.sin(a) * L * u))
        d.line(pts, fill=255, width=9)
        for i in range(4, 40, 3):
            px, py = pts[i]
            for side in (-1, 1):
                la = ang + side * math.radians(rng.uniform(35, 65)) + 0.5 * (i / 39) * (1 if b % 2 else -1)
                la += math.radians(sway * rng.uniform(4, 10))
                ll, lw = rng.uniform(70, 140), rng.uniform(22, 38)
                cxl, cyl = px + math.cos(la) * ll * 0.55, py + math.sin(la) * ll * 0.55
                poly = []
                for k in range(30):
                    t = 2 * math.pi * k / 30
                    ex, ey = math.cos(t) * ll / 2, math.sin(t) * lw / 2 * (1 - 0.35 * math.cos(t))
                    poly.append((cxl + ex * math.cos(la) - ey * math.sin(la), cyl + ex * math.sin(la) + ey * math.cos(la)))
                d.polygon(poly, fill=255)
    return im


def build_bg():
    B = {}
    noise = fractal_noise(H, W, 11)
    fine = fractal_noise(H, W, 5, scales=(1, 2, 4), weights=(1, .6, .4))
    shade = np.array([214, 190, 156], np.float32)
    lit = np.array([255, 236, 198], np.float32)
    tex = (noise * 7 + fine * 3)[..., None]
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    B["shade"] = shade + tex - yy * 18
    B["lit"] = lit + tex * 0.8
    # arched two-pane window, sheared like late-morning sun, very soft edges
    big = Image.new("L", (W + 600, H + 600), 0)
    d = ImageDraw.Draw(big)
    for x in (420, 900):
        d.rectangle((x, 520, x + 420, 1700), fill=255)
        d.ellipse((x, 310, x + 420, 730), fill=255)
    big = big.transform(big.size, Image.AFFINE, (1, 0.38, -380, 0, 1, 0), resample=Image.BICUBIC)
    B["window"] = np.asarray(big.filter(ImageFilter.GaussianBlur(22)), np.float32) / 255
    poses = []
    for sway in (-1, 1):
        sh = branch_shadow(21, (W + 200, H + 200), sway)
        a = np.asarray(sh.filter(ImageFilter.GaussianBlur(9)), np.float32) / 255
        b = np.asarray(branch_shadow(34, (W + 200, H + 200), sway * 0.7).filter(ImageFilter.GaussianBlur(26)), np.float32) / 255
        poses.append(np.clip(a * 0.8 + b * 0.55, 0, 1))
    B["leaves"] = poses
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    B["vignette"] = (1 - 0.22 * (((xx - W * .55) / W) ** 2 + ((yy - H * .4) / H) ** 2) * 2.2)[..., None]
    rng = np.random.default_rng(9)
    B["grain"] = [rng.normal(0, 3.5, (H, W, 1)).astype(np.float32) for _ in range(3)]
    am = Image.new("L", (28, 28), 0)
    ImageDraw.Draw(am).ellipse((9, 9, 19, 19), fill=235)
    B["mote"] = Image.new("RGBA", (28, 28), (255, 250, 236, 0))
    B["mote"].putalpha(am.filter(ImageFilter.GaussianBlur(3.5)))
    # out-of-focus foreground leaves (depth), alpha blurred only
    fg = Image.new("L", (W + 300, 900), 0)
    fd = ImageDraw.Draw(fg)
    for cx, cy, ln, wd, ang in [(980, 640, 620, 170, -62), (1180, 520, 520, 140, -100), (760, 820, 520, 150, -30)]:
        poly = []
        a = math.radians(ang)
        for k in range(60):
            tt = 2 * math.pi * k / 60
            ex, ey = math.cos(tt) * ln / 2, math.sin(tt) * wd / 2 * (1 - 0.3 * math.cos(tt))
            poly.append((cx + ex * math.cos(a) - ey * math.sin(a), cy + ex * math.sin(a) + ey * math.cos(a)))
        fd.polygon(poly, fill=255)
    B["fg"] = Image.new("RGBA", fg.size, (24, 48, 33, 0))
    B["fg"].putalpha(fg.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.8)))
    B["motes"] = [(rng.uniform(250, 1080), rng.uniform(200, 1700), rng.uniform(4, 14), rng.uniform(0, 6.28), rng.uniform(.4, 1))
                  for _ in range(34)]
    return B


def background(t, B):
    light_on = ease_in_out(prog(t, 0.0, 1.6))
    wx = int(300 - 40 * t / DURATION * 4)       # sun slowly travels
    wy = int(300 - 10 * t / DURATION * 4)
    win = B["window"][wy:wy + H, wx:wx + W]
    sway = 0.5 + 0.5 * math.sin(t * 0.9)
    lx, ly = int(100 + 6 * math.sin(t * 0.5)), int(100 + 4 * math.cos(t * 0.4))
    leaves = B["leaves"][0][ly:ly + H, lx:lx + W] * (1 - sway) + B["leaves"][1][ly:ly + H, lx:lx + W] * sway
    mask = (win * (1 - 0.72 * leaves) * (0.15 + 0.85 * light_on))[..., None]
    img = B["shade"] + (B["lit"] - B["shade"]) * mask
    img = img * B["vignette"] + B["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, spd, ph, a) in B["motes"]:
        mx = x + 18 * math.sin(t * 0.3 + ph)
        my = (y - spd * t) % H
        m = win[int(min(max(my, 0), H - 1)), int(min(max(mx, 0), W - 1))]
        if m > 0.2:
            put(f, B["mote"], mx, my, a * m * light_on * 0.9)
    put(f, B["fg"], -40 - 10 * math.sin(t * 0.35) - 14 * t / DURATION, H - 760 + 6 * math.sin(t * 0.5))
    return f, mask


# ---------------------------------------------------------------- assets
def build():
    A = build_bg()
    A["brand"] = Text("THE PURE ESCAPE", jost(30, "Medium"), GREEN, tracking=9)
    avail_font = jost(168, "Bold")
    while avail_font.getlength("AVAILABLE") > 880:
        avail_font = jost(avail_font.size - 2, "Bold")
    A["available"] = Text("AVAILABLE", avail_font, GREEN)
    appt = Text("appointments", script(150), AMBER)
    A["appointments"] = appt
    A["underline"] = brush_stroke(470, 14, AMBER)
    A["day"] = Text(DAY, jost(50, "SemiBold"), GREEN, tracking=12)
    A["month"] = Text(MONTH + " ", jost(132, "Bold"), GREEN)
    A["daynum"] = Text(DAYNUM, jost(132, "Bold"), AMBER)

    A["ic_cal"] = icon("calendar", 40, AMBER)
    A["ic_clock"] = icon("clock", 40, AMBER)
    A["ic_pin"] = icon("pin", 44, AMBER)
    A["date_label"] = Text(f"{DAY}, {MONTH} {DAYNUM}", jost(38, "SemiBold"), GREEN, tracking=4)
    A["open"] = Text("Open", jost(76, "Bold"), GREEN)
    A["times_script"] = Text("times", script(118), AMBER)
    tf = jost(230, "Bold")
    A["times"] = []
    for num, suf in TIMES:
        chars, x = [], 0
        for ch in num:
            chars.append((x, Text(ch, tf, GREEN)))
            x += tf.getlength(ch)
        A["times"].append((chars, x, Text(suf, jost(62, "Medium"), AMBER)))

    A["choose"] = Text("Choose your", jost(76, "Bold"), GREEN)
    A["treatment"] = Text("treatment", script(124), AMBER)
    A["svc"] = []
    for bold, reg, sub, kind in SERVICES:
        A["svc"].append((Text(bold, jost(54, "SemiBold"), GREEN), Text(reg, jost(54, "Regular"), INK),
                         Text(sub, jost(34, "Regular"), AMBER, tracking=2) if sub else None,
                         icon(kind, 64, GREEN)))

    logo = Image.open(LOGO).convert("RGBA")
    lw = 660
    A["logo"] = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    A["with"] = Text("with ", jost(46, "Regular"), INK)
    A["therapist"] = Text(THERAPIST, jost(46, "SemiBold"), GREEN)
    A["address"] = Text(ADDRESS, jost(42, "Regular"), INK)
    A["end_date"] = Text(f"{DAY} · {MONTH} {DAYNUM}", jost(36, "SemiBold"), AMBER, tracking=6)
    A["end_times"] = [(Text(n, jost(96, "Bold"), GREEN), Text(s, jost(38, "Medium"), AMBER)) for n, s in TIMES]
    A["cta"] = Text("BOOK YOUR APPOINTMENT", jost(40, "SemiBold"), CREAM, tracking=3)
    return A


# ---------------------------------------------------------------- timeline
def light_sweep(f, t, start, dur):
    """Warm light bloom crossing the frame: the graphic wipe between beats."""
    p = prog(t, start, dur)
    if p <= 0 or p >= 1:
        return
    cx = -500 + ease_in_out(p) * (W + 1000)
    band = Image.new("L", (W, H), 0)
    ImageDraw.Draw(band).polygon([(cx - 260, 0), (cx + 160, 0), (cx + 560, H), (cx + 140, H)], fill=255)
    band = band.filter(ImageFilter.GaussianBlur(120))
    glow = Image.new("RGBA", (W, H), (255, 240, 205, 0))
    glow.putalpha(band.point(lambda v: int(v * 0.85 * math.sin(math.pi * p))))
    f.alpha_composite(glow)


def frame_at(t, A):
    f, _ = background(t, A)

    # ---- Beat 1: hook (0 – 4.6)
    if t < 4.7:
        def out(k):
            q = ease_in_out(prog(t, 4.0 + 0.08 * k, 0.45))
            return 1 - q, -60 * q
        a, dy = out(0)
        put_text(f, A["brand"], X0, 330 + 16 * (1 - ease_out(prog(t, 0.4, .6))), ease_out(prog(t, 0.4, .6)) * a, dy=dy)
        a, dy = out(1)
        rise_text(f, A["available"], X0 - 8, 700, prog(t, 0.6, 0.75), a, dy)
        a, dy = out(2)
        wipe_text(f, A["appointments"], 330, 835, prog(t, 1.15, 0.9), a, dy)
        p = prog(t, 1.85, 0.55)
        if p > 0:
            ul = A["underline"]
            put(f, ul.crop((0, 0, max(1, int(ul.width * ease_in_out(p))), ul.height)), 360, 850 + dy, a)
        a, dy = out(3)
        p = ease_out(prog(t, 2.3, 0.6))
        put_text(f, A["day"], X0, 1050 + 24 * (1 - p), p * a, dy=dy)
        rise_text(f, A["month"], X0 - 6, 1200, prog(t, 2.55, 0.7), a, dy)
        p = prog(t, 2.95, 0.6)
        if p > 0:
            s = 0.6 + 0.4 * ease_out(p)
            dn = A["daynum"].img
            dn = dn.resize((int(dn.width * s), int(dn.height * s)), Image.LANCZOS)
            bx = X0 - 6 + A["month"].adv - A["daynum"].pad * s
            put(f, dn, bx, 1200 - A["daynum"].asc * s + dy, ease_out(p) * a)

    # ---- Beat 2: times (4.6 – 11.5)
    if 4.6 <= t < 11.6:
        q = ease_in_out(prog(t, 10.9, 0.5))
        a, dy = 1 - q, -60 * q
        p = ease_out(prog(t, 4.6, 0.6))
        put(f, ring(76, AMBER, prog(t, 4.6, 0.8)), X0, 300 + dy, a)
        put(f, A["ic_cal"], X0 + 18, 318 + dy, p * a)
        put_text(f, A["date_label"], X0 + 100 - 24 * (1 - p), 352, p * a, dy=dy)
        p = prog(t, 5.0, 0.6)
        rise_text(f, A["open"], X0 - 4, 560, p, a, dy)
        wipe_text(f, A["times_script"], X0 + A["open"].adv + 20, 575, prog(t, 5.3, 0.8), a, dy)
        for i, (chars, adv, suf) in enumerate(A["times"]):
            start = 5.8 + 0.75 * i
            base = 870 + 262 * i
            for k, (cx, ch) in enumerate(chars):
                rise_text(f, ch, X0 - 10 + cx, base, prog(t, start + 0.06 * k, 0.6), a, dy)
            ps = ease_out(prog(t, start + 0.45, 0.5))
            put_text(f, suf, X0 + adv + 8 - 26 * (1 - ps), base, ps * a, dy=dy)
            L = 870 * ease_in_out(prog(t, start + 0.25, 0.8))
            rect(f, X0, base + 48 + dy, L, 3, AMBER, 0.45 * a)

    light_sweep(f, t, 11.1, 1.1)

    # ---- Beat 3: services (11.8 – 17.6)
    if 11.8 <= t < 17.7:
        q = ease_in_out(prog(t, 17.1, 0.5))
        a, dy = 1 - q, -60 * q
        rise_text(f, A["choose"], X0 - 4, 420, prog(t, 11.8, 0.6), a, dy)
        wipe_text(f, A["treatment"], X0 + 250, 540, prog(t, 12.1, 0.9), a, dy)
        base = 720
        for i, (b, r, sub, ic) in enumerate(A["svc"]):
            st = 12.6 + 0.32 * i
            p = ease_out(prog(t, st + 0.15, 0.55))
            cy = base - 48
            put(f, ring(104, AMBER, prog(t, st, 0.7)), X0, cy - 4 + dy, a)
            put(f, ic, X0 + 20, cy + 16 + dy, p * a)
            tx = X0 + 136 - 30 * (1 - p)
            put_text(f, b, tx, base + 18, p * a, dy=dy)
            put_text(f, r, tx + b.adv, base + 18, p * a, dy=dy)
            if sub:
                put_text(f, sub, tx + 2, base + 66, p * a, dy=dy)
            base += 150

    # ---- Beat 4: end card (17.6 – 25)
    if t >= 17.6:
        p = ease_out(prog(t, 17.6, 0.9))
        lg = A["logo"]
        s = 0.95 + 0.05 * p
        img = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS) if s < 0.999 else lg
        # soft cream plate behind the logo keeps its black line art crisp on the light wall
        plate = Image.new("RGBA", (lg.width + 320, lg.height + 280), CREAM + (0,))
        pm = Image.new("L", plate.size, 0)
        ImageDraw.Draw(pm).ellipse((130, 120, plate.width - 130, plate.height - 120), fill=120)
        plate.putalpha(pm.filter(ImageFilter.GaussianBlur(55)))
        put(f, plate, (W - plate.width) / 2, 290 - 140, p)
        put(f, img, (W - img.width) / 2, 290 + (lg.height - img.height) / 2, p)

        p = ease_out(prog(t, 18.2, 0.6))
        tot = A["with"].adv + A["therapist"].adv
        x = (W - tot) / 2
        put_text(f, A["with"], x, 720, p, dy=18 * (1 - p))
        put_text(f, A["therapist"], x + A["with"].adv, 720, p, dy=18 * (1 - p))
        p = ease_out(prog(t, 18.5, 0.6))
        tot = 44 + 12 + A["address"].adv
        x = (W - tot) / 2
        put(f, A["ic_pin"], x, 754 + 18 * (1 - p), p)
        put_text(f, A["address"], x + 56, 792, p, dy=18 * (1 - p))

        p = ease_out(prog(t, 18.9, 0.6))
        put_text(f, A["end_date"], (W - A["end_date"].adv) / 2, 900, p, dy=18 * (1 - p))
        colw = 300
        for i, (n, s_) in enumerate(A["end_times"]):
            cx = W / 2 + (i - 1) * colw
            ps = prog(t, 19.2 + 0.2 * i, 0.6)
            rise_text(f, n, cx - n.adv / 2, 1030, ps)
            pe = ease_out(prog(t, 19.5 + 0.2 * i, 0.5))
            put_text(f, s_, cx - s_.adv / 2, 1088, pe)
        for i in (0, 1):
            rect(f, W / 2 - colw / 2 + i * colw - 1, 960, 2, 140, AMBER, 0.4 * ease_out(prog(t, 19.3, 0.6)))

        p = ease_in_out(prog(t, 20.3, 0.7))
        if p > 0:
            bw, bh, by = 900, 120, 1220
            x = -bw + p * bw
            rect(f, x, by, bw, bh, GREEN, 1.0)
            put_text(f, A["cta"], x + 90, by + bh / 2 + 15, ease_out(prog(t, 20.7, 0.5)))
            pa = ease_out(prog(t, 20.9, 0.5))
            ax = x + 90 + A["cta"].adv + 40 + 14 * (1 - pa)
            ar = Image.new("RGBA", (70 * 4, 40 * 4), (0, 0, 0, 0))
            dd = ImageDraw.Draw(ar)
            dd.line((0, 80, 260, 80), fill=CREAM + (255,), width=12)
            dd.line((200, 20, 262, 80, 200, 140), fill=CREAM + (255,), width=12, joint="curve")
            put(f, ar.resize((70, 40), Image.LANCZOS), ax, by + bh / 2 - 20, pa)
    return np.asarray(f.convert("RGB"))


# ---------------------------------------------------------------- audio (original, synthesized)
def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    out = np.zeros(n)

    def pad(freqs, start, end, gain):
        env = np.clip((t - start) / 2.5, 0, 1) * np.clip((end - t) / 2.5, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.5, 0.5):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.22 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.15 * np.sin(2 * np.pi * 0.11 * t)
        return gain * env * s / len(freqs)

    def chime(at, f0, gain):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 2.0) * np.clip(tt / 0.01, 0, 1)
        out[idx] += gain * env * (np.sin(2 * np.pi * f0 * tt) + 0.35 * np.sin(2 * np.pi * f0 * 2.76 * tt)
                                  + 0.12 * np.sin(2 * np.pi * f0 * 5.4 * tt))

    out += pad([196.00, 246.94, 293.66, 369.99, 440.00], -2.5, 12.5, 0.11)   # G maj9
    out += pad([164.81, 246.94, 293.66, 392.00, 369.99], 10.6, DURATION + 2.5, 0.11)  # E min9
    for at, f0, g in [(0.6, 1174.7, .09), (5.8, 987.8, .06), (6.55, 1108.7, .06), (7.3, 1174.7, .06),
                      (12.6, 880.0, .045), (17.6, 1174.7, .08), (20.3, 1479.9, .05)]:
        chime(at, f0, g)
    rng = np.random.default_rng(3)
    noise = np.convolve(rng.normal(0, 1, n), np.ones(50) / 50, mode="same")
    out += 0.06 * noise * np.exp(-((t - 11.6) / 0.5) ** 2)
    out *= np.clip((DURATION - t) / 1.2, 0, 1) * np.clip(t / 0.3, 0, 1)
    out = out / np.max(np.abs(out)) * 10 ** (-6 / 20)
    data = (np.stack([out, out], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def main(mode):
    os.makedirs(OUT_DIR, exist_ok=True)
    A = build()
    if mode == "stills":
        qc = os.path.join(OUT_DIR, "qc")
        os.makedirs(qc, exist_ok=True)
        for ts in [0.4, 3.6, 9.5, 11.6, 15.5, 23.0]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"v2-{ts:05.1f}s.png"))
        return
    wav = os.path.join(OUT_DIR, f"{NAME}.wav")
    synth_audio(wav)
    mp4 = os.path.join(OUT_DIR, f"{NAME}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(DURATION * FPS)):
        proc.stdin.write(frame_at(i / FPS, A).tobytes())
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    Image.fromarray(frame_at(3.6, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
