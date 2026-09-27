"""「10円玉の中の平等院」の音を全部 Python で合成する（外部素材なし）。

0.0 秒   10円玉を机に置く音（チャリン、小さな跳ね）
0.4 秒〜 部屋の静けさ・笙の和音がゆっくりふくらむ
6.2 秒   浮き彫りが立体に立ち上がり、本物の鳳凰堂になって全景まで引く：梵鐘、笙が開く、池の水音と秋の虫
15.2 秒  締め：手元の 10円玉に戻って、りん
18.7 秒  終わり

出力：build/audio/juuen_mix.wav（48kHz・16bit・ステレオ）
"""
import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
FPS = 24
COIN_CUT = 149                  # 10円玉の 149 コマのあとに鳳凰堂が始まる（compose.sh と同じ）
BLD_LEN = 216
END_LEN = 84                    # 締めの 10円玉（finish/compose_juuen.py と同じ）
DUR = (COIN_CUT + BLD_LEN + END_LEN) / FPS
N = int(SR * DUR)
T_MELT = COIN_CUT / FPS
T_END = (COIN_CUT + BLD_LEN) / FPS  # 締めのカット
rng = np.random.default_rng(11)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build', 'audio')


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='low', fs=SR, output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='high', fs=SR, output='sos'), x)


