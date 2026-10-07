"""Available Appointments — Wednesday, October 7, 2026 — "Green Hour" motion design.

Renders a 1080x1920, 30 fps, ~25 s vertical video with original synthesized audio.

Usage:
  python3 production/oct7_available_appointments.py stills   # QC frames only
  python3 production/oct7_available_appointments.py video    # full MP4
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
NAME = "2026-10-07-available-appointments"

W, H, FPS = 1080, 1920, 30
DURATION = 25.0
X0 = 110  # left text margin; right safe margin is 120 px

# Palette "Green Hour": deep green + cream + gold, echoing the logo green.
FOREST = (30, 58, 43)
FOREST_LIGHT = (52, 88, 66)
CREAM = (243, 235, 221)
GOLD = (200, 164, 94)
CHARCOAL = (43, 42, 39)

# ---------------------------------------------------------------- facts (never edit without the owner)
DAY = "WEDNESDAY"
DATE = "OCTOBER 7"
TIMES = [("11:00", "a.m."), ("12:45", "p.m."), ("2:30", "p.m.")]
SERVICES = [
    ("Foot Reflexology", None),
    ("Hand Reflexology", None),
    ("Facial Reflexology", "BERGMAN METHOD"),
    ("Spanish Massage", None),
    ("Ultimate Escape Package", None),
]
THERAPIST = "Zarina, RCRT"
ADDRESS = "698 Corydon Ave"


# ---------------------------------------------------------------- helpers
def font(name, size, variation):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    f.set_variation_by_name(variation)
    return f


def jost(size, weight="Medium"):
    return font("Jost[wght].ttf", size, weight)


def serif(size, weight="SemiBold"):
    return font("CormorantGaramond[wght].ttf", size, weight)


def serif_italic(size, weight="Medium Italic"):
    return font("CormorantGaramond-Italic[wght].ttf", size, weight)


class Text:
    """A pre-rendered text layer positioned by its baseline."""

    def __init__(self, txt, fnt, fill, tracking=0, features=("lnum",)):
        # lining figures: Cormorant defaults to old-style numerals, which hurt time readability
        asc, desc = fnt.getmetrics()
        kw = {"features": list(features)} if features else {}
        if tracking:
            width = sum(fnt.getlength(c) for c in txt) + tracking * (len(txt) - 1)
        else:
            width = fnt.getlength(txt, **kw)
        self.img = Image.new("RGBA", (math.ceil(width) + 6, asc + desc), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        if tracking:
            x = 3
            for c in txt:
                d.text((x, asc), c, font=fnt, fill=fill, anchor="ls")
                x += fnt.getlength(c) + tracking
        else:
            d.text((3, asc), txt, font=fnt, fill=fill, anchor="ls", **kw)
        self.asc = asc
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
    if alpha <= 0.001:
        return
    frame.alpha_composite(with_alpha(img, alpha), (int(round(x)), int(round(y))))


def put_text(frame, tx, x, baseline, alpha=1.0, dx=0.0, dy=0.0):
    put(frame, tx.img, x + dx, baseline - tx.asc + dy, alpha)


def rise_text(frame, tx, x, baseline, p, alpha=1.0):
    """Mask reveal: text rises into a window the size of its own layer."""
    if p <= 0:
        return
    top = baseline - tx.asc
    off = (1 - ease_out(p)) * tx.h * 0.85
    visible = int(tx.h - off)
    if visible <= 0:
        return
    put(frame, tx.img.crop((0, 0, tx.w, visible)), x, top + off, alpha)


def hline(frame, x, y, length, thickness, color, alpha=1.0):
    if length <= 0.5 or alpha <= 0:
        return
    layer = Image.new("RGBA", (int(length) + 1, thickness), color + (int(255 * alpha),))
    frame.alpha_composite(layer, (int(x), int(y)))


# ---------------------------------------------------------------- icons (drawn 4x, downsampled)
def icon_canvas(size):
    s = size * 4
    return Image.new("RGBA", (s, s), (0, 0, 0, 0)), s


def icon_calendar(size, color):
    im, s = icon_canvas(size)
    d = ImageDraw.Draw(im)
    lw = int(s * 0.07)
    d.rounded_rectangle((s * .08, s * .18, s * .92, s * .92), radius=s * .12, outline=color, width=lw)
    d.line((s * .08, s * .40, s * .92, s * .40), fill=color, width=lw)
    for x in (.32, .68):
        d.line((s * x, s * .06, s * x, s * .28), fill=color, width=lw)
    return im.resize((size, size), Image.LANCZOS)


def icon_clock(size, color, p):
    im, s = icon_canvas(size)
    d = ImageDraw.Draw(im)
    lw = int(s * 0.07)
    if p > 0:
        d.arc((s * .06, s * .06, s * .94, s * .94), -90, -90 + 360 * ease_out(p), fill=color, width=lw)
    if p > 0.7:
        h = ease_out((p - 0.7) / 0.3)
        c = s / 2
        d.line((c, c, c, c - s * .28 * h), fill=color, width=lw)
        d.line((c, c, c + s * .2 * h, c + s * .02 * h), fill=color, width=lw)
    return im.resize((size, size), Image.LANCZOS)


def icon_pin(size, color):
    im, s = icon_canvas(size)
    d = ImageDraw.Draw(im)
    lw = int(s * 0.07)
    cx, cy, r = s / 2, s * .38, s * .28
    pts = []
    for i in range(0, 361, 6):
        a = math.radians(i)
        # teardrop: circle on top, point at the bottom
        if 40 <= i <= 140:
            continue
        pts.append((cx + r * math.cos(a + math.pi / 2 * 0) , cy - r * math.sin(a)))
    d.arc((cx - r, cy - r, cx + r, cy + r), 140, 400, fill=color, width=lw)
    tip = (cx, s * .94)
    left = (cx + r * math.cos(math.radians(140)), cy + r * math.sin(math.radians(140)))
    right = (cx + r * math.cos(math.radians(40)), cy + r * math.sin(math.radians(40)))
    d.line((left, tip), fill=color, width=lw)
    d.line((right, tip), fill=color, width=lw)
    rr = s * .09
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=color, width=lw)
    return im.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- backgrounds
def leaf(draw, cx, cy, length, width, angle, fill, rib):
    pts_top, pts_bot = [], []
    ca, sa = math.cos(angle), math.sin(angle)
    for i in range(41):
        s = i / 40
        x = (s - 0.5) * length
        y = width * math.sin(math.pi * s) ** 0.85
        pts_top.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
        pts_bot.append((cx + x * ca + y * sa, cy + x * sa - y * ca))
    draw.polygon(pts_top + pts_bot[::-1], fill=fill)
    if rib:
        a = (cx - 0.5 * length * ca, cy - 0.5 * length * sa)
        b = (cx + 0.5 * length * ca, cy + 0.5 * length * sa)
        draw.line((a, b), fill=rib, width=6)


def leaf_layer(specs, color, alpha, rib_alpha, blur, size=(1400, 2400)):
    big = Image.new("RGBA", (size[0] * 2, size[1] * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for cx, cy, ln, wd, ang in specs:
        leaf(d, cx * 2, cy * 2, ln * 2, wd * 2, math.radians(ang), color + (alpha,),
             color + (rib_alpha,) if rib_alpha else None)
    img = big.resize(size, Image.LANCZOS)
    return img.filter(ImageFilter.GaussianBlur(blur)) if blur else img


def gradient_bg(base, glow, glow_center, radius):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt((xx - glow_center[0]) ** 2 + (yy - glow_center[1]) ** 2) / radius
    k = np.clip(1 - dist, 0, 1) ** 2
    arr = np.array(base, np.float32)[None, None, :] * (1 - k[..., None]) + np.array(glow, np.float32)[None, None, :] * k[..., None]
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")


# ---------------------------------------------------------------- build assets once
def build():
    A = {}
    A["dark_bg"] = gradient_bg(FOREST, (48, 84, 62), (150, 250), 1500)
    A["cream_bg"] = gradient_bg((236, 226, 209), (250, 245, 236), (200, 300), 1700)
    A["leaves_far"] = leaf_layer(
        [(1150, 500, 900, 170, -55), (1000, 1250, 1000, 190, -35), (180, 1900, 800, 150, 30)],
        FOREST_LIGHT, 120, 0, 10)
    A["leaves_near"] = leaf_layer(
        [(1200, 1650, 1100, 210, -60), (1250, 950, 700, 130, -20)],
        (62, 102, 76), 150, 90, 2)
    A["leaves_cream"] = leaf_layer(
        [(1230, 1700, 1000, 190, -55), (1300, 1100, 650, 120, -25)],
        (185, 170, 130), 55, 35, 3)
    rng = np.random.default_rng(7)
    A["grain"] = [rng.normal(0, 4.2, (H, W, 1)).astype(np.int16) for _ in range(3)]

    # Beat 1
    A["brand"] = Text("THE PURE ESCAPE", jost(30, "Medium"), GOLD, tracking=9)
    A["available"] = Text("AVAILABLE", jost(146, "SemiBold"), CREAM, tracking=3)
    A["appointments"] = Text("appointments", serif_italic(132), GOLD)
    A["day"] = Text(DAY, jost(44, "Medium"), CREAM, tracking=11)
    A["date"] = Text(DATE, serif(124), CREAM)
    # Beat 2
    A["cal"] = icon_calendar(44, GOLD)
    A["label_date"] = Text(f"{DAY} · {DATE}", jost(36, "Medium"), CREAM, tracking=6)
    A["open_times"] = Text("OPEN TIMES", jost(30, "Medium"), GOLD, tracking=9)
    A["times"] = [(Text(n, serif(236), CREAM), Text(s, serif_italic(84), GOLD)) for n, s in TIMES]
    # Beat 3
    A["services_label"] = Text("SERVICES", jost(30, "Medium"), FOREST, tracking=10)
    A["services_title"] = Text("Choose your treatment", serif_italic(84), FOREST)
    svc_font = serif(76)
    A["services"] = [(Text(n, svc_font, CHARCOAL), Text(sub, jost(32, "Medium"), GOLD, tracking=7) if sub else None)
                     for n, sub in SERVICES]
    # Beat 4
    logo = Image.open(LOGO).convert("RGBA")
    lw = 720
    A["logo"] = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    A["with"] = Text("with ", jost(46, "Regular"), CHARCOAL)
    A["therapist"] = Text(THERAPIST, jost(46, "SemiBold"), FOREST)
    A["pin"] = icon_pin(46, GOLD)
    A["address"] = Text(ADDRESS, jost(42, "Regular"), CHARCOAL)
    A["end_date"] = Text(f"{DAY} · {DATE}", jost(36, "Medium"), FOREST, tracking=6)
    A["end_times"] = [(Text(n, serif(108), CHARCOAL), Text(s, serif_italic(56), GOLD)) for n, s in TIMES]
    A["cta"] = Text("BOOK NOW", jost(40, "SemiBold"), CREAM, tracking=8)
    return A


# ---------------------------------------------------------------- timeline
WIPE_START, WIPE_DUR = 11.3, 0.75


def frame_at(t, A):
    # background
    if t < WIPE_START + WIPE_DUR:
        f = A["dark_bg"].copy()
        put(f, A["leaves_far"], -160 - 4 * t, -220 - 7 * t, 1.0)
        put(f, A["leaves_near"], -160 - 9 * t, -260 - 15 * t, 1.0)
    else:
        f = A["cream_bg"].copy()
    if t >= WIPE_START:
        p = ease_in_out(prog(t, WIPE_START, WIPE_DUR))
        top = int(H * (1 - p))
        cream = A["cream_bg"].copy()
        put(cream, A["leaves_cream"], -200 - 5 * (t - WIPE_START), -260 - 8 * (t - WIPE_START))
        f.paste(cream.crop((0, top, W, H)), (0, top))
        if p < 1:
            hline(f, 0, top - 2, W, 4, GOLD, 1.0)

    # ---- Beat 1: hook (0 – 4.4)
    if t < 4.5:
        out = ease_in_out(prog(t, 3.9, 0.5))
        a_out, dy = 1 - out, -40 * out
        put_text(f, A["brand"], X0, 420, ease_out(prog(t, 0.2, 0.6)) * a_out, dy=dy)
        if t < 3.9:
            rise_text(f, A["available"], X0 - 6, 760, prog(t, 0.35, 0.7))
        else:
            put_text(f, A["available"], X0 - 6, 760, a_out, dy=dy)
        p = ease_out(prog(t, 0.95, 0.7))
        put_text(f, A["appointments"], X0 - 40 * (1 - p), 910, p * a_out, dy=dy)
        hline(f, X0, 1000 + dy, 260 * ease_in_out(prog(t, 1.55, 0.6)), 3, GOLD, a_out)
        p = ease_out(prog(t, 1.9, 0.6))
        put_text(f, A["day"], X0, 1120 + 20 * (1 - p), p * a_out, dy=dy)
        if t < 3.9:
            rise_text(f, A["date"], X0 - 4, 1260, prog(t, 2.15, 0.7))
        else:
            put_text(f, A["date"], X0 - 4, 1260, a_out, dy=dy)

    # ---- Beat 2: times (4.3 – 11.5)
    if 4.3 <= t < 11.6:
        out = ease_in_out(prog(t, 10.9, 0.5))
        a_out, dy = 1 - out, -50 * out
        p = ease_out(prog(t, 4.3, 0.6))
        put(f, A["cal"], X0, 360 - 36 + dy, p * a_out)
        put_text(f, A["label_date"], X0 + 66 - 20 * (1 - p), 360, p * a_out, dy=dy)
        put(f, icon_clock(60, GOLD, prog(t, 4.6, 0.9)), X0, 560 + dy, a_out)
        p = ease_out(prog(t, 4.9, 0.6))
        put_text(f, A["open_times"], X0 + 84, 602, p * a_out, dy=dy)
        for i, (num, suf) in enumerate(A["times"]):
            start = 5.1 + 0.8 * i
            base = 870 + 270 * i
            if t < 10.9:
                rise_text(f, num, X0 - 8, base, prog(t, start, 0.65))
            else:
                put_text(f, num, X0 - 8, base, a_out, dy=dy)
            ps = ease_out(prog(t, start + 0.35, 0.5))
            put_text(f, suf, X0 + num.w + 10 - 20 * (1 - ps), base, ps * a_out, dy=dy)
            hline(f, X0, base + 60 + dy, 860 * ease_in_out(prog(t, start + 0.2, 0.7)), 2, GOLD, 0.55 * a_out)

    # ---- Beat 3: services (12.0 – 17.7)
    if 12.0 <= t < 17.8:
        out = ease_in_out(prog(t, 17.2, 0.5))
        a_out, dy = 1 - out, -40 * out
        p = ease_out(prog(t, 12.0, 0.6))
        put_text(f, A["services_label"], X0, 420, p * a_out, dy=dy)
        p = ease_out(prog(t, 12.2, 0.7))
        put_text(f, A["services_title"], X0 - 30 * (1 - p), 530, p * a_out, dy=dy)
        hline(f, X0, 580 + dy, 200 * ease_in_out(prog(t, 12.5, 0.6)), 3, GOLD, a_out)
        base = 740
        for i, (name, sub) in enumerate(A["services"]):
            p = ease_out(prog(t, 12.7 + 0.35 * i, 0.55))
            dot = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
            ImageDraw.Draw(dot).ellipse((0, 0, 11, 11), fill=GOLD + (255,))
            put(f, dot, X0, base - 28 + dy, p * a_out)
            put_text(f, name, X0 + 36 - 40 * (1 - p), base, p * a_out, dy=dy)
            if sub:
                put_text(f, sub, X0 + 40 - 40 * (1 - p), base + 60, p * a_out, dy=dy)
                base += 62
            base += 145

    # ---- Beat 4: end card (17.7 – end)
    if t >= 17.7:
        p = ease_out(prog(t, 17.7, 0.9))
        sc = 0.96 + 0.04 * p
        logo = A["logo"]
        lg = logo.resize((int(logo.width * sc), int(logo.height * sc)), Image.LANCZOS) if sc < 0.999 else logo
        put(f, lg, (W - lg.width) / 2, 300 + (logo.height - lg.height) / 2, p)

        p = ease_out(prog(t, 18.3, 0.6))
        total = A["with"].w + A["therapist"].w
        x = (W - total) / 2
        put_text(f, A["with"], x, 780, p, dy=15 * (1 - p))
        put_text(f, A["therapist"], x + A["with"].w, 780, p, dy=15 * (1 - p))

        p = ease_out(prog(t, 18.6, 0.6))
        total = 46 + 14 + A["address"].w
        x = (W - total) / 2
        put(f, A["pin"], x, 780 + 75 - 40 + 15 * (1 - p), p)
        put_text(f, A["address"], x + 60, 860, p, dy=15 * (1 - p))

        L = 220 * ease_in_out(prog(t, 18.9, 0.6))
        hline(f, (W - L) / 2, 930, L, 3, GOLD)

        p = ease_out(prog(t, 19.1, 0.6))
        put_text(f, A["end_date"], (W - A["end_date"].w) / 2, 1010, p, dy=15 * (1 - p))
        for i, (num, suf) in enumerate(A["end_times"]):
            ps = prog(t, 19.4 + 0.25 * i, 0.6)
            total = num.w + 12 + suf.w
            x = (W - total) / 2
            base = 1135 + 115 * i
            rise_text(f, num, x, base, ps)
            put_text(f, suf, x + num.w + 12, base, ease_out(prog(t, 19.6 + 0.25 * i, 0.5)))

        p = ease_out(prog(t, 20.4, 0.6))
        if p > 0:
            bw, bh = 460, 104
            sc = 0.92 + 0.08 * p
            pill = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle((0, 0, bw * 4 - 1, bh * 4 - 1), radius=bh * 2, fill=FOREST + (255,))
            pill = pill.resize((int(bw * sc), int(bh * sc)), Image.LANCZOS)
            px, py = (W - pill.width) / 2, 1420 + (bh - pill.height) / 2
            put(f, pill, px, py, p)
            cta = A["cta"]
            put_text(f, cta, (W - cta.w) / 2 + 4, 1420 + bh / 2 + 15, p)

    # grain
    arr = np.asarray(f.convert("RGB")).astype(np.int16)
    arr += A["grain"][int(t * FPS / 2) % 3]
    return np.clip(arr, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- audio (original, synthesized)
def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    out = np.zeros(n)

    def pad(freqs, start, end, gain):
        env = np.clip((t - start) / 2.5, 0, 1) * np.clip((end - t) / 2.5, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.6, 0.6):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.25 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.15 * np.sin(2 * np.pi * 0.12 * t)  # slow breathing
        return gain * env * s / len(freqs)

    def chime(at, f0, gain):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 2.2) * np.clip(tt / 0.01, 0, 1)
        out[idx] += gain * env * (np.sin(2 * np.pi * f0 * tt) + 0.35 * np.sin(2 * np.pi * f0 * 2.76 * tt)
                                  + 0.15 * np.sin(2 * np.pi * f0 * 5.4 * tt))

    # F major 9 -> D minor 9: warm, calm, unresolved-to-resolved
    out += pad([174.61, 220.00, 261.63, 329.63, 392.00], -2.5, 12.8, 0.11)
    out += pad([146.83, 220.00, 261.63, 349.23, 329.63], 10.8, DURATION + 2.5, 0.11)
    for at, f0, g in [(0.35, 1046.5, 0.10), (5.1, 880.0, 0.07), (5.9, 987.8, 0.07), (6.7, 1046.5, 0.07),
                      (17.7, 1046.5, 0.09), (19.4, 880.0, 0.05), (20.4, 1318.5, 0.06)]:
        chime(at, f0, g)
    # soft airy swell into the wipe
    rng = np.random.default_rng(3)
    noise = np.convolve(rng.normal(0, 1, n), np.ones(60) / 60, mode="same")
    sw = np.exp(-((t - 11.9) / 0.45) ** 2)
    out += 0.05 * noise * sw
    fade = np.clip((DURATION - t) / 1.2, 0, 1) * np.clip(t / 0.3, 0, 1)
    out *= fade
    out = out / np.max(np.abs(out)) * 10 ** (-6 / 20)  # peak -6 dBFS
    data = (np.stack([out, out], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------- main
def main(mode):
    os.makedirs(OUT_DIR, exist_ok=True)
    A = build()
    if mode == "stills":
        qc = os.path.join(OUT_DIR, "qc")
        os.makedirs(qc, exist_ok=True)
        for ts in [1.0, 3.2, 5.6, 9.0, 11.7, 15.5, 23.0]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"{NAME}-{ts:05.1f}s.png"))
        return
    wav = os.path.join(OUT_DIR, f"{NAME}.wav")
    synth_audio(wav)
    mp4 = os.path.join(OUT_DIR, f"{NAME}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DURATION * FPS)
    for i in range(total):
        proc.stdin.write(frame_at(i / FPS, A).tobytes())
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    Image.fromarray(frame_at(3.2, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
