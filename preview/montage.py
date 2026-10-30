#!/usr/bin/env python3
"""montage.py - many screenshots -> one labelled review sheet (read one image instead of twenty).

    python3 preview/montage.py out.png shots/*.png [--cols 4] [--width 1600] [--title "..."]

Each tile is labelled with its file name (the camera name), so a problem on the sheet maps straight back to a view in
mapinfo.json / autoviews. Tiles keep the screenshots' aspect ratio.
"""
import os, sys, argparse
from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def sheet(files, out, cols=4, width=1600, title=None):
    files = [f for f in files if os.path.exists(f)]
    if not files: raise SystemExit('no images')
    ims = [Image.open(f).convert('RGB') for f in files]
    tw = width // cols; th = int(tw * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    top = 44 if title else 0
    S = Image.new('RGB', (tw * cols, th * rows + top), (24, 26, 30)); d = ImageDraw.Draw(S)
    try: f = ImageFont.truetype(FONT, max(12, tw // 22)); ft = ImageFont.truetype(FONT, 26)
    except OSError: f = ft = ImageFont.load_default()
    if title: d.text((12, 8), title, font=ft, fill=(240, 240, 240))
    for i, (im, fn) in enumerate(zip(ims, files)):
        x, y = (i % cols) * tw, (i // cols) * th + top
        S.paste(im.resize((tw - 4, th - 4)), (x + 2, y + 2))
        lab = os.path.splitext(os.path.basename(fn))[0]
        bb = d.textbbox((0, 0), lab, font=f)
        d.rectangle((x + 2, y + 2, x + 12 + bb[2], y + 10 + bb[3]), fill=(0, 0, 0))
        d.text((x + 7, y + 4), lab, font=f, fill=(255, 230, 120))
    S.save(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out'); ap.add_argument('files', nargs='+')
    ap.add_argument('--cols', type=int, default=4); ap.add_argument('--width', type=int, default=1600); ap.add_argument('--title')
    a = ap.parse_args()
    print(sheet(sorted(a.files), a.out, a.cols, a.width, a.title))


if __name__ == '__main__':
    main()
