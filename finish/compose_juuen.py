"""10円玉・銅の浮き彫り・本物の鳳凰堂・締めの 10円玉をつないで、投稿用の mp4 にする。

1〜149 コマ        10円玉に寄る（build/coin_frames）
150〜168 コマ      10円玉の浮き彫りと、銅の浮き彫りの版（build/bld_relief）が重なる。位置はぴったり同じ
169〜224 コマ      銅の浮き彫りが立体に立ち上がる
225〜253 コマ      銅の版が本物の鳳凰堂（build/bld_frames）に溶ける。本物は銅の色から本来の色へ
254〜365 コマ      全景まで引く。最後の 10 コマで暗転
366〜449 コマ      締め：10円玉を真上から丸ごと（build/coin_end）と、縦書きの題

    python finish/compose_juuen.py      → build/juuen.mp4（yuv420p・テレビ範囲）
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fonts  # noqa: E402

B = os.path.join(ROOT, 'build')
FPS = 24
COIN_CUT = 149          # sound/juuen_audio.py と同じ
MELT = 19               # 10円玉 → 銅の版
REAL_START, RELIEF_END = 76, 104    # tools/building_shot.py と同じ
TINT_LEN = 50
COIN_LEN, BLD_LEN, END_LEN = 168, 216, 84
DIP = 10                # 締めの前後の暗転
TITLE = ['10', '円', '玉', 'の', '中', 'の', '平', '等', '院']
COPPER = np.array([1.0, 0.64, 0.40])


def smooth(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


def load(path):
    return np.asarray(Image.open(path).convert('RGB')).astype(np.float32) / 255.0


def copper(img):
    """明るさだけ残して銅の色に染める"""
    y = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    return np.clip(y[..., None] * COPPER * 1.1, 0, 1)


def title_layer():
    """右寄りに縦書きの題。「10」は縦中横（1 マスに横並び）。白い文字と、柔らかい影"""
    W, H = 1920, 1080
    size = 62
    f = ImageFont.truetype(fonts.find('mincho'), size, index=2)
    f_num = ImageFont.truetype(fonts.find('mincho'), int(size * 0.78), index=2)
    txt = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(txt)
    step = size * 1.18
    x_c = 1480
    y = H / 2 - step * len(TITLE) / 2
    for ch in TITLE:
        font = f_num if ch.isdigit() else f
        bb = d.textbbox((0, 0), ch, font=font)
        d.text((x_c - (bb[0] + bb[2]) / 2, y + step / 2 - (bb[1] + bb[3]) / 2), ch, font=font, fill=255)
        y += step
    a = np.asarray(txt).astype(np.float32) / 255.0
    shadow = np.asarray(txt.filter(ImageFilter.GaussianBlur(9))).astype(np.float32) / 255.0
    return a, shadow


frames = []
for k in range(1, COIN_CUT + BLD_LEN + END_LEN + 1):
    frames.append(k)

need = [os.path.join(B, 'coin_frames', f'c_{c:04d}.png') for c in range(1, COIN_LEN + 1)]
need += [os.path.join(B, 'bld_relief', f'r_{b:04d}.png') for b in range(1, RELIEF_END + 1)]
need += [os.path.join(B, 'bld_frames', f'b_{b:04d}.png') for b in range(REAL_START, BLD_LEN + 1)]
need += [os.path.join(B, 'coin_end', f'e_{e:04d}.png') for e in range(1, END_LEN + 1)]
missing = [p for p in need if not os.path.exists(p)]
if missing:
    sys.exit(f'コマが足りない：{len(missing)} 枚（例：{missing[0]}）')

t_a, t_sh = title_layer()
out_dir = os.path.join(B, 'final_frames')
os.makedirs(out_dir, exist_ok=True)
for name in os.listdir(out_dir):
    os.remove(os.path.join(out_dir, name))
for k in frames:
    b = k - COIN_CUT
    e = b - BLD_LEN
    if b < 1:
        img = load(os.path.join(B, 'coin_frames', f'c_{k:04d}.png'))
    elif e >= 1:
        img = load(os.path.join(B, 'coin_end', f'e_{e:04d}.png'))
        ta = smooth((e - 22) / 22) * (1 - smooth((e - (END_LEN - 14)) / 12))
        img = img * (1 - 0.55 * ta * t_sh[..., None]) + ta * t_a[..., None] * (np.array([0.97, 0.94, 0.89]) - img)
        img = img * smooth(e / DIP) * (1 - smooth((e - (END_LEN - DIP)) / DIP))
    else:
        if b <= RELIEF_END:
            rel = load(os.path.join(B, 'bld_relief', f'r_{b:04d}.png'))
        if b >= REAL_START:
            real = load(os.path.join(B, 'bld_frames', f'b_{b:04d}.png'))
            tint = 1.0 - smooth((b - REAL_START) / TINT_LEN)
            real = real * (1 - tint) + copper(real) * tint
        if b < REAL_START:
            img = rel
        elif b > RELIEF_END:
            img = real
        else:
            a = smooth((b - REAL_START) / (RELIEF_END - REAL_START))
            img = rel * (1 - a) + real * a
        if k <= COIN_LEN:
            a = smooth(b / MELT)
            img = load(os.path.join(B, 'coin_frames', f'c_{k:04d}.png')) * (1 - a) + img * a
        img = img * (1 - smooth((b - (BLD_LEN - DIP)) / DIP))
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(out_dir, f'j_{k:04d}.png'))

mp4 = os.path.join(B, 'juuen.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(out_dir, 'j_%04d.png'),
                '-i', os.path.join(B, 'audio', 'juuen_mix.wav'),
                '-vf', 'scale=in_range=pc:out_range=tv,format=yuv420p', '-pix_fmt', 'yuv420p', '-color_range', 'tv',
                '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                '-bsf:v', 'h264_metadata=video_full_range_flag=0',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-profile:v', 'high', '-movflags', '+faststart',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', mp4], check=True)
print('wrote', mp4)
