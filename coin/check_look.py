"""10円玉を真上から丸ごと 1 枚撮る（本物の写真と並べて、色と光の具合を確かめる用）。

    blender -b build/coin.blend -P coin/check_look.py -- 出力.png [コマ]
"""
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
out = a[0]
frame = int(a[1]) if len(a) > 1 else 120
scn = bpy.context.scene
scn.frame_set(frame)
cam = scn.camera
cam.animation_data_clear()
cam.data.animation_data_clear()
cam.rotation_mode = 'QUATERNION'
cam.location = Vector((0, 0, 0.0015 + 0.080))
cam.rotation_quaternion = (1, 0, 0, 0)          # 真下を向く・画面の上が +y
cam.data.lens = 100.0
cam.data.dof.use_dof = False
scn.render.resolution_x, scn.render.resolution_y = 1080, 1080
scn.render.resolution_percentage = 100
scn.render.filepath = out
bpy.ops.render.render(write_still=True)
