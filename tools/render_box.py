"""Render clips from a stream/reaction video that has a fixed facecam box.
usage: render_box.py SRC layout.json clips.json OUTDIR [ids]
layout.json: {"cam": [x, y, w, h],    # facecam interior (inside border), ~9:8
              "game": [x, y, w, h],   # 9:8 gameplay window clear of the cam box
              "wide": [x, y, w, h]}   # region for the 'wide' style (shown on black)
clips: [{"id", "start", "end", "hook", "style": "split"|"wide", "color": "bw"|"wb"|"by"|"yb",
         "caps": [[s, e, text], ...] optional, "game": [x,y,w,h] optional per-clip override}]
split: cam zoomed on top, gameplay below, hook on the seam for 4.5 s, captions on the seam after.
wide : region zoomed on black, hook above it for the whole clip, captions below the middle.
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hookimg import render as render_hook
from hookgold import render as render_gold

src, lpath, cpath, outdir = sys.argv[1:5]
only = set(sys.argv[5:])
os.makedirs(outdir, exist_ok=True)
L = json.load(open(lpath))
W, H, HALF, HOOK_SECS = 1080, 1920, 960, 4.5
EMO = r"\s+(?=[\U0001F000-\U0001FAFF☀-➿⬀-⯿])"
COL = {"bw": ((0, 0, 0, 255), (255, 255, 255, 255)), "wb": ((255, 255, 255, 255), (0, 0, 0, 255)),
       "by": ((0, 0, 0, 255), (255, 214, 0, 255)), "yb": ((255, 214, 0, 255), (0, 0, 0, 255))}
ENC = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "medium", "-crf", "18",
       "-maxrate", "14M", "-bufsize", "28M", "-g", "60", "-bf", "2", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart"]


def ts(t):
    t = max(t, 0); h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass(caps, y, path, yh=None, size=96):
    out = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2",
           "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Cap,Vazirmatn,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4.5,1.5,5,60,60,0,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for a, b, t in caps:
        yy = yh if (yh and a < HOOK_SECS) else y
        out.append(f"Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({W // 2},{yy})}}{t}")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")


for c in json.load(open(cpath, encoding="utf-8")):
    if only and c["id"] not in only:
        continue
    s0, dur = c["start"], c["end"] - c["start"]
    assert 15 <= dur <= 60, c
    base = os.path.join(outdir, f"clip{c['id']}")
    fg, bg = COL[c.get("color", "bw")]
    style = c.get("style", "split")
    gold = c.get("hookstyle") in ("gold", "box")   # both stay on the seam for the whole clip
    if c.get("hookstyle") == "box":
        hw, hh = render_hook(re.sub(EMO, "", c["hook"]), base + ".hook.png", size=58, max_w=900, single=True, fg=fg, bg=bg)
    elif gold:
        hw, hh = render_gold(c["hook"], base + ".hook.png")
    else:
        hw, hh = render_hook(re.sub(EMO, "", c["hook"]), base + ".hook.png", size=60, max_w=900, single=True, fg=fg, bg=bg)
    cx, cy, cw, ch = L["cam"]
    gx, gy, gw, gh = c.get("game", L["game"])
    if style == "split":
        hook_y = HALF - hh // 2 if gold else HALF + 20 - hh // 2
        cap_y = HALF
        fc = (f"[0:v]split[a][b];"
              f"[a]crop={cw}:{ch}:{cx}:{cy},scale={W}:{HALF}:flags=lanczos,cas=0.5,setsar=1[top];"
              f"[b]crop={gw}:{gh}:{gx}:{gy},scale={W}:{HALF}:flags=lanczos,setsar=1[bot];"
              f"[top][bot]vstack,fps=30[st];"
              + ("[1:v]format=rgba[hk];[st][hk]overlay=0:" + str(hook_y) + ":format=auto[v1]" if gold else
                 f"[1:v]format=rgba,fade=t=out:st={HOOK_SECS - 0.25}:d=0.25:alpha=1[hk];"
                 f"[st][hk]overlay=0:{hook_y}:enable='lt(t,{HOOK_SECS})':format=auto[v1]"))
    else:
        wx, wy, ww, wh = L["wide"]
        vh = int(W * wh / ww) // 2 * 2
        vy = (H - vh) // 2
        hook_y = vy - 30 - hh
        assert hook_y > 230, hook_y
        cap_y = vy + vh + 110 if vy + vh + 110 < H - 300 else vy + int(vh * 0.8)
        fc = (f"color=c=black:s={W}x{H}:r=30[bg];"
              f"[0:v]crop={ww}:{wh}:{wx}:{wy},scale={W}:{vh}:flags=lanczos,setsar=1,fps=30[vid];"
              f"[bg][vid]overlay=0:{vy}:shortest=1[st];[1:v]format=rgba[hk];"
              f"[st][hk]overlay=0:{hook_y}:format=auto[v1]")
    if c.get("caps"):
        if gold and style == "split":
            cy = hook_y + hh + 55
            ass(c["caps"], cy, base + ".ass", cy, size=68)
        else:
            ass(c["caps"], cap_y, base + ".ass", (hook_y + hh + 70) if style == "split" else None)
        fc += f";[v1]subtitles={base}.ass:fontsdir=/usr/share/fonts/truetype/vazirmatn,format=yuv420p[v]"
    else:
        fc += ";[v1]format=yuv420p[v]"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s0:.2f}", "-t", f"{dur:.2f}", "-i", src,
                    "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png", "-filter_complex", fc,
                    "-map", "[v]", "-map", "0:a:0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
                    *ENC, "-t", f"{dur:.2f}", base + ".mp4"], check=True)
    print("rendered", base + ".mp4", style, flush=True)
