"""10円玉の浮き彫りから溶けてつながる、本物の鳳凰堂のショット。

最初のコマは tools/juuen_camera.py のカメラ（浮き彫りの奥行き画像と同じ位置・画角）。
そこから画角を広げながら少しだけ上がり、池と森ごと全景を見せて止まる。カメラは一方向にしか動かない。

    blender -b build/byodoin.blend -P tools/building_shot.py -- [開始 終了]   # 1〜SHOT_LEN の範囲を描く
    blender -b build/byodoin.blend -P tools/building_shot.py -- save       # 設定だけして build/building_shot.blend に保存

描いたコマは build/bld_frames/b_0001.png から。シーンのコマは FRAME0 + ショットのコマ（肉付けも灯りも終わったあと）。
"""
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.juuen_camera import START_CAM, START_TGT, START_LENS  # noqa: E402
from scene.common import F_END, fcurves_of  # noqa: E402

SHOT_LEN = 216                      # 9 秒
FRAME0 = 400                        # ショットの 1 コマ目 = シーンの 401 コマ目
HOLD_IN, HOLD_OUT = 20, 18          # 溶けてつながるあいだは止め、最後も少し止める
END_CAM = (170.0, 0.0, 9.0)
END_TGT = (0.0, 0.0, 8.4)
END_LENS = 40.0

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
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
                print('extend', idb.name, fc.data_path)


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (u * 6 - 15) + 10)


def lerp3(a, b, u):
    return Vector(a).lerp(Vector(b), u)


# 画角は見かけの大きさが一定の速さで変わるよう、焦点距離を対数で補間する
for i in range(1, SHOT_LEN + 1):
    u = ease((i - HOLD_IN) / (SHOT_LEN - HOLD_IN - HOLD_OUT))
    f = FRAME0 + i
    cam.location = lerp3(START_CAM, END_CAM, u)
    tgt.location = lerp3(START_TGT, END_TGT, u)
    cam.data.lens = START_LENS * (END_LENS / START_LENS) ** u
    cam.keyframe_insert('location', frame=f)
    tgt.keyframe_insert('location', frame=f)
    cam.data.keyframe_insert('lens', frame=f)

scn.frame_start, scn.frame_end = FRAME0 + 1, FRAME0 + SHOT_LEN
out = os.path.join(ROOT, 'build', 'bld_frames')
os.makedirs(out, exist_ok=True)
scn.render.filepath = os.path.join(out, 'b_')
scn.render.use_overwrite = False
scn.render.use_file_extension = True

if args and args[0] == 'save':
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'build', 'building_shot.blend'))
else:
    s, e = (int(args[0]), int(args[1])) if len(args) >= 2 else (1, SHOT_LEN)
    for i in range(s, e + 1):
        path = os.path.join(out, f'b_{i:04d}.png')
        if os.path.exists(path):
            continue
        scn.frame_set(FRAME0 + i)
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print('frame', i, flush=True)
