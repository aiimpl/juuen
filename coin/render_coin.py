"""10円玉の本番のコマを 1 枚ずつ描く（build/coin_frames/c_0001.png〜）。

露出のキー（斜めのあいだ暗め）は、Blender のアニメーション書き出し（-a）では反映されないので、
1 コマずつ frame_set してから描く。描き終えたコマは飛ばす。

    blender -b build/coin.blend -P coin/render_coin.py
"""
import os

import bpy

scn = bpy.context.scene
out = os.path.join(os.path.dirname(bpy.data.filepath), 'coin_frames')
os.makedirs(out, exist_ok=True)
for f in range(scn.frame_start, scn.frame_end + 1):
    path = os.path.join(out, f'c_{f:04d}.png')
    if os.path.exists(path):
        continue
    scn.frame_set(f)
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('frame', f, round(scn.view_settings.exposure, 2), flush=True)
