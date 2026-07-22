#!/usr/bin/env python3
"""List all unique shift location values from current+future months."""
import os, re, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY = os.environ["GOOGLE_SERVICE_ACCOUNT_KEY"]
SHEET_ID = "1vuP1qxZX9sXifzbP0Zk40zfFf7eYbFqk727V4wWU3lU"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
_SHEET_PAT = re.compile(r"^(\d{4})\.(\d{1,2})月\s*$")
SKIP_CELLS = {"休", "有", "希"}
SKIP_NAME_PAT = re.compile(r"院Dr人数")

creds = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES)
svc = build("sheets", "v4", credentials=creds)

sheets = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()["sheets"]
today = datetime.date.today()

shift_values = set()
for s in sheets:
    p = s["properties"]
    m = _SHEET_PAT.match(p["title"])
    if not m:
        continue
    y, mo = int(m.group(1)), int(m.group(2))
    if (y, mo) < (today.year, today.month):
        continue

    title = p["title"]
    rows = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"'{title}'"
    ).execute().get("values", [])

    for row in rows:
        if len(row) < 2 or "Dr" not in row[1]:
            continue
        if SKIP_NAME_PAT.search(row[1]):
            continue
        for cell in row[2:]:
            v = cell.strip()
            if v and v not in SKIP_CELLS and not v.isdigit():
                shift_values.add(v)

for v in sorted(shift_values):
    print(v)
