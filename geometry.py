"""平等院鳳凰堂をイメージした共通の寸法データ（実測ではなく、一般的な外観をもとにした作図）。
単位 m、x=東（正面） y=北 z=上、原点=中堂の中心。
DXF・巻物の図・Blender のシーンが全部これを読むので、図面と立体の位置が一致する。
"""
import math

# ---- 中堂 ------------------------------------------------------------------
CORE_Y = [-4.8, -1.6, 1.6, 4.8]          # 身舎 桁行3間（南北）
CORE_X = [-3.6, 0.0, 3.6]                # 身舎 梁間2間（東西）
MOKO_Y = [-7.1, -4.8, -1.6, 1.6, 4.8, 7.1]   # 裳階
MOKO_X = [-5.9, -3.6, 0.0, 3.6, 5.9]
PODIUM = dict(x0=-7.3, x1=7.3, y0=-8.5, y1=8.5, z0=-0.6, z1=0.75)
FLOOR = 0.95
MOKO = dict(top=4.25, eave=4.35, over=1.5, lift=0.35)     # 裳階の屋根
CORE_TOP = 7.3
ROOF = dict(eave=7.55, over=2.5, lift=0.75, top=12.2)     # 大屋根（入母屋を寄棟＋破風で）
RIDGE_HALF = 3.4                                          # 大棟の半分の長さ（南北）
PHOENIX = [(0.0, -3.3, 12.35), (0.0, 3.3, 12.35)]

# ---- 翼廊（南北対称） ------------------------------------------------------
WING_X = -1.5          # 翼廊の中心線（東西）
WING_W = 3.2
WING_Y0, WING_Y1 = 9.2, 21.5
BAY_W = 2.45
TOWER = dict(y=23.3, half=1.9)
FWD_X0, FWD_X1 = 0.35, 9.6     # 隅楼から東へ折れる部分
W_FLOOR = 0.55
W_UPPER = 3.55
W_TOP = 6.3
W_ROOF = dict(eave=6.45, over=1.15, lift=0.3, top=8.0)
T_ROOF = dict(eave=8.7, over=1.35, lift=0.45, top=11.3)

# ---- 尾廊 ------------------------------------------------------------------
TAIL = dict(x0=-24.0, x1=-5.9, half=1.5, floor=0.95, top=3.5)
TAIL_ROOF = dict(eave=3.7, over=1.0, lift=0.2, top=5.1)

# ---- 庭（阿字池） ----------------------------------------------------------
def catmull(pts, n=10):
    out = []
    m = len(pts)
    for i in range(m):
        p0, p1, p2, p3 = pts[(i - 1) % m], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    return out


POND = catmull([(-40, -58), (-4, -54), (40, -60), (100, -70), (150, -64), (175, -30), (178, 10), (160, 48),
                (100, 60), (40, 56), (-6, 50), (-50, 62), (-120, 58), (-158, 20), (-160, -24), (-118, -62)], 8)
# 中島：中堂と翼廊が乗る。前は洲浜
ISLAND = catmull([(-9, -27.5), (4, -28.5), (12.5, -26.5), (13.5, -12), (12.2, 0), (13.5, 12), (12.5, 26.5),
                  (4, 28.5), (-9, 27.5), (-11, 12), (-10.5, 2.5), (-10.5, -2.5), (-11, -12)], 8)
ROCKS = [(16, -34, 1.2), (22, 18, 1.0), (30, -8, 0.9), (38, 30, 1.1), (44, -30, 1.0), (-20, 34, 1.2), (-22, -36, 1.1),
         (60, 8, 0.8), (18, 36, 0.9), (82, -40, 1.3), (90, 22, 1.1), (70, -12, 0.9)]
LANTERN_FRONT = (10.4, 0.0)
BRIDGE = dict(x=3.0, y0=27.5, y1=40.0, w=2.4, rise=1.3)   # 北の反橋
SCROLL = dict(x0=-33.0, x1=23.0, y0=-32.0, y1=32.0)


def grid_between(a, b, step):
    n = max(1, round(abs(b - a) / step))
    return [a + (b - a) * i / n for i in range(n + 1)]


