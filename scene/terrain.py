"""地形：阿字池と中島、岸の森の土台、背後（西）の山並み。池の水面は時間とともに上がる。
高さは numpy の関数で計算し、近景（0.5m 格子）と遠景（12m 格子）の 2 枚のメッシュにする。
"""
import math
import random

import bpy
import numpy as np

import geometry as G
from .common import F_END, T, link, new_coll, sock_ramp, mat_new, out_node, N, L, principled, texcoord
from .materials import mat_plain
from .mesh import MB

NEAR = (-175, 185, -80, 75)      # 近景メッシュの範囲（x0, x1, y0, y1）


def hash2(ix, iy, seed):
    h = np.sin(ix * 127.1 + iy * 311.7 + seed * 74.7) * 43758.5453
    return h - np.floor(h)


def vnoise(x, y, seed=0):
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = hash2(ix, iy, seed)
    b_ = hash2(ix + 1, iy, seed)
    c = hash2(ix, iy + 1, seed)
    d = hash2(ix + 1, iy + 1, seed)
    return (a + (b_ - a) * ux) + ((c + (d - c) * ux) - (a + (b_ - a) * ux)) * uy


def fbm(x, y, octaves=5, seed=0):
    v, amp, f = 0.0, 0.5, 1.0
    for i in range(octaves):
        v = v + amp * (vnoise(x * f, y * f, seed + i * 13) - 0.5)
        f *= 2.03
        amp *= 0.5
    return v


def poly_sdist(px, py, poly):
    """符号付き距離（内側が正）"""
    P = np.array(poly)
    A = P
    B = np.roll(P, -1, axis=0)
    best = np.full(px.shape, 1e9)
    inside = np.zeros(px.shape, bool)
    for (ax, ay), (bx, by) in zip(A, B):
        dx, dy = bx - ax, by - ay
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12), 0, 1)
        d = np.hypot(px - (ax + t * dx), py - (ay + t * dy))
        best = np.minimum(best, d)
        cond = ((ay > py) != (by > py)) & (px < (bx - ax) * (py - ay) / (by - ay + 1e-12) + ax)
        inside ^= cond
    return np.where(inside, best, -best)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)



def grid_mesh(name, xr, yr, step, zfun, coll, lower_rect=None, mat=None):
    xs_ = np.arange(xr[0], xr[1] + 1e-6, step)
    ys_ = np.arange(yr[0], yr[1] + 1e-6, step)
    X, Y = np.meshgrid(xs_, ys_)
    Z = zfun(X, Y)
    if lower_rect is not None:
        x0, x1, y0, y1 = lower_rect
        inside = (X > x0 + step) & (X < x1 - step) & (Y > y0 + step) & (Y < y1 - step)
        Z = np.where(inside, Z - 4.0, Z)
    ny_, nx_ = X.shape
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    idx = np.arange(nx_ * ny_).reshape(ny_, nx_)
    faces = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    me.loops.add(faces.size)
    me.loops.foreach_set('vertex_index', faces.ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set('loop_start', np.arange(0, faces.size, 4))
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', [True] * len(faces))
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    return ob, (X, Y, Z)


def mat_ground():
    m, nt = mat_new('地面')
    b_ = principled(nt, **{'Roughness': 0.9})
    geo = N(nt, 'ShaderNodeNewGeometry')
    sep = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, geo.outputs['Position'], sep.inputs[0])
    v = texcoord(nt, 'Object')
    nz = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 0.35, 'Detail': 10.0, 'Roughness': 0.65})
    L(nt, v, nz.inputs['Vector'])
    nz2 = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 4.0, 'Detail': 8.0})
    L(nt, v, nz2.inputs['Vector'])
    moss = N(nt, 'ShaderNodeValToRGB')
    moss.color_ramp.elements[0].color = (0.02, 0.032, 0.012, 1)
    moss.color_ramp.elements[1].color = (0.06, 0.075, 0.03, 1)
    L(nt, nz.outputs['Fac'], moss.inputs[0])
    mud = N(nt, 'ShaderNodeValToRGB')
    mud.color_ramp.elements[0].color = (0.05, 0.04, 0.03, 1)
    mud.color_ramp.elements[1].color = (0.14, 0.11, 0.08, 1)
    L(nt, nz2.outputs['Fac'], mud.inputs[0])
    # 高さで泥→湿った汀→苔
    zf = N(nt, 'ShaderNodeMapRange', inputs={1: 0.6, 2: 0.95, 3: 0.0, 4: 1.0})
    L(nt, sep.outputs['Z'], zf.inputs[0])
    mix = N(nt, 'ShaderNodeMix', data_type='RGBA')
    L(nt, zf.outputs[0], mix.inputs['Factor'])
    L(nt, mud.outputs[0], mix.inputs[6])
    L(nt, moss.outputs[0], mix.inputs[7])
    L(nt, mix.outputs[2], b_.inputs['Base Color'])
    rough = N(nt, 'ShaderNodeMapRange', inputs={1: 0.0, 2: 0.4, 3: 0.35, 4: 0.95})
    L(nt, sep.outputs['Z'], rough.inputs[0])
    L(nt, rough.outputs[0], b_.inputs['Roughness'])
    bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.35})
    L(nt, nz2.outputs['Fac'], bump.inputs['Height'])
    L(nt, bump.outputs[0], b_.inputs['Normal'])
    L(nt, b_.outputs[0], out_node(nt).inputs['Surface'])
    return m


