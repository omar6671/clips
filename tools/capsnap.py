"""Snap caption times to real speech: start when the voice starts, end right after it stops; no gap filling.
usage: capsnap.py SRC clips.json ID"""
import json, subprocess, sys, numpy as np
src, cpath, cid = sys.argv[1:4]
clips = json.load(open(cpath, encoding="utf-8")); c = [x for x in clips if x["id"] == cid][0]
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(c["start"]), "-t", str(c["end"] - c["start"]), "-i", src,
                      "-vn", "-ac", "1", "-ar", "16000", "-af", "highpass=f=120,lowpass=f=4000", "-f", "s16le", "-"], capture_output=True).stdout
a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
hop = 320  # 20ms
db = 20 * np.log10(np.array([np.sqrt((a[i:i + hop] ** 2).mean()) + 1e-6 for i in range(0, len(a) - hop, hop)]))
thr = np.percentile(db, 15) + 15
voiced = db > thr
def onset(t0, t1):
    i0, i1 = max(int(t0 / 0.02), 0), min(int(t1 / 0.02), len(voiced) - 3)
    for i in range(i0, i1):
        if voiced[i] and voiced[i + 1] and voiced[i + 2]: return i * 0.02
    return None
def offset(t0, t1):
    i1, i0 = min(int(t1 / 0.02), len(voiced) - 1), max(int(t0 / 0.02), 0)
    for i in range(i1, i0, -1):
        if voiced[i]: return (i + 1) * 0.02
    return None
caps = c["caps"]; out = []
for k, (s, e, t) in enumerate(caps):
    nxt = caps[k + 1][0] if k + 1 < len(caps) else c["end"] - c["start"]
    on = onset(s - 0.1, min(e, nxt)) or s
    off = offset(on, min(e + 0.3, nxt)) or e
    st = max(on - 0.03, out[-1][1] if out else 0)
    en = max(min(off + 0.2, nxt), st + 0.45)
    out.append([round(st, 2), round(en, 2), t])
for (s, e, t), (s2, e2, _) in zip(caps, out): print(f"{s:5.2f}-{e:5.2f} -> {s2:5.2f}-{e2:5.2f}  {t}")
c["caps"] = out
json.dump(clips, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
