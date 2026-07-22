#!/usr/bin/env python3
"""Read one month's sheet ONCE and emit both axes for IG cards:
  {"clinics": {code: {day: [family,...] sheet-order}},
   "doctors": {family: {day: clinic_label}}}
Usage: dump_month_all.py <YYYY.M>   e.g. 2026.9
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
CLINIC_CODES = ["銀座", "新宿", "池袋", "大阪", "福岡", "静脈", "歯科"]

want = sys.argv[1]
creds = service_account.Credentials.from_service_account_file(
    KEY, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
meta = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()["sheets"]
titles = [s["properties"]["title"] for s in meta]
target = f"{want}月"
tab = next((t for t in titles if t == target), None) or next((t for t in titles if t.startswith(target)), None)
rows = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=f"'{tab}'").execute().get("values", [])

day_row = next((r for r in rows if len(r) > 2 and r[2].strip() == "1"), None)
day_cols = {i: int(v.strip()) for i, v in enumerate(day_row) if i >= 2 and v.strip().isdigit()}

clinics = {c: {} for c in CLINIC_CODES}
doctors = {}
for r in rows:
    if len(r) < 2:
        continue
    name = r[1].strip()
    if "Dr" not in name or "院Dr人数" in name:
        continue
    fam = name.split("Dr")[0].strip().splitlines()[0].strip()
    for ci, day in day_cols.items():
        if ci >= len(r):
            continue
        code = r[ci].strip()
        if code not in CLINIC_CODES:
            continue
        clinics[code].setdefault(str(day), []).append(fam)
        label = SL.CLINIC_LABEL[code]
        doctors.setdefault(fam, {}).setdefault(str(day), label)  # first clinic wins

print(json.dumps({"tab": tab.strip(), "clinics": clinics, "doctors": doctors}, ensure_ascii=False))
