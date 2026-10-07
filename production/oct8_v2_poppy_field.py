"""Available Appointments — Thursday, October 8, 2026 — v2 "Poppy Field".

Hook: a direct question ("What are you waiting for?") + honest urgency (only 2 times).
Background: golden-hour poppy field with wheat ears moving in the wind (procedural).
Type: Oswald (bold condensed) + Cormorant Garamond Italic accent + Montserrat.
Palette: poppy red + charcoal + warm white.

  python3 production/oct8_v2_poppy_field.py stills
  python3 production/oct8_v2_poppy_field.py video
"""
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poppy_field import W, H, build as build_field, render as render_field  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")
LOGO = os.path.join(ROOT, "brand", "the-pure-escape-logo.png")
OUT_DIR = os.path.join(ROOT, "content", "videos")
NAME = "2026-10-08-available-appointments-v2"
FPS = 30
DURATION = 22.0

RED = (190, 34, 30)
INK = (34, 28, 28)
CREAM = (255, 249, 240)

# ---------------------------------------------------------------- facts (never edit without the owner)
DAY, MONTH, DAYNUM = "THURSDAY", "October", "8"
TIMES = [("5:30", "p.m."), ("6:45", "p.m.")]
SERVICES = [("Foot", " Reflexology", None), ("Hand", " Reflexology", None),
            ("Facial", " Reflexology", "Bergman Method"), ("Spanish", " Massage", None),
            ("Ultimate Escape", " Package", None)]
THERAPIST = "Zarina, RCRT"
ADDRESS = "698 Corydon Ave"


