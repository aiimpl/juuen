"""10円玉と本物の鳳凰堂のコマをつないで、投稿用の mp4 にする。

1〜149 コマ     10円玉（build/coin_frames）
150〜168 コマ   浮き彫りと本物が重なって溶ける（どちらも止まっている。位置はぴったり同じ）
169 コマ〜      本物の鳳凰堂（build/bld_frames）。最初は銅の色が残り、40 コマかけて本来の色に戻る

    python finish/compose_juuen.py      → build/juuen.mp4（yuv420p・テレビ範囲）
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, 'build')
COIN_CUT = 149          # sound/juuen_audio.py と同じ
MELT = 19
TINT_LEN = 40
COIN_LEN, BLD_LEN = 168, 216
COPPER = np.array([1.0, 0.62, 0.42])


def smooth(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


def load(path):
    return np.asarray(Image.open(path).convert('RGB')).astype(np.float32) / 255.0


def copper(img):
    """明るさだけ残して銅の色に染める（10円玉の面の色味）"""
    y = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    return np.clip(y[..., None] * COPPER * 1.1, 0, 1)


frames = []
for k in range(1, COIN_CUT + BLD_LEN + 1):
    b_i = k - COIN_CUT
    frames.append((k, k if k <= COIN_LEN else None, b_i if b_i >= 1 else None))

missing = [p for p in (os.path.join(B, 'coin_frames', f'c_{c:04d}.png') for _, c, _ in frames if c) if not os.path.exists(p)]
missing += [p for p in (os.path.join(B, 'bld_frames', f'b_{b:04d}.png') for _, _, b in frames if b) if not os.path.exists(p)]
if missing:
    sys.exit(f'コマが足りない：{len(missing)} 枚（例：{missing[0]}）')

out_dir = os.path.join(B, 'final_frames')
os.makedirs(out_dir, exist_ok=True)
for k, c, b in frames:
    if b is None:
        img = load(os.path.join(B, 'coin_frames', f'c_{c:04d}.png'))
    else:
        bld = load(os.path.join(B, 'bld_frames', f'b_{b:04d}.png'))
        tint = 1.0 - smooth((b - MELT * 0.5) / TINT_LEN)
        bld = bld * (1 - tint) + copper(bld) * tint
        if c is not None:
            a = smooth(b / MELT)
            img = load(os.path.join(B, 'coin_frames', f'c_{c:04d}.png')) * (1 - a) + bld * a
        else:
            img = bld
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(out_dir, f'j_{k:04d}.png'))

mp4 = os.path.join(B, 'juuen.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '24', '-i', os.path.join(out_dir, 'j_%04d.png'),
                '-i', os.path.join(B, 'audio', 'juuen_mix.wav'),
                '-vf', 'scale=in_range=pc:out_range=tv,format=yuv420p', '-pix_fmt', 'yuv420p', '-color_range', 'tv',
                '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                '-bsf:v', 'h264_metadata=video_full_range_flag=0',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-profile:v', 'high', '-movflags', '+faststart',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', mp4], check=True)
print('wrote', mp4)
