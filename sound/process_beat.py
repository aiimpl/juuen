"""作り方の動画（finish/make_process.py）の音。120 BPM の和のビートを全部 Python で合成する（外部素材なし）。

1 小節＝2 秒＝48 コマ。小節の頭で映像が切り替わる。
  0 小節      10円玉を置く音と笙だけ（つかみ）
  1〜7 小節   太鼓（1・3 拍）、手拍子（2・4 拍）、鈴（8 分）、都節音階のベース。工程が変わる小節の頭で「チャリン」
  8 小節      締め：梵鐘と、りん

出力：build/audio/process_beat.wav（48kHz・16bit・ステレオ）
"""
import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
BARS = 9
DUR = BARS * BAR
N = int(SR * DUR)
rng = np.random.default_rng(21)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build', 'audio')


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='low', fs=SR, output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='high', fs=SR, output='sos'), x)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def place(buf, sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[:N - i0]
    buf[i0:i0 + len(sig), 0] += sig * gain * np.cos((pan + 1) * np.pi / 4)
    buf[i0:i0 + len(sig), 1] += sig * gain * np.sin((pan + 1) * np.pi / 4)


def env(n, a, r):
    e = np.ones(n)
    A, R = int(a * SR), int(r * SR)
    e[:A] = np.linspace(0, 1, A)
    e[-R:] *= np.linspace(1, 0, R)
    return e


# ---- 音の部品 ------------------------------------------------------------------------------------
def taiko(strength=1.0):
    """大太鼓：下がっていく低い音と、皮を打つ音"""
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 52 + 70 * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5)
    skin = lp(rng.standard_normal(n), 900) * np.exp(-t * 40)
    return (body + 0.5 * skin) * strength


def clap():
    """手拍子：少しずれた 3 回の破裂を重ねる"""
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for d in (0.0, 0.011, 0.023):
        i = int(d * SR)
        s[i:] += bp(rng.standard_normal(n - i), 900, 5200) * np.exp(-t[:n - i] * 55)
    return s


def suzu(accent):
    """鈴：高い金属の細かい鳴り"""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    s = hp(rng.standard_normal(n), 6500) * np.exp(-t * 60)
    for fr in (5200, 7400, 9100):
        s += 0.3 * np.sin(2 * np.pi * fr * t) * np.exp(-t * 45)
    return s * (1.0 if accent else 0.55)


def bass_note(m, dur):
    """ベース：のこぎり波を低域に絞り、はじくような立ち上がり"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi(m)
    saw = 2 * ((f * t) % 1.0) - 1
    s = lp(saw, 900) + 0.6 * np.sin(2 * np.pi * f * t)
    return s * env(n, 0.004, min(0.06, dur * 0.4)) * np.exp(-t * 3.0)


def clink(gain, bright=1.0, dur=1.2):
    """10円玉の打音（円板の振動の比でならぶ高い倍音）"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for ratio, a, dcy in ((1.0, 1.0, 9.0), (1.73, 0.7, 11.0), (2.33, 0.55, 14.0), (3.01, 0.4, 18.0), (3.87, 0.28, 24.0)):
        s += a * np.sin(2 * np.pi * 2350 * ratio * t + rng.uniform(0, 6.28)) * np.exp(-t * dcy / bright)
    s += 0.5 * hp(rng.standard_normal(n), 5000) * np.exp(-t * 400)
    return s * 0.5 * gain


