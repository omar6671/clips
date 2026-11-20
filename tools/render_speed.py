"""Two layouts for the 1280x592 IShowSpeed GTA6 stream.
A: facecam top (1080x700) / gameplay bottom (1080x1220), hook on seam, captions in gameplay.
B: stream view enlarged in the middle over a blurred fill, hook above, captions below."""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hookimg import render as render_hook
src, cpath, outdir = sys.argv[1:4]; os.makedirs(outdir, exist_ok=True)
EMO = r"\s+(?=[\U0001F000-\U0001FAFF☀-➿⬀-⯿])"
def ts(t):
    t = max(t, 0); h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h)}:{int(m):02d}:{s:05.2f}"
def ass(caps, y, path, size=68, y_early=None):
    out = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
           "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Cap,Vazirmatn,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,1.5,5,60,60,0,1", "",
           "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for a, b, t in caps:
        yy = y_early if (y_early and a < 4.5) else y
        out.append(f"Dialogue: 1,{ts(a)},{ts(max(b, a + 0.5))},Cap,,0,0,0,,{{\pos(540,{yy})}}‏{t}")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
for c in json.load(open(cpath, encoding="utf-8")):
    dur = c["end"] - c["start"]; base = os.path.join(outdir, f"clip{c['id']}")
    w, hh = render_hook(re.sub(EMO, "", c["hook"]), base + ".hook.png", size=60, max_w=900, single=True)
    if c["style"] == "A":
        TOP = 700
        hook_y = TOP - hh // 2; cap_y = TOP; cap_early = TOP + hh // 2 + 60; cap_size = 76
        v = (f"[0:v]split[a][b];"
             f"[a]crop=190:122:126:259,scale=1080:{TOP}:flags=lanczos,cas=0.8,unsharp=5:5:0.5,setsar=1[top];"
             f"[b]crop=392:442:444:43,scale=1080:{1920-TOP}:flags=lanczos,cas=0.5,setsar=1[bot];"
             f"[top][bot]vstack,fps=30[st]")
    else:
        VY, VH = 640, 670  # crop 712x442 keeps aspect
        hook_y = VY - 30 - hh; cap_y = VY + VH + 120; cap_early = None; cap_size = 68
        v = (f"[0:v]crop=712:442:115:43,split[a][b];"
             f"[a]scale=-2:1920,crop=1080:1920,boxblur=30:3,eq=brightness=-0.15[bg];"
             f"[b]scale=1080:{VH}:flags=lanczos,cas=0.6,setsar=1[fg];"
             f"[bg][fg]overlay=0:{VY},fps=30[st]")
    ass(c["caps"], cap_y, base + ".ass", size=cap_size, y_early=cap_early)
    fc = (v + f";[1:v]format=rgba,fade=t=out:st=4.25:d=0.25:alpha=1[hk];"
          f"[st][hk]overlay=0:{hook_y}:enable='lt(t,4.5)':format=auto[v1];"
          f"[v1]subtitles={base}.ass:fontsdir=/usr/share/fonts,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{c['start']:.2f}", "-t", f"{dur:.2f}", "-i", src,
                    "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png", "-filter_complex", fc, "-map", "[v]", "-map", "0:a:0",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
                    "-preset", "slow", "-crf", "18", "-g", "60", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", f"{dur:.2f}",
                    "-movflags", "+faststart", base + ".mp4"], check=True)
    print("rendered", base + ".mp4", flush=True)
