"""ADVANCED MASSAGE THERAPY — Available Appointments, week of Nov 23, 2026 ("Gilded Leaves").
Monday, November 23: 5:30 p.m. · 6:45 p.m.   Friday, November 27: 9:15 · 10:30 · 11:45 a.m. · 1:00 p.m.
Services (owner's list): Spanish Massage · Foot, Hand & Facial Reflexology. Zarina, RCRT. DM to book.

Background: owner's bronze-and-gold leaf photo, alive: palm fronds sway (masked warp), a champagne
light sweep glides over the gold leaves, drifting gold dust, slow camera push / slide (§45, §48).
Text: safe area x 60–960, y 250–1580 (§49); blur-in opening, blur-out ending.
Type (new): DM Serif Display (roman + italic) + Lexend + Corinthia (script accent).
Music (§46, new): F minor → A♭, 88 BPM lo-fi: warm Rhodes chords, soft flute-like lead, lo-fi kick
+ rim, tape hiss with gentle wow; glass ping on each time reveal.

  python3 production/nov23_amt_week.py stills [t ...] | video
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
from oct16_amt_thanksgiving import Text, bilinear, ease_in_out, ease_out, letters, line, prog, put, put_c, put_x, rise, sharp_in, wash, wipe  # noqa: E402

ROOT = base.ROOT
FONTS = base.FONTS
BG = os.path.join(ROOT, "brand", "photos", "amt-nov23", "gold-leaves.jpg")
LOGO = os.path.join(ROOT, "brand", "locations", "advanced-massage-therapy-logo.png")
OUT_DIR = base.OUT_DIR
NAME = "2026-11-23-amt-available-appointments"
W, H, FPS = 1080, 1920, 30
DURATION = 30.0

IVORY = (252, 246, 236)
NIGHT = (24, 14, 8)
GOLD_LINE = (232, 198, 138)
base.GOLDS["gilt"] = ((255, 240, 206), (232, 194, 128), (172, 128, 64))

CLINIC, ADDRESS, THERAPIST = "Advanced Massage Therapy", "2020 Corydon Ave, Winnipeg", "Zarina, RCRT"
DAYS = [("MONDAY", "November 23", [("5:30", "p.m."), ("6:45", "p.m.")]),
        ("FRIDAY", "November 27", [("9:15", "a.m."), ("10:30", "a.m."), ("11:45", "a.m."), ("1:00", "p.m.")])]
SERVICES = ["Spanish Massage", "Foot Reflexology", "Hand Reflexology", "Facial Reflexology"]


def dms(size, italic=False):
    return ImageFont.truetype(os.path.join(FONTS, "DMSerifDisplay-Italic.ttf" if italic else "DMSerifDisplay-Regular.ttf"), size)


def lex(size, wght=400):
    f = ImageFont.truetype(os.path.join(FONTS, "Lexend[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def cor(size):
    return ImageFont.truetype(os.path.join(FONTS, "Corinthia-Regular.ttf"), size)


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT)


# ---------------------------------------------------------------- living background
def build_bg():
    im = Image.open(BG).convert("RGB")
    k = max(W / im.width, H / im.height) * 1.18
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 50, 2))
    arr = np.asarray(big, np.float32) * 0.82                     # deepen for readable ivory/gold type
    h, w = arr.shape[:2]
    lum = np.asarray(big.convert("L"), np.float32)
    rgb = np.asarray(big, np.float32)
    gold = np.clip((lum - 150) / 60, 0, 1) * np.clip((rgb[..., 0] - rgb[..., 2] - 30) / 40, 0, 1)
    gold = np.asarray(Image.fromarray((gold * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    palm = np.clip((xx / w - 0.40) / 0.2, 0, 1) * np.clip(1 - (yy / h - 0.62) / 0.12, 0, 1)   # gold palm fronds (top right)
    palm = np.asarray(Image.fromarray((palm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40)), np.float32) / 255
    return {"arr": arr, "w": w, "h": h, "gold": gold, "palm": palm}


CAM = [(0.0, 0.50, 0.50, 1.00), (6.4, 0.46, 0.46, 1.06), (12.3, 0.54, 0.52, 1.10), (19.2, 0.50, 0.56, 1.04), (DURATION, 0.50, 0.50, 1.00)]


def cam(t):
    for (t0, *a), (t1, *b) in zip(CAM, CAM[1:]):
        if t0 <= t <= t1:
            e = ease_in_out((t - t0) / (t1 - t0))
            return tuple(x + (y - x) * e for x, y in zip(a, b))
    return CAM[-1][1:]


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
    pm = B["palm"][iy, ix]
    gx = gx + pm * (5.0 * np.sin(0.9 * t + gy * 0.004) + 2.0 * np.sin(1.9 * t + gx * 0.006))
    gy = gy + pm * (2.5 * np.sin(1.1 * t + gx * 0.005))
    img = bilinear(B["arr"], gx, gy)
    # champagne light sweep travelling over the gold leaves
    g = B["gold"][iy, ix]
    sx = ((t * 0.11) % 1.4 - 0.2) * W
    band = np.exp(-(((A["xx"] - sx) + (A["yy"] - H / 2) * 0.45) / 170.0) ** 2)
    img = img + (g * band)[..., None] * np.array([120, 96, 52], np.float32) + (g * 18)[..., None]
    if soften > 0.01:
        img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8 * soften)), np.float32)
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    for (x, y, spd, ph, a) in A["dust"]:
        put(f, A["mote"], x + 18 * math.sin(t * 0.4 + ph), (y - spd * t) % H, a * (0.4 + 0.6 * max(0.0, math.sin(t * 1.5 + ph))))
    return f


def build():
    A = {"B": build_bg()}
    rng = np.random.default_rng(23)
    A["grain"] = [rng.normal(0, 2.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["xx"], A["yy"] = xx, yy
    A["vig"] = (1 - 0.3 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    m = Image.new("L", (20, 20), 0)
    ImageDraw.Draw(m).ellipse((8, 8, 12, 12), fill=230)
    mote = Image.new("RGBA", (20, 20), (255, 228, 170, 0))
    mote.putalpha(m.filter(ImageFilter.GaussianBlur(2)))
    A["mote"] = mote
    A["dust"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(5, 14), rng.uniform(0, 6.28), rng.uniform(0.3, 0.7)) for _ in range(34)]
    logo = Image.open(LOGO).convert("RGBA")          # official file, untouched, directly on the dark scene
    A["logo"] = logo.resize((420, round(logo.height * 420 / logo.width)), Image.LANCZOS)
    A["logo_s"] = logo.resize((300, round(logo.height * 300 / logo.width)), Image.LANCZOS)

    A["h_six"] = T("6", dms(420), "gilt")
    A["h_open"] = T("openings", cor(190), IVORY)
    A["h_week"] = T("NEXT WEEK  ·  FOR YOU", lex(36, 500), IVORY, tracking=12)
    A["clinic"] = T(CLINIC.upper(), lex(34, 500), IVORY, tracking=8)
    A["addr"] = T(ADDRESS, dms(56, True), "gilt")
    A["day"] = [(T(d, lex(40, 600), IVORY, tracking=16), T(dt, dms(110), IVORY)) for d, dt, _ in DAYS]
    A["times"] = [[(T(tm, dms(230), "gilt"), T(ap, lex(54, 400), IVORY, tracking=2)) for tm, ap in ts] for _, _, ts in DAYS]
    A["svc_h"] = T("treatments", cor(170), "gilt")
    A["svc"] = [T(s_, dms(84), IVORY) for s_ in SERVICES]
    A["s_title"] = T("Available appointments", cor(130), "gilt")
    A["s_day"] = [T(f"{d}, {dt.upper()}", lex(30, 600), IVORY, tracking=6) for d, dt, _ in DAYS]
    A["s_t"] = [[(T(tm, dms(84), "gilt"), T(ap, lex(30, 400), IVORY)) for tm, ap in ts] for _, _, ts in DAYS]
    A["s_svc"] = T("Spanish Massage  ·  Foot, Hand & Facial Reflexology", lex(30, 400), IVORY, tracking=1)
    A["s_who"] = T(f"{THERAPIST}  ·  {ADDRESS}", lex(30, 500), IVORY, tracking=1)
    A["s_cta"] = T("DM TO BOOK", lex(52, 600), IVORY, tracking=18)
    return A


def fade(t, s, e, fi=0.5, fo=0.45):
    return ease_out(prog(t, s, fi)) * (1 - ease_in_out(prog(t, e - fo, fo)))


REV = {0: [7.9, 9.7], 1: [13.9, 15.1, 16.3, 17.5]}   # time reveals


def frame_at(t, A):
    soften = sum(math.exp(-((t - r) / 0.3) ** 2) for rs in REV.values() for r in rs) * 0.7
    f = background(A, t, soften)
    cx = W / 2
    # 1 · hook 0–3.4: big gold "6" from blur, script "openings", small line
    if t < 3.6:
        a = fade(t, 0.0, 3.5, 0.3)
        sharp_in(f, A["h_six"], cx - A["h_six"].adv / 2, 900, prog(t, 0.5, 0.9), a, scale_from=1.06, blur=14)
        if t > 1.5:
            put_shine(f, A["h_six"], cx - A["h_six"].adv / 2, 900, a, prog(t, 1.5, 1.4))
        wipe(f, A["h_open"], cx - A["h_open"].adv / 2, 1060, prog(t, 1.0, 0.9), a)
        letters(f, A["h_week"], cx - A["h_week"].adv / 2, 1170, 1.6, t, a, step=0.025)
    # 2 · location 3.4–6.6: logo + clinic + address
    if 3.3 <= t < 6.7:
        a = fade(t, 3.3, 6.6)
        lg = A["logo"]
        p = ease_out(prog(t, 3.4, 0.7))
        put(f, lg, cx - lg.width / 2, 620 + 16 * (1 - p), a * p)
        letters(f, A["clinic"], cx - A["clinic"].adv / 2, 1000, 4.0, t, a, step=0.02)
        rise(f, A["addr"], cx - A["addr"].adv / 2, 1100, prog(t, 4.6, 0.7), a)
    # 3 · Monday (6.6–12.4) and Friday (12.4–19.4): day + date, times as hero reveals in a column
    for k, (s, e) in enumerate(((6.6, 12.4), (12.4, 19.4))):
        if s <= t < e:
            a = fade(t, s, e)
            d, dt = A["day"][k]
            letters(f, d, cx - d.adv / 2, 380, s + 0.1, t, a, step=0.04)
            drop(f, dt, cx - dt.adv / 2, 500, prog(t, s + 0.3, 0.7), a)
            line(f, cx, 540, 300 * ease_in_out(prog(t, s + 0.7, 0.6)), GOLD_LINE, a)
            n = len(A["times"][k])
            step = 250 if n == 2 else 230
            y0 = 820 if n == 2 else 760
            for j, (tm, ap) in enumerate(A["times"][k]):
                tr = REV[k][j]
                tot = tm.adv + 18 + ap.adv
                x = cx - tot / 2
                by = y0 + j * step if n == 2 else 720 + j * 215
                sharp_in(f, tm, x, by, prog(t, tr, 0.7), a, scale_from=0.92 if j % 2 else 1.06, blur=12)
                if t > tr + 0.7:
                    put_shine(f, tm, x, by, a, prog(t, tr + 0.7, 1.0))
                pp = ease_out(prog(t, tr + 0.35, 0.45))
                put_x(f, ap, x + tm.adv + 18, by, a * pp, dx=-20 * (1 - pp))
    # 4 · services 19.4–23.4
    if 19.3 <= t < 23.5:
        a = fade(t, 19.3, 23.4)
        wipe(f, A["svc_h"], cx - A["svc_h"].adv / 2, 560, prog(t, 19.4, 0.8), a)
        for j, sv in enumerate(A["svc"]):
            slide(f, sv, cx - sv.adv / 2, 780 + j * 130, prog(t, 19.9 + j * 0.45, 0.6), a, dx=(-70 if j % 2 == 0 else 70))
    # 5 · summary 23.4–30 (+ blur-out)
    if t >= 23.3:
        a = ease_out(prog(t, 23.4, 0.6))
        wash(f, 250, 1600, NIGHT, 0.35 * a, 0.35 * a)
        lg = A["logo_s"]
        put(f, lg, cx - lg.width / 2, 290, a)
        wipe(f, A["s_title"], cx - A["s_title"].adv / 2, 600, prog(t, 23.6, 0.9))
        y = 720
        for k in range(2):
            dl = A["s_day"][k]
            letters(f, dl, cx - dl.adv / 2, y, 24.1 + k * 0.8, t, step=0.012)
            row = A["s_t"][k]
            gap = 42
            tot = sum(tm.adv + 8 + ap.adv for tm, ap in row) + gap * (len(row) - 1)
            sc = min(1.0, 900 / tot)
            x = cx - tot * sc / 2
            for j, (tm, ap) in enumerate(row):
                pp = ease_out(prog(t, 24.3 + k * 0.8 + j * 0.15, 0.5))
                if sc < 1:
                    tm_i = tm.img.resize((int(tm.w * sc), int(tm.h * sc)), Image.LANCZOS)
                    ap_i = ap.img.resize((int(ap.w * sc), int(ap.h * sc)), Image.LANCZOS)
                    put(f, tm_i, x - tm.pad * sc, y + 105 - tm.asc * sc + 10 * (1 - pp), pp)
                    put(f, ap_i, x + (tm.adv + 8) * sc - ap.pad * sc, y + 105 - ap.asc * sc + 10 * (1 - pp), pp)
                else:
                    put_x(f, tm, x, y + 105, pp, dy=10 * (1 - pp))
                    put_x(f, ap, x + tm.adv + 8, y + 105, pp, dy=10 * (1 - pp))
                x += (tm.adv + 8 + ap.adv + gap) * sc
            y += 210
        line(f, cx, y - 30, 420 * ease_in_out(prog(t, 25.6, 0.6)), GOLD_LINE)
        p = ease_out(prog(t, 25.9, 0.5))
        put_c(f, A["s_svc"], y + 30, p, dy=10 * (1 - p))
        put_c(f, A["s_who"], y + 85, p, dy=10 * (1 - p))
        p = ease_out(prog(t, 26.4, 0.6))
        put_c(f, A["s_cta"], y + 190, p, dy=12 * (1 - p))
        line(f, cx, y + 215, 300 * ease_in_out(prog(t, 26.7, 0.6)), GOLD_LINE, p, thick=2)
    bi = 1 - ease_out(prog(t, 0.0, 1.0))
    bo = ease_in_out(prog(t, DURATION - 1.5, 1.5))
    b = max(bi, bo)
    if b > 0.01:
        f = f.filter(ImageFilter.GaussianBlur(24 * b))
        if bo > 0.01:
            f.alpha_composite(Image.new("RGBA", (W, H), (60, 40, 26, int(90 * bo))))
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
    rng = np.random.default_rng(88)
    out = np.zeros(n)

    def add(at_, sig):
        i = int(at_ * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        k = min(len(sig), n - i)
        out[i:i + k] += sig[:k]
    BPM = 88
    BEAT = 60 / BPM
    BAR = 4 * BEAT
    NT = {"F2": 87.31, "Db2": 69.30, "Ab1": 51.91, "Eb2": 77.78, "F3": 174.61, "Ab3": 207.65, "C4": 261.63, "Eb4": 311.13,
          "Db3": 138.59, "F4": 349.23, "Bb3": 233.08, "G3": 196.0, "Ab4": 415.3, "C5": 523.25, "Eb5": 622.25, "F5": 698.46, "G4": 392.0, "Bb4": 466.16, "Db4": 277.18, "Eb3": 155.56}
    CH = [("F2", ["Ab3", "C4", "Eb4", "G4"]), ("Db2", ["Ab3", "C4", "F4", "Db4"]), ("Ab1", ["Ab3", "C4", "Eb4", "G4"]), ("Eb2", ["G3", "Bb3", "Eb4", "F4"])]
    MEL = ["C5", "Eb5", "F5", "Eb5", "C5", "Ab4", "Bb4", "C5", "Ab4", "F4", "G4", "Ab4", "Bb4", "G4", "Eb4", "F4"]

    def rhodes(f0, L, vel):
        tt = np.arange(L) / sr
        idx = 1.2 * np.exp(-tt * 3) + 0.15
        env = np.exp(-tt * 0.9) * np.clip(tt / 0.006, 0, 1)
        trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * tt)
        return vel * env * trem * np.sin(2 * np.pi * f0 * tt + idx * np.sin(2 * np.pi * f0 * tt))

    def flute(f0, L, vel):
        tt = np.arange(L) / sr
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5 * tt) * np.clip(tt / 0.3, 0, 1)
        ph = 2 * np.pi * f0 * np.cumsum(vib) / sr
        env = np.clip(tt / 0.08, 0, 1) * np.clip((L / sr - tt) / 0.15, 0, 1)
        breath = rng.normal(0, 1, L) * 0.04
        return vel * env * (np.sin(ph) + 0.12 * np.sin(2 * ph) + breath)

    def kick():
        tt = np.arange(int(0.35 * sr)) / sr
        fr = 50 + 60 * np.exp(-tt * 28)
        return np.sin(2 * np.pi * np.cumsum(fr) / sr) * np.exp(-tt * 9)

    def rim():
        L = int(0.06 * sr)
        tt = np.arange(L) / sr
        return (np.sin(2 * np.pi * 1700 * tt) * 0.6 + rng.normal(0, 1, L) * 0.4) * np.exp(-tt * 70)
    nb = int(DURATION / BAR) + 1
    for b in range(nb):
        root, voi = CH[b % 4]
        t0 = b * BAR
        for nn in voi:
            add(t0 + 0.02, rhodes(NT[nn], int(BAR * sr * 1.1), 0.09))
        add(t0 + 2.5 * BEAT, rhodes(NT[voi[-1]], int(1.2 * sr), 0.06))
        tt = np.arange(int(BAR * sr)) / sr
        add(t0, 0.32 * np.sin(2 * np.pi * NT[root] * tt) * np.exp(-tt * 0.7))
        if t0 > 3.0:
            add(t0, 0.5 * kick())
            add(t0 + 2.5 * BEAT, 0.35 * kick())
            for beat in (1, 3):
                add(t0 + beat * BEAT + 0.015, 0.16 * rim())
        if 6.0 < t0 < 26:
            for j in range(4):
                add(t0 + j * BEAT, flute(NT[MEL[(b * 4 + j) % 16]], int(BEAT * 0.95 * sr), 0.06))
    for tr in REV[0] + REV[1] + [0.5, 3.4, 23.5]:
        tt = np.arange(int(2.0 * sr)) / sr
        add(tr, 0.07 * np.exp(-tt * 2.8) * (np.sin(2 * np.pi * 2093 * tt) + 0.3 * np.sin(2 * np.pi * 2093 * 2.32 * tt)))
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    X *= np.clip((fr - 2000) / 6000, 0, 1) * np.exp(-fr / 14000)
    hiss = np.fft.irfft(X, n)
    out = out / (np.abs(out).max() + 1e-9) + hiss / np.abs(hiss).max() * 0.012
    wow = (np.arange(n) + 0.0006 * sr * np.sin(2 * np.pi * 0.5 * t)).clip(0, n - 1)
    out = np.interp(wow, np.arange(n), out)
    st = np.stack([out, np.roll(out, int(0.012 * sr))], 1)
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
        for s in [float(x) for x in sys.argv[2:]] or [2.6, 5.6, 11.0, 18.6, 22.6, 27.8]:
            Image.fromarray(frame_at(s, A)).save(os.path.join(OUT_DIR, "qc", f"n23-{s:05.2f}s.png"))
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
    Image.fromarray(frame_at(27.6, A)).save(os.path.join(OUT_DIR, f"{NAME}-story.jpg"), quality=93)
    print(NAME)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
