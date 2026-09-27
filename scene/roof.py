"""照り屋根：軒の反り・丸瓦の列・軒瓦・隅棟と鬼瓦・二軒の垂木・隅木。"""
import math

from mathutils import Vector

import geometry as G
from .materials import MAT


def roof_z(t, frac, r):
    return r['eave'] + G.eave_lift(frac, r['lift']) * (1 - t) ** 2 + (r['top'] - r['eave']) * G.roof_profile(t)


def roof_ring(hx, hy, n_side):
    """矩形の外周点列と、各点の辺中央からの比 frac"""
    pts = []
    for side in range(4):
        for k in range(n_side):
            s = -1 + 2 * k / n_side
            if side == 0:
                p = (s * hx, -hy)
            elif side == 1:
                p = (hx, s * hy)
            elif side == 2:
                p = (-s * hx, hy)
            else:
                p = (-hx, -s * hy)
            pts.append((p, abs(s)))
    return pts


def build_roof(mb, half_x, half_y, r, top_hx, top_hy, thick=0.28, n_side=36, n_t=14, tile_w=0.13, ridge_w=0.34):
    Ax, Ay = half_x + r['over'], half_y + r['over']
    top_rows, bot_rows = [], []
    ring0 = roof_ring(1, 1, n_side)
    for i, ((ux, uy), frac) in enumerate(ring0):
        col_t, col_b = [], []
        for j in range(n_t + 1):
            t = j / n_t
            hx = Ax + (top_hx - Ax) * t
            hy = Ay + (top_hy - Ay) * t
            z = roof_z(t, frac, r)
            col_t.append((ux * hx, uy * hy, z))
            col_b.append((ux * hx, uy * hy, z - thick * (1 - 0.6 * t) - 0.02))
        top_rows.append(col_t)
        bot_rows.append(col_b)
    per = 2 * (Ax + Ay) * 2
    mb.grid(top_rows, MAT['tile'], closed_u=True,
            uv=lambda i, j: (i / len(ring0) * per / 1.0, j / n_t * 5.0))
    mb.grid([list(reversed(c)) for c in bot_rows], MAT['ni'], closed_u=True)
    # 丸瓦の列：半分埋まった円筒を流れに沿って。軒先には軒丸瓦（円盤）と軒平瓦
    nring = len(ring0)
    for side in range(4):
        A_ = Ax if side % 2 == 0 else Ay
        spacing = 2 * A_ / n_side
        step = max(1, round(0.3 / spacing))
        for k in range(0, n_side, step):
            i = side * n_side + k
            if k == 0:
                continue
            col = top_rows[i]
            rr_ = min(0.075, spacing * step * 0.3)
            for j in range(len(col) - 1):
                a0 = Vector(col[j]) + Vector((0, 0, rr_ * 0.35))
                a1 = Vector(col[j + 1]) + Vector((0, 0, rr_ * 0.35))
                mb.cyl(tuple(a0), tuple(a1), rr_, MAT['tile'], 8)
            p0 = Vector(col[0])
            tng = Vector(top_rows[(i + 1) % nring][0]) - Vector(top_rows[i - 1][0])
            outw = Vector((tng.y, -tng.x, 0)).normalized()
            if outw.dot(Vector((p0.x, p0.y, 0))) < 0:
                outw = -outw
            c0 = p0 + Vector((0, 0, rr_ * 0.2))
            mb.cyl(tuple(c0), tuple(c0 + outw * 0.035), rr_ * 1.12, MAT['tile'], 16)
            mb.cyl(tuple(c0 + outw * 0.035), tuple(c0 + outw * 0.045), rr_ * 0.45, MAT['tile'], 12, rr_ * 0.3)
    # 隅棟：四隅の稜線に熨斗瓦を積み、下端に鬼瓦
    if top_hx < Ax - 0.3 and top_hy < Ay - 0.3:
        for side in range(4):
            col = top_rows[side * n_side]
            for j in range(len(col) - 1):
                a0 = Vector(col[j]) + Vector((0, 0, 0.12))
                a1 = Vector(col[j + 1]) + Vector((0, 0, 0.12))
                mb.seg_box(tuple(a0), tuple(a1), ridge_w, ridge_w * 0.8, MAT['tile'])
                mb.cyl(tuple(a0 + Vector((0, 0, ridge_w * 0.45))), tuple(a1 + Vector((0, 0, ridge_w * 0.45))), ridge_w * 0.28, MAT['tile'], 8)
            p0 = Vector(col[1]) + Vector((0, 0, 0.2))
            mb.box(tuple(p0), (ridge_w * 0.9, ridge_w * 0.5, ridge_w * 1.2), MAT['tile'], math.atan2(p0.y, p0.x) + math.pi / 2)
            mb.cyl(tuple(p0 + Vector((0, 0, ridge_w * 0.6))), tuple(p0 + Vector((0, 0, ridge_w * 0.95))), ridge_w * 0.2, MAT['tile'], 10, ridge_w * 0.05)
    # 軒先（広小舞・茅負）の縁
    edge = [[bot_rows[i][0], top_rows[i][0]] for i in range(len(ring0))]
    mb.grid([[e[0], e[1]] for e in edge], MAT['ni'], closed_u=True)
    # 軒先を厚く見せる白木の茅負
    for i in range(len(ring0)):
        a = Vector(top_rows[i][0])
        b = Vector(top_rows[(i + 1) % len(ring0)][0])
        mb.seg_box(a + Vector((0, 0, -0.12)), b + Vector((0, 0, -0.12)), 0.14, 0.2, MAT['ni'])
    # 垂木
    for side in range(4):
        along = Ax if side % 2 == 0 else Ay
        wall = half_y if side % 2 == 0 else half_x
        outer = Ay if side % 2 == 0 else Ax
        n = int(along * 2 / 0.32)
        for k in range(n + 1):
            s = -along + 2 * along * k / n
            if abs(s) > along - 0.2:
                continue
            d0 = max(wall, abs(s) - (along - outer)) if abs(s) > (along - (outer - wall)) else wall
            d0 = max(d0, wall)
            if d0 >= outer - 0.15:
                continue
            def rpt(d, dz=0.0):
                t = max(0.0, min(1.0, (outer - d) / max(0.3, outer - (top_hy if side % 2 == 0 else top_hx))))
                frac = abs(s) / along
                z = roof_z(t, frac, r) - thick * (1 - 0.6 * t) - 0.09 + dz
                if side == 0:
                    return (s, -d, z)
                if side == 1:
                    return (d, s, z)
                if side == 2:
                    return (-s, d, z)
                return (-d, -s, z)
            # 地垂木（奥）と飛檐垂木（軒先）の二軒
            p0, p1 = rpt(d0 - 0.2, -0.18), rpt(outer - 0.75, -0.2)
            mb.seg_box(p0, p1, 0.09, 0.11, MAT['ni'])
            dv = (Vector(p1) - Vector(p0)).normalized()
            mb.seg_box(p1, tuple(Vector(p1) + dv * 0.03), 0.1, 0.12, MAT['ochre'])
            f0_, f1_ = rpt(outer - 1.3, -0.02), rpt(outer - 0.14, -0.02)
            mb.seg_box(f0_, f1_, 0.08, 0.09, MAT['ni'])
            dv2 = (Vector(f1_) - Vector(f0_)).normalized()
            mb.seg_box(f1_, tuple(Vector(f1_) + dv2 * 0.03), 0.09, 0.1, MAT['ochre'])
    # 隅木
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        pts = []
        for t in (0.0, 0.6):
            hx = Ax + (top_hx - Ax) * t
            hy = Ay + (top_hy - Ay) * t
            z = roof_z(t, 1.0, r) - thick - 0.05
            pts.append((sx * hx, sy * hy, z))
        mb.seg_box(pts[0], pts[1], 0.16, 0.2, MAT['ni'])
