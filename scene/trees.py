"""樹木：枝ぶりを再帰で生やし、葉を 1 枚ずつ（6 頂点の葉）付けた原型を作って、ジオメトリノードで並べる。
近景は詳細な原型（1 本 2〜5 万面）、山の森は葉を大きくした軽い原型を約 1 万本。
"""
import math
import random

import bpy
import numpy as np
from mathutils import Vector

import geometry as G
from .common import link, new_coll, mat_new, out_node, N, L, principled
from .materials import mat_wood
from .terrain import NEAR, height, near_height, poly_sdist

# build() で中身が入る
BARK = {}
LEAF = {}
_PROTO = {}     # 原型を入れるコレクション

# 近景の木を置かないカメラの通り道（camera.py の経路に合わせる）
CAM_PATH = [(40, -36), (50, -20), (54, 0), (115, 0)]


def mat_bark(name, c0, c1):
    return mat_wood(name, c0, c1, rough=0.9, reveal=False, grain=6.0)


def mat_leaf(name, c0, c1, trans=0.35):
    m, nt = mat_new(name)
    b_ = principled(nt, **{'Roughness': 0.45, 'Specular IOR Level': 0.45})
    att = N(nt, 'ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='lv')
    oi = N(nt, 'ShaderNodeObjectInfo')
    mixv = N(nt, 'ShaderNodeMix', data_type='FLOAT', inputs={'Factor': 0.4})
    L(nt, att.outputs['Fac'], mixv.inputs[2])
    L(nt, oi.outputs['Random'], mixv.inputs[3])
    cr = N(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (*c0, 1)
    cr.color_ramp.elements[1].color = (*c1, 1)
    L(nt, mixv.outputs[0], cr.inputs[0])
    L(nt, cr.outputs[0], b_.inputs['Base Color'])
    tr = N(nt, 'ShaderNodeBsdfTranslucent')
    hs = N(nt, 'ShaderNodeHueSaturation', inputs={'Value': 1.4, 'Saturation': 1.2})
    L(nt, cr.outputs[0], hs.inputs['Color'])
    L(nt, hs.outputs[0], tr.inputs['Color'])
    ms = N(nt, 'ShaderNodeMixShader', inputs={0: trans})
    L(nt, b_.outputs[0], ms.inputs[1])
    L(nt, tr.outputs[0], ms.inputs[2])
    L(nt, ms.outputs[0], out_node(nt).inputs['Surface'])
    return m


class TreeMB:
    def __init__(self):
        self.v, self.f, self.mi, self.lv = [], [], [], []

    def cyl(self, a, c, r0, r1, seg, mi):
        a, c = Vector(a), Vector(c)
        d = (c - a)
        if d.length < 1e-5:
            return
        d.normalize()
        u = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(u).normalized()
        y = d.cross(x).normalized()
        base = len(self.v)
        for p, r in ((a, r0), (c, r1)):
            for i in range(seg):
                t = 2 * math.pi * i / seg
                self.v.append(tuple(p + (x * math.cos(t) + y * math.sin(t)) * r))
        for i in range(seg):
            j = (i + 1) % seg
            self.f.append((base + i, base + j, base + seg + j, base + seg + i))
            self.mi.append(mi)
            self.lv.append(0.0)

    def leaf(self, p, d, up, size, mi, shape='oval'):
        """葉1枚：葉柄の付け根 p、向き d。6頂点の楕円葉を中肋で少し折る"""
        d = Vector(d).normalized()
        side = d.cross(Vector(up)).normalized()
        if side.length < 0.1:
            side = d.orthogonal().normalized()
        nrm = side.cross(d).normalized()
        L_ = size
        W_ = size * (0.42 if shape == 'oval' else 0.16)
        pts = [p, p + d * L_ * 0.25 + side * W_ * 0.8 + nrm * W_ * 0.15, p + d * L_ * 0.65 + side * W_ + nrm * W_ * 0.12,
               p + d * L_, p + d * L_ * 0.65 - side * W_ + nrm * W_ * 0.12, p + d * L_ * 0.25 - side * W_ * 0.8 + nrm * W_ * 0.15]
        base = len(self.v)
        self.v += [tuple(q) for q in pts]
        lv = random.random()
        self.f.append((base, base + 1, base + 2, base + 3))
        self.f.append((base, base + 3, base + 4, base + 5))
        self.mi += [mi, mi]
        self.lv += [lv, lv]

    def build(self, name, mats):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in mats:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', self.mi)
        at = me.attributes.new('lv', 'FLOAT', 'FACE')
        at.data.foreach_set('value', self.lv)
        me.update()
        ob = bpy.data.objects.new(name, me)
        link(ob, _PROTO['coll'])
        return ob


def broadleaf(name, leafmat, height=9.0, spread=4.0, leaves_per_twig=26, levels=(5, 4, 5), leaf_size=0.13,
              seed=0, lod=False):
    rr = random.Random(seed)
    tb = TreeMB()
    trunk_h = height * rr.uniform(0.3, 0.4)
    lean = Vector((rr.uniform(-0.15, 0.15), rr.uniform(-0.15, 0.15), 1)).normalized()
    top = Vector((0, 0, 0)) + lean * trunk_h
    tb.cyl((0, 0, -0.3), top, 0.28 * height / 9, 0.2 * height / 9, 8 if not lod else 5, 0)
    crown_c = Vector((0, 0, height * 0.62))

    def branch(p, d, length, radius, level):
        segs = 3 if not lod else 2
        pts = [p]
        dd = d.copy()
        for i in range(segs):
            dd = (dd + Vector((rr.uniform(-0.3, 0.3), rr.uniform(-0.3, 0.3), rr.uniform(-0.1, 0.25)))).normalized()
            pts.append(pts[-1] + dd * (length / segs))
        for i in range(segs):
            r0 = radius * (1 - 0.5 * i / segs)
            tb.cyl(pts[i], pts[i + 1], r0, r0 * 0.75, 6 if (level == 0 and not lod) else 4, 0)
        if level + 1 < len(levels):
            n = levels[level + 1]
            for k in range(n):
                t = 0.35 + 0.65 * (k + rr.random()) / n
                idx = min(segs - 1, int(t * segs))
                q = pts[idx].lerp(pts[idx + 1], t * segs - idx)
                nd = (dd + Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-0.2, 0.9)))).normalized()
                # 樹冠の外へ向かう
                out = (q - crown_c)
                out.z *= 0.6
                if out.length > 0:
                    nd = (nd + out.normalized() * 0.7).normalized()
                branch(q, nd, length * rr.uniform(0.5, 0.65), radius * 0.55, level + 1)
        else:
            # 葉：小枝の先に密に
            for k in range(leaves_per_twig):
                t = rr.uniform(0.2, 1.0)
                idx = min(segs - 1, int(t * segs))
                q = pts[idx].lerp(pts[idx + 1], t * segs - idx)
                ld = (dd * 0.6 + Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-0.4, 0.8)))).normalized()
                sz = leaf_size * rr.uniform(0.75, 1.25)
                q2 = q + Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-1, 1))) * (0.3 if not lod else 0.6)
                tb.leaf(q2, ld, (0, 0, 1), sz, 1)

    n0 = levels[0]
    for k in range(n0):
        a = 2 * math.pi * (k + rr.random() * 0.6) / n0
        d = Vector((math.cos(a) * 0.8, math.sin(a) * 0.8, rr.uniform(0.6, 1.2))).normalized()
        branch(top, d, spread * rr.uniform(0.8, 1.05), 0.14 * height / 9, 0)
    # 真ん中の主幹の延長
    branch(top, Vector((0, 0, 1)), height * 0.45, 0.13 * height / 9, 0)
    return tb.build(name, [BARK['bark'], leafmat])


