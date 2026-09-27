"""作り方の動画。120 BPM のビート（sound/process_beat.py）に合わせて、1 小節（2 秒＝48 コマ）ごとに工程を見せる。

実際に作った途中の絵（奥行き画像・高さの地図・10円玉・輪郭の重なり・立ち上がり）をそのまま使う。
小節の頭で切り替え、ズームのはね返りと白い光を入れる。字幕は左からすべり込む。

    python finish/make_process.py      → build/juuen_process.mp4（yuv420p・テレビ範囲）
    （先に make render と make video を済ませ、build/bld_frames_v1/b_0001.png がない場合は tools/shot.py で START のコマを描く）
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
W, H, FPS = 1920, 1080, 24
BEAT = 12
BAR = 48
BG = np.array([0.055, 0.047, 0.043], np.float32)
G = ImageFont.truetype(fonts.find('gothic'), 54)
G_SUB = ImageFont.truetype(fonts.find('gothic'), 32)
M_TITLE = ImageFont.truetype(fonts.find('mincho'), 112, index=2)
M_SUB = ImageFont.truetype(fonts.find('mincho'), 46, index=2)


def smooth(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


def load(path, size=(W, H)):
    im = Image.open(path)
    if im.mode == 'I;16' or im.mode == 'I':
        a = np.asarray(im).astype(np.float32) / 65535.0
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGB')
    im = im.convert('RGB')
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def zoom(img, s, cx=0.5, cy=0.5):
    """画面を s 倍に寄せて W×H で返す（cx, cy は寄せる中心の割合）。img は W×H より大きくてもよい"""
    h0, w0 = img.shape[:2]
    s = max(1.0, s)
    if abs(s - 1.0) < 1e-4 and (w0, h0) == (W, H):
        return img
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    cw, ch = w0 / s, h0 / s
    x0 = min(max(cx * w0 - cw / 2, 0), w0 - cw)
    y0 = min(max(cy * h0 - ch / 2, 0), h0 - ch)
    im = im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    return np.asarray(im).astype(np.float32) / 255.0


# ---- 途中の絵 -----------------------------------------------------------------------------------
def hillshade(scale=2):
    """10円玉の面の高さの地図を、左上から光を当てた陰影図に（技術資料ふうの青みがかった灰色）。
    寄っても粗くならないよう、画面の scale 倍の大きさで作る"""
    h = np.load(os.path.join(B, 'coin_face.npy')).astype(np.float32)
    px = 23.5 / h.shape[0]
    gy, gx = np.gradient(h, px)
    n = np.stack([-gx * 6, gy * 6, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array([-0.55, 0.55, 0.63])
    sh = np.clip(n @ (L / np.linalg.norm(L)), 0, 1) * 0.85 + 0.15 * (h / h.max())
    yy, xx = np.meshgrid(np.linspace(-1, 1, h.shape[0]), np.linspace(-1, 1, h.shape[0]), indexing='ij')
    inside = (np.hypot(xx, yy) <= 1.0)[..., None]
    col = np.stack([sh * 0.86, sh * 0.9, sh * 0.96], -1)
    side = H * scale
    col = np.asarray(Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).resize((side, side), Image.LANCZOS))
    inside = np.asarray(Image.fromarray(inside[..., 0].astype(np.uint8) * 255).resize((side, side), Image.LANCZOS))[..., None] / 255.0
    canvas = np.tile(BG, (H * scale, W * scale, 1))
    x0 = (W * scale - side) // 2
    canvas[:, x0:x0 + side] = canvas[:, x0:x0 + side] * (1 - inside) + col / 255.0 * inside
    return canvas


def depth_img():
    """奥行き画像。建物の中だけで明暗を広げ直して、近い・遠いが見えるように（近いほど白い）"""
    d = np.asarray(Image.open(os.path.join(B, 'relief_depth.png'))).astype(np.float32) / 65535.0
    m = d > 0.02
    lo, hi = np.percentile(d[m], 5), np.percentile(d[m], 99.5)          # 大半は狭い範囲に集まるので、下は 5% 点から
    v = np.where(m, 0.12 + 0.88 * np.clip((d - lo) / (hi - lo), 0, 1), 0.0)
    v = np.asarray(Image.fromarray((v * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)).astype(np.float32) / 255.0
    return v[..., None] * np.array([0.9, 0.95, 1.0], np.float32)


def caption(img, text, sub, t):
    """字幕：下の帯に、番号つきの見出しと小さな補足。t はすべり込みの進み（0〜1）"""
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    band = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle([0, H - 210, W, H], fill=(0, 0, 0, 150))
    band = band.filter(ImageFilter.GaussianBlur(22))
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    e = smooth(t)
    dx = (1 - e) * -120
    a = int(255 * e)
    d.text((110 + dx, H - 178), text, font=G, fill=(255, 250, 240, a))
    if sub:
        d.text((114 + dx, H - 104), sub, font=G_SUB, fill=(230, 214, 188, a))
    return np.asarray(Image.alpha_composite(Image.alpha_composite(im, band), layer).convert('RGB')).astype(np.float32) / 255.0


def title(img, t):
    """冒頭の題"""
    im = Image.fromarray((np.clip(img * (1 - 0.6 * smooth(t)), 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * smooth(t))
    for txt, font, y, col in (('10円玉の中の平等院', M_TITLE, H / 2 - 120, (255, 246, 228)),
                              ('ぜんぶコードで作った、その工程', M_SUB, H / 2 + 50, (236, 206, 170))):
        bb = d.textbbox((0, 0), txt, font=font)
        d.text(((W - (bb[2] - bb[0])) / 2, y), txt, font=font, fill=col + (a,))
    return np.asarray(Image.alpha_composite(im, layer).convert('RGB')).astype(np.float32) / 255.0


def seq(prefix, i0, i1, k, n):
    """コマ番号 i0〜i1 の連番を、n コマに縮めたときの k 番目"""
    i = int(round(i0 + (i1 - i0) * k / max(1, n - 1)))
    return load(os.path.join(B, prefix.format(i)))


# ---- 小節ごとの中身 --------------------------------------------------------------------------------
HS = hillshade()
DEPTH = depth_img()
START = load(os.path.join(B, 'bld_frames_v1', 'b_0001.png'))
ALIGN = load(os.path.join(ROOT, 'docs', 'align.png'))
COIN_END = load(os.path.join(B, 'coin_end', 'e_0060.png'))
COIN_CLOSE = load(os.path.join(B, 'coin_frames', 'c_0168.png'))
RELIEF0 = load(os.path.join(B, 'bld_relief', 'r_0001.png'))
# 高さの地図の中の位置（画面の割合）。coin/make_face.py の文字の角度・半径から：画面の高さ＝直径 23.5mm


def hs_pos(ang_deg, r_mm):
    a = np.radians(ang_deg)
    return 0.5 + r_mm * np.sin(a) / 23.5 * H / W, 0.5 - r_mm * np.cos(a) / 23.5


HS_POS = {'日': hs_pos(-47, 7.9), '本': hs_pos(0, 7.75), '国': hs_pos(47, 7.9), '唐草': hs_pos(25, 8.25)}

STEPS = [
    ('① 3Dモデルを正面から撮って、奥行きの画像に', '近いところほど白い。これが浮き彫りの元'),
    ('② 遠近を縮めて、細かい段差だけ強める', '柱・格子・屋根の段を残して、高さ0.24mmの浮き彫りに'),
    ('③ 文字は円周に1文字ずつ、唐草もコードで', '「日本国」「十円」は本物と同じ向きに回す'),
    ('④ 実寸（直径23.5mm）でBlenderへ', '色は本物の10円玉の写真から測って合わせた'),
    ('⑤ カメラを本物とそろえると、輪郭がぴったり重なる', '赤＝10円玉、緑＝本物の建物、黄色＝一致'),
    ('⑥ 視線に沿って押しつぶして、元の奥行きへ戻す', '10円玉の絵のまま、立体に立ち上がる'),
    ('⑦ 本物の鳳凰堂に溶かして、全景まで', '池も森も夕空も、全部コード'),
]


def frame(k):
    bar, f = divmod(k, BAR)
    beat = f // BEAT
    u = f / (BAR - 1)
    if bar == 0:                                    # つかみ：丸ごとの 10円玉 → 題
        img = zoom(COIN_END, 1.0 + 0.04 * u)
        if f >= 2 * BEAT:
            img = title(img, (f - 2 * BEAT) / 8)
        return img, None
    if bar == 8:                                    # 締め
        img = zoom(COIN_END, 1.04 - 0.04 * smooth(u))
        return img, ('全部コードです', 'github.com/aiimpl/juuen')
    step = STEPS[bar - 1]
    if bar == 1:                                    # 本物を正面から → 上から下へ走査して奥行きへ
        s = smooth((f - 10) / 26)
        line = int(H * s)
        img = START.copy()
        img[:line] = DEPTH[:line]
        if 0 < line < H:
            img[max(0, line - 3):line + 3] = [0.6, 0.85, 1.0]
    elif bar == 2:                                  # 奥行き → 浮き彫り（寄り）→ 10円玉の面の全体
        if beat == 0:
            img = DEPTH
        elif beat == 1:
            img = zoom(HS, 1.9, 0.5, 0.47)
        else:
            img = zoom(HS, 1.9 - 0.9 * smooth((f - 2 * BEAT) / 18), 0.5, 0.47)
    elif bar == 3:                                  # 拍ごとに 日・本・国・唐草 へ寄る
        key = ['日', '本', '国', '唐草'][beat]
        cx, cy = HS_POS[key]
        img = zoom(HS, 3.2 - 0.25 * ((f % BEAT) / BEAT), cx, cy)
    elif bar == 4:                                  # 10円玉のショットを早回し
        img = seq('coin_frames/c_{:04d}.png', 1, 168, f, BAR)
    elif bar == 5:                                  # 拍ごとに 10円玉 ↔ 本物 → 輪郭の重なり
        img = [COIN_CLOSE, START, COIN_CLOSE, ALIGN][beat]
    elif bar == 6:                                  # 立ち上がりを早回し
        img = seq('bld_relief/r_{:04d}.png', 1, 104, f, BAR)
    else:                                           # 本物へ溶けて全景まで（本編の 225〜365 コマ）
        img = seq('final_frames/j_{:04d}.png', 225, 360, f, BAR)
    return img, step


def punch(img, f):
    """小節の頭：ズームのはね返りと白い光"""
    s = 1.0 + 0.06 * (1 - smooth(f / 8))
    img = zoom(img, s)
    flash = 0.28 * (1 - smooth(f / 4))
    return img + (1 - img) * flash


out_dir = os.path.join(B, 'process_frames')
os.makedirs(out_dir, exist_ok=True)
for name in os.listdir(out_dir):
    os.remove(os.path.join(out_dir, name))
TOTAL = 9 * BAR
for k in range(TOTAL):
    bar, f = divmod(k, BAR)
    img, cap = frame(k)
    if bar > 0:
        img = punch(img, f)
    if bar == 5 and f % BEAT == 0 and f > 0:       # 拍の切り替えにも小さな光
        img = img + (1 - img) * 0.12
    if cap:
        img = caption(img, cap[0], cap[1], (f - 2) / 6)
    if bar == 8:
        img = img * (1 - smooth((f - (BAR - 14)) / 14))
    if k < 6:
        img = img * smooth(k / 6)
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(out_dir, f'p_{k:04d}.png'))

mp4 = os.path.join(B, 'juuen_process.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(out_dir, 'p_%04d.png'),
                '-i', os.path.join(B, 'audio', 'process_beat.wav'),
                '-vf', 'scale=in_range=pc:out_range=tv,format=yuv420p', '-pix_fmt', 'yuv420p', '-color_range', 'tv',
                '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                '-bsf:v', 'h264_metadata=video_full_range_flag=0',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-profile:v', 'high', '-movflags', '+faststart',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', mp4], check=True)
print('wrote', mp4)