def mat_mountain():
    m, nt = mat_new('山肌')
    b_ = principled(nt, **{'Roughness': 0.95})
    v = texcoord(nt, 'Object')
    nz = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 0.08, 'Detail': 12.0, 'Roughness': 0.7})
    L(nt, v, nz.inputs['Vector'])
    cr = N(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0.012, 0.022, 0.01, 1)
    cr.color_ramp.elements[1].color = (0.05, 0.07, 0.025, 1)
    L(nt, nz.outputs['Fac'], cr.inputs[0])
    L(nt, cr.outputs[0], b_.inputs['Base Color'])
    vor = N(nt, 'ShaderNodeTexVoronoi', inputs={'Scale': 0.25})
    L(nt, v, vor.inputs['Vector'])
    bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.6, 'Distance': 2.0})
    L(nt, vor.outputs['Distance'], bump.inputs['Height'])
    L(nt, bump.outputs[0], b_.inputs['Normal'])
    L(nt, b_.outputs[0], out_node(nt).inputs['Surface'])
    return m


def azim(x, y):
    return (np.degrees(np.arctan2(x, y)) + 360) % 360


PEAKS = [(-480, -40, 55, 110), (-520, 200, 60, 120), (-460, -300, 90, 150), (-560, 460, 110, 170),
         (-760, -80, 190, 230), (-900, 380, 230, 260), (-650, -520, 170, 220), (-1100, 60, 260, 320),
         (-120, -190, 30, 60), (-130, 170, 28, 60), (160, 420, 70, 150), (120, -460, 60, 150)]


def height(x, y):
    z = 1.0 + 0.08 * fbm(x / 6, y / 6, 3, 1)
    m_ = np.zeros_like(x)
    for (px_, py_, h_, s_) in PEAKS:
        m_ = m_ + h_ * np.exp(-(((x - px_) ** 2 + (y - py_) ** 2) / (2 * s_ * s_)))
    rid = fbm(x / 80, y / 80, 6, 9)
    r = np.hypot(x, y)
    env = smooth(170, 380, r)
    az = azim(x, y)
    notch = 1 - 0.55 * np.exp(-((az - 270) / 12) ** 2)
    z = z + (m_ * (1 + 0.4 * rid) + env * 16 * rid + env * 5 * fbm(x / 20, y / 20, 4, 21)) * env * notch
    # 西の岸の小高い森
    z = z + smooth(-150, -190, x) * (4 + 3 * fbm(x / 25, y / 25, 3, 13))
    return z


def near_height(x, y):
    z = height(x, y)
    sd = poly_sdist(x, y, G.POND)
    bed = -1.0 + 0.3 * fbm(x / 7, y / 7, 5, 3) + 0.1 * fbm(x / 1.5, y / 1.5, 3, 4)
    w = smooth(0.0, 3.0, sd)
    shore = np.where(sd > 0, 0.3 + (bed - 0.3) * w, z + (0.3 - z) * smooth(-1.5, 0.0, sd))
    z = np.where(sd > -1.5, shore, z)
    for isl, top_ in ((G.ISLAND, 0.38),):
        si = poly_sdist(x, y, isl)
        top = top_ + 0.08 * smooth(0, 4, si) + 0.04 * fbm(x, y, 3, 7)
        z = np.where(si > -2.5, np.maximum(z, bed + (top - bed) * smooth(-2.5, 0.2, si)), z)
    return z


