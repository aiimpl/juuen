#!/bin/bash
# 本番：25〜504 コマを 30 コマずつ。低い優先度・Blender は 1 本ずつ・合間に 45 秒冷ます。
# 途中で止めても、描き終えたコマは飛ばして続きから描く（use_overwrite=False）。
set -eu
cd "$(dirname "$0")/.."
mkdir -p build/frames
LOG=build/frames/log.txt
echo "start $(date)" >> "$LOG"
for S in $(seq 25 30 504); do
  E=$((S + 29)); [ "$E" -gt 504 ] && E=504
  T0=$(date +%s)
  nice -n 15 blender -b build/byodoin.blend -s "$S" -e "$E" -a > "build/frames/chunk_$S.log" 2>&1
  N=$(ls build/frames/f_*.png 2>/dev/null | wc -l | tr -d ' ')
  echo "$(date +%H:%M:%S) chunk $S-$E $(( $(date +%s) - T0 ))s total_frames=$N" >> "$LOG"
  [ "$E" -lt 504 ] && sleep 45
done
echo "done $(date)" >> "$LOG"
