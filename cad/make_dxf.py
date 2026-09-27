"""DXF 図面（単位 mm、A2 横 594x420、表題欄つき）を3枚書く。
  01 配置図 1:600 / 02 社殿群平面図 1:300 / 03 中堂東立面図・石灯籠 1:200
"""
import os
import random
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import geometry as G  # noqa: E402

OUT = os.path.join(ROOT, 'build', 'dxf')
A2 = (594.0, 420.0)


def new_doc():
    doc = ezdxf.new('R2010', setup=True)
    doc.header['$INSUNITS'] = 4  # mm
    doc.header['$MEASUREMENT'] = 1
    doc.styles.new('JP', dxfattribs={'font': 'msmincho.ttc'})
    for name, color, lw in [('枠', 7, 50), ('表題', 7, 25), ('外形', 7, 50), ('柱', 7, 35),
                            ('通り芯', 1, 13), ('細線', 8, 13), ('池', 5, 25), ('植栽', 3, 18),
                            ('文字', 7, 18), ('寸法', 2, 13), ('屋根', 7, 35)]:
        doc.layers.add(name, color=color, lineweight=lw)
    doc.linetypes.add('CENTER2', pattern=[12.0, 8.0, -1.5, 1.0, -1.5], description='Center ____ _ ____')
    return doc


def text(msp, s, x, y, h, layer='文字', align=TextEntityAlignment.LEFT, rot=0):
    t = msp.add_text(s, height=h, rotation=rot, dxfattribs={'layer': layer, 'style': 'JP'})
    t.set_placement((x, y), align=align)
    return t


def frame(msp, title, scale, no):
    W, H = A2
    msp.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True, dxfattribs={'layer': '細線'})
    msp.add_lwpolyline([(10, 10), (W - 10, 10), (W - 10, H - 10), (10, H - 10)], close=True, dxfattribs={'layer': '枠'})
    # 表題欄 右下 180x50
    x0, y0, x1, y1 = W - 190, 10, W - 10, 60
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={'layer': '枠'})
    for y in (22, 34, 46):
        msp.add_line((x0, y), (x1, y), dxfattribs={'layer': '表題'})
    msp.add_line((x0 + 40, y0), (x0 + 40, y1), dxfattribs={'layer': '表題'})
    msp.add_line((x0 + 120, y0), (x0 + 120, 34), dxfattribs={'layer': '表題'})
    rows = [('工事名', '平等院鳳凰堂 イメージ図', 49.5),
            ('図面名', title, 37.5), ('縮尺', scale, 25.5), ('図番', no, 13.5)]
    for k, v, y in rows:
        text(msp, k, x0 + 4, y, 3.5)
        text(msp, v, x0 + 44, y, 4.5 if k != '工事名' else 4.0)
    text(msp, '用紙 A2', x0 + 124, 25.5, 3.2)
    text(msp, '単位 mm', x0 + 124, 13.5, 3.2)
    text(msp, '※実測図ではありません（一般的な外観をもとにした作図）', 14, 13, 3.0)


def north(msp, x, y, r=10):
    msp.add_circle((x, y), r, dxfattribs={'layer': '細線'})
    msp.add_lwpolyline([(x, y + r), (x - r * 0.35, y - r * 0.6), (x, y - r * 0.25), (x + r * 0.35, y - r * 0.6)],
                       close=True, dxfattribs={'layer': '外形'})
    text(msp, 'N', x, y + r + 2, 4, align=TextEntityAlignment.BOTTOM_CENTER)


def scalebar(msp, x, y, scale, meters):
    L = meters * 1000 / scale
    n = 5
    for i in range(n):
        xa = x + L * i / n
        pts = [(xa, y), (xa + L / n, y), (xa + L / n, y + 2), (xa, y + 2)]
        if i % 2 == 0:
            msp.add_solid(pts[:2] + pts[:1:-1], dxfattribs={'layer': '外形'})
        msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': '外形'})
    text(msp, '0', x, y + 4, 2.5)
    text(msp, f'{meters}m', x + L, y + 4, 2.5, align=TextEntityAlignment.BOTTOM_CENTER)


