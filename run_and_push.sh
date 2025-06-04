#!/bin/bash
cd /home/yesaouo/HF-TrendRadar || exit 1
/usr/bin/python3 main.py
if [ $? -ne 0 ]; then
  echo "main.py 執行失敗" >&2
  exit 1
fi
git add data/output.json
COMMIT_MSG="自動更新 output.json：$(date +'%Y-%m-%d %H:%M:%S')"
git commit -m "$COMMIT_MSG"
git push origin main