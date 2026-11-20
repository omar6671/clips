"""Film / single-camera clips on black with the hook above the video for the whole clip.
usage: render_film.py SRC clips.json OUTDIR [ids]
clips: [{"id","start","end","hook","style": "crop"|"wide","color": "bw|wb|by|yb"}]
crop: 4:5 window that follows the faces of each shot (framing.analyze), 1080x1350 at y=430
wide: 16:9 frame zoomed slightly, 1080x608 centred
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framing import analyze
from hookimg import render as render_hook

src, cpath, outdir = sys.argv[1:4]
only = set(sys.argv[4:])
os.makedirs(outdir, exist_ok=True)
W, H = 1080, 1920
EMO = r"\s+(?=[\U0001F000-\U0001FAFF☀-➿⬀-⯿])"
COL = {"bw": ((0, 0, 0, 255), (255, 255, 255, 255)), "wb": ((255, 255, 255, 255), (0, 0, 0, 255)),
       "by": ((0, 0, 0, 255), (255, 214, 0, 255)), "yb": ((255, 214, 0, 255), (0, 0, 0, 255))}
ENC = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "medium", "-crf", "18",
       "-maxrate", "14M", "-bufsize", "28M", "-g", "60", "-bf", "2", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart"]
o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                    "-of", "csv=p=0", src], capture_output=True, text=True).stdout
sw, sh = map(int, o.strip().split(","))

for c in json.load(open(cpath, encoding="utf-8")):
    if only and c["id"] not in only:
        continue
    s0, dur = c["start"], c["end"] - c["start"]
    assert 15 <= dur <= 60, c
    base = os.path.join(outdir, f"clip{c['id']}")
    fg, bg = COL[c.get("color", "bw")]
    pre = min(3.0, s0)  # decode from earlier and trim: the source shows black frames right after a seek
    hw, hh = render_hook(re.sub(EMO, "", c["hook"]), base + ".hook.png", size=58, max_w=920, single=True, fg=fg, bg=bg)
    if c.get("style", "crop") == "crop":
        cw = int(sh * 4 / 5) // 2 * 2
        if os.path.exists(base + ".shots.json"):
            shots = json.load(open(base + ".shots.json"))
        else:
            shots = analyze(src, s0, dur, sw, sh)
            json.dump(shots, open(base + ".shots.json", "w"), indent=1)
        xpos = lambda cx: int(min(max(cx * sw - cw / 2, 0), sw - cw)) // 2 * 2
        xexpr = str(xpos(0.5))
        for s in reversed(shots):
            xexpr = f"if(between(t,{s['a']:.3f},{s['b']:.3f}),{xpos(s['cx'])},{xexpr})"
        vh = 1350; vy = min(max(430, 205 + hh + 25), H - vh)
        vid = f"[0:v]trim=start={pre},setpts=PTS-STARTPTS,fps=30,crop={cw}:{sh}:'{xexpr}':0,scale={W}:{vh}:flags=lanczos,setsar=1[vid];"
    else:
        zw = int(sw / 1.12) // 2 * 2; zh = int(sh / 1.12) // 2 * 2
        vh = int(W * zh / zw) // 2 * 2; vy = (H - vh) // 2
        vid = f"[0:v]trim=start={pre},setpts=PTS-STARTPTS,fps=30,crop={zw}:{zh},scale={W}:{vh}:flags=lanczos,setsar=1[vid];"
    hook_y = vy - 25 - hh
    assert hook_y >= 200, (c["id"], hook_y)
    fc = (f"color=c=black:s={W}x{H}:r=30[bg];" + vid +
          f"[bg][vid]overlay=0:{vy}:shortest=1[st];[1:v]format=rgba[hk];"
          f"[st][hk]overlay=0:{hook_y}:format=auto,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s0 - pre:.2f}", "-t", f"{dur + pre:.2f}", "-i", src,
                    "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png", "-filter_complex", fc,
                    "-map", "[v]", "-map", "0:a:0", "-af", f"atrim=start={pre},asetpts=PTS-STARTPTS,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
                    *ENC, "-t", f"{dur:.2f}", base + ".mp4"], check=True)
    print("rendered", base + ".mp4", flush=True)
