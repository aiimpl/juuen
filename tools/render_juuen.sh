#!/bin/bash
# 本番：本物の鳳凰堂 → 銅の浮き彫りの版 → 10円玉の寄り → 締めの 10円玉。描き終えたコマは飛ばして続きから描く。
set -eu
cd "$(dirname "$0")/.."
LOG=build/render_log.txt
echo "start $(date)" >> "$LOG"
nice -n 10 blender -b build/byodoin.blend -P tools/building_shot.py -- real > build/real_render.log 2>&1
echo "$(date +%H:%M:%S) real done" >> "$LOG"
nice -n 10 blender -b build/byodoin.blend -P tools/building_shot.py -- relief > build/relief_render.log 2>&1
echo "$(date +%H:%M:%S) relief done" >> "$LOG"
nice -n 10 blender -b build/coin.blend -P coin/render_coin.py > build/coin_render.log 2>&1
echo "$(date +%H:%M:%S) coin done" >> "$LOG"
nice -n 10 blender -b build/coin.blend -P coin/render_coin.py -- end > build/end_render.log 2>&1
echo "$(date +%H:%M:%S) end done" >> "$LOG"
echo "done $(date)" >> "$LOG"