def M(scale, ox, oy):
    k = 1000.0 / scale
    return lambda x, y: (ox + x * k, oy + y * k)


def poly(msp, pts, T, layer, close=True):
    msp.add_lwpolyline([T(*p) for p in pts], close=close, dxfattribs={'layer': layer})


def rect(msp, T, x0, y0, x1, y1, layer):
    poly(msp, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], T, layer)


def col(msp, T, x, y, size, k, layer='柱'):
    s = size * k / 2
    cx, cy = T(x, y)
    msp.add_lwpolyline([(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)], close=True,
                       dxfattribs={'layer': layer})


def dim_h(msp, p0, p1, y):
    d = msp.add_linear_dim(base=(p0[0], y), p1=p0, p2=p1, dimstyle='EZDXF',
                           override={'dimtxt': 2.5, 'dimasz': 2.0, 'dimclrd': 2, 'dimclre': 2, 'dimexe': 1.5})
    d.render()


def dim_v(msp, p0, p1, x):
    d = msp.add_linear_dim(base=(x, p0[1]), p1=p0, p2=p1, angle=90, dimstyle='EZDXF',
                           override={'dimtxt': 2.5, 'dimasz': 2.0, 'dimclrd': 2, 'dimclre': 2, 'dimexe': 1.5})
    d.render()


# ---------------------------------------------------------------------------
def plan_draw(msp, T, k, detail=True):
    for ln in G.plan_lines():
        msp.add_line(T(ln[0], ln[1]), T(ln[2], ln[3]), dxfattribs={'layer': '外形'})
    for (x, y, z0, z1, kind) in G.columns():
        col(msp, T, x, y, 0.45 if kind in ('core', 'moko') else 0.34, k)


def sheet_site():
    doc = new_doc()
    msp = doc.modelspace()
    frame(msp, '配置図', '1:600', 'B-01')
    sc = 600
    k = 1000 / sc
    T = M(sc, 284, 238)
    poly(msp, G.POND, T, '池')
    poly(msp, G.offset_poly(G.POND, 1.5), T, '細線')
    poly(msp, G.ISLAND, T, '外形')
    poly(msp, G.offset_poly(G.ISLAND, -1.2), T, '細線')
    for x, y, r in G.ROCKS:
        msp.add_circle(T(x, y), r * k, dxfattribs={'layer': '外形'})
    plan_draw(msp, T, k)
    for x, y in (G.LANTERN_FRONT,):
        col(msp, T, x, y, 1.2, k, '外形')
    text(msp, '鳳凰堂', *T(0, -3.5), 3.5, align=TextEntityAlignment.TOP_CENTER)
    text(msp, '阿字池', *T(60, -25), 6.0, align=TextEntityAlignment.MIDDLE_CENTER)
    text(msp, '洲浜', *T(15, 6), 3.0)
    text(msp, '反橋', *T(5, 34), 3.0)
    rnd = random.Random(3)
    for i in range(420):
        x, y = rnd.uniform(-240, 200), rnd.uniform(-100, 100)
        if G.point_in_poly(x, y, G.POND) or G.dist_to_poly(x, y, G.POND) < 3:
            continue
        p = T(x, y)
        if not (15 < p[0] < 579 and 65 < p[1] < 405):
            continue
        if (p[1] > 380 and p[0] < 230) or (abs(p[0] - 545) < 25 and abs(p[1] - 378) < 28):
            continue
        msp.add_circle(p, rnd.uniform(2.0, 3.5) * k, dxfattribs={'layer': '植栽'})
    north(msp, 545, 375)
    scalebar(msp, 40, 30, sc, 50)
    text(msp, '配置図  S=1:600', 40, 395, 7)
    doc.saveas(os.path.join(OUT, 'B-01_配置図_1-600.dxf'))


