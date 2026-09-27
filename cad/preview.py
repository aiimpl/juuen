"""build/dxf の DXF を PNG に描いて目視確認する（matplotlib が必要）"""
import glob
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build', 'dxf')
for f in sorted(glob.glob(os.path.join(D, '*.dxf'))):
    doc = ezdxf.readfile(f)
    audit = doc.audit()
    fig = plt.figure(figsize=(14.85, 10.5), dpi=110)
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK)
    Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace())
    ax.set_xlim(0, 594); ax.set_ylim(0, 420); ax.set_aspect('equal')
    out = f[:-4] + '.png'
    fig.savefig(out)
    plt.close(fig)
    print(os.path.basename(f), 'errors', len(audit.errors), '->', os.path.basename(out))