def wing_segments():
    """翼廊の直線部（x0,x1,y0,y1, 棟の向き 'y' or 'x'）"""
    segs = []
    for s in (-1, 1):
        y0, y1 = sorted((s * WING_Y0, s * WING_Y1))
        segs.append((WING_X - WING_W / 2, WING_X + WING_W / 2, y0, y1, 'y'))
        yc = s * TOWER['y']
        segs.append((FWD_X0, FWD_X1, yc - WING_W / 2, yc + WING_W / 2, 'x'))
    return segs


def columns():
    """(x, y, z0, z1, 種類)"""
    cols = []
    for x in MOKO_X:
        for y in MOKO_Y:
            if x in (MOKO_X[0], MOKO_X[-1]) or y in (MOKO_Y[0], MOKO_Y[-1]):
                cols.append((x, y, FLOOR, MOKO['top'], 'moko'))
    for x in CORE_X:
        for y in CORE_Y:
            cols.append((x, y, FLOOR, CORE_TOP, 'core'))
    for (x0, x1, y0, y1, d) in wing_segments():
        if d == 'y':
            for y in grid_between(y0, y1, BAY_W):
                for x in (x0, x1):
                    cols.append((x, y, W_FLOOR, W_TOP, 'wing'))
        else:
            for x in grid_between(x0, x1, BAY_W):
                for y in (y0, y1):
                    cols.append((x, y, W_FLOOR, W_TOP, 'wing'))
    for s in (-1, 1):
        yc = s * TOWER['y']
        h = TOWER['half']
        for x in (WING_X - h, WING_X + h):
            for y in (yc - h, yc + h):
                cols.append((x, y, W_FLOOR, T_ROOF['eave'] - 0.3, 'tower'))
    for x in grid_between(TAIL['x0'], TAIL['x1'] - 0.3, 2.4):
        for y in (-TAIL['half'], TAIL['half']):
            cols.append((x, y, TAIL['floor'], TAIL['top'], 'tail'))
    return cols


def plan_lines():
    """巻物・DXF 用の平面線 [(x0,y0,x1,y1)]"""
    L = []

    def rect(x0, y0, x1, y1):
        L.extend([(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)])

    p = PODIUM
    rect(p['x0'], p['y0'], p['x1'], p['y1'])
    rect(MOKO_X[0], MOKO_Y[0], MOKO_X[-1], MOKO_Y[-1])
    rect(CORE_X[0], CORE_Y[0], CORE_X[-1], CORE_Y[-1])
    o = ROOF['over']
    rect(CORE_X[0] - o, CORE_Y[0] - o, CORE_X[-1] + o, CORE_Y[-1] + o)
    for (x0, x1, y0, y1, d) in wing_segments():
        rect(x0, y0, x1, y1)
        rect(x0 - 0.9, y0 - (0.9 if d == 'x' else 0), x1 + 0.9, y1 + (0.9 if d == 'x' else 0))
    for s in (-1, 1):
        yc = s * TOWER['y']
        h = TOWER['half']
        rect(WING_X - h, yc - h, WING_X + h, yc + h)
        rect(WING_X - h - 1.3, yc - h - 1.3, WING_X + h + 1.3, yc + h + 1.3)
        L.append((WING_X - h, yc - h, WING_X + h, yc + h))
        L.append((WING_X - h, yc + h, WING_X + h, yc - h))
    t = TAIL
    rect(t['x0'], -t['half'], t['x1'], t['half'])
    b = BRIDGE
    rect(b['x'] - b['w'] / 2, b['y0'], b['x'] + b['w'] / 2, b['y1'])
    for y in grid_between(b['y0'], b['y1'], 1.3):
        L.append((b['x'] - b['w'] / 2, y, b['x'] + b['w'] / 2, y))
    return L


def point_in_poly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def dist_to_poly(x, y, poly):
    best = 1e9
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy + 1e-12)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def offset_poly(poly, d):
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    sgn = 1 if area > 0 else -1
    out = []
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i - 1], poly[(i + 1) % n]
        tx, ty = bx - ax, by - ay
        L_ = math.hypot(tx, ty) + 1e-12
        out.append((poly[i][0] - sgn * ty / L_ * d, poly[i][1] + sgn * tx / L_ * d))
    return out


def eave_lift(frac, lift):
    return lift * frac ** 2.2


def roof_profile(t):
    return t ** 1.55
