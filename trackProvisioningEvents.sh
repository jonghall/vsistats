#!/bin/bash
(
flock -x -w 10 200 || exit 1
cd /directory
source /root/vsistats/venv/bin/activate
python trackProvisioningEvents.py

) 200>/var/lock/.trackProvisioningEvents.exclusivelock
