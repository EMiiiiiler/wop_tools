#!/usr/bin/env python3
"""Make World of Padman style levelshots from preview renders.

    python3 levelshots.py <mapname> <outdir> --cover aerial.png --shots a.png b.png c.png
                          --title "SPLASH WORLD" --sub "CLOUD LAGOON" --badge "3 SLIDES!|SECRET|GROTTO!"

Writes <outdir>/<map>.jpg (512, loading screen), <map>A.jpg (256, start-server list) and
<map>B1..B3.jpg (256, server browser focus pics). Add this to your .shader so the B shots animate:

    levelshots/<map>B
    {
        nomipmaps
        {
            animmap 0.5 levelshots/<map>B1 levelshots/<map>B2 levelshots/<map>B3
        }
    }
"""
import os, math, argparse
from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONT):
    FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def fit(d, t, maxw, size):
    while size > 10:
        f = ImageFont.truetype(FONT, size)
        if d.textlength(t, font=f) <= maxw: return f
        size -= 2
    return ImageFont.truetype(FONT, size)


def ol(d, xy, text, font, fill, stroke, sw):
    d.text(xy, text, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke)


def cover(bg, title, sub, badge, S=512):
    im = Image.open(bg).convert('RGB').resize((S - 24, S - 24))
    c = Image.new('RGB', (S, S), (255, 210, 40)); c.paste(im, (12, 12))
    d = ImageDraw.Draw(c)
    d.rectangle([12, 12, S - 12, S - 12], outline=(20, 20, 30), width=4)
    d.polygon([(12, 12), (S - 12, 12), (S - 12, 124), (12, 150)], fill=(20, 120, 215))
    f1 = fit(d, title, S - 80, 72); w = d.textlength(title, font=f1)
    ol(d, ((S - w) / 2, 22), title, f1, (255, 226, 60), (20, 20, 40), 5)
    if sub:
        f2 = fit(d, sub, S - 160, 30); w2 = d.textlength(sub, font=f2)
        ol(d, ((S - w2) / 2, 96), sub, f2, (255, 255, 255), (20, 20, 40), 3)
    if badge:
        cx, cy, r1, r2 = 408, 418, 80, 58
        pts = [(cx + (r1 if i % 2 == 0 else r2) * math.cos(math.pi * i / 12 - 0.2),
                cy + (r1 if i % 2 == 0 else r2) * math.sin(math.pi * i / 12 - 0.2)) for i in range(24)]
        d.polygon(pts, fill=(240, 60, 50), outline=(20, 20, 30))
        lines = badge.split('|'); f3 = ImageFont.truetype(FONT, 19)
        for k, line in enumerate(lines):
            w = d.textlength(line, font=f3)
            ol(d, (cx - w / 2, cy - 12 * len(lines) + 23 * k - 4), line, f3, (255, 255, 255), (60, 10, 10), 2)
    tag = 'a World of Padman map'; ft = ImageFont.truetype(FONT, 18)
    ol(d, (28, S - 46), tag, ft, (255, 255, 255), (20, 20, 40), 2)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map'); ap.add_argument('out')
    ap.add_argument('--cover', required=True); ap.add_argument('--shots', nargs='*', default=[])
    ap.add_argument('--title', default=None); ap.add_argument('--sub', default='')
    ap.add_argument('--badge', default='')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    c = cover(a.cover, a.title or a.map.upper(), a.sub, a.badge)
    c.save(os.path.join(a.out, a.map + '.jpg'), quality=92)
    c.resize((256, 256), Image.LANCZOS).save(os.path.join(a.out, a.map + 'A.jpg'), quality=92)
    for i, s in enumerate(a.shots[:3]):
        Image.open(s).convert('RGB').resize((256, 256), Image.LANCZOS).save(os.path.join(a.out, f'{a.map}B{i + 1}.jpg'), quality=90)
    print('levelshots written to', a.out)


if __name__ == '__main__':
    main()
