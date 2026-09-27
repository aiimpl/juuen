"""音を全部 Python で合成する（外部素材なし）。
本編 20.0 秒（レンダーの 25〜504 コマ）。エンドカードなし。
BGM：雅楽風（笙・篳篥・龍笛・楽太鼓・鉦鼓）
効果音：巻物の音、立ち上がり、梵鐘、池に水が満ちる音、秋の虫、夕暮れのカラス、りん
"""
import os
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 20.0
N = int(SR * DUR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(3)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build', 'audio')


def frame_t(f):
    """レンダーのコマ番号 → 本編の秒"""
    return (f - 25) / 24.0


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return sosfilt(sos, x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='low', fs=SR, output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='high', fs=SR, output='sos'), x)


def env_adsr(n, a, d, s, r, sustain=0.8):
    e = np.ones(n) * sustain
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    A = min(A, n)
    e[:A] = np.linspace(0, 1, A)
    D2 = min(D, n - A)
    e[A:A + D2] = np.linspace(1, sustain, D2)
    if R > 0 and R < n:
        e[-R:] *= np.linspace(1, 0, R)
    return e


def place(buf, sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[:N - i0]
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    buf[i0:i0 + len(sig), 0] += sig * gain * l
    buf[i0:i0 + len(sig), 1] += sig * gain * r


bgm = np.zeros((N, 2))
sfx = np.zeros((N, 2))

# ---------------------------------------------------------------------------
# 笙：合竹（和音）を息の強弱でふくらませる。自由リードの倍音
def sho_chord(notes, dur, att=1.2, rel=1.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, m in enumerate(notes):
        f = midi(m) * (1 + rng.uniform(-0.0015, 0.0015))
        ph = rng.uniform(0, 6.28)
        for h in range(1, 10):
            amp = (1 / h ** 1.15) * (1.25 if h % 2 == 1 else 0.8)
            if f * h > 9000:
                break
            out += amp * np.sin(2 * np.pi * f * h * t + ph * h) * (1 + 0.03 * np.sin(2 * np.pi * (0.3 + 0.1 * k) * t))
    breath = 0.65 + 0.35 * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
    out *= env_adsr(n, att, 0.1, 1.0, rel, 1.0) * breath
    out += 0.02 * bp(rng.standard_normal(n), 800, 4000) * env_adsr(n, att, 0.1, 1.0, rel, 1.0)
    return out / len(notes)


# 平調（E を主音）ふうの合竹。低め→高めへ移っていく
E4 = 64
chords = [
    ([E4, E4 + 2, E4 + 7, E4 + 12, E4 + 14], 0.0, 4.2),
    ([E4 + 2, E4 + 5, E4 + 7, E4 + 12, E4 + 17], 3.6, 3.8),
    ([E4, E4 + 5, E4 + 7, E4 + 10, E4 + 12], 7.0, 3.4),
    ([E4 + 2, E4 + 7, E4 + 9, E4 + 14, E4 + 19], 10.0, 3.4),
    ([E4, E4 + 2, E4 + 7, E4 + 12, E4 + 14, E4 + 19], 12.8, 5.5),
    ([E4 - 5, E4, E4 + 2, E4 + 7, E4 + 12], 17.6, 5.9),
]
for notes, t0, d in chords:
    place(bgm, sho_chord(notes, d, att=1.0, rel=1.4), t0, 0.16, 0.0)


# ---------------------------------------------------------------------------
# 篳篥：鼻にかかった太い音。音の入りを下からずり上げる（塩梅）
def hichiriki(seq, t0):
    """seq=[(midi, dur), ...]"""
    total = sum(d for _, d in seq)
    n = int(total * SR)
    f = np.zeros(n)
    amp = np.zeros(n)
    i = 0
    prev = seq[0][0] - 2
    for m, d in seq:
        k = int(d * SR)
        tt = np.arange(k) / SR
        # 塩梅：前の音（か少し下）から目的の音へゆっくり
        start = midi(prev if prev != m else m - 1)
        target = midi(m)
        glide = np.clip(tt / 0.28, 0, 1) ** 0.6
        fk = start + (target - start) * glide
        fk *= 1 + 0.004 * np.sin(2 * np.pi * 5.2 * tt) * np.clip((tt - 0.4) / 0.4, 0, 1)
        f[i:i + k] = fk
        a = np.clip(tt / 0.08, 0, 1) * (0.85 + 0.15 * np.sin(np.pi * tt / d)) * np.clip((d - tt) / 0.06, 0, 1)
        amp[i:i + k] = a
        i += k
        prev = m
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.zeros(n)
    for h in range(1, 26):
        fh = f * h
        # フォルマント：1.1kHz と 2.6kHz あたりを強く
        g = (1 / h) * (1 + 2.2 * np.exp(-((fh - 1100) / 380) ** 2) + 1.3 * np.exp(-((fh - 2600) / 600) ** 2))
        g = np.where(fh < 11000, g, 0)
        sig += g * np.sin(h * ph)
    sig *= amp
    sig += 0.03 * bp(rng.standard_normal(n), 1500, 5000) * amp
    return sig


mel1 = [(E4 + 7, 0.9), (E4 + 9, 0.6), (E4 + 7, 0.5), (E4 + 5, 1.1), (E4 + 2, 0.7), (E4 + 5, 0.6), (E4 + 7, 1.6)]
mel2 = [(E4 + 12, 1.0), (E4 + 10, 0.5), (E4 + 9, 0.5), (E4 + 7, 1.2), (E4 + 9, 0.6), (E4 + 7, 0.6), (E4 + 5, 0.6), (E4 + 7, 1.9)]
place(bgm, hichiriki(mel1, 0), 4.4, 0.085, -0.15)
place(bgm, hichiriki(mel2, 0), 10.6, 0.08, -0.15)


# ---------------------------------------------------------------------------
# 龍笛：息まじりの高い笛。装飾の小さな上下
def ryuteki(seq, t0):
    total = sum(d for _, d in seq)
    n = int(total * SR)
    f = np.zeros(n)
    amp = np.zeros(n)
    i = 0
    for m, d in seq:
        k = int(d * SR)
        tt = np.arange(k) / SR
        fk = midi(m) * (1 + 0.006 * np.sin(2 * np.pi * 5.8 * tt) * np.clip((tt - 0.25) / 0.3, 0, 1))
        # 打ち指の小さな跳ね
        fk *= np.where(tt < 0.06, 2 ** (2 / 12), 1.0)
        f[i:i + k] = fk
        amp[i:i + k] = np.clip(tt / 0.05, 0, 1) * np.clip((d - tt) / 0.08, 0, 1) * (0.8 + 0.2 * np.sin(np.pi * tt / d))
        i += k
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(ph) + 0.22 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    noise = rng.standard_normal(n)
    breath = np.zeros(n)
    # 息の音：その音程のまわりだけ
    breath = bp(noise, 1800, 7000) * 0.18
    return (sig + breath) * amp


rt1 = [(E4 + 19, 0.7), (E4 + 21, 0.5), (E4 + 24, 1.2), (E4 + 21, 0.5), (E4 + 19, 0.6), (E4 + 17, 1.0), (E4 + 19, 1.5)]
rt2 = [(E4 + 24, 1.2), (E4 + 26, 0.6), (E4 + 24, 0.6), (E4 + 21, 1.0), (E4 + 19, 1.4), (E4 + 17, 0.6), (E4 + 19, 2.2)]
place(bgm, ryuteki(rt1, 0), 7.6, 0.07, 0.25)
place(bgm, ryuteki(rt2, 0), 14.2, 0.075, 0.25)


# ---------------------------------------------------------------------------
# 楽太鼓と鉦鼓
def taiko(strength=1.0, low=58):
    n = int(1.8 * SR)
    t = np.arange(n) / SR
    f = low * (1 + 0.6 * np.exp(-t * 18))
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 2.6) + 0.35 * np.sin(1.6 * ph) * np.exp(-t * 5)
    hit = lp(rng.standard_normal(n), 900) * np.exp(-t * 40) * 0.8
    return (body + hit) * strength


def shoko():
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for fr, a, dcy in ((1320, 1.0, 5), (2210, 0.7, 7), (3480, 0.5, 9), (4850, 0.3, 12)):
        sig += a * np.sin(2 * np.pi * fr * t) * np.exp(-t * dcy)
    sig += 0.4 * hp(rng.standard_normal(n), 3000) * np.exp(-t * 60)
    return sig * 0.5


phase_starts = [frame_t(f) for f in (132, 152, 178, 204, 246)]
for k, ts in enumerate(phase_starts):
    place(bgm, taiko(0.9 if k < 4 else 1.0), ts, 0.42, 0.0)
    place(bgm, shoko(), ts + 0.45, 0.10, 0.35)
# 雅楽の太鼓は「ドン…ドン」と間をおいて二打（雌桴・雄桴）
place(bgm, taiko(0.45), frame_t(108) - 0.1, 0.35)
place(bgm, taiko(0.6), frame_t(108) + 0.55, 0.35)
place(bgm, taiko(1.1, 52), frame_t(400), 0.5)
place(bgm, taiko(0.5, 52), frame_t(400) + 0.7, 0.4)

# ---------------------------------------------------------------------------
# 効果音
# 巻物が広がる：紙のこすれ＋軸の転がる低い音
f0, f1 = frame_t(25), frame_t(61)
n = int((f1 - f0 + 0.3) * SR)
t = np.arange(n) / SR
paper = bp(rng.standard_normal(n), 1500, 9000) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 7 * t))) * np.sin(np.pi * np.clip(t / (f1 - f0 + 0.3), 0, 1)) ** 0.8
roll = lp(rng.standard_normal(n), 180) * 3 * np.sin(np.pi * np.clip(t / (f1 - f0 + 0.3), 0, 1))
place(sfx, paper * 0.10 + roll * 0.14, f0)
# 冒頭のりん
def rin(f=620, dur=5.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for ratio, a, dcy in ((1.0, 1.0, 0.7), (2.76, 0.55, 1.4), (5.40, 0.3, 2.4), (8.93, 0.15, 3.5)):
        fr = f * ratio
        sig += a * np.sin(2 * np.pi * fr * t) * np.exp(-t * dcy) * (1 + 0.15 * np.sin(2 * np.pi * 3.1 * ratio * t))
    sig += 0.3 * hp(rng.standard_normal(n), 4000) * np.exp(-t * 80)
    return sig


place(sfx, rin(640, 5), 0.05, 0.16, 0.1)
# 墨線が立ち上がる：高いきらめき
f0, f1 = frame_t(108), frame_t(134)
n = int((f1 - f0 + 1.0) * SR)
t = np.arange(n) / SR
sh = np.zeros(n)
for k in range(6):
    fr = 1800 * 2 ** (k / 5) * (1 + 0.4 * t / (f1 - f0))
    sh += np.sin(2 * np.pi * np.cumsum(fr) / SR) / 6
sh *= np.sin(np.pi * np.clip(t / (f1 - f0 + 1.0), 0, 1)) ** 2
place(sfx, sh, f0, 0.035, 0.0)


# 梵鐘：巻物が消えて景色が開くところ
def bonsho(f=98, dur=8.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for ratio, a, dcy, beat in ((0.5, 0.6, 0.25, 0.9), (1.0, 1.0, 0.35, 1.7), (1.62, 0.6, 0.5, 2.3), (2.23, 0.5, 0.7, 1.1),
                                (2.95, 0.35, 0.9, 2.9), (4.1, 0.2, 1.4, 3.4), (5.4, 0.12, 2.0, 1.3)):
        fr = f * ratio
        sig += a * (np.sin(2 * np.pi * fr * t) + 0.5 * np.sin(2 * np.pi * (fr + beat) * t)) * np.exp(-t * dcy)
    sig += 0.8 * lp(rng.standard_normal(n), 400) * np.exp(-t * 25)
    return sig / 2


place(sfx, bonsho(), frame_t(298), 0.36, 0.0)
# 池に水が満ちる：低いざわめきと、ひたひたの水音
f0 = frame_t(314)
n = N - int(f0 * SR)
t = np.arange(n) / SR
swell = np.clip(t / 3.5, 0, 1)
wash = lp(rng.standard_normal(n), 600) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.22 * t) ** 2)
wash = hp(wash, 60)
lap = np.zeros(n)
for k in range(int(n / SR * 3.0)):
    tk = rng.uniform(0, n / SR)
    i0 = int(tk * SR)
    m = int(0.18 * SR)
    if i0 + m >= n:
        continue
    tt = np.arange(m) / SR
    fr = rng.uniform(300, 900)
    lap[i0:i0 + m] += np.sin(2 * np.pi * fr * tt * (1 + 2.5 * tt)) * np.exp(-tt * 28) * rng.uniform(0.3, 1)
