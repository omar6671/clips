"""Render split-screen clips: podcast on top, muted gameplay below, hook image + Arabic captions.

usage: render_split.py PODCAST.mp4 STREAM.mp4 transcript.jsonl clips.json OUTDIR [clip_id ...]
clips.json: [{"id": "01", "start": s, "end": e, "hook": "...", "game": stream_start_sec,
              "gcx": 0.5 (optional gameplay crop center), "gzoom": 1.0 (optional)}]
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framing import analyze
from hookimg import render as render_hook

pod, stream, tpath, cpath, outdir = sys.argv[1:6]
only = set(sys.argv[6:])
os.makedirs(outdir, exist_ok=True)

W, H, HALF = 1080, 1920, 960
HOOK_SECS = 4.5
HOOK_BOTTOM = clip_hb = 905          # hook block sits just above the seam
CAP_Y = 1010               # captions centred right below the hook, on the seam
PUNCT = ".,،؟?!:;…\"'"

words = []
with open(tpath, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            words += [w for w in json.loads(line)["words"] if w["w"].strip()]


def ts(t):
    t = max(t, 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def clean(w):
    return w.strip().strip(PUNCT).strip().replace("{", "").replace("}", "").replace("\\", "")


def caption_groups(cw, max_words=3, max_gap=0.6, max_chars=16):
    groups, cur = [], []
    for w in cw:
        if cur and (len(cur) >= max_words or w["s"] - cur[-1]["e"] > max_gap
                    or cur[-1]["w"].rstrip()[-1:] in ".?!؟"
                    or sum(len(x["w"]) + 1 for x in cur) + len(w["w"]) > max_chars):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def build_ass(clip):
    s0, s1 = clip["start"], clip["end"]
    cw = [dict(w, s=w["s"] - s0, e=w["e"] - s0) for w in words if w["s"] >= s0 - 0.05 and w["e"] <= s1 + 0.05]
    out = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Cap,Vazirmatn,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,2,5,40,40,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    groups = caption_groups(cw)
    for i, g in enumerate(groups):
        start, end = g[0]["s"], g[-1]["e"]
        if i + 1 < len(groups):
            end = min(max(end, start + 0.35), groups[i + 1][0]["s"])
        text = " ".join(c for c in (clean(w["w"]) for w in g) if c)
        if text:
            out.append(f"Dialogue: 1,{ts(start)},{ts(end)},Cap,,0,0,0,,"
                       f"{{\\pos({W // 2},{CAP_Y})\\fscx90\\fscy90\\t(0,80,\\fscx100\\fscy100)}}{text}")
    return "\n".join(out) + "\n"


def dims(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return map(int, o.strip().split(","))


sw, sh = dims(pod)
gw, gh = dims(stream)
pcw = int(sh * W / HALF) // 2 * 2                  # podcast crop width for a 9:8 window

for clip in json.load(open(cpath, encoding="utf-8")):
    if only and clip["id"] not in only:
        continue
    dur = clip["end"] - clip["start"]
    assert 15 <= dur <= 60, f"clip {clip['id']} is {dur:.1f}s"
    base = os.path.join(outdir, f"clip{clip['id']}")

    # top: podcast, crop follows each camera shot
    shots = analyze(pod, clip["start"], dur, sw, sh)
    json.dump(shots, open(base + ".shots.json", "w"), indent=1)
    xpos = lambda cx: int(min(max(cx * sw - pcw / 2, 0), sw - pcw)) // 2 * 2
    xexpr = str(xpos(0.47))
    for s in reversed(shots):
        xexpr = f"if(between(t,{s['a']:.3f},{s['b']:.3f}),{xpos(s['cx'])},{xexpr})"

    # bottom: gameplay, 9:8 window (optionally zoomed)
    z = clip.get("gzoom", 1.0)
    gch = int(gh / z) // 2 * 2
    gcw = int(gch * W / HALF) // 2 * 2
    gx = int(min(max(clip.get("gcx", 0.5) * gw - gcw / 2, 0), gw - gcw)) // 2 * 2
    gy = int(min(max(clip.get("gcy", 0.5) * gh - gch / 2, 0), gh - gch)) // 2 * 2

    render_hook(clip["hook"], base + ".hook.png", size=60, max_w=900, single=True)
    hh = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=height", "-of", "csv=p=0",
                         base + ".hook.png"], capture_output=True, text=True).stdout.strip()
    hook_y = HOOK_BOTTOM - int(hh)
    ass = base + ".ass"
    open(ass, "w", encoding="utf-8").write(build_ass(clip))

    fc = (f"[0:v]fps=30,crop={pcw}:{sh}:'{xexpr}':0,scale={W}:{HALF}:flags=lanczos,setsar=1[top];"
          f"[1:v]fps=30,crop={gcw}:{gch}:{gx}:{gy},scale={W}:{HALF}:flags=lanczos,setsar=1[bot];"
          f"[top][bot]vstack[st];"
          f"[2:v]format=rgba,fade=t=out:st={HOOK_SECS - 0.25}:d=0.25:alpha=1[hk];"
          f"[st][hk]overlay=0:{hook_y}:enable='lt(t,{HOOK_SECS})':format=auto[v1];"
          f"[v1]subtitles={ass}:fontsdir=/usr/share/fonts,format=yuv420p[v]")
    out = base + ".mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-ss", f"{clip['start']:.2f}", "-t", f"{dur:.2f}", "-i", pod,
           "-ss", f"{clip['game']:.2f}", "-t", f"{dur:.2f}", "-i", stream,
           "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png",
           "-filter_complex", fc, "-map", "[v]", "-map", "0:a:0",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
           "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "slow", "-crf", "18",
           "-maxrate", "12M", "-bufsize", "24M", "-g", "60", "-bf", "2",
           "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", f"{dur:.2f}",
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("rendered", out, flush=True)
