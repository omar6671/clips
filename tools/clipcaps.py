"""Word-timed captions for chosen clips: re-transcribe each clip (large-v3, no VAD), group into short
caption chunks timed to the voice, store as clip["caps"] in clips.json (text to be checked by hand).
usage: clipcaps.py SRC clips.json MODEL_DIR [ids]"""
import json, os, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

src, cpath, mdir = sys.argv[1:4]
only = set(sys.argv[4:])
PUNCT = ".,،؟?!:;…\"'"
model = WhisperModel(mdir, device="cpu", compute_type="int8", cpu_threads=os.cpu_count())


def audio(s, d):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{s:.2f}", "-t", f"{d:.2f}", "-i", src, "-vn", "-ac", "1",
                          "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def voiced_mask(a):
    hop = 320
    b = a[:len(a) // hop * hop].reshape(-1, hop)
    db = 20 * np.log10(np.sqrt((b ** 2).mean(1)) + 1e-6)
    return db > np.percentile(db, 15) + 14


clips = json.load(open(cpath, encoding="utf-8"))
for c in clips:
    if only and c["id"] not in only:
        continue
    dur = c["end"] - c["start"]
    a = audio(c["start"], dur)
    segs, _ = model.transcribe(a, language="ar", beam_size=5, word_timestamps=True, vad_filter=False,
                               condition_on_previous_text=False, initial_prompt="سوالف باللهجة السعودية الخليجية.")
    words = [w for s in segs for w in (s.words or []) if w.word.strip().strip(PUNCT)]
    vm = voiced_mask(a)
    groups, cur = [], []
    for w in words:
        txt = w.word.strip()
        if cur and (len(cur) >= 3 or w.start - cur[-1].end > 0.5 or cur[-1].word.strip()[-1:] in ".?!؟،,"
                    or sum(len(x.word.strip()) + 1 for x in cur) + len(txt) > 17):
            groups.append(cur); cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    caps = []
    for i, g in enumerate(groups):
        st, en = g[0].start, g[-1].end
        # snap the start to the first voiced frame near the word start (whisper is often early)
        i0, i1 = int(max(st - 0.1, 0) / 0.02), int(min(en, dur) / 0.02)
        on = next((k for k in range(i0, max(i0, i1 - 2)) if vm[k:k + 3].all()), None)
        if on is not None:
            st = on * 0.02 - 0.03
        nxt = groups[i + 1][0].start if i + 1 < len(groups) else dur
        en = min(en + 0.15, nxt, dur)
        if caps:
            st = max(st, caps[-1][1])
        en = max(en, st + 0.4)
        text = " ".join(x.word.strip().strip(PUNCT) for x in g)
        caps.append([round(st, 2), round(en, 2), text])
    c["caps"] = caps
    print(c["id"], " | ".join(t for _, _, t in caps), flush=True)
    json.dump(clips, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
