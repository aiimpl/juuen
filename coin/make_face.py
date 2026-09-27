"""10円玉の表面の高さ（mm）を、1 枚の高さの地図にまとめて計算する。

- 直径 23.5mm。外周に盛り上がった縁
- 中央：鳳凰堂の浮き彫り。build/relief_depth.png（モデルから描いた奥行き）を、建物の中だけで明暗を広げ直し、
  浅い浮き彫り（最大 0.24mm）にする
- 縁に沿って上に「日本国」、下に「十円」（高さ 0.13mm）。文字のあいだを唐草でつなぐ（高さ 0.085mm）

出力：build/coin_face.npy（N×N の高さ mm）と、確認用の build/coin_face.png
"""
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fonts  # noqa: E402
from coin.spec import R_COIN, RECT_W, RECT_H, RECT_CY  # noqa: E402

N = 2048                      # 高さの地図の解像度（面の 23.5mm 四方）
RIM_IN, RIM_H = 10.85, 0.20   # 縁の内側の半径と高さ
RELIEF_H = 0.24
TEXT_H = 0.13
VINE_H = 0.085

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
relief = gaussian_filter(relief, 1.5)             # 画素より細い線はカメラが動くとちらつくので、少しだけなめらかに
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

# ---- 文字：縁に沿って、上に「日本国」、下に「十円」----
# 本物と同じく 1 文字ずつ円周に置いて回す。上の文字は頭を外へ、下の文字は頭を中心へ向ける
def char_layer(ch, ang_deg, r_mm, size_mm, head_out):
    f = ImageFont.truetype(fonts.find('mincho'), int(size_mm * px_per_mm), index=2)   # ヒラギノ明朝 W6
    S = int(size_mm * px_per_mm * 1.6)
    img = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), ch, font=f)
    d.text((S / 2 - (bb[0] + bb[2]) / 2, S / 2 - (bb[1] + bb[3]) / 2), ch, font=f, fill=255)
    rot = -ang_deg if head_out else 180 - ang_deg
    img = img.rotate(rot, resample=Image.BICUBIC)
    out = Image.new('L', (N, N), 0)
    a = np.radians(ang_deg)
    cx, cy = N / 2 + r_mm * np.sin(a) * px_per_mm, N / 2 - r_mm * np.cos(a) * px_per_mm
    out.paste(img, (int(cx - S / 2), int(cy - S / 2)))
    return out


txt = Image.new('L', (N, N), 0)
for ch, ang, r, size, head_out in (('日', -47, 7.9, 3.0, True), ('本', 0, 7.75, 3.0, True), ('国', 47, 7.9, 3.0, True),
                                   ('十', -150, 7.35, 3.3, False), ('円', 150, 7.35, 3.3, False)):
    txt = ImageChops.lighter(txt, char_layer(ch, ang, r, size, head_out))
txt = txt.filter(ImageFilter.MaxFilter(7))                 # 本物の文字は太いので、線を 0.07mm ずつ太らせる
a_txt = np.asarray(txt.filter(ImageFilter.GaussianBlur(1.3))).astype(np.float64) / 255.0
text = smooth(0.15, 0.85, a_txt) * TEXT_H


