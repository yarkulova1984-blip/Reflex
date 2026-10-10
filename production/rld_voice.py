"""Voiceover for the RLD Reel v2 — Kokoro TTS, gentle blend of af_heart (70 %) + af_bella (30 %),
slightly slower, softened highs and a touch of room. One WAV per line + a JSON of durations."""
import json
import os
import subprocess

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "production", "rld_audio")
LINES = [
    "Your lymphatic system has no heart to pump it. So what keeps it moving?",
    "Lymph carries extra fluid and immune cells. It moves with your muscles, your breath, and gentle touch.",
    "Reflexology Lymph Drainage, or R L D, is a gentle reflexology technique for the feet and hands.",
    "Many clients find it deeply relaxing, and their legs feel lighter. Research is promising, but still early.",
    "It's loved by people on their feet all day, frequent flyers, and anyone with tired, heavy legs.",
    "Zarina works the spaces between the toes, then the thymus, diaphragm, spleen and kidney reflexes.",
    "On the hands: between the fingers, the back of the hand, and the wrist.",
    "Check with your doctor first if you have a fever, a blood clot, heart or kidney problems, cancer treatment, or early pregnancy. Reflexology supports medical care. It never replaces it.",
    "To book, send us a DM with the word, LYMPH.",
]


def soften(x, sr):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    X *= 1 / (1 + (f / 7000) ** 2) ** 0.35          # gentle high roll-off (less sibilance)
    X *= 1 + 0.12 * np.exp(-((f - 220) / 120) ** 2)  # a little warmth
    y = np.fft.irfft(X, len(x))
    ir_len = int(0.35 * sr)                          # small, soft room
    rng = np.random.default_rng(3)
    ir = rng.normal(0, 1, ir_len) * np.exp(-np.arange(ir_len) / (0.07 * sr))
    wet = np.convolve(y, ir)[: len(y)]
    wet = wet / (np.abs(wet).max() + 1e-9) * np.abs(y).max()
    return 0.9 * y + 0.10 * wet


def main():
    os.makedirs(OUT, exist_ok=True)
    k = Kokoro(os.path.join(ROOT, "brand", "voice", "kokoro-v1.0.onnx"), os.path.join(ROOT, "brand", "voice", "voices-v1.0.bin"))
    voice = 0.7 * k.get_voice_style("af_heart") + 0.3 * k.get_voice_style("af_bella")
    durs = []
    for i, line in enumerate(LINES):
        audio, sr = k.create(line, voice=voice, speed=0.95, lang="en-us")
        audio = soften(np.asarray(audio, np.float64), sr)
        p = os.path.join(OUT, f"line{i + 1}.wav")
        sf.write(p, audio, sr)
        durs.append(len(audio) / sr)
    json.dump({"sr": sr, "durations": durs}, open(os.path.join(OUT, "durations.json"), "w"), indent=1)
    print([round(d, 2) for d in durs], round(sum(durs), 1))


if __name__ == "__main__":
    main()
