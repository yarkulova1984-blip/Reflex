"""ADVANCED MASSAGE THERAPY (2020 Corydon Ave) — Available Appointments — Monday, November 2 & Friday, November 6, 2026
("Dusty Rose"). Zarina, RCRT. 30 s Reel + 9:16 story still.

Owner's photo: two dusty-rose roses on a soft mauve background. Living background: slow breathing of the petals (masked
local scale), drifting warm light across the petals, soft foreground bokeh, camera push-in / tilt from the upper rose to the
lower rose / gentle pull-back; time reveals push toward the foreground.
Palette: dusty rose + mauve + ivory + champagne gold on deep plum. Type: Jost (clean geometric sans, light + medium) +
Great Vibes (script accent, sparingly) — new pairing.
Music (§46, new): see synth_audio().

  python3 production/nov2_6_amt_roses.py stills t [t ...]
  python3 production/nov2_6_amt_roses.py video
  python3 production/nov2_6_amt_roses.py story
"""
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")
LOGO = os.path.join(ROOT, "brand", "locations", "advanced-massage-therapy-logo.png")
PHOTO = os.path.join(ROOT, "brand", "photos", "amt-nov2-6", "roses.jpg")
OUT = os.path.join(ROOT, "content", "videos")
NAME = "2026-11-02-06-amt-available-appointments"
W, H, FPS, T_END = 1080, 1920, 30, 30.0


