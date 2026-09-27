"""10円玉の表面の高さ（mm）を、1 枚の高さの地図にまとめて計算する。

- 直径 23.5mm。外周に盛り上がった縁
- 中央：鳳凰堂の浮き彫り。build/relief_depth.png（モデルから描いた奥行き）を、建物の中だけで明暗を広げ直し、
  浅い浮き彫り（最大 0.24mm）にする
- 上に「日本国」、下に「十円」の文字（高さ 0.13mm、縁はなだらか）

出力：build/coin_face.npy（N×N の高さ mm）と、確認用の build/coin_face.png
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fonts  # noqa: E402

N = 2048                      # 高さの地図の解像度（面の 23.5mm 四方）
R_COIN = 11.75                # 半径 mm
RIM_IN, RIM_H = 10.85, 0.20   # 縁の内側の半径と高さ
RELIEF_H = 0.24
TEXT_H = 0.13
# 浮き彫りを置く矩形（奥行き画像の全体をここへ写す）。動画でつなぐカメラもこの矩形を画面いっぱいに撮る
RECT_W = 19.0
RECT_H = RECT_W * 9 / 16
RECT_CY = 0.35                # 少し上に寄せる

mm = np.linspace(-R_COIN, R_COIN, N)
X, Y = np.meshgrid(mm, -mm)   # 画像の上が +y
Rr = np.hypot(X, Y)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ---- 縁：内側はなだらかに立ち上がり、外側は面取り ----
rim = RIM_H * smooth(RIM_IN - 0.25, RIM_IN + 0.1, Rr) * (1 - 0.35 * smooth(R_COIN - 0.18, R_COIN, Rr))

# ---- 浮き彫り：鳳凰堂 ----
dep = np.asarray(Image.open(os.path.join(ROOT, 'build', 'relief_depth.png'))).astype(np.float64) / 65535.0
H0, W0 = dep.shape
mask = dep > 0.02
# 右端に入る反橋は浮き彫りに入れない
mask[:, int(W0 * 0.965):] = False
vals = dep[mask]
lo, hi = np.percentile(vals, 1), np.percentile(vals, 99.5)
dn = np.clip((dep - lo) / (hi - lo), 0, 1)
# 浅い浮き彫り：建物の地の高さ＋奥行きの差（近い所ほど高い）。遠近差は圧縮する
# 浮き彫りの定番：大きな遠近は圧縮し、細かな段差（柱・格子・屋根の段）を強調する
dm = np.where(mask, dn, 0.0)
w = gaussian_filter(mask.astype(np.float64), 10) + 1e-6
local = gaussian_filter(dm, 10) / w
detail = np.clip((dn - local) * 3.2, -0.35, 0.35)
h = np.where(mask, np.clip(0.5 + 0.28 * dn + detail, 0.08, 1.0), 0.0)
# 矩形 → 面の高さの地図の画素へ
px_per_mm = (N - 1) / (2 * R_COIN)
rw, rh = int(RECT_W * px_per_mm), int(RECT_H * px_per_mm)
hr = np.asarray(Image.fromarray(h.astype(np.float32), mode='F').resize((rw, rh), Image.LANCZOS))
relief = np.zeros((N, N))
cx = N // 2
cy = int(N / 2 - RECT_CY * px_per_mm)
y0, x0 = cy - rh // 2, cx - rw // 2
relief[y0:y0 + rh, x0:x0 + rw] = np.clip(hr, 0, 1)
# 縁をなだらかに（打刻の斜面）
relief = gaussian_filter(relief, 1.1)
relief *= RELIEF_H
# 地面の線：建物の足元に、横に長い台（池のほとりの基壇）
base_y = None
rows = np.where(relief.max(axis=1) > 0.02)[0]
if len(rows):
    base_y = rows.max()
    band = np.zeros((N, N))
    by = base_y + int(0.12 * px_per_mm)
    band[by:by + int(0.32 * px_per_mm), :] = 1.0
    band *= (np.abs(X) < 9.2)
    band = gaussian_filter(band, 2.0)
    relief = np.maximum(relief, band * RELIEF_H * 0.45)

# ---- 文字：上に「日本国」、下に「十円」----
def text_layer(txt, cy_mm, size_mm, track_mm):
    img = Image.new('L', (N, N), 0)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(fonts.find('mincho'), int(size_mm * px_per_mm), index=2)   # ヒラギノ明朝 W6
    ws = [d.textbbox((0, 0), ch, font=f)[2] - d.textbbox((0, 0), ch, font=f)[0] for ch in txt]
    tw = sum(ws) + track_mm * px_per_mm * (len(txt) - 1)
    x = N / 2 - tw / 2
    for ch, w in zip(txt, ws):
        bb = d.textbbox((0, 0), ch, font=f)
        d.text((x - bb[0], N / 2 - cy_mm * px_per_mm - (bb[3] + bb[1]) / 2), ch, font=f, fill=255)
        x += w + track_mm * px_per_mm
    a = np.asarray(img.filter(ImageFilter.GaussianBlur(1.3))).astype(np.float64) / 255.0
    return smooth(0.15, 0.85, a) * TEXT_H


text = np.maximum(text_layer('日本国', 7.2, 2.15, 0.55), text_layer('十円', -7.55, 2.9, 1.1))

face = np.maximum(np.maximum(rim, relief), text)
face[Rr > R_COIN] = 0.0
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
np.save(os.path.join(ROOT, 'build', 'coin_face.npy'), face.astype(np.float32))
prev = (face / face.max() * 255).astype(np.uint8)
Image.fromarray(prev).resize((1024, 1024), Image.LANCZOS).save(os.path.join(ROOT, 'build', 'coin_face.png'))
print('face', face.shape, 'max %.3f mm' % face.max(), 'rect', RECT_W, RECT_H, 'center y', RECT_CY)
