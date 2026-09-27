"""10円玉の浮き彫りの元になる奥行き画像を、鳳凰堂のモデルそのものから描く。

正面（東）の望遠カメラから、建物だけを、カメラに近いほど白い 16bit の画像にする。
池の水・地面・庭石は黒で描いて残す（水面より下の基壇が浮き彫りに入らないよう、手前を隠す役）。
このカメラは、動画で 10円玉から本物の鳳凰堂へ溶けてつながる最初のコマと同じ位置・同じ画角。

    blender -b build/byodoin.blend -P tools/relief_depth.py
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.juuen_camera import START_CAM, START_TGT, START_LENS, NEAR, FAR  # noqa: E402

scn = bpy.context.scene
scn.frame_set(420)                                    # 肉付けが終わり、紙も消えたあとのコマ

cam = scn.camera
tgt = bpy.data.objects['注視点']
for idb in (cam, tgt, cam.data):
    idb.animation_data_clear()
cam.location = START_CAM
tgt.location = START_TGT
cam.data.lens = START_LENS

# 建物（5 段の部材）と、手前を隠す水・地面・庭石だけを残す
keep = {'鳳凰堂_p1', '鳳凰堂_p2', '鳳凰堂_p3', '鳳凰堂_p4', '鳳凰堂_p5'}
occluders = {'池水', '地形_近景', '洲浜'}
for ob in scn.objects:
    if ob.type in ('MESH', 'CURVES', 'VOLUME', 'LIGHT_PROBE', 'EMPTY') and ob.name not in keep:
        ob.animation_data_clear()
        ob.hide_render = not (ob.name in occluders or ob.name.startswith('庭石_'))
        ob.pass_index = 0
for name in keep:
    ob = bpy.data.objects[name]
    ob.animation_data_clear()
    ob['prog'] = 100.0                                # 全部の部材が実体化した状態
    ob.pass_index = 1
    for m in ob.modifiers:
        if m.type == 'BEVEL':
            m.show_render = True

# 奥行き：カメラからの距離を、近いほど白く
m = bpy.data.materials.new('奥行き')
nt = m.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL':
        nt.nodes.remove(n)
out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
cd = nt.nodes.new('ShaderNodeCameraData')
mr = nt.nodes.new('ShaderNodeMapRange')
mr.inputs[1].default_value = NEAR
mr.inputs[2].default_value = FAR
mr.inputs[3].default_value = 1.0
mr.inputs[4].default_value = 0.0
oi = nt.nodes.new('ShaderNodeObjectInfo')
only = nt.nodes.new('ShaderNodeMath')                # 建物以外は黒
only.operation = 'MULTIPLY'
em = nt.nodes.new('ShaderNodeEmission')
nt.links.new(cd.outputs['View Z Depth'], mr.inputs[0])
nt.links.new(mr.outputs[0], only.inputs[0])
nt.links.new(oi.outputs['Object Index'], only.inputs[1])
nt.links.new(only.outputs[0], em.inputs['Color'])
nt.links.new(em.outputs[0], out.inputs['Surface'])
scn.view_layers[0].material_override = m

w = bpy.data.worlds.new('黒')
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
scn.world = w
r = scn.render
r.resolution_x, r.resolution_y, r.resolution_percentage = 3840, 2160, 100
r.image_settings.file_format = 'PNG'
r.image_settings.color_depth = '16'
r.image_settings.color_mode = 'BW'
r.filepath = os.path.join(os.path.dirname(bpy.data.filepath), 'relief_depth.png')
scn.view_settings.view_transform = 'Standard'
scn.view_settings.look = 'None'
scn.eevee.taa_render_samples = 16
scn.eevee.use_raytracing = False
bpy.ops.render.render(write_still=True)
print('wrote', r.filepath)