def hx(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255


IVORY, GOLD_HI, PLUM, ROSE = hx("#F6EFE8"), hx("#E9D3A0"), hx("#2A1720"), hx("#E7B7B0")
DAYS = [("MONDAY", "November 2", [("3:00", "p.m."), ("5:30", "p.m."), ("6:45", "p.m.")], 7.4, 13.6),
        ("FRIDAY", "November 6", [("9:15", "a.m."), ("10:30", "a.m."), ("11:45", "a.m."), ("1:00", "p.m.")], 13.6, 20.6)]
SERVICES = ["Spanish Massage", "Hand & Foot Reflexology", "Facial Reflexology — Bergman Method", "Reflexology Lymph Drainage (RLD)"]
T_SERV, T_EC = 20.4, 25.0


def clamp(x):
    return min(1.0, max(0.0, x))


def ramp(t, a, b):
    return clamp((t - a) / (b - a))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def jost(s, w=400):
    f = ImageFont.truetype(os.path.join(FONTS, "Jost[wght].ttf"), s)
    f.set_variation_by_axes([w])
    return f


def vibes(s):
    return ImageFont.truetype(os.path.join(FONTS, "GreatVibes-Regular.ttf"), s)


_cache = {}


def text(txt, fnt, fill, tracking=0, key=None):
    """RGBA float text image; fill 'gold' = metallic champagne gradient."""
    k = key or (txt, id(fnt), str(fill), tracking)
    if k in _cache:
        return _cache[k]
    asc, desc = fnt.getmetrics()
    ws = [fnt.getlength(c) for c in txt]
    w, h = int(sum(ws) + tracking * max(0, len(txt) - 1)) + 16, asc + desc + 16
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    x = 8
    for c, cw in zip(txt, ws):
        d.text((x, 8), c, font=fnt, fill=255)
        x += cw + tracking
    a = np.asarray(m, np.float32) / 255
    if isinstance(fill, str):
        yy = np.linspace(0, 1, h)
        stops = [hx("#FBF1D6"), hx("#E8CE96"), hx("#C9A765"), hx("#9C7A42")]
        g = np.stack([np.interp(yy, [0, .4, .62, 1], [s[i] for s in stops]) for i in range(3)], -1)
        rgb = np.broadcast_to(g[:, None, :], (h, w, 3))
    else:
        rgb = np.broadcast_to(np.asarray(fill, np.float32), (h, w, 3))
    out = np.dstack([rgb, a]).astype(np.float32)
    _cache[k] = out
    return out


class Canvas:
    def __init__(self, a):
        self.a = a

    def put(self, img, x, y, alpha=1.0, anchor="ct", blur=0.0, scale=1.0, reveal=None, sweep=None, shadow=0.0):
        if alpha <= 0.003:
            return
        if shadow > 0:
            sh = img.copy()
            sh[..., :3] = 0.05
            self.put(sh, x + 2, y + 3, alpha * shadow * 0.8, anchor, blur=max(blur, 8.0), scale=scale, reveal=reveal)
        im = img
        if scale != 1.0 or blur > 0.3:
            pil = Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8), "RGBA")
            if scale != 1.0:
                pil = pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))), Image.BICUBIC)
            if blur > 0.3:
                pad = int(blur * 3)
                big = Image.new("RGBA", (pil.width + 2 * pad, pil.height + 2 * pad), (0, 0, 0, 0))
                big.paste(pil, (pad, pad))
                pil = big.filter(ImageFilter.GaussianBlur(blur))
                y -= pad if anchor[1] == "t" else 0
            im = np.asarray(pil, np.float32) / 255
        hh, ww = im.shape[:2]
        x = x - ww / 2 if anchor[0] == "c" else (x - ww if anchor[0] == "r" else x)
        y = y - hh / 2 if anchor[1] == "m" else y
        x, y = int(round(x)), int(round(y))
        al = im[..., 3] * alpha
        if reveal is not None:
            axis, fr = reveal
            if axis == "x":
                al = al * np.clip((fr * (ww + 40) - 20 - np.arange(ww)[None, :]) / 20, 0, 1)
            else:
                al = al * np.clip((fr * (hh + 30) - 15 - np.arange(hh)[:, None]) / 15, 0, 1)
        rgb = im[..., :3]
        if sweep is not None:
            pos = sweep * (ww + hh) - hh
            band = np.exp(-(((np.arange(ww)[None, :] + np.arange(hh)[:, None] * 0.6) - pos) / 40.0) ** 2)
            rgb = np.clip(rgb + band[..., None] * 0.35, 0, 1)
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + ww), min(H, y + hh)
        if x1 <= x0 or y1 <= y0:
            return
        sl = (slice(y0 - y, y1 - y), slice(x0 - x, x1 - x))
        a = al[sl][..., None]
        self.a[y0:y1, x0:x1] = self.a[y0:y1, x0:x1] * (1 - a) + rgb[sl] * a

    def line(self, x0, x1, y, color, alpha, width=2, frac=1.0):
        if alpha <= 0.003 or frac <= 0:
            return
        x1 = x0 + (x1 - x0) * frac
        self.a[int(y):int(y) + width, int(x0):int(x1)] = (self.a[int(y):int(y) + width, int(x0):int(x1)] * (1 - alpha) + color * alpha)

    def dot(self, cx, cy, r, color, alpha):
        R = int(r * 3 + 4)
        x0, y0, x1, y1 = max(0, int(cx) - R), max(0, int(cy) - R), min(W, int(cx) + R), min(H, int(cy) + R)
        if x1 <= x0 or y1 <= y0:
            return
        ys, xs = np.mgrid[y0:y1, x0:x1]
        g = np.exp(-((xs - cx) ** 2 + (ys - cy) ** 2) / (2 * r * r))[..., None] * alpha
        self.a[y0:y1, x0:x1] = np.clip(self.a[y0:y1, x0:x1] + g * color, 0, 1)


