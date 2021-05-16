#!/bin/bash
(
flock -x -w 10 200 || exit 1
cd /directory
source /root/vsistats/venv/bin/activate
python generateDailyReport.py

) 200>/var/lock/.generateDailyStats.exclusivelock
