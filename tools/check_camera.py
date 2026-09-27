"""カメラの動きを数値で確かめる（酔いやすい急な振りがないか）。

    blender -b build/byodoin.blend -P tools/check_camera.py
"""
import math

import bpy

scn = bpy.context.scene
cam = scn.camera
prev, rows = None, []
for f in range(25, scn.frame_end + 1):
    scn.frame_set(f)
    m = cam.matrix_world
    fwd = -(m.to_3x3().col[2]).normalized()
    pos = m.translation.copy()
    if prev:
        ang = math.degrees(fwd.angle(prev[0])) if fwd.dot(prev[0]) < 0.999999 else 0.0
        rows.append((f, ang, (pos - prev[1]).length))
    prev = (fwd, pos)
rot = max(rows, key=lambda r: r[1])
mov = max(rows, key=lambda r: r[2])
jerk = max(abs(rows[i][1] - rows[i - 1][1]) for i in range(1, len(rows)))
print(f'視線の回転 最大 {rot[1]:.3f}°/コマ（{rot[0]}コマ目）')
print(f'移動 最大 {mov[2]:.3f}m/コマ（{mov[0]}コマ目）')
print(f'回転量の変化 最大 {jerk:.4f}°/コマ')