class Reel:
    def __init__(self):
        self.im = Image.open(PHOTO).convert("RGB")
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        r = np.hypot((xx - W / 2) / W, (yy - H / 2) / H)
        self.vig = np.clip(1.08 - 0.7 * r ** 1.8, 0.45, 1)[..., None]
        # deep plum shade behind the centred text column (light only; the roses stay visible at the edges)
        self.col = np.clip(1 - 0.58 * np.exp(-((xx - 540) / 470) ** 4 - ((yy - 900) / 560) ** 4), 0.3, 1)[..., None]
        logo = Image.open(LOGO).convert("RGBA")
        logo = logo.crop(logo.getbbox())
        self.logo_big = np.asarray(logo.resize((640, int(logo.height * 640 / logo.width)), Image.LANCZOS), np.float32) / 255
        self.logo_sm = np.asarray(logo.resize((520, int(logo.height * 520 / logo.width)), Image.LANCZOS), np.float32) / 255
        rng = np.random.default_rng(1102)
        self.bokeh = np.c_[rng.uniform(0, W, 22), rng.uniform(0, H, 22), rng.uniform(18, 46, 22), rng.uniform(0, 6.3, 22)]
        self.grain = [rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(5)]
        self.reveals = [d[3] + 0.8 + i * 0.75 for d in DAYS for i in range(len(d[2]))]
        self.f = dict(tag=jost(30, 500), hook=jost(132, 300), hook_b=jost(150, 600), script=vibes(120), script_s=vibes(86),
                      day=jost(108, 500), date=vibes(104), time=jost(118, 400), ampm=jost(40, 500), serv=jost(46, 400),
                      addr=jost(56, 500), city=jost(38, 400), dm=jost(118, 600))
        # camera keys (source px: centre x, centre y, crop height)
        self.keys = [(0.0, (368, 640, 1308)), (7.0, (368, 560, 1120)), (13.6, (380, 860, 1080)), (20.4, (380, 760, 1220)),
                     (25.0, (368, 654, 1308)), (30.0, (368, 654, 1240))]

    def cam(self, t):
        ks = self.keys
        for (ta, a), (tb, b) in zip(ks[:-1], ks[1:]):
            if t <= tb:
                u = ease((t - ta) / (tb - ta))
                return [p + (q - p) * u for p, q in zip(a, b)]
        return ks[-1][1]

    def frame(self, t):
        cx, cy, h = self.cam(t)
        h /= 1.0 + sum(0.02 * ease((t - tr) / 0.9) * (1 - ramp(t, T_SERV, T_SERV + 1.0)) for tr in self.reveals)
        sw, sh = self.im.size
        h = min(h, sh, sw * H / W)
        w = h * W / H
        cx, cy = float(np.clip(cx, w / 2, sw - w / 2)), float(np.clip(cy, h / 2, sh - h / 2))
        crop = self.im.transform((W, H), Image.EXTENT, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), Image.BICUBIC)
        img = np.asarray(crop, np.float32) / 255
        # drifting warm light across the petals
        sweep = np.exp(-(((self.xx * 0.75 + self.yy * 0.5) - (-500 + 210 * (t % 13))) / 360) ** 2)[..., None]
        img = img * (0.94 + 0.10 * sweep) + sweep * np.array([1.0, 0.86, 0.7]) * 0.05
        # legibility: deep plum veil, stronger behind the text column, lighter on the end card's blur
        ec = ramp(t, T_EC - 0.4, T_EC + 0.3)
        if ec > 0:
            blur = np.asarray(crop.filter(ImageFilter.GaussianBlur(28)), np.float32) / 255
            img = img * (1 - ec) + blur * ec
        veil = 0.42 + 0.18 * ec
        img = img * (1 - veil) + PLUM * veil * 0.55 + img * veil * 0.45
        k = 1.0 if t < T_EC else 1 - ramp(t, T_EC, T_EC + 0.5) * 0.4
        img = img * (1 - k + k * self.col) + PLUM * (1 - self.col) * k * 0.6
        cv = Canvas(np.clip(img * self.vig, 0, 1).astype(np.float32))
        for x, y, r, ph in self.bokeh:  # soft foreground bokeh drifting up
            yy = (y - t * (10 + 8 * np.sin(ph))) % (H + 100) - 50
            cv.dot(x + 25 * np.sin(t * 0.35 + ph), yy, r, ROSE * 0.6 + GOLD_HI * 0.4, 0.05 + 0.04 * np.sin(t * 1.3 + ph))
        self.overlays(cv, t)
        out = cv.a + np.repeat(np.repeat(self.grain[int(t * FPS) % 5], 2, 0), 2, 1)[..., None] * 0.01
        return (np.clip(out * (1 - ramp(t, T_END - 0.5, T_END)), 0, 1) * 255).astype(np.uint8)

    def overlays(self, cv, t):
        f = self.f
        # HOOK — frame 0 is the cover; letter-spaced reveal of "SEVEN"
        if t < 3.4:
            a = 1 - ramp(t, 3.0, 3.4)
            e = ease_out(t / 1.2) if t > 0.05 else 1.0
            cv.put(text("NEXT WEEK", f["tag"], GOLD_HI, tracking=10), 540, 560, a, shadow=1.0)
            cv.put(text("SEVEN", f["hook_b"], IVORY, tracking=6 + 18 * (1 - e)), 540, 620, a, shadow=1.0)
            cv.put(text("moments for you", f["script"], "gold", key="mom"), 540, 790, a, shadow=1.0, sweep=ramp(t, 0.4, 1.8) if t > 0.05 else None)
            cv.put(text("MONDAY  &  FRIDAY  ·  ZARINA, RCRT", f["tag"], IVORY, tracking=5), 540, 960, a, shadow=1.0)
        # LOGO + therapist
        if 3.1 <= t < 7.6:
            a = ramp(t, 3.2, 3.7) * (1 - ramp(t, 7.1, 7.6))
            cv.put(self.logo_big, 540, 600, a, blur=10 * (1 - ease_out((t - 3.2) / 0.8)))
            k = ramp(t, 4.4, 4.8)
            cv.put(text("Available Appointments", f["script_s"], "gold", key="aa"), 540, 1000, a * k, shadow=1.0, reveal=("x", ramp(t, 4.4, 5.4)))
            cv.put(text("WITH ZARINA, RCRT", f["tag"], IVORY, tracking=8), 540, 1130, a * ramp(t, 5.2, 5.6), shadow=1.0)
        # DAYS — hero time reveals (push toward the foreground), full list stays readable
        for day, date, times, t0, t1 in DAYS:
            if t0 - 0.1 <= t < t1:
                a = ramp(t, t0, t0 + 0.35) * (1 - ramp(t, t1 - 0.4, t1))
                cv.put(text(day, f["day"], IVORY, tracking=12), 540, 500, a, shadow=1.0, reveal=("y", ramp(t, t0, t0 + 0.5)))
                cv.put(text(date, f["date"], "gold", key=("d", date)), 540, 640, a * ramp(t, t0 + 0.25, t0 + 0.6), shadow=1.0)
                for i, (tm, ap) in enumerate(times):
                    tr = t0 + 0.8 + i * 0.75
                    k = ramp(t, tr, tr + 0.35)
                    ti, ai = text(tm, f["time"], "gold", key=("t", tm)), text(ap, f["ampm"], IVORY)
                    tw = ti.shape[1] + 14 + ai.shape[1]
                    y = 820 + i * 140
                    x = 540 - tw / 2
                    cv.put(ti, x, y, a * k, "lt", shadow=1.0, scale=1.12 - 0.12 * ease_out((t - tr) / 0.6), blur=7 * (1 - ease_out((t - tr) / 0.5)))
                    cv.put(ai, x + ti.shape[1] + 14, y + ti.shape[0] - ai.shape[0] - 26, a * ramp(t, tr + 0.25, tr + 0.55), "lt", shadow=1.0)
        # SERVICES
        if T_SERV <= t < T_EC + 0.1:
            a = ramp(t, T_SERV + 0.1, T_SERV + 0.4) * (1 - ramp(t, T_EC - 0.35, T_EC + 0.05))
            cv.put(text("Services", f["script"], "gold", key="sv"), 540, 470, a, shadow=1.0)
            for i, s in enumerate(SERVICES):
                ts = T_SERV + 0.6 + i * 0.45
                cv.put(text(s, f["serv"], IVORY), 540 + 40 * (1 - ease_out((t - ts) / 0.6)), 680 + i * 100, a * ramp(t, ts, ts + 0.4), shadow=1.0)
            cv.line(540 - 160, 540 + 160, 1110, GOLD_HI, a * 0.9, 2, frac=ramp(t, T_SERV + 2.2, T_SERV + 3.0))
        # END CARD
        if t >= T_EC - 0.1:
            a = ramp(t, T_EC + 0.1, T_EC + 0.5)
            cv.put(self.logo_sm, 540, 380, a, scale=0.96 + 0.04 * ease_out((t - T_EC) / 0.8))
            k = ramp(t, T_EC + 0.6, T_EC + 1.0)
            cv.put(text("2020 Corydon Ave", f["addr"], IVORY), 540, 780, a * k, shadow=1.0)
            cv.put(text("Winnipeg, Manitoba", f["city"], IVORY), 540, 860, a * k, shadow=1.0)
            cv.put(text("ZARINA, RCRT", f["tag"], GOLD_HI, tracking=8), 540, 935, a * k, shadow=1.0)
            k2 = ramp(t, T_EC + 1.2, T_EC + 1.6)
            cv.line(540 - 220, 540 + 220, 1015, GOLD_HI, a * k2, 2, frac=ramp(t, T_EC + 1.2, T_EC + 1.9))
            cv.put(text("DM TO BOOK", f["dm"], "gold", key="dm"), 540, 1060, a * k2, shadow=1.0,
                   scale=0.92 + 0.08 * ease_out((t - T_EC - 1.2) / 0.6), sweep=ramp(t, T_EC + 1.9, T_EC + 3.1))


