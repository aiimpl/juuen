"""10円玉の本番のコマを 1 枚ずつ描く。描き終えたコマは飛ばす。

露出のキー（斜めのあいだ暗め）は、Blender のアニメーション書き出し（-a）では反映されないので、
1 コマずつ frame_set してから描く。

    blender -b build/coin.blend -P coin/render_coin.py            寄りのショット → build/coin_frames/c_0001.png〜
    blender -b build/coin.blend -P coin/render_coin.py -- end     締め：真上から 10円玉を丸ごと → build/coin_end/e_0001.png〜
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

END_LEN = 84                        # 締めのカット 3.5 秒
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
scn = bpy.context.scene
root = os.path.dirname(bpy.data.filepath)

if args and args[0] == 'end':
    # 真上から、10円玉を画面の左寄りに丸ごと（右に縦書きの題を置く）。ゆっくり寄りながら、わずかに回る
    cam = scn.camera
    cam.animation_data_clear()
    cam.data.animation_data_clear()
    cam.data.dof.use_dof = False
    cam.rotation_mode = 'XYZ'
    face_z = 0.0015
    scn.frame_set(scn.frame_end)                 # 真上から見たとき（写真に合わせた）の露出
    ev = scn.view_settings.exposure
    scn.animation_data_clear()                  # 露出のキーを外し、真上の明るさに固定
    scn.view_settings.exposure = ev
    key = bpy.data.objects['斜光']
    key.animation_data_clear()
    for f in range(1, END_LEN + 1):
        u = (f - 1) / (END_LEN - 1)
        s = u * u * (3 - 2 * u)
        d = 0.150 - 0.012 * s
        cam.location = (0.0043 * d / 0.15, 0.0, face_z + d)
        cam.rotation_euler = Euler((0, 0, math.radians(-4 + 4 * s)))
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_euler', frame=f)
        # 斜光が左上から右上へゆっくり回り、面を光が渡る
        a = math.radians(150 - 60 * s)
        key.location = (0.114 * math.cos(a), 0.114 * math.sin(a), 0.06)
        key.rotation_euler = (Vector((0, 0, 0)) - key.location).to_track_quat('-Z', 'Y').to_euler()
        key.keyframe_insert('location', frame=f)
        key.keyframe_insert('rotation_euler', frame=f)
    out, prefix, frames = os.path.join(root, 'coin_end'), 'e_', range(1, END_LEN + 1)
else:
    out, prefix, frames = os.path.join(root, 'coin_frames'), 'c_', range(scn.frame_start, scn.frame_end + 1)

os.makedirs(out, exist_ok=True)
for f in frames:
    path = os.path.join(out, f'{prefix}{f:04d}.png')
    if os.path.exists(path):
        continue
    scn.frame_set(f)
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('frame', f, round(scn.view_settings.exposure, 2), flush=True)
