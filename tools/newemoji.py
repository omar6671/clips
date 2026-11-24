"""Draw original emoji-style faces (our own designs, not copies of any emoji set). render(kind, path, size=180)."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math

S = 1024  # draw big, downscale for smooth edges
FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"


def face(d, img):
    # soft shadow, gradient yellow ball, thin darker rim, glossy highlight
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((70, 95, S - 70, S - 45), fill=(0, 0, 0, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22)))
    ball = Image.new("RGBA", (S, S), (0, 0, 0, 0)); bd = ImageDraw.Draw(ball)
    for r in range(0, 440, 2):   # radial gradient: light centre-top -> orange edge
        t = r / 440
        col = (int(255 - 10 * t), int(222 - 70 * t), int(80 - 60 * t), 255)
        cx, cy = S // 2, S // 2 - int(60 * (1 - t))
        bd.ellipse((cx - (440 - r), cy - (440 - r) + int(60 * (1 - t)), cx + (440 - r), cy + (440 - r) + int(60 * (1 - t))), fill=col)
    mask = Image.new("L", (S, S), 0); ImageDraw.Draw(mask).ellipse((72, 72, S - 72, S - 72), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0)); out.paste(ball, (0, 0), mask); img.alpha_composite(out)
    d.ellipse((72, 72, S - 72, S - 72), outline=(214, 130, 20, 255), width=10)
    gl = Image.new("RGBA", (S, S), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse((250, 120, 620, 300), fill=(255, 255, 255, 110))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18)))


def loading(d, img):   # brain buffering: spinner eyes, progress bar, flat mouth
    face(d, img)
    for cx in (360, 664):
        d.ellipse((cx - 95, 400, cx + 95, 590), fill=(255, 255, 255, 255), outline=(60, 40, 20, 255), width=10)
        for k in range(8):   # spinner dots fading
            a = k / 8 * 2 * math.pi; r = 58; al = int(255 * (k + 1) / 8)
            x, y = cx + r * math.cos(a), 495 + r * math.sin(a)
            d.ellipse((x - 17, y - 17, x + 17, y + 17), fill=(70, 70, 80, al))
    d.rounded_rectangle((270, 200, 754, 290), 40, fill=(255, 255, 255, 255), outline=(60, 40, 20, 255), width=10)
    d.rounded_rectangle((285, 215, 360, 275), 30, fill=(60, 200, 90, 255))
    f = ImageFont.truetype(FONT, 56); d.text((512, 245), "1.5%", font=f, fill=(60, 40, 20, 255), anchor="mm")
    d.rounded_rectangle((400, 740, 624, 775), 18, fill=(110, 55, 20, 255))


def spiral(d, img):    # name overload: spiral eyes, open grin, "OZ" letters flying out
    face(d, img)
    for cx in (360, 664):
        d.ellipse((cx - 100, 390, cx + 100, 590), fill=(255, 255, 255, 255), outline=(60, 40, 20, 255), width=10)
        pts = [(cx + 6 * t * math.cos(t), 490 + 6 * t * math.sin(t)) for t in [i / 10 for i in range(0, 150)]]
        d.line(pts, fill=(60, 40, 20, 255), width=12)
    d.chord((330, 620, 694, 860), 0, 180, fill=(110, 40, 30, 255), outline=(60, 30, 20, 255), width=10)
    d.chord((380, 760, 644, 880), 180, 360, fill=(240, 100, 110, 255))
    f = ImageFont.truetype(FONT, 190)
    for txt, (x, y, rot) in (("O", (190, 120, 25)), ("Z", (820, 100, -20))):
        t = Image.new("RGBA", (260, 260), (0, 0, 0, 0)); td = ImageDraw.Draw(t)
        td.text((130, 130), txt, font=f, fill=(255, 255, 255, 255), anchor="mm", stroke_width=12, stroke_fill=(40, 90, 220, 255))
        t = t.rotate(rot, resample=Image.BICUBIC); img.alpha_composite(t, (x - 130, y - 130))


def moneytears(d, img):  # tears of joy, but the tears are banknotes
    face(d, img)
    for cx in (360, 664):   # happy closed eyes
        d.arc((cx - 95, 400, cx + 95, 560), 200, 340, fill=(60, 40, 20, 255), width=24)
    d.chord((300, 560, 724, 880), 0, 180, fill=(110, 40, 30, 255), outline=(60, 30, 20, 255), width=10)
    d.rectangle((370, 722, 654, 762), fill=(255, 255, 255, 255))
    for x, y, rot in ((150, 560, 35), (874, 560, -35), (110, 760, 20), (914, 760, -20)):
        n = Image.new("RGBA", (230, 230), (0, 0, 0, 0)); nd = ImageDraw.Draw(n)
        nd.rounded_rectangle((15, 60, 215, 170), 14, fill=(80, 175, 95, 255), outline=(30, 100, 50, 255), width=8)
        nd.ellipse((85, 85, 145, 145), outline=(30, 100, 50, 255), width=8)
        n = n.rotate(rot, resample=Image.BICUBIC); img.alpha_composite(n, (x - 115, y - 115))


def render(kind, path, size=180):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    {"loading": loading, "spiral": spiral, "moneytears": moneytears}[kind](d, img)
    img.resize((size, size), Image.LANCZOS).save(path)


if __name__ == "__main__":
    import sys
    render(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 180)
