#!/usr/bin/env python3
"""
generate.py — docrot-calendar CLIエントリーポイント

使用例:
    python generate.py --type schedule --date 2026-03-01
    python generate.py --type schedule --month 2026-03
    python generate.py --type calendar --month 2026-03
    python generate.py --type ical --month 2026-03
"""

import argparse
import os
import sys
from datetime import date

# オプションモジュール: 未実装の場合はImportErrorをキャッチしてスキップ
try:
    from image_calendar import generate_calendar_image

    _has_calendar = True
except ImportError:
    _has_calendar = False

try:
    from image_poem import generate_poem_image

    _has_poem = True
except ImportError:
    _has_poem = False

try:
    from ical_generator import generate_ical

    _has_ical = True
except ImportError:
    _has_ical = False

from data_fetcher import fetch_schedule
from image_schedule import generate_schedule_image


def cmd_schedule(args: argparse.Namespace) -> None:
    """--type schedule: 出勤情報ストーリー画像を生成する。"""
    month = args.month or date.today().strftime("%Y-%m")
    target_date = args.date

    print(f"スケジュール取得中: {month} ...")
    entries = fetch_schedule(month=month)

    if not entries:
        print(f"スケジュールデータが見つかりません: {month}", file=sys.stderr)
        return

    if target_date:
        entries = [e for e in entries if e["date"] == target_date]
        if not entries:
            print(f"指定日のデータなし: {target_date}", file=sys.stderr)
            return

    os.makedirs(args.output, exist_ok=True)
    count = 0
    for entry in entries:
        date_slug = entry["date"].replace("-", "")
        doctor_safe = entry["doctor_name"].replace("/", "_").replace(" ", "_")
        filename = f"schedule_{date_slug}_{doctor_safe}.png"
        out_path = os.path.join(args.output, filename)
        generate_schedule_image(entry, out_path)
        print(f"生成: {out_path}")
        count += 1

    print(f"完了: {count}件生成しました")


def cmd_calendar(args: argparse.Namespace) -> None:
    """--type calendar: カレンダー画像を生成する（image_calendar.py実装待ち）。"""
    if not _has_calendar:
        print("image_calendar モジュール未実装 (subtask_312b待ち)", file=sys.stderr)
        sys.exit(1)

    month = args.month or date.today().strftime("%Y-%m")
    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, f"calendar_{month.replace('-', '')}.png")
    generate_calendar_image(month=month, output_path=out_path)
    print(f"生成: {out_path}")


def cmd_poem(args: argparse.Namespace) -> None:
    """--type poem: ポエム画像を生成する。"""
    if not _has_poem:
        print("image_poem モジュール未実装 (subtask_312c待ち)", file=sys.stderr)
        sys.exit(1)

    from image_poem import POEM_DEFAULTS  # type: ignore
    import random

    target_date = args.date or date.today().strftime("%Y-%m-%d")
    poem = random.choice(POEM_DEFAULTS)
    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, f"poem_{target_date.replace('-', '')}.png")
    generate_poem_image(text=poem["text"], output_path=out_path, author=poem.get("author", ""))
    print(f"生成: {out_path}")


def cmd_ical(args: argparse.Namespace) -> None:
    """--type ical: iCalendarファイルを生成する。"""
    if not _has_ical:
        print("ical_generator モジュール未実装 (subtask_312c待ち)", file=sys.stderr)
        sys.exit(1)

    month = args.month or date.today().strftime("%Y-%m")
    print(f"スケジュール取得中: {month} ...")
    schedule_data = fetch_schedule(month=month)
    if not schedule_data:
        print(f"スケジュールデータが見つかりません: {month}", file=sys.stderr)
        return

    # start_time/end_timeが空の場合はデフォルト値を補完（ical_generator要件）
    for entry in schedule_data:
        if not entry.get("start_time"):
            entry["start_time"] = "09:00"
        if not entry.get("end_time"):
            entry["end_time"] = "18:00"

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, f"schedule_{month.replace('-', '')}.ics")
    generate_ical(schedule_data=schedule_data, output_path=out_path)
    print(f"生成: {out_path} ({len(schedule_data)}件)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="docrot-calendar — 医師シフト画像・iCal生成ツール"
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["schedule", "calendar", "poem", "ical"],
        help="生成タイプ: schedule=出勤画像, calendar=カレンダー画像, poem=ポエム画像, ical=iCal",
    )
    parser.add_argument(
        "--date",
        help="対象日付 YYYY-MM-DD（省略時は今日）",
    )
    parser.add_argument(
        "--month",
        help="対象月 YYYY-MM（省略時は今月）",
    )
    parser.add_argument(
        "--output",
        default="output/",
        help="出力ディレクトリ（デフォルト: output/）",
    )

    args = parser.parse_args()

    dispatch = {
        "schedule": cmd_schedule,
        "calendar": cmd_calendar,
        "poem": cmd_poem,
        "ical": cmd_ical,
    }
    dispatch[args.type](args)


if __name__ == "__main__":
    main()
