#!/bin/bash
# Daily shift-calendar sync (clinic + doctor). Separate from run.sh (中村Dr flow).
# Installed on zetithnas cron. Re-asserts public ACL (idempotent) so any newly
# created calendar auto-publishes. Horizon rolls automatically on the 1st.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
export GOOGLE_SERVICE_ACCOUNT_KEY=/volume1/secrets/service_account.json
mkdir -p output
/volume1/@appstore/Python3.9/usr/bin/python3 sync_calendars.py --set-public \
  >> output/shift_sync.log 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') shift-calendar sync exit=$?" >> output/shift_sync.log
