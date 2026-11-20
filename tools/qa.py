"""QA rendered clips: full decode, stream checks, loudness, contact sheet."""
import json, os, re, subprocess, sys

outdir = sys.argv[1]
files = sorted(f for f in os.listdir(outdir) if f.endswith(".mp4") and f.startswith("clip"))
ok_all = True
for f in files:
    p = os.path.join(outdir, f)
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", p],
                                   capture_output=True, text=True).stdout)
    v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in pr["streams"] if s["codec_type"] == "audio"]
    dur = float(pr["format"]["duration"])
    vd, ad = float(v.get("duration", 0)), float(a[0].get("duration", 0)) if a else 0
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                         capture_output=True, text=True)
    errs = [l for l in dec.stderr.splitlines() if l.strip() and "Summary" not in l and not l.startswith(" ")]
    lufs = subprocess.run(["ffmpeg", "-nostats", "-i", p, "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", lufs)
    I = float(m[-1]) if m else None
    head = open(p, "rb").read(64)
    faststart = head.find(b"moov") != -1 or b"moov" in open(p, "rb").read(200000)
    checks = {
        "1080x1920": (v["width"], v["height"]) == (1080, 1920),
        "h264/yuv420p": v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p",
        "30fps": v["r_frame_rate"] == "30/1",
        "audio aac": bool(a) and a[0]["codec_name"] == "aac",
        "15-60s": 15 <= dur <= 60.05,
        "a/v len": abs(vd - ad) < 0.15,
        "decode clean": not errs,
        "loudness": I is not None and -16.5 < I < -11.5,
        "faststart": faststart,
    }
    bad = [k for k, ok in checks.items() if not ok]
    ok_all &= not bad
    print(f"{f}: {dur:5.1f}s  v={vd:.2f} a={ad:.2f}  {I} LUFS  {os.path.getsize(p)/1e6:.0f}MB  "
          + ("OK" if not bad else "FAIL " + ",".join(bad) + (" | " + errs[0][:120] if errs else "")))
    sheet = p[:-4] + ".sheet.jpg"
    n = int(dur * 30)
    sel = "+".join(f"eq(n,{int(n * k / 6)})" for k in range(6))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", f"select='{sel}',scale=240:-2,tile=6x1",
                    "-vsync", "0", "-frames:v", "1", sheet])
print("ALL OK" if ok_all else "SOME FAILED")
