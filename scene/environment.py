"""空・霞・光。肉付けまでは暗い工房（カメラにだけ見えるドーム）と斜光、巻物が消えると夕空・霞・夕日に替わる。"""
import math

import bpy
from mathutils import Vector

from .common import T, PAPER_Z, scene, link, ramp, sock_ramp, show_between, mat_new, out_node, N, L
from .materials import mat_plain

SUN_EL = math.radians(4.0)          # 夕日の高さ
SUN_AZ = math.radians(292.5)        # 西北西（北から時計回り）


def build(env_coll):
    # 地形と森は巻物が消えるまで隠す
    # キーを打つと all_objects が作り直されるので、先にリストへ写す
    for ob in list(env_coll.all_objects):
        show_between(ob, T['env'][0], None)
    e0, e1 = T['env']
    world = bpy.data.worlds.new('夕空')
    scene().world = world
    wt = world.node_tree
    for n in list(wt.nodes):
        wt.nodes.remove(n)
    wo = wt.nodes.new('ShaderNodeOutputWorld')
    sky = wt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = SUN_EL
    sky.sun_rotation = (-SUN_AZ) % (2 * math.pi)
    sky.air_density = 1.5
    sky.aerosol_density = 4.0
    sky.altitude = 30
    sky.sun_disc = True
    sky.sun_size = math.radians(1.6)
    sky.sun_intensity = 0.6
    bg_sky = wt.nodes.new('ShaderNodeBackground')
    wt.links.new(sky.outputs[0], bg_sky.inputs[0])
    wt.links.new(bg_sky.outputs[0], wo.inputs['Surface'])
    sock_ramp(bg_sky.inputs['Strength'], [(1, 0.45), (e0, 0.45), (e1, 0.9)])

    # 工房の暗い背景：カメラにだけ見えるドーム
    m, nt = mat_new('工房ドーム')
    em = N(nt, 'ShaderNodeEmission', inputs={'Color': (0.026, 0.023, 0.021, 1), 'Strength': 1.0})
    trn = N(nt, 'ShaderNodeBsdfTransparent')
    att = N(nt, 'ShaderNodeAttribute', attribute_type='OBJECT', attribute_name='fade')
    msh = N(nt, 'ShaderNodeMixShader')
    L(nt, att.outputs['Fac'], msh.inputs[0])
    L(nt, trn.outputs[0], msh.inputs[1])
    L(nt, em.outputs[0], msh.inputs[2])
    L(nt, msh.outputs[0], out_node(nt).inputs['Surface'])
    m.surface_render_method = 'DITHERED'
    bpy.ops.mesh.primitive_uv_sphere_add(radius=2600, segments=48, ring_count=24, location=(0, 0, 0))
    dome = bpy.context.active_object
    dome.name = '工房ドーム'
    dome.data.materials.append(m)
    dome.visible_shadow = False
    dome.hide_probe_volume = dome.hide_probe_sphere = dome.hide_probe_plane = True
    ramp(dome, '["fade"]', e0, e1, 1.0, 0.0)
    show_between(dome, None, e1)
    # 巻物の下の暗い台
    M_DESK = mat_plain('台', (0.03, 0.027, 0.025), 0.7, reveal=False, noise=0.1)
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, PAPER_Z - 0.35))
    desk = bpy.context.active_object
    desk.name = '台'
    desk.data.materials.append(M_DESK)
    show_between(desk, None, e0)

    # 霞：金色に濃く、高いところほど薄く
    m, nt = mat_new('霞')
    vol = N(nt, 'ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.92, 0.76, 0.58, 1)
    vol.inputs['Anisotropy'].default_value = 0.6
    geo = N(nt, 'ShaderNodeNewGeometry')
    sep = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, geo.outputs['Position'], sep.inputs[0])
    hz = N(nt, 'ShaderNodeMapRange', inputs={1: 0.0, 2: 220.0, 3: 1.0, 4: 0.2})
    L(nt, sep.outputs['Z'], hz.inputs[0])
    # 手前（池）は澄んで、奥の山ほど霧が濃い
    dist = N(nt, 'ShaderNodeVectorMath', operation='DISTANCE')
    L(nt, geo.outputs['Position'], dist.inputs[0])
    dist.inputs[1].default_value = (60.0, 0.0, 0.0)
    hd = N(nt, 'ShaderNodeMapRange', inputs={1: 90.0, 2: 420.0, 3: 0.08, 4: 1.0})
    L(nt, dist.outputs['Value'], hd.inputs[0])
    hf = N(nt, 'ShaderNodeMath', operation='MULTIPLY')
    L(nt, hz.outputs[0], hf.inputs[0])
    L(nt, hd.outputs[0], hf.inputs[1])
    dval = N(nt, 'ShaderNodeValue')
    dmul = N(nt, 'ShaderNodeMath', operation='MULTIPLY')
    L(nt, hf.outputs[0], dmul.inputs[0])
    L(nt, dval.outputs[0], dmul.inputs[1])
    L(nt, dmul.outputs[0], vol.inputs['Density'])
    L(nt, vol.outputs[0], out_node(nt).inputs['Volume'])
    sock_ramp(dval.outputs[0], [(1, 0.0), (e0, 0.0), (e1, 0.0033)])
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-500, 0, 150))
    haze = bpy.context.active_object
    haze.name = '霞'
    haze.scale = (3400, 3400, 320)
    haze.data.materials.append(m)
    show_between(haze, e0, None)

    sun_d = bpy.data.lights.new('夕日', 'SUN')
    sun_d.color = (1.0, 0.6, 0.32)
    sun_d.angle = math.radians(0.8)
    sun = bpy.data.objects.new('夕日', sun_d)
    link(sun)
    sdir = Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))
    sun.rotation_euler = (-sdir).to_track_quat('-Z', 'Y').to_euler()
    sun_d.energy = 0.0
    sun_d.keyframe_insert('energy', frame=e0)
    sun_d.energy = 3.0
    sun_d.keyframe_insert('energy', frame=e1)
    # 工房の光：肉付けのあいだ、左手前から温かい斜光
    key_d = bpy.data.lights.new('工房の光', 'SUN')
    key_d.color = (1.0, 0.9, 0.78)
    key_d.angle = math.radians(8)
    key = bpy.data.objects.new('工房の光', key_d)
    link(key)
    key.rotation_euler = (math.radians(50), 0, math.radians(125))
    key_d.energy = 3.4
    key_d.keyframe_insert('energy', frame=e0)
    key_d.energy = 0.0
    key_d.keyframe_insert('energy', frame=e1)
    fill_d = bpy.data.lights.new('工房の補助光', 'SUN')
    fill_d.color = (0.85, 0.88, 1.0)
    fill_d.angle = math.radians(30)
    fill = bpy.data.objects.new('工房の補助光', fill_d)
    link(fill)
    fill.rotation_euler = (math.radians(55), 0, math.radians(-60))
    fill_d.energy = 0.9
    fill_d.keyframe_insert('energy', frame=e0)
    fill_d.energy = 0.0
    fill_d.keyframe_insert('energy', frame=e1)
