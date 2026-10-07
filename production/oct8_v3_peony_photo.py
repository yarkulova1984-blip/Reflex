"""Available Appointments — Thursday, October 8, 2026 — v3 "Peony Noir" (owner's photo).

The owner's dark-background peony photo is brought to life: slow push-in, a gentle
breeze warp so petals breathe, a warm light drifting across the bouquet and a few
floating motes. Type: Bodoni Moda + Allura script + Montserrat, cream/blush/gold.

  python3 production/oct8_v3_peony_photo.py stills
  python3 production/oct8_v3_peony_photo.py video
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
PHOTO = os.path.join(ROOT, "brand", "photos", "peonies-dark-bouquet.jpg")
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-08-available-appointments-v3"
W, H, FPS = 1080, 1920, 30
DURATION = 22.0

CREAM = (250, 240, 228)
BLUSH = (240, 176, 188)
GOLD = (214, 178, 120)
NIGHT = (14, 10, 12)

# ---------------------------------------------------------------- facts (never edit without the owner)
DAY, MONTH, DAYNUM = "THURSDAY", "October", "8"
TIMES = [("5:30", "p.m."), ("6:45", "p.m.")]
SERVICES = [("Foot", " Reflexology", None), ("Hand", " Reflexology", None),
            ("Facial", " Reflexology", "BERGMAN METHOD"), ("Spanish", " Massage", None),
            ("Ultimate Escape", " Package", None)]
THERAPIST = "Zarina, RCRT"
ADDRESS = "698 Corydon Ave"


# ---------------------------------------------------------------- type helpers
def bodoni(size, wght=500, italic=False):
    f = ImageFont.truetype(os.path.join(FONTS, "BodoniModa-Italic[opsz,wght].ttf" if italic else "BodoniModa[opsz,wght].ttf"), size)
    f.set_variation_by_axes([wght, 14])  # low optical size = sturdier hairlines on phones
    return f


def allura(size):
    return ImageFont.truetype(os.path.join(FONTS, "Allura-Regular.ttf"), size)


def mont(size, var="Medium"):
    f = ImageFont.truetype(os.path.join(FONTS, "Montserrat[wght].ttf"), size)
    f.set_variation_by_name(var)
    return f


class Text:
    def __init__(self, txt, fnt, fill, tracking=0, shadow=True):
        kw = {"features": ["lnum"]}
        asc, desc = fnt.getmetrics()
        pad = int(fnt.size * 0.35)
        width = (sum(fnt.getlength(c, **kw) for c in txt) + tracking * (len(txt) - 1)) if tracking else fnt.getlength(txt, **kw)
        size = (math.ceil(width) + 2 * pad, asc + desc + pad)
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if tracking:
            x = pad
            for c in txt:
                d.text((x, asc), c, font=fnt, fill=fill, anchor="ls", **kw)
                x += fnt.getlength(c, **kw) + tracking
        else:
            d.text((pad, asc), txt, font=fnt, fill=fill, anchor="ls", **kw)
        if shadow:  # soft dark glow keeps light type crisp over petals
            sh = Image.new("RGBA", size, NIGHT + (0,))
            sh.putalpha(layer.getchannel("A").filter(ImageFilter.GaussianBlur(max(3, fnt.size // 14))).point(lambda v: int(v * 0.75)))
            sh.alpha_composite(layer)
            layer = sh
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


def put_c(f, tx, base, a=1.0, dy=0.0, cx=W / 2):
    put(f, tx.img, cx - tx.adv / 2 - tx.pad, base - tx.asc + dy, a)


def put_x(f, tx, x, base, a=1.0, dy=0.0):
    put(f, tx.img, x - tx.pad, base - tx.asc + dy, a)


def rise_c(f, tx, base, p, a=1.0, cx=W / 2):
    if p <= 0:
        return
    put_c(f, tx, base, ease_out(p) * a, 26 * (1 - ease_out(p)), cx)


def blur_in_c(f, tx, base, p, a=1.0):
    """Defocus-to-focus reveal (soft cinematic)."""
    if p <= 0:
        return
    e = ease_out(p)
    img = tx.img if e > 0.97 else tx.img.filter(ImageFilter.GaussianBlur(10 * (1 - e)))
    put(f, img, W / 2 - tx.adv / 2 - tx.pad, base - tx.asc, e * a)


def wipe_c(f, tx, base, p, a=1.0):
    if p <= 0:
        return
    vis = int(tx.w * ease_in_out(p))
    if vis > 0:
        put(f, tx.img.crop((0, 0, vis, tx.h)), W / 2 - tx.adv / 2 - tx.pad, base - tx.asc, a)


def rect(f, x, y, w, h, color, a=1.0):
    if w > 0.5 and h > 0.5 and a > 0:
        f.alpha_composite(Image.new("RGBA", (int(w), int(h)), color + (int(255 * a),)), (int(x), int(y)))


def vgrad(f, y0, y1, a0, a1, a):
    """Vertical dark gradient scrim."""
    if a <= 0:
        return
    h = int(y1 - y0)
    col = np.linspace(a0, a1, h, dtype=np.float32)[:, None] * a
    m = Image.fromarray((np.repeat(col, W, 1) * 255).astype(np.uint8), "L")
    s = Image.new("RGBA", (W, h), NIGHT + (0,))
    s.putalpha(m)
    f.alpha_composite(s, (0, int(y0)))


def dark_glass(f, box, a, radius=56):
    if a <= 0.003:
        return
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    region = f.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(22))
    region = Image.blend(region, Image.new("RGBA", (w, h), NIGHT + (255,)), 0.58)
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), radius * 2, fill=int(255 * a))
    region.putalpha(m.resize((w, h), Image.LANCZOS))
    f.alpha_composite(region, (x0, y0))
    e = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    ImageDraw.Draw(e).rounded_rectangle((1, 1, w * 2 - 2, h * 2 - 2), radius * 2, outline=GOLD + (int(120 * a),), width=3)
    f.alpha_composite(e.resize((w, h), Image.LANCZOS), (x0, y0))


def diamond(size, color):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(s / 2, 0), (s, s / 2), (s / 2, s), (0, s / 2)], fill=color + (255,))
    return im.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- living photo
OVER = 1.14


def build_photo():
    src = Image.open(PHOTO).convert("RGB")
    k = max(W / src.width, H / src.height) * OVER
    big = src.resize((int(src.width * k), int(src.height * k)), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    arr = np.asarray(big, np.float32)
    lum = arr.mean(-1) / 255.0
    P = {"arr": arr, "bw": big.width, "bh": big.height}
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    P["X"], P["Y"] = xx, yy
    # petals (bright areas) sway more than the dark background
    lm = Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30))
    P["sway"] = np.asarray(lm.resize((big.width, big.height)), np.float32) / 255.0
    rng = np.random.default_rng(12)
    P["motes"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(6, 20), rng.uniform(0, 6.28), rng.uniform(0.25, 0.7))
                  for _ in range(36)]
    m = Image.new("L", (28, 28), 0)
    ImageDraw.Draw(m).ellipse((8, 8, 20, 20), fill=255)
    mote = Image.new("RGBA", (28, 28), (255, 226, 180, 0))
    mote.putalpha(m.filter(ImageFilter.GaussianBlur(3.5)))
    P["mote"] = mote
    P["grain"] = [rng.normal(0, 2.6, (H, W, 1)).astype(np.float32) for _ in range(3)]
    vx, vy = (xx - W / 2) / W, (yy - H / 2) / H
    P["vig"] = (1 - 0.35 * np.clip((vx ** 2 + vy ** 2) * 2.2, 0, 1))[..., None]
    return P


def bilinear(arr, sx, sy):
    h, w = arr.shape[:2]
    sx = np.clip(sx, 0, w - 1.001)
    sy = np.clip(sy, 0, h - 1.001)
    x0, y0 = sx.astype(np.int32), sy.astype(np.int32)
    fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
    a = arr[y0, x0]
    b = arr[y0, x0 + 1]
    c = arr[y0 + 1, x0]
    d = arr[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def render_photo(t, P):
    s = 1.0 + 0.075 * ease_in_out(t / DURATION)            # slow push-in
    cx = P["bw"] / 2 + 14 * math.sin(t * 0.17)
    cy = P["bh"] / 2 - 18 * t / DURATION
    X, Y = P["X"], P["Y"]
    sx = cx + (X - W / 2) / s
    sy = cy + (Y - H / 2) / s
    # breeze: low-frequency travelling waves, weighted toward the petals
    ix = np.clip(sx.astype(np.int32), 0, P["bw"] - 1)
    iy = np.clip(sy.astype(np.int32), 0, P["bh"] - 1)
    wgt = 0.35 + 0.65 * P["sway"][iy, ix]
    dx = (3.2 * np.sin(0.95 * t + sx * 0.0075 + sy * 0.0035) + 1.6 * np.sin(1.7 * t + sy * 0.012 + 1.3)) * wgt
    dy = (2.4 * np.sin(1.15 * t + sx * 0.006 - sy * 0.007 + 0.7) + 1.1 * np.sin(2.1 * t + sx * 0.013)) * wgt
    img = bilinear(P["arr"], sx + dx, sy + dy) / 255.0
    # warm light drifting across the bouquet
    lx = 150 + 700 * (t / DURATION)
    ly = 420 + 900 * (t / DURATION)
    r = np.sqrt((X - lx) ** 2 + (Y - ly) ** 2)
    glow = (np.exp(-r / 520) * (0.16 + 0.03 * math.sin(t * 0.8)))[..., None] * np.array([1.0, 0.86, 0.7], np.float32)
    img = 1 - (1 - img) * (1 - glow)
    img = img * P["vig"] * 255 + P["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, spd, ph, a) in P["motes"]:
        mx = x + 22 * math.sin(t * 0.35 + ph)
        my = (y - spd * t) % H
        put(f, P["mote"], mx, my, a * (0.6 + 0.4 * math.sin(t * 1.3 + ph)))
    return f


# ---------------------------------------------------------------- assets
def build():
    A = {"P": build_photo()}
    A["still"] = Text("Still", allura(170), BLUSH)
    A["thinking"] = Text("THINKING", bodoni(150, 700), CREAM, tracking=4)
    A["about"] = Text("about it?", bodoni(112, 400, italic=True), CREAM)
    A["only_a"] = Text("Only ", mont(42), CREAM)
    A["only_2"] = Text("2", mont(42, "Bold"), GOLD)
    A["only_b"] = Text(" evening times remain this Thursday", mont(42), CREAM)

    A["day"] = Text(DAY, mont(40, "SemiBold"), GOLD, tracking=16)
    A["date"] = Text(f"{MONTH} {DAYNUM}", bodoni(124, 400, italic=True), CREAM)
    tf = bodoni(230, 600)
    A["times"] = []
    for num, suf in TIMES:
        chars, x = [], 0
        for ch in num:
            chars.append((x, Text(ch, tf, CREAM)))
            x += tf.getlength(ch, features=["lnum"])
        A["times"].append((chars, x, Text(suf, allura(120), BLUSH)))

    A["all"] = Text("All services", bodoni(104, 400, italic=True), CREAM)
    A["avail"] = Text("available", allura(130), BLUSH)
    A["dia"] = diamond(22, GOLD)
    A["svc"] = [(Text(b, bodoni(60, 700), CREAM), Text(r, bodoni(60, 400), CREAM),
                 Text(sub, mont(28, "SemiBold"), GOLD, tracking=6) if sub else None) for b, r, sub in SERVICES]

    A["reserve"] = Text("Reserve", bodoni(150, 700), CREAM)
    A["evening"] = Text("your evening", allura(140), BLUSH)
    A["before"] = Text("before it's gone", bodoni(76, 400, italic=True), CREAM)
    logo = Image.open(LOGO).convert("RGBA")
    lw = 460
    A["logo"] = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    A["who"] = Text(f"{THERAPIST}  ·  {ADDRESS}", mont(38), CREAM)
    A["when"] = Text(f"Thursday, {MONTH} {DAYNUM}  ·  {TIMES[0][0]} {TIMES[0][1]}  ·  {TIMES[1][0]} {TIMES[1][1]}",
                     mont(34, "SemiBold"), GOLD)
    A["cta"] = Text("DM TO BOOK", mont(44, "Bold"), NIGHT, tracking=8, shadow=False)
    return A


def frame_at(t, A):
    f = render_photo(t, A["P"])
    cx = W / 2

    # ---- Beat 1: hook question (0 – 4.4)
    if t < 4.5:
        q = ease_in_out(prog(t, 4.0, 0.45))
        a = 1 - q
        vgrad(f, 0, 940, 0.9, 0.55, ease_out(prog(t, 0, 0.6)) * a)
        vgrad(f, 940, 1200, 0.55, 0.0, ease_out(prog(t, 0, 0.6)) * a)
        wipe_c(f, A["still"], 440, prog(t, 0.2, 0.8), a)
        th = A["thinking"]
        blur_in_c(f, th, 610, prog(t, 0.6, 0.7), a)
        rise_c(f, A["about"], 740, prog(t, 1.2, 0.6), a)
        L = 240 * ease_in_out(prog(t, 1.7, 0.6))
        rect(f, cx - L / 2, 790, L, 2, GOLD, a)
        p = ease_out(prog(t, 2.0, 0.6))
        tot = A["only_a"].adv + A["only_2"].adv + A["only_b"].adv
        x = cx - tot / 2
        for k in ("only_a", "only_2", "only_b"):
            put_x(f, A[k], x, 870, p * a, 18 * (1 - p))
            x += A[k].adv

    # ---- Beat 2: date + times on dark glass (4.4 – 9.9)
    if 4.4 <= t < 10.0:
        q = ease_in_out(prog(t, 9.5, 0.45))
        a = 1 - q
        p = ease_out(prog(t, 4.4, 0.6))
        dark_glass(f, (100, 520 + 40 * (1 - p), 980, 1400 + 40 * (1 - p)), p * a)
        rise_c(f, A["day"], 650, prog(t, 4.7, 0.5), a)
        rise_c(f, A["date"], 800, prog(t, 4.9, 0.6), a)
        L = 200 * ease_in_out(prog(t, 5.3, 0.5))
        rect(f, cx - L / 2, 850, L, 2, GOLD, a)
        for i, (chars, adv, suf) in enumerate(A["times"]):
            st = 5.5 + 0.7 * i
            base = 1080 + 230 * i
            tot = adv + 20 + suf.adv
            x = cx - tot / 2
            for k, (ox, ch) in enumerate(chars):
                pp = ease_out(prog(t, st + 0.07 * k, 0.55))
                put_x(f, ch, x + ox, base, pp * a, 34 * (1 - pp))
            ps = prog(t, st + 0.35, 0.7)
            if ps > 0:
                vis = int(suf.w * ease_in_out(ps))
                put(f, suf.img.crop((0, 0, max(1, vis), suf.h)), x + adv + 20 - suf.pad, base - suf.asc, a)

    # ---- Beat 3: all services (9.9 – 15.7)
    if 9.9 <= t < 15.8:
        q = ease_in_out(prog(t, 15.3, 0.45))
        a = 1 - q
        p = ease_out(prog(t, 9.9, 0.6))
        dark_glass(f, (90, 440 + 40 * (1 - p), 990, 1420 + 40 * (1 - p)), p * a)
        rise_c(f, A["all"], 590, prog(t, 10.1, 0.6), a)
        wipe_c(f, A["avail"], 700, prog(t, 10.4, 0.8), a)
        base = 840
        for i, (b, r, sub) in enumerate(A["svc"]):
            pp = ease_out(prog(t, 10.9 + 0.3 * i, 0.55))
            tot = 22 + 22 + b.adv + r.adv
            x = cx - tot / 2
            put(f, A["dia"], x, base - 34 + 18 * (1 - pp), pp * a)
            put_x(f, b, x + 44, base, pp * a, 18 * (1 - pp))
            put_x(f, r, x + 44 + b.adv, base, pp * a, 18 * (1 - pp))
            if sub:
                put_c(f, sub, base + 50, pp * a, 18 * (1 - pp))
                base += 50
            base += 104

    # ---- Beat 4: booking (15.7 – end)
    if t >= 15.7:
        p = ease_out(prog(t, 15.7, 0.7))
        vgrad(f, 0, 780, 0.9, 0.55, p)
        vgrad(f, 780, 960, 0.55, 0.0, p)
        vgrad(f, 860, 1920, 0.0, 0.9, p)
        blur_in_c(f, A["reserve"], 470, prog(t, 15.8, 0.7))
        wipe_c(f, A["evening"], 610, prog(t, 16.3, 0.9))
        rise_c(f, A["before"], 720, prog(t, 17.0, 0.6))
        p = ease_out(prog(t, 17.5, 0.7))
        lg = A["logo"]
        pw, ph = lg.width + 120, lg.height + 70
        plaque = Image.new("RGBA", (pw * 2, ph * 2), (0, 0, 0, 0))
        ImageDraw.Draw(plaque).rounded_rectangle((0, 0, pw * 2 - 1, ph * 2 - 1), 60, fill=CREAM + (236,))
        py = 930 + 30 * (1 - p)
        put(f, plaque.resize((pw, ph), Image.LANCZOS), (W - pw) / 2, py, p)
        put(f, lg, (W - lg.width) / 2, py + 35, p)
        pp = ease_out(prog(t, 18.0, 0.5))
        put_c(f, A["who"], py + ph + 72, pp, 14 * (1 - pp))
        pp = ease_out(prog(t, 18.3, 0.5))
        put_c(f, A["when"], py + ph + 130, pp, 14 * (1 - pp))
        p = prog(t, 18.8, 0.5)
        if p > 0:
            pulse = 1 + 0.03 * max(0.0, math.sin((t - 19.3) * 3.0)) * (t > 19.3)
            bw, bh = 500, 112
            sc = (0.88 + 0.12 * ease_out(p)) * pulse
            pill = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle((0, 0, bw * 4 - 1, bh * 4 - 1), bh * 2, fill=GOLD + (255,))
            pill = pill.resize((int(bw * sc), int(bh * sc)), Image.LANCZOS)
            by = py + ph + 180
            put(f, pill, (W - pill.width) / 2, by + (bh - pill.height) / 2, min(1, p * 2))
            put_c(f, A["cta"], by + bh / 2 + 16, min(1, p * 2))
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
        env = np.clip((t - start) / 2.2, 0, 1) * np.clip((end - t) / 2.2, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.4, 0.4):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.18 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.12 * np.sin(2 * np.pi * 0.1 * t)
        return gain * env * s / len(freqs)

    def pluck(at, f0, g):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 2.6) * np.clip(tt / 0.006, 0, 1)
        out[idx] += g * env * (np.sin(2 * np.pi * f0 * tt) + 0.45 * np.sin(2 * np.pi * f0 * 2 * tt) + 0.2 * np.sin(2 * np.pi * f0 * 3 * tt))

    out += pad([155.56, 233.08, 293.66, 349.23, 392.0], -2, 10.3, 0.10)   # Eb maj9
    out += pad([130.81, 196.0, 233.08, 293.66, 311.13], 9.2, 16.4, 0.10)  # C min9
    out += pad([103.83, 155.56, 207.65, 261.63, 311.13], 15.2, DURATION + 2, 0.10)  # Ab maj7
    for at, f0 in [(0.6, 622.25), (1.2, 783.99), (5.5, 698.46), (6.2, 783.99), (10.4, 932.33),
                   (15.8, 622.25), (16.3, 783.99), (18.8, 1046.5)]:
        pluck(at, f0, 0.07)
    out *= np.clip((DURATION - t) / 1.4, 0, 1) * np.clip(t / 0.3, 0, 1)
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
        for ts in [3.0, 8.0, 14.0, 21.0]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"v3-{ts:04.1f}s.png"))
        return
    wav = os.path.join(OUT_DIR, f"{NAME}.wav")
    synth_audio(wav)
    mp4 = os.path.join(OUT_DIR, f"{NAME}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4, initializer=_init) as pool:
        for buf in pool.imap(_render, range(int(DURATION * FPS)), chunksize=4):
            proc.stdin.write(buf)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    A = build()
    Image.fromarray(frame_at(3.0, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
