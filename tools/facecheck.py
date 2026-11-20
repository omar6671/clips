"""For each clipNN.mp4 in OUTDIR (ids given), check faces vs hook box during the first 4.5s.
Prints overlap fraction per clip; >0 means the hook touches a face."""
import sys, os, subprocess, numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framing import FRONT, PROFILE
outdir, hook_bottom = sys.argv[1], int(sys.argv[2]); ids = sys.argv[3:]
for i in ids:
    base = os.path.join(outdir, f"clip{i}")
    a = np.array(Image.open(base + ".hook.png"))[:, :, 3]
    ys, xs = np.nonzero(a > 0); hh = a.shape[0]; y0 = hook_bottom - hh if hook_bottom > 0 else -hook_bottom - hh // 2
    hb = (xs.min(), y0 + ys.min(), xs.max(), y0 + ys.max())
    worst = 0.0
    for t in (0.2, 1.0, 2.0, 3.0, 4.0):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", base + ".mp4", "-frames:v", "1",
                              "-vf", "crop=1080:960:0:0,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        img = np.frombuffer(raw[:1080 * 960], np.uint8).reshape(960, 1080)
        for casc in (FRONT, PROFILE):
            for (x, y, w, h) in casc.detectMultiScale(img, 1.1, 5, minSize=(60, 60)):
                # face incl. chin margin
                fx0, fy0, fx1, fy1 = x, y, x + w, y + int(h * 1.15)
                ix = max(0, min(fx1, hb[2]) - max(fx0, hb[0])); iy = max(0, min(fy1, hb[3]) - max(fy0, hb[1]))
                worst = max(worst, ix * iy / (w * h))
    print(i, "hook y", hb[1], "-", hb[3], "face overlap", round(worst, 2), "BAD" if worst > 0 else "ok")
