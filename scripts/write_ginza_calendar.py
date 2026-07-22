#!/usr/bin/env python3
"""Sync Ginza-clinic daily doctor roster to Google Calendar.

Each day gets one all-day event summarising who is at Ginza, e.g.
  "鉄, 守屋, 中村, 小川"
Run with --dry-run to print events without inserting them.
"""
import argparse
import calendar
import datetime
import os
import re
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

SPREADSHEET_ID = "1vuP1qxZX9sXifzbP0Zk40zfFf7eYbFqk727V4wWU3lU"
SOURCE_TAG = "ginza-shift-sync"

KEY_FILE = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_KEY",
    os.path.join(os.path.dirname(__file__), "../secrets/service_account.json"),
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/calendar",
]

_SHEET_PAT = re.compile(r"^(\d{4})\.(\d{1,2})月\s*$")
_DR_STRIP = re.compile(r"Dr.*$", re.DOTALL)


def short_name(raw: str) -> str:
    """'守屋Dr\\n ~16:30' → '守屋'"""
    return _DR_STRIP.sub("", raw).strip()


def discover_target_months(all_sheets):
    today = datetime.date.today()
    result = []
    for s in all_sheets:
        props = s["properties"]
        m = _SHEET_PAT.match(props["title"])
        if not m:
            continue
        year, month = int(m.group(1)), int(m.group(2))
        if (year, month) >= (today.year, today.month):
            result.append((props["sheetId"], props["title"], year, month))
    return sorted(result, key=lambda x: (x[2], x[3]))


def fetch_ginza_roster(sheets_svc, target_months):
    """Returns {date_str: "鉄, 守屋, ..."} for all days with ≥1 Ginza doctor."""
    roster = {}
    for _gid, sheet_name, year, month in target_months:
        rows = sheets_svc.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{sheet_name}'",
        ).execute().get("values", [])

        # find day-number header row (first row whose col2 is "1")
        day_row = next(
            (r for r in rows if len(r) > 2 and r[2].strip() == "1"), None
        )
        if not day_row:
            print(f"  {year}/{month:02d}: 日付行見つからずスキップ")
            continue

        # col index 2 = day 1, col index N = day (N-1)
        day_cols = {}  # col_index -> day_number
        for col_idx, cell in enumerate(day_row[2:], start=2):
            try:
                day = int(cell.strip())
                day_cols[col_idx] = day
            except (ValueError, AttributeError):
                pass

        # collect doctor rows (col1 ends with 'Dr' pattern, skip summary rows)
        doctor_rows = [
            r for r in rows
            if len(r) > 1 and "Dr" in r[1] and r[1].strip() not in ("銀座院Dr人数", "大阪院Dr人数", "福岡院Dr人数", "池袋院Dr人数", "新宿院Dr人数")
        ]

        for col_idx, day_num in day_cols.items():
            try:
                date = datetime.date(year, month, day_num)
            except ValueError:
                continue
            date_str = date.isoformat()

            doctors_today = []
            for row in doctor_rows:
                if col_idx < len(row) and row[col_idx].strip() == "銀座":
                    doctors_today.append(short_name(row[1]))

            if doctors_today:
                roster[date_str] = ", ".join(doctors_today)

    return roster


def list_tagged_events(cal_svc, cal_id, year, month):
    last_day = calendar.monthrange(year, month)[1]
    events, page_token = [], None
    while True:
        resp = cal_svc.events().list(
            calendarId=cal_id,
            timeMin=f"{year}-{month:02d}-01T00:00:00Z",
            timeMax=f"{year}-{month:02d}-{last_day}T23:59:59Z",
            privateExtendedProperty=f"source={SOURCE_TAG}",
            pageToken=page_token,
            maxResults=250,
            singleEvents=True,
        ).execute()
        events.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return events


def sync_month(cal_svc, cal_id, year, month, roster, dry_run=False):
    existing = [] if dry_run else list_tagged_events(cal_svc, cal_id, year, month)
    existing_by_date = {e["start"]["date"]: e for e in existing}

    want = {
        date_str: summary
        for date_str, summary in roster.items()
        if date_str.startswith(f"{year}-{month:02d}")
    }

    added = deleted = updated = 0

    for date_str, event in existing_by_date.items():
        if date_str not in want:
            if dry_run:
                print(f"    [DRY] DEL {date_str}  {event.get('summary','')}")
            else:
                cal_svc.events().delete(calendarId=cal_id, eventId=event["id"]).execute()
            deleted += 1

    for date_str, summary in sorted(want.items()):
        if date_str in existing_by_date:
            if existing_by_date[date_str].get("summary") != summary:
                if dry_run:
                    print(f"    [DRY] UPD {date_str}  {summary}")
                else:
                    cal_svc.events().patch(
                        calendarId=cal_id,
                        eventId=existing_by_date[date_str]["id"],
                        body={"summary": summary},
                    ).execute()
                updated += 1
        else:
            if dry_run:
                print(f"    [DRY] ADD {date_str}  {summary}")
            else:
                cal_svc.events().insert(
                    calendarId=cal_id,
                    body={
                        "summary": summary,
                        "start": {"date": date_str},
                        "end":   {"date": date_str},
                        "extendedProperties": {"private": {"source": SOURCE_TAG}},
                    },
                ).execute()
            added += 1

    tag = "[DRY] " if dry_run else ""
    print(f"  {year}/{month:02d}: {tag}+{added} ~{updated} -{deleted}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cal-id", required=True, help="Target Google Calendar ID")
    args = parser.parse_args()

    creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
    sheets_svc = build("sheets", "v4", credentials=creds)
    cal_svc = build("calendar", "v3", credentials=creds)

    all_sheets = sheets_svc.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()["sheets"]
    months = discover_target_months(all_sheets)

    print(f"対象月: {[(y,m) for _,_,y,m in months]}")
    roster = fetch_ginza_roster(sheets_svc, months)

    for _gid, _name, year, month in months:
        sync_month(cal_svc, args.cal_id, year, month, roster, dry_run=args.dry_run)

    print("完了")


if __name__ == "__main__":
    main()
