#!/bin/bash
(
flock -x -w 10 200 || exit 1
cd /root/AFI
source /root/.virtualenvs/AFI/bin/activate
python trackProvisioningEvents.py

) 200>/var/lock/.trackProvisioningEvents.exclusivelock
