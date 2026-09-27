"""使うフォントを探す。macOS の標準フォントを優先し、なければ環境変数で指定したものを使う。

  BYODOIN_FONT_TITLE   題字・タイトル（太い明朝）
  BYODOIN_FONT_MINCHO  ラベル（明朝）
  BYODOIN_FONT_SERIF   欧文（ローマ字の添え書き）
  BYODOIN_FONT_GOTHIC  字幕（太い角ゴシック）
"""
import glob
import os

_CANDIDATES = {
    'title': [
        '/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/ToppanBunkyuMidashiMinchoStdN-ExtraBold.otf',
        '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc',
    ],
    'mincho': ['/System/Library/Fonts/ヒラギノ明朝 ProN.ttc'],
    'gothic': ['/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc', '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc'],
    'serif': ['/System/Library/Fonts/Supplemental/Didot.ttc', '/System/Library/Fonts/Supplemental/Baskerville.ttc'],
}


def find(kind):
    env = os.environ.get('BYODOIN_FONT_' + kind.upper())
    if env and os.path.exists(env):
        return env
    for pat in _CANDIDATES[kind]:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    raise FileNotFoundError(f'{kind} のフォントが見つかりません。BYODOIN_FONT_{kind.upper()} で指定してください')
