"""マテリアル（すべてプロシージャル）。建物の材質は「部材ごとの実体化」と「隅の汚れ（AO）」を共通で持つ。"""
from .common import mat_new, out_node, N, L, principled, texcoord

# init() で中身が入る。ほかのモジュールは MAT['ni'] のように参照する
MAT = {}
GLOW = {}     # 夕方にともる灯りの BSDF（発光の強さをキー打ちする）


def mat_wood(name, c0, c1, rough=0.7, reveal=True, grain=40.0):
    m, nt = mat_new(name)
    b = principled(nt, **{'Roughness': rough})
    v = texcoord(nt, 'Object', (1, 1, 1))
    mp = N(nt, 'ShaderNodeMapping', inputs={'Scale': (1.0, 1.0, grain)})
    L(nt, v, mp.inputs['Vector'])
    wave = N(nt, 'ShaderNodeTexWave', inputs={'Scale': 3.0, 'Distortion': 6.0, 'Detail': 3.0})
    wave.wave_type = 'RINGS'
    L(nt, mp.outputs[0], wave.inputs['Vector'])
    nz = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 8.0, 'Detail': 8.0})
    L(nt, v, nz.inputs['Vector'])
    mix = N(nt, 'ShaderNodeMix', data_type='FLOAT', inputs={'Factor': 0.5})
    L(nt, wave.outputs['Fac'], mix.inputs[2])
    L(nt, nz.outputs['Fac'], mix.inputs[3])
    cr = N(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (*c0, 1)
    cr.color_ramp.elements[1].color = (*c1, 1)
    L(nt, mix.outputs[0], cr.inputs[0])
    L(nt, cr.outputs[0], b.inputs['Base Color'])
    bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.15, 'Distance': 0.005})
    L(nt, mix.outputs[0], bump.inputs['Height'])
    L(nt, bump.outputs[0], b.inputs['Normal'])
    return finish(m, nt, b, reveal)


def mat_plain(name, col, rough=0.8, reveal=True, noise=0.08, metal=0.0):
    m, nt = mat_new(name)
    b = principled(nt, **{'Base Color': (*col, 1), 'Roughness': rough, 'Metallic': metal})
    if noise:
        v = texcoord(nt, 'Object', (1, 1, 1))
        nz = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 6.0, 'Detail': 8.0})
        L(nt, v, nz.inputs['Vector'])
        cr = N(nt, 'ShaderNodeValToRGB')
        cr.color_ramp.elements[0].color = tuple(max(0, c * (1 - noise * 2)) for c in col) + (1,)
        cr.color_ramp.elements[1].color = tuple(min(1, c * (1 + noise)) for c in col) + (1,)
        L(nt, nz.outputs['Fac'], cr.inputs[0])
        L(nt, cr.outputs[0], b.inputs['Base Color'])
        bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.1})
        L(nt, nz.outputs['Fac'], bump.inputs['Height'])
        L(nt, bump.outputs[0], b.inputs['Normal'])
    return finish(m, nt, b, reveal)

# ---------------------------------------------------------------------------
# 部材ごとの実体化：頂点属性 ord（0〜1、中堂から外へ）と、オブジェクトの prog を比べる
def ord_alpha(nt):
    att = N(nt, 'ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='ord')
    prog = N(nt, 'ShaderNodeAttribute', attribute_type='OBJECT', attribute_name='prog')
    sub = N(nt, 'ShaderNodeMath', operation='SUBTRACT')
    L(nt, prog.outputs['Fac'], sub.inputs[0])
    L(nt, att.outputs['Fac'], sub.inputs[1])
    a = N(nt, 'ShaderNodeMapRange', inputs={1: 0.0, 2: 0.06, 3: 0.0, 4: 1.0})
    L(nt, sub.outputs[0], a.inputs[0])
    return a.outputs[0]


def finish(m, nt, bsdf, reveal=False):
    # 隅の暗がり（AO）で汚れと奥行き
    bc = bsdf.inputs['Base Color']
    src = bc.links[0].from_socket if bc.links else None
    ao = N(nt, 'ShaderNodeAmbientOcclusion', inputs={'Distance': 0.5})
    ao.samples = 8
    aor = N(nt, 'ShaderNodeMapRange', inputs={1: 0.0, 2: 1.0, 3: 0.45, 4: 1.0})
    L(nt, ao.outputs['AO'], aor.inputs[0])
    mul = N(nt, 'ShaderNodeMix', data_type='RGBA', inputs={'Factor': 1.0})
    mul.blend_type = 'MULTIPLY'
    if src:
        L(nt, src, mul.inputs[6])
    else:
        mul.inputs[6].default_value = bc.default_value
    L(nt, aor.outputs[0], mul.inputs[7])
    L(nt, mul.outputs[2], bc)
    if reveal:
        L(nt, ord_alpha(nt), bsdf.inputs['Alpha'])
        m.surface_render_method = 'DITHERED'
        try:
            m.use_transparent_shadow = True
        except Exception:
            pass
    L(nt, bsdf.outputs[0], out_node(nt).inputs['Surface'])
    return m


def mat_ni(name='丹塗り', col=(0.56, 0.12, 0.04)):
    """丹塗り：少し退色したムラと、角の擦れ"""
    m, nt = mat_new(name)
    b = principled(nt, **{'Base Color': (*col, 1), 'Roughness': 0.55})
    v = texcoord(nt, 'Object')
    nz = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 3.0, 'Detail': 8.0, 'Roughness': 0.6})
    L(nt, v, nz.inputs['Vector'])
    cr = N(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (col[0] * 0.72, col[1] * 0.7, col[2] * 0.8, 1)
    cr.color_ramp.elements[1].color = (min(1, col[0] * 1.08), col[1] * 1.15, col[2] * 1.1, 1)
    L(nt, nz.outputs['Fac'], cr.inputs[0])
    L(nt, cr.outputs[0], b.inputs['Base Color'])
    bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.08})
    L(nt, nz.outputs['Fac'], bump.inputs['Height'])
    L(nt, bump.outputs[0], b.inputs['Normal'])
    return finish(m, nt, b, True)


