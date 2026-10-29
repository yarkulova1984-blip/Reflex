"""THE PURE ESCAPE (698 Corydon Ave) — Available Appointments, November 2026. Zarina, RCRT.
Two Reels from one engine:
  tue_thu — Tuesday Nov 3, Wednesday Nov 4, Thursday Nov 5 ("Candlelit Week"): owner's photo of Zarina at a foot session.
  sat7    — Saturday Nov 7 ("Chanel Saturday"): owner's facial reflexology + Chanel skincare photos.
Photos are only cropped, scaled, moved and lit (Zarina's face is either fully in frame or out of it). The Pure Escape logo is
placed unchanged over an edgeless soft light glow (no plate). Dates, times, services typeset here.
Type: Marcellus (classic display) + Mulish (clean sans) — new pairing. Music: see synth_* (new directions, §46).

  python3 production/nov_pe_appointments.py <tue_thu|sat7> stills t [t ...]
  python3 production/nov_pe_appointments.py <tue_thu|sat7> video
"""
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nov2_6_amt_roses import Canvas, ease, ease_out, hx, ramp, text  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
PH = os.path.join(ROOT, "brand", "photos")
OUT = os.path.join(ROOT, "content", "videos")
W, H, FPS = 1080, 1920, 30
IVORY, GOLD_HI, ESPRESSO, SAGE = hx("#F7F0E6"), hx("#E9D3A0"), hx("#24170F"), hx("#B9C8A6")


def marc(s):
    return ImageFont.truetype(os.path.join(FONTS, "Marcellus-Regular.ttf"), s)


def mul(s, w=500):
    f = ImageFont.truetype(os.path.join(FONTS, "Mulish[wght].ttf"), s)
    f.set_variation_by_axes([w])
    return f


CFG = {
    "tue_thu": dict(
        name="2026-11-03-05-pe-available-appointments",
        hook=("THIS WEEK", "EIGHT", "openings for you", "TUE  ·  WED  ·  THU  ·  ZARINA, RCRT"),
        days=[("TUESDAY", "November 3", [("11:00", "a.m."), ("12:45", "p.m."), ("2:00", "p.m."), ("3:45", "p.m.")]),
              ("WEDNESDAY", "November 4", [("11:00", "a.m."), ("12:15", "p.m."), ("3:30", "p.m.")]),
              ("THURSDAY", "November 5", [("7:00", "p.m.")])],
        # shots: (photo, t0, t1, box0 (cx, cy, h), box1) — source px
        shots=[("pe-nov/zarina-foot-session.png", 0.0, 3.8, (470, 835, 1670), (470, 800, 1560)),
               ("pe-nov/zarina-foot-session.png", 3.4, 21.0, (560, 1090, 1100), (540, 1130, 960)),   # hands + feet, face out of frame
               ("pe-nov/zarina-foot-session.png", 20.6, 40.0, (470, 835, 1670), (470, 820, 1560))],
        music="tue_thu"),
    "sat7": dict(
        name="2026-11-07-pe-available-appointments",
        hook=("SATURDAY  ·  NOVEMBER 7", "THREE", "openings to glow", "FACIAL REFLEXOLOGY  ·  CHANEL SKINCARE"),
        days=[("SATURDAY", "November 7", [("9:00", "a.m."), ("12:15", "p.m."), ("1:30", "p.m.")])],
        shots=[("pe-facial/16-hand-cream.png", 0.0, 3.8, (543, 724, 1448), (543, 700, 1340)),  # hands only: hook text never covers a face
               ("pe-facial/08-la-mousse-hands.png", 3.4, 7.8, (512, 768, 1537), (520, 800, 1380)),
               ("pe-facial/11-le-gommage.png", 7.4, 14.6, (561, 701, 1402), (540, 720, 1260)),
               ("pe-facial/16-hand-cream.png", 14.2, 40.0, (560, 820, 1200), (540, 780, 1100))],
        music="sat7"),
}
SERVICES = ["Facial Reflexology — Bergman Method", "Chanel Skincare", "Foot & Hand Reflexology", "Spanish Massage",
            "Ultimate Escape Package"]


def timeline(c):
    t, days = 7.6, []
    for d in c["days"]:
        n = len(d[2])
        dur = 0.9 + n * 0.75 + 2.6
        days.append((t, t + dur))
        t += dur
    serv = (t - 0.2, t + 4.6)
    ec = serv[1]
    return days, serv, ec, ec + 5.2


