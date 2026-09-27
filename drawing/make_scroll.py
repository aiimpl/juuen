"""巻物に貼る墨の配置図（透明背景の RGBA）を build/tex/scroll_ink.png に描く。
紙の上＝西、右＝北。geometry.SCROLL の矩形（世界座標）がそのまま画像全面になるので、
墨線の立ち上がり（scene/wire.py）と図の線の位置が一致する。
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fonts  # noqa: E402
import geometry as G  # noqa: E402

PX = 70
OUT = os.path.join(ROOT, 'build', 'tex')
os.makedirs(OUT, exist_ok=True)
sc = G.SCROLL
W = int((sc['y1'] - sc['y0']) * PX)   # 横＝南北
H = int((sc['x1'] - sc['x0']) * PX)   # 縦＝東西（上が西）
rnd = random.Random(5)


def P(x, y):
    return ((y - sc['y0']) * PX, (x - sc['x0']) * PX)


ink = Image.new('L', (W, H), 0)
red = Image.new('L', (W, H), 0)
d = ImageDraw.Draw(ink)


def seg(x0, y0, x1, y1, w=3, a=225):
    d.line([P(x0, y0), P(x1, y1)], fill=a, width=max(2, int(w * 1.7)))


def poly(pts, w=3, a=225, closed=True):
    pp = [P(*p) for p in pts] + ([P(*pts[0])] if closed else [])
    d.line(pp, fill=a, width=max(2, int(w * 1.7)), joint='curve')


def rect(x0, y0, x1, y1, w=3, a=225):
    poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], w, a)


def dot(x, y, r=0.24, a=250):
    (u, v) = P(x, y)
    rr = r * PX
    d.rectangle([u - rr, v - rr, u + rr, v + rr], fill=a)


# 池の汀（太線）と内側の水線、中島の汀
poly(G.POND, 6)
poly(G.offset_poly(G.POND, 1.0), 2, 150)
poly(G.ISLAND, 5)
poly(G.offset_poly(G.ISLAND, -0.9), 2, 140)
# 洲浜の小石
for i in range(420):
    x, y = rnd.uniform(8, 14), rnd.uniform(-27, 27)
    if G.point_in_poly(x, y, G.ISLAND) and G.dist_to_poly(x, y, G.ISLAND) < 2.2:
        (u, v) = P(x, y)
        r = rnd.uniform(2, 5)
        d.ellipse([u - r, v - r, u + r, v + r], outline=170, width=2)
# 波紋：水面いっぱいに「〜」
for i in range(1400):
    x, y = rnd.uniform(sc['x0'], sc['x1']), rnd.uniform(sc['y0'], sc['y1'])
    if not G.point_in_poly(x, y, G.POND) or G.point_in_poly(x, y, G.ISLAND):
        continue
    if G.dist_to_poly(x, y, G.ISLAND) < 1.2 or G.dist_to_poly(x, y, G.POND) < 1.5:
        continue
    L_ = rnd.uniform(1.2, 2.2)
    pts = [(x + 0.28 * math.sin(k * 1.1), y + L_ * k / 10) for k in range(11)]
    poly(pts, 2, 175, closed=False)
for x, y, r in G.ROCKS:
    pts = [(x + r * 0.7 * math.cos(a) * (1 + 0.15 * math.sin(3 * a)), y + r * math.sin(a)) for a in np.linspace(0, 6.28, 14)]
    poly(pts, 3)
    seg(x - r * 0.2, y - r * 0.4, x + r * 0.2, y + r * 0.3, 2, 150)

# 建物：平面線・柱・床の目地
for ln in G.plan_lines():
    seg(*ln, 3, 235)
for (x, y, z0, z1, kind) in G.columns():
    dot(x, y, 0.2 if kind in ('core', 'moko') else 0.16)
for (x0, x1, y0, y1, dd) in G.wing_segments():
    if dd == 'y':
        for y in G.grid_between(y0, y1, G.BAY_W / 3):
            seg(x0, y, x1, y, 1, 120)
    else:
        for x in G.grid_between(x0, x1, G.BAY_W / 3):
            seg(x, y0, x, y1, 1, 120)
for x in G.grid_between(G.TAIL['x0'], G.TAIL['x1'], 0.8):
    seg(x, -G.TAIL['half'], x, G.TAIL['half'], 1, 120)
# 中堂の内部：須弥壇と天蓋
rect(-1.6, -2.4, 1.2, 2.4, 3, 200)
d.ellipse([*[v - 60 for v in P(-0.2, 0)], *[v + 60 for v in P(-0.2, 0)]], outline=200, width=3)
for x, y in (G.LANTERN_FRONT,):
    rect(x - 0.5, y - 0.5, x + 0.5, y + 0.5, 3)
    dot(x, y, 0.2)


# 西の森（上の縁）と、池の外の木立
def tree_mark(x, y, r):
    pts = []
    for a in np.linspace(0, 2 * math.pi, 18):
        rr = r * (1 + 0.16 * math.sin(a * 5 + x * 3))
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    poly(pts, 2, 160)
    for k in range(4):
        a = rnd.uniform(0, 6.28)
        seg(x, y, x + math.cos(a) * r * 0.55, y + math.sin(a) * r * 0.55, 1, 120)


for i in range(900):
    x, y = rnd.uniform(sc['x0'], sc['x1']), rnd.uniform(sc['y0'], sc['y1'])
    if G.point_in_poly(x, y, G.POND) or G.dist_to_poly(x, y, G.POND) < 2.0:
        continue
    if abs(y) < 3 and x > -27:
        continue
    if y > 26.5 and x < 8:
        continue
    tree_mark(x, y, rnd.uniform(1.3, 2.2))

# 文字
f_l = ImageFont.truetype(fonts.find('mincho'), 62, index=0)
f_m = ImageFont.truetype(fonts.find('mincho'), 90, index=0)
tf = ImageFont.truetype(fonts.find('title'), 225)


def vtext(txt, x, y, font, fill=235, spacing=1.08, draw=d):
    (u, v) = P(x, y)
    for i, ch in enumerate(txt):
        bb = draw.textbbox((0, 0), ch, font=font)
        draw.text((u - (bb[2] - bb[0]) / 2 - bb[0], v + i * font.size * spacing), ch, font=font, fill=fill)


def htext(txt, x, y, font, fill=230):
    (u, v) = P(x, y)
    bb = d.textbbox((0, 0), txt, font=font)
    d.text((u - (bb[2] - bb[0]) / 2, v - (bb[3] - bb[1]) / 2), txt, font=font, fill=fill)


htext('中堂', 4.6, 0, f_l)
htext('北翼廊', -4.4, 15.5, f_l)
htext('南翼廊', -4.4, -15.5, f_l)
htext('尾廊', -18, 3.4, f_l)
htext('隅楼', -4.9, 23.3, ImageFont.truetype(fonts.find('mincho'), 48))
htext('隅楼', -4.9, -23.3, ImageFont.truetype(fonts.find('mincho'), 48))
htext('洲浜', 14.8, 8, ImageFont.truetype(fonts.find('mincho'), 50))
htext('反橋', 5.6, 33.5, ImageFont.truetype(fonts.find('mincho'), 50))
htext('阿 字 池', 19, -24, f_m)
vtext('平等院鳳凰堂之圖', -31.6, 29.0, tf, 250, 1.0)
rd = ImageDraw.Draw(red)
for (x, y, s, txt) in [(12.4, 29.0, 3.6, '宇治'), (17.0, 29.0, 2.6, '鳳凰')]:
    (u0, v0) = P(x - s / 2, y - s / 2)
    (u1, v1) = P(x + s / 2, y + s / 2)
    rd.rectangle([u0, v0, u1, v1], fill=235)
    sf = ImageFont.truetype(fonts.find('title'), int(s * PX * 0.4))
    for i, ch in enumerate(txt):
        cu = (u0 + u1) / 2
        cv = v0 + (v1 - v0) * (0.28 + 0.44 * i)
        bb = rd.textbbox((0, 0), ch, font=sf)
        rd.text((cu - (bb[2] - bb[0]) / 2 - bb[0], cv - (bb[3] - bb[1]) / 2 - bb[1]), ch, font=sf, fill=25)
    rd.rectangle([u0, v0, u1, v1], outline=235, width=9)
# 方位
(u, v) = P(sc['x1'] - 4, sc['y0'] + 4)
d.ellipse([u - 70, v - 70, u + 70, v + 70], outline=220, width=4)
d.polygon([(u, v - 70), (u - 22, v + 30), (u + 22, v + 30)], fill=230)

arr = np.asarray(ink).astype(np.float32) / 255
blur = np.asarray(ink.filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32) / 255
# 墨のかすれ用のノイズ（種を固定して毎回同じ図にする）
_n = np.clip(np.random.default_rng(3).normal(128, 90, (H, W)), 0, 255).astype(np.uint8)
noise = np.asarray(Image.fromarray(_n).filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
arr = np.clip(np.maximum(arr * (0.8 + 0.3 * noise), blur * 0.3), 0, 1)
r_arr = np.clip(np.asarray(red.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255 * (0.8 + 0.3 * noise), 0, 1)
rgba = np.zeros((H, W, 4), np.float32)
ink_col = np.array([0.05, 0.045, 0.04])
red_col = np.array([0.74, 0.14, 0.08])
a_tot = np.clip(arr + r_arr, 0, 1)
col = (ink_col * arr[..., None] + red_col * r_arr[..., None]) / np.maximum(a_tot[..., None], 1e-4)
rgba[..., :3] = col
rgba[..., 3] = a_tot
Image.fromarray((rgba * 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'scroll_ink.png'))
paper = np.ones((H, W, 3), np.float32) * np.array([0.90, 0.86, 0.77])
prev = paper * (1 - a_tot[..., None]) + col * a_tot[..., None]
Image.fromarray((prev * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.LANCZOS).save(os.path.join(OUT, 'scroll_preview.jpg'))
print(W, H)