lap = bp(lap, 200, 3000)
water = (wash * 0.9 + lap * 0.35) * swell * np.clip((n / SR - t) / 2.0, 0.25, 1)
place(sfx, water, f0, 0.2, 0.0)


# 秋の虫（鈴虫の「リーン」、コオロギのコロコロ）
def suzumushi(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    car = np.sin(2 * np.pi * 4300 * t)
    gate = (np.sin(2 * np.pi * 42 * t) > 0).astype(float)
    ph = (t % 1.4) / 1.4
    burst = np.where(ph < 0.45, np.sin(np.pi * ph / 0.45), 0)
    return car * gate * burst


def korogi(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    car = np.sin(2 * np.pi * 3600 * t)
    gate = (np.sin(2 * np.pi * 28 * t) > 0.2).astype(float)
    ph = (t % 0.9) / 0.9
    burst = np.where(ph < 0.3, 1.0, 0)
    return car * gate * burst


f0 = frame_t(330)
dur = DUR - f0
fade = lambda n: np.clip(np.arange(n) / SR / 2.5, 0, 1)
s1 = suzumushi(dur)
s1 *= fade(len(s1))
place(sfx, lp(s1, 7000), f0, 0.012, -0.6)
k1 = korogi(dur - 1.0)
k1 *= fade(len(k1))
place(sfx, k1, f0 + 1.0, 0.009, 0.55)


# 夕暮れのカラス（遠く）
def crow():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 620 * (1 + 0.25 * np.sin(np.pi * t / 0.42)) * (1 - 0.15 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.zeros(n)
    for h in range(1, 12):
        fh = f * h
        g = (1 / h) * (1 + 3 * np.exp(-((fh - 1400) / 300) ** 2) + 2 * np.exp(-((fh - 2300) / 400) ** 2))
        sig += g * np.sin(h * ph)
    sig += 0.5 * bp(rng.standard_normal(n), 1000, 3000)
    return lp(sig * np.sin(np.pi * t / 0.42) ** 0.6, 3500)


for t0, pan in ((15.3, -0.7), (15.85, -0.7), (17.9, 0.6)):
    place(sfx, crow(), t0, 0.022, pan)
# タイトルでりん
place(sfx, rin(760, 5.5), frame_t(443), 0.14, 0.0)

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
mix = bgm * 0.9 + sfx
# フェードイン・アウト
fi = int(0.02 * SR)
mix[:fi] *= np.linspace(0, 1, fi)[:, None]
fo = int(2.2 * SR)
mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
# 軽いリバーブ（多重ディレイ）
rev = np.zeros_like(mix)
for d, a in ((0.031, 0.35), (0.047, 0.3), (0.071, 0.25), (0.113, 0.2), (0.173, 0.15), (0.257, 0.1), (0.371, 0.07)):
    k = int(d * SR)
    rev[k:, 0] += mix[:-k, 1] * a
    rev[k:, 1] += mix[:-k, 0] * a
mix = mix + lp(rev, 5000) * 0.5
peak = np.abs(mix).max()
mix = mix / peak * 0.89
os.makedirs(OUT, exist_ok=True)
out = os.path.join(OUT, 'byodoin_mix.wav')
wavfile.write(out, SR, (mix * 32767).astype(np.int16))
print('wrote', out, f'{DUR}s peak(before norm)={peak:.2f}')
