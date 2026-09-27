"""鳳凰堂（中堂・裳階・翼廊・隅楼・尾廊・反橋）を部材から組み立てる。
部材は 5 つの段（p1 基壇・床 → p2 柱 → p3 壁・欄間・組物 → p4 屋根 → p5 高欄・鳳凰・灯籠）に分けて
別々のオブジェクトにし、段ごとに prog をキー打ちして、中堂から外へ部材ごとに実体化させる。
"""
import math

import numpy as np
from mathutils import Vector

import geometry as G
from .common import T, new_coll
from .materials import MAT, GLOW
from .mesh import MB
from .roof import build_roof


def ring_beam(mb, x0, x1, y0, y1, z, w, h, mat, nose=0.32):
    for a, c in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        mb.at((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
        va, vc = Vector((*a, z)), Vector((*c, z))
        dv = (vc - va).normalized()
        mb.seg_box(tuple(va - dv * nose), tuple(vc + dv * nose), w, h, mat)
        # 木鼻の先に黄土の木口
        mb.seg_box(tuple(vc + dv * nose), tuple(vc + dv * (nose + 0.02)), w * 1.02, h * 1.02, MAT['ochre'])


def renji(mb, p0, p1, z0, z1, n=None, mat=None):
    """連子窓：縦の細い格子（丹）と黒い奥"""
    mat = mat or MAT['ni']
    a, c = Vector((*p0, 0)), Vector((*p1, 0))
    d = (c - a)
    Lw = d.length
    d.normalize()
    nrm = Vector((-d.y, d.x, 0))
    n = n or max(4, int(Lw / 0.16))
    for zz in (z0, z1):
        mb.seg_box((*a.xy, zz), (*c.xy, zz), 0.1, 0.1, mat)
    for i in range(1, n):
        p = a + d * (Lw * i / n)
        mb.seg_box((*p.xy, z0), (*p.xy, z1), 0.05, 0.07, mat)
    back = (a + c) / 2 + nrm * 0.06
    mb.box((back.x, back.y, (z0 + z1) / 2), (Lw, 0.03, z1 - z0), MAT['black'], math.atan2(d.y, d.x))


def ranma(mb, p0, p1, z0, z1):
    """欄間：菱格子に、交点ごとに金の花菱"""
    a, c = Vector((*p0, 0)), Vector((*p1, 0))
    d = (c - a)
    Lw = d.length
    d.normalize()
    nrm = Vector((-d.y, d.x, 0))
    H_ = z1 - z0
    for zz in (z0, z1):
        mb.seg_box((*a.xy, zz), (*c.xy, zz), 0.1, 0.1, MAT['ni'])
    back = (a + c) / 2 + nrm * 0.05
    mb.box((back.x, back.y, (z0 + z1) / 2), (Lw, 0.02, H_), MAT['black'], math.atan2(d.y, d.x))

    def P(u, v):
        q = a + d * u
        return (q.x, q.y, z0 + v)
    step = 0.22
    k = -int(H_ / step) - 1
    while k * step < Lw + H_:
        for sgn in (1, -1):
            c0 = k * step
            # 直線 v = sgn*(u - c0)（sgn=-1 は右下がり）を矩形 [0,Lw]x[0,H_] で切る
            if sgn > 0:
                u0, v0 = max(0.0, c0), max(0.0, -c0)
                u1 = min(Lw, c0 + H_)
                v1 = u1 - c0
            else:
                u0 = max(0.0, c0 - H_) if c0 - H_ > 0 else 0.0
                v0 = c0 - u0 if c0 - u0 <= H_ else H_
                u0 = c0 - v0
                u1 = min(Lw, c0)
                v1 = c0 - u1
            if u1 - u0 > 0.02 and 0 <= v0 <= H_ + 1e-6 and 0 <= v1 <= H_ + 1e-6:
                mb.seg_box(P(u0, v0), P(u1, v1), 0.03, 0.04, MAT['ni'])
        k += 1
    # 花菱（交点の中心に四弁）
    for iu in range(int(Lw / step) + 1):
        for iv in range(int(H_ / step) + 1):
            u_, v_ = iu * step + (step / 2 if iv % 2 else 0), iv * step
            if 0.08 < u_ < Lw - 0.08 and 0.08 < v_ < H_ - 0.08:
                p = Vector(P(u_, v_)) - nrm * 0.03
                for ang in range(4):
                    aa = ang * math.pi / 2 + math.pi / 4
                    q = p + (d * math.cos(aa) + Vector((0, 0, 1)) * math.sin(aa)) * 0.03
                    mb.cyl(tuple(q), tuple(q - nrm * 0.015), 0.022, MAT['gold'], 8)


def koza(mb, p0, p1, z0, z1):
    """格狭間：腰壁に彫った曲線の窓。金の縁と黒い奥"""
    a, c = Vector((*p0, 0)), Vector((*p1, 0))
    d = (c - a)
    Lw = d.length
    d.normalize()
    nrm = Vector((-d.y, d.x, 0))
    mid = (a + c) / 2
    W_, H_ = Lw * 0.7, (z1 - z0) * 0.72
    # 右半分の制御点（u は半幅比、v は高さ比）：脚→内へ刳る→肩の尖り→火灯形の上辺→頂
    ctrl = [(0.78, 0.0), (0.8, 0.08), (0.66, 0.22), (0.7, 0.42), (0.98, 0.56), (0.8, 0.66), (0.5, 0.78), (0.22, 0.88), (0.0, 1.0)]

    def cr(pts, n=6):
        out = []
        for i in range(len(pts) - 1):
            p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
            for k in range(n):
                t = k / n
                out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                        + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
        out.append(pts[-1])
        return out
    right = cr(ctrl)
    left = [(-u, v) for (u, v) in reversed(right[:-1])]
    pts = [(u * W_ / 2, v * H_) for (u, v) in [(-0.78, 0.0)] + right + left[:-1]]
    ctr = mid + nrm * 0.07
    rot_u = d
    org = Vector((ctr.x, ctr.y, z0 + (z1 - z0) * 0.14))
    big = [(u * 1.1, v * 1.08 - 0.02) for (u, v) in pts]
    mb.extrude(big, 0.025, tuple(org), rot_u, (0, 0, 1), MAT['gold'])
    mb.extrude(pts, 0.02, tuple(org + nrm * 0.016), rot_u, (0, 0, 1), MAT['black'])


def door(mb, p0, p1, z0, z1):
    """板扉＋上の格子：丹の枠"""
    a, c = Vector((*p0, 0)), Vector((*p1, 0))
    d = (c - a)
    Lw = d.length
    d.normalize()
    nrm = Vector((-d.y, d.x, 0))
    mid = (a + c) / 2 + nrm * 0.04
    rot = math.atan2(d.y, d.x)
    zm = z0 + (z1 - z0) * 0.72
    mb.box((mid.x, mid.y, (z0 + zm) / 2), (Lw - 0.25, 0.08, zm - z0), MAT['ni'], rot)
    # 扉の割れ目と金具
    mb.box((mid.x - nrm.x * 0.05, mid.y - nrm.y * 0.05, (z0 + zm) / 2), (0.03, 0.02, zm - z0 - 0.1), MAT['black'], rot)
    for k in (-0.25, 0.25):
        p = mid + d * (Lw * k) - nrm * 0.06
        for zz in (z0 + 0.4, zm - 0.4):
            mb.box((p.x, p.y, zz), (0.4, 0.02, 0.08), MAT['gold'], rot)
        # 乳金物（饅頭形の鋲）を縦横に
        for iz in range(5):
            zz = z0 + 0.35 + (zm - z0 - 0.7) * iz / 4
            for ix in (-1, 0, 1):
                q = p + d * (ix * Lw * 0.09) - nrm * 0.01
                mb.cyl((q.x, q.y, zz), (q.x - nrm.x * 0.05, q.y - nrm.y * 0.05, zz), 0.035, MAT['gold'], 8, 0.015)
    ranma(mb, tuple((a + d * 0.12 - nrm * 0.02).xy), tuple((c - d * 0.12 - nrm * 0.02).xy), zm + 0.08, z1 - 0.1)
    # 扉の框と桟
    for k_ in (-0.5, 0.0, 0.5):
        p = mid + d * ((Lw - 0.3) * k_ * 0.98) - nrm * 0.05
        mb.box((p.x, p.y, (z0 + zm) / 2), (0.09, 0.03, zm - z0 - 0.05), MAT['ni'], rot)
    for zz in (z0 + 0.12, (z0 + zm) / 2, zm - 0.1):
        p = mid - nrm * 0.05
        mb.box((p.x, p.y, zz), (Lw - 0.3, 0.035, 0.08), MAT['ni'], rot)


def wall(mb, p0, p1, z0, z1, mat):
    a, c = Vector((*p0, 0)), Vector((*p1, 0))
    d = (c - a)
    mid = (a + c) / 2
    mb.box((mid.x, mid.y, (z0 + z1) / 2), (d.length, 0.1, z1 - z0), mat, math.atan2(d.y, d.x))


def arc_pts(c, r_u, r_v, a0, a1, n=6):
    return [(c[0] + r_u * math.cos(a0 + (a1 - a0) * k / n), c[1] + r_v * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def hijiki_prof(L, h):
    """肘木の側面：上は真っ直ぐ、両端の下を円弧で繰る"""
    r = 0.2 * L
    pts = [(-L / 2, h), (L / 2, h), (L / 2, h * 0.45)]
    pts += arc_pts((L / 2 - r, h * 0.45), r, h * 0.45, 0, -math.pi / 2, 6)[1:]
    pts += arc_pts((-L / 2 + r, h * 0.45), r, h * 0.45, -math.pi / 2, -math.pi, 6)
    return pts


def masu(mb, pos, w, h, o, mat=None):
    """斗：下の斗尻が曲面ですぼまり（斗繰り）、上は垂直"""
    mat = mat or MAT['ni']
    side = Vector((-o.y, o.x, 0))
    loops = []
    for k in range(9):
        t = k / 8
        if t <= 0.5:
            tt = t / 0.5
            half = w * (0.34 + 0.16 * (1 - math.sqrt(max(0, 1 - tt * tt))))
            z = h * 0.45 * tt
        else:
            half = w * 0.5
            z = h * (0.45 + 0.55 * (t - 0.5) / 0.5)
        c = Vector(pos) + Vector((0, 0, z))
        loops.append([tuple(c + o * dx * half + side * dy * half) for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    mb.loft(loops, mat)


def hijiki(mb, center, axis, L, h, t, mat=None):
    ax = Vector(axis).normalized()
    mb.extrude(hijiki_prof(L, h), t, center, ax, (0, 0, 1), mat or MAT['ni'])
    # 木口（両端）を黄土に
    for sgn in (-1, 1):
        p = Vector(center) + ax * (sgn * L / 2) + Vector((0, 0, h * 0.72))
        mb.seg_box(tuple(p), tuple(p + ax * sgn * 0.012), t * 1.02, h * 0.55, MAT['ochre'])


def kaerumata(mb, center, axis, W, H, t):
    """蟇股：蛙が股を広げたような曲線の束。上に小さな斗"""
    n = 8
    outer_l = [(-W / 2 + (W / 2 - 0.12 * W) * (1 - math.cos(math.pi / 2 * k / n)), H * 0.9 * math.sin(math.pi / 2 * k / n)) for k in range(n + 1)]
    outer_r = [(-u, v) for (u, v) in reversed(outer_l)]
    inner_r = [(0.4 * W * math.cos(math.pi / 2 * k / n), 0.62 * H * math.sin(math.pi / 2 * k / n)) for k in range(n + 1)]
    inner_l = [(-u, v) for (u, v) in reversed(inner_r[:-1])]
    pts = outer_l + [(-0.12 * W, H), (0.12 * W, H)] + outer_r + inner_r + inner_l
    ax = Vector(axis).normalized()
    mb.extrude(pts, t, center, ax, (0, 0, 1), MAT['ni'])
    # 中の彫り（宝珠形）を金で
    c = Vector(center) + Vector((0, 0, H * 0.42))
    w_ = ax.cross(Vector((0, 0, 1))).normalized()
    mb.cyl(tuple(c - w_ * t * 0.3), tuple(c + w_ * t * 0.3), H * 0.16, MAT['gold'], 14)


def kumimono(mb, x, y, z, outward, size=1.0):
    """組物（三手先）：曲面の大斗→繰形の肘木と巻斗→外へ三段の手先→尾垂木→通肘木"""
    s_ = size
    o = Vector((outward[0], outward[1], 0))
    if o.length < 1e-6:
        o = Vector((1, 0, 0))
    o.normalize()
    side = Vector((-o.y, o.x, 0))
    base = Vector((x, y, z))
    masu(mb, base, 0.44 * s_, 0.2 * s_, o)
    zc = 0.2 * s_
    for k in range(3):
        zk = base.z + zc + k * 0.15 * s_
        cpos = Vector((x, y, zk)) + o * (0.36 * k * s_)
        L_ = (1.15 - 0.12 * k) * s_
        hijiki(mb, tuple(cpos), side, L_, 0.12 * s_, 0.12 * s_)
        for u in (-0.4, 0.0, 0.4):
            masu(mb, tuple(cpos + side * (u * L_) + Vector((0, 0, 0.12 * s_))), 0.2 * s_, 0.1 * s_, o)
        tip = Vector((x, y, zk)) + o * (0.36 * (k + 1) * s_)
        arm_c = (Vector((x, y, zk)) + tip) / 2 + o * 0.05 * s_
        hijiki(mb, tuple(arm_c), o, (tip - Vector((x, y, zk))).length + 0.5 * s_, 0.12 * s_, 0.12 * s_)
        masu(mb, tuple(tip + Vector((0, 0, 0.12 * s_))), 0.2 * s_, 0.1 * s_, o)
    t0 = Vector((x, y, base.z + 0.58 * s_)) - o * 0.3 * s_
    t1 = Vector((x, y, base.z + 0.3 * s_)) + o * 1.15 * s_
    mb.seg_box(tuple(t0), tuple(t1), 0.14 * s_, 0.16 * s_, MAT['ni'])
    mb.seg_box(tuple(t1), tuple(t1 + (t1 - t0).normalized() * 0.03), 0.15 * s_, 0.17 * s_, MAT['ochre'])
    top = Vector((x, y, base.z + 0.62 * s_)) + o * 1.08 * s_
    hijiki(mb, tuple(top), side, 1.5 * s_, 0.13 * s_, 0.14 * s_)


def railing(mb, pts, z0, h, mat=None, step=1.2):
    mat = mat or MAT['ni']
    for i in range(len(pts) - 1):
        a, c = Vector(pts[i]), Vector(pts[i + 1])
        mb.at((a.x + c.x) / 2, (a.y + c.y) / 2)
        for zz, wh in ((z0 + 0.06, 0.1), (z0 + h * 0.5, 0.07), (z0 + h, 0.1)):
            mb.seg_box((a.x, a.y, zz), (c.x, c.y, zz), wh, wh, mat)
        Lc = (c - a).length
        k = max(1, int(Lc / step))
        for j in range(k + 1):
            p = a + (c - a) * (j / k)
            mb.seg_box((p.x, p.y, z0), (p.x, p.y, z0 + h + 0.06), 0.1, 0.1, mat)
            zt = z0 + h + 0.06
            mb.cyl((p.x, p.y, zt), (p.x, p.y, zt + 0.06), 0.065, MAT['gold'], 10, 0.07)
            mb.cyl((p.x, p.y, zt + 0.06), (p.x, p.y, zt + 0.14), 0.075, MAT['gold'], 10, 0.05)
            mb.cyl((p.x, p.y, zt + 0.14), (p.x, p.y, zt + 0.24), 0.05, MAT['gold'], 10, 0.004)
        kk = max(2, int(Lc / 0.3))
        for j in range(kk):
            p = a + (c - a) * ((j + 0.5) / kk)
            mb.seg_box((p.x, p.y, z0 + 0.06), (p.x, p.y, z0 + h * 0.5), 0.035, 0.035, mat)


def roof_at(mb, cx, cy, hx, hy, r, thx, thy, **kw):
    sub = MB()
    sub.cur = mb.cur
    build_roof(sub, hx, hy, r, thx, thy, **kw)
    mb.merge(sub, (cx, cy, 0))


def phoenix(mb, x, y, z, ang, sc=1.15):
    """鳳凰：曲面の胴・首・頭、軸と刻みのある羽根（翼三層・鱗羽・尾羽）"""
    g = MAT['gold']
    ca, sa = math.cos(ang), math.sin(ang)

    def W(p):
        fx, fy, fz = p
        return Vector((x + (fx * ca - fy * sa) * sc, y + (fx * sa + fy * ca) * sc, z + fz * sc))

    def Wv(v):
        return Vector((v[0] * ca - v[1] * sa, v[0] * sa + v[1] * ca, v[2]))

    def bez(p0, p1, p2, p3, t):
        return tuple((1 - t) ** 3 * p0[k] + 3 * (1 - t) ** 2 * t * p1[k] + 3 * (1 - t) * t * t * p2[k] + t ** 3 * p3[k] for k in range(3))

    def tube(pts, radii, ry=1.0, seg=16):
        loops = []
        n = len(pts)
        side = None
        for i in range(n):
            p = W(pts[i])
            tn = (W(pts[min(i + 1, n - 1)]) - W(pts[max(i - 1, 0)])).normalized()
            if side is None:
                side = Wv((0, 1, 0))
            side = (side - tn * side.dot(tn)).normalized()
            up = side.cross(tn).normalized()
            if up.z < 0 and i == 0:
                side = -side
                up = -up
            r = radii[i] * sc
            loops.append([tuple(p + side * math.cos(2 * math.pi * k / seg) * r + up * math.sin(2 * math.pi * k / seg) * r * ry)
                          for k in range(seg)])
        mb.loft(loops, g)

    def feather(pts, wmax, hint=(0, 1, 0), notch=0.1, rib=0.3, shape=None):
        n = len(pts)
        ws = []
        for i in range(n):
            t = i / (n - 1)
            f = shape(t) if shape else (math.sin(math.pi * min(1, t * 1.15)) ** 0.7 * (1 - 0.85 * t ** 3) + 0.15 * (1 - t))
            ws.append(max(0.004, wmax * f) * sc)
        mb.blade([tuple(W(p)) for p in pts], ws, tuple(Wv(hint)), g, rib=rib, notch=notch, thick=0.008 * sc)

    # 台座・脚・爪
    mb.cyl(tuple(W((0, 0, -0.05))), tuple(W((0, 0, 0.03))), 0.17 * sc, g, 20, 0.15 * sc)
    mb.cyl(tuple(W((0, 0, 0.03))), tuple(W((0, 0, 0.07))), 0.12 * sc, g, 20, 0.1 * sc)
    for fy in (-0.06, 0.06):
        tube([(0.02, fy, 0.07), (0.05, fy, 0.18), (0.03, fy, 0.3), (-0.02, fy, 0.38)], [0.022, 0.026, 0.034, 0.045], seg=10)
        for k in range(3):
            a_ = math.radians(-35 + 35 * k)
            tube([(0.02, fy, 0.075), (0.02 + 0.07 * math.cos(a_), fy + 0.07 * math.sin(a_), 0.07)], [0.012, 0.004], seg=6)
    # 胴
    body = [bez((-0.4, 0, 0.46), (-0.2, 0, 0.36), (0.05, 0, 0.38), (0.22, 0, 0.56), i / 11) for i in range(12)]
    tube(body, [0.035 + 0.085 * math.sin(math.pi * (i / 11)) ** 0.8 for i in range(12)], ry=1.15, seg=20)
    # 首（S 字）と頭
    neck = [bez((0.2, 0, 0.54), (0.34, 0, 0.7), (0.18, 0, 0.86), (0.36, 0, 0.99), i / 11) for i in range(12)]
    tube(neck, [0.085 - 0.04 * (i / 11) for i in range(12)], seg=14)
    head = [bez((0.33, 0, 0.98), (0.38, 0, 1.05), (0.45, 0, 1.05), (0.5, 0, 1.01), i / 7) for i in range(8)]
    tube(head, [0.048, 0.058, 0.06, 0.056, 0.048, 0.036, 0.022, 0.008], seg=14)
    mb.cyl(tuple(W((0.49, 0, 1.015))), tuple(W((0.6, 0, 0.99))), 0.02 * sc, g, 8, 0.002 * sc)      # くちばし
    for fy in (-0.04, 0.04):
        mb.cyl(tuple(W((0.43, fy * 0.9, 1.035))), tuple(W((0.43, fy * 1.25, 1.035))), 0.012 * sc, MAT['black'], 8)  # 目
    tube([(0.44, 0, 0.99), (0.45, 0, 0.93), (0.42, 0, 0.88)], [0.022, 0.018, 0.006], seg=8)        # 肉垂
    for k, (dx, dz, bend) in enumerate(((-0.3, 0.32, 0.08), (-0.4, 0.2, 0.05), (-0.2, 0.36, 0.1))):
        pts = [bez((0.38, 0, 1.06), (0.38 + dx * 0.3, 0, 1.06 + dz * 0.6 + bend), (0.38 + dx * 0.8, 0, 1.06 + dz), (0.38 + dx, 0, 1.06 + dz * 0.85), i / 7) for i in range(8)]
        feather(pts, 0.035, hint=(0, 1, 0), notch=0.2)
    # 翼：風切羽（上へ扇）、次列風切、雨覆
    for side in (-1, 1):
        root = Vector((0.02, side * 0.11, 0.58))
        for k in range(12):
            a_ = math.radians(24 + 7.8 * k)
            L_ = 0.62 + 0.2 * math.sin(math.pi * k / 11)
            tip = root + Vector((-L_ * math.cos(a_) * 0.72, side * (0.2 + 0.12 * math.sin(a_)), L_ * math.sin(a_)))
            mid = root * 0.45 + tip * 0.55 + Vector((-0.05, side * 0.07, 0.03))
            pts = [bez(tuple(root), tuple(root * 0.6 + mid * 0.4), tuple(mid), tuple(tip), i / 8) for i in range(9)]
            feather(pts, 0.052, hint=(0, side, 0.3), notch=0.14)
        for k in range(9):
            a_ = math.radians(30 + 9 * k)
            L_ = 0.4
            tip = root + Vector((-L_ * math.cos(a_) * 0.7, side * 0.17, L_ * math.sin(a_)))
            pts = [tuple(root * (1 - i / 6) + tip * (i / 6) + Vector((0, side * 0.03 * math.sin(math.pi * i / 6), 0))) for i in range(7)]
            feather(pts, 0.06, hint=(0, side, 0.3), notch=0.1)
        for row in range(3):
            for k in range(6):
                a_ = math.radians(35 + 12 * k)
                L_ = 0.1 + 0.05 * row
                r0 = root + Vector((-0.03 * row, side * (0.02 + 0.03 * row), 0.02 * row))
                tip = r0 + Vector((-L_ * math.cos(a_), side * 0.05, L_ * math.sin(a_)))
                feather([tuple(r0), tuple(r0 * 0.5 + tip * 0.5), tuple(tip)], 0.04, hint=(0, side, 0.3), notch=0.0, rib=0.15,
                        shape=lambda t: 0.7 + 0.3 * math.sin(math.pi * t))
    # 尾羽：上下に扇状に開いて後ろへ伸び、先は一枚ずつ渦を巻く
    for k in range(7):
        d_ = k - 3
        fy = d_ * 0.035
        spread = d_ * 0.1
        pts = []
        n1 = 12
        for i in range(n1):
            t = i / (n1 - 1)
            ax_ = -0.36 - (0.78 - 0.05 * abs(d_)) * t
            az_ = 0.44 + (0.08 + 0.06 * d_) * t + (0.55 + 0.1 * d_) * t ** 2.0
            pts.append((ax_, fy + spread * t, az_))
        # 渦巻き：最後の点から、進行方向に沿って内側へ巻く
        px_, py_, pz_ = pts[-1]
        dx, dz = pts[-1][0] - pts[-2][0], pts[-1][2] - pts[-2][2]
        a0 = math.atan2(dz, dx)
        R = 0.09
        cx_, cz_ = px_ + R * math.cos(a0 + math.pi / 2), pz_ + R * math.sin(a0 + math.pi / 2)
        for j in range(1, 9):
            aa = a0 - math.pi / 2 + j * (1.5 * math.pi / 8)
            rr_ = R * (1 - 0.55 * j / 8)
            pts.append((cx_ + rr_ * math.cos(aa), py_, cz_ + rr_ * math.sin(aa)))
        feather(pts, 0.062, hint=(0, 1, 0), notch=0.12,
                shape=lambda t: (0.35 + 0.3 * math.sin(math.pi * min(1, t / 0.6)) + 0.35 * math.exp(-((t - 0.52) / 0.09) ** 2)) * (1 - 0.7 * max(0, t - 0.6) / 0.4))


def lantern(mb, x, y, z=0.35, s=1.0, glow=True):
    st = MAT['stone']
    mb.at(x, y, jit=0.05)
    mb.cyl((x, y, z), (x, y, z + 0.28 * s), 0.42 * s, st, 8, 0.36 * s)
    mb.cyl((x, y, z + 0.28 * s), (x, y, z + 1.25 * s), 0.13 * s, st, 12)
    mb.cyl((x, y, z + 1.25 * s), (x, y, z + 1.45 * s), 0.25 * s, st, 6, 0.36 * s)
    mb.cyl((x, y, z + 1.45 * s), (x, y, z + 1.95 * s), 0.3 * s, st, 6)
    for k in range(6):
        a = k * math.pi / 3 + math.pi / 6
        mb.box((x + math.cos(a) * 0.3 * s, y + math.sin(a) * 0.3 * s, z + 1.7 * s), (0.16 * s, 0.16 * s, 0.3 * s), MAT['glow'] if glow else MAT['black'], a)
    mb.cyl((x, y, z + 1.95 * s), (x, y, z + 2.3 * s), 0.62 * s, st, 6, 0.1 * s)
    for k in range(6):
        a = k * math.pi / 3
        mb.seg_box((x, y, z + 2.25 * s), (x + math.cos(a) * 0.66 * s, y + math.sin(a) * 0.66 * s, z + 2.02 * s), 0.08 * s, 0.1 * s, st)
    mb.cyl((x, y, z + 2.3 * s), (x, y, z + 2.6 * s), 0.14 * s, st, 8, 0.03 * s)

def build():
    """5 段の部材オブジェクトを作って {'p1': obj, ...} を返す"""
    coll = new_coll('鳳凰堂')
    mbs = {k: MB() for k in ('p1', 'p2', 'p3', 'p4', 'p5')}
    cols = G.columns()
    # ---- p1：基壇・床・束 ------------------------------------------------------
    m = mbs['p1']
    p = G.PODIUM
    m.at(0, 0)
    m.boxr(p['x0'], p['y0'], p['z0'], p['x1'], p['y1'], p['z1'], MAT['stone'])
    for k in range(3):
        z = p['z0'] + 0.35 + k * 0.33
        m.boxr(p['x0'] - 0.02, p['y0'] - 0.02, z, p['x1'] + 0.02, p['y1'] + 0.02, z + 0.025, MAT['stone'])
    # 正面の石段
    for k in range(4):
        m.boxr(p['x1'], -2.0, p['z0'] + 0.3 + 0.2 * k - 0.4, p['x1'] + 1.4 - 0.35 * k, 2.0, p['z0'] + 0.5 + 0.2 * k, MAT['stone'])
    m.boxr(G.MOKO_X[0], G.MOKO_Y[0], G.FLOOR - 0.12, G.MOKO_X[-1], G.MOKO_Y[-1], G.FLOOR, MAT['wood'])
    for x in np.arange(G.MOKO_X[0] + 0.15, G.MOKO_X[-1], 0.3):
        m.at(x, 0)
        m.boxr(x - 0.13, G.MOKO_Y[0] + 0.05, G.FLOOR, x + 0.13, G.MOKO_Y[-1] - 0.05, G.FLOOR + 0.015, MAT['wood'])
    for (x0, x1, y0, y1, dd) in G.wing_segments():
        m.at((x0 + x1) / 2, (y0 + y1) / 2)
        m.boxr(x0 - 0.5, y0 - (0.5 if dd == 'x' else 0), -0.3, x1 + 0.5, y1 + (0.5 if dd == 'x' else 0), G.W_FLOOR - 0.12, MAT['stone'])
        m.boxr(x0 - 0.1, y0, G.W_FLOOR - 0.12, x1 + 0.1, y1, G.W_FLOOR, MAT['wood'])
        if dd == 'y':
            for y in np.arange(y0 + 0.15, y1, 0.3):
                m.at((x0 + x1) / 2, y)
                m.boxr(x0, y - 0.13, G.W_FLOOR, x1, y + 0.13, G.W_FLOOR + 0.015, MAT['wood'])
        else:
            for x in np.arange(x0 + 0.15, x1, 0.3):
                m.at(x, (y0 + y1) / 2)
                m.boxr(x - 0.13, y0, G.W_FLOOR, x + 0.13, y1, G.W_FLOOR + 0.015, MAT['wood'])
    for s in (-1, 1):
        yc = s * G.TOWER['y']
        h = G.TOWER['half']
        m.at(G.WING_X, yc)
        m.boxr(G.WING_X - h - 0.5, yc - h - 0.5, -0.3, G.WING_X + h + 0.5, yc + h + 0.5, G.W_FLOOR - 0.12, MAT['stone'])
        m.boxr(G.WING_X - h, yc - h, G.W_FLOOR - 0.12, G.WING_X + h, yc + h, G.W_FLOOR, MAT['wood'])
    # 翼廊の二階の床（外から見える縁）
    for (x0, x1, y0, y1, dd) in G.wing_segments():
        m.at((x0 + x1) / 2, (y0 + y1) / 2)
        ex = 0.45 if dd == 'y' else 0
        ey = 0.45 if dd == 'x' else 0
        m.boxr(x0 - ex, y0 - ey, G.W_UPPER - 0.1, x1 + ex, y1 + ey, G.W_UPPER + 0.05, MAT['wood'])
    # 尾廊：池を渡る床と束
    t = G.TAIL
    m.at(-12, 0)
    m.boxr(t['x0'], -t['half'] - 0.1, t['floor'] - 0.14, t['x1'], t['half'] + 0.1, t['floor'], MAT['wood'])
    for x in np.arange(t['x0'] + 0.15, t['x1'], 0.3):
        m.at(x, 0)
        m.boxr(x - 0.13, -t['half'], t['floor'], x + 0.13, t['half'], t['floor'] + 0.015, MAT['wood'])
    for x in G.grid_between(t['x0'], t['x1'] - 0.3, 2.4):
        for y in (-t['half'], t['half']):
            m.at(x, y)
            m.cyl((x, y, -1.1), (x, y, t['floor'] - 0.14), 0.13, MAT['wood'], 8)
            m.cyl((x, y, -1.1), (x, y, -0.3), 0.26, MAT['stone'], 8)

    # ---- p2：柱 ----------------------------------------------------------------
    m = mbs['p2']
    RAD = dict(core=0.24, moko=0.19, wing=0.15, tower=0.18, tail=0.13)
    for (x, y, z0, z1, kind) in cols:
        m.at(x, y)
        m.cyl((x, y, z0), (x, y, z1), RAD[kind], MAT['ni'], 12)
        m.cyl((x, y, z0 - 0.02), (x, y, z0 + 0.12), RAD[kind] * 1.35, MAT['stone'], 12)   # 礎石
        m.cyl((x, y, z0 + 0.12), (x, y, z0 + 0.3), RAD[kind] * 1.07, MAT['gold'], 16)      # 根巻金具
        m.cyl((x, y, z1 - 0.28), (x, y, z1 - 0.16), RAD[kind] * 1.06, MAT['gold'], 16)

    # ---- p3：梁・壁・扉・連子窓・組物 ------------------------------------------
    m = mbs['p3']
    # 中堂 身舎：正面3間は扉、側面は連子窓、上は白壁
    cx0, cx1 = G.CORE_X[0], G.CORE_X[-1]
    cy0, cy1 = G.CORE_Y[0], G.CORE_Y[-1]
    zc0, zc1 = G.FLOOR, G.CORE_TOP
    for i in range(3):
        ya, yb = G.CORE_Y[i], G.CORE_Y[i + 1]
        m.at(cx1, (ya + yb) / 2)
        door(m, (cx1, ya), (cx1, yb), zc0, zc0 + 3.6)
        wall(m, (cx1, ya), (cx1, yb), zc0 + 3.6, zc1 - 0.4, MAT['plaster'])
        m.at(cx0, (ya + yb) / 2)
        wall(m, (cx0, yb), (cx0, ya), zc0, zc1 - 0.4, MAT['plaster'])
    for side in (cy0, cy1):
        for j in range(2):
            xa, xb = G.CORE_X[j], G.CORE_X[j + 1]
            m.at((xa + xb) / 2, side)
            wall(m, (xa, side), (xb, side), zc0, zc0 + 0.9, MAT['ni'])
            koza(m, (xa + 0.2, side) if side > 0 else (xb - 0.2, side), (xb - 0.2, side) if side > 0 else (xa + 0.2, side), zc0, zc0 + 0.9)
            renji(m, (xa + 0.25, side), (xb - 0.25, side), zc0 + 0.9, zc0 + 2.7)
            wall(m, (xa, side), (xb, side), zc0 + 2.7, zc1 - 0.4, MAT['plaster'])
    for zz in (zc0 + 3.65, zc1 - 0.35, zc1):
        ring_beam(m, cx0, cx1, cy0, cy1, zz, 0.22, 0.24, MAT['ni'])
    for (x, y, z0, z1, kind) in cols:
        if kind == 'core':
            m.at(x, y)
            kumimono(m, x, y, zc1, (1 if x > 0 else (-1 if x < 0 else 0), 1 if y > 0 else -1), 1.1)
    for i in range(3):
        ym = (G.CORE_Y[i] + G.CORE_Y[i + 1]) / 2
        for xx in (cx1, cx0):
            m.at(xx, ym)
            kaerumata(m, (xx + (0.02 if xx > 0 else -0.02), ym, zc1 + 0.12), (0, 1, 0), 0.95, 0.46, 0.12)
    for side in (cy0, cy1):
        for j in range(2):
            xm = (G.CORE_X[j] + G.CORE_X[j + 1]) / 2
            m.at(xm, side)
            kaerumata(m, (xm, side, zc1 + 0.12), (1, 0, 0), 0.95, 0.46, 0.12)
    # 中堂 裳階：頭貫と組物
    mx0, mx1, my0, my1 = G.MOKO_X[0], G.MOKO_X[-1], G.MOKO_Y[0], G.MOKO_Y[-1]
    ring_beam(m, mx0, mx1, my0, my1, G.MOKO['top'] - 0.1, 0.2, 0.22, MAT['ni'])
    ring_beam(m, mx0, mx1, my0, my1, G.MOKO['top'] - 0.55, 0.14, 0.16, MAT['ni'])
    for (x, y, z0, z1, kind) in cols:
        if kind == 'moko':
            m.at(x, y)
            kumimono(m, x, y, G.MOKO['top'] - 0.25, (1 if x >= mx1 else (-1 if x <= mx0 else 0), 1 if y >= my1 else (-1 if y <= my0 else 0)), 0.55)
    for i in range(len(G.MOKO_Y) - 1):
        ym = (G.MOKO_Y[i] + G.MOKO_Y[i + 1]) / 2
        m.at(mx1, ym)
        kaerumata(m, (mx1 + 0.02, ym, G.MOKO['top'] - 0.1), (0, 1, 0), 0.7, 0.3, 0.1)
    # 翼廊：頭貫・腰長押・二階の下の貫
    for (x0, x1, y0, y1, dd) in G.wing_segments():
        for zz in (G.W_UPPER - 0.25, G.W_TOP - 0.1, G.W_FLOOR + 2.4):
            ring_beam(m, x0, x1, y0, y1, zz, 0.16, 0.18, MAT['ni'])
        for (x, y, z0, z1, kind) in cols:
            if kind == 'wing' and x0 - 0.01 <= x <= x1 + 0.01 and y0 - 0.01 <= y <= y1 + 0.01:
                m.at(x, y)
                out = ((1 if x >= x1 - 0.01 else -1), 0) if dd == 'y' else (0, (1 if y >= y1 - 0.01 else -1))
                kumimono(m, x, y, G.W_TOP - 0.2, out, 0.45)
        if dd == 'y':
            for y in G.grid_between(y0, y1, G.BAY_W)[:-1]:
                for xx in (x0, x1):
                    m.at(xx, y + G.BAY_W / 2)
                    kaerumata(m, (xx, y + G.BAY_W / 2, G.W_TOP - 0.05), (0, 1, 0), 0.6, 0.26, 0.09)
        else:
            for x in G.grid_between(x0, x1, G.BAY_W)[:-1]:
                for yy in (y0, y1):
                    m.at(x + G.BAY_W / 2, yy)
                    kaerumata(m, (x + G.BAY_W / 2, yy, G.W_TOP - 0.05), (1, 0, 0), 0.6, 0.26, 0.09)
    # 隅楼：白壁と連子窓、二段の頭貫
    for s in (-1, 1):
        yc = s * G.TOWER['y']
        h = G.TOWER['half']
        x0, x1, y0, y1 = G.WING_X - h, G.WING_X + h, yc - h, yc + h
        for zz in (G.W_UPPER - 0.25, G.W_TOP - 0.1, G.T_ROOF['eave'] - 0.35):
            ring_beam(m, x0, x1, y0, y1, zz, 0.18, 0.2, MAT['ni'])
        for (a, c) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            m.at((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
            wall(m, a, c, G.W_TOP, G.T_ROOF['eave'] - 0.35, MAT['plaster'])
            aa = Vector(a) + (Vector(c) - Vector(a)) * 0.2
            cc = Vector(a) + (Vector(c) - Vector(a)) * 0.8
            renji(m, tuple(aa), tuple(cc), G.W_TOP + 0.35, G.T_ROOF['eave'] - 0.8)
        for sx in (-1, 1):
            for sy in (-1, 1):
                m.at(G.WING_X + sx * h, yc + sy * h)
                kumimono(m, G.WING_X + sx * h, yc + sy * h, G.T_ROOF['eave'] - 0.45, (sx, sy), 0.55)
    # 尾廊の頭貫
    ring_beam(m, t['x0'], t['x1'], -t['half'], t['half'], t['top'] - 0.1, 0.15, 0.17, MAT['ni'])
    ring_beam(m, t['x0'], t['x1'], -t['half'], t['half'], t['floor'] + 0.8, 0.1, 0.12, MAT['ni'])

    # ---- p4：屋根 --------------------------------------------------------------
    m = mbs['p4']
    m.at(0, 0, jit=0.0)
    # 裳階の屋根（身舎の壁に取りつく片流れの輪）
    roof_at(m, 0, 0, (mx1 - mx0) / 2, (my1 - my0) / 2, dict(eave=G.MOKO['eave'], over=G.MOKO['over'], lift=G.MOKO['lift'], top=5.25),
            cx1 + 0.25, cy1 + 0.25, thick=0.22, n_side=40, n_t=8)
    # 正面中央の持ち上がった裳階：格子の窓と、その上の小屋根
    m.set_ord(0.08)
    yc0, yc1 = G.CORE_Y[1], G.CORE_Y[2]
    mbw = mbs['p3']
    mbw.set_ord(0.05)
    for zz in (G.MOKO['top'] + 0.05, G.MOKO['top'] + 1.35):
        mbw.seg_box((mx1 - 0.1, yc0 - 0.3, zz), (mx1 - 0.1, yc1 + 0.3, zz), 0.16, 0.18, MAT['ni'])
    for y in (yc0, yc1):
        mbw.cyl((mx1 - 0.1, y, G.MOKO['top'] - 0.2), (mx1 - 0.1, y, G.MOKO['top'] + 1.5), 0.16, MAT['ni'], 12)
    renji(mbw, (mx1 - 0.1, yc0 + 0.15), (mx1 - 0.1, yc1 - 0.15), G.MOKO['top'] + 0.12, G.MOKO['top'] + 1.28, n=18)
    roof_at(m, mx1 - 0.6, 0, 0.7, (yc1 - yc0) / 2 + 0.2, dict(eave=G.MOKO['top'] + 1.65, over=0.9, lift=0.25, top=G.MOKO['top'] + 2.5),
            0.7 + 0.9, 0.08, thick=0.18, n_side=20, n_t=6, ridge_w=0.2)
    # 大屋根
    m.at(0, 0, jit=0.0)
    m.set_ord(0.12)
    roof_at(m, 0, 0, cx1, cy1, G.ROOF, 0.15, G.RIDGE_HALF, thick=0.34, n_side=44, n_t=16)
    # 大棟・破風
    # 大棟：熨斗瓦を段々に積み、上に丸い冠瓦
    zt = G.ROOF['top'] - 0.1
    for k in range(7):
        w = 0.34 - 0.012 * k
        m.boxr(-w, -G.RIDGE_HALF - 0.3, zt, w, G.RIDGE_HALF + 0.3, zt + 0.07, MAT['tile'])
        m.boxr(-w + 0.03, -G.RIDGE_HALF - 0.28, zt + 0.07, w - 0.03, G.RIDGE_HALF + 0.28, zt + 0.085, MAT['black'])
        zt += 0.085
    m.cyl((0, -G.RIDGE_HALF - 0.32, zt + 0.05), (0, G.RIDGE_HALF + 0.32, zt + 0.05), 0.13, MAT['tile'], 12)
    for s_ in (-1, 1):
        m.box((0, s_ * (G.RIDGE_HALF + 0.35), zt - 0.2), (0.75, 0.16, 0.9), MAT['tile'])   # 鬼瓦
    for s in (-1, 1):
        # 入母屋の妻（三角の破風板と白い妻壁）
        y = s * (G.RIDGE_HALF - 0.1)
        zb = G.ROOF['eave'] + (G.ROOF['top'] - G.ROOF['eave']) * 0.45
        tri = [m.add_v((-2.2, y, zb)), m.add_v((2.2, y, zb)), m.add_v((0, y, G.ROOF['top']))]
        m.face(tri if s > 0 else list(reversed(tri)), MAT['plaster'])
        for sx in (-1, 1):
            m.seg_box((sx * 2.5, y + s * 0.05, zb - 0.1), (0, y + s * 0.05, G.ROOF['top'] + 0.15), 0.12, 0.35, MAT['ni'])
        m.box((0, y + s * 0.08, G.ROOF['top'] - 0.25), (0.4, 0.06, 0.4), MAT['gold'])
    # 翼廊・隅楼・尾廊の屋根
    for (x0, x1, y0, y1, dd) in G.wing_segments():
        m.at((x0 + x1) / 2, (y0 + y1) / 2, jit=0.02)
        hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
        if dd == 'y':
            roof_at(m, (x0 + x1) / 2, (y0 + y1) / 2, hx, hy, G.W_ROOF, 0.08, hy + 0.35, thick=0.2, n_side=34, n_t=7)
        else:
            roof_at(m, (x0 + x1) / 2, (y0 + y1) / 2, hx, hy, G.W_ROOF, hx + 0.35, 0.08, thick=0.2, n_side=34, n_t=7)
    for s in (-1, 1):
        yc = s * G.TOWER['y']
        m.at(G.WING_X, yc, jit=0.02)
        roof_at(m, G.WING_X, yc, G.TOWER['half'], G.TOWER['half'], G.T_ROOF, 0.12, 0.12, thick=0.24, n_side=18, n_t=9)
        m.cyl((G.WING_X, yc, G.T_ROOF['top'] - 0.1), (G.WING_X, yc, G.T_ROOF['top'] + 0.35), 0.22, MAT['gold'], 12, 0.12)
        m.cyl((G.WING_X, yc, G.T_ROOF['top'] + 0.35), (G.WING_X, yc, G.T_ROOF['top'] + 0.95), 0.05, MAT['gold'], 8)
    m.at(-15, 0, jit=0.02)
    roof_at(m, (t['x0'] + t['x1']) / 2, 0, (t['x1'] - t['x0']) / 2, t['half'], G.TAIL_ROOF, (t['x1'] - t['x0']) / 2 + 0.3, 0.08,
            thick=0.18, n_side=34, n_t=6)

    # ---- p5：高欄・鳳凰・灯籠・反橋 --------------------------------------------
    m = mbs['p5']
    for (x0, x1, y0, y1, dd) in G.wing_segments():
        if dd == 'y':
            for xx in (x0 - 0.4, x1 + 0.4):
                railing(m, [(xx, y0), (xx, y1)], G.W_UPPER + 0.05, 0.75)
        else:
            for yy in (y0 - 0.4, y1 + 0.4):
                railing(m, [(x0, yy), (x1, yy)], G.W_UPPER + 0.05, 0.75)
    railing(m, [(t['x0'], -t['half'] - 0.1), (t['x1'], -t['half'] - 0.1)], t['floor'], 0.6)
    railing(m, [(t['x0'], t['half'] + 0.1), (t['x1'], t['half'] + 0.1)], t['floor'], 0.6)
    for (x, y, z) in G.PHOENIX:
        m.at(0, 0, jit=0.0)
        m.set_ord(0.5)
        # 南北の鳳凰は向かい合う
        phoenix(m, x, y, z + 0.6, -math.pi / 2 if y > 0 else math.pi / 2)

    lantern(m, *G.LANTERN_FRONT, 0.35, 1.0)
    # 翼廊の軒の釣灯籠（夕方に灯る）
    for (x0, x1, y0, y1, dd) in G.wing_segments():
        if dd == 'y':
            for y in G.grid_between(y0, y1, G.BAY_W)[:-1]:
                yy = y + G.BAY_W / 2
                m.at(x1 + 0.5, yy)
                m.cyl((x1 + 0.5, yy, G.W_UPPER - 0.4), (x1 + 0.5, yy, G.W_UPPER - 0.9), 0.14, MAT['glow'], 6)
                m.cyl((x1 + 0.5, yy, G.W_UPPER - 0.35), (x1 + 0.5, yy, G.W_UPPER - 0.4), 0.2, MAT['gold'], 6)
        else:
            for x in G.grid_between(x0, x1, G.BAY_W)[:-1]:
                xx = x + G.BAY_W / 2
                for yy in (y0 - 0.5, y1 + 0.5):
                    m.at(xx, yy)
                    m.cyl((xx, yy, G.W_UPPER - 0.4), (xx, yy, G.W_UPPER - 0.9), 0.14, MAT['glow'], 6)
                    m.cyl((xx, yy, G.W_UPPER - 0.35), (xx, yy, G.W_UPPER - 0.4), 0.2, MAT['gold'], 6)
    for y in G.MOKO_Y[:-1]:
        yy = (y + G.MOKO_Y[G.MOKO_Y.index(y) + 1]) / 2
        m.at(mx1 + 0.6, yy)
        m.cyl((mx1 + 0.7, yy, G.MOKO['top'] - 0.6), (mx1 + 0.7, yy, G.MOKO['top'] - 1.15), 0.16, MAT['glow'], 6)
    # 反橋
    br = G.BRIDGE
    m.at(br['x'], (br['y0'] + br['y1']) / 2)
    prev = None
    n = 16
    for i in range(n + 1):
        u = i / n
        y = br['y0'] + (br['y1'] - br['y0']) * u
        z = 0.5 + br['rise'] * math.sin(math.pi * u)
        if prev:
            m.seg_box((br['x'], prev[0], prev[1]), (br['x'], y, z), br['w'], 0.16, MAT['wood'], up=(1, 0, 0))
            for sx in (-1, 1):
                xx = br['x'] + sx * br['w'] / 2
                m.seg_box((xx, prev[0], prev[1] + 0.75), (xx, y, z + 0.75), 0.09, 0.09, MAT['ni'], up=(1, 0, 0))
                m.seg_box((xx, prev[0], prev[1] + 0.35), (xx, y, z + 0.35), 0.06, 0.06, MAT['ni'], up=(1, 0, 0))
        for sx in (-1, 1):
            xx = br['x'] + sx * br['w'] / 2
            m.seg_box((xx, y, z), (xx, y, z + 0.8), 0.09, 0.09, MAT['ni'])
        if i % 4 == 0:
            m.cyl((br['x'], y, -1.0), (br['x'], y, z - 0.08), 0.12, MAT['wood'], 8)
        prev = (y, z)

    PHASE_OBJ = {}
    for k, mb_ in mbs.items():
        ob = mb_.build('鳳凰堂_' + k, coll)
        ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
        ob.data.set_sharp_from_angle(angle=math.radians(40))     # 40° より鋭い辺だけ角を立てる
        if k in ('p1', 'p2', 'p3', 'p5'):
            bv = ob.modifiers.new('面取り', 'BEVEL')
            bv.width = 0.012
            bv.segments = 2
            bv.limit_method = 'ANGLE'
            bv.angle_limit = math.radians(50)
            bv.harden_normals = False
        ob['prog'] = -0.2
        f0, f1 = T[k]
        ob.keyframe_insert('["prog"]', frame=1)
        ob.keyframe_insert('["prog"]', frame=f0)
        ob['prog'] = 1.08
        ob.keyframe_insert('["prog"]', frame=f1)
        PHASE_OBJ[k] = ob
        print('phase', k, len(ob.data.vertices), 'verts')

    # 灯りは夕方に点く
    g0, g1 = T['lights']
    GLOW['bsdf'].inputs['Emission Strength'].default_value = 0.0
    GLOW['bsdf'].inputs['Emission Strength'].keyframe_insert('default_value', frame=g0)
    GLOW['bsdf'].inputs['Emission Strength'].default_value = 3.0
    GLOW['bsdf'].inputs['Emission Strength'].keyframe_insert('default_value', frame=g1)
    return PHASE_OBJ
