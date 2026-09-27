"""墨のワイヤーフレーム：部材メッシュの辺をそのまま墨線（細い管）にし、紙から立ち上げる。
線は部材と同じ ord を持ち、その部材が実体化した瞬間に消える。
"""
import bpy

from .common import T, PAPER_Z, link, new_coll, show_between
from .materials import MAT


def ink_node_group():
    gn = bpy.data.node_groups.new('墨線化', 'GeometryNodeTree')
    gn.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    gn.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi = gn.nodes.new('NodeGroupInput')
    go = gn.nodes.new('NodeGroupOutput')
    m2c = gn.nodes.new('GeometryNodeMeshToCurve')
    cc = gn.nodes.new('GeometryNodeCurvePrimitiveCircle')
    cc.inputs['Resolution'].default_value = 4
    cc.inputs['Radius'].default_value = 0.016
    c2m = gn.nodes.new('GeometryNodeCurveToMesh')
    smat = gn.nodes.new('GeometryNodeSetMaterial')
    smat.inputs['Material'].default_value = MAT['ink']
    gn.links.new(gi.outputs[0], m2c.inputs['Mesh'])
    gn.links.new(m2c.outputs[0], c2m.inputs['Curve'])
    gn.links.new(cc.outputs[0], c2m.inputs['Profile Curve'])
    gn.links.new(c2m.outputs[0], smat.inputs['Geometry'])
    gn.links.new(smat.outputs[0], go.inputs[0])
    return gn


def build(phase_objs):
    coll = new_coll('墨線')
    rise = bpy.data.objects.new('墨線_立ち上がり', None)
    link(rise, coll)
    rise.location = (0, 0, PAPER_Z + 0.01)
    bpy.context.view_layer.update()
    gn = ink_node_group()
    for k, ob in phase_objs.items():
        w = bpy.data.objects.new('墨線_' + k, ob.data)      # 部材と同じメッシュを共有
        link(w, coll)
        w.parent = rise
        w.matrix_parent_inverse = rise.matrix_world.inverted()
        w.modifiers.new('墨線', 'NODES').node_group = gn
        w['fade'] = 1.0
        f0, f1 = T[k]
        w['prog'] = -0.2
        w.keyframe_insert('["prog"]', frame=1)
        w.keyframe_insert('["prog"]', frame=f0)
        w['prog'] = 1.08
        w.keyframe_insert('["prog"]', frame=f1)
        show_between(w, T['rise'][0] - 2, f1 + 1)
    # 紙に貼りついた平面から、高さ方向に伸ばして立ち上げる
    rise.scale = (1, 1, 0.003)
    rise.keyframe_insert('scale', frame=T['rise'][0])
    rise.scale = (1, 1, 1)
    rise.keyframe_insert('scale', frame=T['rise'][1])