def sheet_plan():
    doc = new_doc()
    msp = doc.modelspace()
    frame(msp, '社殿群平面図', '1:300', 'B-02')
    sc = 300
    k = 1000 / sc
    # 東を下に（正面を手前に）：x→-縦、y→横
    ox, oy = 297, 250

    def T(x, y):
        return (ox + y * k, oy - x * k)
    poly(msp, G.ISLAND, T, '細線')
    plan_draw(msp, T, k)
    # 通り芯（中堂）
    for y in G.MOKO_Y:
        msp.add_line(T(9, y), T(-8, y), dxfattribs={'layer': '通り芯', 'linetype': 'CENTER2'})
    for x in G.MOKO_X:
        msp.add_line(T(x, -10), T(x, 10), dxfattribs={'layer': '通り芯', 'linetype': 'CENTER2'})
    # 寸法
    dim_h(msp, T(9.5, G.MOKO_Y[0]), T(9.5, G.MOKO_Y[-1]), T(11.5, 0)[1])
    dim_h(msp, T(11, -G.TOWER['y'] - G.TOWER['half']), T(11, G.TOWER['y'] + G.TOWER['half']), T(15, 0)[1])
    dim_v(msp, T(G.MOKO_X[-1], G.MOKO_Y[-1]), T(G.MOKO_X[0], G.MOKO_Y[-1]), T(0, 11)[0])
    dim_v(msp, T(G.TAIL['x1'], G.TAIL['half']), T(G.TAIL['x0'], G.TAIL['half']), T(0, 4.5)[0])
    for lbl, x, y in [('中堂', 1.2, 0), ('北翼廊', -4.2, 15.3), ('南翼廊', -4.2, -15.3), ('尾廊', -15, 3.2),
                      ('隅楼', -1.5, 26.5), ('隅楼', -1.5, -26.5)]:
        text(msp, lbl, *T(x, y), 3.5, align=TextEntityAlignment.MIDDLE_CENTER)
    text(msp, '↓ 正面（東）', *T(14, 0), 3.5, align=TextEntityAlignment.TOP_CENTER)
    scalebar(msp, 40, 30, sc, 10)
    text(msp, '社殿群平面図  S=1:300', 40, 395, 7)
    doc.saveas(os.path.join(OUT, 'B-02_社殿群平面図_1-300.dxf'))


def roof_el(msp, T, half, over, eave, top, lift, top_half):
    A = half + over
    e = [(u * A, eave + G.eave_lift(abs(u), lift)) for u in [i / 20 - 1 for i in range(41)]]
    side = [(A + (top_half - A) * t, eave + lift + (top - eave - lift) * G.roof_profile(t)) for t in [i / 20 for i in range(21)]]
    poly(msp, e, T, '屋根', close=False)
    poly(msp, [(x, z - 0.3) for x, z in e], T, '細線', close=False)
    poly(msp, side, T, '屋根', close=False)
    poly(msp, [(-x, z) for x, z in side], T, '屋根', close=False)
    msp.add_line(T(side[-1][0], side[-1][1]), T(-side[-1][0], side[-1][1]), dxfattribs={'layer': '屋根'})