def pine(name, height=6.0, seed=0, lod=False, tufts_per_pad=110):
    """松：くねった幹、水平に張る枝、雲形の葉の笠。針葉は束（2本ずつの細い葉）"""
    rr = random.Random(seed)
    tb = TreeMB()
    pts = [Vector((0, 0, -0.3))]
    d = Vector((rr.uniform(-0.3, 0.3), rr.uniform(-0.3, 0.3), 1)).normalized()
    for i in range(7):
        d = (d + Vector((rr.uniform(-0.35, 0.35), rr.uniform(-0.35, 0.35), 0.15))).normalized()
        pts.append(pts[-1] + d * height / 7)
    for i in range(7):
        r0 = 0.25 * height / 6 * (1 - 0.8 * i / 7)
        tb.cyl(pts[i], pts[i + 1], r0, r0 * 0.85, 8 if not lod else 5, 0)
    pads = []
    for i in range(2, 8):
        n = 2 if i < 7 else 1
        for k in range(n):
            a = rr.uniform(0, 2 * math.pi)
            L_ = height * rr.uniform(0.25, 0.45) * (1.2 - i / 8)
            q = pts[i]
            e = q + Vector((math.cos(a) * L_, math.sin(a) * L_, rr.uniform(-0.3, 0.4)))
            mid = q.lerp(e, 0.5) + Vector((0, 0, rr.uniform(0.1, 0.4)))
            tb.cyl(q, mid, 0.09 * height / 6, 0.06 * height / 6, 5 if not lod else 4, 0)
            tb.cyl(mid, e, 0.06 * height / 6, 0.035 * height / 6, 5 if not lod else 4, 0)
            pads.append((e, rr.uniform(0.9, 1.5) * height / 6))
    pads.append((pts[-1] + Vector((0, 0, 0.2)), 1.1 * height / 6))
    for c, R in pads:
        n = tufts_per_pad if not lod else 10
        for k in range(n):
            # 笠：扁平な楕円体の上面に房
            a = rr.uniform(0, 2 * math.pi)
            rad = R * math.sqrt(rr.random())
            q = c + Vector((math.cos(a) * rad, math.sin(a) * rad, rr.uniform(-0.1, 0.25) * R * (1 - rad / R)))
            tb.cyl(c, q, 0.02, 0.012, 3, 0) if (k % 6 == 0 and not lod) else None
            nn = 14 if not lod else 5
            for j in range(nn):
                th = rr.uniform(0, 2 * math.pi)
                ld = Vector((math.cos(th) * 0.8, math.sin(th) * 0.8, rr.uniform(0.3, 1.0))).normalized()
                tb.leaf(q, ld, (0, 0, 1), rr.uniform(0.15, 0.22) * (1 if not lod else 3.5), 1, shape='needle' if not lod else 'oval')
    return tb.build(name, [BARK['pine'], LEAF['pine']])


