"""Voiceover for the Thanksgiving greeting (Oct 12, 2026) — same gentle voice as the RLD Reel."""
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rld_voice import soften  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "production", "thanks_audio")
LINES = [
    "Happy Thanksgiving!",
    "To every client who has trusted me with their care this year: thank you.",
    "May your table be full, your home be warm, and your heart be light.",
    "Take time to rest, slow down, and enjoy every moment with the people you love.",
    "With gratitude, Zarina.",
]


def main():
    os.makedirs(OUT, exist_ok=True)
    k = Kokoro(os.path.join(ROOT, "brand", "voice", "kokoro-v1.0.onnx"), os.path.join(ROOT, "brand", "voice", "voices-v1.0.bin"))
    voice = 0.7 * k.get_voice_style("af_heart") + 0.3 * k.get_voice_style("af_bella")
    durs = []
    for i, line in enumerate(LINES):
        audio, sr = k.create(line, voice=voice, speed=0.92, lang="en-us")
        audio = soften(np.asarray(audio, np.float64), sr)
        sf.write(os.path.join(OUT, f"line{i + 1}.wav"), audio, sr)
        durs.append(len(audio) / sr)
    json.dump({"sr": sr, "durations": durs}, open(os.path.join(OUT, "durations.json"), "w"), indent=1)
    print([round(d, 2) for d in durs], round(sum(durs), 1))


if __name__ == "__main__":
    main()
