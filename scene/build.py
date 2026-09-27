"""シーンを組み立てて build/byodoin.blend に保存する。

    blender -b --factory-startup -P scene/build.py

先に drawing/make_scroll.py で build/tex/scroll_ink.png を作っておくこと。
"""
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

bpy.ops.wm.read_factory_settings(use_empty=True)

from scene import camera, common, environment, hall, materials, scroll, terrain, trees, wire  # noqa: E402


def render_settings(scn):
    """最初から軽い設定：EEVEE 16 サンプル、レイトレースは半解像度、霞の体積は 8px タイル"""
    r = scn.render
    r.engine = 'BLENDER_EEVEE'
    r.resolution_x, r.resolution_y = 1920, 1080
    r.resolution_percentage = 100
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    r.filepath = os.path.join(common.BUILD, 'frames', 'f_')
    r.use_overwrite = False          # 途中で止めても、描いたコマから続けられる
    r.use_placeholder = True
    ee = scn.eevee
    ee.taa_render_samples = 16
    ee.use_raytracing = True
    ee.ray_tracing_options.resolution_scale = '2'
    ee.ray_tracing_options.trace_max_roughness = 0.3
    ee.ray_tracing_method = 'SCREEN'
    ee.use_shadows = True
    ee.shadow_ray_count = 1
    ee.shadow_step_count = 6
    ee.volumetric_tile_size = '8'
    ee.volumetric_samples = 32
    ee.volumetric_end = 1800
    ee.use_volumetric_shadows = True
    scn.view_settings.view_transform = 'AgX'
    scn.view_settings.look = 'AgX - Medium High Contrast'


def main():
    scn = bpy.context.scene
    scn.render.fps = common.FPS
    scn.frame_start = 1
    scn.frame_end = common.F_END

    materials.init()
    phases = hall.build()          # 鳳凰堂（5 段の部材）
    wire.build(phases)             # 墨線
    scroll.build()                 # 巻物
    env = terrain.build()          # 地形・池・水面
    trees.build(env)               # 樹木
    environment.build(env)         # 空・霞・光
    camera.build()
    common.constant_visibility_keys()

    render_settings(scn)
    scn.frame_set(1)
    os.makedirs(common.BUILD, exist_ok=True)
    out = os.path.join(common.BUILD, 'byodoin.blend')
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('saved', out)


main()
