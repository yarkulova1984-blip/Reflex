"""THE voice for every video (CLAUDE.md §47.8): ElevenLabs "Zara – The Warm Real-World
Conversationalist" (voice ID jqcCZkN6Knx8BJ5TBdYR), generated through the owner's json2video
account. The API key is a network secret on this environment (host api.json2video.com, header
x-api-key) injected by the proxy, so the code only sends a placeholder.

  python3 production/zara_tts.py script.txt out.mp3

script.txt = the final English voiceover (one paragraph per line). Output: MP3, 48 kHz, mono.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

API = "https://api.json2video.com/v2/movies"
VOICE = "jqcCZkN6Knx8BJ5TBdYR"   # Zara – The Warm Real-World Conversationalist (matches the owner's reference Reels)
MODEL = "elevenlabs"


def _req(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"x-api-key": "proxy-injected", "Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def synth(text, out_mp3):
    movie = {"resolution": "custom", "width": 360, "height": 640, "quality": "low",
             "scenes": [{"elements": [{"type": "voice", "text": text, "voice": VOICE, "model": MODEL}]}]}
    project = _req(API, movie)["project"]
    for _ in range(120):
        m = _req(f"{API}?project={project}").get("movie", {})
        if m.get("status") == "done":
            break
        if m.get("status") == "error":
            raise RuntimeError(m.get("message"))
        time.sleep(5)
    else:
        raise TimeoutError(project)
    with tempfile.TemporaryDirectory() as d:
        mp4 = os.path.join(d, "v.mp4")
        urllib.request.urlretrieve(m["url"], mp4)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vn", "-ac", "1", "-ar", "48000",
                        "-c:a", "libmp3lame", "-b:a", "192k", out_mp3], check=True)
    return out_mp3


if __name__ == "__main__":
    lines = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    print(synth("\n".join(lines), sys.argv[2]))
