#!/bin/bash
# 本番：本物の鳳凰堂のショット（216 コマ）→ 10円玉（168 コマ）。描き終えたコマは飛ばして続きから描く。
set -eu
cd "$(dirname "$0")/.."
mkdir -p build/bld_frames build/coin_frames
LOG=build/render_log.txt
echo "start $(date)" >> "$LOG"
for S in $(seq 1 24 216); do
  E=$((S + 23))
  nice -n 15 blender -b build/byodoin.blend -P tools/building_shot.py -- "$S" "$E" > build/bld_frames/chunk_$S.log 2>&1
  echo "$(date +%H:%M:%S) building $S-$E" >> "$LOG"
done
nice -n 15 blender -b build/coin.blend -P coin/render_coin.py > build/coin_frames/render.log 2>&1
echo "$(date +%H:%M:%S) coin done" >> "$LOG"
echo "done $(date)" >> "$LOG"
