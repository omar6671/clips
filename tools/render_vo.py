"""Voiceover clip: trailer/gameplay shots cut to an ElevenLabs voice, hook box above, big synced captions.
usage: render_vo.py KEY  (reads KEY.mp3, KEY.words.json, scripts.json[KEY]=(hook, text), shots.json[KEY])
shots.json[KEY]: [[src, t, anchor_word_or_null, mode?], ...]  mode: "crop" (default) | "fit" (whole 16:9 frame over blur)
Sources: dmz/story/campaign/pc trailers in /home/user/src/trailers, k1/k2 = Kaydra stream parts."""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hookimg import render as render_hook

K = sys.argv[1]
SRC = {"dmz": "/home/user/src/trailers/dmz.mp4", "story": "/home/user/src/trailers/story.mp4",
       "campaign": "/home/user/src/trailers/campaign.mp4", "pc": "/home/user/src/trailers/pc.mp4",
       "k1": "/home/user/src/kaydra/part1.mp4", "k2": "/home/user/src/kaydra/part2.mp4"}
CROP = {"dmz": "crop=907:680:506:130", "story": "crop=907:680:506:150,eq=gamma=1.3:saturation=1.1",
        "campaign": "crop=907:680:506:150,eq=gamma=1.2",
        "pc": "crop=1440:1080:240:0", "k1": "crop=1093:820:180:180", "k2": "crop=1093:820:180:180"}
W, H, VW, VH, VY = 1080, 1920, 1080, 810, 600
# spoken words -> how they are written in captions
SUBS = [("مودرن وارفير فور", "مودرن وارفير 4"), ("الدي إم زد", "DMZ"), ("دي إم إيه", "DMA"), ("تي بي إم تو", "TPM 2.0"),
        ("دي إل إس إس فور بوينت فايف", "DLSS 4.5"), ("إف إس آر ريدستون", "FSR Redstone"), ("إكس إي إس إس ثري", "XeSS 3"),
        ("إكس زيرو ون", "X01"), ("مية وواحد وأربعين", "141"), ("سبعين ألف", "70 ألف"), ("مية لِفل", "100 لفل")]

hook, _ = json.load(open("scripts.json"))[K]
shots = json.load(open("shots.json"))[K]
words = json.load(open(K + ".words.json"))
bare = lambda t: re.sub(r"\W", "", t)

# merge multi-word terms for captions
cw, i = [], 0
while i < len(words):
    for sp, wr in SUBS:
        n = len(sp.split())
        if i + n <= len(words) and " ".join(bare(w[2]) for w in words[i:i + n]) == " ".join(bare(x) for x in sp.split()):
            tail = re.sub(r"^[\w؀-ۿ]+", "", words[i + n - 1][2].split()[-1]) if False else re.findall(r"[؟?!.،…]+$", words[i + n - 1][2])
            cw.append([words[i][0], words[i + n - 1][1], wr + (tail[0] if tail else "")]); i += n; break
    else:
        cw.append(words[i]); i += 1

dur = words[-1][1] + 0.5
# cut points: anchors at named words, the rest spread evenly between anchors
starts = [None] * len(shots)
starts[0] = 0.0
for j, s in enumerate(shots):
    if j and len(s) > 2 and s[2]:
        hit = [w[0] for w in words if bare(w[2]).startswith(bare(s[2]))]
        assert hit, (K, s)
        prev = max([x for x in starts[:j] if x is not None])
        starts[j] = min([h for h in hit if h > prev] or [hit[-1]])
idx = [j for j, x in enumerate(starts) if x is not None] + [len(shots)]
bounds = starts[:] + [dur]
for a, b in zip(idx, idx[1:]):
    t0, t1 = bounds[a], (bounds[b] if b < len(shots) else dur)
    for k in range(a + 1, b):
        bounds[k] = t0 + (t1 - t0) * (k - a) / (b - a)
bounds[len(shots)] = dur

ins, fc, lab = [], [], []
for j, s in enumerate(shots):
    src, t = s[0], s[1]
    mode = s[3] if len(s) > 3 else "crop"
    d = bounds[j + 1] - bounds[j]
    ins += ["-ss", f"{t}", "-t", f"{d + 0.2:.2f}", "-i", SRC[src]]
    if mode in ("fit", "fittop"):   # whole frame (fittop: without the bottom subtitle band) over a blurred fill
        top = ",crop=1920:880:0:0" if mode == "fittop" else ""
        fh = 496 if mode == "fittop" else 608
        fc.append(f"[{j}:v]fps=30,scale=1920:1080{top},split[a{j}][b{j}];[a{j}]scale={VW}:{VH}:force_original_aspect_ratio=increase,"
                  f"crop={VW}:{VH},boxblur=20:2,eq=brightness=-0.1[bl{j}];[b{j}]scale={VW}:{fh}[fg{j}];"
                  f"[bl{j}][fg{j}]overlay=0:{(VH - fh) // 2},setsar=1,trim=duration={d:.3f},setpts=PTS-STARTPTS[s{j}]")
    else:
        fc.append(f"[{j}:v]fps=30,scale=1920:1080,{CROP[src]},scale={VW}:{VH}:flags=lanczos,setsar=1,"
                  f"trim=duration={d:.3f},setpts=PTS-STARTPTS[s{j}]")
    lab.append(f"[s{j}]")
n = len(shots)
hw, hh = render_hook(re.sub(r"\s+(?=[\U0001F000-\U0001FAFF☀-➿])", "", hook), K + ".hook.png", size=60, max_w=900, single=True)
fc.append("".join(lab) + f"concat=n={n}:v=1:a=0[vid]")
fc.append(f"color=c=black:s={W}x{H}:r=30:d={dur:.2f}[bg];[bg][vid]overlay=0:{VY}:shortest=1[b1]")
fc.append(f"[{n}:v]format=rgba[hk];[b1][hk]overlay=0:{VY - 30 - hh}:format=auto[b2]")
fc.append(f"[b2]subtitles={K}.ass:fontsdir=/usr/share/fonts/truetype/vazirmatn,format=yuv420p[v]")

# captions: <=3 words / <=14 letters, break on punctuation
clean = lambda t: re.sub(r"[\.،…]+", "", t)
groups, cur = [], []
for w in cw:
    cur.append(w)
    if len(cur) == 3 or re.search(r"[\.،!؟\?…]", w[2]) or sum(len(clean(x[2])) for x in cur) >= 14:
        groups.append(cur); cur = []
if cur: groups.append(cur)
def ts(x):
    h, r = divmod(max(x, 0), 3600); m, s = divmod(r, 60); return f"{int(h)}:{int(m):02d}:{s:05.2f}"
ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
       "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: Cap,Vazirmatn,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,2,5,60,60,0,1", "",
       "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
for gi, g in enumerate(groups):
    s, e = g[0][0], g[-1][1] + 0.15
    if gi + 1 < len(groups): e = min(e, groups[gi + 1][0][0])
    ass.append(f"Dialogue: 1,{ts(s)},{ts(e)},Cap,,0,0,0,,{{\\pos(540,1290)}}" + " ".join(clean(x[2]) for x in g))
open(K + ".ass", "w", encoding="utf-8").write("\n".join(ass) + "\n")

subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins, "-loop", "1", "-t", f"{dur:.2f}", "-i", K + ".hook.png",
                "-i", K + ".mp3", "-filter_complex", ";".join(fc), "-map", "[v]", "-map", f"{n + 1}:a",
                "-af", "apad,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
                "-t", f"{dur:.2f}", K + ".mp4"], check=True)
print("rendered", K, round(dur, 1), "s", n, "shots")