def vfont(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if var:
        f.set_variation_by_name(var)
    return f


def osw(size, var="Bold"):
    return vfont("Oswald[wght].ttf", size, var)


def cor_i(size, var="SemiBold Italic"):
    return vfont("CormorantGaramond-Italic[wght].ttf", size, var)


def mont(size, var="SemiBold"):
    return vfont("Montserrat[wght].ttf", size, var)


class Text:
    def __init__(self, txt, fnt, fill, tracking=0):
        kw = {"features": ["lnum"]}
        asc, desc = fnt.getmetrics()
        pad = int(fnt.size * 0.3)
        width = (sum(fnt.getlength(c, **kw) for c in txt) + tracking * (len(txt) - 1)) if tracking else fnt.getlength(txt, **kw)
        self.img = Image.new("RGBA", (math.ceil(width) + 2 * pad, asc + desc + pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        if tracking:
            x = pad
            for c in txt:
                d.text((x, asc), c, font=fnt, fill=fill, anchor="ls", **kw)
                x += fnt.getlength(c, **kw) + tracking
        else:
            d.text((pad, asc), txt, font=fnt, fill=fill, anchor="ls", **kw)
        self.asc, self.pad, self.adv = asc, pad, width
        self.w, self.h = self.img.size


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def ease_back(p):
    p = min(max(p, 0.0), 1.0)
    c = 1.4
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def ease_in_out(p):
    p = min(max(p, 0.0), 1.0)
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def prog(t, s, d):
    return min(max((t - s) / d, 0.0), 1.0)


def with_alpha(img, a):
    if a >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


def put(f, img, x, y, a=1.0):
    if a > 0.003:
        f.alpha_composite(with_alpha(img, a), (int(round(x)), int(round(y))))


def put_text(f, tx, x, base, a=1.0, dy=0.0):
    put(f, tx.img, x - tx.pad, base - tx.asc + dy, a)


def slam(f, tx, cx, base, p, a=1.0, dy=0.0):
    """Scale-down 'slam' entrance, centred on cx."""
    if p <= 0:
        return
    s = 1.0 + 0.35 * (1 - ease_back(p))
    img = tx.img if abs(s - 1) < 0.003 else tx.img.resize((int(tx.w * s), int(tx.h * s)), Image.LANCZOS)
    x = cx - (tx.adv / 2 + tx.pad) * s
    y = base - tx.asc * s + dy
    put(f, img, x, y, min(1, p * 2.5) * a)


def rise(f, tx, x, base, p, a=1.0, dy=0.0):
    if p <= 0:
        return
    if p >= 1:
        return put_text(f, tx, x, base, a, dy)
    off = (1 - ease_out(p)) * tx.h * 0.9
    vis = int(tx.h - off)
    if vis > 0:
        put(f, tx.img.crop((0, 0, tx.w, vis)), x - tx.pad, base - tx.asc + off + dy, a)


def rect(f, x, y, w, h, color, a=1.0):
    if w > 0.5 and h > 0.5 and a > 0:
        f.alpha_composite(Image.new("RGBA", (int(w), int(h)), color + (int(255 * a),)), (int(x), int(y)))


def soft_scrim(f, y0, y1, a):
    """Warm-white veil behind type, feathered top and bottom, for contrast on the sky."""
    if a <= 0:
        return
    h = int(y1 - y0)
    col = np.zeros((h, 1), np.float32)
    u = np.linspace(0, 1, h)
    col[:, 0] = np.clip(np.minimum(u / 0.25, (1 - u) / 0.25), 0, 1) * 0.42 * a
    m = Image.fromarray((np.repeat(col, W, 1) * 255).astype(np.uint8), "L")
    veil = Image.new("RGBA", (W, h), CREAM + (0,))
    veil.putalpha(m)
    f.alpha_composite(veil, (0, int(y0)))


def poppy_dot(size):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        cx, cy = s / 2 + math.cos(a) * s * .17, s / 2 + math.sin(a) * s * .17
        d.ellipse((cx - s * .27, cy - s * .27, cx + s * .27, cy + s * .27), fill=RED + (255,))
    d.ellipse((s * .38, s * .38, s * .62, s * .62), fill=INK + (255,))
    return im.resize((size, size), Image.LANCZOS)


def build():
    A = {"F": build_field()}
    A["what"] = Text("WHAT ARE YOU", osw(124, "SemiBold"), INK, tracking=2)
    A["waiting"] = Text("waiting", cor_i(250), RED)
    A["for"] = Text("FOR?", osw(270), INK)
    A["only_a"] = Text("Only ", mont(44, "Medium"), INK)
    A["only_2"] = Text("2", mont(44, "Bold"), RED)
    A["only_b"] = Text(" evening times left this Thursday", mont(44, "Medium"), INK)

    A["day"] = Text(DAY, osw(70, "Medium"), INK, tracking=14)
    A["date"] = Text(f"{MONTH} {DAYNUM}", cor_i(124), RED)
    tf = osw(270)
    A["times"] = []
    for num, suf in TIMES:
        chars, x = [], 0
        for ch in num:
            chars.append((x, Text(ch, tf, INK)))
            x += tf.getlength(ch)
        A["times"].append((chars, x, Text(suf, mont(66, "SemiBold"), RED)))

    A["all"] = Text("ALL 5 SERVICES", osw(84, "SemiBold"), INK, tracking=3)
    A["open"] = Text("open on Thursday", cor_i(84), RED)
    A["dot"] = poppy_dot(40)
    A["svc"] = [(Text(b, mont(52, "Bold"), INK), Text(r, mont(52, "Regular"), INK),
                 Text(sub, cor_i(46), RED) if sub else None) for b, r, sub in SERVICES]

    A["dont"] = Text("DON'T WAIT.", osw(176), RED)
    A["before"] = Text("Book before it's gone", cor_i(96), INK)
    logo = Image.open(LOGO).convert("RGBA")
    lw = 520
    A["logo"] = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    A["who"] = Text(f"{THERAPIST}  ·  {ADDRESS}", mont(40, "Medium"), INK)
    A["end_date"] = Text(f"Thursday, {MONTH} {DAYNUM}", mont(44, "Bold"), RED)
    A["end_times"] = Text(f"{TIMES[0][0]} {TIMES[0][1]}  ·  {TIMES[1][0]} {TIMES[1][1]}", mont(44, "Bold"), INK)
    A["cta"] = Text("BOOK NOW", osw(58, "SemiBold"), CREAM, tracking=6)
    return A


def frame_at(t, A):
    f = render_field(t, A["F"], sun_amt=0.55 + 0.45 * ease_in_out(prog(t, 0, 2.0)))
    cx = W / 2

    # ---- Beat 1: hook question (0 – 4.3)
    if t < 4.4:
        q = ease_in_out(prog(t, 3.9, 0.45))
        a, dy = 1 - q, -70 * q
        soft_scrim(f, 330, 1210, ease_out(prog(t, 0.0, 0.4)) * a)
        slam(f, A["what"], cx, 540, prog(t, 0.15, 0.4), a, dy)
        slam(f, A["waiting"], cx, 770, prog(t, 0.55, 0.45), a, dy)
        slam(f, A["for"], cx, 1085, prog(t, 0.95, 0.45), a, dy)
        p = ease_out(prog(t, 1.9, 0.5))
        tot = A["only_a"].adv + A["only_2"].adv + A["only_b"].adv
        x = cx - tot / 2
        for k in ("only_a", "only_2", "only_b"):
            put_text(f, A[k], x, 1160 + 20 * (1 - p), p * a, dy)
            x += A[k].adv
        uw = (A["only_2"].adv + 14) * ease_in_out(prog(t, 2.3, 0.5))
        x2 = cx - tot / 2 + A["only_a"].adv + A["only_2"].adv / 2
        rect(f, x2 - uw / 2, 1172 + dy, uw, 5, RED, a)

    # ---- Beat 2: date + times (4.3 – 9.7)
    if 4.3 <= t < 9.8:
        q = ease_in_out(prog(t, 9.25, 0.45))
        a, dy = 1 - q, -70 * q
        soft_scrim(f, 300, 1220, ease_out(prog(t, 4.3, 0.4)) * a)
        p = ease_out(prog(t, 4.35, 0.5))
        put_text(f, A["day"], cx - A["day"].adv / 2, 420 + 20 * (1 - p), p * a, dy)
        rise(f, A["date"], cx - A["date"].adv / 2, 560, prog(t, 4.6, 0.6), a, dy)
        for i, (chars, adv, suf) in enumerate(A["times"]):
            st = 5.0 + 0.7 * i
            base = 850 + 295 * i
            tot = adv + 22 + suf.adv
            x = cx - tot / 2
            for k, (ox, ch) in enumerate(chars):
                rise(f, ch, x + ox, base, prog(t, st + 0.06 * k, 0.55), a, dy)
            ps = ease_out(prog(t, st + 0.4, 0.45))
            put_text(f, suf, x + adv + 22 - 24 * (1 - ps), base, ps * a, dy)
            L = tot * ease_in_out(prog(t, st + 0.3, 0.6))
            rect(f, x, base + 30 + dy, L, 6, RED, 0.85 * a)

    # ---- Beat 3: all services (9.7 – 15.5)
    if 9.7 <= t < 15.6:
        q = ease_in_out(prog(t, 15.05, 0.45))
        a, dy = 1 - q, -70 * q
        soft_scrim(f, 300, 1220, ease_out(prog(t, 9.7, 0.4)) * a)
        slam(f, A["all"], cx, 450, prog(t, 9.75, 0.45), a, dy)
        rise(f, A["open"], cx - A["open"].adv / 2, 560, prog(t, 10.1, 0.6), a, dy)
        base = 690
        for i, (b, r, sub) in enumerate(A["svc"]):
            p = ease_out(prog(t, 10.5 + 0.28 * i, 0.5))
            tot = 40 + 20 + b.adv + r.adv
            x = cx - tot / 2 - 30 * (1 - p)
            put(f, A["dot"], x, base - 38 + dy, p * a)
            put_text(f, b, x + 60, base, p * a, dy)
            put_text(f, r, x + 60 + b.adv, base, p * a, dy)
            if sub:
                put_text(f, sub, cx - sub.adv / 2, base + 56, p * a, dy)
                base += 56
            base += 98

    # ---- Beat 4: urgency CTA (15.5 – end)
    if t >= 15.5:
        soft_scrim(f, 330, 1210, ease_out(prog(t, 15.5, 0.4)))
        slam(f, A["dont"], cx, 560, prog(t, 15.55, 0.45))
        rise(f, A["before"], cx - A["before"].adv / 2, 680, prog(t, 16.0, 0.6))
        p = ease_out(prog(t, 16.6, 0.7))
        cy0 = 740 + 40 * (1 - p)
        card = Image.new("RGBA", (920 * 2, 460 * 2), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((0, 0, 1839, 919), 80, fill=CREAM + (228,))
        put(f, card.resize((920, 460), Image.LANCZOS), (W - 920) / 2, cy0, p)
        lg = A["logo"]
        put(f, lg, (W - lg.width) / 2, cy0 + 26, ease_out(prog(t, 16.9, 0.6)))
        pp = ease_out(prog(t, 17.3, 0.5))
        y = cy0 + 26 + lg.height + 44
        put_text(f, A["who"], cx - A["who"].adv / 2, y, pp, 12 * (1 - pp))
        pp = ease_out(prog(t, 17.6, 0.5))
        put_text(f, A["end_date"], cx - A["end_date"].adv / 2, y + 62, pp, 12 * (1 - pp))
        put_text(f, A["end_times"], cx - A["end_times"].adv / 2, y + 118, pp, 12 * (1 - pp))
        p = prog(t, 18.2, 0.5)
        if p > 0:
            pulse = 1 + 0.035 * max(0.0, math.sin((t - 18.7) * 3.2)) * (t > 18.7)
            bw, bh = 470, 118
            s = (0.85 + 0.15 * ease_back(p)) * pulse
            pill = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle((0, 0, bw * 4 - 1, bh * 4 - 1), bh * 2, fill=RED + (255,))
            pill = pill.resize((int(bw * s), int(bh * s)), Image.LANCZOS)
            by = 1240
            put(f, pill, (W - pill.width) / 2, by + (bh - pill.height) / 2, min(1, p * 2))
            ct = A["cta"]
            put_text(f, ct, cx - ct.adv / 2, by + bh / 2 + 22, min(1, p * 2))
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
    out = np.zeros(n)

    def pad(freqs, start, end, gain):
        env = np.clip((t - start) / 2.0, 0, 1) * np.clip((end - t) / 2.0, 0, 1)
        s = np.zeros(n)
        for f0 in freqs:
            for det in (-0.5, 0.5):
                s += np.sin(2 * np.pi * (f0 + det) * t) + 0.2 * np.sin(2 * np.pi * 2 * (f0 + det) * t)
        s *= 1 + 0.12 * np.sin(2 * np.pi * 0.12 * t)
        return gain * env * s / len(freqs)

    def hit(at, f0, g, decay=6.0):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * decay) * np.clip(tt / 0.004, 0, 1)
        out[idx] += g * env * (np.sin(2 * np.pi * f0 * tt) + 0.4 * np.sin(2 * np.pi * f0 * 2 * tt))

    def chime(at, f0, g):
        idx = t >= at
        tt = t[idx] - at
        env = np.exp(-tt * 1.8) * np.clip(tt / 0.01, 0, 1)
        out[idx] += g * env * (np.sin(2 * np.pi * f0 * tt) + 0.3 * np.sin(2 * np.pi * f0 * 2.76 * tt))

    out += pad([130.81, 196.0, 246.94, 293.66, 329.63], -2, 9.8, 0.10)    # C maj9
    out += pad([110.0, 164.81, 220.0, 261.63, 246.94], 8.8, 16.2, 0.10)    # A min9
    out += pad([174.61, 220.0, 261.63, 329.63, 392.0], 15.0, DURATION + 2, 0.10)  # F maj9
    for at in (0.15, 0.55, 0.95, 15.55):   # soft low "slams" on the hook words
        hit(at, 92.5, 0.22)
    for at, f0 in [(1.9, 1046.5), (5.0, 880.0), (5.7, 987.8), (9.75, 1174.7), (18.2, 1318.5)]:
        chime(at, f0, 0.06)
    out *= np.clip((DURATION - t) / 1.2, 0, 1) * np.clip(t / 0.05, 0, 1)
    out = out / np.max(np.abs(out)) * 10 ** (-6 / 20)
    data = (np.stack([out, out], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def main(mode):
    os.makedirs(OUT_DIR, exist_ok=True)
    if mode == "stills":
        A = build()
        qc = os.path.join(OUT_DIR, "qc")
        os.makedirs(qc, exist_ok=True)
        for ts in [2.6, 7.5, 13.5, 20.0]:
            Image.fromarray(frame_at(ts, A)).save(os.path.join(qc, f"pop-{ts:04.1f}s.png"))
        return
    wav = os.path.join(OUT_DIR, f"{NAME}.wav")
    synth_audio(wav)
    mp4 = os.path.join(OUT_DIR, f"{NAME}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4, initializer=_init) as pool:
        for buf in pool.imap(_render, range(int(DURATION * FPS)), chunksize=4):
            proc.stdin.write(buf)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    A = build()
    Image.fromarray(frame_at(2.6, A)).save(os.path.join(OUT_DIR, f"{NAME}-cover.png"))
    print(mp4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "video")
