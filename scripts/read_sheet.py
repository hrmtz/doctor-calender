#!/usr/bin/env python3
"""Read the doctor schedule spreadsheet and print raw data."""
import os, json, sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = "1vuP1qxZX9sXifzbP0Zk40zfFf7eYbFqk727V4wWU3lU"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

service = build("sheets", "v4", credentials=creds)
spreadsheet = service.spreadsheets().get(
    spreadsheetId=SHEET_ID,
    fields="sheets.properties"
).execute()

for s in spreadsheet["sheets"]:
    p = s["properties"]
    print(f"sheetId={p['sheetId']}  title={p['title']}")