def synth_audio(path, sr=48000):
    """§46 new direction: B major (Bmaj7 · G#m9 · Emaj9 · F#sus4→F#) · 88 BPM · warm Wurlitzer-like keys + soft cello-like
    bass + light marimba counter-melody · soft cajón-like thump on 1 and brushed off-beats · gentle wind-chime texture ·
    harp-like upward glints on each time reveal."""
    rng = np.random.default_rng(1106)
    N = int(T_END * sr)
    b = np.zeros((N, 2))

    def add(sig, t0, g, pan=0.0):
        i = int(t0 * sr)
        if i >= N:
            return
        sig = sig[:N - i]
        b[i:i + len(sig), 0] += sig * g * np.sqrt(0.5 * (1 - pan))
        b[i:i + len(sig), 1] += sig * g * np.sqrt(0.5 * (1 + pan))

    def tt(d):
        return np.arange(int(d * sr)) / sr

    def m2f(m):
        return 440 * 2 ** ((m - 69) / 12)

    def wurli(f, d):
        x = tt(d)
        mod = np.sin(2 * np.pi * f * x) * (1.2 * np.exp(-x * 5) + 0.2)
        return np.sin(2 * np.pi * f * x + mod) * np.exp(-x * 1.3) * (1 + 0.15 * np.sin(2 * np.pi * 5 * x)) * np.minimum(1, x / 0.005)

    beat = 60 / 88
    prog = [[47, 51, 54, 58, 61], [44, 47, 51, 54, 58], [40, 44, 47, 51, 54], [42, 47, 49, 54, 56]]
    counter = [78, 75, 73, 71, 73, 75, 78, 80]
    t, k = 0.0, 0
    while t < T_END - 1.0:
        ch = prog[k % 4]
        x = tt(4 * beat)
        add(np.sin(2 * np.pi * m2f(ch[0] - 12) * x) * np.exp(-x * 0.8) * np.minimum(1, x / 0.03), t, 0.17)
        for j in (0, 1.5, 2.5):
            for n in ch[1:]:
                add(wurli(m2f(n), 1.6), t + j * beat, 0.035, pan=(n % 5 - 2) * 0.15)
        if k >= 1:
            for j in range(4):
                x = tt(0.9)
                f = m2f(counter[(k * 4 + j) % 8])
                add((np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 4 * x) * np.exp(-x * 30)) * np.exp(-x * 7), t + j * beat + beat / 2, 0.05, pan=0.3)
        t += 4 * beat
        k += 1
    thump = np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-tt(0.25) * 25)) / sr) * np.exp(-tt(0.25) * 14)
    brush = rng.normal(0, 1, int(0.15 * sr)) * np.exp(-tt(0.15) * 25)
    brush = brush - np.convolve(brush, np.ones(8) / 8, "same")
    t, i = 3.0, 0
    while t < T_END - 2.0:
        if i % 4 == 0:
            add(thump, t, 0.16)
        if i % 2 == 1:
            add(brush, t, 0.04, pan=0.2)
        t += beat
        i += 1
    for _ in range(26):  # wind chimes
        f = m2f(int(rng.choice([83, 85, 87, 90, 92, 95])))
        x = tt(2.5)
        add(np.sin(2 * np.pi * f * x) * np.exp(-x * 2.2), rng.uniform(0.5, T_END - 3), 0.012, pan=rng.uniform(-0.8, 0.8))
    reveals = [d[3] + 0.8 + i * 0.75 for d in DAYS for i in range(len(d[2]))]
    for tr in reveals + [3.2, T_EC + 0.1]:
        for j, n in enumerate([71, 75, 78, 83]):
            x = tt(1.4)
            add(np.sin(2 * np.pi * m2f(n) * x) * np.exp(-x * 4), tr - 0.12 + j * 0.04, 0.03, pan=-0.4 + 0.25 * j)
    # reverb
    n = int(2.4 * sr)
    nfft = 1 << (N + n - 2).bit_length()
    for c in range(2):
        ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (0.32 * sr))
        y = np.fft.irfft(np.fft.rfft(b[:, c], nfft) * np.fft.rfft(ir, nfft), nfft)[:N]
        b[:, c] = b[:, c] * 0.74 + y / (np.abs(y).max() + 1e-9) * np.abs(b[:, c]).max() * 0.26
    x = np.arange(N) / sr
    b *= np.clip(np.minimum(x / 0.03, (T_END - x) / 1.5), 0, 1)[:, None]
    b *= 0.9 / np.abs(b).max()
    raw = path.replace(".wav", "_raw.wav")
    with wave.open(raw, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((b * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(sr), path], check=True)
    os.remove(raw)


def main():
    mode = sys.argv[1]
    R = Reel()
    if mode == "stills":
        d = os.path.join(OUT, "_stills")
        os.makedirs(d, exist_ok=True)
        for t in sys.argv[2:]:
            Image.fromarray(R.frame(float(t))).save(os.path.join(d, f"{NAME}_{float(t):05.2f}.png"))
        return
    if mode == "story":  # static 9:16 still: summary of both days
        Image.fromarray(R.frame(T_SERV - 1.0)).save(os.path.join(OUT, f"{NAME}-cover.jpg"), quality=92)
        return
    vid = os.path.join(OUT, f"{NAME}_video.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
    for i in range(int(round(T_END * FPS))):
        p.stdin.write(R.frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    wav = os.path.join(OUT, f"{NAME}.wav")
    synth_audio(wav)
    out = os.path.join(OUT, f"{NAME}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(vid)
    os.remove(wav)
    Image.fromarray(R.frame(0.0)).save(os.path.join(OUT, f"{NAME}-cover.jpg"), quality=92)
    print(out)


if __name__ == "__main__":
    main()
