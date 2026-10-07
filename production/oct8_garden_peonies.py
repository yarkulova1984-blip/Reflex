"""Available Appointments — Thursday, October 8, 2026 — "Garden Light".

Concept: a sunlit garden of pink and white peonies, shot wide open (soft bokeh).
The sun comes up through the leaves. Information sits on frosted-glass panels:
Playfair Display + Montserrat with a Pinyon Script accent, soft rose and charcoal.

  python3 production/oct8_garden_peonies.py stills
  python3 production/oct8_garden_peonies.py video
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from garden_bokeh import W, H, build_garden, render_bg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")
LOGO = os.path.join(ROOT, "brand", "the-pure-escape-logo.png")
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-08-available-appointments"
FPS = 30
DURATION = 18.5

ROSE = (176, 64, 104)
INK = (44, 40, 42)
IVORY = (252, 248, 244)

# ---------------------------------------------------------------- facts (never edit without the owner)
DAY, MONTH, DAYNUM = "THURSDAY", "October", "8"
TIMES = [("5:30", "p.m."), ("6:45", "p.m.")]
THERAPIST = "Zarina, RCRT"
ADDRESS = "698 Corydon Ave"


def vfont(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if var:
        f.set_variation_by_name(var)
    return f


def play(size, var="SemiBold"):
    return vfont("PlayfairDisplay[wght].ttf", size, var)


def play_i(size, var="Medium Italic"):
    return vfont("PlayfairDisplay-Italic[wght].ttf", size, var)


def mont(size, var="SemiBold"):
    return vfont("Montserrat[wght].ttf", size, var)


def script(size):
    return vfont("PinyonScript-Regular.ttf", size)


class Text:
    def __init__(self, txt, fnt, fill, tracking=0):
        kw = {"features": ["lnum"]}
        asc, desc = fnt.getmetrics()
        pad = int(fnt.size * 0.3)
        width = (sum(fnt.getlength(c, **kw) for c in txt) + tracking * (len(txt) - 1)) if tracking else fnt.getlength(txt, **kw)
        self.img = Image.new("RGBA", (math.ceil(width) + 2 * pad, asc + desc + pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        if tracking:
            x = pad
            for c in txt:
                d.text((x, asc), c, font=fnt, fill=fill, anchor="ls", **kw)
                x += fnt.getlength(c, **kw) + tracking
        else:
            d.text((pad, asc), txt, font=fnt, fill=fill, anchor="ls", **kw)
        self.asc, self.pad, self.adv = asc, pad, width
        self.w, self.h = self.img.size


def fit(maker, txt, size, maxw, **kw):
    f = maker(size)
    while f.getlength(txt) > maxw:
        size -= 2
        f = maker(size)
    return f


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


def put_text(f, tx, x, base, a=1.0, dy=0.0):
    put(f, tx.img, x - tx.pad, base - tx.asc + dy, a)


def put_center(f, tx, base, a=1.0, dy=0.0, cx=W / 2):
    put_text(f, tx, cx - tx.adv / 2, base, a, dy)


def rise(f, tx, x, base, p, a=1.0):
    if p <= 0:
        return
    if p >= 1:
        return put_text(f, tx, x, base, a)
    off = (1 - ease_out(p)) * tx.h * 0.9
    vis = int(tx.h - off)
    if vis > 0:
        put(f, tx.img.crop((0, 0, tx.w, vis)), x - tx.pad, base - tx.asc + off, a)


def wipe(f, tx, x, base, p, a=1.0):
    if p <= 0:
        return
    vis = int(tx.w * ease_in_out(p))
    if vis > 0:
        put(f, tx.img.crop((0, 0, vis, tx.h)), x - tx.pad, base - tx.asc, a)


def glass(f, box, a, radius=48, tint=0.58):
    """Frosted-glass panel: blur what is behind it, tint with ivory, soft shadow, hairline edge."""
    if a <= 0.003:
        return
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    sh = Image.new("RGBA", (w + 160, h + 160), (40, 30, 30, 0))
    m = Image.new("L", sh.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((80, 100, 80 + w, 100 + h), radius, fill=int(70 * a))
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(34)))
    f.alpha_composite(sh, (x0 - 80, y0 - 80))
    region = f.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(26))
    ivory = Image.new("RGBA", (w, h), IVORY + (255,))
    region = Image.blend(region, ivory, tint)
    mask = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), radius * 2, fill=int(255 * a))
    region.putalpha(mask.resize((w, h), Image.LANCZOS))
    f.alpha_composite(region, (x0, y0))
    edge = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle((1, 1, w * 2 - 2, h * 2 - 2), radius * 2, outline=(255, 255, 255, int(150 * a)), width=3)
    f.alpha_composite(edge.resize((w, h), Image.LANCZOS), (x0, y0))


def rect(f, x, y, w, h, color, a=1.0):
    if w > 0.5 and h > 0.5 and a > 0:
        f.alpha_composite(Image.new("RGBA", (int(w), int(h)), color + (int(255 * a),)), (int(x), int(y)))


def icon(kind, size, color):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (255,)
    lw = int(s * .075)
    if kind == "calendar":
        d.rounded_rectangle((s * .14, s * .22, s * .86, s * .86), radius=s * .1, outline=c, width=lw)
        d.line((s * .14, s * .42, s * .86, s * .42), fill=c, width=lw)
        for x in (.34, .66):
            d.line((s * x, s * .12, s * x, s * .30), fill=c, width=lw)
    elif kind == "pin":
        cx, cy, r = s * .5, s * .40, s * .26
        d.arc((cx - r, cy - r, cx + r, cy + r), 140, 400, fill=c, width=lw)
        for a in (140, 40):
            p = (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
            d.line((p, (cx, s * .92)), fill=c, width=lw)
        rr = s * .08
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=c, width=lw)
    elif kind == "moon":  # early-evening cue next to the times
        d.ellipse((s * .16, s * .16, s * .84, s * .84), fill=c)
        d.ellipse((s * .34, s * .06, s * .98, s * .70), fill=(0, 0, 0, 0))
    return im.resize((size, size), Image.LANCZOS)


def build():
    A = {"L": build_garden()}
    inner = 760
    A["brand"] = Text("THE PURE ESCAPE", mont(28, "Medium"), IVORY, tracking=9)
    A["available"] = Text("AVAILABLE", mont(40), ROSE, tracking=16)
    A["evening"] = Text("evening", script(178), ROSE)
    A["appointments"] = Text("APPOINTMENTS", fit(play, "APPOINTMENTS", 96, inner), INK)
    A["day"] = Text(DAY, mont(42), INK, tracking=14)
    A["date"] = Text(f"{MONTH} {DAYNUM}", play_i(104), INK)

    A["cal"] = icon("calendar", 36, ROSE)
    A["pill"] = Text(f"{DAY}, {MONTH.upper()} {DAYNUM}", mont(34), INK, tracking=5)
    tf = play(214, "Bold")
    A["times"] = []
    for num, suf in TIMES:
        chars, x = [], 0
        for ch in num:
            chars.append((x, Text(ch, tf, INK)))
            x += tf.getlength(ch, features=["lnum"])
        A["times"].append((chars, x, Text(suf, mont(62, "Medium"), ROSE)))
    A["moon"] = icon("moon", 34, ROSE)
    A["after"] = Text("after-work times", play_i(48, "Italic"), INK)

    logo = Image.open(LOGO).convert("RGBA")
    lw = 600
    A["logo"] = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    A["with"] = Text("with ", mont(42, "Regular"), INK)
    A["ther"] = Text(THERAPIST, mont(42, "SemiBold"), INK)
    A["pin"] = icon("pin", 40, ROSE)
    A["addr"] = Text(ADDRESS, mont(40, "Regular"), INK)
    A["end_date"] = Text(f"{DAY} · {MONTH.upper()} {DAYNUM}", mont(32), ROSE, tracking=7)
    A["end_times"] = [(Text(n, play(104, "Bold"), INK), Text(s, mont(40, "Medium"), ROSE)) for n, s in TIMES]
    A["cta"] = Text("BOOK YOUR TIME", mont(38), IVORY, tracking=6)
    return A


def frame_at(t, A):
    sun = ease_in_out(prog(t, 0.0, 1.8))
    flash = math.exp(-((t - 11.5) / 0.35) ** 2) * 0.35   # sun flare between beats
    f = render_bg(t, A["L"], intro=sun + flash)

    # ---- Beat 1: hook (0 – 4.6)
    if t < 4.7:
        q = ease_in_out(prog(t, 4.1, 0.5))
        out, dy = 1 - q, -50 * q
        p = ease_out(prog(t, 0.3, 0.7))
        top = 520 + 60 * (1 - p) + dy
        glass(f, (90, top, 990, top + 780), p * out)
        put_center(f, A["available"], top + 130, ease_out(prog(t, 0.7, 0.5)) * out)
        ev = A["evening"]
        wipe(f, ev, W / 2 - ev.adv / 2, top + 330, prog(t, 0.95, 0.9), out)
        ap = A["appointments"]
        rise(f, ap, W / 2 - ap.adv / 2, top + 470, prog(t, 1.5, 0.7), out)
        L = 220 * ease_in_out(prog(t, 2.0, 0.6))
        rect(f, W / 2 - L / 2, top + 530, L, 3, ROSE, out)
        p2 = ease_out(prog(t, 2.3, 0.6))
        put_center(f, A["day"], top + 630 + 20 * (1 - p2), p2 * out)
        rise(f, A["date"], W / 2 - A["date"].adv / 2, top + 740, prog(t, 2.6, 0.7), out)

    # ---- Beat 2: times (4.6 – 11.6)
    if 4.6 <= t < 11.7:
        q = ease_in_out(prog(t, 11.0, 0.5))
        out, dy = 1 - q, -50 * q
        p = ease_out(prog(t, 4.6, 0.6))
        pw = A["pill"].adv + 120
        glass(f, (W / 2 - pw / 2, 300 + dy, W / 2 + pw / 2, 390 + dy), p * out, radius=45, tint=0.66)
        put(f, A["cal"], W / 2 - pw / 2 + 36, 327 + dy, p * out)
        put_text(f, A["pill"], W / 2 - pw / 2 + 88, 358, p * out, dy)
        for i, (chars, adv, suf) in enumerate(A["times"]):
            st = 5.0 + 0.8 * i
            pc = ease_out(prog(t, st, 0.7))
            sx = (-1 if i == 0 else 1) * 140 * (1 - pc)
            y0 = 500 + 400 * i + dy
            glass(f, (130 + sx, y0, 950 + sx, y0 + 330), pc * out)
            total = adv + 24 + suf.adv
            x = W / 2 - total / 2 + sx
            base = y0 + 245
            for k, (cx, ch) in enumerate(chars):
                rise(f, ch, x + cx, base, prog(t, st + 0.25 + 0.06 * k, 0.6), out)
            ps = ease_out(prog(t, st + 0.6, 0.5))
            put_text(f, suf, x + adv + 24, base, ps * out)
        p = ease_out(prog(t, 6.9, 0.7))
        tw = 34 + 16 + A["after"].adv
        glass(f, (W / 2 - tw / 2 - 50, 1300 + dy, W / 2 + tw / 2 + 50, 1390 + dy), p * out, radius=45, tint=0.66)
        put(f, A["moon"], W / 2 - tw / 2, 1328 + dy, p * out)
        put_text(f, A["after"], W / 2 - tw / 2 + 50, 1360, p * out, dy)

    # ---- Beat 3: end card (11.7 – end)
    if t >= 11.7:
        p = ease_out(prog(t, 11.7, 0.8))
        top = 290 + 50 * (1 - p)
        glass(f, (90, top, 990, top + 1090), p)
        lg = A["logo"]
        put(f, lg, (W - lg.width) / 2, top + 60, ease_out(prog(t, 12.0, 0.8)))
        y = top + 60 + lg.height + 90
        p = ease_out(prog(t, 12.5, 0.6))
        tot = A["with"].adv + A["ther"].adv
        put_text(f, A["with"], W / 2 - tot / 2, y, p, 16 * (1 - p))
        put_text(f, A["ther"], W / 2 - tot / 2 + A["with"].adv, y, p, 16 * (1 - p))
        p = ease_out(prog(t, 12.8, 0.6))
        tot = 40 + 12 + A["addr"].adv
        put(f, A["pin"], W / 2 - tot / 2, y + 36 + 16 * (1 - p), p)
        put_text(f, A["addr"], W / 2 - tot / 2 + 52, y + 72, p, 16 * (1 - p))
        L = 200 * ease_in_out(prog(t, 13.1, 0.6))
        rect(f, W / 2 - L / 2, y + 120, L, 3, ROSE)
        p = ease_out(prog(t, 13.3, 0.6))
        put_center(f, A["end_date"], y + 195, p, 16 * (1 - p))
        for i, (n, s_) in enumerate(A["end_times"]):
            cx = W / 2 + (i - 0.5) * 380
            tot = n.adv + 14 + s_.adv
            rise(f, n, cx - tot / 2, y + 330, prog(t, 13.6 + 0.25 * i, 0.6))
            pe = ease_out(prog(t, 13.9 + 0.25 * i, 0.5))
            put_text(f, s_, cx - tot / 2 + n.adv + 14, y + 330, pe)
        rect(f, W / 2 - 1, y + 245, 2, 100, ROSE, 0.45 * ease_out(prog(t, 13.7, 0.6)))
        p = ease_out(prog(t, 14.5, 0.6))
        if p > 0:
            bw, bh = 520, 108
            sc = 0.9 + 0.1 * p
            pill = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle((0, 0, bw * 4 - 1, bh * 4 - 1), radius=bh * 2, fill=ROSE + (255,))
            pill = pill.resize((int(bw * sc), int(bh * sc)), Image.LANCZOS)
            by = y + 410
            put(f, pill, (W - pill.width) / 2, by + (bh - pill.height) / 2, p)
            put_center(f, A["cta"], by + bh / 2 + 14, p)
    return np.asarray(f.convert("RGB"))


def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    out = np.zeros(n)

    def pad(freqs, start, end, gain):
        env = np.clip((t - start) / 2.5, 0, 1) * np.clip((end - t) / 2.5, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.45, 0.45):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.2 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.14 * np.sin(2 * np.pi * 0.1 * t)
        return gain * env * s / len(freqs)

    def chime(at, f0, g):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 1.8) * np.clip(tt / 0.01, 0, 1)
        out[idx] += g * env * (np.sin(2 * np.pi * f0 * tt) + 0.3 * np.sin(2 * np.pi * f0 * 2.76 * tt)
                               + 0.1 * np.sin(2 * np.pi * f0 * 5.4 * tt))

    out += pad([146.83, 220.0, 277.18, 329.63, 369.99], -2.5, 12.2, 0.11)   # D maj9
    out += pad([123.47, 185.0, 246.94, 293.66, 277.18], 10.4, DURATION + 2.5, 0.11)  # B min9
    for at, f0, g in [(0.95, 1108.7, .08), (5.25, 880.0, .06), (6.05, 987.8, .06),
                      (11.5, 1318.5, .06), (12.0, 1108.7, .07), (14.5, 1479.9, .05)]:
        chime(at, f0, g)
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
        for ts in [3.6, 8.5, 17.0]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"oct8-{ts:04.1f}s.png"))
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
