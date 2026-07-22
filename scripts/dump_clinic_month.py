#!/usr/bin/env python3
"""Dump one clinic's month as {day: [family-name,...]} in SHEET ROW ORDER
(the order doctors appear top-to-bottom in the sheet), for the IG calendar image.
Usage: dump_clinic_month.py <YYYY.M> <clinic-code>   e.g. 2026.8 銀座
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import shift_lib as SL  # noqa: E402
from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

KEY = os.environ["GOOGLE_SERVICE_ACCOUNT_KEY"]
with open(os.path.join(os.path.dirname(__file__), "list_shifts.py"), encoding="utf-8") as f:
    SHEET_ID = re.search(r'SHEET_ID\s*=\s*"([^"]+)"', f.read()).group(1)

want, code = sys.argv[1], sys.argv[2]  # "2026.8", "銀座"
creds = service_account.Credentials.from_service_account_file(
    KEY, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
meta = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()["sheets"]
titles = [s["properties"]["title"] for s in meta]
target = f"{want}月"
tab = next((t for t in titles if t == target), None) or next((t for t in titles if t.startswith(target)), None)
rows = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=f"'{tab}'").execute().get("values", [])

# day-number header row
day_row = next((r for r in rows if len(r) > 2 and r[2].strip() == "1"), None)
day_cols = {i: int(v.strip()) for i, v in enumerate(day_row) if i >= 2 and v.strip().isdigit()}

out = {}  # day -> [family names, sheet order]
for r in rows:
    if len(r) < 2:
        continue
    name = r[1].strip()
    if "Dr" not in name or "院Dr人数" in name:
        continue
    fam = name.split("Dr")[0].strip().splitlines()[0].strip()
    for ci, day in day_cols.items():
        if ci < len(r) and r[ci].strip() == code:
            out.setdefault(str(day), []).append(fam)

print(json.dumps({"tab": tab.strip(), "days": out}, ensure_ascii=False))
