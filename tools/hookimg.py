"""Render a TikTok-style Arabic hook (black text, white rounded box per line, color emoji) to a PNG."""
import re
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
B = "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]"
EMOJI_RE = re.compile(f"({B}(?:[\uFE0F\U0001F3FB-\U0001F3FF]|\u200D{B})*)")


def _join_latin(text):
    # keep runs of Latin words/numbers (e.g. "GTA 6", "MW4") together and in reading order
    return re.sub(r"(?<=[A-Za-z0-9])\s+(?=[A-Za-z0-9])", " ", text)


def tokens(text):
    text = _join_latin(text)
    out = []
    for word in [w for w in text.split(' ') if w.strip()]:
        for part in EMOJI_RE.split(word):
            if part:
                out.append(("e" if EMOJI_RE.fullmatch(part) else "t", part))
        out.append(("s", " "))
    return out[:-1]


def render(text, path, width=1080, max_w=940, size=68, pad_x=30, pad_y=14, radius=22, single=False):
    font = ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)
    efont = ImageFont.truetype(EMOJI, 109)
    esz = int(size * 1.05)
    space = int(size * 0.28)
    asc, desc = font.getmetrics()
    line_h = asc + desc

    def tok_img(kind, s):
        if kind == "e":
            im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((10, 10), s, font=efont, embedded_color=True)
            im = im.crop(im.getbbox() or (0, 0, 1, 1))
            return im.resize((esz, int(esz * im.height / im.width)), Image.LANCZOS)
        d_ = "rtl" if re.search(r"[؀-ۿ]", s) else "ltr"
        w = int(font.getlength(s, direction=d_)) + 2
        im = Image.new("RGBA", (w, line_h), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((w, 0), s, font=font, fill=(0, 0, 0, 255), anchor="ra", direction=d_)
        return im

    # group tokens into words (text+emoji glued), then wrap greedily right-to-left
    def mkwords(t):
        ws, cur = [], []
        for kind, s in tokens(t):
            if kind == "s":
                ws.append(cur); cur = []
            else:
                cur.append(tok_img(kind, s))
        ws.append(cur)
        return [w for w in ws if w]
    forced = [mkwords(p.strip()) for p in text.split("|")] if "|" in text else None
    words = [w for ln in forced for w in ln] if forced else mkwords(text)
    wwidth = lambda w: sum(i.width for i in w) + 4 * (len(w) - 1)

    lines, line = [], []
    for w in words:
        trial = line + [w]
        if line and sum(map(wwidth, trial)) + space * (len(trial) - 1) > max_w - 2 * pad_x:
            lines.append(line); line = [w]
        else:
            line = trial
    lines.append(line)
    if forced:
        lines = forced
    elif single and len(lines) == 2:  # balance two lines so they read as one block
        allw = lines[0] + lines[1]; lim = max_w - 2 * pad_x
        lw_ = lambda ws: sum(map(wwidth, ws)) + space * (len(ws) - 1)
        best = min((k for k in range(1, len(allw)) if lw_(allw[:k]) <= lim and lw_(allw[k:]) <= lim),
                   key=lambda k: max(lw_(allw[:k]), lw_(allw[k:])), default=None)
        if best: lines = [allw[:best], allw[best:]]

    row_h = line_h + 2 * pad_y
    gap = -6  # boxes slightly overlap so they read as one block
    H = len(lines) * row_h + (len(lines) - 1) * gap + 8
    img = Image.new("RGBA", (width, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 4
    boxes = []
    for ln in lines:
        lw = sum(map(wwidth, ln)) + space * (len(ln) - 1)
        x0 = (width - lw) // 2 - pad_x
        boxes.append((x0, y, x0 + lw + 2 * pad_x, y + row_h, ln, lw))
        y += row_h + gap
    if single:  # one solid block around all lines
        bx0 = min(b[0] for b in boxes); bx1 = max(b[2] for b in boxes)
        d.rounded_rectangle((bx0, boxes[0][1], bx1, boxes[-1][3]), radius=radius, fill=(255, 255, 255, 255))
    else:
        for (x0, y0, x1, y1, _, _) in boxes:
            d.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=(255, 255, 255, 255))
    for (x0, y0, x1, y1, ln, lw) in boxes:
        x = x1 - pad_x  # place words right-to-left
        for w in ln:
            ww = wwidth(w)
            xx = x - ww
            for part in w:  # parts within a word are in logical order -> lay out right-to-left too
                pass
            px = x
            for part in w:
                px -= part.width
                py = y0 + pad_y + (line_h - part.height) // 2 if part.height != line_h else y0 + pad_y
                img.alpha_composite(part, (px, py))
                px -= 4
            x = xx - space
    img.save(path)
    return img.size


if __name__ == "__main__":
    import sys
    print(render(sys.argv[1], sys.argv[2]))
