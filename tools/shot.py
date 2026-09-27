"""好きな位置から静止画を 1 枚撮る（寄りの確認用）。

    blender -b build/byodoin.blend -P tools/shot.py -- コマ 出力.png カメラx y z 注視点x y z レンズmm [解像度%]
"""
import sys

import bpy

a = sys.argv[sys.argv.index('--') + 1:]
frame, out = int(a[0]), a[1]
cx, cy, cz, tx, ty, tz, lens = map(float, a[2:9])
pct = int(a[9]) if len(a) > 9 else 50

scn = bpy.context.scene
scn.frame_set(frame)
cam = scn.camera
tgt = bpy.data.objects['注視点']
for idb in (cam, tgt, cam.data):
    idb.animation_data_clear()
cam.location = (cx, cy, cz)
tgt.location = (tx, ty, tz)
cam.data.lens = lens
scn.render.resolution_percentage = pct
scn.render.filepath = out
bpy.ops.render.render(write_still=True)
