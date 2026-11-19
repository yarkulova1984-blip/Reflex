"""THE PURE ESCAPE — Available Appointments, week of Nov 24, 2026 (two Reels, owner's request):
  "midweek": Tuesday 24 · Wednesday 25 · Thursday 26 together   (background: rose + eucalyptus bouquet)
  "sat":     Saturday 28 separately                               (background: cream blossoms)
Services (owner's list): Ultimate Escape Package · Facial Reflexology + Hand Reflexology with Chanel
skincare · Foot Reflexology · Hand Reflexology · Spanish Massage. Zarina, RCRT. DM to book.

Living background: flowers breathe/sway (masked warp), champagne light sweep over the bright petals,
drifting pollen, slow camera moves; text inside the safe area (§49); blur-in / blur-out.
  midweek — Bellefair + Karla + Birthstone; music: D major 92 BPM, chorus-guitar arpeggios, cello,
            soft shaker, birdsong texture.
  sat     — Abhaya Libre + Nunito Sans + Allison; music: B♭ major 100 BPM bossa, vibraphone, upright
            bass, brushed shaker, morning room tone.

  python3 production/nov24_pe_week.py {midweek|sat} stills [t ...] | video
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
from doctor_story_reel import put_shine, drop, slide  # noqa: E402
from oct15_pe_thu_sat import ks  # noqa: E402
from oct16_amt_thanksgiving import Text, bilinear, ease_in_out, ease_out, letters, line, prog, put, put_c, put_x, rise, sharp_in, wash, wipe  # noqa: E402

ROOT = base.ROOT
FONTS = base.FONTS
PH = os.path.join(ROOT, "brand", "photos", "pe-nov24")
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
OUT_DIR = base.OUT_DIR
W, H, FPS = 1080, 1920, 30
IVORY = (252, 247, 238)
NIGHT = (22, 16, 12)
GOLD_LINE = (230, 200, 146)
base.GOLDS["gilt2"] = ((255, 242, 212), (232, 198, 140), (170, 130, 72))

CLINIC, ADDRESS, THERAPIST = "The Pure Escape", "698 Corydon Ave, Winnipeg", "Zarina, RCRT"
SERVICES = [("Ultimate Escape Package", ""), ("Facial + Hand Reflexology", "WITH CHANEL SKINCARE"),
            ("Foot Reflexology", ""), ("Hand Reflexology", ""), ("Spanish Massage", "")]

VARIANTS = {
    "midweek": {
        "name": "2026-11-24-pe-tue-wed-thu-available-appointments", "bg": "rose-eucalyptus.jpg", "dur": 34.0,
        "days": [("TUESDAY", "November 24", [("11:00", "a.m."), ("3:15", "p.m.")]),   # owner wrote "3:15 a.m." → confirm p.m.
                 ("WEDNESDAY", "November 25", [("11:00", "a.m."), ("12:15", "p.m."), ("1:30", "p.m."), ("2:45", "p.m."), ("4:00", "p.m.")]),
                 ("THURSDAY", "November 26", [("3:00", "p.m."), ("4:15", "p.m."), ("5:30", "p.m.")])],
        "hook": ("10", "openings", "TUESDAY  ·  WEDNESDAY  ·  THURSDAY"),
        "fonts": ("Bellefair-Regular.ttf", "Karla[wght].ttf", "Birthstone-Regular.ttf"),
        "cam": [(0.0, 0.50, 0.50, 1.00), (8.0, 0.44, 0.46, 1.07), (16.0, 0.56, 0.54, 1.10), (24.0, 0.48, 0.50, 1.05), (34.0, 0.50, 0.50, 1.00)],
    },
    "sat": {
        "name": "2026-11-28-pe-saturday-available-appointments", "bg": "cream-blossoms.jpg", "dur": 24.0,
        "days": [("SATURDAY", "November 28", [("9:00", "a.m."), ("11:30", "a.m.")])],
        "hook": ("Saturday", "is for you", "TWO MORNING OPENINGS"),
        "fonts": ("AbhayaLibre-SemiBold.ttf", "NunitoSans[YTLC,opsz,wdth,wght].ttf", "Allison-Regular.ttf"),
        "cam": [(0.0, 0.50, 0.46, 1.08), (8.0, 0.52, 0.50, 1.00), (16.0, 0.46, 0.56, 1.06), (24.0, 0.50, 0.52, 1.00)],
    },
}
V = VARIANTS[sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in VARIANTS else "sat"]
NAME, DURATION, DAYS = V["name"], V["dur"], V["days"]


def serif(size):
    return ImageFont.truetype(os.path.join(FONTS, V["fonts"][0]), size)


def sans(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, V["fonts"][1]), size)
    ax = f.get_variation_axes()
    f.set_variation_by_axes([wght if a["name"] == b"Weight" else a["default"] for a in ax])
    return f


def scr(size):
    return ImageFont.truetype(os.path.join(FONTS, V["fonts"][2]), size)


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT)


def build_bg():
    im = Image.open(os.path.join(PH, V["bg"])).convert("RGB")
    k = max(W / im.width, H / im.height) * 1.16
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 50, 2))
    arr = np.asarray(big, np.float32) * 0.74
    h, w = arr.shape[:2]
    lum = np.asarray(big.convert("L"), np.float32)
    bright = np.clip((lum - 170) / 60, 0, 1)
    bright = np.asarray(Image.fromarray((bright * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32) / 255
    rng = np.random.default_rng(3)
    small = rng.normal(0, 1, (h // 160 + 2, w // 160 + 2)).astype(np.float32)
    phase = np.asarray(Image.fromarray(small, "F").resize((w, h), Image.BICUBIC), np.float32)
    return {"arr": arr, "w": w, "h": h, "bright": bright, "phase": phase}


def cam(t):
    C = V["cam"]
    for (t0, *a), (t1, *b) in zip(C, C[1:]):
        if t0 <= t <= t1:
            e = ease_in_out((t - t0) / (t1 - t0))
            return tuple(x + (y - x) * e for x, y in zip(a, b))
    return C[-1][1:]


def background(A, t, soften=0.0):
    B = A["B"]
    u, v, z = cam(t)
    s = max(W / B["w"], H / B["h"])
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * B["w"], cw / 2), B["w"] - cw / 2)
    cy = min(max(v * B["h"], ch / 2), B["h"] - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    ix = np.clip(gx.astype(np.int32), 0, B["w"] - 1)
    iy = np.clip(gy.astype(np.int32), 0, B["h"] - 1)
    ph = B["phase"][iy, ix]
    gx = gx + 3.2 * np.sin(0.8 * t + ph * 2.0) + 1.4 * np.sin(1.7 * t + gy * 0.004)   # petals breathing in a soft breeze
    gy = gy + 2.4 * np.sin(0.7 * t + ph * 2.0 + 1.0)
    img = bilinear(B["arr"], gx, gy)
    br = B["bright"][iy, ix]
    sx = ((t * 0.09) % 1.4 - 0.2) * W
    band = np.exp(-(((A["xx"] - sx) - (A["yy"] - H / 2) * 0.4) / 200.0) ** 2)
    img = img + (br * band)[..., None] * np.array([70, 58, 36], np.float32)
    if soften > 0.01:
        img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8 * soften)), np.float32)
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, spd, p, a) in A["dust"]:
        put(f, A["mote"], x + 18 * math.sin(t * 0.4 + p), (y - spd * t) % H, a * (0.4 + 0.6 * max(0.0, math.sin(t * 1.3 + p))))
    return f


def build():
    A = {"B": build_bg()}
    rng = np.random.default_rng(24)
    A["grain"] = [rng.normal(0, 2.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["xx"], A["yy"] = xx, yy
    A["vig"] = (1 - 0.3 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    m = Image.new("L", (20, 20), 0)
    ImageDraw.Draw(m).ellipse((8, 8, 12, 12), fill=230)
    mote = Image.new("RGBA", (20, 20), (255, 236, 196, 0))
    mote.putalpha(m.filter(ImageFilter.GaussianBlur(2)))
    A["mote"], A["dust"] = mote, [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(5, 14), rng.uniform(0, 6.28), rng.uniform(0.3, 0.6)) for _ in range(30)]
    logo = Image.open(LOGO).convert("RGBA")       # official file, untouched; soft edgeless light glow (no plate, §38)
    for key, wdt in (("logo", 420), ("logo_s", 300)):
        lg = logo.resize((wdt, round(logo.height * wdt / logo.width)), Image.LANCZOS)
        pad = 210
        gl = Image.new("L", (lg.width + 2 * pad, lg.height + 2 * pad), 0)
        ImageDraw.Draw(gl).ellipse((pad - 40, pad - 30, gl.width - pad + 40, gl.height - pad + 30), fill=220)
        glow = Image.new("RGBA", gl.size, (252, 247, 238, 0))
        glow.putalpha(gl.filter(ImageFilter.GaussianBlur(60)))
        A[key], A[key + "_g"] = lg, glow
    h1, h2, h3 = V["hook"]
    A["h1"] = T(h1, serif(300 if len(h1) < 4 else 180), "gilt2")
    A["h2"] = T(h2, scr(170), IVORY)
    A["h3"] = base.fit(lambda s_: T(h3, sans(s_, 600), IVORY, tracking=10), 34, 900)
    A["clinic"] = T(CLINIC.upper(), sans(34, 600), IVORY, tracking=10)
    A["addr"] = T(ADDRESS, serif(64), "gilt2")
    A["day"] = [(T(d, sans(40, 700), IVORY, tracking=16), T(dt, serif(110), IVORY)) for d, dt, _ in DAYS]
    A["times"] = [[(T(tm, serif(220 if len(ts) < 4 else 170), "gilt2"), T(ap, sans(50 if len(ts) < 4 else 42, 500), IVORY, tracking=2)) for tm, ap in ts] for _, _, ts in DAYS]
    A["svc_h"] = T("treatments", scr(180), "gilt2")
    A["svc"] = [(T(n, serif(76), IVORY), T(sub, sans(26, 700), "gilt2", tracking=10) if sub else None) for n, sub in SERVICES]
    A["s_title"] = T("Available appointments", scr(130), "gilt2")
    A["s_day"] = [T(f"{d}, {dt.upper()}", sans(28, 700), IVORY, tracking=6) for d, dt, _ in DAYS]
    A["s_t"] = [[(T(tm, serif(80), "gilt2"), T(ap, sans(28, 500), IVORY)) for tm, ap in ts] for _, _, ts in DAYS]
    A["s_who"] = T(f"{THERAPIST}  ·  {ADDRESS}", sans(30, 600), IVORY, tracking=1)
    A["s_cta"] = T("DM TO BOOK", sans(52, 700), IVORY, tracking=18)
    return A


def plan():
    """Timeline: hook, location, one hero scene per day (each time revealed), services, summary."""
    P = {"hook": (0.0, 3.6), "loc": (3.4, 6.8)}
    t = 6.8
    P["days"] = []
    for _, _, ts in DAYS:
        n = len(ts)
        dur = 2.0 + 1.15 * n if len(DAYS) > 1 else 3.0 + 1.6 * n
        reveals = [t + 1.1 + j * (1.15 if len(DAYS) > 1 else 1.6) for j in range(n)]
        P["days"].append((t, t + dur, reveals))
        t += dur
    svc_d = 4.6
    P["svc"] = (t, t + svc_d)
    P["sum"] = t + svc_d
    return P


PL = plan()


def fade(t, s, e, fi=0.5, fo=0.45):
    return ease_out(prog(t, s, fi)) * (1 - ease_in_out(prog(t, e - fo, fo)))


def soft_band(f, y0, y1, a):
    """Dark gradient band with feathered top and bottom edges (no visible box)."""
    if a <= 0.01:
        return
    m = min(160, (y1 - y0) // 2 - 1)
    wash(f, y0 - m, y0 + m, NIGHT, 0.0, a)
    if y1 - m > y0 + m + 1:
        wash(f, y0 + m, y1 - m, NIGHT, a, a)
    wash(f, y1 - m, y1 + m, NIGHT, a, 0.0)


def put_logo(f, A, key, cx, top, a):
    lg, gl = A[key], A[key + "_g"]
    put(f, gl, cx - gl.width / 2, top + lg.height / 2 - gl.height / 2, a * 0.92)
    put(f, lg, cx - lg.width / 2, top, a)


def frame_at(t, A):
    soften = sum(math.exp(-((t - r) / 0.3) ** 2) for _, _, rs in PL["days"] for r in rs) * 0.6
    f = background(A, t, soften)
    cx = W / 2
    s, e = PL["hook"]
    if t < e:
        a = fade(t, s, e, 0.3)
        soft_band(f, 650, 1250, 0.35 * a)
        sharp_in(f, A["h1"], cx - A["h1"].adv / 2, 880, prog(t, 0.5, 0.9), a, scale_from=1.06, blur=14)
        if t > 1.5:
            put_shine(f, A["h1"], cx - A["h1"].adv / 2, 880, a, prog(t, 1.5, 1.4))
        wipe(f, A["h2"], cx - A["h2"].adv / 2, 1050, prog(t, 1.0, 0.9), a)
        letters(f, A["h3"], cx - A["h3"].adv / 2, 1170, 1.6, t, a, step=0.02)
    s, e = PL["loc"]
    if s <= t < e:
        a = fade(t, s, e)
        soft_band(f, 940, 1220, 0.4 * a)
        p = ease_out(prog(t, s + 0.1, 0.7))
        put_logo(f, A, "logo", cx, 640 + 14 * (1 - p), a * p)
        letters(f, A["clinic"], cx - A["clinic"].adv / 2, 1020, s + 0.6, t, a, step=0.02)
        rise(f, A["addr"], cx - A["addr"].adv / 2, 1150, prog(t, s + 1.2, 0.7), a)
    for k, (s, e, reveals) in enumerate(PL["days"]):
        if s <= t < e:
            a = fade(t, s, e)
            soft_band(f, 300, 1500, 0.40 * a)
            d, dt = A["day"][k]
            letters(f, d, cx - d.adv / 2, 380, s + 0.1, t, a, step=0.04)
            drop(f, dt, cx - dt.adv / 2, 500, prog(t, s + 0.3, 0.7), a)
            line(f, cx, 545, 300 * ease_in_out(prog(t, s + 0.7, 0.6)), GOLD_LINE, a)
            ts = A["times"][k]
            n = len(ts)
            gap = 210 if n <= 3 else 175
            y0 = (1000 - (n - 1) * gap / 2) + 80
            for j, (tm, ap) in enumerate(ts):
                tr = reveals[j]
                tot = tm.adv + 16 + ap.adv
                x = cx - tot / 2
                by = y0 + j * gap
                if j % 2 == 0:
                    sharp_in(f, tm, x, by, prog(t, tr, 0.7), a, scale_from=1.06, blur=12)
                else:
                    slide(f, tm, x, by, prog(t, tr, 0.6), a, dx=-60)
                if t > tr + 0.7:
                    put_shine(f, tm, x, by, a, prog(t, tr + 0.7, 1.0))
                pp = ease_out(prog(t, tr + 0.3, 0.45))
                put_x(f, ap, x + tm.adv + 16, by, a * pp, dx=-18 * (1 - pp))
    s, e = PL["svc"]
    if s <= t < e:
        a = fade(t, s, e)
        soft_band(f, 400, 1350, 0.45 * a)
        wipe(f, A["svc_h"], cx - A["svc_h"].adv / 2, 520, prog(t, s + 0.1, 0.8), a)
        y = 700
        for j, (nm, sub) in enumerate(A["svc"]):
            ts_ = s + 0.5 + j * 0.4
            rise(f, nm, cx - nm.adv / 2, y, prog(t, ts_, 0.6), a)
            if sub is not None:
                letters(f, sub, cx - sub.adv / 2, y + 44, ts_ + 0.3, t, a, step=0.015)
                y += 140
            else:
                y += 112
    s = PL["sum"]
    if t >= s - 0.1:
        a = ease_out(prog(t, s, 0.6))
        soft_band(f, 250, 1600, 0.42 * a)
        put_logo(f, A, "logo_s", cx, 280, a)
        wipe(f, A["s_title"], cx - A["s_title"].adv / 2, 590, prog(t, s + 0.2, 0.9))
        y = 690
        rows = len(DAYS)
        rh = 190 if rows > 1 else 240
        for k in range(rows):
            dl = A["s_day"][k]
            letters(f, dl, cx - dl.adv / 2, y, s + 0.6 + k * 0.6, t, step=0.012)
            row = A["s_t"][k]
            gp = 38
            tot = sum(tm.adv + 8 + ap.adv for tm, ap in row) + gp * (len(row) - 1)
            sc = min(1.0, 900 / tot)
            x = cx - tot * sc / 2
            for j, (tm, ap) in enumerate(row):
                pp = ease_out(prog(t, s + 0.8 + k * 0.6 + j * 0.12, 0.5))
                ti = tm.img if sc == 1 else tm.img.resize((int(tm.w * sc), int(tm.h * sc)), Image.LANCZOS)
                ai = ap.img if sc == 1 else ap.img.resize((int(ap.w * sc), int(ap.h * sc)), Image.LANCZOS)
                put(f, ti, x - tm.pad * sc, y + 100 - tm.asc * sc + 10 * (1 - pp), pp)
                put(f, ai, x + (tm.adv + 8) * sc - ap.pad * sc, y + 100 - ap.asc * sc + 10 * (1 - pp), pp)
                x += (tm.adv + 8 + ap.adv + gp) * sc
            y += rh
        line(f, cx, y - 30, 420 * ease_in_out(prog(t, s + 2.0, 0.6)), GOLD_LINE)
        p = ease_out(prog(t, s + 2.3, 0.5))
        put_c(f, A["s_who"], y + 30, p, dy=10 * (1 - p))
        p = ease_out(prog(t, s + 2.7, 0.6))
        put_c(f, A["s_cta"], y + 140, p, dy=12 * (1 - p))
        line(f, cx, y + 165, 300 * ease_in_out(prog(t, s + 3.0, 0.6)), GOLD_LINE, p, thick=2)
    bi = 1 - ease_out(prog(t, 0.0, 1.0))
    bo = ease_in_out(prog(t, DURATION - 1.5, 1.5))
    b = max(bi, bo)
    if b > 0.01:
        f = f.filter(ImageFilter.GaussianBlur(24 * b))
        if bo > 0.01:
            f.alpha_composite(Image.new("RGBA", (W, H), (240, 228, 214, int(80 * bo))))
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
    rng = np.random.default_rng(92 if V is VARIANTS["midweek"] else 100)
    out = np.zeros(n)

    def add(at_, sig, gain=1.0):
        i = int(at_ * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        k = min(len(sig), n - i)
        out[i:i + k] += gain * sig[:k]

    def shaker(L=0.08):
        L = int(L * sr)
        x = rng.normal(0, 1, L)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(L, 1 / sr)
        X *= np.clip((fr - 4500) / 3000, 0, 1)
        y = np.fft.irfft(X, L)
        tt = np.arange(L) / sr
        return y / (np.abs(y).max() + 1e-9) * np.exp(-tt * 40) * np.clip(tt / 0.008, 0, 1)
    if V is VARIANTS["midweek"]:
        BPM = 92
        BEAT = 60 / BPM
        BAR = 4 * BEAT
        CH = [(73.42, [293.66, 369.99, 440.0, 554.37]), (61.74, [246.94, 293.66, 369.99, 440.0]),
              (98.0, [293.66, 392.0, 493.88, 587.33]), (110.0, [277.18, 329.63, 440.0, 554.37])]   # Dmaj7 Bm7 Gmaj7 A6
        seed = 0
        for b in range(int(DURATION / BAR) + 1):
            root, voi = CH[b % 4]
            t0 = b * BAR
            for k, idx in enumerate([0, 1, 2, 3, 2, 1, 2, 3]):
                seed += 1
                g = ks(voi[idx], 1.6, sr, bright=0.5, seed=seed)
                add(t0 + k * BEAT / 2, g, 0.13)
                add(t0 + k * BEAT / 2 + 0.012, g, 0.05)              # chorus doubling
            L = int((BAR + 1.0) * sr)
            tt = np.arange(L) / sr
            ph = 2 * np.pi * root * 2 * np.cumsum(1 + 0.004 * np.sin(2 * np.pi * 5 * tt)) / sr
            env = np.clip(tt / 0.8, 0, 1) * np.clip((BAR + 1.0 - tt) / 0.9, 0, 1)
            add(t0 - 0.2, env * sum((0.5 / kk) * np.sin(kk * ph) for kk in range(1, 6)), 0.12)
            if t0 > 3.0:
                for k in range(8):
                    add(t0 + k * BEAT / 2, shaker(), 0.05 if k % 2 else 0.03)
        for _ in range(26):                                          # birdsong chirps
            at_ = rng.uniform(1, DURATION - 2)
            L = int(rng.uniform(0.08, 0.16) * sr)
            tt = np.arange(L) / sr
            f0 = rng.uniform(3000, 4600)
            fr = f0 * (1 + 0.25 * np.sin(2 * np.pi * rng.uniform(18, 30) * tt))
            add(at_, np.sin(2 * np.pi * np.cumsum(fr) / sr) * np.sin(np.pi * tt / tt[-1]) ** 2, 0.025)
    else:
        BPM = 100
        BEAT = 60 / BPM
        BAR = 4 * BEAT
        CH = [(58.27, [293.66, 349.23, 440.0, 523.25]), (98.0, [293.66, 349.23, 392.0, 466.16]),
              (65.41, [311.13, 392.0, 466.16, 587.33]), (87.31, [311.13, 349.23, 440.0, 523.25])]   # Bbmaj7 Gm7 Cm9 F9
        for b in range(int(DURATION / BAR) + 1):
            root, voi = CH[b % 4]
            t0 = b * BAR
            for k, pos in enumerate([0, 1.5, 2.5, 3.5]):            # bossa comping, vibraphone
                L = int(1.6 * sr)
                tt = np.arange(L) / sr
                env = np.exp(-tt * 2.2) * np.clip(tt / 0.003, 0, 1) * (1 + 0.25 * np.sin(2 * np.pi * 5.5 * tt))
                add(t0 + pos * BEAT, sum(np.sin(2 * np.pi * f * tt) + 0.2 * np.sin(2 * np.pi * f * 4 * tt) * np.exp(-tt * 8) for f in voi) * env, 0.04)
            for pos, mul in ((0, 1), (1.5, 1.5), (2, 1), (3.5, 1.5)):  # upright bass
                L = int(0.7 * sr)
                tt = np.arange(L) / sr
                add(t0 + pos * BEAT, np.sin(2 * np.pi * root * mul * tt) * np.exp(-tt * 4) * np.clip(tt / 0.01, 0, 1), 0.3)
            if t0 > 2.5:
                for k in range(8):
                    add(t0 + k * BEAT / 2, shaker(0.12), 0.06 if k % 2 else 0.035)
        x = rng.normal(0, 1, n)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(n, 1 / sr)
        X *= 1 / np.sqrt(np.maximum(fr, 50)) * np.exp(-fr / 4000)
        room = np.fft.irfft(X, n)
        out += room / np.abs(room).max() * 0.02
    for _, _, rs in PL["days"]:
        for tr in rs:
            L = int(1.8 * sr)
            tt = np.arange(L) / sr
            add(tr, np.exp(-tt * 3) * (np.sin(2 * np.pi * 1760 * tt) + 0.3 * np.sin(2 * np.pi * 1760 * 2.32 * tt)), 0.05)
    out = out / (np.abs(out).max() + 1e-9)
    st = np.stack([out, np.roll(out, int(0.011 * sr))], 1)
    st *= (np.clip((DURATION - t) / 2.0, 0, 1) * np.clip(t / 0.6, 0, 1))[:, None]
    st = st / np.max(np.abs(st)) * 10 ** (-1.5 / 20)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def main(mode):
    os.makedirs(os.path.join(OUT_DIR, "qc"), exist_ok=True)
    if mode == "stills":
        A = build()
        ts = [float(x) for x in sys.argv[3:]] or [2.6, 5.5] + [rs[-1] + 1.0 for _, _, rs in PL["days"]] + [PL["svc"][0] + 3.5, DURATION - 2.0]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(OUT_DIR, "qc", f"{NAME[:13]}-{s:05.2f}s.png"))
        print(ts)
        return
    tmp = os.path.join(OUT_DIR, f".{NAME}.render.mp4")
    wav = os.path.join(OUT_DIR, f".{NAME}.wav")
    synth_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "48000", "-c:v", "libx264", "-preset", "slow", "-crf", "22",
           "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4, initializer=_init) as pool:
        for buf in pool.imap(_render, range(int(DURATION * FPS)), chunksize=4):
            proc.stdin.write(buf)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    os.replace(tmp, os.path.join(OUT_DIR, f"{NAME}.mp4"))
    A = build()
    Image.fromarray(frame_at(2.6, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    Image.fromarray(frame_at(DURATION - 2.0, A)).save(os.path.join(OUT_DIR, f"{NAME}-story.jpg"), quality=93)
    print(NAME)


if __name__ == "__main__":
    main(sys.argv[2] if len(sys.argv) > 2 else "video")
