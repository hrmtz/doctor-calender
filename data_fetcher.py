"""
data_fetcher.py — Google Sheets からDrシフトデータを取得するモジュール
"""

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1vuP1qxZX9sXifzbP0Zk40zfFf7eYbFqk727V4wWU3lU"
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(__file__), "secrets", "snappy-flash-488807-h4-88e00a722344.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# シフト値 → クリニック名マッピング
CLINIC_MAP = {
    "銀座": "銀座院",
    "大阪": "大阪院",
    "福岡": "福岡院",
    "池袋": "池袋院",
    "新宿": "新宿院",
    "静脈": "静脈科",
    "歯科": "歯科",
}

# スキップするシフト値（非勤務）
SKIP_VALUES = {"休", "希", "有", ""}


def _get_client() -> gspread.Client:
    creds_path = os.path.abspath(CREDENTIALS_PATH)
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"認証JSONが見つかりません: {creds_path}")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


def _find_sheet(
    spreadsheet: gspread.Spreadsheet, year: int, month: int
) -> gspread.Worksheet:
    """指定年月のワークシートを検索する。"""
    target_name = f"{year}.{month}月"
    worksheets = spreadsheet.worksheets()

    # 完全一致優先
    for ws in worksheets:
        if ws.title == target_name:
            return ws

    # 前方一致フォールバック（「2026.2月  のコピー」等を除外するため完全一致を優先）
    for ws in worksheets:
        if ws.title.startswith(target_name):
            return ws

    raise ValueError(f"シートが見つかりません: {target_name}")


def fetch_schedule(month: Optional[str] = None) -> List[Dict[str, Any]]:
    """Google SheetsからDrシフトデータを取得する。

    Args:
        month: "YYYY-MM" 形式。省略時は今月。

    Returns:
        List[dict] — 各dictのキー: date, doctor_name, clinic_name, start_time, end_time
    """
    if month is None:
        today = date.today()
        year, mon = today.year, today.month
    else:
        dt = datetime.strptime(month, "%Y-%m")
        year, mon = dt.year, dt.month

    client = _get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    ws = _find_sheet(spreadsheet, year, mon)

    all_values = ws.get_all_values()

    # 最低5行必要（タイトル行・空行・日付行・曜日行・データ行）
    if len(all_values) < 5:
        return []

    # 行2（index 2）: 日付（1〜31）、col C(index 2)から開始
    date_row = all_values[2]

    # col_index -> date オブジェクトのマップを構築
    date_col_map: Dict[int, date] = {}
    for col_idx in range(2, len(date_row)):
        cell_val = date_row[col_idx].strip()
        if cell_val.isdigit():
            day = int(cell_val)
            try:
                date_col_map[col_idx] = date(year, mon, day)
            except ValueError:
                pass  # 月末を超える日付はスキップ

    results: List[Dict[str, Any]] = []

    # 行4（index 4）以降: 医師シフトデータ
    for row in all_values[4:]:
        if not any(cell.strip() for cell in row):
            continue

        doctor_name = row[1].strip() if len(row) > 1 else ""
        if not doctor_name:
            continue

        for col_idx, shift_date in date_col_map.items():
            if col_idx >= len(row):
                continue
            shift_val = row[col_idx].strip()

            if shift_val in SKIP_VALUES:
                continue
            if shift_val not in CLINIC_MAP:
                continue  # 未知のシフト値はスキップ

            results.append(
                {
                    "date": shift_date.strftime("%Y-%m-%d"),
                    "doctor_name": doctor_name,
                    "clinic_name": CLINIC_MAP[shift_val],
                    "start_time": "",
                    "end_time": "",
                }
            )

    # 日付→医師名順でソート
    results.sort(key=lambda e: (e["date"], e["doctor_name"]))
    return results
