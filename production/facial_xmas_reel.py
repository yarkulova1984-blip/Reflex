"""Reel — "The best gift this Christmas isn't under the tree." — The Pure Escape.
Facial Reflexology (Bergman Method) + Hand Reflexology, finished with Chanel skincare · 75 min · $145
· Christmas gift certificates (DM).

Voice (§47.8): ElevenLabs Zara via json2video (production/zara_tts.py), timed with faster-whisper word
timestamps (production/facial_xmas_audio/words.json).
Footage: owner's clips (café steps, café friends with phone, Zarina at the skincare shelf) + stills
(facial reflexology ×2, friends leaving the café, mirror portrait) + the hand-reflexology clip.
Living layers: falling snow + warm bokeh, champagne light sweeps, glowing reflex points that pulse on
the brows (reflexology concepts, owner's Bergman training map), presses with ripples.
Type (new pairing): Prata (display serif) + Questrial (sans) + Monsieur La Doulaise (script accent).
Music (§46, new): E major, 76 BPM, glockenspiel melody, "ahh" choir pad, sleigh-bell shaker,
soft handbells on reveals, warm sub; ducks under the voice.

  python3 production/facial_xmas_reel.py stills [t ...]
  python3 production/facial_xmas_reel.py video
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
from doctor_story_reel import Clip, crop_zoom, put_shine, drop, slide, flick  # noqa: E402
from oct16_amt_thanksgiving import Text, bilinear, ease_in_out, ease_out, letters, line, prog, put, put_c, put_x, rise, sharp_in, wash, wipe  # noqa: E402
import doctor_story_reel as dsr  # noqa: E402

ROOT = base.ROOT
FONTS = base.FONTS
FX = os.path.join(ROOT, "brand", "photos", "facial-xmas")
AUD = os.path.join(ROOT, "production", "facial_xmas_audio")
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
dsr.FR = "/tmp/claude-0/-home-user-Reflex/f74b54ed-c929-5941-94f0-7201420216f3/scratchpad/fx_frames"
OUT_DIR = base.OUT_DIR
NAME = "2026-11-facial-hand-chanel-christmas"
W, H, FPS = 1080, 1920, 30
WORDS = json.load(open(os.path.join(AUD, "words.json")))
VOICE_END = WORDS[-1]["e"]
DURATION = round(VOICE_END + 2.8, 1)

IVORY = (252, 247, 238)
NIGHT = (14, 9, 8)
AQUA = (150, 236, 222)
GOLD_LINE = (226, 194, 136)
base.GOLDS["champ"] = ((252, 238, 208), (226, 194, 140), (168, 130, 78))


def at(word, after=0.0):
    w0 = word.lower().strip(".,?!")
    for w in WORDS:
        if w["s"] >= after - 0.05 and w["w"].lower().strip(".,?!'s") == w0.strip("'s"):
            return w["s"]
    raise KeyError(word)


def prata(size):
    return ImageFont.truetype(os.path.join(FONTS, "Prata-Regular.ttf"), size)


def quest(size):
    return ImageFont.truetype(os.path.join(FONTS, "Questrial-Regular.ttf"), size)


def scr(size):
    return ImageFont.truetype(os.path.join(FONTS, "MonsieurLaDoulaise-Regular.ttf"), size)


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT)


# ---------------------------------------------------------------- scenes (from the voice timing)
SCENES = [
    ("still", "steps", 0.0, 3.05, {}),
    ("clip", "c-cafe-phone", 2.85, 6.25, {"src": 0.6, "speed": 1.0, "z0": 1.0, "z1": 1.06}),
    ("clip", "c-shelf", 6.05, 11.45, {"src": 0.0, "speed": 0.95, "z0": 1.04, "z1": 1.0}),
    ("still", "between", 11.25, 22.10, {}),
    ("still", "brows", 21.90, 27.10, {}),
    ("clip", "c9-hand", 26.90, 32.00, {"src": 0.3, "speed": 0.95, "z0": 1.0, "z1": 1.06}),
    ("clip", "c-steps", 31.80, 40.80, {"src": 0.0, "speed": 0.55, "z0": 1.0, "z1": 1.05}),
    ("still", "friends", 40.60, 44.60, {}),
    ("still", "mirror", 44.40, DURATION, {}),
]
STILLS = {"steps": "steps-coffee.png", "between": "facial-between-brows.png", "brows": "facial-brows.png",
          "friends": "friends-leaving.png", "mirror": "mirror.png"}
CAMS = {"steps": (0.5, 0.40, 1.08, 1.0), "between": (0.70, 0.62, 1.55, 1.75), "brows": (0.55, 0.60, 1.30, 1.15),
        "friends": (0.5, 0.40, 1.0, 1.08), "mirror": (0.66, 0.42, 1.12, 1.02)}
# reflex points on facial-between-brows.png (source pixels; reflexology concepts, owner's Bergman map)
PIT = (846, 806)
BROW = [(765, 803), (800, 797), (890, 801), (935, 807), (976, 826)]


def build_still(key):
    im = Image.open(os.path.join(FX, "stills", STILLS[key])).convert("RGB")
    k = max(W / im.width, H / im.height) * 1.1
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 50, 2))
    return {"arr": np.asarray(big, np.float32), "w": big.width, "h": big.height, "k": k}


def cam_window(S, key, p):
    u, v, z0, z1 = CAMS[key]
    z = z0 + (z1 - z0) * ease_in_out(p)
    w, h = S["w"], S["h"]
    s = max(W / w, H / h)
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * w, cw / 2), w - cw / 2)
    cy = min(max(v * h, ch / 2), h - ch / 2)
    return cx - cw / 2, cy - ch / 2, cw / W


def to_screen(S, key, p, x, y):
    x0, y0, sc = cam_window(S, key, p)
    return (x * S["k"] - x0) / sc, (y * S["k"] - y0) / sc


def render_still(key, S, t, p, presses=()):
    x0, y0, sc = cam_window(S, key, p)
    gx = x0 + np.arange(W, dtype=np.float32)[None, :].repeat(H, 0) * sc
    gy = y0 + np.arange(H, dtype=np.float32)[:, None].repeat(W, 1) * sc
    shade = None
    for (px, py, amt, rad) in presses:
        if amt < 0.01:
            continue
        bx, by = px * S["k"], py * S["k"]
        dx, dy = gx - bx, gy - by
        f = np.exp(-(dx * dx + dy * dy) / (rad * rad)) * amt
        gx, gy = gx + dx * f * 0.18, gy + dy * f * 0.18
        shade = (1 - 0.08 * f) if shade is None else shade * (1 - 0.08 * f)
    img = bilinear(S["arr"], gx, gy)
    if shade is not None:
        img = img * shade[..., None]
    return img


def scene_frame(A, i, t):
    kind, key, s, e, ex = SCENES[i]
    p = min(1.0, max(0.0, (t - s) / (e - s)))
    if kind == "clip":
        cl = A["clips"][key]
        fr = cl.frame(ex["src"] + (t - s) * ex["speed"])
        gx, gy = crop_zoom(fr, ex["z0"] + (ex["z1"] - ex["z0"]) * ease_in_out(p))
        return bilinear(fr, gx, gy)
    presses = []
    if key == "between":
        S = A["S"][key]
        for (x, y), t0 in [(PIT, at("pituitary") - 0.1)] + [(b, at("occipital") - 0.3 + 0.35 * j) for j, b in enumerate(BROW)]:
            presses.append((x, y, math.exp(-((t - t0 - 0.3) / 0.3) ** 2), 26 * S["k"]))
    return render_still(key, A["S"][key], t, p, presses)


def background(A, t):
    act = [i for i, sc in enumerate(SCENES) if sc[2] - 1e-3 <= t <= sc[3] + 1e-3]
    if len(act) >= 2:
        i1, i2 = act[-2], act[-1]
        p = (t - SCENES[i2][2]) / max(1e-3, SCENES[i1][3] - SCENES[i2][2])
        a = Image.fromarray(np.clip(scene_frame(A, i1, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10 * p))
        b = Image.fromarray(np.clip(scene_frame(A, i2, t), 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10 * (1 - p)))
        img = np.asarray(Image.blend(a, b, ease_in_out(p)), np.float32)
    else:
        img = scene_frame(A, act[0], t)
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    f = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # Christmas atmosphere: soft snow + a few warm bokeh lights (foreground depth)
    for (x, y, spd, ph, a, k) in A["snow"]:
        sx = x + 22 * math.sin(t * 0.6 + ph)
        sy = (y + spd * t) % (H + 60) - 30
        put(f, A["flake"][k], sx, sy, a)
    for (x, y, r, ph) in A["bokeh"]:
        put(f, A["bk"][r], x + 30 * math.sin(t * 0.2 + ph) - r, y + 20 * math.cos(t * 0.17 + ph) - r, 0.18 + 0.1 * math.sin(t + ph))
    return f, act


def glow_dot(r, color):
    S = int(r * 6)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse((S / 2 - r * 1.6, S / 2 - r * 1.6, S / 2 + r * 1.6, S / 2 + r * 1.6), fill=150)
    im = Image.new("RGBA", (S, S), color + (0,))
    im.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.9)))
    ImageDraw.Draw(im).ellipse((S / 2 - r * 0.55, S / 2 - r * 0.55, S / 2 + r * 0.55, S / 2 + r * 0.55), fill=(255, 255, 255, 235))
    return im


def ring(f, x, y, r, color, a):
    if a < 0.02:
        return
    S = int(2 * r + 12)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((6, 6, S - 6, S - 6), outline=color + (int(255 * a),), width=2)
    f.alpha_composite(im, (int(x - S / 2), int(y - S / 2)))


def point(f, A, x, y, t, t0):
    if t < t0:
        return
    p = ease_out(prog(t, t0, 0.45))
    s = p * (0.84 + 0.16 * math.sin((t - t0) * 3.1))
    d = A["dot"]
    im = d.resize((max(1, int(d.width * s)), max(1, int(d.height * s))), Image.LANCZOS)
    put(f, im, x - im.width / 2, y - im.height / 2, p)
    for k in range(2):
        rp = prog(t, t0 + 0.25 * k, 1.0)
        if 0 < rp < 1:
            ring(f, x, y, 12 + 44 * ease_out(rp), AQUA, (1 - rp) * 0.8)


def build():
    A = {"clips": {k: Clip(k) for k in {sc[1] for sc in SCENES if sc[0] == "clip"}},
         "S": {k: build_still(k) for k in {sc[1] for sc in SCENES if sc[0] == "still"}}}
    rng = np.random.default_rng(25)
    A["grain"] = [rng.normal(0, 2.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.24 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    A["flake"] = {}
    for k in (3, 5, 8):
        m = Image.new("L", (k * 4, k * 4), 0)
        ImageDraw.Draw(m).ellipse((k, k, 3 * k, 3 * k), fill=230)
        im = Image.new("RGBA", m.size, (255, 255, 255, 0))
        im.putalpha(m.filter(ImageFilter.GaussianBlur(k * 0.5 + (2 if k == 8 else 0))))
        A["flake"][k] = im
    A["snow"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(40, 120), rng.uniform(0, 6.28), rng.uniform(0.25, 0.7), int(rng.choice([3, 5, 8]))) for _ in range(70)]
    A["bk"] = {}
    for r in (40, 70):
        m = Image.new("L", (2 * r, 2 * r), 0)
        ImageDraw.Draw(m).ellipse((r * 0.2, r * 0.2, r * 1.8, r * 1.8), fill=160)
        im = Image.new("RGBA", (2 * r, 2 * r), (255, 214, 150, 0))
        im.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.25)))
        A["bk"][r] = im
    A["bokeh"] = [(rng.uniform(0, W), rng.uniform(0, H), int(rng.choice([40, 70])), rng.uniform(0, 6.28)) for _ in range(7)]
    A["dot"] = glow_dot(12, AQUA)
    logo = Image.open(LOGO).convert("RGBA")
    A["logo"] = logo.resize((300, round(logo.height * 300 / logo.width)), Image.LANCZOS)
    pad = 200
    gl = Image.new("L", (A["logo"].width + 2 * pad, A["logo"].height + 2 * pad), 0)
    ImageDraw.Draw(gl).ellipse((pad - 30, pad - 20, gl.width - pad + 30, gl.height - pad + 20), fill=215)
    glow = Image.new("RGBA", gl.size, (252, 246, 236, 0))
    glow.putalpha(gl.filter(ImageFilter.GaussianBlur(55)))
    A["logo_glow"] = glow   # soft edgeless light (no plate, §38) so the black line art reads on the dark third

    A["h1"] = T("The best gift", prata(124), IVORY)
    A["h2"] = T("this Christmas", scr(150), "champ")
    A["h3"] = T("isn't under the tree.", prata(70), IVORY)
    A["time"] = T("It's time.", prata(130), "champ")
    A["for"] = [T(w, scr(130), IVORY) for w in ("for her", "for you")]
    A["fr"] = base.fit(lambda z: T("FACIAL REFLEXOLOGY", quest(z), IVORY, tracking=10), 58, 940)
    A["bm"] = T("Bergman Method", scr(110), "champ")
    A["hr"] = T("+ HAND REFLEXOLOGY", quest(44), IVORY, tracking=10)
    A["ch"] = T("finished with Chanel skincare", prata(52), "champ")
    A["pit"] = T("PITUITARY · HYPOTHALAMUS", quest(34), IVORY, tracking=6)
    A["brw"] = T("OCCIPITAL · EAR · EYE", quest(34), IVORY, tracking=6)
    A["map"] = T("in facial reflexology", scr(96), "champ")
    A["soft"] = T("soften the forehead", prata(84), IVORY)
    A["unw"] = T("unwind", scr(170), "champ")
    A["hands"] = T("then the hands", scr(130), "champ")
    A["pbp"] = T("POINT BY POINT", quest(46), IVORY, tracking=16)
    A["min"] = T("75 MINUTES", quest(52), IVORY, tracking=14)
    A["price"] = T("$145", prata(230), "champ")
    A["glow"] = T("lighter & glowing", scr(118), IVORY)
    A["gift"] = T("Christmas", scr(170), "champ")
    A["gift2"] = T("GIFT CERTIFICATES", quest(54), IVORY, tracking=12)
    A["dm"] = T("SEND ME A DM", quest(40), IVORY, tracking=14)
    A["wpg"] = T("WINNIPEG LUXURY THERAPY", quest(32), IVORY, tracking=10)
    A["zr"] = T("Zarina, RCRT", prata(120), IVORY)
    A["ther"] = T("your reflexology therapist", scr(92), "champ")
    A["addr"] = T("The Pure Escape  ·  698 Corydon Ave, Winnipeg", quest(32), IVORY, tracking=1)
    A["cta"] = T("DM TO BOOK  ·  GIFT CERTIFICATES", quest(36), IVORY, tracking=6)
    return A


def fade(t, s, e, fi=0.4, fo=0.35):
    return ease_out(prog(t, s, fi)) * (1 - ease_in_out(prog(t, e - fo, fo)))


def frame_at(t, A):
    f, act = background(A, t)
    cx = W / 2
    # 1 · hook (0–3)
    if t < 3.1:
        a = fade(t, 0, 3.05, 0.15)
        wash(f, 0, 760, NIGHT, 0.6 * a, 0.0)
        sharp_in(f, A["h1"], cx - A["h1"].adv / 2, 300, prog(t, 0.0, 0.5), a, scale_from=1.1, blur=16)
        p = prog(t, at("Christmas") - 0.2, 0.6)
        if p > 0:
            put_shine(f, A["h2"], cx - A["h2"].adv / 2, 440, a * ease_out(p), prog(t, 1.0, 1.2))
        rise(f, A["h3"], cx - A["h3"].adv / 2, 540, prog(t, at("under") - 0.1, 0.5), a)
    # 2 · time, for her, for you (café)
    if 2.85 <= t < 6.3:
        a = fade(t, 2.85, 6.25)
        wash(f, 1300, H, NIGHT, 0.0, 0.75 * a)
        sharp_in(f, A["time"], cx - A["time"].adv / 2, 1560, prog(t, at("time") - 0.1, 0.5), a, blur=12)
        for k, w in enumerate(("her", "you")):
            p = ease_out(prog(t, at(w) - 0.25, 0.45))
            tx = A["for"][k]
            put_x(f, tx, (cx - 230 if k == 0 else cx + 230) - tx.adv / 2, 1700, a * p, dy=16 * (1 - p))
    # 3 · services (shelf)
    if 6.05 <= t < 11.5:
        a = fade(t, 6.05, 11.45)
        wash(f, 1280, H, NIGHT, 0.0, 0.8 * a)
        letters(f, A["fr"], cx - A["fr"].adv / 2, 1460, at("Facial") - 0.1, t, a, step=0.02)
        wipe(f, A["bm"], cx - A["bm"].adv / 2, 1570, prog(t, at("Bergman") - 0.15, 0.7), a)
        slide(f, A["hr"], cx - A["hr"].adv / 2, 1660, prog(t, at("hand") - 0.1, 0.5), a, dx=90)
        p = prog(t, at("Chanel") - 0.2, 0.6)
        if p > 0:
            put_shine(f, A["ch"], cx - A["ch"].adv / 2, 1760 + 14 * (1 - ease_out(p)), a * ease_out(p), prog(t, at("Chanel") + 0.4, 1.0))
    # 4 · the facial map (between the brows, then along the brows)
    if 11.25 <= t < 22.15:
        a = fade(t, 11.25, 22.1)
        S = A["S"]["between"]
        p = (t - 11.25) / (22.1 - 11.25)
        wash(f, 0, 520, NIGHT, 0.6 * a, 0.0)
        wipe(f, A["map"], cx - A["map"].adv / 2, 220, prog(t, at("In") , 0.8), a)
        tp = at("pituitary") - 0.1
        sx, sy = to_screen(S, "between", p, *PIT)
        point(f, A, sx, sy - 14, t, tp)
        p2 = ease_out(prog(t, tp + 0.2, 0.5)) * (1 - ease_in_out(prog(t, at("Along") - 0.3, 0.3)))
        put_c(f, A["pit"], 360, a * p2, dy=12 * (1 - p2))
        tb = at("occipital") - 0.3
        pts = [to_screen(S, "between", p, *b) for b in BROW]
        for j, (bx, by) in enumerate(pts):
            point(f, A, bx, by - 10, t, tb + 0.35 * j)
        # a fine aqua line traced along each brow
        for seg in (pts[:2], pts[2:]):
            q = ease_in_out(prog(t, tb, 1.4))
            if q > 0 and len(seg) > 1:
                im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                xy = [(x, y - 10) for x, y in seg]
                n = max(2, int(len(xy) * q + 0.999))
                ImageDraw.Draw(im).line(xy[:n], fill=AQUA + (int(170 * a),), width=3)
                f.alpha_composite(im.filter(ImageFilter.GaussianBlur(1.2)))
        p3 = ease_out(prog(t, at("Along") - 0.1, 0.5))
        put_c(f, A["brw"], 360, a * p3, dy=12 * (1 - p3))
    # 5 · soften the forehead
    if 21.9 <= t < 27.15:
        a = fade(t, 21.9, 27.1)
        wash(f, 0, 600, NIGHT, 0.6 * a, 0.0)
        drop(f, A["soft"], cx - A["soft"].adv / 2, 250, prog(t, at("soften") - 0.2, 0.6), a)
        p = prog(t, at("unwind") - 0.3, 0.7)
        if p > 0:
            put_shine(f, A["unw"], cx - A["unw"].adv / 2, 420 + 14 * (1 - ease_out(p)), a * ease_out(p), prog(t, at("unwind") + 0.3, 1.0))
    # 6 · hands
    if 26.9 <= t < 32.05:
        a = fade(t, 26.9, 32.0)
        wash(f, 0, 520, NIGHT, 0.5 * a, 0.0)
        wipe(f, A["hands"], cx - A["hands"].adv / 2, 230, prog(t, at("Then") - 0.1, 0.8), a)
        letters(f, A["pbp"], cx - A["pbp"].adv / 2, 330, at("point", 29.0) - 0.1, t, a, step=0.03)
    # 7 · 75 minutes · $145 · lighter & glowing (café steps)
    if 31.8 <= t < 40.85:
        a = fade(t, 31.8, 40.8)
        wash(f, 1240, H, NIGHT, 0.0, 0.8 * a)
        letters(f, A["min"], cx - A["min"].adv / 2, 1420, at("75") - 0.1, t, a, step=0.03)
        tp = at("$145") - 0.25
        sharp_in(f, A["price"], cx - A["price"].adv / 2, 1640, prog(t, tp, 0.6), a, scale_from=0.84, blur=14)
        if t > tp + 0.7:
            put_shine(f, A["price"], cx - A["price"].adv / 2, 1640, a, prog(t, tp + 0.7, 1.1))
        wipe(f, A["glow"], cx - A["glow"].adv / 2, 1790, prog(t, at("lighter") - 0.2, 0.8), a)
    # 8 · gift certificates (friends leaving the café)
    if 40.6 <= t < 44.65:
        a = fade(t, 40.6, 44.6)
        wash(f, 1250, H, NIGHT, 0.0, 0.8 * a)
        p = prog(t, at("Christmas", 40.0) - 0.1, 0.6)
        if p > 0:
            put_shine(f, A["gift"], cx - A["gift"].adv / 2, 1520, a * ease_out(p), prog(t, at("Christmas", 40.0) + 0.4, 1.0))
        rise(f, A["gift2"], cx - A["gift2"].adv / 2, 1640, prog(t, at("certificates") - 0.1, 0.5), a)
        letters(f, A["dm"], cx - A["dm"].adv / 2, 1740, at("Send") - 0.1, t, a, step=0.025)
    # 9 · end card (mirror portrait): logo on the light wall, frosted lower third
    if t >= 44.4:
        a = ease_out(prog(t, 44.4, 0.5))
        fr = ease_in_out(prog(t, 44.5, 0.8))
        if fr > 0.01:
            low = f.crop((0, 1080, W, H)).filter(ImageFilter.GaussianBlur(20 * fr))
            ramp = np.clip(np.arange(H - 1080, dtype=np.float32) / 200.0, 0, 1)[:, None].repeat(W, 1)
            f.paste(low, (0, 1080), Image.fromarray((ramp * 255).astype(np.uint8), "L"))
        wash(f, 1080, 1280, NIGHT, 0.0, 0.8 * a)
        wash(f, 1280, H, NIGHT, 0.8 * a, 0.88 * a)
        lg = A["logo"]
        put(f, A["logo_glow"], cx - A["logo_glow"].width / 2, 1215 - A["logo_glow"].height / 2, a * 0.95)
        put(f, lg, cx - lg.width / 2, 1215 - lg.height / 2 + 12 * (1 - a), a)
        letters(f, A["wpg"], cx - A["wpg"].adv / 2, 1360, at("Winnipeg") - 0.05, t, step=0.02)
        tz = at("RCRT") - 0.7
        sharp_in(f, A["zr"], cx - A["zr"].adv / 2, 1500, prog(t, tz, 0.6), 1.0, blur=12)
        wipe(f, A["ther"], cx - A["ther"].adv / 2, 1600, prog(t, at("your", 48.0) - 0.1, 0.8))
        p = ease_out(prog(t, at("therapist") + 0.2, 0.5))
        put_c(f, A["addr"], 1690, p, dy=12 * (1 - p))
        p = ease_out(prog(t, at("therapist") + 0.6, 0.5))
        put_c(f, A["cta"], 1780, p, dy=14 * (1 - p))
        L = 420 * ease_in_out(prog(t, at("therapist") + 0.9, 0.6))
        line(f, cx, 1806, L, GOLD_LINE, p, thick=3)
    return np.asarray(f.convert("RGB"))


_A = None


def _init():
    global _A
    _A = build()


def _render(i):
    return frame_at(i / FPS, _A).tobytes()


# ---------------------------------------------------------------- audio (§46 new)
def synth_audio(path, sr=48000):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(76)
    tmp = os.path.join(OUT_DIR, ".fx_voice48.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(AUD, "zara-voiceover.mp3"), "-ac", "1", "-ar", str(sr), tmp], check=True)
    v, vsr = sf.read(tmp)
    os.remove(tmp)
    assert vsr == sr
    voice = np.zeros(n)
    m = min(len(v), n)
    voice[:m] = v[:m]
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.95
    mus = np.zeros(n)

    def add(at_, sig, buf=mus):
        i = int(at_ * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        k = min(len(sig), n - i)
        buf[i:i + k] += sig[:k]
    BPM = 76
    BEAT = 60 / BPM
    BAR = 4 * BEAT
    NT = {"E2": 82.41, "C#2": 69.30, "A1": 55.0, "B1": 61.74, "E3": 164.81, "G#3": 207.65, "B3": 246.94,
          "C#4": 277.18, "A3": 220.0, "D#4": 311.13, "F#3": 185.0, "E4": 329.63, "G#4": 415.3, "B4": 493.88,
          "C#5": 554.37, "D#5": 622.25, "E5": 659.25, "F#5": 739.99, "G#5": 830.61, "B5": 987.77}
    CH = [("E2", ["E3", "G#3", "B3", "D#4"]), ("C#2", ["C#4", "E3", "G#3", "B3"]), ("A1", ["A3", "C#4", "E4", "G#4"]), ("B1", ["B3", "D#4", "F#3", "E4"])]
    MEL = ["G#5", "B5", "G#5", "E5", "F#5", "G#5", "E5", "C#5", "E5", "F#5", "G#5", "B4", "D#5", "E5", "F#5", "D#5"]

    def choir(f0, L):
        tt = np.arange(L) / sr
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.3 * tt)
        ph = 2 * np.pi * f0 * np.cumsum(vib) / sr
        sig = np.zeros(L)
        for k in range(1, 16):
            fk = f0 * k
            g = np.exp(-((fk - 750) / 250) ** 2) + 0.7 * np.exp(-((fk - 1150) / 300) ** 2) + 0.25 * np.exp(-((fk - 2600) / 500) ** 2) + 0.15 / k
            sig += g * np.sin(k * ph)
        return sig

    def glock(f0):
        L = int(2.5 * sr)
        tt = np.arange(L) / sr
        return np.exp(-tt * 2.2) * np.clip(tt / 0.002, 0, 1) * (np.sin(2 * np.pi * f0 * tt) + 0.4 * np.sin(2 * np.pi * f0 * 2.76 * tt) * np.exp(-tt * 6))

    def bell():
        L = int(0.12 * sr)
        x = rng.normal(0, 1, L)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(L, 1 / sr)
        X *= np.exp(-((fr - 7000) / 2500) ** 2)
        y = np.fft.irfft(X, L)
        tt = np.arange(L) / sr
        jingle = sum(np.sin(2 * np.pi * f * tt) for f in (5200, 6100, 7300)) * 0.2
        return (y / (np.abs(y).max() + 1e-9) + jingle) * np.exp(-tt * 35)
    nb = int(DURATION / BAR) + 1
    for b in range(nb):
        root, voi = CH[b % 4]
        t0 = b * BAR
        L = int((BAR + 1.2) * sr)
        tt = np.arange(L) / sr
        env = np.clip(tt / 1.0, 0, 1) * np.clip((BAR + 1.2 - tt) / 1.0, 0, 1)
        for nn in voi:
            add(t0 - 0.3, 0.022 * env * choir(NT[nn], L))
        tt2 = np.arange(int(BAR * sr)) / sr
        add(t0, 0.25 * np.sin(2 * np.pi * NT[root] * tt2) * np.exp(-tt2 * 0.8))
        for j in range(4):
            add(t0 + j * BEAT + (BEAT / 2 if j % 2 else 0), 0.10 * glock(NT[MEL[(b * 4 + j) % len(MEL)]]))
        if t0 > 2.8:
            for k in range(8):
                add(t0 + k * BEAT / 2, (0.05 if k % 2 else 0.035) * bell())
    for at_ in [0.0, at("Christmas") - 0.1, at("pituitary") - 0.1, at("occipital") - 0.3, at("$145") - 0.25,
                at("Christmas", 40.0) - 0.1, at("RCRT") - 0.7]:
        add(at_, 0.12 * glock(NT["E5"]) + 0.08 * glock(NT["B5"]))
    music = mus / (np.abs(mus).max() + 1e-9)
    env = np.convolve(np.abs(voice), np.ones(int(0.25 * sr)) / int(0.25 * sr), mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    gain = 0.30 - 0.16 * env
    st = np.stack([voice + music * gain, voice + np.roll(music, int(0.012 * sr)) * gain], 1)
    st *= (np.clip((DURATION - t) / 1.5, 0, 1) * np.clip(t / 0.05, 0, 1))[:, None]
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
        ts = [float(x) for x in sys.argv[2:]] or [1.8, 5.0, 10.6, 16.0, 21.0, 26.0, 30.0, 35.5, 39.5, 43.8, 50.8]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(OUT_DIR, "qc", f"fx-{s:05.2f}s.png"))
        return
    tmp = os.path.join(OUT_DIR, f".{NAME}.render.mp4")
    wav = os.path.join(OUT_DIR, f".{NAME}.wav")
    synth_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "48000", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
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
    Image.fromarray(frame_at(1.8, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(NAME, DURATION)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
