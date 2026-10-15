#!/usr/bin/env bash
# Frames + the music cut -> social MP4 (H.264 yuv420p, AAC, faststart).
#   bash encode.sh reddit-v2
# Audio window comes from the shot JSON so picture and score can't drift apart.
set -e
NAME="$1"; HERE="$(cd "$(dirname "$0")" && pwd)"; HERE_W="$(cygpath -w "$HERE")"
PY="/d/Projects/Sisi baby blue/.venv/Scripts/python.exe"
JSON_W="$(cygpath -w "$HERE/$NAME.json")"
read T0 DUR FPS < <("$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['audio']['t0'],d['dur'],d['fps'])" "$JSON_W")
FR="$HERE/renders/$NAME"; OUT="$HERE/out"; mkdir -p "$OUT"
AUD="/d/CLAUDE/TreeSeasons/music/married-life-toms-mucenieks-piano.mp3"
ffmpeg -v error -y -framerate "$FPS" -i "$FR/frame_%05d.png" \
  -ss "$T0" -t "$DUR" -i "$AUD" \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p \
  -profile:v high -level 4.1 -r "$FPS" \
  -af "afade=t=in:d=0.015,afade=t=out:st=$("$PY" -c "print(round($DUR-0.03,3))"):d=0.03" \
  -c:a aac -b:a 192k -movflags +faststart -shortest "$OUT/$NAME.mp4"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration,size \
  -of default=noprint_wrappers=1 "$OUT/$NAME.mp4"
