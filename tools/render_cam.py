"""Facecam-on-top / gameplay-bottom renderer for 4K streams with a top-right facecam box.
usage: render_cam.py SRC clips.json OUTDIR [ids]   clips: [{"id","start","end","hook"}]"""
import json, os, subprocess, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hookimg import render as render_hook
from framing import FRONT, PROFILE
src, cpath, outdir = sys.argv[1:4]; only = set(sys.argv[4:]); os.makedirs(outdir, exist_ok=True)
W, H, HALF, HOOK_SECS = 1080, 1920, 960, 4.5
BX0, BY0, BX1, BY1 = 2734, 168, 3638, 638      # facecam interior (inside border, above MW4 logo)
CH = BY1 - BY0; CW = int(CH * W / HALF) // 2 * 2  # 9:8 window inside the cam
GX, GY, GW, GH = 600, 292, 2100, 1868          # gameplay 9:8 window, clear of the cam box

def face_cx(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", "-vf",
                          f"crop={BX1-BX0}:{CH}:{BX0}:{BY0},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    img = np.frombuffer(raw[:(BX1 - BX0) * CH], np.uint8).reshape(CH, BX1 - BX0)
    fs = [x + w / 2 for c in (FRONT, PROFILE) for (x, y, w, h) in c.detectMultiScale(img, 1.1, 5, minSize=(80, 80))]
    return float(np.median(fs)) if fs else None

for clip in json.load(open(cpath, encoding="utf-8")):
    if only and clip["id"] not in only: continue
    s0, dur = clip["start"], clip["end"] - clip["start"]
    assert 15 <= dur <= 60, clip
    base = os.path.join(outdir, f"clip{clip['id']}")
    # follow whoever is on cam: sample every 0.5s, hold last position, switch on a stable change
    xpos = lambda c: int(min(max(c - CW / 2, 0), (BX1 - BX0) - CW)) // 2 * 2
    samples = [(t, face_cx(s0 + t)) for t in np.arange(0.0, dur, 0.5)]
    first = next((c for _, c in samples if c is not None), (BX1 - BX0) / 2)
    shots, cur = [[0.0, xpos(first)]], xpos(first)
    for k, (t, c) in enumerate(samples):
        if c is None: continue
        nx = xpos(c)
        nxt = samples[k + 1][1] if k + 1 < len(samples) else c
        if abs(nx - cur) > 50 and nxt is not None and abs(xpos(nxt) - nx) < 50:
            shots.append([max(t - 0.25, 0.0), nx]); cur = nx
    xexpr = str(shots[-1][1])
    for (a, x), nb in zip(reversed(shots), [None] + [s[0] for s in reversed(shots[1:])]):
        pass
    xexpr = str(shots[0][1])
    for a, x in shots[1:]:
        xexpr = f"if(gte(t,{a:.2f}),{x},{xexpr})"
    cx0 = 0
    hw, hh = render_hook(__import__("re").sub(r"\s+(?=[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF])", "", clip["hook"]), base + ".hook.png", size=60, max_w=900, single=True)
    hook_y = HALF - hh // 2
    fc = (f"[0:v]split[a][b];"
          f"[a]crop={CW}:{CH}:'{BX0}+{xexpr}':{BY0},scale={W}:{HALF}:flags=lanczos,cas=0.55,setsar=1[top];"
          f"[b]crop={GW}:{GH}:{GX}:{GY},scale={W}:{HALF}:flags=lanczos,setsar=1[bot];"
          f"[top][bot]vstack,fps=30[st];"
          f"[1:v]format=rgba,fade=t=out:st={HOOK_SECS - 0.25}:d=0.25:alpha=1[hk];"
          f"[st][hk]overlay=0:{hook_y}:enable='lt(t,{HOOK_SECS})':format=auto,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s0:.2f}", "-t", f"{dur:.2f}", "-i", src,
                    "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png",
                    "-filter_complex", fc, "-map", "[v]", "-map", "0:a:0",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
                    "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "slow", "-crf", "18",
                    "-maxrate", "12M", "-bufsize", "24M", "-g", "60", "-bf", "2",
                    "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", f"{dur:.2f}", "-movflags", "+faststart",
                    base + ".mp4"], check=True)
    print("rendered", base + ".mp4", "hook_y", hook_y, "h", hh, flush=True)
