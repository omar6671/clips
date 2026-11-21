"""Gold-gradient Arabic hook in quotes ("..."), heavy font, dark outline + soft shadow, no box. Max 2 lines ("|").
render(text, path) -> (w, h)"""
import re
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Black.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMO = re.compile(r"\s*([\U0001F000-\U0001FAFF☀-➿⬀-⯿][️‍\U0001F000-\U0001FAFF]*)\s*")


def render(text, path, width=1080, size=88, top=(255, 236, 140), bottom=(242, 176, 0)):
    emojis = EMO.findall(text)
    text = EMO.sub(" ", text).strip()
    lines = [l.strip() for l in text.split("|")]
    pad, stroke, qgap = 24, 3, 10
    ne = len(emojis[:2])
    while True:  # shrink until every line (with quotes and emoji) fits in 960 px
        font = ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)
        qfont = font
        esz = int(size * 0.95)
        boxes = [font.getbbox(l, direction="rtl", stroke_width=stroke) for l in lines]
        qw = int(qfont.getlength("\u201d")) + stroke * 2
        def lwidth(i):
            w = boxes[i][2] - boxes[i][0]
            if i == 0: w += qw + qgap
            if i == len(lines) - 1: w += qw + qgap + (ne * (esz + 6) + 6 if ne else 0)
            return w
        if max(lwidth(i) for i in range(len(lines))) <= 960 or size <= 40: break
        size -= 2
    lh = max(b[3] - b[1] for b in boxes)
    W = width
    H = len(lines) * (lh + 10) + 2 * pad
    mask = Image.new("L", (W, H), 0); outline = Image.new("L", (W, H), 0)
    md, od = ImageDraw.Draw(mask), ImageDraw.Draw(outline)
    def put(x, y, s_, b):
        od.text((x - b[0], y - b[1]), s_, font=font, fill=255, direction="rtl", stroke_width=stroke, stroke_fill=255)
        md.text((x - b[0], y - b[1]), s_, font=font, fill=255, direction="rtl")
    emo_at = None
    y = pad
    for i, (l, b) in enumerate(zip(lines, boxes)):
        right = (W + lwidth(i)) // 2          # lay pieces out from the right edge leftwards
        if i == 0:
            qb = font.getbbox("\u201d", stroke_width=stroke)
            put(right - (qb[2] - qb[0]), y, "\u201d", (qb[0], b[1], qb[2], b[3])); right -= qw + qgap
        put(right - (b[2] - b[0]), y, l, b); right -= (b[2] - b[0]) + qgap
        if i == len(lines) - 1:
            qb = font.getbbox("\u201c", stroke_width=stroke)
            put(right - (qb[2] - qb[0]), y, "\u201c", (qb[0], b[1], qb[2], b[3])); right -= qw + 6
            emo_at = (right, y)
        y += lh + 10
    grad = Image.new("RGBA", (W, H))
    gd = ImageDraw.Draw(grad)
    for yy in range(H):
        # gradient per line height so each line goes light -> gold
        t = ((yy - pad) % (lh + 10)) / max(lh, 1)
        t = min(max(t, 0), 1)
        gd.line([(0, yy), (W, yy)], fill=tuple(int(a + (b_ - a) * t) for a, b_ in zip(top, bottom)) + (255,))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(outline.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.7)))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.alpha_composite(shadow, (3, 4))
    ol = Image.new("RGBA", (W, H), (40, 24, 0, 255)); ol.putalpha(outline)
    img.alpha_composite(ol)
    fill = grad.copy(); fill.putalpha(mask)
    img.alpha_composite(fill)
    if emojis:  # emoji(s) at the left end of the last line (RTL reading end)
        efont = ImageFont.truetype(EMOJI, 109)
        ex, y = emo_at
        ex -= esz
        for e in emojis[:2]:
            im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((10, 10), e, font=efont, embedded_color=True)
            im = im.crop(im.getbbox() or (0, 0, 1, 1)); im = im.resize((esz, int(esz * im.height / im.width)), Image.LANCZOS)
            img.alpha_composite(im, (ex, y + (lh - im.height) // 2))
            ex -= esz + 4
    bb = img.getbbox()
    img = img.crop((0, bb[1], W, bb[3]))
    img.save(path)
    return img.size


if __name__ == "__main__":
    import sys
    print(render(sys.argv[1], sys.argv[2]))