def build():
    """地形・洲浜・庭石・水面を作り、環境のコレクションを返す（巻物が消えるまで隠す）"""
    coll = new_coll('環境')
    grid_mesh('地形_近景', NEAR[:2], NEAR[2:], 0.5, near_height, coll, mat=mat_ground())
    grid_mesh('地形_遠景', (-2400, 900), (-1800, 1800), 12.0, height, coll, lower_rect=NEAR, mat=mat_mountain())

    # 洲浜の小石（中島の前）
    M_PEBBLE = mat_plain('洲浜', (0.20, 0.19, 0.175), 0.8, reveal=False, noise=0.3)
    peb = MB()
    rr = random.Random(12)
    for i in range(1800):
        x, y = rr.uniform(7, 15), rr.uniform(-28, 28)
        if G.point_in_poly(x, y, G.ISLAND) and G.dist_to_poly(x, y, G.ISLAND) < 2.6:
            s_ = rr.uniform(0.08, 0.2)
            z = float(near_height(np.array([x]), np.array([y]))[0])
            peb.box((x, y, z + s_ * 0.3), (s_ * 1.3, s_, s_ * 0.7), M_PEBBLE, rr.uniform(0, 3))
    peb.build('洲浜', coll)
    # 庭石
    M_ROCK = mat_plain('庭石', (0.12, 0.11, 0.10), 0.8, reveal=False, noise=0.3)
    for i, (x, y, r) in enumerate(G.ROCKS):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, -0.2 if i < len(G.ROCKS) else 0.1))
        rk = bpy.context.active_object
        rk.name = f'庭石_{i}'
        for c_ in rk.users_collection:
            c_.objects.unlink(rk)
        coll.objects.link(rk)
        rr = random.Random(i)
        for v in rk.data.vertices:
            n = v.co.normalized()
            v.co *= 0.8 + 0.35 * (math.sin(n.x * 5 + i) * math.cos(n.y * 4 + i * 2) * 0.5 + 0.5) + rr.uniform(-0.05, 0.05)
            v.co.z *= 0.7
        rk.rotation_euler = (0, 0, rr.uniform(0, 6))
        rk.data.materials.append(M_ROCK)
        bpy.ops.object.shade_smooth()

    # 水
    water_coll = new_coll('水', coll)
    m, nt = mat_new('池水')
    b_ = principled(nt, **{'Base Color': (0.015, 0.025, 0.03, 1), 'Roughness': 0.02, 'IOR': 1.333, 'Specular IOR Level': 0.5})
    tc = N(nt, 'ShaderNodeTexCoord')
    mp_ = N(nt, 'ShaderNodeMapping', inputs={'Scale': (1.0, 1.0, 1.0)})
    L(nt, tc.outputs['Object'], mp_.inputs['Vector'])
    wn = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 6.0, 'Detail': 5.0, 'Roughness': 0.5})
    wn.noise_dimensions = '4D'
    L(nt, mp_.outputs[0], wn.inputs['Vector'])
    sock_ramp(wn.inputs['W'], [(1, 0.0), (F_END, 5.0)])
    bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.05, 'Distance': 0.02})
    L(nt, wn.outputs['Fac'], bump.inputs['Height'])
    L(nt, bump.outputs[0], b_.inputs['Normal'])
    L(nt, b_.outputs[0], out_node(nt).inputs['Surface'])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(8, 0, -1.3))
    water = bpy.context.active_object
    water.name = '池水'
    water.scale = (370, 150, 1)
    for c_ in water.users_collection:
        c_.objects.unlink(water)
    water_coll.objects.link(water)
    water.data.materials.append(m)
    water.hide_probe_plane = True
    f0, f1 = T['flood']
    water.location.z = -1.3
    water.keyframe_insert('location', frame=f0)
    water.location.z = 0.0
    water.keyframe_insert('location', frame=f1)
    lp = bpy.data.lightprobes.new('映り込み', 'PLANE')
    lpo = bpy.data.objects.new('映り込み', lp)
    link(lpo, water_coll)
    lpo.parent = water
    lpo.location = (0, 0, 0.001)
    lpo.scale = (0.5, 0.5, 1)
    return coll