# ---- 唐草：文字のあいだを円周に沿ってつなぐ蔓。波打つ茎・山ごとの巻きひげ・小さな葉 ----
def karakusa(a0, a1, r_mm, amp_mm, waves, seed):
    rng = np.random.default_rng(seed)
    img = Image.new('L', (N, N), 0)
    d = ImageDraw.Draw(img)
    w = max(2, int(0.26 * px_per_mm))

    def P(ang_deg, rr):
        a = np.radians(ang_deg)
        return (N / 2 + rr * np.sin(a) * px_per_mm, N / 2 - rr * np.cos(a) * px_per_mm)

    ts = np.linspace(0, 1, 400)
    angs = a0 + (a1 - a0) * ts
    rs = r_mm + amp_mm * np.sin(2 * np.pi * waves * ts)
    d.line([P(a, rr) for a, rr in zip(angs, rs)], fill=255, width=w, joint='curve')
    for k in range(int(waves * 2)):
        t = (k + 0.5) / (waves * 2)
        ang = a0 + (a1 - a0) * t
        side = 1 if k % 2 == 0 else -1                      # 山は外へ、谷は内へ巻く
        base_r = r_mm + side * amp_mm
        # 巻きひげ：茎から外（内）へ出て、だんだん小さく 1.4 回巻く
        R0 = 0.42 + rng.uniform(-0.06, 0.06)
        th = np.linspace(0, 2 * np.pi * 1.4, 160)
        rad = R0 * (1 - th / th[-1] * 0.85)
        cx_r = base_r + side * R0
        dirn = 1 if (a1 - a0) > 0 else -1
        pts = []
        for tt, rr in zip(th, rad):
            dx = rr * np.sin(tt) * dirn * side                # 円周方向（mm）
            dr = -side * rr * np.cos(tt)                      # 半径方向（mm）
            pts.append(P(ang + np.degrees(dx / cx_r), cx_r + dr))
        d.line(pts, fill=255, width=max(2, int(w * 0.8)), joint='curve')
        # 葉：巻きひげの根もとに、茎に沿った細い葉を 2 枚
        for s_ in (-1, 1):
            la = ang + s_ * np.degrees(0.55 / r_mm)
            lr = r_mm + side * amp_mm * 0.5
            L = 0.75
            leaf = [P(la + np.degrees(L * u * s_ / lr), lr - side * 0.45 * np.sin(np.pi * u) ** 0.8 * v)
                    for u in np.linspace(0, 1, 20) for v in (1,)]
            leaf += [P(la + np.degrees(L * u * s_ / lr), lr - side * 0.05 * np.sin(np.pi * u))
                     for u in np.linspace(1, 0, 20)]
            d.polygon(leaf, fill=255)
    return img


vine = Image.new('L', (N, N), 0)
for (a0, a1, r, amp, waves), seed in zip(((-40, -9, 8.25, 0.34, 2.5), (9, 40, 8.25, 0.34, 2.5),
                                           (-82, -57, 8.1, 0.32, 1.5), (57, 82, 8.1, 0.32, 1.5),
                                           (-138, -110, 7.7, 0.32, 1.5), (110, 138, 7.7, 0.32, 1.5),
                                           (-164, -196, 7.55, 0.34, 2.5)), range(7)):
    vine = ImageChops.lighter(vine, karakusa(a0, a1, r, amp, waves, seed))
a_vine = np.asarray(vine.filter(ImageFilter.GaussianBlur(1.1))).astype(np.float64) / 255.0
text = np.maximum(text, smooth(0.15, 0.85, a_vine) * VINE_H)

face = np.maximum(np.maximum(rim, relief), text)
face[Rr > R_COIN] = 0.0
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
np.save(os.path.join(ROOT, 'build', 'coin_face.npy'), face.astype(np.float32))
# くぼみの汚れ：盛り上がりのすぐ脇の低いところほど 1 に近い（本物の 10円玉で、浮き彫りや文字の縁が黒く見えるところ）
cav = np.clip((gaussian_filter(face, 5.0) - face) / 0.03, 0, 1) ** 0.8
cav = np.maximum(cav, 0.6 * np.clip((gaussian_filter(face, 16.0) - face) / 0.03, 0, 1))
np.save(os.path.join(ROOT, 'build', 'coin_cav.npy'), cav.astype(np.float32))
prev = (face / face.max() * 255).astype(np.uint8)
Image.fromarray(prev).resize((1024, 1024), Image.LANCZOS).save(os.path.join(ROOT, 'build', 'coin_face.png'))
print('face', face.shape, 'max %.3f mm' % face.max(), 'rect', RECT_W, RECT_H, 'center y', RECT_CY)
