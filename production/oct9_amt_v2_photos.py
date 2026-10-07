"""Advanced Massage Therapy — Friday, October 9, 2026 — v2 "Candlelit Morning" (owner's photos).

Three owner-supplied photos (reflexology thumb-walk, foot hold, treatment room), each
brought to life with its own camera move; scenes change through a soft defocus.
Type: Cinzel (classical caps, in the spirit of the logo) + Raleway. Metallic gold,
ivory and a touch of the logo teal. No boxes: type floats in the dark negative space.

  python3 production/oct9_amt_v2_photos.py stills
  python3 production/oct9_amt_v2_photos.py video
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
PHOTOS = os.path.join(ROOT, "brand", "photos", "amt")
LOGO = os.path.join(ROOT, "brand", "locations", "advanced-massage-therapy-logo.png")
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-09-amt-available-appointments-v2"
W, H, FPS = 1080, 1920, 30
DURATION = 30.0

IVORY = (246, 238, 224)
TEAL = (126, 210, 214)
NIGHT = (10, 8, 6)

# ---------------------------------------------------------------- facts (never edit without the owner)
LOCATION = "Advanced Massage Therapy"
ADDRESS = "2020 Corydon Ave, Winnipeg"
THERAPIST = "Zarina, RCRT"
DAY, MONTH, DAYNUM = "FRIDAY", "October", "9"
TIMES = [("9:15", "a.m."), ("10:30", "a.m."), ("11:45", "a.m.")]
SERVICES = ["Foot Reflexology", "Hand Reflexology", "Facial Reflexology", "Spanish Massage", "Bamboo Massage"]


def cinzel(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "Cinzel[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def raleway(size, wght=400, italic=False):
    f = ImageFont.truetype(os.path.join(FONTS, "Raleway-Italic[wght].ttf" if italic else "Raleway[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


# ---------------------------------------------------------------- living photos
def extend_top(im, frac):
    """Add dark, defocused headroom above a photo (its top is already dark bokeh),
    so type can sit above the feet and hands instead of covering them."""
    add = int(im.height * frac)
    strip = im.crop((0, 0, im.width, max(8, int(im.height * 0.12))))
    strip = strip.transpose(Image.FLIP_TOP_BOTTOM).resize((im.width, add), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    arr = np.asarray(strip, np.float32) * np.linspace(0.55, 1.0, add, dtype=np.float32)[:, None, None]
    out = Image.new("RGB", (im.width, im.height + add))
    out.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (0, 0))
    out.paste(im, (0, add))
    m = Image.new("L", (im.width, 40), 0)   # feather the seam
    for y in range(40):
        ImageDraw.Draw(m).line((0, y, im.width, y), fill=int(255 * y / 39))
    seam = im.crop((0, 0, im.width, 40))
    out.paste(Image.blend(Image.fromarray(np.clip(arr[-40:], 0, 255).astype(np.uint8)), seam, 0.5), (0, add), None)
    return out


def load_photo(name, grade, headroom=0.0):
    im = Image.open(os.path.join(PHOTOS, name)).convert("RGB")
    if headroom:
        im = extend_top(im, headroom)
    k = max(W / im.width, H / im.height) * 1.5          # headroom for push-ins
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=3, percent=70, threshold=2))
    arr = np.asarray(im, np.float32) * np.array(grade, np.float32)  # gentle warm, unified grade
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# camera keyframes per photo: (t, centre_u, centre_v, zoom); zoom 1 = frame just covered
SHOTS = {
    "thumb": [(0.0, 0.50, 0.50, 1.00), (7.0, 0.52, 0.52, 1.06), (11.2, 0.56, 0.60, 1.16)],   # slow push-in to the thumb
    "hold": [(10.9, 0.40, 0.50, 1.10), (14.8, 0.58, 0.50, 1.10), (18.9, 0.60, 0.56, 1.30)],   # lateral slide, then wide-to-detail
    "room": [(18.6, 0.44, 0.52, 1.14), (24.6, 0.56, 0.50, 1.16), (30.0, 0.52, 0.50, 1.02)],   # slide, then gentle pull-back
}
# scene windows (photo, start, end); cross-defocus where they overlap
SCENES = [("thumb", 0.0, 11.2), ("hold", 10.9, 18.9), ("room", 18.6, 30.0)]


def cam(name, t):
    ks = SHOTS[name]
    if t <= ks[0][0]:
        return ks[0][1:]
    for (t0, *a), (t1, *b) in zip(ks, ks[1:]):
        if t0 <= t <= t1:
            e = ease_in_out((t - t0) / (t1 - t0))
            return tuple(x + (y - x) * e for x, y in zip(a, b))
    return ks[-1][1:]


def shot(A, name, t):
    im = A["photos"][name]
    u, v, z = cam(name, t)
    base = max(W / im.width, H / im.height) * im.width     # covered width in source px... per zoom
    cw = im.width / (z * (im.width / base)) if False else (W * im.width / (base)) / z * (base / W)
    # crop size in source pixels for this zoom (z=1 => crop covers whole short side)
    scale_cover = max(W / im.width, H / im.height)
    cw = W / scale_cover / z
    ch = H / scale_cover / z
    cx = np.clip(u * im.width, cw / 2, im.width - cw / 2)
    cy = np.clip(v * im.height, ch / 2, im.height - ch / 2)
    return im.transform((W, H), Image.EXTENT, (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2), Image.BILINEAR)


def background(t, A, soften=0.0):
    active = [(n, s, e) for n, s, e in SCENES if s - 0.01 <= t <= e]
    if len(active) == 2:   # cross-defocus transition
        (n1, _, e1), (n2, s2, _) = active
        p = (t - s2) / (e1 - s2)
        a = shot(A, n1, t).filter(ImageFilter.GaussianBlur(14 * p))
        b = shot(A, n2, t).filter(ImageFilter.GaussianBlur(14 * (1 - p)))
        img = Image.blend(a, b, ease_in_out(p))
    else:
        img = shot(A, active[0][0], t)
        if soften > 0.01:
            img = img.filter(ImageFilter.GaussianBlur(10 * soften))
    arr = np.asarray(img, np.float32) * A["vig"] + A["grain"][int(t * 15) % 3]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def build():
    A = {"photos": {
        "thumb": load_photo("reflexology-thumb.jpg", (1.0, 0.98, 0.95), headroom=0.35),
        "hold": load_photo("foot-hold.jpg", (1.0, 0.98, 0.95)),
        "room": load_photo("room-towels.jpg", (1.0, 0.98, 0.95)),
    }}
    rng = np.random.default_rng(9)
    A["grain"] = [rng.normal(0, 3.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.32 * np.clip(((xx - W / 2) / W) ** 2 * 2.6 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]

    A["your"] = Text("YOUR WEEKEND", cinzel(92, 500), IVORY, tracking=6)
    A["starts"] = Text("STARTS EARLY", cinzel(118, 700), "gold", tracking=4)
    A["sub"] = Text("3 morning openings  ·  Friday", raleway(44, 400, italic=True), IVORY, tracking=1)
    A["day"] = Text(DAY, raleway(46, 600), TEAL, tracking=22)
    A["date"] = Text(f"{MONTH} {DAYNUM}", cinzel(140, 500), IVORY)
    A["times"] = [(Text(n, cinzel(240, 600), "gold"), Text(s, raleway(62, 300), IVORY, tracking=4)) for n, s in TIMES]
    A["choose"] = Text("YOUR CHOICE OF", raleway(40, 500), TEAL, tracking=14)
    A["svc"] = [Text(s, cinzel(68, 500), IVORY, tracking=2) for s in SERVICES]
    logo = Image.open(LOGO).convert("RGBA")
    lw = 680
    A["logo"] = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    A["with"] = Text(f"with {THERAPIST}", raleway(44, 400), IVORY, tracking=1)
    A["pin"] = pin_icon(40, TEAL)
    A["addr"] = Text(ADDRESS, raleway(42, 400), IVORY, tracking=1)
    A["end_day"] = Text(f"{DAY}  ·  {MONTH.upper()} {DAYNUM}", raleway(42, 600), "gold", tracking=8)
    A["end_times"] = [(Text(n, cinzel(96, 600), "gold"), Text(s, raleway(38, 400), IVORY, tracking=3)) for n, s in TIMES]
    A["cta"] = Text("DM TO BOOK", raleway(48, 700), NIGHT, tracking=12, shadow=0)
    return A


TIME_BEATS = [(7.3, 10.85), (11.3, 14.85), (15.0, 18.55)]


def frame_at(t, A):
    soften = 0.0
    for s0, s1 in TIME_BEATS:
        if s0 <= t < s1:
            soften = math.exp(-((t - (s0 + 0.5)) / 0.42) ** 2)
    f = background(t, A, soften)
    vgrad(f, 0, 1000, 0.72, 0.0, 1.0)            # dark negative space for type

    # ---- Hook (0 – 3.9): emotional statement, letter-tracking + blur reveals
    if t < 4.0:
        q = ease_in_out(prog(t, 3.5, 0.45))
        a = 1 - q
        p = ease_out(prog(t, 0.15, 0.7))
        put_c(f, A["your"], 440, p * a, dy=-26 * (1 - p))
        sharp_in(f, A["starts"], W / 2 - A["starts"].adv / 2, 590, prog(t, 0.6, 0.8), a, scale_from=1.1)
        gold_line(f, W / 2, 636, 320 * ease_in_out(prog(t, 1.3, 0.6)), a)
        p = ease_out(prog(t, 1.6, 0.6))
        put_c(f, A["sub"], 712, p * a, dy=18 * (1 - p))

    # ---- Date (3.8 – 7.3): FRIDAY slides in from the right, date from soft focus
    if 3.8 <= t < 7.4:
        q = ease_in_out(prog(t, 6.9, 0.4))
        a = 1 - q
        p = ease_out(prog(t, 3.9, 0.7))
        put_c(f, A["day"], 430, p * a, dx=140 * (1 - p))
        sharp_in(f, A["date"], W / 2 - A["date"].adv / 2, 600, prog(t, 4.3, 0.8), a)
        gold_line(f, W / 2, 650, 240 * ease_in_out(prog(t, 5.0, 0.6)), a)

    # ---- Hero time reveals: scene softens, gold time appears sharp, scene refocuses
    for i, (s0, s1) in enumerate(TIME_BEATS):
        if s0 <= t < s1 + 0.05:
            q = ease_in_out(prog(t, s1 - 0.45, 0.45))
            a = 1 - q
            num, suf = A["times"][i]
            tot = num.adv + 24 + suf.adv
            x = W / 2 - tot / 2
            sharp_in(f, num, x, 560, prog(t, s0 + 0.25, 0.7), a)
            ps = ease_out(prog(t, s0 + 0.75, 0.5))
            put_x(f, suf, x + num.adv + 24, 560, ps * a, dy=-22 * (1 - ps))
            gold_line(f, W / 2, 610, 380 * ease_in_out(prog(t, s0 + 0.8, 0.8)), a, thick=2)
            # small progress dots: which opening this is
            for k in range(3):
                col = (214, 178, 112) if k == i else IVORY
                dot = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
                ImageDraw.Draw(dot).ellipse((2, 2, 16, 16), fill=col + (255 if k == i else 120,))
                put(f, dot, W / 2 - 40 + k * 32, 650, ease_out(prog(t, s0 + 0.4, 0.4)) * a)

    # ---- Services (18.9 – 24.7): one by one, rising from soft focus
    if 18.9 <= t < 24.8:
        q = ease_in_out(prog(t, 24.3, 0.45))
        a = 1 - q
        p = ease_out(prog(t, 19.0, 0.6))
        put_c(f, A["choose"], 430, p * a, dy=16 * (1 - p))
        gold_line(f, W / 2, 470, 160 * ease_in_out(prog(t, 19.3, 0.5)), a)
        for i, s in enumerate(A["svc"]):
            sharp_in(f, s, W / 2 - s.adv / 2, 580 + i * 104, prog(t, 19.5 + 0.7 * i, 0.6), a)

    # ---- Summary + CTA (24.7 – 30)
    if t >= 24.7:
        p = ease_out(prog(t, 24.7, 0.7))
        vgrad(f, 0, H, 0.6, 0.6, p)
        lg = A["logo"]
        s = 0.96 + 0.04 * p
        img = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS) if s < 0.999 else lg
        put(f, img, (W - img.width) / 2, 230 + (lg.height - img.height) / 2, p)
        y = 230 + lg.height + 70
        p = ease_out(prog(t, 25.2, 0.5))
        put_c(f, A["with"], y, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 25.45, 0.5))
        tot = 40 + 12 + A["addr"].adv
        put(f, A["pin"], W / 2 - tot / 2, y + 30 + 14 * (1 - p), p)
        put_x(f, A["addr"], W / 2 - tot / 2 + 52, y + 64, p, dy=14 * (1 - p))
        p = ease_out(prog(t, 25.7, 0.5))
        put_c(f, A["end_day"], y + 165, p, dy=14 * (1 - p))
        for i, (n, s_) in enumerate(A["end_times"]):
            cx = W / 2 + (i - 1) * 320
            sharp_in(f, n, cx - n.adv / 2, y + 295, prog(t, 25.95 + 0.2 * i, 0.5))
            put_c(f, s_, y + 345, ease_out(prog(t, 26.2 + 0.2 * i, 0.4)), cx=cx)
        p = ease_out(prog(t, 26.7, 0.6))
        if p > 0:
            bw, bh = 540, 116
            pulse = 1 + 0.025 * max(0.0, math.sin((t - 27.4) * 2.8)) * (t > 27.4)
            sc = (0.9 + 0.1 * p) * pulse
            pill = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle((0, 0, bw * 4 - 1, bh * 4 - 1), bh * 2, fill=(214, 178, 112, 255))
            pill = pill.resize((int(bw * sc), int(bh * sc)), Image.LANCZOS)
            by = y + 420
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
        env = np.clip((t - start) / 2.4, 0, 1) * np.clip((end - t) / 2.4, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.4, 0.4):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.2 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.12 * np.sin(2 * np.pi * 0.09 * t)
        return gain * env * s / len(freqs)

    def bell(at, f0, g):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 1.6) * np.clip(tt / 0.008, 0, 1)
        out[idx] += g * env * (np.sin(2 * np.pi * f0 * tt) + 0.35 * np.sin(2 * np.pi * f0 * 2.76 * tt) + 0.12 * np.sin(2 * np.pi * f0 * 5.4 * tt))

    out += pad([110.0, 164.81, 220.0, 277.18, 329.63], -2, 11.6, 0.10)    # A maj9
    out += pad([146.83, 220.0, 277.18, 329.63, 369.99], 10.4, 19.6, 0.10)  # D maj9
    out += pad([123.47, 185.0, 246.94, 293.66, 369.99], 18.2, DURATION + 2, 0.10)  # B min9
    for at, f0 in [(0.6, 880.0), (4.3, 987.8), (7.55, 1108.7), (11.55, 1174.7), (15.25, 1318.5),
                   (19.5, 880.0), (24.7, 1108.7), (26.7, 1318.5)]:
        bell(at, f0, 0.07)
    out *= np.clip((DURATION - t) / 1.5, 0, 1) * np.clip(t / 0.3, 0, 1)
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
        for ts in [2.6, 6.2, 9.6, 13.4, 17.4, 23.8, 29.0]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"amt2-{ts:04.1f}s.png"))
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
    Image.fromarray(frame_at(2.6, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
