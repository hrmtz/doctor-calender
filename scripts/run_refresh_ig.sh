#!/bin/bash
# 日次cron: シフトSheet更新を検知したら Instagram カードを再生成→共有ドライブへ。
# chichibu(JST)で実行。chrome + Google Fonts(要ネット) + SA鍵を使用。
export PATH=/home/hrmtz/.local/bin:/usr/local/bin:/usr/bin:/bin
cd /home/hrmtz/projects/doctor-calender || exit 1
mkdir -p /home/hrmtz/.local/log
echo "=== $(date '+%Y-%m-%d %H:%M:%S') refresh_ig start ===" >> /home/hrmtz/.local/log/ig_refresh.log
/usr/bin/python3 refresh_ig.py >> /home/hrmtz/.local/log/ig_refresh.log 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') refresh_ig exit=$? ===" >> /home/hrmtz/.local/log/ig_refresh.log
