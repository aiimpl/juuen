"""締めのタイトル（横書き・下の中央）を透過 PNG で build/title.png に作る。"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fonts  # noqa: E402

OUT = os.path.join(ROOT, 'build')
W, H = 1920, 1080

layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(layer)
tf = ImageFont.truetype(fonts.find('title'), 92)
sf = ImageFont.truetype(fonts.find('mincho'), 30, index=0)
ef = ImageFont.truetype(fonts.find('serif'), 24)
gold = (242, 220, 170, 255)
title = '平等院鳳凰堂'
sp = 34
ws = [d.textbbox((0, 0), ch, font=tf)[2] - d.textbbox((0, 0), ch, font=tf)[0] for ch in title]
tw = sum(ws) + sp * (len(title) - 1)
x = (W - tw) / 2
y0 = 842
for ch, w in zip(title, ws):
    bb = d.textbbox((0, 0), ch, font=tf)
    d.text((x - bb[0], y0 - bb[1]), ch, font=tf, fill=gold)
    x += w + sp
# 上下の細い線と、小さな添え書き
cy = y0 + 118
d.line([(W / 2 - 420, cy), (W / 2 - 140, cy)], fill=(242, 220, 170, 200), width=2)
d.line([(W / 2 + 140, cy), (W / 2 + 420, cy)], fill=(242, 220, 170, 200), width=2)
sub = '宇治'
bb = d.textbbox((0, 0), sub, font=sf)
d.text((W / 2 - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), sub, font=sf, fill=(236, 222, 196, 255))
eng = 'B Y O D O - I N    P H O E N I X   H A L L'
bb = d.textbbox((0, 0), eng, font=ef)
d.text(((W - (bb[2] - bb[0])) / 2, cy + 30), eng, font=ef, fill=(236, 222, 196, 220))
y1 = y0 - 34
d.line([(W / 2 - 60, y1), (W / 2 + 60, y1)], fill=(242, 220, 170, 200), width=2)
a = np.asarray(layer)[..., 3]
shadow = Image.fromarray(a).filter(ImageFilter.GaussianBlur(10))
sh = Image.new('RGBA', (W, H), (18, 10, 4, 0))
sh.putalpha(shadow.point(lambda v: int(v * 0.7)))
out = Image.alpha_composite(sh, layer)
os.makedirs(OUT, exist_ok=True)
out.save(os.path.join(OUT, 'title.png'))
print('wrote', os.path.join(OUT, 'title.png'))