def mat_tile(name='本瓦'):
    """本瓦葺：平瓦の段と、いぶし銀のムラ"""
    m, nt = mat_new(name)
    b = principled(nt, **{'Roughness': 0.5, 'Metallic': 0.15})
    tc = N(nt, 'ShaderNodeTexCoord')
    br = N(nt, 'ShaderNodeTexBrick', inputs={'Scale': 1.0, 'Mortar Size': 0.01, 'Brick Width': 0.34, 'Row Height': 0.26,
                                                 'Color1': (0.15, 0.115, 0.085, 1), 'Color2': (0.10, 0.08, 0.06, 1),
                                                 'Mortar': (0.03, 0.03, 0.03, 1)})
    br.offset = 0.0
    L(nt, tc.outputs['UV'], br.inputs['Vector'])
    nz = N(nt, 'ShaderNodeTexNoise', inputs={'Scale': 4.0, 'Detail': 8.0})
    L(nt, tc.outputs['UV'], nz.inputs['Vector'])
    mix = N(nt, 'ShaderNodeMix', data_type='RGBA', inputs={'Factor': 0.3})
    mix.blend_type = 'MULTIPLY'
    L(nt, br.outputs['Color'], mix.inputs[6])
    L(nt, nz.outputs['Color'], mix.inputs[7])
    L(nt, mix.outputs[2], b.inputs['Base Color'])
    bump = N(nt, 'ShaderNodeBump', inputs={'Strength': 0.5, 'Distance': 0.02})
    L(nt, br.outputs['Fac'], bump.inputs['Height'])
    L(nt, bump.outputs[0], b.inputs['Normal'])
    return finish(m, nt, b, True)


def mat_ink():
    """墨線：オブジェクトの fade と、部材が実体化した分だけ消える"""
    m, nt = mat_new('墨線')
    b = principled(nt, **{'Base Color': (0.02, 0.018, 0.016, 1), 'Roughness': 0.9})
    fade = N(nt, 'ShaderNodeAttribute', attribute_type='OBJECT', attribute_name='fade')
    inv = N(nt, 'ShaderNodeMath', operation='SUBTRACT', inputs={0: 1.0})
    L(nt, ord_alpha(nt), inv.inputs[1])
    mul = N(nt, 'ShaderNodeMath', operation='MULTIPLY')
    L(nt, fade.outputs['Fac'], mul.inputs[0])
    L(nt, inv.outputs[0], mul.inputs[1])
    L(nt, mul.outputs[0], b.inputs['Alpha'])
    m.surface_render_method = 'DITHERED'
    L(nt, b.outputs[0], out_node(nt).inputs['Surface'])
    return m


def mat_glow(name='灯り'):
    m, nt = mat_new(name)
    b = principled(nt, **{'Base Color': (0.9, 0.8, 0.6, 1), 'Roughness': 0.6,
                          'Emission Color': (1.0, 0.62, 0.28, 1), 'Emission Strength': 0.0})
    return finish(m, nt, b, True), b


def init():
    MAT.update(
        ni=mat_ni(),
        tile=mat_tile(),
        wood=mat_wood('床板', (0.16, 0.10, 0.06), (0.30, 0.20, 0.12)),
        plaster=mat_plain('白壁', (0.86, 0.84, 0.79), 0.9, noise=0.04),
        stone=mat_plain('石', (0.34, 0.33, 0.31), 0.85, noise=0.18),
        ochre=mat_plain('黄土', (0.80, 0.58, 0.22), 0.6, noise=0.05),
        gold=mat_plain('金具', (0.85, 0.62, 0.25), 0.3, noise=0.05, metal=1.0),
        black=mat_plain('黒', (0.03, 0.028, 0.026), 0.6, noise=0.02),
        ink=mat_ink(),
    )
    MAT['glow'], GLOW['bsdf'] = mat_glow()
    return MAT
