#!/bin/bash
export PK=/tmp/nb271
cd /home/claude/t
for s in big b2a b3s b3m b2b b3h1 b3h2; do
  echo "=== $s" > /tmp/reg_$s.txt
  timeout 600 python3 $s.py >> /tmp/reg_$s.txt 2>&1
  echo "=== done $s" >> /tmp/reg_$s.txt
done
echo ALLDONE > /tmp/reg_done.txt
