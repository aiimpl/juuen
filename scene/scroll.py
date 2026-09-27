"""巻物：上（西）の軸は固定し、下（東）の軸が転がって紙が広がる。
紙には drawing/make_scroll.py が描いた墨の配置図を貼る。紙は肉付けのあいだ地面として残り、最後に虫食い状に消える。
"""
import os

import bpy

import geometry as G
from .common import BUILD, T, PAPER_Z, link, new_coll, ramp, show_between, mat_new, out_node, N, L, principled
from .materials import mat_wood, mat_plain
from .mesh import MB

SC = G.SCROLL
MX, MY = 0.9, 1.3          # 表装（朱の縁）の幅：x 方向（上下）、y 方向（左右）
X0, X1 = SC['x0'] - MX, SC['x1'] + MX
Y0, Y1 = SC['y0'] - MY, SC['y1'] + MY


def paper_material():
    """和紙（繊維と漉きムラ）＋墨の図＋朱の縁。rod_x より西だけ見え、vanish で虫食い状に消える"""
    m, nt = mat_new('巻物')
    b_ = principled(nt, **{'Roughness': 0.9})
    tc = N(nt, 'ShaderNodeTexCoord')
    geo = N(nt, 'ShaderNodeNewGeometry')
    sepw = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, geo.outputs['Position'], sepw.inputs[0])
    sepuv = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, tc.outputs['UV'], sepuv.inputs[0])
    img = bpy.data.images.load(os.path.join(BUILD, 'tex', 'scroll_ink.png'))
    it = N(nt, 'ShaderNodeTexImage', image=img, extension='CLIP', interpolation='Cubic')
    L(nt, tc.outputs['UV'], it.inputs['Vector'])
    # 和紙：生成り色に繊維と漉きムラ
    fib = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 70.0, 'Detail': 12.0, 'Roughness': 0.7})
    L(nt, tc.outputs['UV'], fib.inputs['Vector'])
    fib2 = N(nt, 'ShaderNodeTexWave', inputs={'Scale': 110.0, 'Distortion': 25.0, 'Detail': 6.0})
    L(nt, tc.outputs['UV'], fib2.inputs['Vector'])
    blot = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 4.0, 'Detail': 3.0})
    L(nt, tc.outputs['UV'], blot.inputs['Vector'])
    pm = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD', inputs={1: 0.35})
    L(nt, fib2.outputs['Fac'], pm.inputs[0])
    L(nt, fib.outputs['Fac'], pm.inputs[2])
    pm2 = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD', inputs={1: 0.4})
    L(nt, blot.outputs['Fac'], pm2.inputs[0])
    L(nt, pm.outputs[0], pm2.inputs[2])
    pc = N(nt, 'ShaderNodeValToRGB')
    pc.color_ramp.elements[0].color = (0.70, 0.62, 0.48, 1)
    pc.color_ramp.elements[1].color = (0.93, 0.88, 0.78, 1)
    pc.color_ramp.elements[0].position = 0.35
    pc.color_ramp.elements[1].position = 1.2
    L(nt, pm2.outputs[0], pc.inputs[0])
    # 本紙の内側か
    inside = N(nt, 'ShaderNodeMath', operation='MULTIPLY')
    cu = N(nt, 'ShaderNodeMath', operation='COMPARE', inputs={1: 0.5, 2: 0.5})
    cv = N(nt, 'ShaderNodeMath', operation='COMPARE', inputs={1: 0.5, 2: 0.5})
    L(nt, sepuv.outputs['X'], cu.inputs[0])
    L(nt, sepuv.outputs['Y'], cv.inputs[0])
    L(nt, cu.outputs[0], inside.inputs[0])
    L(nt, cv.outputs[0], inside.inputs[1])
    paper_ink = N(nt, 'ShaderNodeMix', data_type='RGBA')
    L(nt, it.outputs['Alpha'], paper_ink.inputs['Factor'])
    L(nt, pc.outputs[0], paper_ink.inputs[6])
    L(nt, it.outputs['Color'], paper_ink.inputs[7])
    border = N(nt, 'ShaderNodeMix', data_type='RGBA')
    L(nt, inside.outputs[0], border.inputs['Factor'])
    border.inputs[6].default_value = (0.62, 0.13, 0.05, 1)      # 朱の縁
    L(nt, paper_ink.outputs[2], border.inputs[7])
    L(nt, border.outputs[2], b_.inputs['Base Color'])
    bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.1})
    L(nt, pm.outputs[0], bump.inputs['Height'])
    L(nt, bump.outputs[0], b_.inputs['Normal'])
    # 広がり：rod_x より西だけ見える
    rod = N(nt, 'ShaderNodeAttribute', attribute_type='OBJECT', attribute_name='rod_x')
    vis = N(nt, 'ShaderNodeMath', operation='LESS_THAN')
    L(nt, sepw.outputs['X'], vis.inputs[0])
    L(nt, rod.outputs['Fac'], vis.inputs[1])
    # 消える：虫食い状に
    van = N(nt, 'ShaderNodeAttribute', attribute_type='OBJECT', attribute_name='vanish')
    vn = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 3.0, 'Detail': 6.0})
    L(nt, tc.outputs['UV'], vn.inputs['Vector'])
    vth = N(nt, 'ShaderNodeMath', operation='GREATER_THAN')
    L(nt, vn.outputs['Fac'], vth.inputs[0])
    vsc = N(nt, 'ShaderNodeMapRange', inputs={1: 0.0, 2: 1.0, 3: 0.0, 4: 1.05})
    L(nt, van.outputs['Fac'], vsc.inputs[0])
    L(nt, vsc.outputs[0], vth.inputs[1])
    alpha = N(nt, 'ShaderNodeMath', operation='MULTIPLY')
    L(nt, vis.outputs[0], alpha.inputs[0])
    L(nt, vth.outputs[0], alpha.inputs[1])
    L(nt, alpha.outputs[0], b_.inputs['Alpha'])
    m.surface_render_method = 'DITHERED'
    m.use_transparent_shadow = True
    L(nt, b_.outputs[0], out_node(nt).inputs['Surface'])

    return m