def cedar(name, height=16.0, seed=0, lod=True):
    """杉・檜：まっすぐな幹に段々の枝葉（山の常緑針葉樹）"""
    rr = random.Random(seed)
    tb = TreeMB()
    tb.cyl((0, 0, -0.5), (0, 0, height), 0.3 * height / 16, 0.03, 6 if not lod else 4, 0)
    tiers = 14 if not lod else 9
    for i in range(tiers):
        z = height * (0.3 + 0.68 * i / tiers)
        R = height * 0.22 * (1 - (z / height - 0.3) / 0.75) + 0.3
        nb = 6 if not lod else 5
        for k in range(nb):
            a = 2 * math.pi * (k + rr.random() * 0.5) / nb + i
            e = Vector((math.cos(a) * R, math.sin(a) * R, z - R * 0.25))
            tb.cyl((0, 0, z), e, 0.05, 0.02, 3, 0)
            nl = 30 if not lod else 12
            for j in range(nl):
                t = rr.uniform(0.2, 1.0)
                q = Vector((0, 0, z)).lerp(e, t)
                ld = (e - Vector((0, 0, z))).normalized() + Vector((rr.uniform(-0.6, 0.6), rr.uniform(-0.6, 0.6), rr.uniform(-0.5, 0.2)))
                tb.leaf(q, ld, (0, 0, 1), rr.uniform(0.35, 0.55) * (1 if not lod else 1.9), 1)
    return tb.build(name, [BARK['bark'], LEAF['cedar']])


