"""THE PURE ESCAPE — Available Appointments, Tue Dec 1 · Wed Dec 2 · Thu Dec 3, 2026 ("Bronze Silk").
Tuesday, December 1: 11:00 a.m. · 12:15 p.m. · 1:30 p.m.
Wednesday, December 2: 11:00 a.m. · 12:15 p.m. · 1:30 p.m.
Thursday, December 3: 2:45 p.m. · 4:00 p.m. · 7:00 p.m.   (9 openings; weekdays verified, Thursday confirmed by the owner)
Services (owner's list for this week): Ultimate Escape Package (90 minutes) · Spanish Massage · Reflexology Therapy ·
Facial Reflexology with Chanel skincare. Zarina, RCRT · 698 Corydon Ave, Winnipeg · DM to book.

Background: owner's bronze + espresso silk clip with gold flakes, ping-ponged at 0.5x; push-ins on each time;
soft focus pocket behind the text; glints + champagne sweep (§45, §48). Logo on a soft light glow (§38).
Type (new): Bodoni Moda (display) + Mulish (sans) + Parisienne (script). Bronze · ivory · espresso.
Music (§46, new): B minor → D, 80 BPM: felt-piano arpeggios, soft synth-string pad, tambourine shimmer on
2 & 4, winter wind + distant chimes, low piano note + string swell on each time.

  python3 production/dec1_pe_midweek.py stills [t ...] | video
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
CLIP = os.path.join(ROOT, "brand", "photos", "pe-dec", "bronze-satin.mp4")
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
FR = "/tmp/claude-0/-home-user-Reflex/f74b54ed-c929-5941-94f0-7201420216f3/scratchpad/dec1.rgb"
OUT_DIR = base.OUT_DIR
NAME = "2026-12-01-pe-tue-wed-thu-available-appointments"
W, H, FPS = 1080, 1920, 30
DURATION = 34.0
IVORY = (250, 244, 232)
NIGHT = (4, 4, 6)
GOLD_LINE = (222, 188, 128)
base.GOLDS["satin"] = ((255, 232, 200), (226, 176, 120), (160, 104, 58))

# beats (s)
HOOK = (0.0, 3.4)
DAYS = [("TUESDAY", "December 1", [("11:00", "a.m."), ("12:15", "p.m."), ("1:30", "p.m.")]),
        ("WEDNESDAY", "December 2", [("11:00", "a.m."), ("12:15", "p.m."), ("1:30", "p.m.")]),
        ("THURSDAY", "December 3", [("2:45", "p.m."), ("4:00", "p.m."), ("7:00", "p.m.")])]
DAY_T = [(3.2, 9.6), (9.4, 15.8), (15.6, 22.0)]
TIMES = [[s + 1.7 + 1.25 * k for k in range(3)] for s, _ in DAY_T]
SVC = (21.8, 28.2)
END = (28.0, DURATION)
T_DAY = [x for row in TIMES for x in row]


def gl(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "BodoniModa[opsz,wght].ttf"), size)
    f.set_variation_by_axes([wght, 96 if size > 60 else 28])
    return f


def fig(size, wght=600):
    f = ImageFont.truetype(os.path.join(FONTS, "Mulish[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def alr(size):
    return ImageFont.truetype(os.path.join(FONTS, "Parisienne-Regular.ttf"), size)


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT)


class Satin:
    def __init__(self):
        w, h = 716, 1280
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
KEYS = [(0.0, 1.04, 0.50, 0.50), (3.2, 1.07, 0.47, 0.48)]
for _d, row in enumerate(TIMES):
    for _k, _tt in enumerate(row):
        KEYS.append((_tt, 1.09 + 0.04 * _k + 0.01 * _d, 0.50 + 0.03 * (-1) ** (_k + _d), 0.47 + 0.03 * _k))
    KEYS.append((DAY_T[_d][1] - 0.2, 1.06, 0.50, 0.50))
KEYS += [(SVC[0], 1.06, 0.52, 0.50), (END[0], 1.03, 0.50, 0.50), (DURATION, 1.08, 0.49, 0.48)]


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
    A["logo"] = logo.resize((380, round(logo.height * 380 / logo.width)), Image.LANCZOS)
    pad = 190
    g = Image.new("L", (A["logo"].width + 2 * pad, A["logo"].height + 2 * pad), 0)
    ImageDraw.Draw(g).ellipse((pad - 40, pad - 30, g.width - pad + 40, g.height - pad + 30), fill=225)
    A["logo_g"] = Image.new("RGBA", g.size, (250, 244, 234, 0))
    A["logo_g"].putalpha(g.filter(ImageFilter.GaussianBlur(50)).point(lambda v: min(255, int(v * 1.15))))   # soft edgeless light, no plate (§38)

    A["nine"] = T("9 OPENINGS THIS WEEK", fig(58, 900), IVORY, tracking=10)
    A["yours"] = T("find your moment", alr(140), "satin")
    A["days"] = [(T(d, fig(48, 900), IVORY, tracking=22), T(dt, fig(104, 300), IVORY)) for d, dt, _ in DAYS]
    A["tm"] = [[T(hm, fig(176, 300), "satin") for hm, _ in row] for _, _, row in DAYS]
    A["am"] = T("a.m.", fig(56, 800), IVORY, tracking=3)
    A["pm"] = T("p.m.", fig(56, 800), IVORY, tracking=3)
    A["svc"] = [(T("Ultimate Escape Package", gl(80, 500), IVORY), T("90 MINUTES", fig(44, 900), "satin", tracking=14)),
                (T("Spanish Massage", gl(88, 500), IVORY), T("Reflexology Therapy", alr(110), "satin")),
                (T("Facial Reflexology", gl(88, 500), IVORY), T("WITH CHANEL SKINCARE", fig(44, 900), "satin", tracking=12))]
    A["s_rows"] = []
    for d, dt, row in DAYS:
        lab = T(f"{d}  ·  {dt.upper()}", fig(34, 900), IVORY, tracking=5)
        tms = base.fit(lambda z, row=row: T("  ·  ".join(f"{hm} {ap}" for hm, ap in row), fig(z, 600), "satin"), 56, 900)
        A["s_rows"].append((lab, tms))
    A["zr"] = T("Zarina, RCRT", fig(66, 400), IVORY, tracking=2)
    A["addr"] = T("698 Corydon Ave  ·  Winnipeg", fig(36, 700), IVORY, tracking=3)
    A["dm"] = T("SEND US A DM TO BOOK", fig(42, 900), IVORY, tracking=10)
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
    # 1 · hook — honest count (9 real openings)
    if t < HOOK[1] + 0.05:
        a = fade(t, *HOOK, 0.6, 0.45)
        letters(f, A["nine"], cx - A["nine"].adv / 2, 830, 0.45, t, a, step=0.028)
        wipe(f, A["yours"], cx - A["yours"].adv / 2, 1000, prog(t, 1.3, 1.1), a)
    # 2 · days — each day enters differently; three hero times stacked, each with its own push-in
    for d, (s0, e0) in enumerate(DAY_T):
        if s0 <= t < e0 + 0.05:
            a = fade(t, s0, e0)
            lab, dt = A["days"][d]
            letters(f, lab, cx - lab.adv / 2, 470, s0 + 0.15, t, a, step=0.035)
            if d == 0:
                drop(f, dt, cx - dt.adv / 2, 610, prog(t, s0 + 0.5, 0.7), a)
            elif d == 1:
                slide(f, dt, cx - dt.adv / 2, 610, prog(t, s0 + 0.5, 0.7), a, dx=90)
            else:
                rise(f, dt, cx - dt.adv / 2, 610, prog(t, s0 + 0.5, 0.7), a)
            for k, (hm, ap) in enumerate(DAYS[d][2]):
                A["_t"] = A["tm"][d][k]
                time_reveal(f, A, "_t", "am" if ap == "a.m." else "pm", t, TIMES[d][k], a, 880 + 250 * k)
    # 3 · services — three beats, two lines each
    if SVC[0] <= t < SVC[1] + 0.05:
        a = fade(t, *SVC)
        beats = [SVC[0], SVC[0] + 2.1, SVC[0] + 4.2]
        for k, (big, small) in enumerate(A["svc"]):
            b0 = beats[k]
            b1 = beats[k + 1] if k < 2 else SVC[1] + 1
            ak = a * ease_out(prog(t, b0, 0.4)) * (1 - ease_in_out(prog(t, b1 - 0.3, 0.3)))
            if ak <= 0.003:
                continue
            sharp_in(f, big, cx - big.adv / 2, 880, prog(t, b0 + 0.05, 0.6), ak, blur=10)
            if small.xs:
                letters(f, small, cx - small.adv / 2, 990, b0 + 0.45, t, ak, step=0.022)
            else:
                wipe(f, small, cx - small.adv / 2, 1020, prog(t, b0 + 0.4, 0.8), ak)
    # 4 · summary — logo on a soft light glow, all nine times, therapist, address, DM
    if t >= END[0]:
        a = ease_out(prog(t, END[0], 0.7))
        lg = A["logo"]
        pl = ease_out(prog(t, END[0] + 0.1, 0.8))
        gw = A["logo_g"]
        put(f, gw, cx - gw.width / 2, 290 + lg.height / 2 - gw.height / 2, a * pl * 0.95)
        put(f, lg, cx - lg.width / 2, 290 + 12 * (1 - pl), a * pl)
        y0 = 290 + lg.height + 110
        for k, (lab, tms) in enumerate(A["s_rows"]):
            yk = y0 + 175 * k
            p = ease_out(prog(t, END[0] + 0.5 + 0.35 * k, 0.6))
            put_c(f, lab, yk, a * p, dy=10 * (1 - p))
            sharp_in(f, tms, cx - tms.adv / 2, yk + 78, prog(t, END[0] + 0.65 + 0.35 * k, 0.6), a, blur=8)
        yz = y0 + 175 * 3 - 20
        line(f, cx, yz, 420 * ease_in_out(prog(t, END[0] + 1.7, 0.7)), GOLD_LINE, a * 0.85, thick=2)
        sharp_in(f, A["zr"], cx - A["zr"].adv / 2, yz + 95, prog(t, END[0] + 1.9, 0.7), a, blur=8)
        p = ease_out(prog(t, END[0] + 2.2, 0.6))
        put_c(f, A["addr"], yz + 160, a * p, dy=10 * (1 - p))
        letters(f, A["dm"], cx - A["dm"].adv / 2, yz + 245, END[0] + 2.5, t, a, step=0.025)
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

    BPM = 80
    BEAT = 60 / BPM
    BAR = 4 * BEAT
    hz = lambda m_: 440.0 * 2 ** ((m_ - 69) / 12)   # noqa: E731
    # B minor → D: Bm9 · Gmaj7 · D · A6
    CH = [(47, [59, 62, 66, 69, 73]), (43, [59, 62, 66, 67, 71]), (50, [57, 62, 66, 69, 74]), (45, [57, 61, 64, 66, 69])]

    def piano(f0, dur=2.6):
        L = int(dur * sr)
        tt = np.arange(L) / sr
        sig = sum(np.sin(2 * np.pi * f0 * k * (1 + 0.0004 * k * k) * tt) * np.exp(-tt * (1.2 + 0.9 * k)) / k ** 1.3 for k in range(1, 7))
        felt = np.clip(tt / 0.012, 0, 1)
        return sig * felt * np.exp(-tt * 0.6)

    def strings(f0, L):
        tt = np.arange(L) / sr
        vib = 1 + 0.003 * np.sin(2 * np.pi * 4.8 * tt)
        ph = 2 * np.pi * f0 * np.cumsum(vib) / sr
        return sum(np.sin(k * ph) * (0.8 ** k) for k in range(1, 7))

    def tamb():
        L = int(0.22 * sr)
        x = rng.normal(0, 1, L)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(L, 1 / sr)
        X *= np.exp(-((fr - 8000) / 2500) ** 2)
        y = np.fft.irfft(X, L)
        tt = np.arange(L) / sr
        jingle = sum(np.sin(2 * np.pi * f * tt) for f in (6200, 7400, 8900)) * 0.15
        return (y / (np.abs(y).max() + 1e-9) + jingle) * np.exp(-tt * 18)

    def chime(f0):
        L = int(3.0 * sr)
        tt = np.arange(L) / sr
        return (np.sin(2 * np.pi * f0 * tt) + 0.4 * np.sin(2 * np.pi * f0 * 2.92 * tt) * np.exp(-tt)) * np.exp(-tt * 1.3)

    def swell(f0, L=1.6):
        Ln = int(L * sr)
        tt = np.arange(Ln) / sr
        return strings(f0, Ln) * np.sin(np.pi * tt / L) ** 2

    nb = int(DURATION / BAR) + 1
    for b in range(nb):
        root, voi = CH[b % 4]
        t0 = b * BAR
        L = int((BAR + 1.2) * sr)
        tt = np.arange(L) / sr
        env = np.clip(tt / 1.0, 0, 1) * np.clip((BAR + 1.2 - tt) / 1.0, 0, 1)
        for nn in voi[:3]:
            add(t0 - 0.2, 0.010 * env * strings(hz(nn), L))
        add(t0, 0.20 * piano(hz(root), 3.0))
        arp = voi + voi[-2:0:-1]
        for j in range(8):
            add(t0 + j * BEAT / 2 + rng.uniform(-0.01, 0.01), 0.07 * piano(hz(arp[j % len(arp)] + 12), 1.8))
        if t0 >= 3.0:
            for j in (1, 3):
                add(t0 + j * BEAT, 0.035 * tamb())
    wind = rng.normal(0, 1, n)
    W_ = np.fft.rfft(wind)
    fr = np.fft.rfftfreq(n, 1 / sr)
    W_ *= np.exp(-((fr - 500) / 400) ** 2)
    wind = np.fft.irfft(W_, n)
    wind = wind / (np.abs(wind).max() + 1e-9) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 7.0)) * 0.05
    out += wind
    for k in range(int(DURATION / 3)):
        add(rng.uniform(0, DURATION), 0.03 * chime(hz(int(rng.choice([86, 90, 93, 98])))))
    for tr in T_DAY:
        add(tr, 0.16 * piano(hz(38), 2.5))
        add(tr - 0.6, 0.02 * swell(hz(74)))
    for at_ in (0.45, DAY_T[0][0], DAY_T[1][0], DAY_T[2][0], SVC[0], END[0]):
        add(at_, 0.05 * chime(hz(86)))
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
        ts = [float(x) for x in sys.argv[2:]] or [2.6, 8.5, 14.8, 21.2, 23.0, 32.0]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(OUT_DIR, "qc", f"d1-{s:05.2f}s.png"))
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
    Image.fromarray(frame_at(32.5, A)).save(os.path.join(OUT_DIR, f"{NAME}-story.jpg"), quality=94)
    print(NAME, DURATION)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
