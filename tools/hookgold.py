"""Yellow quoted Arabic hook (TikTok "classic" look): flat yellow Noto Sans Arabic Bold, thin dark outline + soft
shadow, no box. The whole hook incl. emojis sits inside straight quotes. Max 2 lines ("|"), max width 800 px so the
first/last word stays clear of the TikTok side buttons.  render(text, path) -> (w, h)
Font: IBM Plex Sans Arabic 600 (npm @fontsource/ibm-plex-sans-arabic, .woff) in /usr/share/fonts/truetype/notoarabic/."""
import re
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/usr/share/fonts/truetype/notoarabic/ibm-plex-sans-arabic-arabic-600-normal.woff"
QFONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMO = re.compile(r"\s*([\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF](?:\uFE0F|[\U0001F3FB-\U0001F3FF]|\u200D[\U0001F000-\U0001FAFF\u2600-\u27BF])*)\s*")
YELLOW = (236, 204, 88, 255)
EDGE = (0, 0, 0, 255)


def render(text, path, width=1080, size=76, max_w=800):
    emojis = EMO.findall(text)[:2]
    lines = [l.strip() for l in EMO.sub(" ", text).strip().split("|")]
    stroke = 3
    while True:
        font = ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)
        qfont = ImageFont.truetype(QFONT, int(size * 1.05))
        esz = int(size * 0.9)
        qw = int(qfont.getlength('\u201d')) + 2
        boxes = [font.getbbox(l, direction="rtl") for l in lines]
        def lw(i):
            w = boxes[i][2] - boxes[i][0]
            if i == 0: w += qw + 2
            if i == len(lines) - 1: w += qw + 2 + len(emojis) * (esz + 6)
            return w
        if max(lw(i) for i in range(len(lines))) <= max_w or size <= 40: break
        size -= 2
    asc, desc = font.getmetrics()
    lh = asc + desc
    pad = 20
    H = len(lines) * lh + 2 * pad
    W = width
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    emo_pos = []
    y = pad
    for i, l in enumerate(lines):
        right = (W + lw(i)) // 2
        if i == 0:  # opening quote at the right (RTL start)
            d.text((right - qw + 2, y + int(size * 0.12)), '\u201d', font=qfont, fill=YELLOW, stroke_width=stroke, stroke_fill=EDGE)
            right -= qw + 2
        b = boxes[i]
        d.text((right - (b[2] - b[0]) - b[0], y), l, font=font, fill=YELLOW, direction="rtl", stroke_width=stroke, stroke_fill=EDGE)
        right -= (b[2] - b[0])
        if i == len(lines) - 1:
            for e in emojis:
                right -= esz + 6; emo_pos.append((right, y + (lh - esz) // 2 + int(size * 0.08)))
            right -= 2
            d.text((right - qw + 2, y + int(size * 0.12)), '\u201d', font=qfont, fill=YELLOW, stroke_width=stroke, stroke_fill=EDGE)
        y += lh
    efont = ImageFont.truetype(EMOJI, 109)
    for e, (ex, ey) in zip(emojis, emo_pos):
        im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), e, font=efont, embedded_color=True)
        im = im.crop(im.getbbox() or (0, 0, 1, 1)); im = im.resize((esz, int(esz * im.height / im.width)), Image.LANCZOS)
        txt.alpha_composite(im, (ex, ey))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(txt.getchannel("A").filter(ImageFilter.GaussianBlur(3)).point(lambda v: min(255, int(v * 1.0))))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.alpha_composite(shadow, (3, 4)); img.alpha_composite(shadow, (1, 2)); img.alpha_composite(txt)
    bb = img.getbbox(); img = img.crop((0, max(bb[1] - 4, 0), W, min(bb[3] + 4, H)))
    img.save(path)
    return img.size


if __name__ == "__main__":
    import sys
    print(render(sys.argv[1], sys.argv[2]))
