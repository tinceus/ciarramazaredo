#!/bin/bash
# Scheduler entry point (cron or launchd): one bounded batch, never overlapping (harvest.py holds a lock).
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "$0")" || exit 1
echo "=== $(date '+%F %T')" >> fetch_run.out
python3 harvest.py fetch --minutes 100 >> fetch_run.out 2>&1
