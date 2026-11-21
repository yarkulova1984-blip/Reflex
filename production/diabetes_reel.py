"""Reel — "Did you know stress can raise your blood sugar?" — Diabetes & Reflexology · Advanced Massage Therapy.

Educational story: stress hormones and blood sugar (established physiology, Diabetes Canada), diabetes and
the feet (neuropathy), the pancreas reflex (reflexology concept), gentle adapted technique, relaxation,
the owner's practitioner observation (5–15 % lower readings after a session, labelled "practitioner
observation · results vary" at the owner's explicit request), insulin safety line, "doesn't replace your
diabetes care", DM to book at Advanced Massage Therapy, 2020 Corydon Ave.

Voice (§47.8): ElevenLabs Zara via json2video (production/zara_tts.py), timed with faster-whisper word
timestamps (production/diabetes_audio/words.json).
Footage: owner's 4 clips (client + feet, Zarina working, client + glucose phone, storefront — shown only as a
heavy soft blur behind the OFFICIAL AMT logo, because the clip's sign is an AI redraw) + 5 stills.
Type (new pairing): Newsreader (editorial serif) + Manrope (sans) + Pinyon Script (accent).
Palette: deep teal (echoes the AMT knot) + ivory + champagne gold.
Music (§46, new): C minor -> E-flat major, 66 BPM, harp-like plucked arpeggios, warm string pad,
brush-swirl pulse on 2 & 4, wooden-knock accents on reveals, reverse swells into scene changes.

  python3 production/diabetes_reel.py stills [t ...]
  python3 production/diabetes_reel.py video
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
from doctor_story_reel import put_shine, drop, slide  # noqa: E402
from oct16_amt_thanksgiving import Text, bilinear, ease_in_out, ease_out, letters, line, prog, put, put_c, put_x, rise, sharp_in, wash, wipe  # noqa: E402
from oct15_pe_thu_sat import ks  # noqa: E402

ROOT = base.ROOT
FONTS = base.FONTS
DB = os.path.join(ROOT, "brand", "photos", "diabetes")
AUD = os.path.join(ROOT, "production", "diabetes_audio")
LOGO = os.path.join(ROOT, "brand", "locations", "advanced-massage-therapy-logo.png")
FR = "/tmp/claude-0/-home-user-Reflex/f74b54ed-c929-5941-94f0-7201420216f3/scratchpad/diab_frames"
OUT_DIR = base.OUT_DIR
NAME = "2026-11-diabetes-reflexology-amt"
W, H, FPS = 1080, 1920, 30
WORDS = json.load(open(os.path.join(AUD, "words.json")))
VOICE_END = WORDS[-1]["e"]
DURATION = round(VOICE_END + 3.4, 1)

IVORY = (252, 247, 238)
NIGHT = (8, 14, 15)
TEAL = (96, 196, 188)
GOLD_LINE = (226, 194, 136)
base.GOLDS["champ"] = ((252, 238, 208), (226, 194, 140), (168, 130, 78))


def at(word, after=0.0):
    w0 = word.lower().strip(".,?!%")
    for w in WORDS:
        if w["s"] >= after - 0.05 and w["w"].lower().strip(".,?!%-") == w0:
            return w["s"]
    raise KeyError(word)


def news(size, wght=420, italic=False):
    f = ImageFont.truetype(os.path.join(FONTS, "Newsreader-Italic[opsz,wght].ttf" if italic else "Newsreader[opsz,wght].ttf"), size)
    f.set_variation_by_axes([72, wght])
    return f


def mano(size, wght=600):
    f = ImageFont.truetype(os.path.join(FONTS, "Manrope[wght].ttf"), size)
    f.set_variation_by_axes([wght])
    return f


def pin(size):
    return ImageFont.truetype(os.path.join(FONTS, "PinyonScript-Regular.ttf"), size)


def T(txt, fnt, fill, tracking=0):
    return Text(txt, fnt, fill, tracking=tracking, shadow=NIGHT)


# ---------------------------------------------------------------- scenes (from the voice timing)
SCENES = [
    ("still", "hook", 0.0, 2.75, {}),
    ("still", "pancreas", 2.55, 5.65, {}),
    ("still", "stress", 5.45, 10.25, {}),
    ("clip", "c1", 10.15, 16.45, {"src": 0.0, "speed": 0.79, "z0": 1.20, "z1": 1.24, "u": 0.62, "v": 0.0}),
    ("still", "chart", 16.35, 20.55, {}),
    ("clip", "c2", 20.45, 25.55, {"src": 0.0, "speed": 0.98, "z0": 1.0, "z1": 1.04, "u": 0.5, "v": 0.5}),
    ("still", "towel", 25.45, 31.30, {}),
    ("fitclip", "c3", 31.20, 44.40, {"src": 0.0, "speed": 0.45, "top": 150}),
    ("blurclip", "c4", 44.30, 49.00, {"src": 0.0, "speed": 1.0}),
    ("still", "portrait", 48.90, DURATION, {}),
]
CLIPS = {"c1": "c1-feet-tingling.mp4", "c2": "c2-zarina-foot.mp4", "c3": "c3-glucose-phone.mp4", "c4": "c4-amt-storefront.mp4"}
# still: (file, source crop box with 9:16 aspect — keeps AI-baked titles out of frame)
STILLS = {"hook": ("client-phone.png", (0, 60, 660, 1233)),
          "pancreas": ("pancreas.png", (40, 380, 560, 1304)),
          "stress": ("client-phone.png", (0, 60, 660, 1233)),
          "chart": ("chart.png", (0, 0, 941, 1672)),
          "towel": ("towel.png", (0, 0, 941, 1672)),
          "portrait": ("portrait.png", (100, 0, 800, 1244))}
CAMS = {"hook": (0.5, 0.42, 1.0, 1.07), "pancreas": (0.5, 0.36, 1.02, 1.20), "stress": (0.45, 0.55, 1.12, 1.30),
        "chart": (0.72, 0.36, 1.00, 1.16), "towel": (0.5, 0.45, 1.08, 1.0), "portrait": (0.5, 0.40, 1.0, 1.06)}
PANC_CHART = (748, 482)      # highlighted pancreas reflex on chart.png (reflexology concept)


def build_still(key):
    fn, box = STILLS[key]
    im = Image.open(os.path.join(DB, "stills", fn)).convert("RGB").crop(box)
    k = max(W / im.width, H / im.height) * 1.1
    big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 40, 2))
    return {"arr": np.asarray(big, np.float32), "w": big.width, "h": big.height, "k": k, "box": box}


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
    bx, by = S["box"][:2]
    return ((x - bx) * S["k"] - x0) / sc, ((y - by) * S["k"] - y0) / sc


def render_still(S, key, p):
    x0, y0, sc = cam_window(S, key, p)
    gx = x0 + np.arange(W, dtype=np.float32)[None, :].repeat(H, 0) * sc
    gy = y0 + np.arange(H, dtype=np.float32)[:, None].repeat(W, 1) * sc
    return bilinear(S["arr"], gx, gy)


class Clip:
    def __init__(self, key):
        src = os.path.join(DB, "clips", CLIPS[key])
        w, h = [int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                                "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip().split(",")]
        p = os.path.join(FR, key + ".rgb")
        if not os.path.exists(p):
            os.makedirs(FR, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", p + ".part"], check=True)
            os.replace(p + ".part", p)
        n = os.path.getsize(p) // (w * h * 3)
        self.frames = np.memmap(p, dtype=np.uint8, mode="r", shape=(n, h, w, 3))
        self.n, self.w, self.h = n, w, h

    def frame(self, ts):
        x = max(0.0, min(ts * 24.0, self.n - 1.001))
        i = int(x)
        f = x - i
        a = self.frames[i].astype(np.float32)
        if f > 0.02:
            a = a * (1 - f) + self.frames[i + 1].astype(np.float32) * f
        return a


def zoom_grid(h, w, z, u, v):
    s = max(W / w, H / h)
    cw, ch = W / s / z, H / s / z
    cx = min(max(u * w, cw / 2), w - cw / 2)
    cy = min(max(v * h, ch / 2), h - ch / 2)
    gx = cx - cw / 2 + np.linspace(0, cw, W, dtype=np.float32)[None, :].repeat(H, 0)
    gy = cy - ch / 2 + np.linspace(0, ch, H, dtype=np.float32)[:, None].repeat(W, 1)
    return gx, gy


def blurred_fill(fr, r=26, dark=0.55):
    im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8))
    sm = im.resize((W // 6, H // 6), Image.BILINEAR) if im.width / im.height < W / H else \
        im.crop(((im.width - im.height * W // H) // 2, 0, (im.width + im.height * W // H) // 2, im.height)).resize((W // 6, H // 6), Image.BILINEAR)
    sm = sm.filter(ImageFilter.GaussianBlur(r / 6))
    return np.asarray(sm.resize((W, H), Image.BILINEAR), np.float32) * dark


def scene_frame(A, i, t):
    kind, key, s, e, ex = SCENES[i]
    p = min(1.0, max(0.0, (t - s) / (e - s)))
    if kind == "clip":
        cl = A["clips"][key]
        fr = cl.frame(ex["src"] + (t - s) * ex["speed"])
        gx, gy = zoom_grid(cl.h, cl.w, ex["z0"] + (ex["z1"] - ex["z0"]) * ease_in_out(p), ex["u"], ex["v"])
        return bilinear(fr, gx, gy)
    if kind == "fitclip":
        # §49.5: the whole clip stays visible (face + phone); width fits, a blurred darker copy fills the rest
        cl = A["clips"][key]
        ts = ex["src"] + (t - s) * ex["speed"]
        fr = cl.frame(ts)
        extra = max(0.0, ts - (cl.n - 1) / 24.0)          # after the clip ends: hold + keep pushing in gently
        z = 1.0 + 0.05 * min(1.0, ts / 5.0) + 0.06 * ease_in_out(min(1.0, extra / 5.0))
        out = blurred_fill(fr)
        fw = int(W * z)
        fh = int(cl.h * fw / cl.w)
        sm = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize((fw, fh), Image.BILINEAR)
        x0 = (W - fw) // 2
        top = ex["top"] - (fh - int(cl.h * W / cl.w)) * 0.75
        im = Image.fromarray(out.astype(np.uint8))
        # feathered edges top/bottom so the plate melts into its blurred copy
        m = np.ones((fh, fw), np.float32)
        ramp = np.clip(np.arange(fh, dtype=np.float32) / 70, 0, 1)
        m *= ramp[:, None] * ramp[::-1][:, None]
        im.paste(sm, (x0, int(top)), Image.fromarray((m * 255).astype(np.uint8), "L"))
        return np.asarray(im, np.float32)
    if kind == "blurclip":
        cl = A["clips"][key]
        fr = cl.frame(ex["src"] + (t - s) * ex["speed"])
        gx, gy = zoom_grid(cl.h, cl.w, 1.0 + 0.06 * ease_in_out(p), 0.5, 0.55)
        im = Image.fromarray(np.clip(bilinear(fr, gx, gy), 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
        im = im.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
        return np.asarray(im, np.float32) * 0.62
    return render_still(A["S"][key], key, p)


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
    # living layer: warm lamp bokeh drifting in the foreground + fine floating dust in the light
    for (x, y, r, ph) in A["bokeh"]:
        put(f, A["bk"][r], x + 34 * math.sin(t * 0.21 + ph) - r, y + 22 * math.cos(t * 0.16 + ph) - r, 0.16 + 0.08 * math.sin(t * 0.9 + ph))
    for (x, y, spd, ph, a) in A["dust"]:
        put(f, A["mote"], (x + 18 * math.sin(t * 0.5 + ph)) % W, (y - spd * t) % H, a * (0.6 + 0.4 * math.sin(t * 1.3 + ph)))
    return f, act


def glow_dot(r, color):
    S = int(r * 6)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse((S / 2 - r * 1.6, S / 2 - r * 1.6, S / 2 + r * 1.6, S / 2 + r * 1.6), fill=160)
    im = Image.new("RGBA", (S, S), color + (0,))
    im.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.9)))
    ImageDraw.Draw(im).ellipse((S / 2 - r * 0.5, S / 2 - r * 0.5, S / 2 + r * 0.5, S / 2 + r * 0.5), fill=(255, 255, 255, 240))
    return im


def ring(f, x, y, r, color, a):
    if a < 0.02:
        return
    S = int(2 * r + 12)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((6, 6, S - 6, S - 6), outline=color + (int(255 * a),), width=3)
    f.alpha_composite(im, (int(x - S / 2), int(y - S / 2)))


def point(f, A, x, y, t, t0):
    if t < t0:
        return
    p = ease_out(prog(t, t0, 0.45))
    s = p * (0.84 + 0.16 * math.sin((t - t0) * 3.1))
    d = A["dot"]
    im = d.resize((max(1, int(d.width * s)), max(1, int(d.height * s))), Image.LANCZOS)
    put(f, im, x - im.width / 2, y - im.height / 2, p)
    for k in range(3):
        rp = prog(t, t0 + 0.5 * k, 1.2)
        if 0 < rp < 1:
            ring(f, x, y, 14 + 60 * ease_out(rp), TEAL, (1 - rp) * 0.85)


def build():
    A = {"clips": {k: Clip(k) for k in {sc[1] for sc in SCENES if sc[0] in ("clip", "fitclip", "blurclip")}},
         "S": {k: build_still(k) for k in {sc[1] for sc in SCENES if sc[0] == "still"}}}
    rng = np.random.default_rng(66)
    A["grain"] = [rng.normal(0, 2.0, (H, W, 1)).astype(np.float32) for _ in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    A["vig"] = (1 - 0.24 * np.clip(((xx - W / 2) / W) ** 2 * 2.4 + ((yy - H / 2) / H) ** 2 * 2.0, 0, 1))[..., None]
    A["bk"] = {}
    for r in (45, 80):
        m = Image.new("L", (2 * r, 2 * r), 0)
        ImageDraw.Draw(m).ellipse((r * 0.2, r * 0.2, r * 1.8, r * 1.8), fill=150)
        im = Image.new("RGBA", (2 * r, 2 * r), (255, 208, 146, 0))
        im.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.28)))
        A["bk"][r] = im
    A["bokeh"] = [(rng.uniform(0, W), rng.uniform(0, H), int(rng.choice([45, 80])), rng.uniform(0, 6.28)) for _ in range(6)]
    m = Image.new("L", (14, 14), 0)
    ImageDraw.Draw(m).ellipse((4, 4, 10, 10), fill=220)
    A["mote"] = Image.new("RGBA", (14, 14), (255, 230, 190, 0))
    A["mote"].putalpha(m.filter(ImageFilter.GaussianBlur(1.6)))
    A["dust"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(8, 26), rng.uniform(0, 6.28), rng.uniform(0.25, 0.6)) for _ in range(38)]
    A["dot"] = glow_dot(13, TEAL)
    logo = Image.open(LOGO).convert("RGBA")
    logo = logo.crop(logo.getchannel("A").getbbox())     # trim transparent margin only (logo itself untouched)
    A["logo"] = logo.resize((520, round(logo.height * 520 / logo.width)), Image.LANCZOS)
    A["logo_s"] = logo.resize((290, round(logo.height * 290 / logo.width)), Image.LANCZOS)

    # 1 hook
    A["stress"] = T("STRESS", mano(150, 700), IVORY, tracking=18)
    A["can"] = T("can raise your", pin(104), "champ")
    A["sugar"] = T("blood sugar?", news(124, 430), IVORY)
    # 2 pancreas
    A["panc"] = T("PANCREAS", mano(64, 700), IVORY, tracking=16)
    A["ins"] = T("makes insulin", news(96, 400, italic=True), "champ")
    # 3 stress hormones
    A["cort"] = T("CORTISOL", mano(58, 700), IVORY, tracking=14)
    A["adr"] = T("ADRENALINE", mano(58, 700), IVORY, tracking=14)
    A["glu"] = T("more glucose in your blood", news(66, 400, italic=True), "champ")
    # 4 feet
    A["nerves"] = T("nerves in your feet", pin(100), "champ")
    A["sym"] = [T(w, news(110, 430), IVORY) for w in ("Tingling.", "Numbness.", "Burning.")]
    # 5 chart
    A["map"] = T("in reflexology maps", pin(96), "champ")
    A["prx"] = T("PANCREAS REFLEX", mano(48, 700), IVORY, tracking=12)
    A["arch"] = T("in the arch of the foot", news(58, 400, italic=True), IVORY)
    # 6 gentle
    A["first"] = T("Feet checked first", news(82, 420), IVORY)
    A["gentle"] = T("gentle pressure", pin(118), "champ")
    # 7 relax
    A["relax"] = T("relax", pin(190), "champ")
    A["may"] = T("MAY HELP YOUR BODY", mano(44, 700), IVORY, tracking=14)
    A["self"] = T("easing stress is everyday self-care", news(50, 400, italic=True), IVORY)
    # 8 observation
    A["prac"] = T("In Zarina's practice", pin(92), "champ")
    A["pct"] = T("5–15%", news(170, 470), "champ")
    A["lower"] = T("lower glucose readings after a session", news(46, 400, italic=True), IVORY)
    A["obs"] = T("PRACTITIONER OBSERVATION  ·  RESULTS VARY", mano(27, 600), IVORY, tracking=5)
    A["ins1"] = T("Use insulin?", news(92, 430), IVORY)
    A["ins2"] = T("CHECK YOUR GLUCOSE BEFORE & AFTER", mano(36, 700), "champ", tracking=6)
    # 9 alongside
    A["repl"] = T("doesn't replace", news(84, 420), IVORY)
    A["care"] = T("your diabetes care", news(84, 420, italic=True), IVORY)
    A["along"] = T("it works alongside it", pin(104), "champ")
    # 10 end card
    A["zr"] = T("Zarina, RCRT", news(112, 430), IVORY)
    A["ther"] = T("your reflexology therapist", pin(86), "champ")
    A["dm"] = T("SEND US A DM TO BOOK", mano(38, 700), IVORY, tracking=10)
    A["addr"] = T("2020 Corydon Ave  ·  Winnipeg", mano(32, 500), IVORY, tracking=3)
    A["drama"] = T("Dramatized story", mano(24, 500), IVORY, tracking=2)
    return A


def fade(t, s, e, fi=0.45, fo=0.4):
    return ease_out(prog(t, s, fi)) * (1 - ease_in_out(prog(t, e - fo, fo)))


def soft_wash(f, y0, y1, a, k=0.6):
    wash(f, y0, y0 + (y1 - y0) * 0.4, NIGHT, 0.0, k * a)
    wash(f, y0 + (y1 - y0) * 0.4, y1, NIGHT, k * a, (k + 0.08) * a)


def top_wash(f, y1, a, k=0.55):
    wash(f, 0, y1, NIGHT, k * a, 0.0)


# Text layout (§49): safe area x 60…960, y 250…1580; lower third by default (≈1180–1560), upper band only when
# the subject fills the lower half. Never over faces, hands at work, feet or the phone being shown.
def frame_at(t, A):
    f, act = background(A, t)
    cx = W / 2
    # 1 · hook — face above, text in the lower third over the knit wrap
    if t < 2.85:
        a = fade(t, 0, 2.75, 0.5, 0.35)
        soft_wash(f, 1020, H, a)
        letters(f, A["stress"], cx - A["stress"].adv / 2, 1260, 0.25, t, a, step=0.04)
        wipe(f, A["can"], cx - A["can"].adv / 2, 1385, prog(t, at("raise") - 0.25, 0.7), a)
        p = prog(t, at("blood") - 0.2, 0.6)
        if p > 0:
            sharp_in(f, A["sugar"], cx - A["sugar"].adv / 2, 1530, p, a, scale_from=1.05, blur=10)
    # 2 · pancreas — organ in the upper middle, text low
    if 2.55 <= t < 5.7:
        a = fade(t, 2.55, 5.65)
        soft_wash(f, 1080, H, a, 0.72)
        letters(f, A["panc"], cx - A["panc"].adv / 2, 1370, at("pancreas") - 0.05, t, a, step=0.035)
        p = prog(t, at("insulin") - 0.2, 0.7)
        if p > 0:
            put_shine(f, A["ins"], cx - A["ins"].adv / 2, 1490 + 10 * (1 - ease_out(p)), a * ease_out(p), prog(t, at("insulin") + 0.4, 1.2))
    # 3 · cortisol + adrenaline — camera on the sensor (lower half), words in the upper band beside the face
    if 5.45 <= t < 10.3:
        a = fade(t, 5.45, 10.25)
        soft_wash(f, 1100, H, a, 0.62)
        slide(f, A["cort"], cx - A["cort"].adv / 2, 1300, prog(t, at("cortisol") - 0.15, 0.6), a, dx=-70)
        slide(f, A["adr"], cx - A["adr"].adv / 2, 1385, prog(t, at("adrenaline") - 0.1, 0.6), a, dx=70)
        wipe(f, A["glu"], cx - A["glu"].adv / 2, 1500, prog(t, at("glucose") - 0.25, 0.9), a)
    # 4 · feet — face top-left, foot centre-right: words on the right of the head, upper band
    if 10.15 <= t < 16.5:
        a = fade(t, 10.15, 16.45)
        soft_wash(f, 1180, H, a, 0.55)
        wipe(f, A["nerves"], cx - A["nerves"].adv / 2, 1330, prog(t, at("nerves") - 0.3, 0.9), a)
        ws = ("tingling", "numbness", "burning")
        for k, w in enumerate(ws):            # one word at a time, swapped in sync with the voice
            tx = A["sym"][k]
            t0 = at(w) - 0.15
            out = 1 - ease_in_out(prog(t, at(ws[k + 1]) - 0.3, 0.25)) if k < 2 else 1.0
            sharp_in(f, tx, cx - tx.adv / 2, 1490, prog(t, t0, 0.45), a * out, scale_from=1.08, blur=9)
    # 5 · chart — Zarina + map up top; glowing reflex point on the highlighted pancreas reflex
    if 16.35 <= t < 20.6:
        a = fade(t, 16.35, 20.55)
        S = A["S"]["chart"]
        p = (t - 16.35) / (20.55 - 16.35)
        sx, sy = to_screen(S, "chart", p, *PANC_CHART)
        point(f, A, sx, sy, t, at("pancreas", 17.0) - 0.05)
        soft_wash(f, 1150, H, a, 0.62)
        wipe(f, A["map"], cx - A["map"].adv / 2, 1300, prog(t, at("reflexology", 16.0) - 0.1, 0.9), a)
        letters(f, A["prx"], cx - A["prx"].adv / 2, 1405, at("pancreas", 17.0) - 0.05, t, a, step=0.03)
        rise(f, A["arch"], cx - A["arch"].adv / 2, 1500, prog(t, at("arch") - 0.2, 0.6), a)
    # 6 · gentle — hands in the middle, towel below: lower third
    if 20.45 <= t < 25.6:
        a = fade(t, 20.45, 25.55)
        soft_wash(f, 1200, H, a, 0.6)
        sharp_in(f, A["first"], cx - A["first"].adv / 2, 1400, prog(t, at("checks") - 0.2, 0.7), a, blur=8)
        p = prog(t, at("pressure") - 0.3, 0.8)
        if p > 0:
            put_shine(f, A["gentle"], cx - A["gentle"].adv / 2, 1535 + 10 * (1 - ease_out(p)), a * ease_out(p), prog(t, at("gentle") + 0.2, 1.3))
    # 7 · relax — face top, hands mid; text low over the blanket
    if 25.45 <= t < 31.35:
        a = fade(t, 25.45, 31.3)
        soft_wash(f, 1250, H, a, 0.55)
        sw = at("easing") - 0.3
        a1 = a * (1 - ease_in_out(prog(t, sw - 0.3, 0.3)))
        letters(f, A["may"], cx - A["may"].adv / 2, 1400, at("may") - 0.1, t, a1, step=0.025)
        p = prog(t, at("relax") - 0.3, 0.9)
        if p > 0:
            put_shine(f, A["relax"], cx - A["relax"].adv / 2, 1555, a1 * ease_out(p), prog(t, at("relax") + 0.3, 1.4))
        rise(f, A["self"], cx - A["self"].adv / 2, 1500, prog(t, sw, 0.6), a * ease_out(prog(t, sw, 0.4)))
    # 8 · observation + insulin safety — whole clip visible (face + phone), text in the blurred band beneath it
    if 31.2 <= t < 44.45:
        a = fade(t, 31.2, 44.4)
        soft_wash(f, 1300, H, a, 0.5)
        sw = at("If") - 0.35
        a1 = a * (1 - ease_in_out(prog(t, sw - 0.35, 0.35)))
        a2 = a * ease_out(prog(t, sw, 0.45))
        pr = ease_out(prog(t, at("practice") - 0.6, 0.8)) * (1 - ease_in_out(prog(t, at("5") - 0.55, 0.35)))
        wipe(f, A["prac"], cx - A["prac"].adv / 2, 1450, prog(t, at("practice") - 0.6, 0.8), a1 * (pr if t < at("5") else 0))
        tp = at("5") - 0.2
        sharp_in(f, A["pct"], cx - A["pct"].adv / 2, 1460, prog(t, tp, 0.7), a1, scale_from=0.92, blur=10)
        if t > tp + 0.8:
            put_shine(f, A["pct"], cx - A["pct"].adv / 2, 1460, a1, prog(t, tp + 0.8, 1.3))
        rise(f, A["lower"], cx - A["lower"].adv / 2, 1530, prog(t, at("lower") - 0.2, 0.6), a1 * (1 - ease_in_out(prog(t, at("Results") - 0.3, 0.3))))
        letters(f, A["obs"], cx - A["obs"].adv / 2, 1530, at("Results") - 0.15, t, a1, step=0.012)
        sharp_in(f, A["ins1"], cx - A["ins1"].adv / 2, 1450, prog(t, sw + 0.1, 0.6), a2, blur=8)
        letters(f, A["ins2"], cx - A["ins2"].adv / 2, 1535, at("check", 40.0) - 0.1, t, a2, step=0.018)
    # 9 · alongside — soft storefront mood, the OFFICIAL logo sharp on top
    if 44.3 <= t < 49.05:
        a = fade(t, 44.3, 49.0)
        lg = A["logo"]
        pl = ease_out(prog(t, 44.5, 0.9))
        put(f, lg, cx - lg.width / 2, 560 - lg.height / 2 + 14 * (1 - pl), a * pl)
        drop(f, A["repl"], cx - A["repl"].adv / 2, 1180, prog(t, at("replace") - 0.3, 0.7), a)
        drop(f, A["care"], cx - A["care"].adv / 2, 1290, prog(t, at("diabetes", 44.0) - 0.2, 0.7), a)
        p = prog(t, at("alongside") - 0.2, 0.9)
        if p > 0:
            put_shine(f, A["along"], cx - A["along"].adv / 2, 1450 + 10 * (1 - ease_out(p)), a * ease_out(p), prog(t, at("alongside") + 0.3, 1.3))
    # 10 · end card — portrait; frosted lower part, small official logo, name, DM, address
    if t >= 48.9:
        a = ease_out(prog(t, 48.9, 0.7))
        fr = ease_in_out(prog(t, 49.0, 1.0))
        if fr > 0.01:
            low = f.crop((0, 980, W, H)).filter(ImageFilter.GaussianBlur(18 * fr))
            ramp = np.clip(np.arange(H - 980, dtype=np.float32) / 200.0, 0, 1)[:, None].repeat(W, 1)
            f.paste(low, (0, 980), Image.fromarray((ramp * 255).astype(np.uint8), "L"))
        wash(f, 980, 1180, NIGHT, 0.0, 0.7 * a)
        wash(f, 1180, H, NIGHT, 0.7 * a, 0.8 * a)
        tz = at("Send") - 0.2
        sharp_in(f, A["zr"], cx - A["zr"].adv / 2, 1170, prog(t, 49.2, 0.7), 1.0, blur=8)
        wipe(f, A["ther"], cx - A["ther"].adv / 2, 1258, prog(t, 49.7, 0.9))
        letters(f, A["dm"], cx - A["dm"].adv / 2, 1340, tz, t, step=0.02)
        lg = A["logo_s"]
        pl = ease_out(prog(t, at("Advanced", 50.0) - 0.4, 0.8))
        put(f, lg, cx - lg.width / 2, 1385 + 8 * (1 - pl), pl)
        line(f, cx, 1365, 300 * ease_in_out(prog(t, tz + 0.6, 0.7)), GOLD_LINE, 0.8, thick=2)
        p = ease_out(prog(t, at("Therapy", 50.0) + 0.1, 0.6))
        put_c(f, A["addr"], 1580, p, dy=10 * (1 - p))
    # small legal note on dramatized client scenes (§49.2 exception)
    da = max(fade(t, 0.0, 2.75, 0.6, 0.35), fade(t, 5.45, 10.25), fade(t, 10.15, 16.45), fade(t, 31.2, 44.4)) * 0.62
    if da > 0.01:
        put_c(f, A["drama"], 1650, da)
    # opening: from blur into reality; ending: back into a soft blur
    bi = 1 - ease_out(prog(t, 0.0, 1.0))
    bo = ease_in_out(prog(t, DURATION - 1.5, 1.5))
    b = max(bi, bo)
    if b > 0.01:
        f = f.filter(ImageFilter.GaussianBlur(24 * b))
        if bo > 0.01:
            f.alpha_composite(Image.new("RGBA", (W, H), (240, 232, 220, int(80 * bo))))
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
    rng = np.random.default_rng(1966)
    tmp = os.path.join(OUT_DIR, ".diab_voice48.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(AUD, "zara-voiceover.mp3"), "-ac", "1", "-ar", str(sr), tmp], check=True)
    v, vsr = sf.read(tmp)
    os.remove(tmp)
    assert vsr == sr
    voice = np.zeros(n)
    m = min(len(v), n)
    voice[:m] = v[:m]
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.95
    mus = np.zeros(n)

    def add(at_, sig):
        i = int(at_ * sr)
        if i >= n:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        k = min(len(sig), n - i)
        mus[i:i + k] += sig[:k]

    BPM = 66
    BEAT = 60 / BPM
    BAR = 4 * BEAT
    hz = lambda m_: 440.0 * 2 ** ((m_ - 69) / 12)   # noqa: E731
    # C minor -> E-flat major: Cm9 · A♭maj7 · E♭ · B♭sus (then E♭ resolves at the payoff)
    CH = [(36, [60, 63, 67, 70, 74]), (32, [60, 63, 67, 68, 72]), (39, [58, 63, 67, 70, 75]), (34, [58, 62, 65, 70, 72])]

    def pad(f0, L):
        tt = np.arange(L) / sr
        sig = np.zeros(L)
        for k in range(1, 9):
            det = 1 + 0.0025 * (k % 3 - 1)
            sig += np.sin(2 * np.pi * f0 * k * det * tt + k) / k ** 1.4
        return sig

    def knock(f0=520):
        L = int(0.35 * sr)
        tt = np.arange(L) / sr
        body = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 28) + 0.5 * np.sin(2 * np.pi * f0 * 2.3 * tt) * np.exp(-tt * 45)
        click = rng.normal(0, 1, L) * np.exp(-tt * 400) * 0.3
        return body + click

    def brush(L=0.5):
        Ln = int(L * sr)
        x = rng.normal(0, 1, Ln)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(Ln, 1 / sr)
        X *= np.exp(-((fr - 5200) / 2600) ** 2)
        y = np.fft.irfft(X, Ln)
        tt = np.arange(Ln) / sr
        return y / (np.abs(y).max() + 1e-9) * np.sin(np.pi * np.clip(tt / L, 0, 1)) ** 2

    def swell(L=1.2):
        Ln = int(L * sr)
        x = rng.normal(0, 1, Ln)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(Ln, 1 / sr)
        X *= np.exp(-((fr - 1800) / 1500) ** 2)
        y = np.fft.irfft(X, Ln)
        tt = np.arange(Ln) / sr
        return y / (np.abs(y).max() + 1e-9) * (tt / L) ** 2.5

    nb = int(DURATION / BAR) + 1
    for b in range(nb):
        root, voi = CH[b % 4]
        t0 = b * BAR
        L = int((BAR + 1.5) * sr)
        tt = np.arange(L) / sr
        env = np.clip(tt / 1.4, 0, 1) * np.clip((BAR + 1.5 - tt) / 1.3, 0, 1)
        for nn in voi[:3]:
            add(t0 - 0.2, 0.020 * env * pad(hz(nn), L))
        tt2 = np.arange(int(BAR * sr)) / sr
        add(t0, 0.22 * np.sin(2 * np.pi * hz(root) * tt2) * np.exp(-tt2 * 0.6))
        # harp-like arpeggio: 8th notes up and down the chord, gently humanised
        arp = voi + voi[-2:0:-1]
        for j in range(8):
            nn = arp[j % len(arp)] + (12 if j in (3, 4) else 0)
            add(t0 + j * BEAT / 2 + rng.uniform(-0.008, 0.008), 0.11 * ks(hz(nn), 2.2, sr, bright=0.45, decay=0.9975, seed=b * 8 + j))
        if t0 > 2.5:
            for j in (1, 3):
                add(t0 + j * BEAT - 0.15, 0.035 * brush())
    for at_ in [0.25, at("pancreas") - 0.05, at("cortisol") - 0.15, at("tingling") - 0.15, at("pancreas", 17.0) - 0.05,
                at("pressure") - 0.3, at("relax") - 0.3, at("5") - 0.2, at("If") - 0.25, at("alongside") - 0.2, at("Send") - 0.2]:
        add(at_, 0.09 * knock(520 + 60 * rng.integers(0, 3)))
    for sc in SCENES[1:]:
        add(sc[2] - 1.0, 0.045 * swell())
    music = mus / (np.abs(mus).max() + 1e-9)
    env = np.convolve(np.abs(voice), np.ones(int(0.25 * sr)) / int(0.25 * sr), mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    gain = 0.30 - 0.17 * env
    room = rng.normal(0, 1, n)
    room = np.convolve(room, np.ones(64) / 64, mode="same") * 0.004
    st = np.stack([voice + music * gain + room, voice + np.roll(music, int(0.011 * sr)) * gain + np.roll(room, 977)], 1)
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
        ts = [float(x) for x in sys.argv[2:]] or [0.3, 2.3, 4.6, 8.8, 15.4, 19.5, 24.5, 30.0, 37.0, 39.8, 43.0, 47.8, 55.2]
        for s in ts:
            Image.fromarray(frame_at(s, A)).save(os.path.join(OUT_DIR, "qc", f"db-{s:05.2f}s.png"))
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
    Image.fromarray(frame_at(2.3, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(NAME, DURATION)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
