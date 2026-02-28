# docrot-calendar

医師シフトスプレッドシート（Google Sheets）から Instagram Story画像・iCalendar を生成するツール。

## セットアップ

```bash
cd /Users/hrmtz/project/personal/doctor-calender
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

認証ファイル `secrets/snappy-flash-488807-h4-88e00a722344.json` を配置すること。

## Quick Start

```bash
# 出勤情報ストーリー画像（今月分）
python generate.py --type schedule

# 出勤情報ストーリー画像（指定月）
python generate.py --type schedule --month 2026-03

# 出勤情報ストーリー画像（指定日）
python generate.py --type schedule --date 2026-03-01

# iCalendarファイル（指定月）
python generate.py --type ical --month 2026-03

# ポエム画像（指定日）
python generate.py --type poem --date 2026-03-01

# カレンダー画像（指定月）
python generate.py --type calendar --month 2026-03
```

出力先は `output/` ディレクトリ（`--output` オプションで変更可）。

## オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--type` | 生成タイプ: schedule / calendar / poem / ical | 必須 |
| `--date` | 対象日付 YYYY-MM-DD | 今日 |
| `--month` | 対象月 YYYY-MM | 今月 |
| `--output` | 出力ディレクトリ | output/ |

## モジュール構成

| ファイル | 役割 |
|---------|------|
| `data_fetcher.py` | Google Sheets からシフトデータを取得 |
| `image_schedule.py` | 出勤情報ストーリー画像生成 (1080x1920) |
| `image_poem.py` | ポエム/名言画像生成 (1080x1920) |
| `ical_generator.py` | iCalendar (.ics) ファイル生成 |
| `generate.py` | CLIエントリーポイント |