def place(buf, sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[:N - i0]
    buf[i0:i0 + len(sig), 0] += sig * gain * np.cos((pan + 1) * np.pi / 4)
    buf[i0:i0 + len(sig), 1] += sig * gain * np.sin((pan + 1) * np.pi / 4)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


mix = np.zeros((N, 2))


# ---- 10円玉：青銅の小さな円板の打音（円板の振動の比でならぶ高い倍音）と、机の木の音 --------------
def clink(gain, bright=1.0, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for ratio, a, dcy in ((1.0, 1.0, 9.0), (1.73, 0.7, 11.0), (2.33, 0.55, 14.0), (3.01, 0.4, 18.0),
                          (3.87, 0.28, 24.0), (4.93, 0.18, 30.0)):
        f = 2350 * ratio * (1 + rng.uniform(-0.004, 0.004))
        s += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t * dcy / bright)
    s += 0.5 * hp(rng.standard_normal(n), 5000) * np.exp(-t * 400)
    wood = lp(rng.standard_normal(n), 900) * np.exp(-t * 60) + 0.6 * np.sin(2 * np.pi * 180 * t) * np.exp(-t * 45)
    return (s * 0.5 + wood * 0.5) * gain


place(mix, clink(0.55), 0.02, 1.0, 0.1)
place(mix, clink(0.35, 0.6), 0.19, 1.0, 0.12)        # 小さく跳ねて
place(mix, clink(0.14, 0.4), 0.29, 1.0, 0.12)        # 落ち着く
# 細かいびびり（縁が机の上で震えて止まる）
n = int(0.5 * SR)
t = np.arange(n) / SR
rattle = np.zeros(n)
for k in range(9):
    tk = 0.33 + 0.028 * k * (1 + 0.15 * k)
    i0 = int((tk - 0.33) * SR)
    m = int(0.03 * SR)
    if i0 + m < n:
        tt = np.arange(m) / SR
        rattle[i0:i0 + m] += np.sin(2 * np.pi * 2350 * 1.73 * tt) * np.exp(-tt * 160) * 0.12 * 0.8 ** k
place(mix, rattle, 0.33, 1.0, 0.12)

# ---- 部屋の静けさ（ごく小さな低いざわめき）----------------------------------------------------
room = lp(rng.standard_normal(N), 250) * 0.012
room = np.stack([room, np.roll(room, 911)], 1)
room *= np.clip(np.arange(N) / SR / 0.8, 0, 1)[:, None] * np.clip((T_MELT + 1.0 - np.arange(N) / SR) / 1.0, 0, 1)[:, None]
mix += room


# ---- 笙：合竹を息の強弱でふくらませる ----------------------------------------------------------
def sho_chord(notes, dur, att=1.2, rel=1.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, m in enumerate(notes):
        f = midi(m) * (1 + rng.uniform(-0.0015, 0.0015))
        ph = rng.uniform(0, 6.28)
        for h in range(1, 10):
            if f * h > 9000:
                break
            amp = (1 / h ** 1.15) * (1.25 if h % 2 == 1 else 0.8)
            out += amp * np.sin(2 * np.pi * f * h * t + ph * h) * (1 + 0.03 * np.sin(2 * np.pi * (0.3 + 0.1 * k) * t))
    env = np.ones(n)
    a, r = int(att * SR), int(rel * SR)
    env[:a] = np.linspace(0, 1, a) ** 2
    env[-r:] *= np.linspace(1, 0, r)
    out += 0.02 * bp(rng.standard_normal(n), 800, 4000)
    return out * env / len(notes)


E4 = 64
place(mix, sho_chord([E4, E4 + 7, E4 + 12], T_MELT + 0.6, att=2.6, rel=0.8), 0.5, 0.13)                 # 寄るあいだ、細く
place(mix, sho_chord([E4 - 5, E4, E4 + 2, E4 + 7, E4 + 12, E4 + 14], DUR - T_MELT + 0.2, att=1.6, rel=3.0), T_MELT - 0.3, 0.15)


# ---- 梵鐘：本物の鳳凰堂に溶けるところ -----------------------------------------------------------
def bonsho(f=98, dur=9.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for ratio, a, dcy, beat in ((0.5, 0.6, 0.25, 0.9), (1.0, 1.0, 0.35, 1.7), (1.62, 0.6, 0.5, 2.3), (2.23, 0.5, 0.7, 1.1),
                                (2.95, 0.35, 0.9, 2.9), (4.1, 0.2, 1.4, 3.4), (5.4, 0.12, 2.0, 1.3)):
        fr = f * ratio
        s += a * (np.sin(2 * np.pi * fr * t) + 0.5 * np.sin(2 * np.pi * (fr + beat) * t)) * np.exp(-t * dcy)
    s += 0.8 * lp(rng.standard_normal(n), 400) * np.exp(-t * 25)
    return s / 2


place(mix, bonsho(), T_MELT, 0.34, 0.0)

# ---- 池の水と秋の虫（鳳凰堂のショットのあいだ）----------------------------------------------------
n = N - int(T_MELT * SR)
t = np.arange(n) / SR
wash = hp(lp(rng.standard_normal(n), 600), 60) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.22 * t) ** 2)
lap = np.zeros(n)
for k in range(int(n / SR * 2.5)):
    i0 = int(rng.uniform(0, n / SR) * SR)
    m = int(0.18 * SR)
    if i0 + m < n:
        tt = np.arange(m) / SR
        lap[i0:i0 + m] += np.sin(2 * np.pi * rng.uniform(300, 900) * tt * (1 + 2.5 * tt)) * np.exp(-tt * 28) * rng.uniform(0.3, 1)
water = (wash * 0.9 + bp(lap, 200, 3000) * 0.35) * np.clip(t / 2.5, 0, 1)
water *= np.clip((T_END + 0.2 - (T_MELT + t)) / 0.8, 0, 1)
place(mix, water, T_MELT, 0.12, -0.1)
car = np.sin(2 * np.pi * 4300 * t) * (np.sin(2 * np.pi * 42 * t) > 0)
ph = (t % 1.4) / 1.4
suzu = car * np.where(ph < 0.45, np.sin(np.pi * ph / 0.45), 0) * np.clip((t - 1.5) / 2.0, 0, 1)
suzu *= np.clip((T_END + 0.2 - (T_MELT + t)) / 0.8, 0, 1)
place(mix, suzu, T_MELT, 0.012, 0.5)

# ---- 締め：手元の 10円玉に戻ったところで、澄んだりんを 1 つ ---------------------------------------------
def rin(f=640, dur=4.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for ratio, a, dcy in ((1.0, 1.0, 0.7), (2.76, 0.55, 1.4), (5.40, 0.3, 2.4), (8.93, 0.15, 3.5)):
        s += a * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * dcy) * (1 + 0.15 * np.sin(2 * np.pi * 3.1 * ratio * t))
    s += 0.3 * hp(rng.standard_normal(n), 4000) * np.exp(-t * 80)
    return s


place(mix, rin(), T_END + 0.3, 0.16, 0.15)

# ---- 仕上げ：軽い残響・終わりのフェード・音量 ---------------------------------------------------------
rev = np.zeros_like(mix)
for d, a in ((0.031, 0.35), (0.047, 0.3), (0.071, 0.25), (0.113, 0.2), (0.173, 0.15), (0.257, 0.1), (0.371, 0.07)):
    k = int(d * SR)
    rev[k:, 0] += mix[:-k, 1] * a
    rev[k:, 1] += mix[:-k, 0] * a
mix = mix + lp(rev, 5000) * 0.45
fo = int(2.4 * SR)
mix[-fo:] *= (np.linspace(1, 0, fo) ** 1.5)[:, None]
peak = np.abs(mix).max()
mix = mix / peak * 0.89
os.makedirs(OUT, exist_ok=True)
out = os.path.join(OUT, 'juuen_mix.wav')
wavfile.write(out, SR, (mix * 32767).astype(np.int16))
print('wrote', out, f'{DUR:.2f}s')
