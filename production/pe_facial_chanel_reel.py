"""THE PURE ESCAPE — Facial Reflexology (Bergman Method) + Hand Reflexology with Chanel skincare.
75 minutes · $145 · Zarina, RCRT · 698 Corydon Ave. Mode A service Reel (~44 s).

Built from the owner's photos: each still gets its own camera move; scenes change through
soft cross-defocus; type sits in dark headroom so faces and hands are never covered.
Type: Italiana (luxury display) + Manrope + Parisienne accent. Champagne gold, ivory, nude blush.

  python3 production/pe_facial_chanel_reel.py stills
  python3 production/pe_facial_chanel_reel.py video
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
from oct9_amt_bamboo import (Text, ease_in_out, ease_out, gold_line, pin_icon, prog, put,  # noqa: E402
                             put_c, put_x, sharp_in, vgrad)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")
PH = os.path.join(ROOT, "brand", "photos", "pe-facial")
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-pe-facial-reflexology-chanel"
W, H, FPS = 1080, 1920, 30
DURATION = 44.0

IVORY = (248, 240, 228)
BLUSH = (232, 186, 172)
NIGHT = (12, 8, 6)

# ---------------------------------------------------------------- facts (owner-provided; never edit without the owner)
CLINIC = "The Pure Escape"
ADDRESS = "698 Corydon Ave, Winnipeg"
THERAPIST = "Zarina, RCRT"
ROLE = "Reflexology Therapist"
PRICE = "$145"
LENGTH = "1 hr 15 min"


def italiana(size):
    return ImageFont.truetype(os.path.join(FONTS, "Italiana-Regular.ttf"), size)


def manrope(size, wght=400):
    f = ImageFont.truetype(os.path.join(FONTS, "Manrope[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def parisienne(size):
    return ImageFont.truetype(os.path.join(FONTS, "Parisienne-Regular.ttf"), size)


# ---------------------------------------------------------------- photos
def extend_top(im, frac):
    """Dark, defocused headroom above a photo so type never covers faces or hands."""
    add = int(im.height * frac)
    if add <= 0:
        return im
    strip = im.crop((0, 0, im.width, max(8, int(im.height * 0.10))))
    strip = strip.transpose(Image.FLIP_TOP_BOTTOM).resize((im.width, add), Image.BICUBIC).filter(ImageFilter.GaussianBlur(26))
    arr = np.asarray(strip, np.float32) * np.linspace(0.35, 0.9, add, dtype=np.float32)[:, None, None]
    out = Image.new("RGB", (im.width, im.height + add))
    out.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (0, 0))
    out.paste(im, (0, add))
    # feather the seam
    seam_h = 60
    top = out.crop((0, add - seam_h, im.width, add + seam_h)).filter(ImageFilter.GaussianBlur(10))
    m = Image.linear_gradient("L").resize((im.width, 2 * seam_h)).transpose(Image.FLIP_TOP_BOTTOM)
    m = Image.fromarray((255 - np.abs(np.asarray(m, np.float32) - 127.5) * 2).clip(0, 255).astype(np.uint8))
    out.paste(top, (0, add - seam_h), m)
    return out


def blur_region(im, box, r=40, darken=0.55):
    x0, y0, x1, y1 = [int(v) for v in (box[0] * im.width, box[1] * im.height, box[2] * im.width, box[3] * im.height)]
    reg = im.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(r))
    reg = Image.fromarray((np.asarray(reg, np.float32) * darken).astype(np.uint8))
    mask = Image.new("L", reg.size, 0)
    ImageDraw.Draw(mask).rectangle((0, 0, reg.width, reg.height), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(30))
    m = Image.new("L", reg.size, 0)
    m.paste(255, (40, 40, reg.width - 40, reg.height - 40))
    m = m.filter(ImageFilter.GaussianBlur(40))
    out = im.copy()
    out.paste(reg, (x0, y0), m)
    return out


def load(name, headroom=0.0, crop_bottom=0.0, blur_box=None):
    im = Image.open(os.path.join(PH, name)).convert("RGB")
    if crop_bottom:
        im = im.crop((0, 0, im.width, int(im.height * (1 - crop_bottom))))
    if blur_box:
        im = blur_region(im, blur_box)
    im = extend_top(im, headroom)
    k = max(W / im.width, H / im.height) * 1.35
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2.5, percent=55, threshold=2))
    return im


# scenes: key, file, headroom, start, end, camera keyframes (t, u, v, zoom); zoom 1 = frame just covered
SCENES = [
    ("map", "14-face-map-oil.png", 0.46, 0.0, 4.7, [(0.0, 0.50, 0.55, 1.00), (4.7, 0.51, 0.58, 1.07)]),          # push-in
    ("facial", "13-forehead-oil.png", 0.46, 4.4, 10.3, [(4.4, 0.44, 0.56, 1.05), (10.3, 0.56, 0.56, 1.05)]),     # lateral slide
    ("hand", "15-hand-map.png", 0.40, 10.0, 15.8, [(10.0, 0.50, 0.55, 1.00), (15.8, 0.48, 0.60, 1.10)]),          # wide to detail
    ("cleanse", "08-la-mousse-hands.png", 0.36, 15.5, 18.9, [(15.5, 0.50, 0.58, 1.00), (18.9, 0.49, 0.62, 1.07)]),
    ("exfoliate", "11-le-gommage.png", 0.50, 18.6, 22.0, [(18.6, 0.54, 0.56, 1.06), (22.0, 0.46, 0.56, 1.06)]),
    ("eyes", "17-le-lift-eyes.png", 0.40, 21.7, 25.1, [(21.7, 0.50, 0.60, 1.10), (25.1, 0.50, 0.55, 1.00)]),     # pull-back
    ("hands", "16-hand-cream.png", 0.40, 24.8, 28.2, [(24.8, 0.44, 0.56, 1.04), (28.2, 0.56, 0.56, 1.04)]),
    ("unwind", "19-mirror-result.png", 0.12, 27.9, 33.6, [(27.9, 0.50, 0.55, 1.12), (33.6, 0.52, 0.52, 1.00)]),  # pull-back
    ("offer", "07-chanel-still-life.png", 0.0, 33.3, 44.0, [(33.3, 0.50, 0.46, 1.00), (38.0, 0.50, 0.44, 1.14), (44.0, 0.50, 0.44, 1.18)]),
]
SHIRT = (0.0, 0.0, 0.40, 0.17)   # soften the printed shirt text so it never fights the type
LOAD_OPTS = {"unwind": {"blur_box": (0.0, 0.0, 0.46, 0.48)}, "offer": {"crop_bottom": 0.16},
             "map": {"blur_box": SHIRT}, "facial": {"blur_box": SHIRT}, "hand": {"blur_box": SHIRT},
             "eyes": {"blur_box": SHIRT}, "hands": {"blur_box": SHIRT}}


def cam(keys, t):
    if t <= keys[0][0]:
        return keys[0][1:]
    for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            e = ease_in_out((t - t0) / (t1 - t0))
            return tuple(x + (y - x) * e for x, y in zip(a, b))
    return keys[-1][1:]


def shot(A, key, t):
    im = A["img"][key]
    keys = A["keys"][key]
    u, v, z = cam(keys, t)
    s = max(W / im.width, H / im.height)
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * im.width, cw / 2), im.width - cw / 2)
    cy = min(max(v * im.height, ch / 2), im.height - ch / 2)
    return im.transform((W, H), Image.EXTENT, (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2), Image.BILINEAR)


def background(t, A, soften=0.0):
    act = [(k, s, e) for k, _, _, s, e, _ in SCENES if s - 1e-3 <= t <= e]
    if len(act) >= 2:
        (k1, _, e1), (k2, s2, _) = act[-2], act[-1]
        p = (t - s2) / max(1e-3, (e1 - s2))
        a = shot(A, k1, t).filter(ImageFilter.GaussianBlur(12 * p))
        b = shot(A, k2, t).filter(ImageFilter.GaussianBlur(12 * (1 - p)))
        img = Image.blend(a, b, ease_in_out(p))
    else:
        img = shot(A, act[0][0], t)
        if soften > 0.01:
            img = img.filter(ImageFilter.GaussianBlur(9 * soften))
    arr = np.asarray(img, np.float32) * A["vig"] + A["grain"][int(t * 15) % 3]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def badge_rgba(width):
    im = Image.open(os.path.join(PH, "06-lsr-bergman-badge.jpg")).convert("RGB")
    a = np.asarray(im, np.float32)
    alpha = np.clip((a.max(-1) - 18) * 6, 0, 255)          # black background -> transparent
    rgba = np.concatenate([a, alpha[..., None]], -1).astype(np.uint8)
    b = Image.fromarray(rgba, "RGBA")
    return b.resize((width, round(b.height * width / b.width)), Image.LANCZOS)


# ---------------------------------------------------------------- assets
def build():
    A = {"img": {}, "keys": {}}
    for key, f, head, s, e, keys in SCENES:
        A["img"][key] = load(f, head, **LOAD_OPTS.get(key, {}))
        A["keys"][key] = keys
    rng = np.random.default_rng(14)
    A["grain"] = [rng.normal(0, 2.6, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.3 * np.clip(((xx - W / 2) / W) ** 2 * 2.6 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]

    A["your_face"] = Text("Your face", parisienne(132), BLUSH)
    A["has_map"] = Text("HAS A MAP", italiana(178), "gold", tracking=6)
    A["map_sub"] = Text("FACIAL REFLEXOLOGY  ·  BERGMAN METHOD", manrope(28, 600), IVORY, tracking=5)

    A["fr_words"] = [Text("FACIAL REFLEXOLOGY", italiana(84), IVORY, tracking=3)]
    A["bergman"] = Text("Bergman Method", parisienne(88), "gold")
    A["fr_body"] = [Text(s, manrope(36, 300), IVORY) for s in ("Gentle, precise touch on the", "reflex points of the face")]

    A["plus"] = Text("+", italiana(130), "gold")
    A["hand"] = Text("HAND REFLEXOLOGY", italiana(90), IVORY, tracking=2)
    A["hand_body"] = [Text(s, manrope(36, 300), IVORY) for s in ("Focused thumb and finger work on", "the reflex areas of the hands")]

    A["ritual"] = Text("THE CHANEL SKINCARE RITUAL", manrope(30, 600), "gold", tracking=8)
    steps = [("CLEANSE", "La Mousse", "Lifts away makeup and daily impurities"),
             ("EXFOLIATE", "Le Gommage", "For smoother-looking, refined skin"),
             ("SMOOTH", "Le Lift Crème Yeux", "A smoothing, firming eye cream"),
             ("NOURISH", "La Crème Main", "Rich cream for soft, cared-for hands")]
    A["steps"] = [(Text(a, italiana(118), IVORY, tracking=6), Text(b, parisienne(72), BLUSH), Text(c, manrope(36, 300), IVORY))
                  for a, b, c in steps]

    A["n75"] = Text("75", italiana(330), "gold")
    A["minutes"] = Text("MINUTES", manrope(42, 600), IVORY, tracking=12)
    A["for_you"] = Text("just for you", parisienne(96), BLUSH)
    A["unwind"] = [Text(s, manrope(36, 300), IVORY) for s in ("Designed to help you", "fully unwind")]

    A["o_title"] = Text("FACIAL REFLEXOLOGY", italiana(92), IVORY, tracking=4)
    A["o_sub"] = Text("Bergman Method  +  Hand Reflexology", manrope(36, 500), IVORY, tracking=1)
    A["o_chanel"] = Text("with Chanel skincare", parisienne(78), BLUSH)
    A["o_price"] = Text(PRICE, manrope(210, 300), "gold")
    A["o_len"] = Text(LENGTH.upper(), manrope(40, 600), IVORY, tracking=10)

    logo = Image.open(LOGO).convert("RGBA")
    lw = 500
    A["logo"] = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    A["who"] = Text(THERAPIST, manrope(46, 600), IVORY, tracking=1)
    A["role"] = Text(ROLE, manrope(34, 300), IVORY, tracking=3)
    A["pin"] = pin_icon(38, BLUSH)
    A["addr"] = Text(ADDRESS, manrope(38, 400), IVORY, tracking=1)
    A["badge"] = badge_rgba(230)
    A["cta"] = Text("DM TO BOOK", manrope(46, 700), NIGHT, tracking=12, shadow=0)
    return A


def tracking_in(f, words, base, p, a, cx=W / 2):
    """Letter-spacing reveal: wide tracking that settles into place (word stack, centred)."""
    if p <= 0:
        return
    e = ease_out(p)
    for i, w in enumerate(words):
        img = w.img
        sx = 1.0 + 0.35 * (1 - e)
        img2 = img.resize((int(w.w * sx), w.h), Image.LANCZOS)
        put(f, img2, cx - (w.adv / 2 + w.pad) * sx, base + i * 120 - w.asc, e * a)


def frame_at(t, A):
    soften = 0.0
    for s0 in (35.4,):   # price "appears from nowhere"
        soften = max(soften, math.exp(-((t - s0) / 0.45) ** 2))
    if t >= 33.6:          # calm, softened still life behind the offer and booking details
        soften = max(soften, 0.55 * ease_in_out(prog(t, 33.6, 0.8)))
    f = background(t, A, soften)
    vgrad(f, 0, 760, 0.78, 0.0, 1.0)

    # ---- S1 hook 0–4.6
    if t < 4.6:
        a = 1 - ease_in_out(prog(t, 4.15, 0.4))
        wipe = prog(t, 0.2, 0.9)
        yf = A["your_face"]
        vis = int(yf.w * ease_in_out(wipe))
        if vis > 0:
            put(f, yf.img.crop((0, 0, vis, yf.h)), W / 2 - yf.adv / 2 - yf.pad, 390 - yf.asc, a)
        sharp_in(f, A["has_map"], W / 2 - A["has_map"].adv / 2, 560, prog(t, 0.8, 0.8), a, scale_from=1.12)
        gold_line(f, W / 2, 602, 300 * ease_in_out(prog(t, 1.5, 0.6)), a)
        p = ease_out(prog(t, 1.8, 0.6))
        put_c(f, A["map_sub"], 660, p * a, dy=16 * (1 - p))

    # ---- S2 facial reflexology 4.4–10.2
    if 4.4 <= t < 10.25:
        a = 1 - ease_in_out(prog(t, 9.8, 0.4))
        tracking_in(f, A["fr_words"], 380, prog(t, 4.6, 0.9), a)
        p = prog(t, 5.4, 0.9)
        b = A["bergman"]
        vis = int(b.w * ease_in_out(p))
        if vis > 0:
            put(f, b.img.crop((0, 0, vis, b.h)), W / 2 - b.adv / 2 - b.pad, 478 - b.asc, a)
        for i, line in enumerate(A["fr_body"]):
            p = ease_out(prog(t, 6.3 + 0.2 * i, 0.6))
            put_c(f, line, 548 + i * 46, p * a, dy=14 * (1 - p))

    # ---- S3 hand reflexology 10.0–15.7
    if 10.0 <= t < 15.75:
        a = 1 - ease_in_out(prog(t, 15.3, 0.4))
        sharp_in(f, A["plus"], W / 2 - A["plus"].adv / 2, 350, prog(t, 10.2, 0.6), a, scale_from=1.3)
        p = ease_out(prog(t, 10.6, 0.7))
        put_c(f, A["hand"], 460, p * a, dx=120 * (1 - p))
        for i, line in enumerate(A["hand_body"]):
            p = ease_out(prog(t, 11.4 + 0.2 * i, 0.6))
            put_c(f, line, 532 + i * 46, p * a, dy=14 * (1 - p))

    # ---- S4 Chanel ritual 15.5–28.1 (four steps, one shared header + progress line)
    if 15.5 <= t < 28.15:
        a_all = ease_out(prog(t, 15.5, 0.5)) * (1 - ease_in_out(prog(t, 27.75, 0.4)))
        put_c(f, A["ritual"], 300, a_all)
        total = 520
        prog_len = total * min(1.0, (t - 15.5) / 12.3)
        gold_line(f, W / 2, 326, total, 0.25 * a_all, thick=2)
        if prog_len > 1:
            gold_line(f, W / 2 - total / 2 + prog_len / 2, 326, prog_len, a_all, thick=2)
        starts = [15.6, 18.75, 21.85, 24.95]
        for i, (word, prod, line) in enumerate(A["steps"]):
            s0 = starts[i]
            s1 = s0 + 3.1
            if s0 <= t < s1:
                a = 1 - ease_in_out(prog(t, s1 - 0.35, 0.35))
                sharp_in(f, word, W / 2 - word.adv / 2, 450, prog(t, s0 + 0.15, 0.55), a)
                p = prog(t, s0 + 0.55, 0.7)
                vis = int(prod.w * ease_in_out(p))
                if vis > 0:
                    put(f, prod.img.crop((0, 0, vis, prod.h)), W / 2 - prod.adv / 2 - prod.pad, 530 - prod.asc, a)
                p = ease_out(prog(t, s0 + 1.0, 0.5))
                put_c(f, line, 592, p * a, dy=14 * (1 - p))

    # ---- S5 75 minutes 27.9–33.5 (left-aligned over the softened poster area)
    if 27.9 <= t < 33.55:
        a = 1 - ease_in_out(prog(t, 33.1, 0.4))
        x = 96
        sharp_in(f, A["n75"], x, 640, prog(t, 28.1, 0.8), a, scale_from=1.15)
        p = ease_out(prog(t, 28.7, 0.6))
        put_x(f, A["minutes"], x + 8, 720, p * a, dx=-40 * (1 - p))
        p = prog(t, 29.2, 0.9)
        fy = A["for_you"]
        vis = int(fy.w * ease_in_out(p))
        if vis > 0:
            put(f, fy.img.crop((0, 0, vis, fy.h)), x - fy.pad, 830 - fy.asc, a)
        for i, line in enumerate(A["unwind"]):
            p = ease_out(prog(t, 30.0 + 0.2 * i, 0.6))
            put_x(f, line, x + 4, 910 + i * 48, p * a, dy=14 * (1 - p))

    # ---- S6a offer + price 33.3–38.3
    if 33.3 <= t < 38.4:
        a = 1 - ease_in_out(prog(t, 37.95, 0.45))
        vgrad(f, 0, H, 0.5, 0.5, ease_out(prog(t, 33.3, 0.6)) * a)
        p = ease_out(prog(t, 33.5, 0.6))
        put_c(f, A["o_title"], 420, p * a, dy=-20 * (1 - p))
        p = ease_out(prog(t, 33.9, 0.6))
        put_c(f, A["o_sub"], 490, p * a, dy=14 * (1 - p))
        p = prog(t, 34.3, 0.8)
        oc = A["o_chanel"]
        vis = int(oc.w * ease_in_out(p))
        if vis > 0:
            put(f, oc.img.crop((0, 0, vis, oc.h)), W / 2 - oc.adv / 2 - oc.pad, 585 - oc.asc, a)
        sharp_in(f, A["o_price"], W / 2 - A["o_price"].adv / 2, 860, prog(t, 35.2, 0.7), a)
        gold_line(f, W / 2, 900, 260 * ease_in_out(prog(t, 35.8, 0.6)), a)
        p = ease_out(prog(t, 36.0, 0.5))
        put_c(f, A["o_len"], 965, p * a, dy=14 * (1 - p))

    # ---- S6b who / where / book 38.2–44
    if t >= 38.2:
        p0 = ease_out(prog(t, 38.2, 0.6))
        vgrad(f, 0, H, 0.62, 0.62, p0)
        lg = A["logo"]
        pw, ph = lg.width + 90, lg.height + 60
        plaque = Image.new("RGBA", (pw * 2, ph * 2), (0, 0, 0, 0))
        ImageDraw.Draw(plaque).rounded_rectangle((0, 0, pw * 2 - 1, ph * 2 - 1), 56, fill=IVORY + (240,))
        py = 250 + 24 * (1 - p0)
        put(f, plaque.resize((pw, ph), Image.LANCZOS), (W - pw) / 2, py, p0)
        put(f, lg, (W - lg.width) / 2, py + 30, p0)
        y = py + ph + 80
        p = ease_out(prog(t, 38.7, 0.5))
        put_c(f, A["who"], y, p, dy=14 * (1 - p))
        put_c(f, A["role"], y + 50, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 39.0, 0.5))
        tot = 38 + 12 + A["addr"].adv
        put(f, A["pin"], W / 2 - tot / 2, y + 88 + 14 * (1 - p), p)
        put_x(f, A["addr"], W / 2 - tot / 2 + 50, y + 122, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 39.4, 0.6))
        bd = A["badge"]
        put(f, bd, (W - bd.width) / 2, y + 160 + 16 * (1 - p), p)
        p = ease_out(prog(t, 40.0, 0.6))
        if p > 0:
            bw, bh = 540, 112
            pulse = 1 + 0.025 * max(0.0, math.sin((t - 40.7) * 2.8)) * (t > 40.7)
            sc = (0.9 + 0.1 * p) * pulse
            pill = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle((0, 0, bw * 4 - 1, bh * 4 - 1), bh * 2, fill=(214, 182, 128, 255))
            pill = pill.resize((int(bw * sc), int(bh * sc)), Image.LANCZOS)
            by = y + 160 + bd.height + 40
            put(f, pill, (W - pill.width) / 2, by + (bh - pill.height) / 2, p)
            put_c(f, A["cta"], by + bh / 2 + 18, p)
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
        env = np.clip((t - start) / 2.6, 0, 1) * np.clip((end - t) / 2.6, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.35, 0.35):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.18 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.12 * np.sin(2 * np.pi * 0.08 * t)
        return gain * env * s / len(freqs)

    def bell(at, f0, g):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 1.5) * np.clip(tt / 0.008, 0, 1)
        out[idx] += g * env * (np.sin(2 * np.pi * f0 * tt) + 0.33 * np.sin(2 * np.pi * f0 * 2.76 * tt) + 0.1 * np.sin(2 * np.pi * f0 * 5.4 * tt))

    chords = [([130.81, 196.0, 246.94, 293.66, 329.63], -2, 11.5),     # C maj9
              ([110.0, 164.81, 220.0, 261.63, 293.66], 10.0, 21.5),    # A min11
              ([174.61, 220.0, 261.63, 329.63, 392.0], 20.0, 33.5),    # F maj9
              ([130.81, 196.0, 246.94, 293.66, 329.63], 32.0, DURATION + 2)]
    for fr, s, e in chords:
        out += pad(fr, s, e, 0.10)
    for at, f0 in [(0.8, 783.99), (4.6, 880.0), (10.2, 987.8), (15.7, 1046.5), (18.85, 1174.7), (21.95, 1318.5),
                   (25.05, 1174.7), (28.1, 880.0), (35.2, 1318.5), (40.0, 1046.5)]:
        bell(at, f0, 0.065)
    out *= np.clip((DURATION - t) / 1.6, 0, 1) * np.clip(t / 0.3, 0, 1)
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
        for ts in [3.0, 7.5, 13.0, 17.3, 20.4, 23.5, 26.6, 31.5, 36.8, 42.5]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"pef-{ts:04.1f}s.png"))
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
    Image.fromarray(frame_at(3.0, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
