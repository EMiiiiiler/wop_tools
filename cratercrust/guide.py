import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import json, math, sys
from PIL import Image, ImageDraw, ImageFont
SCR = sys.argv[1]; OUT = sys.argv[2]
exec(open(_os.path.join(_HERE, 'build_map.py')).read())
base = Image.open(SCR + '/renders/topdown.png').convert('RGB')
W, H = base.size
f = (W / 2) / math.tan(math.radians(8.8) / 2)
def px(x, y, z=0):
    dz = 30000 - z
    return (W / 2 + f * (x - 416) / dz, H / 2 - f * y / dz)
img = Image.new('RGB', (W, H + 230), (16, 10, 32)); img.paste(base, (0, 0))
ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
F = lambda s: ImageFont.truetype('/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf', s)
# jump pads
for p in pads:
    t = p['trig']; sx, sy = (t.mins[0] + t.maxs[0]) / 2, (t.mins[1] + t.maxs[1]) / 2
    a = px(sx, sy, t.mins[2]); b = px(*p['land'])
    d.line([a, b], fill=(255, 255, 255, 200), width=3)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-0.5, 0.5):
        d.line([b, (b[0] - 14 * math.cos(ang + s), b[1] - 14 * math.sin(ang + s))], fill=(255, 255, 255, 230), width=3)
# zones
for name, x, y in (('KITCHEN', -1300, -760), ('STOREROOM', -1490, 800), ('DINING', -600, 900), ('ARCADE', 800, 960),
                   ('BALL PIT', 864, 180), ('LANDER', 192, -280), ('PARKING LOT', 2050, -900), ('VAN', 1984, -680)):
    d.text(px(x, y), name, font=F(22), fill=(255, 255, 255, 235), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0, 255))
COL = {'imperius': (255, 40, 40), 'splasher': (60, 200, 255), 'boaster': (255, 160, 40), 'betty': (255, 60, 200),
       'pumper': (120, 255, 120), 'balloony': (255, 230, 60), 'bubbleg': (190, 120, 255)}
num = 1; legend = []
for it in items:
    c = it['cls']
    if not c.startswith('weapon_'): continue
    w = c.split('_')[1]; x, y, z = it['origin']
    p_ = px(x, y, z); r = 15
    d.ellipse([p_[0] - r, p_[1] - r, p_[0] + r, p_[1] + r], fill=COL[w] + (255,), outline=(0, 0, 0, 255), width=3)
    d.text(p_, str(num), font=F(17), fill=(0, 0, 0, 255), anchor='mm')
    legend.append((num, w, it['note'], z - 24)); num += 1
for e in ents:
    if e.kv['classname'] == 'station_health':
        x, y, z = e.kv['origin']; p_ = px(x, y)
        d.rectangle([p_[0] - 11, p_[1] - 4, p_[0] + 11, p_[1] + 4], fill=(255, 255, 255, 255)); d.rectangle([p_[0] - 4, p_[1] - 11, p_[0] + 4, p_[1] + 11], fill=(255, 255, 255, 255))
    if e.kv['classname'] in ('team_CTL_redlolly', 'team_CTL_bluelolly'):
        x, y, z = e.kv['origin']; p_ = px(x, y); c = (255, 60, 60, 255) if 'red' in e.kv['classname'] else (60, 120, 255, 255)
        d.polygon([(p_[0], p_[1] - 16), (p_[0] + 14, p_[1] + 10), (p_[0] - 14, p_[1] + 10)], fill=c, outline=(255, 255, 255, 255))
img = Image.alpha_composite(img.convert('RGBA'), ov).convert('RGB'); d = ImageDraw.Draw(img)
d.text((20, H + 12), 'CRATER CRUST  -  weapons, jump pads (white arrows), health stations (+), CTL lollies (triangles)', font=F(20), fill=(255, 230, 120))
colw = 530
for i, (n, w, note, z) in enumerate(legend):
    cx = 20 + (i // 6) * colw; cy = H + 50 + (i % 6) * 29
    d.ellipse([cx, cy, cx + 22, cy + 22], fill=COL[w], outline=(0, 0, 0), width=2)
    d.text((cx + 11, cy + 11), str(n), font=F(13), fill=(0, 0, 0), anchor='mm')
    d.text((cx + 32, cy + 1), '%s  -  %s%s' % (w.upper(), note, ('  (height %d)' % z) if z > 40 else ''), font=F(16), fill=(235, 235, 255))
img.save(OUT)
print('ok')
