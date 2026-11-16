#!/bin/bash
# final render: 4 single-thread workers that claim frames; safe to re-run (skips finished frames)
cd "$(dirname "$0")"
find frames2 -size 0 -delete 2>/dev/null
for i in 1 2 3 4; do
  SAMPLES=5 THREADS=1 OUT=frames2 nohup setsid python3 film2.py render 1 2533 > render$i.log 2>&1 &
  sleep 3
done
