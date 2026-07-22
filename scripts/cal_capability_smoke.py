#!/usr/bin/env python3
"""Smoke: verify the service account can create + delete a secondary calendar.

Creates a throwaway calendar, prints its id, then deletes it. No public ACL,
no events. Confirms calendars.insert/delete capability before we design on it.
"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY = os.environ["GOOGLE_SERVICE_ACCOUNT_KEY"]
SCOPES = ["https://www.googleapis.com/auth/calendar"]

creds = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES)
svc = build("calendar", "v3", credentials=creds, cache_discovery=False)

created = svc.calendars().insert(
    body={"summary": "zzz-smoke-DELETE", "timeZone": "Asia/Tokyo"}
).execute()
cid = created["id"]
print("CREATE_OK id_len=%d ends=%s" % (len(cid), cid[-18:]))

# also confirm we can read the SA's own calendarList / owner acl
acl = svc.acl().list(calendarId=cid).execute()
roles = sorted({r.get("role") for r in acl.get("items", [])})
print("ACL_roles=%s" % roles)

svc.calendars().delete(calendarId=cid).execute()
print("DELETE_OK")
