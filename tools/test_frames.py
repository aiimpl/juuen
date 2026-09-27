"""指定したコマだけ描いて build/test/ に保存する（本番の前の確認用）。

    blender -b build/byodoin.blend -P tools/test_frames.py -- 150,250,480 [解像度%]
"""
import os
import sys
import time

import bpy

args = sys.argv[sys.argv.index('--') + 1:]
frames = [int(a) for a in args[0].split(',')]
pct = int(args[1]) if len(args) > 1 else 50
scn = bpy.context.scene
scn.render.resolution_percentage = pct
out_dir = os.path.join(os.path.dirname(bpy.data.filepath), 'test')
os.makedirs(out_dir, exist_ok=True)
for f in frames:
    scn.frame_set(f)
    scn.render.filepath = os.path.join(out_dir, f'test_{f:04d}.png')
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f'frame {f}: {time.time() - t:.1f}s', flush=True)
