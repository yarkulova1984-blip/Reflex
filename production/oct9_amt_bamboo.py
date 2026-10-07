"""Available Appointments — Friday, October 9, 2026 — ADVANCED MASSAGE THERAPY.

Concept "Morning Bamboo": a massage still life (bamboo massage sticks, rolled towels,
warm wood, deep teal wall echoing the logo). A virtual camera slides, pushes in and
pulls back across the plate; each time is a hero reveal in metallic gold that appears
"from nowhere" while the scene softens and returns to focus.
Type: Marcellus (classic serif caps, echoes the logo) + Josefin Sans. Gold, ivory, teal.

  python3 production/oct9_amt_bamboo.py stills
  python3 production/oct9_amt_bamboo.py video
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
from bamboo_scene import PW, PH, build_plate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")
LOGO = os.path.join(ROOT, "brand", "locations", "advanced-massage-therapy-logo.png")
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-09-amt-available-appointments"
W, H, FPS = 1080, 1920, 30
DURATION = 30.0

IVORY = (244, 238, 226)
TEAL = (120, 206, 210)
NIGHT = (8, 14, 16)

# ---------------------------------------------------------------- facts (never edit without the owner)
LOCATION = "Advanced Massage Therapy"
ADDRESS = "2020 Corydon Ave, Winnipeg"
THERAPIST = "Zarina, RCRT"
DAY, MONTH, DAYNUM = "FRIDAY", "October", "9"
TIMES = [("9:15", "a.m."), ("10:30", "a.m."), ("11:45", "a.m.")]
SERVICES = ["Foot Reflexology", "Hand Reflexology", "Facial Reflexology", "Spanish Massage", "Bamboo Massage"]


def marc(size):
    return ImageFont.truetype(os.path.join(FONTS, "Marcellus-Regular.ttf"), size)


def jos(size, var="Regular"):
    f = ImageFont.truetype(os.path.join(FONTS, "JosefinSans[wght].ttf"), size)
    f.set_variation_by_name(var)
    return f


def gold_fill(w, h):
    """Refined metallic gold: soft vertical gradient with a gentle diagonal sheen."""
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    top, mid, bot = np.array([238, 214, 162]), np.array([206, 168, 102]), np.array([158, 118, 62])
    g = np.where(y < 0.55, top + (mid - top) * (y / 0.55)[..., None][..., 0][..., None] if False else 0, 0)
    col = np.empty((h, w, 3), np.float32)
    k = np.clip(y / 0.55, 0, 1)
    col[:] = (top * (1 - k[..., None]) + mid * k[..., None])
    k2 = np.clip((y - 0.55) / 0.45, 0, 1)
    col = col * (1 - k2[..., None]) + bot * k2[..., None]
    sheen = np.exp(-(((x - y * 0.4) - 0.35) / 0.12) ** 2)[..., None] * 0.18
    col = col * (1 - sheen) + np.array([255, 240, 205]) * sheen
    return col


class Text:
    def __init__(self, txt, fnt, fill, tracking=0, shadow=0.7):
        kw = {"features": ["lnum"]}
        asc, desc = fnt.getmetrics()
        pad = int(fnt.size * 0.35)
        width = (sum(fnt.getlength(c, **kw) for c in txt) + tracking * (len(txt) - 1)) if tracking else fnt.getlength(txt, **kw)
        size = (math.ceil(width) + 2 * pad, asc + desc + pad)
        mask = Image.new("L", size, 0)
        d = ImageDraw.Draw(mask)
        if tracking:
            x = pad
            for c in txt:
                d.text((x, asc), c, font=fnt, fill=255, anchor="ls", **kw)
                x += fnt.getlength(c, **kw) + tracking
        else:
            d.text((pad, asc), txt, font=fnt, fill=255, anchor="ls", **kw)
        if fill == "gold":
            col = gold_fill(*size)
            rgba = np.concatenate([col, np.asarray(mask, np.float32)[..., None]], -1)
            layer = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")
        else:
            layer = Image.new("RGBA", size, fill + (0,))
            layer.putalpha(mask)
        if shadow:
            sh = Image.new("RGBA", size, NIGHT + (0,))
            sh.putalpha(mask.filter(ImageFilter.GaussianBlur(max(3, fnt.size // 12))).point(lambda v: int(v * shadow)))
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


def put_x(f, tx, x, base, a=1.0, dx=0.0, dy=0.0):
    put(f, tx.img, x - tx.pad + dx, base - tx.asc + dy, a)


def put_c(f, tx, base, a=1.0, dx=0.0, dy=0.0, cx=W / 2):
    put_x(f, tx, cx - tx.adv / 2, base, a, dx, dy)


def sharp_in(f, tx, x, base, p, a=1.0, scale_from=1.0):
    """Blur -> sharp, optional subtle scale from large."""
    if p <= 0:
        return
    e = ease_out(p)
    img = tx.img
    s = scale_from + (1 - scale_from) * e
    if abs(s - 1) > 0.003:
        img = img.resize((int(tx.w * s), int(tx.h * s)), Image.LANCZOS)
    if e < 0.97:
        img = img.filter(ImageFilter.GaussianBlur(12 * (1 - e)))
    cx = x + tx.adv / 2
    put(f, img, cx - (tx.adv / 2 + tx.pad) * s, base - tx.asc * s, e * a)


def rect(f, x, y, w, h, color, a=1.0):
    if w > 0.5 and h > 0.5 and a > 0:
        f.alpha_composite(Image.new("RGBA", (int(w), int(h)), color + (int(255 * a),)), (int(x), int(y)))


def gold_line(f, cx, y, length, a=1.0, thick=3):
    if length <= 1 or a <= 0:
        return
    col = gold_fill(int(length), thick)
    im = Image.fromarray(np.concatenate([col, np.full((thick, int(length), 1), 255 * a)], -1).astype(np.uint8), "RGBA")
    f.alpha_composite(im, (int(cx - length / 2), int(y)))


def vgrad(f, y0, y1, a0, a1, a):
    if a <= 0:
        return
    h = int(y1 - y0)
    col = np.linspace(a0, a1, h, dtype=np.float32)[:, None] * a
    m = Image.fromarray((np.repeat(col, W, 1) * 255).astype(np.uint8), "L")
    s = Image.new("RGBA", (W, h), NIGHT + (0,))
    s.putalpha(m)
    f.alpha_composite(s, (0, int(y0)))


def pin_icon(size, color):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (255,)
    lw = int(s * .075)
    cx, cy, r = s * .5, s * .40, s * .26
    d.arc((cx - r, cy - r, cx + r, cy + r), 140, 400, fill=c, width=lw)
    for a in (140, 40):
        p = (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
        d.line((p, (cx, s * .92)), fill=c, width=lw)
    return im.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- camera over the plate
# keyframes: (time, centre_x, centre_y, crop_width)
CAM = [(0.0, 780, 1377, 1450), (3.8, 900, 1377, 1450), (7.2, 920, 1420, 1400),
       (10.8, 1150, 1700, 1120),            # push-in toward the bamboo (time 1)
       (14.6, 640, 1648, 1180),             # lateral slide to the towels (time 2)
       (18.4, 880, 1471, 1340),             # gentle pull-back (time 3)
       (24.6, 860, 1337, 1440), (30.0, 850, 1340, 1500)]


def camera(t):
    for (t0, x0, y0, w0), (t1, x1, y1, w1) in zip(CAM, CAM[1:]):
        if t0 <= t <= t1:
            e = ease_in_out((t - t0) / (t1 - t0))
            return x0 + (x1 - x0) * e, y0 + (y1 - y0) * e, w0 + (w1 - w0) * e
    return CAM[-1][1:]


def render_scene(t, A, soften=0.0):
    cx, cy, cw = camera(t)
    ch = cw * H / W
    x0, y0 = cx - cw / 2, cy - ch / 2
    box = (x0, y0, x0 + cw, y0 + ch)
    img = A["plate"].transform((W, H), Image.EXTENT, box, Image.BILINEAR)
    # foreground moves 1.5x (parallax), relative to the plate centre
    fx = (cx - PW / 2) * 0.5
    fy = (cy - PH / 2) * 0.5
    fbox = (x0 + fx, y0 + fy, x0 + fx + cw, y0 + fy + ch)
    fg = A["fg"].transform((W, H), Image.EXTENT, fbox, Image.BILINEAR)
    img.alpha_composite(fg)
    if soften > 0.01:
        img = img.filter(ImageFilter.GaussianBlur(9 * soften))
    arr = np.asarray(img.convert("RGB"), np.float32) + A["grain"][int(t * 15) % 3]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


# ---------------------------------------------------------------- assets
def build():
    plate, fg = build_plate()
    A = {"plate": plate, "fg": fg}
    rng = np.random.default_rng(5)
    A["grain"] = [rng.normal(0, 2.6, (H, W, 1)).astype(np.float32) for _ in range(3)]
    A["three"] = Text("3", marc(430), "gold")
    A["morning"] = Text("MORNING", jos(78, "SemiBold"), IVORY, tracking=10)
    A["openings"] = Text("OPENINGS", jos(78, "SemiBold"), IVORY, tracking=10)
    A["this"] = Text("this Friday", marc(66), TEAL)
    days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", DAY]
    A["days"] = [Text(d, jos(76, "Light"), IVORY, tracking=16) for d in days[:-1]] + [Text(DAY, jos(84, "SemiBold"), "gold", tracking=18)]
    A["date"] = Text(f"{MONTH} {DAYNUM}", marc(128), IVORY)
    A["times"] = [(Text(n, marc(250), "gold"), Text(s, jos(64, "Light"), IVORY, tracking=4),
                   Text(f"OPENING  {i + 1}  OF  3", jos(32, "SemiBold"), TEAL, tracking=8)) for i, (n, s) in enumerate(TIMES)]
    A["choose"] = Text("Choose your", jos(56, "Light"), IVORY, tracking=2)
    A["treatment"] = Text("TREATMENT", marc(104), "gold", tracking=6)
    A["svc"] = [Text(s, marc(66), IVORY) for s in SERVICES]
    logo = Image.open(LOGO).convert("RGBA")
    lw = 640
    A["logo"] = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    A["with"] = Text(f"with {THERAPIST}", jos(44, "Regular"), IVORY, tracking=1)
    A["pin"] = pin_icon(40, TEAL)
    A["addr"] = Text(ADDRESS, jos(40, "Regular"), IVORY, tracking=1)
    A["end_day"] = Text(f"{DAY}, {MONTH.upper()} {DAYNUM}", jos(40, "SemiBold"), "gold", tracking=8)
    A["end_times"] = [(Text(n, marc(98), "gold"), Text(s, jos(40, "Regular"), IVORY, tracking=3)) for n, s in TIMES]
    A["cta"] = Text("DM TO BOOK", jos(46, "SemiBold"), IVORY, tracking=12)
    return A


TIME_BEATS = [(7.2, 10.95), (10.95, 14.7), (14.7, 18.45)]


def frame_at(t, A):
    soften = 0.0
    for s0, s1 in TIME_BEATS:   # background softens as each time appears, then returns to focus
        if s0 <= t < s1:
            soften = math.exp(-((t - (s0 + 0.55)) / 0.45) ** 2)
    f = render_scene(t, A, soften)
    vgrad(f, 0, 1150, 0.55, 0.0, 1.0)   # gentle support for type on the wall

    # ---- Beat 1: countdown hook (0 – 3.9)
    if t < 4.0:
        q = ease_in_out(prog(t, 3.45, 0.45))
        a = 1 - q
        sharp_in(f, A["three"], 110, 860, prog(t, 0.1, 0.8), a, scale_from=1.12)
        p = ease_out(prog(t, 0.55, 0.6))
        put_x(f, A["morning"], 440, 610, p * a, dx=-60 * (1 - p))
        p = ease_out(prog(t, 0.75, 0.6))
        put_x(f, A["openings"], 440, 710, p * a, dx=-60 * (1 - p))
        p = ease_out(prog(t, 1.2, 0.6))
        put_x(f, A["this"], 444, 820, p * a, dy=20 * (1 - p))

    # ---- Beat 2: day scroll + date (3.8 – 7.2)
    if 3.8 <= t < 7.3:
        q = ease_in_out(prog(t, 6.85, 0.4))
        a = 1 - q
        step = 118
        sc = ease_in_out(prog(t, 3.85, 1.5)) * step * (len(A["days"]) - 1)
        for i, d in enumerate(A["days"]):
            y = 620 + i * step - sc
            dist = abs(y - 620) / step
            al = max(0.0, 1 - dist * 0.55) * (0.35 if i < len(A["days"]) - 1 else 1.0)
            if i == len(A["days"]) - 1:
                al = max(al, ease_out(prog(t, 4.9, 0.4)))
            if -100 < y < 1200:
                put_c(f, d, y, al * a)
        sharp_in(f, A["date"], W / 2 - A["date"].adv / 2, 800, prog(t, 5.3, 0.7), a)
        gold_line(f, W / 2, 850, 260 * ease_in_out(prog(t, 5.8, 0.6)), a)

    # ---- Beats 3–5: hero time reveals
    for i, (s0, s1) in enumerate(TIME_BEATS):
        if s0 <= t < s1 + 0.05:
            q = ease_in_out(prog(t, s1 - 0.45, 0.45))
            a = 1 - q
            num, suf, lab = A["times"][i]
            p = ease_out(prog(t, s0 + 0.15, 0.5))
            put_c(f, lab, 500, p * a, dy=14 * (1 - p))
            tot = num.adv + 22 + suf.adv
            x = W / 2 - tot / 2
            sharp_in(f, num, x, 760, prog(t, s0 + 0.35, 0.65), a)
            ps = ease_out(prog(t, s0 + 0.8, 0.5))
            put_x(f, suf, x + num.adv + 22, 760, ps * a, dx=-20 * (1 - ps))
            gold_line(f, W / 2, 810, 420 * ease_in_out(prog(t, s0 + 0.9, 0.8)), a, thick=2)

    # ---- Beat 6: services, introduced one by one (18.45 – 24.7)
    if 18.45 <= t < 24.8:
        q = ease_in_out(prog(t, 24.3, 0.45))
        a = 1 - q
        p = ease_out(prog(t, 18.5, 0.6))
        put_c(f, A["choose"], 420, p * a, dy=16 * (1 - p))
        sharp_in(f, A["treatment"], W / 2 - A["treatment"].adv / 2, 530, prog(t, 18.75, 0.6), a)
        gold_line(f, W / 2, 575, 200 * ease_in_out(prog(t, 19.1, 0.5)), a)
        for i, s in enumerate(A["svc"]):
            p = ease_out(prog(t, 19.4 + 0.75 * i, 0.6))
            put_c(f, s, 700 + i * 98, p * a, dx=70 * (1 - p))

    # ---- Beat 7: summary + CTA (24.7 – 30)
    if t >= 24.7:
        vgrad(f, 0, 1500, 0.45, 0.25, ease_out(prog(t, 24.7, 0.6)))
        p = ease_out(prog(t, 24.75, 0.8))
        lg = A["logo"]
        s = 0.96 + 0.04 * p
        img = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS) if s < 0.999 else lg
        put(f, img, (W - img.width) / 2, 250 + (lg.height - img.height) / 2, p)
        y = 250 + lg.height + 70
        p = ease_out(prog(t, 25.2, 0.5))
        put_c(f, A["with"], y, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 25.45, 0.5))
        tot = 40 + 12 + A["addr"].adv
        put(f, A["pin"], W / 2 - tot / 2, y + 30 + 14 * (1 - p), p)
        put_x(f, A["addr"], W / 2 - tot / 2 + 52, y + 64, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 25.7, 0.5))
        put_c(f, A["end_day"], y + 160, p, dy=14 * (1 - p))
        for i, (n, s_) in enumerate(A["end_times"]):
            cx = W / 2 + (i - 1) * 310
            sharp_in(f, n, cx - n.adv / 2, y + 290, prog(t, 25.95 + 0.2 * i, 0.5))
            pe = ease_out(prog(t, 26.2 + 0.2 * i, 0.4))
            put_c(f, s_, y + 340, pe, cx=cx)
        for i in (0, 1):
            gold_line(f, W / 2 - 155 + i * 310, y + 210, 2, ease_out(prog(t, 26.0, 0.5)), thick=150) if False else None
        p = ease_out(prog(t, 26.7, 0.6))
        if p > 0:
            bw, bh = 520, 112
            pill = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
            dd = ImageDraw.Draw(pill)
            dd.rounded_rectangle((4, 4, bw * 4 - 5, bh * 4 - 5), bh * 2, outline=(214, 178, 112, 255), width=10)
            pill = pill.resize((bw, bh), Image.LANCZOS)
            by = y + 410
            glow = 0.5 + 0.5 * math.sin((t - 27.3) * 2.6) if t > 27.3 else 0
            put(f, pill, (W - bw) / 2, by, p)
            put_c(f, A["cta"], by + bh / 2 + 17, p)
            gold_line(f, W / 2, by + bh + 24, 180 * (0.6 + 0.4 * glow) * p, p * 0.8, thick=2)
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
        env = np.clip((t - start) / 2.4, 0, 1) * np.clip((end - t) / 2.4, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.4, 0.4):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.2 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.12 * np.sin(2 * np.pi * 0.09 * t)
        return gain * env * s / len(freqs)

    rng = np.random.default_rng(2)

    def bamboo_tok(at, f0, g):
        """Hollow wooden knock: two damped partials + a tiny click."""
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 22) * np.clip(tt / 0.002, 0, 1)
        click = np.exp(-tt * 300) * rng.normal(0, 1, tt.size) * 0.3
        out[idx] += g * (env * (np.sin(2 * np.pi * f0 * tt) + 0.6 * np.sin(2 * np.pi * f0 * 2.4 * tt)) + click)

    out += pad([146.83, 220.0, 293.66, 329.63, 440.0], -2, 12.0, 0.10)   # D sus/add9
    out += pad([123.47, 185.0, 246.94, 293.66, 369.99], 10.5, 20.0, 0.10)  # B min9
    out += pad([146.83, 220.0, 277.18, 329.63, 369.99], 18.5, DURATION + 2, 0.10)  # D maj9
    for at, f0 in [(0.15, 520), (0.6, 640), (0.8, 700), (5.3, 600), (7.55, 640), (11.3, 700),
                   (15.05, 760), (18.8, 600), (24.8, 520), (26.7, 700)]:
        bamboo_tok(at, f0, 0.32)
    out *= np.clip((DURATION - t) / 1.5, 0, 1) * np.clip(t / 0.05, 0, 1)
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
        for ts in [2.4, 6.4, 9.5, 13.4, 17.2, 23.5, 29.0]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"amt-{ts:04.1f}s.png"))
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
    Image.fromarray(frame_at(2.4, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
