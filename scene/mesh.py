"""メッシュを Python で組み立てる道具。部材ごとの実体化の順番（頂点属性 ord）もここで付ける。"""
import math

import bpy
from mathutils import Vector

from .common import link, rnd


class MB:
    """メッシュ組み立て。set_ord() 以降に足した部材の頂点に ord を付ける"""

    def __init__(self):
        self.v, self.f, self.m, self.uv = [], [], [], []
        self.mats = []
        self.vo = []
        self.cur = 0.0

    def _fill(self):
        self.vo.extend([self.cur] * (len(self.v) - len(self.vo)))

    def set_ord(self, o):
        self._fill()
        self.cur = float(o)

    def at(self, x, y, spread=34.0, jit=0.1):
        """位置から ord を決める（中堂から外へ広がる）"""
        self.set_ord(min(1.0, math.hypot(x * 1.2, y) / spread * (1 - jit) + rnd.random() * jit))

    def mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def face(self, idx, mat, uvs=None):
        self.f.append(idx)
        self.m.append(self.mi(mat))
        self.uv.append(uvs or [(0, 0)] * len(idx))

    def add_v(self, p):
        self.v.append(tuple(p))
        return len(self.v) - 1

    def box(self, c, s, mat, rot=0.0):
        cx, cy, cz = c
        sx, sy, sz = s[0] / 2, s[1] / 2, s[2] / 2
        cr, sr = math.cos(rot), math.sin(rot)
        base = len(self.v)
        for dz in (-sz, sz):
            for dx, dy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
                self.v.append((cx + dx * cr - dy * sr, cy + dx * sr + dy * cr, cz + dz))
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.face([base + i for i in q], mat)

    def boxr(self, x0, y0, z0, x1, y1, z1, mat):
        self.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), mat)

    def seg_box(self, p0, p1, w, h, mat, up=(0, 0, 1)):
        a, b = Vector(p0), Vector(p1)
        d = (b - a)
        if d.length < 1e-6:
            return
        d.normalize()
        u = Vector(up)
        if abs(d.dot(u)) > 0.95:
            u = Vector((1, 0, 0))
        x = d.cross(u).normalized() * (w / 2)
        y = x.cross(d).normalized() * (h / 2)
        base = len(self.v)
        for p in (a, b):
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                self.v.append(tuple(p + x * sx + y * sy))
        for q in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            self.face([base + i for i in q], mat)

    def cyl(self, p0, p1, r0, mat, seg=10, r1=None):
        a, b = Vector(p0), Vector(p1)
        d = (b - a).normalized()
        u = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(u).normalized()
        y = d.cross(x).normalized()
        r1 = r0 if r1 is None else r1
        base = len(self.v)
        for p, r in ((a, r0), (b, r1)):
            for i in range(seg):
                t = 2 * math.pi * i / seg
                self.v.append(tuple(p + (x * math.cos(t) + y * math.sin(t)) * r))
        for i in range(seg):
            j = (i + 1) % seg
            self.face([base + i, base + j, base + seg + j, base + seg + i], mat)
        self.face([base + seg - 1 - i for i in range(seg)], mat)
        self.face([base + seg + i for i in range(seg)], mat)

    def grid(self, P, mat, closed_u=False, uv=None):
        nu, nv = len(P), len(P[0])
        idx = [[self.add_v(P[i][j]) for j in range(nv)] for i in range(nu)]
        for i in range(nu - (0 if closed_u else 1)):
            i2 = (i + 1) % nu
            for j in range(nv - 1):
                q = [idx[i][j], idx[i2][j], idx[i2][j + 1], idx[i][j + 1]]
                uvs = [uv(i, j), uv(i + 1, j), uv(i + 1, j + 1), uv(i, j + 1)] if uv else None
                self.face(q, mat, uvs)

    def extrude(self, pts2, thick, origin, ax_u, ax_v, mat, cap_mat=None):
        """2D の輪郭（u,v）を ax_u×ax_v 面に置き、法線方向へ thick だけ押し出す（凹多角形可）"""
        o = Vector(origin)
        u, v = Vector(ax_u).normalized(), Vector(ax_v).normalized()
        w = u.cross(v).normalized()
        n = len(pts2)
        base = len(self.v)
        for sgn in (-0.5, 0.5):
            for (pu, pv) in pts2:
                self.v.append(tuple(o + u * pu + v * pv + w * (thick * sgn)))
        self.face([base + n - 1 - i for i in range(n)], cap_mat or mat)
        self.face([base + n + i for i in range(n)], cap_mat or mat)
        for i in range(n):
            j = (i + 1) % n
            self.face([base + i, base + j, base + n + j, base + n + i], mat)

    def loft(self, loops, mat, cap=True):
        """同じ点数の閉ループを順につなぐ"""
        m_ = len(loops[0])
        base = len(self.v)
        for lp in loops:
            for p in lp:
                self.v.append(tuple(p))
        for k in range(len(loops) - 1):
            for i in range(m_):
                j = (i + 1) % m_
                a0 = base + k * m_
                a1 = base + (k + 1) * m_
                self.face([a0 + i, a0 + j, a1 + j, a1 + i], mat)
        if cap:
            self.face([base + m_ - 1 - i for i in range(m_)], mat)
            last = base + (len(loops) - 1) * m_
            self.face([last + i for i in range(m_)], mat)

    def blade(self, spine, widths, normal_hint, mat, rib=0.25, notch=0.0, thick=0.012):
        """羽根：spine の点列に沿って、幅 widths の刃。中央の軸を盛り上げ、縁を刻む（厚みつき）"""
        n = len(spine)
        rows = []
        for i in range(n):
            p = Vector(spine[i])
            t = (Vector(spine[min(i + 1, n - 1)]) - Vector(spine[max(i - 1, 0)])).normalized()
            side = t.cross(Vector(normal_hint)).normalized()
            if side.length < 0.1:
                side = t.orthogonal().normalized()
            up = side.cross(t).normalized()
            w = widths[i] * (1 + (notch if i % 2 else -notch) * (0 < i < n - 1))
            rows.append((p, side, up, w))
        for sgn in (1, -1):
            base = len(self.v)
            for (p, side, up, w) in rows:
                lift = up * (thick * 0.5 * sgn)
                self.v.append(tuple(p - side * w + lift - up * w * 0.15))
                self.v.append(tuple(p + up * w * rib + lift * 2))
                self.v.append(tuple(p + side * w + lift - up * w * 0.15))
            for i in range(n - 1):
                a0, a1 = base + i * 3, base + (i + 1) * 3
                q1 = [a0, a1, a1 + 1, a0 + 1]
                q2 = [a0 + 1, a1 + 1, a1 + 2, a0 + 2]
                if sgn < 0:
                    q1.reverse()
                    q2.reverse()
                self.face(q1, mat)
                self.face(q2, mat)

    def merge(self, other, offset=(0, 0, 0)):
        other._fill()
        self._fill()
        base = len(self.v)
        ox, oy, oz = offset
        self.v += [(v[0] + ox, v[1] + oy, v[2] + oz) for v in other.v]
        self.vo += other.vo
        for f, mi_, uv in zip(other.f, other.m, other.uv):
            self.face([base + i for i in f], other.mats[mi_], uv)

    def build(self, name, coll=None):
        self._fill()
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', self.m)
        uvl = me.uv_layers.new(name='UVMap')
        flat = [c for f in self.uv for c in f]
        uvl.data.foreach_set('uv', [x for p in flat for x in p])
        at = me.attributes.new('ord', 'FLOAT', 'POINT')
        at.data.foreach_set('value', self.vo)
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        link(ob, coll)
        return ob
