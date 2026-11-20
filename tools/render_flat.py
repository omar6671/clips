"""Horizontal video on black (barely zoomed), Latin-script hook above it for the whole clip.
Hook text: lines split by "|", words wrapped in *stars* get the accent colour, emojis render in colour.
usage: render_flat.py SRC clips.json OUTDIR [ids]
clips: [{"id","start","end","hook","accent": "#F5C518", "zoom": 1.04}]"""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

src, cpath, outdir = sys.argv[1:4]
only = set(sys.argv[4:])
os.makedirs(outdir, exist_ok=True)
W, H = 1080, 1920
FONT = "/usr/share/fonts/truetype/inter/Inter-Bold.ttf" if os.path.exists("/usr/share/fonts/truetype/inter/Inter-Bold.ttf") else None
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMO = re.compile(r"([\U0001F000-\U0001FAFF☀-➿⬀-⯿][️‍\U0001F000-\U0001FAFF]*)")
ENC = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "medium", "-crf", "18", "-g", "60",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart"]


def find_font():
    out = subprocess.run(["fc-match", "-f", "%{file}", "Inter:bold"], capture_output=True, text=True).stdout
    return FONT or out


def hook_png(text, path, accent, size=62):
    font = ImageFont.truetype(find_font(), size)
    efont = ImageFont.truetype(EMOJI, 109)
    esz = int(size * 1.05)
    asc, desc = font.getmetrics(); lh = asc + desc
    lines = []
    for ln in text.split("|"):
        parts = []  # (kind, text, colour)
        for tok in re.split(r"(\*[^*]+\*)", ln.strip()):
            if not tok: continue
            col = accent if tok.startswith("*") else "#FFFFFF"
            tok = tok.strip("*")
            for p in EMO.split(tok):
                if p: parts.append(("e" if EMO.fullmatch(p) else "t", p, col))
        lines.append(parts)
    def width(parts):
        w = 0
        for k, t, c in parts:
            w += esz + 6 if k == "e" else font.getlength(t)
        return int(w)
    gap = 14
    Hh = len(lines) * lh + (len(lines) - 1) * gap + 10
    img = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    y = 0
    for parts in lines:
        x = (W - width(parts)) // 2
        for k, t, c in parts:
            if k == "e":
                im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
                ImageDraw.Draw(im).text((10, 10), t, font=efont, embedded_color=True)
                im = im.crop(im.getbbox() or (0, 0, 1, 1)); im = im.resize((esz, int(esz * im.height / im.width)), Image.LANCZOS)
                img.alpha_composite(im, (x + 6, y + (lh - im.height) // 2 + 2)); x += esz + 6
            else:
                d.text((x, y), t, font=font, fill=c); x += int(font.getlength(t))
        y += lh + gap
    img.save(path)
    return Hh


for c in json.load(open(cpath, encoding="utf-8")):
    if only and c["id"] not in only: continue
    s0, dur = c["start"], c["end"] - c["start"]
    base = os.path.join(outdir, f"clip{c['id']}")
    hh = hook_png(c["hook"], base + ".hook.png", c.get("accent", "#F5C518"))
    z = c.get("zoom", 1.04)
    vh = int(W / (16 / 9)) // 2 * 2
    vy = (H - vh) // 2
    hy = vy - 40 - hh
    assert hy > 220, hy
    fc = (f"color=c=black:s={W}x{H}:r=30[bg];"
          f"[0:v]fps=30,crop=iw/{z}:ih/{z},scale={W}:{vh}:flags=lanczos,setsar=1[vid];"
          f"[bg][vid]overlay=0:{vy}:shortest=1[st];[1:v]format=rgba[hk];"
          f"[st][hk]overlay=0:{hy}:format=auto,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s0:.2f}", "-t", f"{dur:.2f}", "-i", src,
                    "-loop", "1", "-t", f"{dur:.2f}", "-i", base + ".hook.png", "-filter_complex", fc,
                    "-map", "[v]", "-map", "0:a:0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
                    *ENC, "-t", f"{dur:.2f}", base + ".mp4"], check=True)
    print("rendered", base + ".mp4", flush=True)
