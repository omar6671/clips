"""Shot-aware framing for a time range of a multi-camera video.

Returns a list of shots relative to the range start:
  {"a": sec, "b": sec, "mode": "crop", "cx": 0..1}  close-up -> crop centered on the face
  {"a": sec, "b": sec, "mode": "fit"}               wide / no face -> full frame on blurred bg
"""
import subprocess, re
import numpy as np
import cv2

FRONT = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PROFILE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
AW = 960  # analysis width


def scene_cuts(src, start, dur, thresh=15.0):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", src, "-t", f"{dur:.2f}",
           "-an", "-vf", "fps=30,scale=64:36", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    fr = np.frombuffer(raw[:len(raw) // 2304 * 2304], np.uint8).reshape(-1, 36, 64).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    out = []
    for i, v in enumerate(d):
        c = (i + 1) / 30
        if v > thresh and (not out or c - out[-1] > 0.4):
            out.append(c)
    return out


def grab(src, t, sw, sh):
    ah = int(AW * sh / sw)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
           "-vf", f"scale={AW}:{ah}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    if len(raw) < AW * ah:
        return None
    return np.frombuffer(raw[:AW * ah], np.uint8).reshape(ah, AW)


def faces(img):
    h = img.shape[0]
    found = []
    for casc, flip in ((FRONT, False), (PROFILE, False), (PROFILE, True)):
        im = cv2.flip(img, 1) if flip else img
        for (x, y, w, fh) in casc.detectMultiScale(im, 1.1, 6, minSize=(int(h * 0.04),) * 2):
            if flip:
                x = img.shape[1] - x - w
            found.append((x + w / 2, fh))
    return found


def analyze(src, start, dur, sw, sh):
    cuts = [c for c in scene_cuts(src, start, dur) if 0.3 < c < dur - 0.3]
    bounds = [0.0] + cuts + [dur]
    shots = []
    for a, b in zip(bounds, bounds[1:]):
        samples = [a + (b - a) * f for f in (0.25, 0.5, 0.75)] if b - a > 1.5 else [(a + b) / 2]
        big, small = [], []
        for t in samples:
            img = grab(src, start + t, sw, sh)
            if img is None:
                continue
            h = img.shape[0]
            fs = faces(img)
            big += [cx for cx, fh in fs if fh > 0.13 * h]
            small += [cx for cx, fh in fs if fh <= 0.13 * h]
        if big:
            shots.append({"a": a, "b": b, "mode": "crop", "cx": float(np.median(big)) / AW})
        else:
            cx = (min(small) + max(small)) / 2 / AW if small else 0.47
            shots.append({"a": a, "b": b, "mode": "fit", "cx": float(min(max(cx, 0.35), 0.65))})
    # merge neighbours with the same framing
    merged = []
    for s in shots:
        p = merged[-1] if merged else None
        if p and p["mode"] == s["mode"] and abs(p["cx"] - s["cx"]) < 0.04:
            p["b"] = s["b"]
        else:
            merged.append(dict(s))
    return merged
