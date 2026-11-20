"""Transcribe Arabic audio with faster-whisper, appending segments to a JSONL file.
Resumable: if the output exists, continues from the last segment's end time."""
import json, os, sys, time, wave
import numpy as np
from faster_whisper import WhisperModel

audio, out, model_dir = sys.argv[1], sys.argv[2], sys.argv[3]

start = 0.0
if os.path.exists(out):
    with open(out, encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    if lines:
        start = json.loads(lines[-1])["end"]
print(f"starting at {start:.1f}s", flush=True)

with wave.open(audio) as wf:
    pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

model = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=os.cpu_count())
segments, info = model.transcribe(
    pcm,
    language="ar",
    beam_size=5,
    word_timestamps=True,
    vad_filter=True,
    condition_on_previous_text=False,
    clip_timestamps=[start] if start else "0",
    initial_prompt="حوار باللهجة الخليجية.",
)
t0 = time.time()
with open(out, "a", encoding="utf-8") as f:
    for s in segments:
        rec = {
            "start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
            "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in (s.words or [])],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        print(f"{s.end:7.1f}s  elapsed {time.time()-t0:6.0f}s", flush=True)
print("DONE", flush=True)