class Reel:
    def __init__(self, key):
        self.c = c = CFG[key]
        self.key = key
        self.days_t, self.serv_t, self.T_EC, self.T_END = timeline(c)
        self.ims = {}
        for s in c["shots"]:
            if s[0] not in self.ims:
                self.ims[s[0]] = Image.open(os.path.join(PH, s[0])).convert("RGB")
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        r = np.hypot((xx - W / 2) / W, (yy - H / 2) / H)
        self.vig = np.clip(1.08 - 0.7 * r ** 1.8, 0.45, 1)[..., None]
        self.col = np.clip(1 - 0.62 * np.exp(-((xx - 540) / 480) ** 4 - ((yy - 930) / 560) ** 4), 0.28, 1)[..., None]
        lg = Image.open(LOGO).convert("RGBA")
        lg = lg.crop(lg.getbbox())
        self.logo = np.asarray(lg.resize((600, int(lg.height * 600 / lg.width)), Image.LANCZOS), np.float32) / 255
        self.logo_sm = np.asarray(lg.resize((480, int(lg.height * 480 / lg.width)), Image.LANCZOS), np.float32) / 255
        rng = np.random.default_rng(1105 if key == "tue_thu" else 1107)
        self.motes = np.c_[rng.uniform(0, W, 40), rng.uniform(0, H, 40), rng.uniform(1.5, 3.5, 40), rng.uniform(0, 6.3, 40)]
        self.grain = [rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(5)]
        self.reveals = [t0 + 0.9 + i * 0.75 for (t0, _), d in zip(self.days_t, c["days"]) for i in range(len(d[2]))]
        self.f = dict(tag=mul(30, 700), hook=marc(150), script=marc(72), day=marc(104), date=mul(56, 300), time=marc(124),
                      ampm=mul(40, 600), serv=mul(46, 500), stitle=marc(84), addr=mul(54, 700), city=mul(38, 500), dm=marc(116))

    def shot(self, s, t):
        name, t0, t1, b0, b1 = s
        u = ease((t - t0) / (t1 - t0))
        cx, cy, h = [a + (b - a) * u for a, b in zip(b0, b1)]
        h /= 1.0 + sum(0.02 * ease((t - tr) / 0.9) for tr in self.reveals if self.serv_t[0] > t)
        im = self.ims[name]
        sw, sh = im.size
        h = min(h, sh, sw * H / W)
        w = h * W / H
        cx, cy = float(np.clip(cx, w / 2, sw - w / 2)), float(np.clip(cy, h / 2, sh - h / 2))
        crop = im.transform((W, H), Image.EXTENT, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), Image.BICUBIC)
        return crop

    def frame(self, t):
        img, wsum, last = np.zeros((H, W, 3), np.float32), 0.0, None
        for s in self.c["shots"]:
            if s[1] - 0.01 <= t <= s[2]:
                a = (1.0 if s[1] == 0 else ramp(t, s[1], s[1] + 0.45)) * (1 - ramp(t, s[2] - 0.45, s[2]))
                if a > 0.001:
                    crop = self.shot(s, t)
                    img += np.asarray(crop, np.float32) / 255 * a
                    wsum += a
                    last = crop
        img = img / max(wsum, 1e-6)
        ec = ramp(t, self.T_EC - 0.4, self.T_EC + 0.3)
        if ec > 0 and last is not None:
            img = img * (1 - ec) + np.asarray(last.filter(ImageFilter.GaussianBlur(30)), np.float32) / 255 * ec
        # candle-warm light breathing + drifting sweep
        br = 0.5 + 0.5 * np.sin(t * 1.7) * np.sin(t * 0.63 + 1)
        sweep = np.exp(-(((self.xx * 0.75 + self.yy * 0.5) - (-500 + 220 * (t % 12))) / 360) ** 2)[..., None]
        img = img * (0.95 + 0.05 * br + 0.08 * sweep) + sweep * np.array([1.0, 0.82, 0.55]) * 0.04
        img = img * self.col + ESPRESSO * (1 - self.col) * 0.5
        cv = Canvas(np.clip(img * self.vig, 0, 1).astype(np.float32))
        for x, y, r, ph in self.motes:
            yy = (y - t * (8 + 6 * np.sin(ph))) % H
            cv.dot(x + 18 * np.sin(t * 0.4 + ph), yy, r, GOLD_HI, 0.10 + 0.12 * (0.5 + 0.5 * np.sin(t * 2 + ph * 5)))
        self.overlays(cv, t)
        out = cv.a + np.repeat(np.repeat(self.grain[int(t * FPS) % 5], 2, 0), 2, 1)[..., None] * 0.01
        return (np.clip(out * (1 - ramp(t, self.T_END - 0.5, self.T_END)), 0, 1) * 255).astype(np.uint8)

    def put_logo(self, cv, logo, y, a, t0, t):
        """Edgeless soft light glow behind The Pure Escape logo (its black line art needs a light ground) — no plate."""
        lh, lw = logo.shape[:2]
        g = np.exp(-(((self.xx - 540) / (lw * 0.62)) ** 2 + ((self.yy - (y + lh / 2)) / (lh * 0.75)) ** 2))[..., None]
        cv.a = np.clip(cv.a * (1 - 0.82 * g * a) + IVORY * 0.82 * g * a, 0, 1)
        cv.put(logo, 540, y, a, scale=0.96 + 0.04 * ease_out((t - t0) / 0.8))

    def overlays(self, cv, t):
        f, c = self.f, self.c
        h1, h2, h3, h4 = c["hook"]
        if t < 3.6:  # HOOK (frame 0 = cover)
            a = 1 - ramp(t, 3.2, 3.6)
            e = ease_out(t / 1.1) if t > 0.05 else 1.0
            cv.put(text(h1, f["tag"], GOLD_HI, tracking=10), 540, 600, a, shadow=1.0)
            cv.put(text(h2, f["hook"], IVORY, tracking=8 + 16 * (1 - e)), 540, 650, a, shadow=1.0)
            cv.put(text(h3, f["script"], "gold", key=("h3", self.key)), 540, 830, a, shadow=1.0, sweep=ramp(t, 0.4, 1.8) if t > 0.05 else None)
            cv.put(text(h4, f["tag"], IVORY, tracking=5), 540, 950, a, shadow=1.0)
        if 3.3 <= t < 7.8:  # LOGO
            a = ramp(t, 3.4, 3.9) * (1 - ramp(t, 7.3, 7.8))
            self.put_logo(cv, self.logo, 470, a, 3.4, t)
            k = ramp(t, 4.6, 5.0)
            cv.put(text("Available Appointments", f["script"], "gold", key="aa"), 540, 900, a * k, shadow=1.0, reveal=("x", ramp(t, 4.6, 5.6)))
            cv.put(text("698 CORYDON AVE  ·  ZARINA, RCRT", f["tag"], IVORY, tracking=6), 540, 1010, a * ramp(t, 5.4, 5.8), shadow=1.0)
        for (t0, t1), (day, date, times) in zip(self.days_t, c["days"]):  # DAYS
            if t0 - 0.1 <= t < t1:
                a = ramp(t, t0, t0 + 0.35) * (1 - ramp(t, t1 - 0.4, t1))
                cv.put(text(day, f["day"], IVORY, tracking=10), 540, 470, a, shadow=1.0, blur=8 * (1 - ease_out((t - t0) / 0.5)))
                cv.put(text(date.upper(), f["date"], GOLD_HI, tracking=12), 540, 610, a * ramp(t, t0 + 0.25, t0 + 0.6), shadow=1.0)
                for i, (tm, ap) in enumerate(times):
                    tr = t0 + 0.9 + i * 0.75
                    ti, ai = text(tm, f["time"], "gold", key=("t", tm)), text(ap, f["ampm"], IVORY)
                    tw = ti.shape[1] + 14 + ai.shape[1]
                    y = 760 + i * 150
                    x = 540 - tw / 2 - 50 * (1 - ease_out((t - tr) / 0.6))
                    cv.put(ti, x, y, a * ramp(t, tr, tr + 0.35), "lt", shadow=1.0)
                    cv.put(ai, x + ti.shape[1] + 14, y + ti.shape[0] - ai.shape[0] - 28, a * ramp(t, tr + 0.25, tr + 0.55), "lt", shadow=1.0)
        s0, s1 = self.serv_t
        if s0 <= t < s1 + 0.1:  # SERVICES
            a = ramp(t, s0 + 0.1, s0 + 0.4) * (1 - ramp(t, s1 - 0.35, s1 + 0.05))
            cv.put(text("SERVICES", f["stitle"], IVORY, tracking=14), 540, 470, a, shadow=1.0)
            for i, sv in enumerate(SERVICES):
                ts = s0 + 0.5 + i * 0.4
                cv.put(text(sv, f["serv"], IVORY if i % 2 == 0 else GOLD_HI), 540, 650 + i * 95, a * ramp(t, ts, ts + 0.35), shadow=1.0,
                       reveal=("y", ramp(t, ts, ts + 0.5)))
        if t >= self.T_EC - 0.1:  # END CARD
            T = self.T_EC
            a = ramp(t, T + 0.1, T + 0.5)
            self.put_logo(cv, self.logo_sm, 330, a, T, t)
            k = ramp(t, T + 0.6, T + 1.0)
            cv.put(text("698 Corydon Ave", f["addr"], IVORY), 540, 760, a * k, shadow=1.0)
            cv.put(text("Winnipeg, Manitoba", f["city"], IVORY), 540, 840, a * k, shadow=1.0)
            cv.put(text("ZARINA, RCRT", f["tag"], GOLD_HI, tracking=8), 540, 915, a * k, shadow=1.0)
            k2 = ramp(t, T + 1.2, T + 1.6)
            cv.line(540 - 220, 540 + 220, 995, GOLD_HI, a * k2, 2, frac=ramp(t, T + 1.2, T + 1.9))
            cv.put(text("DM TO BOOK", f["dm"], "gold", key="dm"), 540, 1040, a * k2, shadow=1.0,
                   scale=0.92 + 0.08 * ease_out((t - T - 1.2) / 0.6), sweep=ramp(t, T + 1.9, T + 3.1))