def sheet_elev():
    doc = new_doc()
    msp = doc.modelspace()
    frame(msp, '中堂東立面図・石灯籠', '1:200', 'B-03')
    sc = 200
    T = M(sc, 250, 140)          # 横＝南北(y)、縦＝高さ
    msp.add_line(T(-32, 0), T(32, 0), dxfattribs={'layer': '池'})
    text(msp, '池水面 ±0', *T(27, 0.3), 2.5)
    p = G.PODIUM
    rect(msp, T, p['y0'], p['z0'] + 0.6, p['y1'], p['z1'], '外形')
    # 裳階と身舎の柱
    for y in G.MOKO_Y:
        rect(msp, T, y - 0.19, G.FLOOR, y + 0.19, G.MOKO['top'], '柱')
    for y in G.CORE_Y:
        rect(msp, T, y - 0.24, G.MOKO['top'] + 0.9, y + 0.24, G.CORE_TOP, '柱')
    rect(msp, T, G.CORE_Y[0], G.MOKO['top'] + 0.9, G.CORE_Y[-1], G.CORE_TOP, '外形')
    for i in range(3):
        a, c = G.CORE_Y[i] + 0.3, G.CORE_Y[i + 1] - 0.3
        rect(msp, T, a, G.FLOOR + 0.1, c, G.FLOOR + 3.6, '細線')
    roof_el(msp, T, (G.MOKO_Y[-1] - G.MOKO_Y[0]) / 2, G.MOKO['over'], G.MOKO['eave'], 5.25, G.MOKO['lift'], G.CORE_Y[-1] + 0.25)
    roof_el(msp, T, G.CORE_Y[-1], G.ROOF['over'], G.ROOF['eave'], G.ROOF['top'], G.ROOF['lift'], G.RIDGE_HALF)
    for (x, y, z) in G.PHOENIX:
        poly(msp, [(y - 0.6, z + 0.6), (y, z + 1.6), (y + 0.7, z + 1.2), (y + 0.2, z + 0.9), (y + 0.5, z + 0.6)], T, '外形')
    text(msp, '鳳凰', *T(3.3, G.ROOF['top'] + 2.0), 2.8, align=TextEntityAlignment.BOTTOM_CENTER)
    # 翼廊と隅楼
    for s in (-1, 1):
        y0, y1 = sorted((s * G.WING_Y0, s * G.WING_Y1))
        for y in G.grid_between(y0, y1, G.BAY_W):
            rect(msp, T, y - 0.15, G.W_FLOOR, y + 0.15, G.W_TOP, '柱')
        rect(msp, T, y0, G.W_UPPER - 0.1, y1, G.W_UPPER + 0.05, '外形')
        rect(msp, T, y0, G.W_UPPER + 0.05, y1, G.W_UPPER + 0.8, '細線')
        poly(msp, [(y0 - 1.1, G.W_ROOF['eave']), (y1 + 1.1, G.W_ROOF['eave']), (y1 + 0.4, G.W_ROOF['top']), (y0 - 0.4, G.W_ROOF['top'])], T, '屋根')
        yc = s * G.TOWER['y']
        h = G.TOWER['half']
        rect(msp, T, yc - h, G.W_TOP, yc + h, G.T_ROOF['eave'] - 0.35, '外形')
        rel = [(yc + u, z) for u, z in [(-h - 1.35, G.T_ROOF['eave']), (0, G.T_ROOF['top']), (h + 1.35, G.T_ROOF['eave'])]]
        poly(msp, rel, T, '屋根', close=False)
    X = -31
    for za, zb in [(0, G.FLOOR), (G.FLOOR, G.MOKO['top']), (G.MOKO['top'], G.CORE_TOP), (G.CORE_TOP, G.ROOF['top'])]:
        dim_v(msp, T(G.MOKO_Y[0], za), T(G.MOKO_Y[0], zb), T(X, 0)[0])
    text(msp, '中堂東立面図（翼廊・隅楼を含む）  S=1:200', 250, 115, 4.5, align=TextEntityAlignment.TOP_CENTER)
    # 中堂前の石灯籠
    T2 = M(sc, 520, 140)
    s = 1.0
    z0 = 0.35
    for (w, za, zb) in [(0.84, 0, 0.28), (0.26, 0.28, 1.25), (0.72, 1.25, 1.45), (0.6, 1.45, 1.95), (1.24, 1.95, 2.3), (0.28, 2.3, 2.6)]:
        rect(msp, T2, -w * s / 2, z0 + za * s, w * s / 2, z0 + zb * s, '外形')
    rect(msp, T2, -1.2, 0.0, 1.2, z0, '細線')
    text(msp, '中堂前の石灯籠 立面  S=1:200', 520, 115, 4.5, align=TextEntityAlignment.TOP_CENTER)
    text(msp, '中堂・翼廊：丹塗り・白壁・本瓦葺　組物：三手先　棟：鳳凰一対', 40, 72, 3.5)
    scalebar(msp, 40, 30, sc, 10)
    text(msp, '中堂東立面図・石灯籠  S=1:200', 40, 395, 7)
    doc.saveas(os.path.join(OUT, 'B-03_中堂東立面図_1-200.dxf'))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    sheet_site()
    sheet_plan()
    sheet_elev()
    print('ok')
