"""ADVANCED MASSAGE THERAPY — Available Appointments, Mon Nov 30 & Fri Dec 4, 2026 ("Midnight Satin").
Monday, November 30: 3:00 p.m.   Friday, December 4: 9:15 a.m. · 1:00 p.m.   (3 openings; weekdays verified)
Services (owner's wording): Reflexology Therapy — Foot & Hand & Facial · Spanish Massage.
Zarina, RCRT · 2020 Corydon Ave, Winnipeg · DM to book.

Background: owner's clip of black satin waves with gold glitter, played slow and ping-ponged so it never
jumps; camera push-ins on every time reveal; twinkling gold glints + a champagne light sweep (§45, §48).
Text: safe area x 60–960, y 250–1580 (§49); blur-in opening, blur-out ending.
Type (new): Italiana (display) + Urbanist (sans) + Imperial Script (accent). Black · gold · ivory · teal hint.
Music (§46, new): A minor → C, 112 BPM: FM bell plucks, airy shimmer pad, soft four-on-the-floor kick +
closed hats, risers into each reveal, low boom + sparkle on the times.

  python3 production/nov30_amt_week.py stills [t ...] | video
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
from oct16_amt_thanksgiving import Text, bilinear, ease_in_out, ease_out, letters, line, prog, put, put_c, rise, sharp_in, wash, wipe  # noqa: E402

ROOT = base.ROOT
FONTS = base.FONTS
CLIP = os.path.join(ROOT, "brand", "photos", "amt-nov30", "black-gold-satin.mp4")
LOGO = os.path.join(ROOT, "brand", "locations", "advanced-massage-therapy-logo.png")
FR = "/tmp/claude-0/-home-user-Reflex/f74b54ed-c929-5941-94f0-7201420216f3/scratchpad/nov30.rgb"
OUT_DIR = base.OUT_DIR
NAME = "2026-11-30-amt-available-appointments"
W, H, FPS = 1080, 1920, 30
DURATION = 24.0
IVORY = (250, 244, 232)
NIGHT = (4, 4, 6)
GOLD_LINE = (222, 188, 128)
base.GOLDS["satin"] = ((255, 236, 196), (222, 182, 112), (156, 112, 52))

# beats (s)
HOOK = (0.0, 3.6)
MON = (3.4, 8.4)
FRI = (8.2, 14.6)
SVC = (14.4, 18.6)
END = (18.4, DURATION)
T_MON = 5.2
T_FRI = (10.0, 11.9)


def ital(size):
    return ImageFont.truetype(os.path.join(FONTS, "Italiana-Regular.ttf"), size)


def urb(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "Urbanist[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def imp(size):
    return ImageFont.truetype(os.path.join(FONTS, "ImperialScript-Regular.ttf"), size)


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT)


class Satin:
    def __init__(self):
        w, h = 652, 1412
        if not os.path.exists(FR):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", CLIP, "-f", "rawvideo", "-pix_fmt", "rgb24", FR + ".part"], check=True)
            os.replace(FR + ".part", FR)
        n = os.path.getsize(FR) // (w * h * 3)
        self.f = np.memmap(FR, dtype=np.uint8, mode="r", shape=(n, h, w, 3))
        self.n, self.w, self.h = n, w, h

    def frame(self, t):
        # slow (0.5x) ping-pong so the satin keeps flowing without a jump cut
        L = (self.n - 1) / 24.0
        x = (t * 0.5) % (2 * L)
        x = x if x <= L else 2 * L - x
        k = x * 24.0
        i = min(int(k), self.n - 2)
        a = k - i
        return self.f[i].astype(np.float32) * (1 - a) + self.f[i + 1].astype(np.float32) * a


# camera keyframes (t, zoom, u, v): gentle push toward the foreground on every time reveal
KEYS = [(0.0, 1.06, 0.50, 0.50), (3.4, 1.10, 0.48, 0.47), (T_MON, 1.16, 0.50, 0.52), (8.2, 1.08, 0.53, 0.48),
        (T_FRI[0], 1.14, 0.50, 0.46), (T_FRI[1], 1.20, 0.49, 0.54), (14.4, 1.10, 0.46, 0.50), (18.4, 1.05, 0.50, 0.50),
        (DURATION, 1.09, 0.50, 0.49)]


def cam(t):
    for (t0, z0, u0, v0), (t1, z1, u1, v1) in zip(KEYS, KEYS[1:]):
        if t0 <= t <= t1:
            p = ease_in_out((t - t0) / (t1 - t0))
            return z0 + (z1 - z0) * p, u0 + (u1 - u0) * p, v0 + (v1 - v0) * p
    return KEYS[-1][1:]


def background(A, t):
    fr = A["clip"].frame(t)
    z, u, v = cam(t)
    h, w = fr.shape[:2]
    s = max(W / w, H / h)
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * w, cw / 2), w - cw / 2)
    cy = min(max(v * h, ch / 2), h - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    img = bilinear(fr, gx, gy)
    # champagne light sweep gliding across the satin every ~8 s (brightens only the glitter highlights)
    ph = (t % 8.0) / 8.0
    xx, yy = A["xx"], A["yy"]
    band = np.exp(-(((xx - yy * 0.45) - (-500 + 2200 * ph)) / 170.0) ** 2)
    lum = img.mean(-1, keepdims=True)
    img = img + band[..., None] * np.clip(lum - 60, 0, 255) / 195 * np.array([90, 70, 40], np.float32)
    sm = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W // 8, H // 8), Image.BILINEAR)
    soft = np.asarray(sm.filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR), np.float32) * 0.42
    k = A["pocket"] * ease_out(prog(t, 0.3, 1.2))
    img = img * (1 - k) + soft * k
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, ph0, sz) in A["glints"]:
        a = max(0.0, math.sin(t * 1.7 + ph0)) ** 6
        if a > 0.03:
            g = A["star"][sz]
            put(f, g, x - g.width / 2, y - g.height / 2, a)
    return f


def star(r):
    S = r * 4
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    d.line((S / 2, 0, S / 2, S), fill=200, width=2)
    d.line((0, S / 2, S, S / 2), fill=200, width=2)
    d.ellipse((S / 2 - r / 3, S / 2 - r / 3, S / 2 + r / 3, S / 2 + r / 3), fill=255)
    im = Image.new("RGBA", (S, S), (255, 226, 170, 0))
    im.putalpha(m.filter(ImageFilter.GaussianBlur(1.2)))
    return im


def build():
    A = {"clip": Satin()}
    rng = np.random.default_rng(1130)
    A["grain"] = [rng.normal(0, 1.8, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["xx"], A["yy"] = xx, yy
    A["vig"] = (1 - 0.30 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    A["star"] = {k: star(k) for k in (8, 12, 18)}
    A["pocket"] = (0.82 * np.exp(-((yy - 900) / 560) ** 4) * np.exp(-((xx - W / 2) / 620) ** 4))[..., None]
    A["glints"] = [(rng.uniform(40, W - 40), rng.uniform(60, H - 60), rng.uniform(0, 6.28), int(rng.choice([8, 12, 18]))) for _ in range(16)]
    logo = Image.open(LOGO).convert("RGBA")
    logo = logo.crop(logo.getchannel("A").getbbox())      # trim transparent margin only; logo itself untouched
    A["logo"] = logo.resize((440, round(logo.height * 440 / logo.width)), Image.LANCZOS)
    A["logo_s"] = logo.resize((340, round(logo.height * 340 / logo.width)), Image.LANCZOS)

    A["only"] = T("ONLY 3 OPENINGS", urb(64, 700), IVORY, tracking=14)
    A["yours"] = T("will one be yours?", imp(150), "satin")
    A["mon"] = T("MONDAY", urb(50, 700), IVORY, tracking=22)
    A["nov30"] = T("November 30", ital(118), IVORY)
    A["fri"] = T("FRIDAY", urb(50, 700), IVORY, tracking=22)
    A["dec4"] = T("December 4", ital(118), IVORY)
    A["t300"] = T("3:00", urb(250, 300), "satin")
    A["t915"] = T("9:15", urb(220, 300), "satin")
    A["t100"] = T("1:00", urb(220, 300), "satin")
    A["pm"] = T("p.m.", urb(66, 600), IVORY, tracking=3)
    A["am"] = T("a.m.", urb(66, 600), IVORY, tracking=3)
    A["refl"] = T("Reflexology Therapy", ital(104), IVORY)
    A["fhf"] = T("FOOT  &  HAND  &  FACIAL", urb(46, 700), "satin", tracking=10)
    A["and"] = T("and", imp(110), "satin")
    A["span"] = T("Spanish Massage", ital(104), IVORY)
    A["zr"] = T("Zarina, RCRT", ital(96), IVORY)
    A["s_mon"] = T("MONDAY  ·  NOVEMBER 30", urb(38, 700), IVORY, tracking=6)
    A["s_mon_t"] = T("3:00 p.m.", urb(78, 500), "satin")
    A["s_fri"] = T("FRIDAY  ·  DECEMBER 4", urb(38, 700), IVORY, tracking=6)
    A["s_fri_t"] = T("9:15 a.m.  ·  1:00 p.m.", urb(78, 500), "satin")
    A["addr"] = T("2020 Corydon Ave  ·  Winnipeg", urb(38, 600), IVORY, tracking=3)
    A["dm"] = T("SEND US A DM TO BOOK", urb(44, 800), IVORY, tracking=10)
    return A


def fade(t, s, e, fi=0.5, fo=0.45):
    return ease_out(prog(t, s, fi)) * (1 - ease_in_out(prog(t, e - fo, fo)))


def time_reveal(f, A, key, suf, t, t0, a, y, scale=1.0):
    """Hero time: blur → sharp out of the satin, then a light sweep; suffix + fine line draw in after."""
    tx, sx = A[key], A[suf]
    total = tx.adv + 14 + sx.adv
    x = W / 2 - total / 2
    p = prog(t, t0, 0.8)
    if p <= 0:
        return
    sharp_in(f, tx, x, y, p, a, scale_from=1.12, blur=18)
    if t > t0 + 0.8:
        put_shine(f, tx, x, y, a, prog(t, t0 + 0.8, 1.3))
    q = ease_out(prog(t, t0 + 0.45, 0.5))
    put(f, sx.img, x + tx.adv + 14 - sx.pad + 20 * (1 - q), y - sx.asc, a * q)
    line(f, W / 2, y + 48, 520 * ease_in_out(prog(t, t0 + 0.6, 0.8)), GOLD_LINE, a * 0.85, thick=2)


def frame_at(t, A):
    f = background(A, t)
    cx = W / 2
    # soft focus pocket: the satin softens behind the text so every word reads (no boxes)
    # 1 · hook — honest count (3 real openings)
    if t < HOOK[1] + 0.05:
        a = fade(t, *HOOK, 0.6, 0.45)
        wash(f, 620, 1250, NIGHT, 0.0, 0.0)
        letters(f, A["only"], cx - A["only"].adv / 2, 830, 0.45, t, a, step=0.03)
        wipe(f, A["yours"], cx - A["yours"].adv / 2, 1010, prog(t, 1.25, 1.1), a)
    # 2 · Monday — date drops in from above, hero time from the satin
    if MON[0] <= t < MON[1] + 0.05:
        a = fade(t, *MON)
        letters(f, A["mon"], cx - A["mon"].adv / 2, 560, MON[0] + 0.15, t, a, step=0.04)
        drop(f, A["nov30"], cx - A["nov30"].adv / 2, 700, prog(t, MON[0] + 0.5, 0.8), a)
        time_reveal(f, A, "t300", "pm", t, T_MON, a, 1080)
    # 3 · Friday — date slides from the right, two hero times stacked with their own push-ins
    if FRI[0] <= t < FRI[1] + 0.05:
        a = fade(t, *FRI)
        letters(f, A["fri"], cx - A["fri"].adv / 2, 500, FRI[0] + 0.15, t, a, step=0.04)
        slide(f, A["dec4"], cx - A["dec4"].adv / 2, 640, prog(t, FRI[0] + 0.5, 0.8), a, dx=90)
        time_reveal(f, A, "t915", "am", t, T_FRI[0], a, 960)
        time_reveal(f, A, "t100", "pm", t, T_FRI[1], a, 1300)
    # 4 · services — two beats, each max two lines
    if SVC[0] <= t < SVC[1] + 0.05:
        a = fade(t, *SVC)
        sw = SVC[0] + 2.2
        a1 = a * (1 - ease_in_out(prog(t, sw - 0.35, 0.35)))
        a2 = a * ease_out(prog(t, sw, 0.45))
        sharp_in(f, A["refl"], cx - A["refl"].adv / 2, 860, prog(t, SVC[0] + 0.2, 0.7), a1, blur=10)
        letters(f, A["fhf"], cx - A["fhf"].adv / 2, 970, SVC[0] + 0.7, t, a1, step=0.022)
        wipe(f, A["and"], cx - A["and"].adv / 2, 820, prog(t, sw, 0.6), a2)
        rise(f, A["span"], cx - A["span"].adv / 2, 970, prog(t, sw + 0.3, 0.6), a2)
    # 5 · summary — official logo on the dark satin (white lettering reads), all times, therapist, DM
    if t >= END[0]:
        a = ease_out(prog(t, END[0], 0.7))
        wash(f, 250, 1600, NIGHT, 0.35 * a, 0.35 * a)
        lg = A["logo"]
        pl = ease_out(prog(t, END[0] + 0.1, 0.8))
        put(f, lg, cx - lg.width / 2, 300 + 12 * (1 - pl), a * pl)
        y0 = 300 + lg.height + 120
        p = ease_out(prog(t, END[0] + 0.6, 0.6))
        put_c(f, A["s_mon"], y0, a * p, dy=10 * (1 - p))
        sharp_in(f, A["s_mon_t"], cx - A["s_mon_t"].adv / 2, y0 + 92, prog(t, END[0] + 0.8, 0.6), a, blur=8)
        p = ease_out(prog(t, END[0] + 1.1, 0.6))
        put_c(f, A["s_fri"], y0 + 200, a * p, dy=10 * (1 - p))
        sharp_in(f, A["s_fri_t"], cx - A["s_fri_t"].adv / 2, y0 + 292, prog(t, END[0] + 1.3, 0.6), a, blur=8)
        line(f, cx, y0 + 360, 420 * ease_in_out(prog(t, END[0] + 1.6, 0.7)), GOLD_LINE, a * 0.85, thick=2)
        sharp_in(f, A["zr"], cx - A["zr"].adv / 2, y0 + 470, prog(t, END[0] + 1.8, 0.7), a, blur=8)
        p = ease_out(prog(t, END[0] + 2.2, 0.6))
        put_c(f, A["addr"], y0 + 540, a * p, dy=10 * (1 - p))
        letters(f, A["dm"], cx - A["dm"].adv / 2, y0 + 640, END[0] + 2.6, t, a, step=0.025)
    # opening: from blur into reality; ending: back into a soft blur
    bi = 1 - ease_out(prog(t, 0.0, 1.0))
    bo = ease_in_out(prog(t, DURATION - 1.4, 1.4))
    b = max(bi, bo)
    if b > 0.01:
        f = f.filter(ImageFilter.GaussianBlur(24 * b))
        if bo > 0.01:
            f.alpha_composite(Image.new("RGBA", (W, H), (30, 24, 18, int(70 * bo))))
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


# ---------------------------------------------------------------- audio (§46: new direction)
def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(112)
    out = np.zeros(n)

    def add(at_, sig, g=1.0):
        i = int(at_ * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        k = min(len(sig), n - i)
        out[i:i + k] += g * sig[:k]

    BPM = 112
    BEAT = 60 / BPM
    BAR = 4 * BEAT
    hz = lambda m_: 440.0 * 2 ** ((m_ - 69) / 12)   # noqa: E731
    # A minor → C: Am9 · Fmaj7 · C · G6
    CH = [(45, [57, 60, 64, 67, 71]), (41, [57, 60, 64, 65, 69]), (48, [55, 60, 64, 67, 72]), (43, [55, 59, 62, 64, 67])]

    def fm_bell(f0, dur=1.6):
        L = int(dur * sr)
        tt = np.arange(L) / sr
        mod = 1.8 * np.exp(-tt * 5) * np.sin(2 * np.pi * f0 * 3.5 * tt)
        return np.sin(2 * np.pi * f0 * tt + mod) * np.exp(-tt * 3.2) * np.clip(tt / 0.003, 0, 1)

    def pad(f0, L):
        tt = np.arange(L) / sr
        sig = np.zeros(L)
        for d in (-0.004, 0.0, 0.005):
            ph = 2 * np.pi * f0 * (1 + d) * tt
            sig += np.sin(ph) + 0.35 * np.sin(2 * ph + 0.3) + 0.15 * np.sin(3 * ph + 1.1)
        return sig / 3

    def kick():
        L = int(0.35 * sr)
        tt = np.arange(L) / sr
        f = 48 + 90 * np.exp(-tt * 30)
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 9)

    def hat():
        L = int(0.05 * sr)
        x = rng.normal(0, 1, L)
        x = np.diff(np.concatenate([[0], x]))
        return x * np.exp(-np.arange(L) / sr * 90) * 0.5

    def riser(L=1.4):
        Ln = int(L * sr)
        x = rng.normal(0, 1, Ln)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(Ln, 1 / sr)
        X *= np.exp(-((fr - 2500) / 2000) ** 2)
        y = np.fft.irfft(X, Ln)
        return y / (np.abs(y).max() + 1e-9) * (np.arange(Ln) / Ln) ** 2.2

    def boom():
        L = int(1.8 * sr)
        tt = np.arange(L) / sr
        return np.sin(2 * np.pi * (44 + 20 * np.exp(-tt * 6)) * tt) * np.exp(-tt * 2.2)

    def sparkle():
        s = np.zeros(int(1.5 * sr))
        for k, m_ in enumerate((88, 91, 95, 100)):
            b = fm_bell(hz(m_), 1.2)
            i = int(k * 0.06 * sr)
            s[i:i + len(b)] += b[:len(s) - i]
        return s

    nb = int(DURATION / BAR) + 1
    for b in range(nb):
        root, voi = CH[b % 4]
        t0 = b * BAR
        L = int((BAR + 1.0) * sr)
        tt = np.arange(L) / sr
        env = np.clip(tt / 0.8, 0, 1) * np.clip((BAR + 1.0 - tt) / 0.9, 0, 1)
        for nn in voi[:4]:
            add(t0, 0.022 * env * pad(hz(nn), L))
        add(t0, 0.18 * np.sin(2 * np.pi * hz(root) * tt[:int(BAR * sr)]) * np.exp(-tt[:int(BAR * sr)] * 0.5))
        for j in range(8):                      # bell pluck pattern (8ths, syncopated)
            if j in (0, 3, 5, 6):
                nn = voi[(j + b) % len(voi)] + 12
                add(t0 + j * BEAT / 2, 0.09 * fm_bell(hz(nn)))
        if t0 >= 1.5:
            for j in range(4):
                add(t0 + j * BEAT, 0.30 * kick())
                add(t0 + j * BEAT + BEAT / 2, 0.06 * hat())
    for tr in (T_MON, T_FRI[0], T_FRI[1]):
        add(tr - 1.4, 0.06 * riser())
        add(tr, 0.20 * boom())
        add(tr + 0.05, 0.08 * sparkle())
    for at_ in (0.45, MON[0], FRI[0], SVC[0], END[0]):
        add(at_, 0.05 * sparkle())
    st = np.stack([out, np.roll(out, int(0.009 * sr))], 1)
    st *= (np.clip((DURATION - t) / 1.6, 0, 1) * np.clip(t / 0.4, 0, 1))[:, None]
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
        ts = [float(x) for x in sys.argv[2:]] or [0.3, 2.6, 7.0, 13.2, 15.8, 18.0, 22.0]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(OUT_DIR, "qc", f"n30-{s:05.2f}s.png"))
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
    Image.fromarray(frame_at(22.5, A)).save(os.path.join(OUT_DIR, f"{NAME}-story.jpg"), quality=94)
    print(NAME, DURATION)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
