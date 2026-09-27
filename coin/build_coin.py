"""10円玉のマクロ撮影のシーンを組んで build/coin.blend に保存する（実寸：直径 23.5mm・厚さ 1.5mm）。

    blender -b --factory-startup -P coin/build_coin.py

表面の高さは coin/make_face.py の build/coin_face.npy。カメラは最後に浮き彫りの矩形を画面いっぱいに撮り、
そのコマが本物の鳳凰堂の最初のコマ（tools/juuen_camera.py）とぴったり重なる。
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from coin.spec import R_COIN, THICK, RECT_W, RECT_CY  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
FPS, F_END = 24, 168
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, F_END

MM = 0.001
# 光の強さ（本物の写真と並べて、地・浮き彫り・縁の色が合うように決めた）
KEY_E, SOFT_E, WORLD, EXPOSURE = 0.06, 0.0, 0.16, 1.5


def node_mat(name):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    return m, nt, [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]


def N(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        if k == 'inputs':
            for kk, vv in v.items():
                n.inputs[kk].default_value = vv
        else:
            setattr(n, k, v)
    return n


def L(nt, a, b):
    nt.links.new(a, b)


# ---- 青銅（10円玉は銅 95%・亜鉛 3〜4%・錫 1〜2%）。色は本物の写真の地・縁・浮き彫りから測った比（R:G:B ≒ 1:0.42:0.18）----------------------------------------
def bronze():
    m, nt, out = node_mat('青銅')
    b = N(nt, 'ShaderNodeBsdfPrincipled', inputs={'Metallic': 1.0, 'Roughness': 0.34})
    tc = N(nt, 'ShaderNodeTexCoord')
    h = N(nt, 'ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='h')      # 表面の高さ（mm）
    ao = N(nt, 'ShaderNodeAmbientOcclusion', inputs={'Distance': 0.00022})
    ao.samples = 12
    # 高い所（縁・浮き彫り・文字の上）は触られて明るく、くぼみは酸化して暗い
    hi = N(nt, 'ShaderNodeMapRange', inputs={1: 0.05, 2: 0.2, 3: 0.0, 4: 1.0})
    L(nt, h.outputs['Fac'], hi.inputs[0])
    col_mid = N(nt, 'ShaderNodeValToRGB')
    col_mid.color_ramp.elements[0].color = (0.30, 0.085, 0.028, 1)
    col_mid.color_ramp.elements[1].color = (0.68, 0.23, 0.075, 1)
    blot = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 180.0, 'Detail': 6.0, 'Roughness': 0.6})
    L(nt, tc.outputs['Object'], blot.inputs['Vector'])
    L(nt, blot.outputs['Fac'], col_mid.inputs[0])
    polish = N(nt, 'ShaderNodeMix', data_type='RGBA')
    L(nt, hi.outputs[0], polish.inputs['Factor'])
    L(nt, col_mid.outputs[0], polish.inputs[6])
    polish.inputs[7].default_value = (0.92, 0.42, 0.17, 1)
    aor = N(nt, 'ShaderNodeMapRange', inputs={1: 0.45, 2: 0.95, 3: 0.12, 4: 1.0})
    L(nt, ao.outputs['AO'], aor.inputs[0])
    patina = N(nt, 'ShaderNodeMix', data_type='RGBA', inputs={'Factor': 1.0})
    patina.blend_type = 'MULTIPLY'
    L(nt, polish.outputs[2], patina.inputs[6])
    L(nt, aor.outputs[0], patina.inputs[7])
    cav = N(nt, 'ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='cav')
    dirt = N(nt, 'ShaderNodeMix', data_type='RGBA')
    L(nt, cav.outputs['Fac'], dirt.inputs['Factor'])
    L(nt, patina.outputs[2], dirt.inputs[6])
    dirt.inputs[7].default_value = (0.09, 0.028, 0.012, 1)     # 酸化して黒ずんだ銅
    L(nt, dirt.outputs[2], b.inputs['Base Color'])
    # 粗さ：細かいすり傷（向きの違う細長いノイズを 2 枚）と、指紋のくもり
    def scratches(rotz, scale):
        # 先に回してから引き伸ばす（Mapping は拡大→回転の順なので 2 段に分ける）
        rt = N(nt, 'ShaderNodeMapping', inputs={'Rotation': (0, 0, rotz)})
        L(nt, tc.outputs['Object'], rt.inputs['Vector'])
        mp = N(nt, 'ShaderNodeMapping', inputs={'Scale': (scale, scale * 30, scale)})
        L(nt, rt.outputs[0], mp.inputs['Vector'])
        nz = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 1.0, 'Detail': 2.0})
        L(nt, mp.outputs[0], nz.inputs['Vector'])
        mr = N(nt, 'ShaderNodeMapRange', inputs={1: 0.69, 2: 0.73, 3: 0.0, 4: 1.0})
        L(nt, nz.outputs['Fac'], mr.inputs[0])
        return mr.outputs[0]
    # 細かすぎると画素と干渉して縞（モアレ）になるので、線の幅は 20μm 前後にする
    s1, s2, s3 = scratches(0.6, 520), scratches(-1.1, 380), scratches(2.2, 450)
    smax0 = N(nt, 'ShaderNodeMath', operation='MAXIMUM')
    L(nt, s1, smax0.inputs[0])
    L(nt, s2, smax0.inputs[1])
    smax = N(nt, 'ShaderNodeMath', operation='MAXIMUM')
    L(nt, smax0.outputs[0], smax.inputs[0])
    L(nt, s3, smax.inputs[1])
    finger = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 90.0, 'Detail': 3.0})
    L(nt, tc.outputs['Object'], finger.inputs['Vector'])
    rough = N(nt, 'ShaderNodeMapRange', inputs={1: 0.3, 2: 0.7, 3: 0.34, 4: 0.52})
    L(nt, finger.outputs['Fac'], rough.inputs[0])
    rh = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD', inputs={1: 0.18})
    L(nt, smax.outputs[0], rh.inputs[0])
    L(nt, rough.outputs[0], rh.inputs[2])
    rpol = N(nt, 'ShaderNodeMix', data_type='FLOAT')
    L(nt, hi.outputs[0], rpol.inputs['Factor'])
    L(nt, rh.outputs[0], rpol.inputs[2])
    rpol.inputs[3].default_value = 0.27
    L(nt, rpol.outputs[0], b.inputs['Roughness'])
    bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.12, 'Distance': 0.00001})
    L(nt, smax.outputs[0], bump.inputs['Height'])
    L(nt, bump.outputs[0], b.inputs['Normal'])
    # 円の外は透明（表面の格子は正方形なので）
    ob_c = N(nt, 'ShaderNodeTexCoord')
    ln = N(nt, 'ShaderNodeVectorMath', operation='LENGTH')
    sep = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, ob_c.outputs['Object'], sep.inputs[0])
    comb = N(nt, 'ShaderNodeCombineXYZ')
    L(nt, sep.outputs['X'], comb.inputs['X'])
    L(nt, sep.outputs['Y'], comb.inputs['Y'])
    L(nt, comb.outputs[0], ln.inputs[0])
    inside = N(nt, 'ShaderNodeMath', operation='LESS_THAN', inputs={1: R_COIN * MM})
    L(nt, ln.outputs['Value'], inside.inputs[0])
    L(nt, inside.outputs[0], b.inputs['Alpha'])
    m.surface_render_method = 'DITHERED'
    m.use_transparent_shadow = True
    L(nt, b.outputs[0], out.inputs['Surface'])
    return m


BRONZE = bronze()

# ---- 表面：高さの地図から格子メッシュ -------------------------------------------------
face = np.load(os.path.join(ROOT, 'build', 'coin_face.npy')).astype(np.float64)
Nf = face.shape[0]
step = 1                                 # 2048×2048 の格子（約 11μm 間隔）
fh = face[::step, ::step]
n = fh.shape[0]
xs = np.linspace(-R_COIN, R_COIN, n)
X, Y = np.meshgrid(xs, -xs)
Z = THICK + fh
verts = np.stack([X.ravel() * MM, Y.ravel() * MM, Z.ravel() * MM], 1)
idx = np.arange(n * n).reshape(n, n)
quads = np.stack([idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()], 1)
# 円の外の四角は落とす（少し余裕を残して、あとはシェーダーで切る）
cx = (X[:-1, :-1] + X[1:, 1:]) / 2
cy = (Y[:-1, :-1] + Y[1:, 1:]) / 2
keep = (np.hypot(cx, cy) < R_COIN + 0.05).ravel()
quads = quads[keep]
me = bpy.data.meshes.new('十円玉_表')
me.vertices.add(len(verts))
me.vertices.foreach_set('co', verts.ravel())
me.loops.add(quads.size)
me.loops.foreach_set('vertex_index', quads.ravel())
me.polygons.add(len(quads))
me.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4))
me.update(calc_edges=True)
me.polygons.foreach_set('use_smooth', [True] * len(quads))
at = me.attributes.new('h', 'FLOAT', 'POINT')
at.data.foreach_set('value', fh.ravel().astype(np.float32))
cav = np.load(os.path.join(ROOT, 'build', 'coin_cav.npy'))[::step, ::step]
at = me.attributes.new('cav', 'FLOAT', 'POINT')
at.data.foreach_set('value', cav.ravel().astype(np.float32))
me.materials.append(BRONZE)
top = bpy.data.objects.new('十円玉_表', me)
scn.collection.objects.link(top)

# 側面（なめらかな縁。角はわずかに丸い）
bpy.ops.mesh.primitive_cylinder_add(vertices=256, radius=R_COIN * MM, depth=THICK * MM, location=(0, 0, THICK * MM / 2))
side = bpy.context.active_object
side.name = '十円玉_側面'
bv = side.modifiers.new('面取り', 'BEVEL')
bv.width = 0.12 * MM
bv.segments = 4
bpy.ops.object.shade_smooth()
m_side, nt, out = node_mat('青銅_側面')
b = N(nt, 'ShaderNodeBsdfPrincipled', inputs={'Base Color': (0.60, 0.27, 0.11, 1), 'Metallic': 1.0, 'Roughness': 0.36})
L(nt, b.outputs[0], out.inputs['Surface'])
side.data.materials.append(m_side)

# ---- 机：暗いくるみ材 -----------------------------------------------------------------
m, nt, out = node_mat('くるみ材')
b = N(nt, 'ShaderNodeBsdfPrincipled', inputs={'Roughness': 0.55, 'Coat Weight': 0.08, 'Coat Roughness': 0.35})
tc = N(nt, 'ShaderNodeTexCoord')
mp = N(nt, 'ShaderNodeMapping', inputs={'Scale': (60.0, 6.0, 60.0)})
L(nt, tc.outputs['Object'], mp.inputs['Vector'])
wave = N(nt, 'ShaderNodeTexWave', inputs={'Scale': 3.0, 'Distortion': 8.0, 'Detail': 6.0, 'Detail Scale': 1.5})
L(nt, mp.outputs[0], wave.inputs['Vector'])
cr = N(nt, 'ShaderNodeValToRGB')
cr.color_ramp.elements[0].color = (0.035, 0.018, 0.01, 1)
cr.color_ramp.elements[1].color = (0.13, 0.07, 0.04, 1)
L(nt, wave.outputs['Fac'], cr.inputs[0])
L(nt, cr.outputs[0], b.inputs['Base Color'])
bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.15, 'Distance': 0.0002})
L(nt, wave.outputs['Fac'], bump.inputs['Height'])
L(nt, bump.outputs[0], b.inputs['Normal'])
L(nt, b.outputs[0], out.inputs['Surface'])
bpy.ops.mesh.primitive_plane_add(size=0.6, location=(0, 0, 0))
table = bpy.context.active_object
table.name = '机'
table.data.materials.append(m)

# ---- 光：浮き彫りが立つよう左上から低く当てる斜光・大きな照り返し・右奥からの輪郭光 ----------
def area(name, loc, size, energy, color, target=(0, 0, 0)):
    d = bpy.data.lights.new(name, 'AREA')
    d.size = size
    d.energy = energy
    d.color = color
    ob = bpy.data.objects.new(name, d)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    scn.collection.objects.link(ob)
    return ob


key = area('斜光', (-0.09, 0.07, 0.055), 0.06, KEY_E, (1.0, 0.93, 0.85))
soft = area('照り返し', (0.0, -0.02, 0.16), 0.16, SOFT_E, (1.0, 0.98, 0.96))
rimL = area('輪郭光', (0.1, 0.1, 0.04), 0.04, 0.008, (0.9, 0.93, 1.0))
# 光の筋が面を横切る：斜光をゆっくり回す
for f, ang in ((1, -0.25), (60, 0.0), (120, 0.35), (F_END, 0.42)):
    r = math.hypot(key.location.x, key.location.y) if f == 1 else 0.114
    key.location = (r * math.cos(math.radians(140) + ang), r * math.sin(math.radians(140) + ang), 0.055)
    key.rotation_euler = (Vector((0, 0, 0)) - key.location).to_track_quat('-Z', 'Y').to_euler()
    key.keyframe_insert('location', frame=f)
    key.keyframe_insert('rotation_euler', frame=f)
# 低い角度からは照り返しが面いっぱいに乗るので、斜光は弱く始めて、上へ回り込むにつれ強める
for f, e in ((1, KEY_E * 0.7), (80, KEY_E)):
    key.data.energy = e
    key.data.keyframe_insert('energy', frame=f)

w = bpy.data.worlds.new('スタジオ')
# 本物の写真のように、まわり全体から柔らかい光が回る（暗い背景に強い光だと、照り返しが後光のように白く飛ぶ）
# 明るいのは真上の丸い天井だけで、横（地平線）は暗い。斜めから見たとき金属が横の光を拾って全体が光るのを防ぐ
wnt = w.node_tree
bg = wnt.nodes['Background']
wtc = wnt.nodes.new('ShaderNodeTexCoord')
wsep = wnt.nodes.new('ShaderNodeSeparateXYZ')
wnt.links.new(wtc.outputs['Generated'], wsep.inputs[0])
dome = wnt.nodes.new('ShaderNodeMapRange')
dome.inputs[1].default_value, dome.inputs[2].default_value = 0.45, 0.92
dome.inputs[3].default_value, dome.inputs[4].default_value = 0.03, 1.0
wnt.links.new(wsep.outputs['Z'], dome.inputs[0])
wcol = wnt.nodes.new('ShaderNodeMix')
wcol.data_type = 'RGBA'
wcol.blend_type = 'MULTIPLY'
wcol.inputs['Factor'].default_value = 1.0
wcol.inputs[6].default_value = (WORLD, WORLD * 0.97, WORLD * 0.94, 1)
wnt.links.new(dome.outputs[0], wcol.inputs[7])
wnt.links.new(wcol.outputs[2], bg.inputs['Color'])
scn.world = w

# ---- カメラ：マクロ 100mm。1 コマずつ位置・向き・ピント・絞りを計算してキーを打つ ---------------
cam_d = bpy.data.cameras.new('マクロ')
cam_d.lens = 100.0
cam_d.sensor_width = 36.0
cam_d.clip_start = 0.02         # 奥行きの精度が落ちると斜めの面に縞が出るので、範囲は狭く
cam_d.clip_end = 0.6
cam_d.dof.use_dof = True
cam = bpy.data.objects.new('マクロ', cam_d)
scn.collection.objects.link(cam)
scn.camera = cam
cam.rotation_mode = 'QUATERNION'

FACE_Z = THICK * MM
END_TGT = Vector((0, RECT_CY * MM, FACE_Z + 0.12 * MM))
END_D = RECT_W * MM * 100.0 / 36.0         # この距離で、幅 19mm の矩形が画面の幅ちょうど


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (u * 6 - 15) + 10)


def lerp(a, b, u):
    return a + (b - a) * u


# 制御点：(コマ, 注視点, 方位角°, 仰角°, 距離 m, 絞り)
KEYS = [
    (1, Vector((0, -0.6 * MM, FACE_Z * 0.5)), -56, 27, 0.088, 8.0),       # 机の上の 10円玉（ひと目で 10円玉とわかる）
    (150, END_TGT, -90, 90, END_D, 16.0),                                  # 真上へ回り込みながら寄り、浮き彫りの矩形を画面いっぱいに
    (F_END, END_TGT, -90, 90, END_D, 16.0),
]


def sample(f):
    ks = KEYS
    if f <= ks[0][0]:
        return ks[0][1:]
    for (f0, t0, a0, e0, d0, s0), (f1, t1, a1, e1, d1, s1) in zip(ks[:-1], ks[1:]):
        if f0 <= f <= f1:
            u = ease((f - f0) / max(1, f1 - f0))
            return t0.lerp(t1, u), lerp(a0, a1, u), lerp(e0, e1, u), d0 * (d1 / d0) ** u, lerp(s0, s1, u)
    return ks[-1][1:]


for f in range(1, F_END + 1):
    tgt, az, el, dist, fs = sample(f)
    a, e = math.radians(az), math.radians(el)
    pos = tgt + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * dist
    fwd = (tgt - pos).normalized()
    up_world = Vector((0, 1, 0)) if el > 80 else Vector((0, 0, 1))
    # 真上に近づくほど、画面の上を 10円玉の上（+y）にそろえる
    up = Vector((0, 1, 0)).lerp(Vector((0, 0, 1)), 1 - ease((el - 40) / 50)).normalized() if el > 40 else up_world
    right = fwd.cross(up).normalized()
    up2 = right.cross(fwd).normalized()
    rot = Matrix((right, up2, -fwd)).transposed().to_quaternion()
    cam.location = pos
    cam.rotation_quaternion = rot
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_quaternion', frame=f)
    cam_d.dof.focus_distance = (tgt - pos).length
    cam_d.dof.aperture_fstop = fs
    cam_d.dof.keyframe_insert('focus_distance', frame=f)
    cam_d.dof.keyframe_insert('aperture_fstop', frame=f)

# ---- レンダー設定 ---------------------------------------------------------------------
r = scn.render
r.engine = 'BLENDER_EEVEE'
r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
r.image_settings.file_format = 'PNG'
r.image_settings.color_mode = 'RGB'
r.filepath = os.path.join(ROOT, 'build', 'coin_frames', 'c_')
r.use_overwrite = False
ee = scn.eevee
ee.taa_render_samples = 48
ee.use_raytracing = True
ee.ray_tracing_options.resolution_scale = '1'
ee.ray_tracing_options.trace_max_roughness = 0.5
ee.use_shadows = True
ee.shadow_ray_count = 2
ee.shadow_step_count = 8
scn.view_settings.view_transform = 'Standard'          # 色を写真と測って合わせるので、色味を変えない変換
scn.view_settings.look = 'None'
# 真上から見たときの色を本物の写真に合わせてある。斜めから見るあいだは照り返しで白く光らないよう暗めに始め、真上に来るまでに戻す
for f, ev in ((1, EXPOSURE - 1.3), (40, EXPOSURE - 1.0), (110, EXPOSURE)):
    scn.view_settings.exposure = ev
    scn.view_settings.keyframe_insert('exposure', frame=f)
scn.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'build', 'coin.blend'))
print('saved coin.blend', len(me.vertices), 'verts')