def sho(notes, dur):
    """笙：合竹（和音）"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, m in enumerate(notes):
        f = midi(m) * (1 + rng.uniform(-0.0015, 0.0015))
        for h in range(1, 9):
            if f * h > 9000:
                break
            out += (1 / h ** 1.15) * (1.25 if h % 2 else 0.8) * np.sin(2 * np.pi * f * h * t + 0.7 * k * h)
    return out * env(n, 0.8, 1.2) / len(notes)


def bonsho(f=98, dur=5.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for ratio, a, dcy, beat in ((0.5, 0.6, 0.35, 0.9), (1.0, 1.0, 0.45, 1.7), (1.62, 0.6, 0.6, 2.3), (2.23, 0.5, 0.8, 1.1), (2.95, 0.35, 1.0, 2.9)):
        s += a * (np.sin(2 * np.pi * f * ratio * t) + 0.5 * np.sin(2 * np.pi * (f * ratio + beat) * t)) * np.exp(-t * dcy)
    s += 0.8 * lp(rng.standard_normal(n), 400) * np.exp(-t * 25)
    return s / 2


def rin(f=640, dur=3.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for ratio, a, dcy in ((1.0, 1.0, 0.9), (2.76, 0.55, 1.6), (5.40, 0.3, 2.6)):
        s += a * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * dcy)
    return s


# ---- 並べる --------------------------------------------------------------------------------------
mix = np.zeros((N, 2))
place(mix, clink(1.0), 0.02, 0.9, 0.1)
place(mix, clink(0.4, 0.6), 0.19, 0.9, 0.12)
E3 = 52
place(mix, sho([E3 + 12, E3 + 19, E3 + 24], BAR * 1.2), 0.3, 0.10)

# 都節音階（E・F・A・B・C）のベース。2 小節で一回り
bass_seq = [(E3 - 12, 1.0), (E3 - 12, 0.5), (E3 - 7, 0.5), (E3 - 11, 1.0), (E3 - 12, 1.0),
            (E3 - 8, 1.0), (E3 - 7, 0.5), (E3 - 5, 0.5), (E3 - 7, 1.0), (E3 - 11, 1.0)]
for bar in range(1, BARS - 1):
    t0 = bar * BAR
    for b in range(4):
        tb = t0 + b * BEAT
        if b in (0, 2):
            place(mix, taiko(1.0 if b == 0 else 0.75), tb, 0.55)
        else:
            place(mix, clap(), tb, 0.22, 0.05)
        for h in range(2):
            place(mix, suzu(h == 0), tb + h * BEAT / 2, 0.05, 0.35)
    if bar % 2 == 1:
        tb = t0
        for m, beats in bass_seq:
            place(mix, bass_note(m, beats * BEAT * 0.95), tb, 0.22)
            tb += beats * BEAT
    place(mix, clink(0.8), t0, 0.35, -0.2)                   # 工程が変わる合図
    place(mix, taiko(0.5), t0 + 3.5 * BEAT, 0.3)              # 小節の終わりに裏の打ち込み
    chord = [E3 + 12, E3 + 17, E3 + 19, E3 + 24] if bar % 2 else [E3 + 13, E3 + 17, E3 + 20, E3 + 24]
    place(mix, sho(chord, BAR + 0.4), t0, 0.07)

# 締め：梵鐘とりん
t_end = (BARS - 1) * BAR
place(mix, taiko(1.2), t_end, 0.6)
place(mix, bonsho(), t_end, 0.35)
place(mix, rin(), t_end + 0.5, 0.14, 0.15)

# 仕上げ：軽い残響・終わりのフェード・音量
rev = np.zeros_like(mix)
for d, a in ((0.029, 0.3), (0.043, 0.25), (0.067, 0.2), (0.109, 0.15), (0.167, 0.1)):
    k = int(d * SR)
    rev[k:, 0] += mix[:-k, 1] * a
    rev[k:, 1] += mix[:-k, 0] * a
mix = mix + lp(rev, 6000) * 0.35
fo = int(1.2 * SR)
mix[-fo:] *= (np.linspace(1, 0, fo) ** 1.5)[:, None]
mix = mix / np.abs(mix).max() * 0.89
os.makedirs(OUT, exist_ok=True)
out = os.path.join(OUT, 'process_beat.wav')
wavfile.write(out, SR, (mix * 32767).astype(np.int16))
print('wrote', out, f'{DUR:.1f}s')
