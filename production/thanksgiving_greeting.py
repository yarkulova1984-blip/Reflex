"""Thanksgiving greeting from Zarina, RCRT — Monday, October 12, 2026 (Canadian Thanksgiving).
Owner's 7 autumn photos, gentle female voiceover with wishes for clients, light music.

Living photos: falling-leaf overlay + branch sway (crate), twinkling string lights + leaf sway,
rising steam (pumpkin pie), sunbeam shimmer + curtain sway (apple pie), dew twinkle (pumpkin),
drifting leaves (forest), dried-flower sway (chalkboard). Camera push / slide / pull.
Palette: cream + pumpkin orange + deep brown + gold. Type: Gloock (display serif) + DM Sans +
Imperial Script (accent). Music (§46, new): 80 BPM, A major, celesta melody, pizzicato strings,
soft string swells on scene changes, fireplace crackle; ducks under the voice.

  python3 production/thanks_voice.py
  python3 production/thanksgiving_greeting.py stills | video
"""
import json
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oct16_amt_thanksgiving as base  # noqa: E402
from oct15_pe_thu_sat import ks  # noqa: E402
from oct16_amt_thanksgiving import Text, bilinear, ease_in_out, ease_out, letters, line, prog, put, put_c, sharp_in, wash, wipe  # noqa: E402
from thanks_voice import LINES  # noqa: E402

ROOT = base.ROOT
FONTS = base.FONTS
PH = os.path.join(ROOT, "brand", "photos", "thanksgiving")
AUD = os.path.join(ROOT, "production", "thanks_audio")
OUT_DIR = base.OUT_DIR
NAME = "2026-10-12-thanksgiving-greeting"
W, H, FPS = 1080, 1920, 30

CREAM = (252, 244, 230)
PUMPKIN = (236, 140, 64)
BROWN = (22, 12, 6)
base.GOLDS["harvest"] = ((252, 228, 180), (226, 172, 98), (168, 110, 48))

_d = json.load(open(os.path.join(AUD, "durations.json")))
DUR_L = _d["durations"]
LEAD, GAP, TAIL = 0.5, 0.75, 4.3
STARTS = []
_t = LEAD
for d in DUR_L:
    STARTS.append(_t)
    _t += d + GAP
DURATION = round(_t - GAP + TAIL, 2)
END = [s + d for s, d in zip(STARTS, DUR_L)]


def wt(i, word):
    s = LINES[i]
    return STARTS[i] + DUR_L[i] * max(0, s.lower().find(word.lower())) / len(s) * 0.97


def gloock(size):
    return ImageFont.truetype(os.path.join(FONTS, "Gloock-Regular.ttf"), size)


def dms(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "DMSans[opsz,wght].ttf"), size)
    f.set_variation_by_axes([14, wght])
    return f


def script(size):
    return ImageFont.truetype(os.path.join(FONTS, "ImperialScript-Regular.ttf"), size)


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=BROWN)


# ---------------------------------------------------------------- photos
# key: (file, fx, sway boxes (u0,v0,u1,v1), steam box)
PHOTOS = {
    "crate": ("happy-thanksgiving-crate.jpg", "leaves", [(0.0, 0.0, 1.0, 0.22)], None),
    "lights": ("maple-leaf-lights.jpg", "twinkle", [(0.05, 0.0, 0.85, 0.95)], None),
    "pumpkinpie": ("pumpkin-pie-steam.jpg", "steam", [], (0.36, 0.0, 0.62, 0.22)),
    "applepie": ("apple-pie-window.jpg", "sun", [(0.5, 0.0, 1.0, 0.45)], None),
    "dew": ("dewy-pumpkin.jpg", "twinkle", [(0.0, 0.0, 1.0, 0.55)], None),
    "forest": ("falling-leaves.jpg", "leaves", [(0.0, 0.0, 1.0, 0.8)], None),
    "chalk": ("chalkboard-thanksgiving.jpg", None, [(0.55, 0.0, 1.0, 0.45), (0.0, 0.3, 0.2, 0.7)], None),
}


def _blurL(a, r):
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(r)), np.float32)


