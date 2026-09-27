"""10円玉の浮き彫りから立体に立ち上がり、本物の鳳凰堂になって全景まで引くショット。

最初のコマは tools/juuen_camera.py のカメラ（浮き彫りの奥行き画像と同じ位置・画角）。
建物の頂点は、このカメラからの視線に沿って奥の壁の面まで押しつぶしてあり（見た目は浮き彫りのまま）、
RISE の間に本来の奥行きへ戻る。最初のカメラから見た輪郭は立ち上がっても変わらないので、10円玉の絵と重なったまま
立体になり、カメラが回り込むにつれて奥行きが見えてくる。

2 つの版を描いて、finish/compose_juuen.py で溶かしてつなぐ。
  relief  銅の浮き彫りの版：建物と奥の壁だけ、10円玉と同じ銅の色（1〜RELIEF_END コマ）
  real    本物の版：いつもの景色（REAL_START〜SHOT_LEN コマ）

    blender -b build/byodoin.blend -P tools/building_shot.py -- relief|real [開始 終了]

描いたコマは build/bld_relief/r_0001.png・build/bld_frames/b_0076.png から。シーンのコマは FRAME0 + ショットのコマ。
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.juuen_camera import START_CAM, START_TGT, START_LENS  # noqa: E402
from scene.common import F_END, fcurves_of  # noqa: E402

SHOT_LEN = 216                      # 9 秒
FRAME0 = 400                        # 肉付けも灯りも終わったあとのコマから
HOLD_IN, HOLD_OUT = 20, 18          # 10円玉から溶けてくるあいだは止め、最後も少し止める
RISE = (20, 84)                     # 浮き彫りが立体に立ち上がる
RELIEF_END, REAL_START = 104, 76    # 銅の版と本物の版が重なる範囲（finish/compose_juuen.py と同じ）
AZ_END = -20.0                      # 回り込む角度（南東へ）
END_Z, END_TGT_Z, END_LENS = 9.0, 8.4, 40.0
WALL_X = -25.8                      # 押しつぶす先の壁（建物のいちばん奥のすぐ後ろ）
RELIEF_EV = 0.4                     # 銅の版の露出（10円玉の最後のコマと明るさをそろえる）
HALL = ['鳳凰堂_p1', '鳳凰堂_p2', '鳳凰堂_p3', '鳳凰堂_p4', '鳳凰堂_p5']

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
mode = args[0] if args else 'real'
scn = bpy.context.scene
cam = scn.camera
tgt = bpy.data.objects['注視点']
for idb in (cam, tgt, cam.data):
    idb.animation_data_clear()

# 本編の終わり（504 コマ）より先も水面が揺れ続けるよう、揺れのキー（1→504 の 2 点）だけ線形に延ばす
for idb in bpy.data.materials:
    ad = idb.node_tree.animation_data if idb.node_tree else None
    if ad and ad.action:
        for fc in fcurves_of(ad.action):
            kf = fc.keyframe_points
            if len(kf) == 2 and kf[0].co.x <= 1 and kf[1].co.x >= F_END:
                fc.extrapolation = 'LINEAR'
                for k in kf:
                    k.interpolation = 'LINEAR'


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (u * 6 - 15) + 10)


# ---- 立ち上がり：最初のカメラからの視線に沿って、奥の壁の前の薄い浮き彫り（奥行き RELIEF_T 倍）まで押しつぶす ----
#   x_flat = WALL_X + (p.x - WALL_X) * RELIEF_T
#   p_flat = C0 + (p - C0) * (x_flat - C0.x) / (p.x - C0.x)、  p' = mix(p_flat, p, 立ち上がり)
C0 = Vector(START_CAM)
RELIEF_T = 0.04
ng = bpy.data.node_groups.new('浮き彫りから立ち上がる', 'GeometryNodeTree')
ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
nd = ng.nodes
gi, go = nd.new('NodeGroupInput'), nd.new('NodeGroupOutput')
rise = nd.new('ShaderNodeValue')                        # 立ち上がり（0＝浮き彫り、1＝本来の奥行き）。5 つの部材で共有
rise.name = '立ち上がり'
pos = nd.new('GeometryNodeInputPosition')
v = nd.new('ShaderNodeVectorMath')
v.operation = 'SUBTRACT'
v.inputs[1].default_value = C0
ng.links.new(pos.outputs[0], v.inputs[0])
sep = nd.new('ShaderNodeSeparateXYZ')
ng.links.new(v.outputs[0], sep.inputs[0])
xf = nd.new('ShaderNodeMath')                           # x_flat - C0.x = (p.x - C0.x) * T + (WALL_X - C0.x) * (1 - T)
xf.operation = 'MULTIPLY_ADD'
xf.inputs[1].default_value = RELIEF_T
xf.inputs[2].default_value = (WALL_X - C0.x) * (1 - RELIEF_T)
ng.links.new(sep.outputs['X'], xf.inputs[0])
k = nd.new('ShaderNodeMath')
k.operation = 'DIVIDE'
ng.links.new(xf.outputs[0], k.inputs[0])
ng.links.new(sep.outputs['X'], k.inputs[1])
sc = nd.new('ShaderNodeVectorMath')
sc.operation = 'SCALE'
ng.links.new(v.outputs[0], sc.inputs[0])
ng.links.new(k.outputs[0], sc.inputs['Scale'])
flat = nd.new('ShaderNodeVectorMath')
flat.operation = 'ADD'
flat.inputs[1].default_value = C0
ng.links.new(sc.outputs[0], flat.inputs[0])
mix = nd.new('ShaderNodeMix')
mix.data_type = 'VECTOR'
ng.links.new(rise.outputs[0], mix.inputs['Factor'])
ng.links.new(flat.outputs[0], mix.inputs[4])
ng.links.new(pos.outputs[0], mix.inputs[5])
sp = nd.new('GeometryNodeSetPosition')
ng.links.new(gi.outputs['Geometry'], sp.inputs['Geometry'])
ng.links.new(mix.outputs[1], sp.inputs['Position'])
ng.links.new(sp.outputs[0], go.inputs['Geometry'])

for name in HALL:
    bpy.data.objects[name].modifiers.new('浮き彫りから立ち上がる', 'NODES').node_group = ng

# ---- カメラ：最初のカメラから、南東へ回り込みながら画角を広げて少し上がる。一方向にしか動かない ---------
R0 = C0.length
for i in range(1, SHOT_LEN + 1):
    f = FRAME0 + i
    u = ease((i - HOLD_IN) / (SHOT_LEN - HOLD_IN - HOLD_OUT))
    a = math.radians(AZ_END) * u
    cam.location = (R0 * math.cos(a), R0 * math.sin(a), START_CAM[2] + (END_Z - START_CAM[2]) * u)
    tgt.location = (0.0, 0.0, START_TGT[2] + (END_TGT_Z - START_TGT[2]) * u)
    cam.data.lens = START_LENS * (END_LENS / START_LENS) ** u
    cam.keyframe_insert('location', frame=f)
    tgt.keyframe_insert('location', frame=f)
    cam.data.keyframe_insert('lens', frame=f)
    rise.outputs[0].default_value = ease((i - RISE[0]) / (RISE[1] - RISE[0]))
    rise.outputs[0].keyframe_insert('default_value', frame=f)

# ---- 銅の浮き彫りの版：建物と奥の壁だけ、10円玉と同じ銅の色 --------------------------------------------
if mode == 'relief':
    for ob in scn.objects:
        if ob.name not in HALL and ob.type in ('MESH', 'CURVES', 'VOLUME', 'LIGHT', 'LIGHT_PROBE', 'EMPTY'):
            ob.animation_data_clear()                   # 表示のキー（景色が現れる）を消してから隠す
            ob.hide_render = True
    for name in HALL:
        bpy.data.objects[name]['prog'] = 100.0
    bpy.ops.mesh.primitive_plane_add(size=1, location=(WALL_X - 0.2, 0, 6.0), rotation=(0, math.radians(90), 0))
    wall = bpy.context.active_object
    wall.name = '10円玉の地'
    wall.scale = (140, 260, 1)
    m = bpy.data.materials.new('銅')
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.70, 0.30, 0.11, 1)      # 10円玉の最後のコマと色味をそろえる
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.4
    scn.view_layers[0].material_override = m
    sun_d = bpy.data.lights.new('斜光', 'SUN')
    sun_d.energy = 4.0
    sun_d.angle = math.radians(6)
    sun = bpy.data.objects.new('斜光', sun_d)
    scn.collection.objects.link(sun)
    sun.rotation_euler = (-Vector((0.55, -0.55, 0.62)).normalized()).to_track_quat('-Z', 'Y').to_euler()
    w = bpy.data.worlds.new('銅の版')
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.12, 0.118, 0.113, 1)
    scn.world = w
    scn.view_settings.view_transform = 'Standard'
    scn.view_settings.look = 'None'
    scn.view_settings.exposure = float(os.environ.get('RELIEF_EV', RELIEF_EV))
    out_dir, prefix, rng = os.path.join(ROOT, 'build', 'bld_relief'), 'r_', (1, RELIEF_END)
else:
    out_dir, prefix, rng = os.path.join(ROOT, 'build', 'bld_frames'), 'b_', (REAL_START, SHOT_LEN)

os.makedirs(out_dir, exist_ok=True)
s, e = (int(args[1]), int(args[2])) if len(args) >= 3 else rng
for i in range(s, e + 1):
    path = os.path.join(out_dir, f'{prefix}{i:04d}.png')
    if os.path.exists(path):
        continue
    scn.frame_set(FRAME0 + i)
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('frame', i, flush=True)