def synth(key, reveals, T_EC, T_END, path, sr=48000):
    """tue_thu: E major (Emaj9 · C#m9 · Amaj7 · B6) · 76 BPM · soft electric piano (Rhodes-like) + bowed-pad strings ·
    gentle heartbeat-like low pulse · crackling-candle texture · celesta glints on each time.
    sat7: F major (Fmaj7 · Dm9 · Bbmaj9 · Csus4→C) · 108 BPM bossa-like groove · nylon guitar comping + flute-like lead ·
    shaker + rim clicks · glass pings on each time."""
    rng = np.random.default_rng(55 if key == "tue_thu" else 77)
    N = int(T_END * sr)
    b = np.zeros((N, 2))

    def add(sig, t0, g, pan=0.0):
        i = int(t0 * sr)
        if i >= N or i < 0:
            return
        sig = sig[:N - i]
        b[i:i + len(sig), 0] += sig * g * np.sqrt(0.5 * (1 - pan))
        b[i:i + len(sig), 1] += sig * g * np.sqrt(0.5 * (1 + pan))

    def tt(d):
        return np.arange(int(d * sr)) / sr

    def m2f(m):
        return 440 * 2 ** ((m - 69) / 12)

    def ks(f, d, bright=0.5):
        n, p = int(d * sr), max(2, int(sr / f))
        buf = rng.uniform(-1, 1, p)
        out = np.zeros(n)
        for i in range(n):
            out[i] = buf[i % p]
            buf[i % p] = (bright * buf[i % p] + (1 - bright) * buf[(i + 1) % p]) * 0.996
        return out

    if key == "tue_thu":
        beat = 60 / 76
        prog = [[52, 56, 59, 63, 66], [49, 52, 56, 59, 63], [45, 49, 52, 56, 61], [47, 51, 54, 56, 59]]
        t, k = 0.0, 0
        while t < T_END - 1:
            ch = prog[k % 4]
            x = tt(4 * beat + 0.8)
            for n in ch[1:]:
                pad = sum(np.sin(2 * np.pi * m2f(n) * (1 + d) * x) for d in (-0.003, 0, 0.003)) / 3
                add(pad * np.minimum(1, x / 1.0) * np.minimum(1, (x[-1] - x) / 0.8), t, 0.03)
            for j in range(4):
                for n in ch[1:4]:
                    y = tt(1.6)
                    mod = np.sin(2 * np.pi * m2f(n + 12) * y) * (1.4 * np.exp(-y * 4) + 0.2)
                    add(np.sin(2 * np.pi * m2f(n + 12) * y + mod) * np.exp(-y * 1.5) * (1 + 0.12 * np.sin(2 * np.pi * 4.5 * y)), t + j * beat, 0.025, pan=0.2 * (j - 1.5))
            add(np.sin(2 * np.pi * m2f(ch[0] - 12) * x) * np.exp(-x * 0.7) * np.minimum(1, x / 0.05), t, 0.14)
            t += 4 * beat
            k += 1
        hb = np.sin(2 * np.pi * 55 * tt(0.25)) * np.exp(-tt(0.25) * 16)
        t = 3.0
        while t < T_END - 2:
            add(hb, t, 0.13)
            add(hb, t + 0.27, 0.08)
            t += 2 * beat
        cr = np.zeros(N)
        idx = rng.integers(0, N, int(T_END * 12))
        cr[idx] = rng.uniform(-1, 1, len(idx))
        add(np.convolve(cr, np.exp(-np.arange(80) / 10), "same"), 0, 0.03)
        for tr in reveals + [3.4, T_EC + 0.1]:
            y = tt(1.6)
            f = m2f(88)
            add((np.sin(2 * np.pi * f * y) + 0.4 * np.sin(2 * np.pi * f * 4 * y) * np.exp(-y * 9)) * np.exp(-y * 3), tr, 0.06)
    else:
        beat = 60 / 108
        prog = [[53, 57, 60, 64], [50, 53, 57, 60, 64], [46, 50, 53, 57, 60], [48, 53, 55, 60]]
        mel = [72, 74, 76, 77, 76, 74, 72, 69, 70, 72, 74, 72, 69, 67, 69, 72]
        t, k = 0.0, 0
        while t < T_END - 1:
            ch = prog[k % 4]
            x = tt(4 * beat)
            add(np.sin(2 * np.pi * m2f(ch[0] - 12) * x) * np.exp(-x * 1.2) * np.minimum(1, x / 0.02), t, 0.16)
            add(np.sin(2 * np.pi * m2f(ch[0] - 5) * x) * np.exp(-x * 1.5) * np.minimum(1, x / 0.02), t + 2 * beat, 0.11)
            for j in (0, 1.5, 2, 3.5):  # bossa comping
                s = sum(ks(m2f(n + 12), 0.6, 0.45) for n in ch[1:]) / len(ch[1:])
                add(s, t + j * beat, 0.08, pan=-0.25)
            if k >= 1:
                for j in range(4):
                    y = tt(beat * 0.95)
                    f = m2f(mel[(k * 4 + j) % 16])
                    vib = 1 + 0.005 * np.sin(2 * np.pi * 5.3 * y) * np.minimum(1, y / 0.25)
                    s = np.sin(2 * np.pi * f * np.cumsum(vib) / sr) + rng.normal(0, 1, len(y)) * 0.03
                    add(s * np.minimum(1, y / 0.06) * np.minimum(1, (y[-1] - y) / 0.1), t + j * beat, 0.055, pan=0.2)
            t += 4 * beat
            k += 1
        shk = rng.normal(0, 1, int(0.06 * sr)) * np.exp(-tt(0.06) * 60)
        rim = (np.sin(2 * np.pi * 1800 * tt(0.05)) + rng.normal(0, 1, int(0.05 * sr)) * 0.4) * np.exp(-tt(0.05) * 90)
        t, i = 2.5, 0
        while t < T_END - 2:
            add(shk, t, 0.03 if i % 2 else 0.02, pan=0.3)
            if i % 4 in (1, 3) and int(t / beat) % 8 in (2, 5):
                add(rim, t, 0.05, pan=-0.1)
            t += beat / 2
            i += 1
        for tr in reveals + [3.4, T_EC + 0.1]:
            y = tt(2.0)
            add(sum(w * np.sin(2 * np.pi * 1568 * h * y) * np.exp(-y * (2 + 2 * h)) for h, w in ((1, 1), (2.7, .3))), tr, 0.05)
    n = int(2.4 * sr)
    nfft = 1 << (N + n - 2).bit_length()
    for ch_ in range(2):
        ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (0.32 * sr))
        y = np.fft.irfft(np.fft.rfft(b[:, ch_], nfft) * np.fft.rfft(ir, nfft), nfft)[:N]
        b[:, ch_] = b[:, ch_] * 0.75 + y / (np.abs(y).max() + 1e-9) * np.abs(b[:, ch_]).max() * 0.25
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
    key, mode = sys.argv[1], sys.argv[2]
    R = Reel(key)
    name = R.c["name"]
    if mode == "stills":
        d = os.path.join(OUT, "_stills")
        os.makedirs(d, exist_ok=True)
        for t in sys.argv[3:]:
            Image.fromarray(R.frame(float(t))).save(os.path.join(d, f"{name}_{float(t):05.2f}.png"))
        print(R.T_END)
        return
    vid = os.path.join(OUT, f"{name}_video.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
    for i in range(int(round(R.T_END * FPS))):
        p.stdin.write(R.frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    wav = os.path.join(OUT, f"{name}.wav")
    synth(key, R.reveals, R.T_EC, R.T_END, wav)
    out = os.path.join(OUT, f"{name}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(vid)
    os.remove(wav)
    Image.fromarray(R.frame(0.0)).save(os.path.join(OUT, f"{name}-cover.jpg"), quality=92)
    print(out)


if __name__ == "__main__":
    main()
