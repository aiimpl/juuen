"""カメラ：一本の滑らかな曲線（時間で重みを付けた Catmull-Rom）で、ズームなし・往復なし。
巻物を真上から → 斜めへ起こす → 中堂を中心に南東から正面へ一方向に回り込みながら降りる → 正面の軸線を後ろへ引いて全景。
"""
import math

import bpy
from mathutils import Vector

import geometry as G
from .common import F_END, scene, link, fcurves_of

PC = ((G.SCROLL['x0'] + G.SCROLL['x1']) / 2, 0.0)     # 巻物の中心
LENS = 32.0


def orbit_pt(f):
    """南東から正面へ、一方向の回り込み（角度は時間に比例）"""
    u = (f - 130) / (395 - 130)
    th = math.radians(-42 + 42 * u)
    r = 54 - 8 * math.sin(math.pi * u)
    z = 30 - 25.5 * u
    return (r * math.cos(th), r * math.sin(th), z), (0.0, 0.0, 3.0 + 3.0 * u)


CTRL = [(1, (PC[0] + 9.0, 0.0, 104.0), (PC[0], 0.0, 0.0)),
        (61, (PC[0] + 9.5, 0.0, 99.0), (PC[0], 0.0, 0.0))]
for f_ in (130, 180, 230, 280, 330, 395):
    c_, t_ = orbit_pt(f_)
    CTRL.append((f_, c_, t_))
CTRL += [(450, (78.0, 0.0, 5.6), (0.0, 0.0, 6.4)), (504, (112.0, 0.0, 7.2), (0.0, 0.0, 6.6))]


def hermite_path(f, idx):
    """時間で重みを付けた Catmull-Rom。両端は速度0、途中は速度が途切れない"""
    fs = [c[0] for c in CTRL]
    ps = [Vector(c[idx]) for c in CTRL]
    n = len(fs)
    if f <= fs[0]:
        return tuple(ps[0])
    if f >= fs[-1]:
        return tuple(ps[-1])
    i = max(k for k in range(n - 1) if fs[k] <= f)

    def tan(k):
        if k == 0 or k == n - 1:
            return Vector((0, 0, 0))
        return (ps[k + 1] - ps[k - 1]) / (fs[k + 1] - fs[k - 1])
    h = fs[i + 1] - fs[i]
    t = (f - fs[i]) / h
    h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
    h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    p = ps[i] * h00 + tan(i) * (h10 * h) + ps[i + 1] * h01 + tan(i + 1) * (h11 * h)
    return tuple(p)


def cam_path(f):
    return hermite_path(f, 1), hermite_path(f, 2)




def build():
    cam_d = bpy.data.cameras.new('カメラ')
    cam = bpy.data.objects.new('カメラ', cam_d)
    link(cam)
    scene().camera = cam
    tgt = bpy.data.objects.new('注視点', None)
    link(tgt)
    tc_ = cam.constraints.new('TRACK_TO')
    tc_.target = tgt
    tc_.track_axis = 'TRACK_NEGATIVE_Z'
    tc_.up_axis = 'UP_Y'
    cam_d.sensor_width = 36
    cam_d.clip_start = 0.1
    cam_d.clip_end = 6000
    cam_d.lens = LENS
    for f in list(range(1, F_END + 1, 2)) + [F_END]:
        c, t_ = cam_path(f)
        cam.location = c
        cam.keyframe_insert('location', frame=f)
        tgt.location = t_
        tgt.keyframe_insert('location', frame=f)
    for idb in (cam, tgt):
        for fc in fcurves_of(idb.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    return cam

