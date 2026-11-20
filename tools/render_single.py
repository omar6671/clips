"""Render single-video clips (black bg, square video, hook above, captions below). Derived from split-screen renderer.

OLD DOC: Render split-screen clips: podcast on top, muted gameplay below, hook image + Arabic captions.

usage: render_split.py PODCAST.mp4 STREAM.mp4 transcript.jsonl clips.json OUTDIR [clip_id ...]
clips.json: [{"id": "01", "start": s, "end": e, "hook": "...", "game": stream_start_sec,
              "gcx": 0.5 (optional gameplay crop center), "gzoom": 1.0 (optional)}]
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framing import analyze
from hookimg import render as render_hook

pod, tpath, cpath, outdir = sys.argv[1:5]
only = set(sys.argv[5:])
os.makedirs(outdir, exist_ok=True)

W, H, HALF = 1080, 1920, 960
HOOK_SECS = 4.5
VID_Y, VID = 470, 1080     # square video area
HOOK_BOTTOM = 450          # hook block sits just above the video
CAP_Y = 1420               # captions centred below the video
PUNCT = ".,،؟?!:;…\"'"
import re
BAD_SEG = ("اشتركوا في القناة", "ترجمة", "المترجم", "قناتنا")
BAD_CH = re.compile(r"[A-Za-z\u0400-\u04FF\u3040-\u30FF\uAC00-\uD7AF\uFFFD]")

words = []
with open(tpath, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            seg = json.loads(line)
            if any(b in seg["text"] for b in BAD_SEG):
                continue
            words += [w for w in seg["words"] if w["w"].strip() and not BAD_CH.search(w["w"])]


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
        "Style: Cap,Vazirmatn,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3.5,1.5,5,40,40,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if "caps" in clip:
        cs = clip["caps"]
        for i, (a, b, text) in enumerate(cs):
            if i + 1 < len(cs):
                b = min(max(b, a + 0.5), cs[i + 1][0])
            else:
                b = max(b, a + 0.6)
            out.append(f"Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({W // 2},{CAP_Y})}}{text}")
        return "\n".join(out) + "\n"
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
pcw = sh // 2 * 2                                  # square crop window

for clip in json.load(open(cpath, encoding="utf-8")):
    if only and clip["id"] not in only:
        continue
    dur = clip["end"] - clip["start"]
    assert 15 <= dur <= 60, f"clip {clip['id']} is {dur:.1f}s"
    base = os.path.join(outdir, f"clip{clip['id']}")

    # top: podcast, crop follows each camera shot
    shots = analyze(pod, clip["start"], dur, sw, sh)
    json.dump(shots, open(base + ".shots.json", "w"), indent=1)
    pcw = clip.get("crop_h", sh) // 2 * 2       # square window (smaller = zoom from top)
    xpos = lambda cx: int(min(max(cx * sw - pcw / 2, 0), sw - pcw)) // 2 * 2
    xexpr = str(xpos(0.47))
    for s in reversed(shots):
        xexpr = f"if(between(t,{s['a']:.3f},{s['b']:.3f}),{xpos(s['cx'])},{xexpr})"

    render_hook(re.sub(r"\s+(?=[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF])", "", clip["hook"]), base + ".hook.png", size=72, max_w=980, single=True)
    hh = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=height", "-of", "csv=p=0",
                         base + ".hook.png"], capture_output=True, text=True).stdout.strip()
    hook_y = HOOK_BOTTOM - int(hh)
    ass = base + ".ass"
    open(ass, "w", encoding="utf-8").write(build_ass(clip))

    fc = (f"color=c=black:s={W}x{H}:r=30[bg];"
          f"[0:v]fps=30,crop={pcw}:{pcw}:'{xexpr}':0,scale={VID}:{VID}:flags=lanczos,setsar=1[vid];"
          f"[bg][vid]overlay=0:{VID_Y}:shortest=1[st];" +
          (f"[1:v]format=rgba[hk];[st][hk]overlay=0:{hook_y}:format=auto[v1];" if clip.get("hook_full") else
           f"[1:v]format=rgba,fade=t=out:st={HOOK_SECS - 0.25}:d=0.25:alpha=1[hk];"
           f"[st][hk]overlay=0:{hook_y}:enable='lt(t,{HOOK_SECS})':format=auto[v1];") +
          (f"[v1]subtitles={ass}:fontsdir=/usr/share/fonts,format=yuv420p[v]" if clip.get("caps") else "[v1]format=yuv420p[v]"))
    out = base + ".mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-ss", f"{clip['start']:.2f}", "-t", f"{dur:.2f}", "-i", pod,
           "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png",
           "-filter_complex", fc, "-map", "[v]", "-map", "0:a:0",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
           "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "slow", "-crf", "18",
           "-maxrate", "12M", "-bufsize", "24M", "-g", "60", "-bf", "2",
           "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", f"{dur:.2f}",
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("rendered", out, flush=True)
