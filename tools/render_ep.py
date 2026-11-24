"""Campaign podcast split screen: podcast on top (shot-aware face crop), muted gameplay below, hook on the
seam for 4.5 s, Khaliji captions (white, thin outline) on the seam.
usage: render_ep.py PODCAST GAMEPLAY clips.json OUTDIR [ids]
clips: [{"id","start","end","hook","color":"bw|wb|by|yb",
         "game": sec, "gzoom": 1.0, "gcx": 0.45, "gcy": 0.45,  # gameplay window (no burned-in subs / cam)
         "caps": [[s, e, "text"], ...]  (relative to clip start)}]
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framing import analyze
from hookimg import render as render_hook
from hookgold import render as render_gold

pod, game, cpath, outdir = sys.argv[1:5]
only = set(sys.argv[5:])
os.makedirs(outdir, exist_ok=True)
W, H, HALF, HOOK_SECS = 1080, 1920, 960, 4.5
EMO = r"\s+(?=[\U0001F000-\U0001FAFF☀-➿⬀-⯿])"
COL = {"bw": ((0, 0, 0, 255), (255, 255, 255, 255)), "wb": ((255, 255, 255, 255), (0, 0, 0, 255)),
       "by": ((0, 0, 0, 255), (255, 214, 0, 255)), "yb": ((255, 214, 0, 255), (0, 0, 0, 255))}
ENC = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "medium", "-crf", "18",
       "-maxrate", "14M", "-bufsize", "28M", "-g", "60", "-bf", "2", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart"]
GAME_TOP, GAME_BOT = 40, 830   # usable rows of the 1080p gameplay (below: burned-in subtitles / HUD)
GAME_RIGHT = 1660              # streamer cam box starts here


def ts(t):
    t = max(t, 0); h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def dims(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    return map(int, o.strip().split(","))


def write_ass(caps, hook_until, path, y_hook, y_after, size=96):
    out = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2",
           "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Cap,Vazirmatn,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4.5,1.5,5,60,60,0,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for a, b, t in caps:
        # a caption that starts under the hook stays there; later ones sit on the seam
        y = y_hook if a < hook_until else y_after
        out.append(f"Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({W // 2},{y})}}{t}")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")


sw, sh = dims(pod)
gw0, gh0 = dims(game)
pcw = int(sh * W / HALF) // 2 * 2
for c in json.load(open(cpath, encoding="utf-8")):
    if only and c["id"] not in only:
        continue
    s0, dur = c["start"], c["end"] - c["start"]
    assert 8 <= dur <= 140, c
    base = os.path.join(outdir, f"clip{c['id']}")
    if os.path.exists(base + ".shots.json"):
        shots = json.load(open(base + ".shots.json"))
    else:
        shots = analyze(pod, s0, dur, sw, sh)
        json.dump(shots, open(base + ".shots.json", "w"), indent=1)
    xpos = lambda cx: int(min(max(cx * sw - pcw / 2, 0), sw - pcw)) // 2 * 2
    xexpr = str(xpos(0.5))
    for s in reversed(shots):
        xexpr = f"if(between(t,{s['a']:.3f},{s['b']:.3f}),{xpos(s.get('ox', s['cx']))},{xexpr})"
    # gameplay window: 9:8, inside the usable area, zoom >= 1
    gt, gb = c.get("gtop", GAME_TOP), c.get("gbot", GAME_BOT)   # usable rows (Kaydra: 180..1000)
    uh = (gb - gt) * gh0 // 1080
    z = c.get("gzoom", 1.0)
    gch = int(uh / z) // 2 * 2
    gcw = int(gch * W / HALF) // 2 * 2
    right = c.get("gright", GAME_RIGHT) * gw0 // 1920
    gx = int(min(max(c.get("gcx", 0.45) * right - gcw / 2, 0), right - gcw)) // 2 * 2
    top = gt * gh0 // 1080
    gy = int(min(max(top + c.get("gcy", 0.5) * uh - gch / 2, top), top + uh - gch)) // 2 * 2

    fg, bg = COL[c.get("color", "bw")]
    nohook = c.get("hookstyle") == "none"
    gold = c.get("hookstyle") in ("gold", "box")
    if nohook:   # no on-screen text at all (X style)
        from PIL import Image; Image.new("RGBA", (W, 2), (0, 0, 0, 0)).save(base + ".hook.png"); hh = 2; hook_y = HALF
    elif c.get("hookstyle") == "box":   # white box hook centred on the seam for the whole clip (top-30 style)
        hw, hh = render_hook(re.sub(EMO, "", c["hook"]), base + ".hook.png", size=c.get("hooksize", 58), max_w=c.get("hookmaxw", 900), single=True, fg=fg, bg=bg, gap=c.get("hookgap", -6))
        hook_y = HALF - hh // 2
    elif gold:   # gold quoted hook centred on the seam for the whole clip, captions just below it
        hw, hh = render_gold(c["hook"], base + ".hook.png")
        hook_y = HALF - hh // 2
    else:
        hw, hh = render_hook(re.sub(EMO, "", c["hook"]), base + ".hook.png", size=60, max_w=900, single=True, fg=fg, bg=bg)
        hook_y = HALF - 15 - hh            # hook block sits just above the seam
    fits = [s for s in shots if s["mode"] == "fit"]
    fh = int(W * sh / sw) // 2 * 2
    if fits:   # wide shots: whole frame over a blurred fill instead of a cut-off crop
        en = "+".join(f"between(t,{s['a']:.3f},{s['b']:.3f})" for s in fits)
        topf = (f"[0:v]fps=30,split[p0][p1];[p0]crop={pcw}:{sh}:'{xexpr}':0,scale={W}:{HALF}:flags=lanczos,setsar=1[tc];"
                f"[p1]split[q0][q1];[q0]scale={W}:{HALF}:force_original_aspect_ratio=increase,crop={W}:{HALF},boxblur=20:2,eq=brightness=-0.08[bl];"
                f"[q1]scale={W}:{fh}:flags=lanczos[fw];[bl][fw]overlay=0:{(HALF - fh) // 2}[tf];"
                f"[tc][tf]overlay=0:0:enable='{en}',setsar=1[top];")
    else:
        topf = f"[0:v]fps=30,crop={pcw}:{sh}:'{xexpr}':0,scale={W}:{HALF}:flags=lanczos,setsar=1[top];"
    fc = (topf +
          f"[1:v]fps=30,crop={gcw}:{gch}:{gx}:{gy},scale={W}:{HALF}:flags=lanczos,setsar=1[bot];"
          f"[top][bot]vstack[st];"
          + ("[2:v]format=rgba[hk];[st][hk]overlay=0:" + str(hook_y) + ":format=auto[v1]" if gold else
             f"[2:v]format=rgba,fade=t=out:st={HOOK_SECS - 0.25}:d=0.25:alpha=1[hk];"
             f"[st][hk]overlay=0:{hook_y}:enable='lt(t,{HOOK_SECS})':format=auto[v1]"))
    if c.get("caps"):
        if gold:
            cy = hook_y + hh + 55
            write_ass(c["caps"], 0, base + ".ass", cy, cy, size=68)
        else:
            write_ass(c["caps"], HOOK_SECS, base + ".ass", HALF + 95, HALF)
        fc += f";[v1]subtitles={base}.ass:fontsdir=/usr/share/fonts/truetype/vazirmatn,format=yuv420p[v]"
    else:
        fc += ";[v1]format=yuv420p[v]"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{s0:.2f}", "-t", f"{dur:.2f}", "-i", pod,
                    "-ss", f"{c['game']:.2f}", "-t", f"{dur:.2f}", "-i", game,
                    "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png",
                    "-filter_complex", fc, "-map", "[v]", "-map", "0:a:0",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
                    *ENC, "-t", f"{dur:.2f}", base + ".mp4"], check=True)
    print("rendered", base + ".mp4", flush=True)