def instancer(name, pts, protos, coll):
    """点群（位置・回転・スケール・種類）から GN でインスタンス"""
    sub = bpy.data.collections.new(name + '_種類')
    _PROTO['coll'].children.link(sub)
    for p_ in protos:
        sub.objects.link(p_)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(pts))
    me.vertices.foreach_set('co', [c for p in pts for c in p[0]])
    at = me.attributes.new('proto', 'INT', 'POINT')
    at.data.foreach_set('value', [p[3] for p in pts])
    at = me.attributes.new('rotz', 'FLOAT', 'POINT')
    at.data.foreach_set('value', [p[1] for p in pts])
    at = me.attributes.new('scl', 'FLOAT', 'POINT')
    at.data.foreach_set('value', [p[2] for p in pts])
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    ng = bpy.data.node_groups.new(name + '_GN', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi_ = ng.nodes.new('NodeGroupInput')
    go_ = ng.nodes.new('NodeGroupOutput')
    m2p = ng.nodes.new('GeometryNodeMeshToPoints')
    ci = ng.nodes.new('GeometryNodeCollectionInfo')
    ci.inputs['Collection'].default_value = sub
    ci.inputs['Separate Children'].default_value = True
    ci.inputs['Reset Children'].default_value = True
    iop = ng.nodes.new('GeometryNodeInstanceOnPoints')
    iop.inputs['Pick Instance'].default_value = True
    na_p = ng.nodes.new('GeometryNodeInputNamedAttribute')
    na_p.data_type = 'INT'
    na_p.inputs['Name'].default_value = 'proto'
    na_r = ng.nodes.new('GeometryNodeInputNamedAttribute')
    na_r.data_type = 'FLOAT'
    na_r.inputs['Name'].default_value = 'rotz'
    na_s = ng.nodes.new('GeometryNodeInputNamedAttribute')
    na_s.data_type = 'FLOAT'
    na_s.inputs['Name'].default_value = 'scl'
    comb = ng.nodes.new('ShaderNodeCombineXYZ')
    e2r = ng.nodes.new('FunctionNodeEulerToRotation')
    ng.links.new(na_r.outputs['Attribute'], comb.inputs['Z'])
    ng.links.new(comb.outputs[0], e2r.inputs[0])
    ng.links.new(gi_.outputs[0], m2p.inputs['Mesh'])
    ng.links.new(m2p.outputs[0], iop.inputs['Points'])
    ng.links.new(ci.outputs[0], iop.inputs['Instance'])
    ng.links.new(na_p.outputs['Attribute'], iop.inputs['Instance Index'])
    ng.links.new(e2r.outputs[0], iop.inputs['Rotation'])
    ng.links.new(na_s.outputs['Attribute'], iop.inputs['Scale'])
    ng.links.new(iop.outputs[0], go_.inputs[0])
    md = ob.modifiers.new('GN', 'NODES')
    md.node_group = ng
    return ob


def near_cam_path(x, y, r):
    for (ax, ay), (bx, by) in zip(CAM_PATH[:-1], CAM_PATH[1:]):
        tt = max(0, min(1, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
        if math.hypot(x - ax - tt * (bx - ax), y - ay - tt * (by - ay)) < r:
            return True
    return False


def build(env_coll):
    """原型の木を作り、近景・中島・山の森に並べる"""
    proto = new_coll('樹木_原型')
    _PROTO['coll'] = proto
    BARK['bark'] = mat_bark('樹皮', (0.05, 0.04, 0.035), (0.16, 0.13, 0.11))
    BARK['pine'] = mat_bark('松の樹皮', (0.045, 0.032, 0.026), (0.12, 0.085, 0.065))
    LEAF.update(
        shii=mat_leaf('葉_椎', (0.02, 0.05, 0.012), (0.07, 0.13, 0.03)),
        kashi=mat_leaf('葉_樫', (0.03, 0.07, 0.02), (0.10, 0.17, 0.045)),
        pine=mat_leaf('葉_松', (0.015, 0.04, 0.015), (0.05, 0.10, 0.03), 0.2),
        cedar=mat_leaf('葉_杉', (0.02, 0.04, 0.018), (0.06, 0.09, 0.035), 0.2),
        momiji_red=mat_leaf('葉_紅葉', (0.35, 0.05, 0.015), (0.75, 0.2, 0.04)),
    )
    PROTO_NEAR = [
        broadleaf('椎_近A', LEAF['shii'], 11, 4.8, 70, (6, 5, 5), 0.24, seed=1),
        broadleaf('樫_近B', LEAF['kashi'], 9, 4.0, 70, (5, 5, 5), 0.22, seed=2),
        broadleaf('椎_近C', LEAF['shii'], 13, 5.5, 70, (6, 5, 5), 0.25, seed=3),
        broadleaf('楓_近', LEAF['momiji_red'], 7, 3.6, 60, (5, 5, 5), 0.18, seed=4),
        pine('松_近A', 7, seed=5),
        pine('松_近B', 9, seed=6),
    ]
    PROTO_FAR = [
        broadleaf('椎_遠A', LEAF['shii'], 11, 4.8, 22, (6, 4, 3), 0.85, seed=11, lod=True),
        broadleaf('樫_遠B', LEAF['kashi'], 10, 4.4, 22, (5, 4, 3), 0.85, seed=12, lod=True),
        broadleaf('椎_遠C', LEAF['shii'], 13, 5.5, 22, (6, 4, 3), 0.9, seed=13, lod=True),
        broadleaf('紅葉_遠', LEAF['momiji_red'], 9, 4.2, 22, (5, 4, 3), 0.8, seed=16, lod=True),
        cedar('杉_遠', 18, seed=14),
    ]
    for ob in PROTO_NEAR + PROTO_FAR:
        ob.location = (0, 0, -500)
    proto.hide_render = True
    proto.hide_viewport = True
    trees = new_coll('樹木', env_coll)

    # 近景：池の外の岸（とくに背後の西）に密に。カメラの通り道と池の中は避ける


    rr = random.Random(99)
    cand = np.array([(rr.uniform(NEAR[0] + 2, NEAR[1] - 2), rr.uniform(NEAR[2] + 2, NEAR[3] - 2)) for _ in range(14000)])
    sd = poly_sdist(cand[:, 0], cand[:, 1], G.POND)
    zc = near_height(cand[:, 0], cand[:, 1])
    near_pts, placed = [], []
    for (x, y), s_, z in zip(cand, sd, zc):
        if s_ > -2.0 or near_cam_path(x, y, 9):
            continue
        dens = 0.8
        if rr.random() > dens:
            continue
        sp = 4.5
        if any((x - px) ** 2 + (y - py) ** 2 < sp * sp for px, py in placed):
            continue
        placed.append((x, y))
        kind = rr.choices([0, 1, 2, 3, 4, 5], weights=[3, 3, 2, 1.3, 1.2, 0.8])[0]
        near_pts.append(((float(x), float(y), float(z)), rr.uniform(0, 6.28), rr.uniform(0.85, 1.3), kind))
    print('near trees', len(near_pts))
    instancer('木_近景', near_pts, PROTO_NEAR, trees)
    # 中島の松（中堂の脇）
    isl = [((9.5, -26), 0.8, 4), ((9.5, 26), 0.85, 5)]
    isl_pts = []
    for (x, y), s_, k in isl:
        z = float(near_height(np.array([x]), np.array([y]))[0])
        isl_pts.append(((x, y, z), rr.uniform(0, 6.28), s_, k))
    instancer('松_中島', isl_pts, PROTO_NEAR, trees)

    # 遠景の森：山並みに常緑広葉樹を多めに密に、ところどころ紅葉
    step = 6.5
    gx = np.arange(-1300, 500, step)
    gy = np.arange(-900, 900, step)
    FX, FY = np.meshgrid(gx, gy)
    FX = FX + np.random.default_rng(1).uniform(-step * 0.45, step * 0.45, FX.shape)
    FY = FY + np.random.default_rng(2).uniform(-step * 0.45, step * 0.45, FY.shape)
    FX, FY = FX.ravel(), FY.ravel()
    outside = ~((FX > NEAR[0]) & (FX < NEAR[1]) & (FY > NEAR[2]) & (FY < NEAR[3]))
    R_ = np.hypot(FX, FY)
    # カメラ（東）から見える西側の扇形
    keep = outside & (R_ < 1100) & (FX < 60) & (np.abs(FY) < 0.9 * np.abs(FX) + 120)
    dens = np.where(R_ < 350, 1.0, np.where(R_ < 700, 0.5, 0.28))
    keep &= np.random.default_rng(3).random(FX.shape) < dens
    FX, FY = FX[keep], FY[keep]
    FZ = height(FX, FY)
    kinds = np.random.default_rng(4).choice(5, size=FX.shape, p=[0.34, 0.3, 0.24, 0.06, 0.06])
    rots = np.random.default_rng(6).uniform(0, 6.28, FX.shape)
    scls = np.random.default_rng(7).uniform(0.85, 1.4, FX.shape) * np.where(R_[keep] > 350, 1.5, 1.0)
    far_pts = [((float(x), float(y), float(z) - 0.3), float(r), float(s_), int(k)) for x, y, z, k, r, s_ in zip(FX, FY, FZ, kinds, rots, scls)]
    print('far trees', len(far_pts))
    instancer('木_遠景', far_pts, PROTO_FAR, trees)
