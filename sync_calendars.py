#!/usr/bin/env python3
"""sync_calendars.py — create/populate the clinic & doctor shift calendars.

Idempotent. Safe to run daily (user: "シフト変更が頻繁なので毎日更新").

  --dry-run     print planned CREATE/ADD/UPD/DEL, write nothing
  --set-public  additionally grant public reader ACL (PII gate — only after ack)
  --today ISO   simulate a date (default: real today)

Calendars are owned by the service account (seo-research@seo-489203). The
slug→calendarId map is persisted in calendar_map.json so ids are stable across
runs; daily runs only touch events, never recreate calendars.

Publication horizon is enforced entirely inside shift_lib.build_views — this
script only ever sees in-window shifts, and it deletes any tagged event that
falls outside [window_bounds] so unpublished months cannot linger.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time

from googleapiclient.errors import HttpError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shift_lib as SL  # noqa: E402
from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAP_PATH = os.path.join(HERE, "calendar_map.json")
CAL_SCOPES = ["https://www.googleapis.com/auth/calendar"]
SHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
TZ = "Asia/Tokyo"

# The 25 profile-page doctor slugs = the distinct values of the name→slug map.
DOCTOR_SLUGS = sorted(set(SL.DOCTOR_NAME_TO_SLUG.values()))
CLINIC_SLUGS = ["ginza", "shinjuku", "ikebukuro", "osaka", "fukuoka"]

# slug → family token (for the calendar's own title), first token that maps to it.
_SLUG_TOKEN: dict = {}
for _tok, _slug in SL.DOCTOR_NAME_TO_SLUG.items():
    _SLUG_TOKEN.setdefault(_slug, _tok)


def _key_file() -> str:
    return os.environ.get(
        "GOOGLE_SERVICE_ACCOUNT_KEY",
        os.path.join(HERE, "secrets", "service_account.json"),
    )


def _sheet_id() -> str:
    with open(os.path.join(HERE, "scripts", "list_shifts.py"), encoding="utf-8") as f:
        return re.search(r'SHEET_ID\s*=\s*"([^"]+)"', f.read()).group(1)


def load_map() -> dict:
    if os.path.exists(MAP_PATH):
        with open(MAP_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"clinic": {}, "doctor": {}}


def save_map(m: dict) -> None:
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


# --------------------------------------------------------------------------

def fetch_shifts(sheet_svc, sheet_id, today):
    meta = sheet_svc.spreadsheets().get(spreadsheetId=sheet_id).execute()["sheets"]
    shifts = []
    for y, m in SL.target_months(today):
        title = SL.resolve_sheet_title(meta, y, m)
        if not title:
            continue
        rows = (
            sheet_svc.spreadsheets().values()
            .get(spreadsheetId=sheet_id, range=f"'{title}'").execute()
            .get("values", [])
        )
        shifts += SL.parse_month_rows(rows, y, m)
    return shifts


def ensure_calendar(cal_svc, cal_map, axis, slug, title, dry_run):
    cid = cal_map[axis].get(slug)
    if cid:
        return cid, False
    if dry_run:
        return None, True
    # Calendar CREATION hits a Google burst/usage quota on bulk runs. Retry with
    # exponential backoff (events/reads are unaffected; only insert is limited).
    delay = 30
    for attempt in range(6):
        try:
            created = cal_svc.calendars().insert(
                body={"summary": title, "timeZone": TZ}
            ).execute()
            break
        except HttpError as e:
            reason = str(getattr(e, "reason", "")) + str(e)
            if e.resp.status in (403, 429) and "quota" in reason.lower() and attempt < 5:
                print(f"  [quota] {axis}:{slug} retry in {delay}s (attempt {attempt+1})")
                time.sleep(delay)
                delay = min(delay * 2, 600)
                continue
            raise
    cal_map[axis][slug] = created["id"]
    save_map(cal_map)
    return created["id"], True


def set_public(cal_svc, cid):
    """Grant public reader ACL. Idempotent: skip if already public so daily
    runs can safely re-assert (and auto-publish any newly-created calendar)."""
    acl = cal_svc.acl().list(calendarId=cid).execute().get("items", [])
    for r in acl:
        if r.get("scope", {}).get("type") == "default" and r.get("role") in ("reader", "writer", "owner"):
            return False
    cal_svc.acl().insert(
        calendarId=cid, body={"role": "reader", "scope": {"type": "default"}}
    ).execute()
    return True


def list_tagged(cal_svc, cid, lo, hi):
    """All sync-tagged events in the window, as a flat list."""
    out, tok = [], None
    while True:
        resp = cal_svc.events().list(
            calendarId=cid,
            timeMin=dt.datetime.combine(lo, dt.time()).isoformat() + "Z",
            timeMax=dt.datetime.combine(hi + dt.timedelta(days=1), dt.time()).isoformat() + "Z",
            privateExtendedProperty=f"source={SL.SOURCE_TAG}",
            singleEvents=True, maxResults=250, pageToken=tok,
        ).execute()
        out.extend(resp.get("items", []))
        tok = resp.get("nextPageToken")
        if not tok:
            break
    return out


def _slot_of(ev):
    """Stable per-event key. Legacy events (no slot) get a unique legacy key so
    they never match a desired slot → cleanly removed on migration."""
    s = ev.get("extendedProperties", {}).get("private", {}).get("slot")
    return s if s else "legacy:" + ev["id"]


def sync_calendar(cal_svc, cid, desired, lo, hi, dry_run, label):
    """desired: {slot: (date_iso, summary)}. One event per slot — the clinic
    axis uses one slot per (day, doctor) so each doctor is a separate entry
    (readable in the iframe instead of a truncated joined line)."""
    existing_list = [] if (dry_run and cid is None) else list_tagged(cal_svc, cid, lo, hi)
    existing = {_slot_of(e): e for e in existing_list}
    add = upd = dele = 0
    for slot, (ds, summary) in sorted(desired.items()):
        ev = existing.get(slot)
        if ev is None:
            add += 1
            if not dry_run:
                cal_svc.events().insert(calendarId=cid, body={
                    "summary": summary,
                    "start": {"date": ds},
                    "end": {"date": (dt.date.fromisoformat(ds) + dt.timedelta(days=1)).isoformat()},
                    "extendedProperties": {"private": {"source": SL.SOURCE_TAG, "slot": slot}},
                }).execute()
        elif ev.get("summary") != summary:
            upd += 1
            if not dry_run:
                cal_svc.events().patch(calendarId=cid, eventId=ev["id"],
                                       body={"summary": summary}).execute()
    for slot, ev in existing.items():
        if slot not in desired:
            dele += 1
            if not dry_run:
                cal_svc.events().delete(calendarId=cid, eventId=ev["id"]).execute()
    print(f"  {label:26s} +{add} ~{upd} -{dele}  (want={len(desired)})")
    return add, upd, dele


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--set-public", action="store_true")
    ap.add_argument("--today")
    ap.add_argument("--only", help="comma list of axis:slug to restrict to, e.g. clinic:ginza,doctor:tetsu")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    key = _key_file()
    sheet_creds = service_account.Credentials.from_service_account_file(key, scopes=SHEET_SCOPES)
    cal_creds = service_account.Credentials.from_service_account_file(key, scopes=CAL_SCOPES)
    sheet_svc = build("sheets", "v4", credentials=sheet_creds, cache_discovery=False)
    cal_svc = build("calendar", "v3", credentials=cal_creds, cache_discovery=False)

    lo, hi = SL.window_bounds(today)
    print(f"today={today} horizon={hi} window=[{lo}..{hi}] dry_run={args.dry_run} set_public={args.set_public}")

    shifts = fetch_shifts(sheet_svc, _sheet_id(), today)
    clinic_view, doctor_view, unmapped = SL.build_views(shifts, today)
    if unmapped:
        print(f"NOTE unmapped sheet doctors (no page, clinic-cal only): {sorted(unmapped)}")

    cal_map = load_map()

    print("\n=== CLINIC ===")
    for slug in CLINIC_SLUGS:
        if only and f"clinic:{slug}" not in only:
            continue
        title = f"出勤医 | {SL.CLINIC_SLUG_NAME[slug]}"
        cid, created = ensure_calendar(cal_svc, cal_map, "clinic", slug, title, args.dry_run)
        if created:
            print(f"  [{'DRY-' if args.dry_run else ''}CREATE] clinic:{slug}")
        # One event per (day, doctor) — separate readable entries, not a joined
        # line that the iframe truncates. Slot keyed by name (order-independent).
        desired = {}
        for d, names in clinic_view.get(slug, {}).items():
            ds = d.isoformat()
            for name in names:
                desired[f"{ds}#{name}"] = (ds, name)
        sync_calendar(cal_svc, cid, desired, lo, hi, args.dry_run, f"clinic:{slug}")
        if args.set_public and cid and not args.dry_run:
            set_public(cal_svc, cid)

    print("\n=== DOCTOR ===")
    for slug in DOCTOR_SLUGS:
        if only and f"doctor:{slug}" not in only:
            continue
        tok = _SLUG_TOKEN.get(slug, slug)
        title = f"出勤 | {tok}Dr"
        cid, created = ensure_calendar(cal_svc, cal_map, "doctor", slug, title, args.dry_run)
        if created:
            print(f"  [{'DRY-' if args.dry_run else ''}CREATE] doctor:{slug}")
        desired = {d.isoformat(): (d.isoformat(), "・".join(labels))
                   for d, labels in doctor_view.get(slug, {}).items()}
        sync_calendar(cal_svc, cid, desired, lo, hi, args.dry_run, f"doctor:{slug}")
        if args.set_public and cid and not args.dry_run:
            set_public(cal_svc, cid)

    if not args.dry_run:
        save_map(cal_map)
    print("\nDONE")


if __name__ == "__main__":
    main()
