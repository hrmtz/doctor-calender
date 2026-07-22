#!/usr/bin/env python3
"""Recon: dump doctor roster (group|name|clinics-worked) for current month.

Reads GOOGLE_SERVICE_ACCOUNT_KEY env. Run on zetithnas where the key lives.
"""
import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY = os.environ["GOOGLE_SERVICE_ACCOUNT_KEY"]
# Derive SHEET_ID from the known-correct sibling script to avoid retyping
# the id (CLI credential-scrubber mangles long ids passed as args).
import re as _re

_sib = os.path.join(os.path.dirname(__file__), "list_shifts.py")
with open(_sib, encoding="utf-8") as _f:
    SHEET_ID = _re.search(r'SHEET_ID\s*=\s*"([^"]+)"', _f.read()).group(1)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
CLINIC = {"銀座", "大阪", "福岡", "池袋", "新宿", "静脈", "歯科"}

want = sys.argv[1] if len(sys.argv) > 1 else "2026.7"  # "YYYY.M"

creds = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES)
svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

# Resolve exact worksheet title (titles may carry trailing spaces / suffixes).
titles = [
    s["properties"]["title"]
    for s in svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()["sheets"]
]
target = f"{want}月"
tab = next((t for t in titles if t == target), None) or next(
    (t for t in titles if t.startswith(target)), None
)
if not tab:
    print(f"NO SHEET for {target}; titles sample={titles[:8]}")
    sys.exit(1)

rows = (
    svc.spreadsheets()
    .values()
    .get(spreadsheetId=SHEET_ID, range=f"'{tab}'")
    .execute()
    .get("values", [])
)
print(f"# tab={tab!r} rows={len(rows)}")

grp = ""
for r in rows:
    if len(r) > 0 and r[0].strip():
        grp = r[0].strip()
    if len(r) < 2 or "Dr" not in r[1] or "院Dr人数" in r[1]:
        continue
    name = r[1].strip().splitlines()[0]
    cl = sorted({c.strip() for c in r[2:] if c.strip() in CLINIC})
    print(f"{grp}|{name}|{','.join(cl)}")
