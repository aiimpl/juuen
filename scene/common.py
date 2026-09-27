"""シーン全体で共有する定数・時間割り・Blender の補助関数。"""
import os
import random

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')

FPS = 24
F_END = 504          # 1〜24 コマは描かない（冒頭 1 秒カット）。本編は 25〜504 の 480 コマ＝20 秒

# 時間割り（コマ番号）。本編の t 秒 = (コマ - 25) / 24
T = dict(
    unroll=(25, 61),                 # 巻物が広がる
    rise=(108, 134),                 # 墨線が紙から立ち上がる
    p1=(132, 162),                   # 基壇・床
    p2=(152, 192),                   # 柱
    p3=(178, 216),                   # 梁・壁・扉・欄間・組物
    p4=(204, 254),                   # 屋根
    p5=(246, 276),                   # 高欄・鳳凰・灯籠・反橋
    vanish=(296, 326),               # 紙が消える
    env=(296, 334),                  # 森・空・霞が現れる
    flood=(316, 380),                # 干潟に水が満ちる
    lights=(330, 360),               # 灯りがともる
)

PAPER_Z = 0.3        # 巻物の紙の高さ（墨線はここから立ち上がる）

# 部材の実体化の順番のゆらぎなどに使う乱数（呼び出し順で結果が決まる）
rnd = random.Random(7)


def scene():
    return bpy.context.scene


def link(ob, coll=None):
    (coll or scene().collection).objects.link(ob)
    return ob


def new_coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene().collection).children.link(c)
    return c


def fcurves_of(action):
    """アクションの F カーブを全部返す（Blender 5 のレイヤー式アクションにも対応）"""
    if hasattr(action, 'fcurves') and not hasattr(action, 'layers'):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def ramp(obj, path, f0, f1, v0, v1):
    """obj の path（カスタムプロパティは '["name"]'）を f0→f1 で v0→v1 にキー打ち"""
    for f, v in ((f0, v0), (f1, v1)):
        if path.startswith('['):
            obj[path[2:-2]] = v
        else:
            setattr(obj, path, v)
        obj.keyframe_insert(path, frame=f)


def sock_ramp(sock, keys):
    """ノードのソケット値に [(コマ, 値), ...] をキー打ち"""
    for f, v in keys:
        sock.default_value = v
        sock.keyframe_insert('default_value', frame=f)


def show_between(ob, f_on=None, f_off=None):
    """レンダーでの表示を切り替える（f_on から表示、f_off の次のコマから非表示）"""
    if f_on is not None:
        ob.hide_render = True
        ob.keyframe_insert('hide_render', frame=1)
        ob.hide_render = False
        ob.keyframe_insert('hide_render', frame=f_on)
    if f_off is not None:
        ob.hide_render = False
        ob.keyframe_insert('hide_render', frame=f_off)
        ob.hide_render = True
        ob.keyframe_insert('hide_render', frame=f_off + 1)


def constant_visibility_keys():
    """hide_render のキーは補間せずに一瞬で切り替える"""
    for ob in bpy.data.objects:
        ad = ob.animation_data
        if ad and ad.action:
            for fc in fcurves_of(ad.action):
                if fc.data_path == 'hide_render':
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'CONSTANT'


# ---- シェーダーノードの補助 ----------------------------------------------------
def mat_new(name):
    """出力ノードだけを残した新しいマテリアル"""
    m = bpy.data.materials.new(name)
    if m.node_tree is None:          # Blender 4.x 以前
        m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    return m, nt


def out_node(nt):
    return [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]


def N(nt, t, **kw):
    """ノードを足す。inputs={名前or番号: 値} で入力の既定値、その他はノードの属性"""
    n = nt.nodes.new(t)
    for k, v in kw.items():
        if k == 'inputs':
            for kk, vv in v.items():
                n.inputs[kk].default_value = vv
        else:
            setattr(n, k, v)
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def principled(nt, **inputs):
    b = N(nt, 'ShaderNodeBsdfPrincipled')
    for k, v in inputs.items():
        b.inputs[k].default_value = v
    return b


def texcoord(nt, kind='Object', scale=(1, 1, 1)):
    tc = N(nt, 'ShaderNodeTexCoord')
    mp = N(nt, 'ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    L(nt, tc.outputs[kind], mp.inputs['Vector'])
    return mp.outputs['Vector']