def make_rod(name, x, coll, mats):
    wood, cap = mats
    mb = MB()
    mb.cyl((0, Y0 - 0.2, 0), (0, Y1 + 0.2, 0), 0.32, wood, 20)
    for ye in (Y0 - 0.2, Y1 + 0.2):
        dy = -0.6 if ye < 0 else 0.6
        mb.cyl((0, ye, 0), (0, ye + dy, 0), 0.4, cap, 20, 0.36)
    ob = mb.build(name, coll)
    ob.location = (x, 0, PAPER_Z + 0.32)
    return ob


def build():
    coll = new_coll('巻物')
    nx_, ny_ = 60, 80
    verts, faces = [], []
    for i in range(nx_ + 1):
        for j in range(ny_ + 1):
            x = X0 + (X1 - X0) * i / nx_
            y = Y0 + (Y1 - Y0) * j / ny_
            verts.append((x, y, PAPER_Z))
    for i in range(nx_):
        for j in range(ny_):
            a = i * (ny_ + 1) + j
            faces.append((a, a + ny_ + 1, a + ny_ + 2, a + 1))
    me = bpy.data.meshes.new('巻物_紙')
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name='UVMap')
    uvd = []
    for f in faces:
        for vi in f:
            x, y, _ = verts[vi]
            # 本紙の範囲で u=南→北、v=東(0)→西(1)
            uvd += [(y - SC['y0']) / (SC['y1'] - SC['y0']), (SC['x1'] - x) / (SC['x1'] - SC['x0'])]
    uvl.data.foreach_set('uv', uvd)
    paper = bpy.data.objects.new('巻物_紙', me)
    link(paper, coll)

    paper['rod_x'] = X0
    paper['vanish'] = 0.0
    paper.data.materials.append(paper_material())
    rod_mats = (mat_wood('軸木', (0.10, 0.06, 0.04), (0.2, 0.12, 0.07), rough=0.4, reveal=False),
                mat_plain('軸端', (0.75, 0.6, 0.35), 0.3, reveal=False, noise=0.05, metal=1.0))
    rod_top = make_rod('巻物_天軸', X0 - 0.2, coll, rod_mats)
    rod_bot = make_rod('巻物_地軸', X0 - 0.2, coll, rod_mats)
    f0, f1 = T['unroll']
    paper['rod_x'] = X0 - 0.1
    paper.keyframe_insert('["rod_x"]', frame=1)
    paper.keyframe_insert('["rod_x"]', frame=f0)
    rod_bot.scale = (2.2, 1, 2.2)
    rod_bot.keyframe_insert('location', frame=f0)
    rod_bot.keyframe_insert('scale', frame=f0)
    rod_bot.rotation_euler = (0, 0, 0)
    rod_bot.keyframe_insert('rotation_euler', frame=f0)
    paper['rod_x'] = X1 + 0.1
    paper.keyframe_insert('["rod_x"]', frame=f1)
    rod_bot.location.x = X1 + 0.35
    rod_bot.scale = (1, 1, 1)
    rod_bot.keyframe_insert('location', frame=f1)
    rod_bot.keyframe_insert('scale', frame=f1)
    rod_bot.rotation_euler = (0, (X1 - X0) / 0.5, 0)
    rod_bot.keyframe_insert('rotation_euler', frame=f1)
    v0, v1 = T['vanish']
    ramp(paper, '["vanish"]', v0, v1, 0.0, 1.0)
    for ob in (rod_top, rod_bot):
        ob.keyframe_insert('scale', frame=v0)
        s_ = ob.scale.copy()
        ob.scale = (0.001, s_.y, 0.001)
        ob.keyframe_insert('scale', frame=v0 + 14)
        show_between(ob, None, v0 + 14)
    show_between(paper, None, v1)
    return paper
