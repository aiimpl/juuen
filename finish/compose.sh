#!/bin/bash
# 本編のコマ（25〜504 コマ＝20 秒）＋タイトル＋音 → build/byodoin.mp4
set -eu
cd "$(dirname "$0")/.."
OUT=build/byodoin.mp4
nice -n 10 ffmpeg -v error -y \
  -framerate 24 -start_number 25 -i build/frames/f_%04d.png \
  -loop 1 -framerate 24 -i build/title.png \
  -i build/audio/byodoin_mix.wav \
  -filter_complex "[1:v]format=rgba,fade=in:st=17.3:d=1.2:alpha=1[t];[0:v][t]overlay=shortest=1,fade=out:st=19.2:d=0.8,format=yuv420p[v]" \
  -map "[v]" -map 2:a -c:v libx264 -crf 18 -preset slow -profile:v high -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of compact "$OUT"