def build_photo(key):
    fn, fx, sways, steam = PHOTOS[key]
    im = Image.open(os.path.join(PH, fn)).convert("RGB")
    W0, H0 = im.size
    k = max(W / W0, H / H0) * 1.12
    big = im.resize((int(W0 * k), int(H0 * k)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.0, percent=55, threshold=2))
    arr = np.asarray(big, np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    P = {"arr": arr, "w": w, "h": h, "fx": fx}
    sw = np.zeros((h, w), np.float32)
    for (u0, v0, u1, v1) in sways:
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).rectangle((u0 * w, v0 * h, u1 * w, v1 * h), fill=255)
        sw += np.asarray(m.filter(ImageFilter.GaussianBlur(60)), np.float32) / 255
    P["sway"] = sw if sways else None
    if fx == "twinkle":
        lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
        P["spec"] = _blurL(np.clip(lum - _blurL(lum, 6) - 12, 0, 70) / 70 * 255, 1.5) / 255
        rng = np.random.default_rng(len(key))
        P["phase"] = _blurL(rng.uniform(0, 255, (h, w)), 8) / 255 * 6.28 * 3
    if fx == "steam":
        u0, v0, u1, v1 = steam
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).ellipse((u0 * w, v0 * h, u1 * w, v1 * h * 1.3), fill=255)
        P["smask"] = np.asarray(m.filter(ImageFilter.GaussianBlur(70)), np.float32) / 255
        rng = np.random.default_rng(5)
        small = rng.normal(0, 1, (h // 40, w // 40)).astype(np.float32)
        P["wisp"] = np.clip(np.asarray(Image.fromarray(small, "F").resize((w, h * 2), Image.BICUBIC), np.float32), 0, None)
    if fx == "sun":
        d = (xx / w * 0.75 + yy / h * 0.65) - 0.35
        P["beam"] = np.exp(-(d / 0.16) ** 2)
    return P


def render_photo(P, t, u, v, z):
    s = max(W / P["w"], H / P["h"])
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * P["w"], cw / 2), P["w"] - cw / 2)
    cy = min(max(v * P["h"], ch / 2), P["h"] - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    ix = np.clip(gx.astype(np.int32), 0, P["w"] - 1)
    iy = np.clip(gy.astype(np.int32), 0, P["h"] - 1)
    if P["sway"] is not None:
        wg = P["sway"][iy, ix]
        gx = gx + wg * (4.5 * np.sin(1.0 * t + gy * 0.005) + 2.0 * np.sin(2.2 * t + gx * 0.008))
        gy = gy + wg * (2.2 * np.sin(1.3 * t + gx * 0.006))
    if P["fx"] == "steam":
        m = P["smask"][iy, ix]
        gx = gx + m * (8 * np.sin(gy * 0.012 - t * 1.4) + 4 * np.sin(gy * 0.03 - t * 2.3))
    img = bilinear(P["arr"], gx, gy)
    if P["fx"] == "twinkle":
        tw = np.clip(np.sin(2.4 * t + P["phase"][iy, ix]), 0, 1) ** 3
        img = img + (P["spec"][iy, ix] * tw)[..., None] * np.array([150, 118, 70], np.float32)
    if P["fx"] == "steam":
        off = int((t * 60) % P["h"])
        wv = P["wisp"][(iy + off) % P["wisp"].shape[0], ix] * P["smask"][iy, ix]
        img = img + (wv * 30)[..., None] * np.array([1.0, 0.95, 0.9], np.float32)
    if P["fx"] == "sun":
        b = P["beam"][iy, ix][..., None]
        img = img * (1 + 0.10 * b * (0.8 + 0.2 * math.sin(t * 0.9))) + b * np.array([30, 18, 4], np.float32) * (0.6 + 0.4 * math.sin(t * 0.7))
    return img


def tw(i, word, lead=0.0):
    return wt(i, word) - lead


SHOTS = [  # (key, start, end, camera keys)
    ("crate", 0.0, STARTS[1] - 0.2, [(0.0, 0.5, 0.50, 1.12), (STARTS[1] - 0.2, 0.5, 0.52, 1.02)]),
    ("lights", STARTS[1] - 0.6, STARTS[2] - 0.2, [(STARTS[1] - 0.6, 0.45, 0.50, 1.04), (STARTS[2] - 0.2, 0.52, 0.48, 1.14)]),
    ("pumpkinpie", STARTS[2] - 0.6, tw(2, "your home") - 0.1, [(STARTS[2] - 0.6, 0.5, 0.52, 1.02), (tw(2, "your home") - 0.1, 0.5, 0.55, 1.12)]),
    ("applepie", tw(2, "your home") - 0.5, tw(2, "your heart") - 0.1, [(tw(2, "your home") - 0.5, 0.42, 0.55, 1.10), (tw(2, "your heart") - 0.1, 0.56, 0.55, 1.10)]),
    ("dew", tw(2, "your heart") - 0.5, STARTS[3] - 0.2, [(tw(2, "your heart") - 0.5, 0.5, 0.40, 1.12), (STARTS[3] - 0.2, 0.5, 0.44, 1.02)]),
    ("forest", STARTS[3] - 0.6, STARTS[4] - 0.2, [(STARTS[3] - 0.6, 0.5, 0.45, 1.02), (STARTS[4] - 0.2, 0.5, 0.52, 1.14)]),
    ("chalk", STARTS[4] - 0.6, DURATION, [(STARTS[4] - 0.6, 0.5, 0.44, 1.14), (DURATION, 0.5, 0.46, 1.02)]),
]


def cam(keys, t):
    if t <= keys[0][0]:
        return keys[0][1:]
    (t0, *a), (t1, *b) = keys[0], keys[-1]
    e = ease_in_out((t - t0) / (t1 - t0))
    return tuple(x + (y - x) * e for x, y in zip(a, b))


def maple_leaf(size, color, seed):
    """Stylised maple leaf silhouette (graphic foreground element, softly blurred for depth)."""
    S = size * 2
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    pts = []
    for kk in range(360):
        th = math.radians(kk)
        r = 0.42 + 0.16 * abs(math.sin(2.5 * th)) ** 0.5 - 0.10 * (abs(math.sin(5 * th)) ** 4)
        if 160 < kk < 200:
            r *= 0.55
        pts.append((S / 2 + S * r * math.sin(th) * 0.95, S / 2 - S * r * math.cos(th) * 0.95))
    ImageDraw.Draw(im).polygon(pts, fill=color + (235,))
    ImageDraw.Draw(im).line([(S / 2, S / 2), (S / 2, S * 0.98)], fill=color + (235,), width=max(2, S // 40))
    return im.resize((size, size), Image.LANCZOS)


def build():
    A = {"P": {k: build_photo(k) for k in PHOTOS}}
    rng = np.random.default_rng(12)
    A["grain"] = [rng.normal(0, 2.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.24 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    cols = [(214, 110, 40), (190, 76, 30), (232, 160, 60), (160, 60, 26)]
    A["leaf_imgs"] = []
    for i in range(10):
        sz = int(rng.uniform(46, 120))
        im = maple_leaf(sz, cols[i % 4], i)
        if sz > 90:
            im = im.filter(ImageFilter.GaussianBlur(5))      # close to the lens: out of focus
        A["leaf_imgs"].append(im)
    A["leaves"] = [(rng.uniform(0, W), rng.uniform(-H, 0), rng.uniform(60, 140), rng.uniform(0, 6.28), rng.uniform(30, 90), i % 10) for i in range(14)]

    A["date"] = T("MONDAY  ·  OCTOBER 12", dms(34, 700), CREAM, tracking=10)
    A["thank"] = T("Thank you", gloock(170), "harvest")
    A["thank_sub"] = T("for trusting me with your care this year", dms(40, 500), CREAM, tracking=1)
    A["w1"] = T("May your table be full,", gloock(86), CREAM)
    A["w2"] = T("your home be warm,", gloock(96), CREAM)
    A["w3"] = T("and your heart be light.", gloock(86), "harvest")
    A["rest"] = [T(w, gloock(118), CREAM) for w in ("Rest.", "Slow down.")]
    A["enjoy"] = T("Enjoy every moment", gloock(96), "harvest")
    A["loved"] = T("with the people you love", script(104), CREAM)
    A["grat"] = T("With gratitude,", script(140), "harvest")
    A["zarina"] = T("Zarina, RCRT", gloock(110), CREAM)
    A["ht"] = T("HAPPY THANKSGIVING", dms(34, 700), CREAM, tracking=12)
    A["ig"] = T("@yourspanish_massage", dms(34, 600), CREAM, tracking=1)
    return A


def leaves_overlay(f, A, t, a):
    for (x0, y0, spd, ph, amp, k) in A["leaves"]:
        im = A["leaf_imgs"][k]
        y = (y0 + spd * t) % (H + 300) - 150
        x = x0 + amp * math.sin(t * 0.8 + ph)
        rot = math.degrees(math.sin(t * 1.1 + ph) * 0.9)
        r = im.rotate(rot, resample=Image.BICUBIC, expand=True)
        put(f, r, x - r.width / 2, y - r.height / 2, a * 0.92)


def frame_at(t, A):
    act = [i for i, (_, s, e, _) in enumerate(SHOTS) if s - 1e-3 <= t <= e]
    imgs = []
    for i in act:
        key, s, e, keys = SHOTS[i]
        imgs.append(render_photo(A["P"][key], t, *cam(keys, t)))
    if len(act) >= 2:
        i2 = act[-1]
        p = (t - SHOTS[i2][1]) / max(1e-3, SHOTS[act[-2]][2] - SHOTS[i2][1])
        a = Image.fromarray(np.clip(imgs[-2], 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12 * p))
        b = Image.fromarray(np.clip(imgs[-1], 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12 * (1 - p)))
        img = np.asarray(Image.blend(a, b, ease_in_out(p)), np.float32)
    else:
        img = imgs[0]
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    cur = act[-1]
    key = SHOTS[cur][0]

    # 1 · crate (the photo already says "Happy Thanksgiving")
    if t < SHOTS[1][1] + 0.4:
        a = 1 - ease_in_out(prog(t, SHOTS[1][1], 0.4))
        wash(f, 0, 520, BROWN, 0.55 * a, 0.0)
        letters(f, A["date"], W / 2 - A["date"].adv / 2, 230, 0.4, t, a, step=0.03)
        leaves_overlay(f, A, t, a)
    # 2 · lights: thank you
    s, e = SHOTS[1][1], SHOTS[1][2]
    if s <= t < e + 0.3:
        a = ease_out(prog(t, s + 0.2, 0.5)) * (1 - ease_in_out(prog(t, e - 0.2, 0.4)))
        wash(f, 1200, H, BROWN, 0.0, 0.75 * a)
        sharp_in(f, A["thank"], W / 2 - A["thank"].adv / 2, 1560, prog(t, STARTS[1] + 0.2, 0.8), a, scale_from=1.08, blur=14)
        wipe(f, A["thank_sub"], W / 2 - A["thank_sub"].adv / 2, 1650, prog(t, STARTS[1] + 0.9, 1.0), a)
    # 3–5 · the three wishes, one per photo
    for k, (key_, word, y, txt) in enumerate((("pumpkinpie", "May your", 1650, "w1"), ("applepie", "your home", 1700, "w2"),
                                              ("dew", "your heart", 330, "w3"))):
        s, e = SHOTS[2 + k][1], SHOTS[2 + k][2]
        if s <= t < e + 0.3:
            a = ease_out(prog(t, s + 0.15, 0.4)) * (1 - ease_in_out(prog(t, e - 0.15, 0.35)))
            if y > 900:
                wash(f, 1250, H, BROWN, 0.0, 0.78 * a)
            else:
                wash(f, 0, 650, BROWN, 0.7 * a, 0.0)
            tx = A[txt]
            sharp_in(f, tx, W / 2 - tx.adv / 2, y, prog(t, tw(2, word, 0.15), 0.6), a, blur=10)
    # 6 · forest: rest, slow down, enjoy
    s, e = SHOTS[5][1], SHOTS[5][2]
    if s <= t < e + 0.3:
        a = ease_out(prog(t, s + 0.2, 0.4)) * (1 - ease_in_out(prog(t, e - 0.2, 0.35)))
        wash(f, 0, H, BROWN, 0.38 * a, 0.38 * a)
        leaves_overlay(f, A, t, a * 0.35)
        for k, w_ in enumerate(("rest", "slow down")):
            sharp_in(f, A["rest"][k], W / 2 - A["rest"][k].adv / 2, 620 + k * 140, prog(t, tw(3, w_, 0.1), 0.5), a, blur=10)
        wipe(f, A["enjoy"], W / 2 - A["enjoy"].adv / 2, 900, prog(t, tw(3, "enjoy", 0.1), 0.8), a)
        wipe(f, A["loved"], W / 2 - A["loved"].adv / 2, 1040, prog(t, tw(3, "people", 0.2), 0.9), a)
    # 7 · signature
    s = SHOTS[6][1]
    if t >= s:
        a = ease_out(prog(t, s + 0.2, 0.6))
        wash(f, 1150, H, BROWN, 0.0, 0.82 * a)
        wipe(f, A["grat"], W / 2 - A["grat"].adv / 2, 1450, prog(t, STARTS[4], 1.0), a)
        sharp_in(f, A["zarina"], W / 2 - A["zarina"].adv / 2, 1590, prog(t, wt(4, "Zarina"), 0.7), a, blur=12)
        line(f, W / 2, 1630, 300 * ease_in_out(prog(t, wt(4, "Zarina") + 0.4, 0.6)), (226, 172, 98), a)
        letters(f, A["ht"], W / 2 - A["ht"].adv / 2, 1705, END[4] + 0.2, t, a, step=0.02)
        p = ease_out(prog(t, END[4] + 0.9, 0.5))
        put_c(f, A["ig"], 1775, p * a, dy=12 * (1 - p))
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


# ---------------------------------------------------------------- music (§46 new)
BPM = 80
BEAT = 60 / BPM
BAR = 4 * BEAT
NT = {"A2": 110.0, "F#2": 92.5, "D2": 73.42, "E2": 82.41, "C#4": 277.18, "E4": 329.63, "G#4": 415.3, "A4": 440.0,
      "B4": 493.88, "C#5": 554.37, "D5": 587.33, "E5": 659.25, "F#5": 739.99, "G#5": 830.61, "A5": 880.0, "F#4": 369.99, "D4": 293.66}
CH = [("A2", ["C#4", "E4", "G#4"]), ("F#2", ["C#4", "E4", "A4"]), ("D2", ["D4", "F#4", "A4"]), ("E2", ["E4", "G#4", "B4"])]
MEL = ["E5", "C#5", "B4", "C#5", "A4", "B4", "C#5", "E5", "F#5", "E5", "D5", "C#5", "B4", "G#4", "B4", "E5"]


def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(80)
    voice = np.zeros(n)
    for i, st in enumerate(STARTS):
        v, vsr = sf.read(os.path.join(AUD, f"line{i + 1}.wav"))
        if v.ndim > 1:
            v = v.mean(1)
        if vsr != sr:   # Kokoro renders at 24 kHz: resample to the mix rate (otherwise the voice plays 2x fast)
            v = np.interp(np.arange(int(len(v) * sr / vsr)) * vsr / sr, np.arange(len(v)), v)
        a0 = int(st * sr)
        m = min(len(v), n - a0)
        voice[a0:a0 + m] += v[:m]
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.92
    mus = np.zeros(n)

    def add(at, sig, buf=mus):
        i = int(at * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        m = min(len(sig), n - i)
        buf[i:i + m] += sig[:m]

    def celesta(f0, vel):
        tt = np.arange(int(1.8 * sr)) / sr
        env = np.exp(-tt * 2.6) * np.clip(tt / 0.003, 0, 1)
        return vel * env * (np.sin(2 * np.pi * f0 * tt) + 0.3 * np.sin(2 * np.pi * 2 * f0 * tt) * np.exp(-tt * 5) + 0.12 * np.sin(2 * np.pi * 4 * f0 * tt) * np.exp(-tt * 9))

    seed = 0
    nb = int(DURATION / BAR) + 1
    for b in range(nb):
        root, voi = CH[b % 4]
        t0 = b * BAR
        for beat in range(4):          # pizzicato: root on 1 and 3, chord tones on 2 and 4
            seed += 1
            f0 = NT[root] * (2 if beat % 2 == 0 else 3)
            add(t0 + beat * BEAT, 0.35 * ks(f0, 0.9, sr, bright=0.25, decay=0.985, seed=seed))
        for j in range(4):             # celesta melody, two notes per beat on the off-beats
            add(t0 + j * BEAT + BEAT / 2, celesta(NT[MEL[(b * 4 + j) % len(MEL)]], 0.16))
        # soft strings
        L = int((BAR + 1.2) * sr)
        tt = np.arange(L) / sr
        env = np.clip(tt / 1.2, 0, 1) * np.clip((BAR + 1.2 - tt) / 1.0, 0, 1)
        for nn in voi:
            f0 = NT[nn] / 2
            add(t0 - 0.3, 0.05 * env * sum((0.6 / k) * np.sin(2 * np.pi * k * f0 * tt + 0.2 * np.sin(2 * np.pi * 5 * tt)) for k in range(1, 5)))
    # string swells into each scene change
    for (_, s, _, _) in SHOTS[1:]:
        L = int(1.2 * sr)
        tt = np.arange(L) / sr
        sw = (tt / 1.2) ** 2 * np.sin(2 * np.pi * NT["E4"] * tt) * 0.08
        add(s - 0.9, sw)
    # fireplace crackle
    fire = np.zeros(n)
    for at in rng.uniform(0, DURATION, 300):
        L = int(rng.uniform(0.003, 0.012) * sr)
        add(at, rng.normal(0, 1, L) * np.exp(-np.arange(L) / (L / 4)) * rng.uniform(0.04, 0.2), fire)
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    X *= np.exp(-((np.log(fr + 1) - np.log(300)) / 0.8) ** 2)
    rumble = np.fft.irfft(X, n)
    fire += rumble / np.abs(rumble).max() * 0.05
    music = mus / (np.abs(mus).max() + 1e-9) + 0.5 * fire
    env = np.convolve(np.abs(voice), np.ones(int(0.25 * sr)) / int(0.25 * sr), mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    gain = 0.30 - 0.16 * env
    st = np.stack([voice + music * gain, voice + np.roll(music, int(0.01 * sr)) * gain], 1)
    st *= (np.clip((DURATION - t) / 2.0, 0, 1) * np.clip(t / 0.1, 0, 1))[:, None]
    st = st / np.max(np.abs(st)) * 10 ** (-1.5 / 20)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def main(mode):
    os.makedirs(OUT_DIR, exist_ok=True)
    if mode == "stills":
        A = build()
        ts = [float(x) for x in sys.argv[2:]] or [1.4, STARTS[1] + 2.5, tw(2, "table") + 0.5, tw(2, "home") + 0.6,
                                                    tw(2, "heart") + 0.7, STARTS[3] + 4.0, DURATION - 0.6]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(OUT_DIR, "qc", f"tg-{s:05.2f}s.png"))
        print([round(x, 2) for x in ts], DURATION)
        return
    tmp = os.path.join(OUT_DIR, f".{NAME}.render.mp4")
    wav = os.path.join(OUT_DIR, f".{NAME}.wav")
    synth_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-profile:v", "high",
           "-level", "4.1", "-pix_fmt", "yuv420p", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4, initializer=_init) as pool:
        for buf in pool.imap(_render, range(int(DURATION * FPS)), chunksize=4):
            proc.stdin.write(buf)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    os.replace(tmp, os.path.join(OUT_DIR, f"{NAME}.mp4"))
    A = build()
    Image.fromarray(frame_at(1.4, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(NAME, DURATION)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
