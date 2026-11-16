#!/bin/bash
# internal QA contact sheets of preview frames (not a deliverable)
cd /home/user/Horror/rbx/prev
for s in 0 1 2 3 4 5; do ffmpeg -v error -y -pattern_type glob -i '*.png' -vf "select='gte(n,$((s*36)))*lt(n,$(((s+1)*36)))',scale=180:320,drawtext=text='%{n}':fontcolor=yellow:fontsize=22:x=4:y=4,tile=12x3" -frames:v 1 ../sheets/s$s.png; done
