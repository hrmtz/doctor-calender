"""
fetch_sheets.py — Google Sheets API疎通確認スクリプト
スプレッドシートのシート名・ヘッダー・サンプルデータを取得してファイルに出力する
"""

import json
import os
import sys

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1vuP1qxZX9sXifzbP0Zk40zfFf7eYbFqk727V4wWU3lU"
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "secrets", "snappy-flash-488807-h4-88e00a722344.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "spreadsheet_structure.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

SAMPLE_ROWS = 3


def fetch_spreadsheet_structure():
    creds_path = os.path.abspath(CREDENTIALS_PATH)
    if not os.path.exists(creds_path):
        print(f"ERROR: 認証JSONが見つかりません: {creds_path}", file=sys.stderr)
        sys.exit(1)

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)

    print(f"スプレッドシートID: {SPREADSHEET_ID} に接続中...")
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    print(f"タイトル: {spreadsheet.title}")

    result = {
        "spreadsheet_id": SPREADSHEET_ID,
        "title": spreadsheet.title,
        "sheets": [],
    }

    worksheets = spreadsheet.worksheets()
    print(f"シート数: {len(worksheets)}")

    for ws in worksheets:
        print(f"\n--- シート: {ws.title} (rows={ws.row_count}, cols={ws.col_count}) ---")
        all_values = ws.get_all_values()

        headers = all_values[0] if all_values else []
        sample_data = all_values[1 : 1 + SAMPLE_ROWS] if len(all_values) > 1 else []

        print(f"ヘッダー: {headers}")
        for i, row in enumerate(sample_data, 1):
            print(f"  行{i}: {row}")

        sheet_info = {
            "title": ws.title,
            "row_count": ws.row_count,
            "col_count": ws.col_count,
            "headers": headers,
            "sample_rows": sample_data,
        }
        result["sheets"].append(sheet_info)

    output_path = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n構造データを保存: {output_path}")

    return result


if __name__ == "__main__":
    fetch_spreadsheet_structure()
