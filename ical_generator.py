"""
ical_generator.py — スケジュールデータ → iCalendar (.ics) 生成モジュール
Google Calendar互換 VCALENDAR/VEVENT形式
"""

from __future__ import annotations

from datetime import datetime, date, time
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

# タイムゾーン
JST = ZoneInfo("Asia/Tokyo")
PRODID = "-//Doctor Calendar//Doctor Schedule//JA"


def _parse_date(date_str: str) -> date:
    """'YYYY-MM-DD' → date オブジェクト"""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def _parse_time(time_str: str) -> time:
    """'HH:MM' → time オブジェクト"""
    return datetime.strptime(time_str, "%H:%M").time()


def generate_ical(schedule_data: list[dict], output_path: str) -> str:
    """
    スケジュールデータを .ics ファイルに変換して保存する。

    Args:
        schedule_data: スケジュールのリスト。各要素は以下のキーを持つ dict:
            - date (str): "YYYY-MM-DD"
            - doctor_name (str): 医師名
            - clinic_name (str): クリニック名
            - start_time (str): "HH:MM" 形式の開始時刻
            - end_time (str): "HH:MM" 形式の終了時刻
            - description (str, optional): 追加説明
        output_path: 出力先パス（例: "output/schedule_2026-03.ics"）

    Returns:
        output_path（保存されたファイルパス）
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "Drシフト")
    cal.add("x-wr-timezone", "Asia/Tokyo")

    for entry in schedule_data:
        event = Event()

        d = _parse_date(entry["date"])
        t_start = _parse_time(entry.get("start_time", "09:00"))
        t_end = _parse_time(entry.get("end_time", "18:00"))

        dt_start = datetime.combine(d, t_start, tzinfo=JST)
        dt_end = datetime.combine(d, t_end, tzinfo=JST)

        doctor = entry.get("doctor_name", "")
        clinic = entry.get("clinic_name", "")

        # SUMMARY: 医師名 + クリニック名
        summary = f"{doctor}（{clinic}）" if clinic else doctor
        event.add("summary", summary)
        event.add("dtstart", dt_start)
        event.add("dtend", dt_end)

        # DESCRIPTION
        desc_parts = []
        if doctor:
            desc_parts.append(f"担当: {doctor}")
        if clinic:
            desc_parts.append(f"クリニック: {clinic}")
        if extra_desc := entry.get("description", ""):
            desc_parts.append(extra_desc)
        if desc_parts:
            event.add("description", "\n".join(desc_parts))

        # UID（重複防止）
        uid = f"{entry['date']}-{doctor}-{clinic}@doctor-calendar".replace(" ", "_")
        event.add("uid", uid)

        event.add("dtstamp", datetime.now(tz=JST))

        cal.add_component(event)

    ics_bytes = cal.to_ical()
    Path(output_path).write_bytes(ics_bytes)
    return output_path


# ============================================================
# スタンドアロンテスト
# ============================================================
if __name__ == "__main__":
    mock_data = [
        {
            "date": "2026-03-01",
            "doctor_name": "鉄Dr",
            "clinic_name": "銀座院",
            "start_time": "09:00",
            "end_time": "18:00",
        },
        {
            "date": "2026-03-01",
            "doctor_name": "守屋Dr",
            "clinic_name": "銀座院",
            "start_time": "10:00",
            "end_time": "19:00",
        },
        {
            "date": "2026-03-02",
            "doctor_name": "王Dr",
            "clinic_name": "新宿院",
            "start_time": "09:00",
            "end_time": "17:00",
            "description": "午後外来のみ",
        },
    ]
    out = generate_ical(mock_data, "output/test_schedule.ics")
    print(f"生成完了: {out}")

    # 内容確認
    content = Path(out).read_text(encoding="utf-8", errors="replace")
    vevent_count = content.count("BEGIN:VEVENT")
    print(f"VEVENTイベント数: {vevent_count}")
    print("VCALENDAR含む:", "BEGIN:VCALENDAR" in content)
