"""Two versions per clip for a 1080p stream with top-right facecam (x1448-1904, y76-477).
A (clipNN_a): facecam top 1080x960 / gameplay bottom 1080x960, hook centred on seam for 4.5s.
B (clipNN_b): frame zoomed ~1.2x, centred on black, hook above in the black space for the whole clip.
usage: render_v6.py SRC clips.json OUTDIR [ids]"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hookimg import render as render_hook
src, cpath, outdir = sys.argv[1:4]; only = set(sys.argv[4:]); os.makedirs(outdir, exist_ok=True)
EMO = r"\s+(?=[\U0001F000-\U0001FAFF☀-➿⬀-⯿])"
ENC = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "slow", "-crf", "18", "-g", "60",
       "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart"]
for c in json.load(open(cpath, encoding="utf-8")):
    if only and c["id"] not in only: continue
    dur = c["end"] - c["start"]; assert 15 <= dur <= 60, c
    base = os.path.join(outdir, f"clip{c['id']}")
    w, hh = render_hook(re.sub(EMO, "", c["hook"]), base + ".hook.png", size=60, max_w=900, single=True)
    common_in = ["-ss", f"{c['start']:.2f}", "-t", f"{dur:.2f}", "-i", src, "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png"]
    af = ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"]
    # A: split screen, hook on seam for 4.5s
    fa = ("[0:v]split[a][b];"
          "[a]crop=442:393:1455:80,scale=1080:960:flags=lanczos,cas=0.6,setsar=1[top];"
          "[b]crop=1080:960:368:120,setsar=1[bot];[top][bot]vstack,fps=30[st];"
          "[1:v]format=rgba,fade=t=out:st=4.25:d=0.25:alpha=1[hk];"
          f"[st][hk]overlay=0:{960 - hh // 2}:enable='lt(t,4.5)':format=auto,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *common_in, "-filter_complex", fa,
                    "-map", "[v]", "-map", "0:a:0", *af, *ENC, "-t", f"{dur:.2f}", base + "_a.mp4"], check=True)
    # B: zoomed frame on black, hook above for the whole clip
    VH = 608; VY = (1920 - VH) // 2
    fb = ("color=c=black:s=1080x1920:r=30[bg];"
          f"[0:v]crop=1600:900:160:90,scale=1080:{VH}:flags=lanczos,setsar=1,fps=30[vid];"
          f"[bg][vid]overlay=0:{VY}:shortest=1[st];[1:v]format=rgba[hk];"
          f"[st][hk]overlay=0:{VY - 40 - hh}:format=auto,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *common_in, "-filter_complex", fb,
                    "-map", "[v]", "-map", "0:a:0", *af, *ENC, "-t", f"{dur:.2f}", base + "_b.mp4"], check=True)
    print("rendered", c["id"], flush=True)
