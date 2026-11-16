"""Story Reel — "Who cares for the ones who care?" — The Pure Escape · Foot + Hand Reflexology.
A dramatized mini-film: a doctor's 12-hour night shift, then reflexology with Zarina, RCRT.

Voice: the owner's ElevenLabs "Zara" MP3 (production/doctor_audio/zara-voiceover.mp3), timed with
word timestamps from faster-whisper (production/doctor_audio/words.json). Every scene cut and text
reveal follows the real voice timing (§48.8).
Footage: the owner's 7 generated clips (5 s each) + 4 stills + the clinic storefront photo.
Living stills: rain + ambulance-light pulse, rain beyond the doors, floating storefront window with
a gold light sweep, breathing + candle flicker, salt-lamp glow.
Type (§48, new pairing): EB Garamond (roman + italic) + Outfit; ivory + champagne gold.
Music (§46, new): B-flat minor → D-flat major strings pad, glass-bowl tones, a heartbeat pulse
that slows from ~100 to ~60 BPM (hospital → treatment room), rain texture; ducks under the voice.

  python3 production/doctor_story_reel.py stills [t ...]
  python3 production/doctor_story_reel.py video
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
from oct16_amt_thanksgiving import Text, bilinear, ease_in_out, ease_out, letters, line, prog, put, put_c, put_x, rise, sharp_in, wash, wipe  # noqa: E402

ROOT = base.ROOT
FONTS = base.FONTS
DS = os.path.join(ROOT, "brand", "photos", "doctor-story")
AUD = os.path.join(ROOT, "production", "doctor_audio")
FR = "/tmp/claude-0/-home-user-Reflex/f74b54ed-c929-5941-94f0-7201420216f3/scratchpad/doc_frames"
LOGO = os.path.join(ROOT, "brand", "locations", "the-pure-escape-logo.png")
OUT_DIR = base.OUT_DIR
NAME = "2026-11-doctor-story-reflexology"
W, H, FPS = 1080, 1920, 30
DURATION = 60.0
CW, CH = 1188, 2112                      # pre-scaled clip frame size (1.1x of the output)

IVORY = (250, 245, 236)
NIGHT = (8, 8, 12)
GOLD_LINE = (222, 190, 132)
base.GOLDS["champ"] = ((252, 236, 204), (224, 192, 138), (166, 128, 76))

WORDS = json.load(open(os.path.join(AUD, "words.json")))


def at(word, after=0.0):
    """Start time of the first spoken word matching `word` at or after time `after`."""
    w0 = word.lower().strip(".,?!")
    for w in WORDS:
        if w["s"] >= after - 0.05 and w["w"].lower().strip(".,?!") == w0:
            return w["s"]
    raise KeyError(word)


def ebg(size, wght=500, italic=False):
    f = ImageFont.truetype(os.path.join(FONTS, "EBGaramond-Italic[wght].ttf" if italic else "EBGaramond[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def outfit(size, wght=500):
    f = ImageFont.truetype(os.path.join(FONTS, "Outfit[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT)


# ---------------------------------------------------------------- scenes (times from the voice)
SCENES = [  # (kind, key, start, end, extra)
    ("still", "hospital", 0.0, 2.80, {}),
    ("still", "wheelchair", 2.60, 7.05, {}),
    ("clip", "c3-running", 6.85, 9.75, {"src": 1.2, "speed": 1.0, "z0": 1.0, "z1": 1.06}),
    ("clip", "c4-newborn", 9.55, 13.30, {"src": 0.5, "speed": 1.0, "z0": 1.04, "z1": 1.0}),
    ("clip", "c5-car", 13.10, 20.25, {"src": 0.0, "speed": 0.70, "z0": 1.0, "z1": 1.08}),
    ("still", "storefront", 20.05, 25.35, {}),
    ("clip", "c7-talking", 25.15, 28.70, {"src": 0.8, "speed": 1.0, "z0": 1.06, "z1": 1.0}),
    ("clip", "c8-foot", 28.50, 30.40, {"src": 0.4, "speed": 1.0, "z0": 1.0, "z1": 1.04}),
    ("clip", "c9-hand", 30.20, 34.20, {"src": 0.4, "speed": 1.0, "z0": 1.0, "z1": 1.06}),
    ("still", "relaxed", 34.00, 41.60, {}),
    ("clip", "c8-foot", 41.40, 44.90, {"src": 2.4, "speed": 0.70, "z0": 1.08, "z1": 1.02}),
    ("clip", "c11-walking", 44.70, 50.05, {"src": 0.0, "speed": 0.95, "z0": 1.0, "z1": 1.06}),
    ("still", "portrait", 49.85, DURATION, {}),
]
XF = 0.2  # cross-defocus length (the overlap between scenes)


class Clip:
    def __init__(self, key):
        p = os.path.join(FR, key + ".rgb")
        n = os.path.getsize(p) // (CW * CH * 3)
        self.frames = np.memmap(p, dtype=np.uint8, mode="r", shape=(n, CH, CW, 3))
        self.n = n

    def frame(self, ts):
        """Frame at source time ts (24 fps) with linear blending between neighbours."""
        x = max(0.0, min(ts * 24.0, self.n - 1.001))
        i = int(x)
        f = x - i
        a = self.frames[i].astype(np.float32)
        if f > 0.02:
            a = a * (1 - f) + self.frames[i + 1].astype(np.float32) * f
        return a


def crop_zoom(arr, z, u=0.5, v=0.5):
    """Crop a W x H window (zoom z relative to the 1.1x plate) and resample to W x H."""
    h, w = arr.shape[:2]
    s = max(W / w, H / h)
    cw, ch = W / s / z * 1.1 / 1.1, H / s / z
    cw = W / s / z
    cx = min(max(u * w, cw / 2), w - cw / 2)
    cy = min(max(v * h, ch / 2), h - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    return gx, gy


def _blurL(a, r):
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(r)), np.float32)


def build_still(key):
    S = {}
    if key == "storefront":
        im = Image.open(os.path.join(DS, "stills", "pe-storefront-pro.jpg")).convert("RGB")
        # booking is DM only: hide the phone number and website on the left sign (keep its red colour)
        box = (28, 540, 246, 628)
        reg = im.crop(box).filter(ImageFilter.GaussianBlur(26))
        m = Image.new("L", reg.size, 0)
        ImageDraw.Draw(m).rectangle((6, 6, reg.width - 6, reg.height - 6), fill=255)
        im.paste(reg, box[:2], m.filter(ImageFilter.GaussianBlur(5)))
    else:
        im = None
    if im is None:
        fn = {"hospital": "hospital-night-rain.png", "wheelchair": "wheelchair-arrival.png",
              "relaxed": "relaxed-table.png", "portrait": "zarina-portrait.png"}[key]
        im = Image.open(os.path.join(DS, "stills", fn)).convert("RGB")
    k = max(W / im.width, H / im.height) * 1.1
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 55, 2))
    arr = np.asarray(big, np.float32)
    h, w = arr.shape[:2]
    S["arr"], S["w"], S["h"] = arr, w, h
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    def gl(pts):
        g = np.zeros((h, w), np.float32)
        for (u, v, r) in pts:
            g += np.exp(-(((xx - u * w) ** 2 + (yy - v * h) ** 2) / (2 * (r * w) ** 2)))
        return np.clip(g, 0, 1)
    if key == "hospital":
        S["red"] = gl([(0.17, 0.70, 0.05), (0.14, 0.82, 0.06), (0.10, 0.90, 0.07)])
        S["blue"] = gl([(0.26, 0.70, 0.05), (0.28, 0.83, 0.06), (0.30, 0.90, 0.07)])
    if key == "relaxed":
        S["flame"] = gl([(0.03, 0.43, 0.03), (0.57, 0.37, 0.03), (0.81, 0.43, 0.03), (0.63, 0.37, 0.06)])
        m = np.zeros((h, w), np.float32)
        m[int(0.55 * h):int(0.95 * h), int(0.0 * w):int(0.9 * w)] = 1
        S["chest"] = _blurL(m * 255, 60) / 255
    if key == "storefront":
        m = np.zeros((h, w), np.float32)
        m[: int(0.30 * h)] = 1
        m[int(0.62 * h):, : int(0.25 * w)] = 1
        m[int(0.80 * h):] = 1
        S["leaves"] = _blurL(m * 255, 50) / 255
        S["signs"] = gl([(0.40, 0.37, 0.10), (0.77, 0.38, 0.12)])
    if key == "portrait":
        S["flame"] = gl([(0.88, 0.39, 0.05), (0.97, 0.43, 0.02), (0.93, 0.59, 0.02)])
    return S


def flick(t, s):
    return (0.55 * math.sin(7.3 * t + s) + 0.3 * math.sin(13.1 * t + 2 * s) + 0.25 * math.sin(3.1 * t + s * 0.5)) / 1.1


def render_still(key, S, t, p):
    """p = 0..1 progress through the scene (camera)."""
    cams = {"hospital": (0.5, 0.42, 1.0, 1.08), "wheelchair": (0.52, 0.45, 1.08, 1.0),
            "relaxed": (0.45, 0.42, 1.0, 1.10), "portrait": (0.5, 0.42, 1.1, 1.0),
            "storefront": (0.55, 0.42, 1.0, 1.10)}
    u, v, z0, z1 = cams[key]
    z = z0 + (z1 - z0) * ease_in_out(p)
    arr, w, h = S["arr"], S["w"], S["h"]
    s = max(W / w, H / h)
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * w, cw / 2), w - cw / 2)
    cy = min(max(v * h, ch / 2), h - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    ix = np.clip(gx.astype(np.int32), 0, w - 1)
    iy = np.clip(gy.astype(np.int32), 0, h - 1)
    if key == "relaxed":   # slow breathing: the chest and blanket rise a little
        br = math.sin(2 * math.pi * t / 4.6)
        gy = gy - S["chest"][iy, ix] * 4.0 * br
    if key == "storefront":   # foliage moving in a light breeze
        lv = S["leaves"][iy, ix]
        gx = gx + lv * (5.0 * np.sin(1.1 * t + gy * 0.006) + 2.0 * np.sin(2.3 * t + gx * 0.01))
        gy = gy + lv * (2.5 * np.sin(1.4 * t + gx * 0.007))
    img = bilinear(arr, gx, gy)
    if key == "storefront":   # warm sunlight drifting over the signs
        sg = S["signs"][iy, ix][..., None]
        img = img * (1 + 0.14 * sg * (0.6 + 0.4 * math.sin(t * 1.3)))
    if key == "hospital":
        r = max(0.0, math.sin(t * 9.0)) ** 2
        b = max(0.0, math.sin(t * 9.0 + math.pi)) ** 2
        img = img + S["red"][iy, ix][..., None] * np.array([150, 20, 20], np.float32) * r + S["blue"][iy, ix][..., None] * np.array([20, 40, 160], np.float32) * b
    if key in ("relaxed", "portrait"):
        g = S["flame"][iy, ix][..., None]
        f = flick(t, 1.3)
        img = img * (1 + g * 0.22 * f) + g * np.array([255, 180, 100], np.float32) * (0.08 + 0.05 * f)
    return img


def rain_layer(A, t, a, heavy=1.0):
    """Falling rain streaks (screen-space overlay)."""
    off = int((t * 2300) % H)
    r = np.roll(A["rain"], off, axis=0)
    return r * a * heavy


def scene_frame(A, i, t):
    kind, key, s, e, ex = SCENES[i]
    p = min(1.0, max(0.0, (t - s) / (e - s)))
    if kind == "clip":
        cl = A["clips"][key]
        fr = cl.frame(ex["src"] + (t - s) * ex["speed"])
        z = ex["z0"] + (ex["z1"] - ex["z0"]) * ease_in_out(p)
        gx, gy = crop_zoom(fr, z * 1.0 / 1.0 * (CW / (W * 1.1)) * 1.1 if False else z)
        return bilinear(fr, gx, gy)
    return render_still(key, A["S"][key], t, p)


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
    if t < 7.0:                      # rain over the hospital opening + beyond the doors
        img = img + rain_layer(A, t, 1.0 if t < 2.8 else 0.45)[..., None]
    img = img * A["vig"] + A["grain"][int(t * 15) % 3]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA"), act


# ---------------------------------------------------------------- typography helpers (§48)
def shine(tx, p):
    """Champagne light sweep across a text image (p 0..1)."""
    if p <= 0 or p >= 1:
        return tx.img
    arr = np.asarray(tx.img, np.float32).copy()
    w = arr.shape[1]
    xs = np.arange(w, dtype=np.float32)[None, :]
    ys = np.arange(arr.shape[0], dtype=np.float32)[:, None]
    cx = -0.2 * w + 1.4 * w * p
    band = np.exp(-(((xs - cx) + ys * 0.35) / (0.07 * w + 20)) ** 2)
    a = arr[..., 3:4] / 255
    arr[..., :3] = np.clip(arr[..., :3] + band[..., None] * 120 * a, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def put_shine(f, tx, x, base_y, a, p):
    put(f, shine(tx, p), x - tx.pad, base_y - tx.asc, a)


def drop(f, tx, x, base_y, p, a=1.0):
    """Top-to-bottom reveal: the text slides down from above while a mask opens downward."""
    if p <= 0:
        return
    e = ease_out(p)
    vis = max(1, int(tx.h * e))
    img = tx.img.crop((0, tx.h - vis, tx.w, tx.h))
    put(f, img, x - tx.pad, base_y - tx.asc + (tx.h - vis) * 0.0 - 30 * (1 - e) + (tx.h - vis) * 0, a * e)


def slide(f, tx, x, base_y, p, a=1.0, dx=-80):
    e = ease_out(p)
    if e > 0:
        put_x(f, tx, x, base_y, a * e, dx=dx * (1 - e))


def build():
    A = {"clips": {k: Clip(k) for k in {sc[1] for sc in SCENES if sc[0] == "clip"}},
         "S": {k: build_still(k) for k in {sc[1] for sc in SCENES if sc[0] == "still"}}}
    rng = np.random.default_rng(11)
    A["grain"] = [rng.normal(0, 2.2, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.26 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    rain = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(rain)
    for _ in range(900):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        ln = rng.uniform(30, 90)
        d.line([(x, y), (x - ln * 0.12, y + ln)], fill=int(rng.uniform(40, 120)), width=1)
    A["rain"] = np.asarray(rain.filter(ImageFilter.GaussianBlur(0.6)), np.float32) * 0.55
    logo = Image.open(LOGO).convert("RGBA")
    A["logo"] = logo.resize((340, round(logo.height * 340 / logo.width)), Image.LANCZOS)
    pad = 220
    gl = Image.new("L", (A["logo"].width + 2 * pad, A["logo"].height + 2 * pad), 0)
    ImageDraw.Draw(gl).ellipse((pad - 30, pad - 20, gl.width - pad + 30, gl.height - pad + 20), fill=215)
    glow = Image.new("RGBA", gl.size, (252, 246, 236, 0))
    glow.putalpha(gl.filter(ImageFilter.GaussianBlur(60)))
    A["logo_glow"] = glow

    A["h1"] = T("Who cares", ebg(170, 500), IVORY)
    A["h2"] = T("for the ones who care?", ebg(92, 450, True), "champ")
    A["wpg"] = T("WINNIPEG  ·  LATE AT NIGHT", outfit(34, 600), IVORY, tracking=10)
    A["oncall"] = T("ON CALL", outfit(40, 700), "champ", tracking=22)
    A["hours"] = T("Hours later…", ebg(96, 400, True), IVORY)
    A["twelve"] = T("12 HOURS", ebg(190, 600), "champ")
    A["feet"] = T("on his feet.", ebg(90, 400, True), IVORY)
    A["hbm"] = [T(w, outfit(40, 600), IVORY, tracking=6) for w in ("HANDS", "BACK", "MIND")]
    A["tired"] = T("all tired.", ebg(84, 400, True), "champ")
    A["week"] = T("LATER THAT WEEK", outfit(34, 600), IVORY, tracking=12)
    A["cory"] = T("Corydon Avenue", ebg(96, 400, True), IVORY)
    A["tpe"] = T("The Pure Escape", ebg(120, 500), "champ")
    A["listens"] = [T(w, ebg(92, 450, True), IVORY) for w in ("Zarina", "listens", "first.")]
    A["foot"] = T("FOOT REFLEXOLOGY", outfit(46, 700), IVORY, tracking=14)
    A["hand"] = T("HAND REFLEXOLOGY", outfit(46, 700), IVORY, tracking=14)
    A["newlife"] = T("the hands that held new life", ebg(78, 400, True), "champ")
    A["rest"] = base.fit(lambda z: T("REST & DIGEST", ebg(z, 600), "champ"), 150, 960)
    A["para"] = T("the parasympathetic nervous system", ebg(56, 400, True), IVORY)
    A["breath"] = T("Breathing slows.", ebg(92, 450, True), IVORY)
    A["should"] = T("Shoulders soften.", ebg(92, 450, True), "champ")
    A["lighter"] = T("Many clients say they leave feeling lighter.", outfit(36, 500), IVORY, tracking=1)
    A["breathe"] = T("Breathe easier.", ebg(120, 500), IVORY)
    A["smile"] = T("Smile more.", ebg(120, 500, True), "champ")
    A["give1"] = T("Give your mind and body", ebg(76, 400, True), IVORY)
    A["give2"] = T("time to rest & recover", ebg(76, 400, True), "champ")
    A["zr"] = T("Zarina, RCRT", ebg(132, 600), IVORY)
    A["ther"] = T("your reflexology therapist", ebg(64, 400, True), "champ")
    A["addr"] = T("The Pure Escape  ·  698 Corydon Ave, Winnipeg", outfit(32, 500), IVORY, tracking=1)
    A["dm"] = T("DM TO BOOK", outfit(52, 700), IVORY, tracking=16)
    A["dram"] = T("Dramatized story", outfit(24, 500), IVORY, tracking=2)
    return A


def fade(t, s, e, fi=0.4, fo=0.35):
    return ease_out(prog(t, s, fi)) * (1 - ease_in_out(prog(t, e - fo, fo)))


def frame_at(t, A):
    f, act = background(A, t)
    cx = W / 2

    # 1 · hook — blur-to-focus headline + gold italic with a light sweep
    if t < 2.9:
        a = fade(t, 0.0, 2.8, 0.2)
        wash(f, 0, 900, NIGHT, 0.55 * a, 0.0)
        sharp_in(f, A["h1"], cx - A["h1"].adv / 2, 430, prog(t, 0.05, 0.6), a, scale_from=1.12, blur=18)
        p = prog(t, at("ones") - 0.15, 0.6)
        if p > 0:
            put_shine(f, A["h2"], cx - A["h2"].adv / 2, 560 + 16 * (1 - ease_out(p)), a * ease_out(p), prog(t, 1.2, 1.2))
    # 2 · wheelchair — letter-by-letter place line
    if 2.6 <= t < 7.1:
        a = fade(t, 2.6, 7.05)
        wash(f, 0, 500, NIGHT, 0.6 * a, 0.0)
        letters(f, A["wpg"], cx - A["wpg"].adv / 2, 230, 2.85, t, a, step=0.03)
    # 3 · running — slide in from the left
    if 6.85 <= t < 9.8:
        a = fade(t, 6.85, 9.75)
        wash(f, 0, 450, NIGHT, 0.45 * a, 0.0)
        slide(f, A["oncall"], cx - A["oncall"].adv / 2, 260, prog(t, at("doctor") - 0.1, 0.6), a, dx=-120)
    # 4 · newborn — italic fades up from the bottom
    if 9.55 <= t < 13.35:
        a = fade(t, 9.55, 13.3)
        wash(f, 1400, H, NIGHT, 0.0, 0.7 * a)
        rise(f, A["hours"], cx - A["hours"].adv / 2, 1720, prog(t, at("Hours"), 0.7), a)
    # 5 · car — "12 HOURS" scales in with a gold sweep, then the tired words drop in
    if 13.1 <= t < 20.3:
        a = fade(t, 13.1, 20.25)
        wash(f, 1250, H, NIGHT, 0.0, 0.78 * a)
        t12 = at("12")
        sharp_in(f, A["twelve"], cx - A["twelve"].adv / 2, 1500, prog(t, t12, 0.6), a * (1 - 0.0), scale_from=0.82, blur=14)
        if t > t12 + 0.7:
            put_shine(f, A["twelve"], cx - A["twelve"].adv / 2, 1500, a, prog(t, t12 + 0.7, 1.0))
        wipe(f, A["feet"], cx - A["feet"].adv / 2, 1610, prog(t, at("feet") - 0.3, 0.7), a)
        xs = [cx - 330, cx, cx + 330]
        for k, wd in enumerate(("hands", "back", "mind")):
            p = prog(t, at(wd, 15.0) - 0.05, 0.4)
            drop(f, A["hbm"][k], xs[k] - A["hbm"][k].adv / 2, 1720, p, a)
        rise(f, A["tired"], cx - A["tired"].adv / 2, 1830, prog(t, at("all") - 0.05, 0.6), a)
    # 6 · storefront — small line, italic street, gold name with light sweep (the window gets its own sweep)
    if 20.05 <= t < 25.4:
        a = fade(t, 20.05, 25.35)
        letters(f, A["week"], cx - A["week"].adv / 2, 330, at("Later"), t, a, step=0.03)
        wipe(f, A["cory"], cx - A["cory"].adv / 2, 450, prog(t, at("Corridon") - 0.1, 0.8), a)
        p = prog(t, at("pure") - 0.2, 0.6)
        if p > 0:
            put_shine(f, A["tpe"], cx - A["tpe"].adv / 2, 1720 + 20 * (1 - ease_out(p)), a * ease_out(p), prog(t, at("pure") + 0.3, 1.2))
    # 7 · talking — word by word
    if 25.15 <= t < 28.75:
        a = fade(t, 25.15, 28.7)
        wash(f, 1350, H, NIGHT, 0.0, 0.75 * a)
        t0 = at("Zarena")
        x = cx - (sum(w.adv for w in A["listens"]) + 2 * 26) / 2
        for k, w in enumerate(A["listens"]):
            p = ease_out(prog(t, t0 + k * 0.32, 0.45))
            put_x(f, w, x, 1680, a * p, dy=18 * (1 - p))
            x += w.adv + 26
    # 8 · foot — mask reveal from the left
    if 28.5 <= t < 30.45:
        a = fade(t, 28.5, 30.4, 0.25, 0.25)
        wash(f, 0, 500, NIGHT, 0.5 * a, 0.0)
        wipe(f, A["foot"], cx - A["foot"].adv / 2, 300, prog(t, at("Foot") - 0.15, 0.6), a)
    # 9 · hand — bottom-to-top + gold italic
    if 30.2 <= t < 34.25:
        a = fade(t, 30.2, 34.2)
        wash(f, 0, 560, NIGHT, 0.45 * a, 0.0)
        rise(f, A["hand"], cx - A["hand"].adv / 2, 280, prog(t, at("hands", 30.0) - 0.2, 0.6), a)
        p = prog(t, at("held") - 0.3, 0.9)
        if p > 0:
            put_shine(f, A["newlife"], cx - A["newlife"].adv / 2, 390, a * ease_out(p), prog(t, at("held") + 0.4, 1.4))
    # 10 · relaxed — REST & DIGEST + a breathing ring that slows
    if 34.0 <= t < 41.65:
        a = fade(t, 34.0, 41.6)
        wash(f, 0, 700, NIGHT, 0.5 * a, 0.0)
        tr = at("rest") - 0.2
        sharp_in(f, A["rest"], cx - A["rest"].adv / 2, 330, prog(t, tr, 0.7), a, scale_from=1.06, blur=14)
        if t > tr + 0.8:
            put_shine(f, A["rest"], cx - A["rest"].adv / 2, 330, a, prog(t, tr + 0.8, 1.2))
        wipe(f, A["para"], cx - A["para"].adv / 2, 420, prog(t, at("parasympathetic") - 0.3, 1.0), a)
        # breathing ring (a calm 4.6 s cycle), around the chest
        br = 0.5 + 0.5 * math.sin(2 * math.pi * t / 4.6)
        r = 70 + 50 * br
        ra = a * 0.55 * ease_out(prog(t, 35.0, 1.0))
        if ra > 0.02:
            S_ = int(r * 2 + 20)
            im = Image.new("RGBA", (S_, S_), (0, 0, 0, 0))
            ImageDraw.Draw(im).ellipse((10, 10, S_ - 10, S_ - 10), outline=GOLD_LINE + (int(255 * ra),), width=3)
            f.alpha_composite(im.filter(ImageFilter.GaussianBlur(1.2)), (int(cx - S_ / 2), int(560 - S_ / 2)))
    # 11 · breathing slows — top-to-bottom reveals
    if 41.4 <= t < 44.95:
        a = fade(t, 41.4, 44.9)
        wash(f, 0, 560, NIGHT, 0.5 * a, 0.0)
        drop(f, A["breath"], cx - A["breath"].adv / 2, 300, prog(t, at("Breathing") - 0.1, 0.6), a)
        drop(f, A["should"], cx - A["should"].adv / 2, 410, prog(t, at("shoulders") - 0.1, 0.6), a)
    # 12 · walking into the sun
    if 44.7 <= t < 50.1:
        a = fade(t, 44.7, 50.05)
        wash(f, 1250, H, NIGHT, 0.0, 0.7 * a)
        p = ease_out(prog(t, at("Many"), 0.6))
        put_c(f, A["lighter"], 1480, a * p * (1 - ease_in_out(prog(t, at("Breathe") - 0.2, 0.3))), dy=12 * (1 - p))
        sharp_in(f, A["breathe"], cx - A["breathe"].adv / 2, 1600, prog(t, at("Breathe"), 0.6), a, blur=12)
        p = prog(t, at("smile") - 0.1, 0.6)
        if p > 0:
            put_shine(f, A["smile"], cx - A["smile"].adv / 2, 1740, a * ease_out(p), prog(t, at("smile") + 0.4, 1.1))
    # 13 · portrait — the wish, then the signature end card (logo on an edgeless light glow)
    if t >= 49.85:
        a = ease_out(prog(t, 49.85, 0.5))
        # frosted lower third: hides the AI embroidery on the scrubs and gives the type a calm base
        fr = ease_in_out(prog(t, 49.9, 0.8))
        if fr > 0.01:
            low = f.crop((0, 900, W, H)).filter(ImageFilter.GaussianBlur(22 * fr))
            ramp = np.clip((np.arange(H - 900, dtype=np.float32) - 0) / 220.0, 0, 1)[:, None].repeat(W, 1)
            f.paste(low, (0, 900), Image.fromarray((ramp * 255).astype(np.uint8), "L"))
        wash(f, 1000, 1200, NIGHT, 0.0, 0.8 * a)
        wash(f, 1200, H, NIGHT, 0.8 * a, 0.88 * a)
        aw = 1 - ease_in_out(prog(t, at("Zarena", 52.0) - 0.4, 0.4))
        wipe(f, A["give1"], cx - A["give1"].adv / 2, 1560, prog(t, at("Give"), 0.8), a * aw)
        wipe(f, A["give2"], cx - A["give2"].adv / 2, 1660, prog(t, at("time", 49.0), 0.8), a * aw)
        if t >= at("Zarena", 52.0) - 0.3:
            te = at("Zarena", 52.0)
            pl = ease_out(prog(t, te - 0.3, 0.7))
            lg = A["logo"]
            put(f, lg, 40, 1000 - lg.height - 30 + 12 * (1 - pl), pl)      # on the light wall, no plate or glow
            sharp_in(f, A["zr"], cx - A["zr"].adv / 2, 1430, prog(t, te, 0.6), 1.0, blur=12)
            wipe(f, A["ther"], cx - A["ther"].adv / 2, 1515, prog(t, at("your", te) - 0.1, 0.8))
            p = ease_out(prog(t, at("your", te) + 0.8, 0.5))
            put_c(f, A["addr"], 1590, p, dy=12 * (1 - p))
            td = at("DM")
            p = ease_out(prog(t, td - 0.3, 0.5))
            put_c(f, A["dm"], 1700, p, dy=14 * (1 - p))
            L = 340 * ease_in_out(prog(t, td + 0.1, 0.6)) * (0.86 + 0.14 * math.sin(max(0.0, t - td - 0.7) * 2.4))
            line(f, cx, 1724, L, GOLD_LINE, p, thick=3)
            put(f, A["dram"].img, 40, H - 70, 0.7 * pl)
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
    rng = np.random.default_rng(60)
    v, vsr = sf.read(os.path.join(AUD, "zara-voiceover.mp3")) if False else sf.read(os.path.join(AUD, "zara16k.wav"))
    # use the full-quality MP3 decoded by ffmpeg at 48 kHz
    tmp = os.path.join(OUT_DIR, ".zara48.wav")
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

    # strings pad, chord by section
    NT = {"Bb1": 58.27, "Gb1": 46.25, "Ab1": 51.91, "Db2": 69.30,
          "Bb2": 116.54, "Db3": 138.59, "F3": 174.61, "Bb3": 233.08, "Gb2": 92.50, "Ab2": 103.83, "Eb3": 155.56,
          "Ab3": 207.65, "C4": 261.63, "Eb4": 311.13, "F4": 349.23, "Db4": 277.18}
    SECT = [(0, 13.2, ["Bb2", "Db3", "F3", "Bb3"]), (13.0, 20.3, ["Gb2", "Bb2", "Db3", "F3"]),
            (20.1, 28.6, ["Ab2", "Eb3", "Ab3", "C4"]), (28.4, 41.6, ["Db3", "F3", "Ab3", "C4", "Eb4"]),
            (41.4, 50.0, ["Gb2", "Bb2", "Db3", "F3"]), (49.8, DURATION + 1, ["Db3", "F3", "Ab3", "C4", "F4"])]
    for s, e, notes in SECT:
        L = int((e - s + 1.5) * sr)
        tt = np.arange(L) / sr
        env = np.clip(tt / 1.4, 0, 1) * np.clip((e - s + 1.5 - tt) / 1.4, 0, 1)
        for nn in notes:
            f0 = NT[nn]
            vib = 1 + 0.003 * np.sin(2 * np.pi * 5.1 * tt + f0)
            ph = 2 * np.pi * f0 * np.cumsum(vib) / sr
            add(s - 0.4, 0.05 * env * sum((0.6 / k) * np.sin(k * ph) for k in range(1, 6)))
    # glass-bowl tones on key moments
    def bowl(f0, g):
        L = int(5.0 * sr)
        tt = np.arange(L) / sr
        env = np.exp(-tt * 0.9) * np.clip(tt / 0.01, 0, 1)
        s_ = (np.sin(2 * np.pi * f0 * tt) * (1 + 0.3 * np.sin(2 * np.pi * 2.2 * tt)) + 0.35 * np.sin(2 * np.pi * f0 * 2.71 * tt) * np.exp(-tt * 1.5)
              + 0.15 * np.sin(2 * np.pi * f0 * 5.15 * tt) * np.exp(-tt * 3))
        return g * env * s_
    for at_, f0 in [(0.05, 466.16), (at("12"), 554.37), (at("pure") - 0.2, 698.46), (at("rest") - 0.2, 554.37),
                    (at("smile") - 0.1, 698.46), (at("Zarena", 52.0) - 0.3, 554.37), (at("DM") - 0.3, 698.46)]:
        add(at_, bowl(f0, 0.20))
    # heartbeat: ~100 BPM in the hospital, slowing to ~60 BPM in the treatment room, then fading out
    def thump(g, f0=52):
        L = int(0.25 * sr)
        tt = np.arange(L) / sr
        fr = f0 * (1 + 0.6 * np.exp(-tt * 30))
        return g * np.sin(2 * np.pi * np.cumsum(fr) / sr) * np.exp(-tt * 14) * np.clip(tt / 0.004, 0, 1)
    tb = 0.3
    while tb < 44.0:
        bpm = 100 if tb < 20 else max(60.0, 100 - (tb - 20) * 3.0)
        g = 0.55 * (1.0 if tb < 34 else max(0.0, 1 - (tb - 34) / 10))
        add(tb, thump(g))
        add(tb + 0.19, thump(g * 0.6, 48))
        tb += 60.0 / bpm
    # rain (hospital and car), fades when he reaches the clinic
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    fr_ = np.fft.rfftfreq(n, 1 / sr)
    X *= np.exp(-((np.log(fr_ + 1) - np.log(3200)) / 0.9) ** 2)
    rain = np.fft.irfft(X, n)
    rain = rain / np.abs(rain).max() * np.clip((21.0 - t) / 1.5, 0, 1) * (0.10 + 0.05 * ((t > 13.1) & (t < 20.3)))
    music = mus / (np.abs(mus).max() + 1e-9) + rain
    env = np.convolve(np.abs(voice), np.ones(int(0.25 * sr)) / int(0.25 * sr), mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    gain = 0.32 - 0.17 * env
    st = np.stack([voice + music * gain, voice + np.roll(music, int(0.011 * sr)) * gain], 1)
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
        ts = [float(x) for x in sys.argv[2:]] or [1.6, 5.0, 8.3, 11.5, 16.5, 23.8, 27.0, 29.5, 32.5, 38.5, 43.0, 48.6, 51.5, 58.5]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(OUT_DIR, "qc", f"doc-{s:05.2f}s.png"))
        return
    tmp = os.path.join(OUT_DIR, f".{NAME}.render.mp4")
    wav = os.path.join(OUT_DIR, f".{NAME}.wav")
    synth_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "48000", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
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
    Image.fromarray(frame_at(1.6, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(NAME, DURATION)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
