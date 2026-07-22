#!/usr/bin/env python3
"""Dry-run: read the live Sheet, build clinic/doctor views, print summaries.

No calendar writes. Validates horizon + mappings against real data.
Run on zetithnas: GOOGLE_SERVICE_ACCOUNT_KEY set, python3.9.
Optional arg: ISO date to simulate "today" (default: real today).
"""
import os
import re
import sys
import datetime as dt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import shift_lib as SL  # noqa: E402
from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

KEY = os.environ["GOOGLE_SERVICE_ACCOUNT_KEY"]
with open(os.path.join(os.path.dirname(__file__), "list_shifts.py"), encoding="utf-8") as f:
    SHEET_ID = re.search(r'SHEET_ID\s*=\s*"([^"]+)"', f.read()).group(1)

today = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()

creds = service_account.Credentials.from_service_account_file(
    KEY, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)
svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
meta = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()["sheets"]

months = SL.target_months(today)
lo, hi = SL.window_bounds(today)
print(f"TODAY={today}  horizon={SL.published_horizon(today)}  window=[{lo}..{hi}]")
print(f"target_months={months}")

shifts = []
for y, m in months:
    title = SL.resolve_sheet_title(meta, y, m)
    if not title:
        print(f"  {y}.{m}: NO SHEET (skip)")
        continue
    rows = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"'{title}'"
    ).execute().get("values", [])
    parsed = SL.parse_month_rows(rows, y, m)
    shifts += parsed
    print(f"  {y}.{m}: title={title!r} parsed_shift_cells={len(parsed)}")

clinic_view, doctor_view, unmapped = SL.build_views(shifts, today)

print("\n=== CLINIC calendars (院軸) ===")
for slug in ["ginza", "shinjuku", "ikebukuro", "osaka", "fukuoka"]:
    dm = clinic_view.get(slug, {})
    days = sorted(dm)
    sample = f"{days[0]}:{'・'.join(dm[days[0]])}" if days else "-"
    print(f"  {slug:10s} days={len(days):3d}  first[{sample}]")

print("\n=== DOCTOR calendars (医師軸) ===")
for slug in sorted(doctor_view):
    dm = doctor_view[slug]
    days = sorted(dm)
    print(f"  {slug:20s} days={len(days):3d}")

covered = set(doctor_view)
all_page_slugs = set(SL.DOCTOR_NAME_TO_SLUG.values())
print("\nprofile-page doctors with NO shift this window:",
      sorted(all_page_slugs - covered))
print("UNMAPPED sheet doctor tokens (no profile page):", sorted(unmapped))
