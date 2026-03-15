"""
image_calendar.py — 月次カレンダー画像生成モジュール (1080x1920, 9:16)
"""

import calendar
import os
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

CANVAS_W = 1080
CANVAS_H = 1920
SAFE_ZONE = 250

BG_COLOR = (250, 250, 252)
HEADER_BG = (30, 100, 200)
HEADER_TEXT_COLOR = (255, 255, 255)
TEXT_COLOR = (30, 30, 40)
CELL_BORDER_COLOR = (200, 205, 215)
CELL_WORK_BG = (232, 245, 233)       # 診療日 (薄緑 #E8F5E9)
CELL_HOLIDAY_BG = (255, 235, 235)    # 休診日 (薄赤 #FFEBEB)
CELL_SUN_BG = (255, 242, 242)        # 日曜背景
CELL_SAT_BG = (242, 246, 255)        # 土曜背景
CELL_OUTOFMONTH_BG = (235, 235, 238) # 当月外
WEEKDAY_HEADER_BG = (235, 238, 248)

DAY_SUN_COLOR = (200, 60, 60)
DAY_SAT_COLOR = (60, 100, 200)
DAY_WEEKDAY_COLOR = (40, 40, 50)
DOCTOR_TEXT_COLOR = (40, 90, 50)

# 7列ヘッダー: 日月火水木金土 (日曜始まり)
WEEKDAYS_JP = ["日", "月", "火", "水", "木", "金", "土"]
WEEKDAY_COLORS = [
    (220, 60, 60),   # 日 - 赤
    (55, 55, 65),    # 月
    (55, 55, 65),    # 火
    (55, 55, 65),    # 水
    (55, 55, 65),    # 木
    (55, 55, 65),    # 金
    (60, 100, 200),  # 土 - 青
]

FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    "/System/Library/Fonts/Supplemental/HiraginoSans.ttc",
]


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    noto_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Regular.ttf")
    if os.path.exists(noto_path):
        return ImageFont.truetype(noto_path, size)
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple:
    """(width, height) を返す。"""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def generate_calendar_image(
    schedule_data: Optional[List[Dict]] = None,
    month: str = "",
    output_path: str = "",
) -> str:
    """月次カレンダー画像を生成する。

    Args:
        schedule_data: スケジュールデータのリスト。Noneの場合はdata_fetcher.fetch_schedule()で自動取得。
            各dictのキー: date (YYYY-MM-DD), doctor_name, clinic_name
        month: "YYYY-MM" 形式の対象月。空の場合は今月。
        output_path: 保存先パス (.png)

    Returns:
        output_path
    """
    if not month:
        month = date.today().strftime("%Y-%m")

    if schedule_data is None:
        from data_fetcher import fetch_schedule
        schedule_data = fetch_schedule(month=month)

    dt = datetime.strptime(month, "%Y-%m")
    year, mon = dt.year, dt.month

    # 日付 → 医師名リストのマップ構築
    day_doctors: Dict[str, List[str]] = defaultdict(list)
    for entry in schedule_data:
        d = entry.get("date", "")
        doctor = entry.get("doctor_name", "")
        if d and doctor:
            day_doctors[d].append(doctor)

    # カレンダーグリッド (日曜始まり: firstweekday=6)
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, mon)
    num_weeks = len(weeks)  # 5 or 6

    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    margin_x = 16
    grid_w = CANVAS_W - 2 * margin_x
    cell_w = grid_w // 7

    font_header = _get_font(48)
    font_weekday = _get_font(32)
    font_day = _get_font(36)
    font_doctor = _get_font(20)
    font_doctor_sm = _get_font(17)
    font_doctor_xs = _get_font(14)
    font_more = _get_font(15)

    content_top = SAFE_ZONE
    content_bottom = CANVAS_H - SAFE_ZONE

    # --- ヘッダー (上セーフゾーン内から描画開始) ---
    header_text = f"{year}年{mon}月　診療カレンダー"
    header_h = 84
    header_y = content_top

    draw.rectangle(
        [margin_x, header_y, CANVAS_W - margin_x, header_y + header_h],
        fill=HEADER_BG,
    )
    tw, th = _text_size(draw, header_text, font_header)
    draw.text(
        ((CANVAS_W - tw) // 2, header_y + (header_h - th) // 2),
        header_text,
        font=font_header,
        fill=HEADER_TEXT_COLOR,
    )

    # --- 曜日ヘッダー行 ---
    weekday_row_y = header_y + header_h + 4
    weekday_row_h = 50
    for i, wd in enumerate(WEEKDAYS_JP):
        x0 = margin_x + i * cell_w
        draw.rectangle(
            [x0, weekday_row_y, x0 + cell_w - 1, weekday_row_y + weekday_row_h - 1],
            fill=WEEKDAY_HEADER_BG,
        )
        tw, th = _text_size(draw, wd, font_weekday)
        draw.text(
            (x0 + (cell_w - tw) // 2, weekday_row_y + (weekday_row_h - th) // 2),
            wd,
            font=font_weekday,
            fill=WEEKDAY_COLORS[i],
        )

    # --- カレンダーグリッド ---
    grid_top = weekday_row_y + weekday_row_h + 2
    grid_bottom = content_bottom
    avail_h = grid_bottom - grid_top
    cell_h = avail_h // num_weeks

    for row_idx, week in enumerate(weeks):
        for col_idx, day in enumerate(week):
            x0 = margin_x + col_idx * cell_w
            y0 = grid_top + row_idx * cell_h
            x1 = x0 + cell_w - 2
            y1 = y0 + cell_h - 2

            # 当月外セル
            if day == 0:
                draw.rectangle([x0, y0, x1, y1], fill=CELL_OUTOFMONTH_BG)
                draw.rectangle([x0, y0, x1, y1], outline=CELL_BORDER_COLOR, width=1)
                continue

            date_str = f"{year}-{mon:02d}-{day:02d}"
            doctors = day_doctors.get(date_str, [])

            # セル背景色
            if col_idx == 0:      # 日曜
                cell_bg = CELL_SUN_BG
            elif col_idx == 6:    # 土曜
                cell_bg = CELL_SAT_BG
            elif doctors:
                cell_bg = CELL_WORK_BG   # 診療日 (緑系)
            else:
                cell_bg = CELL_HOLIDAY_BG  # 休診日 (赤系)

            draw.rectangle([x0, y0, x1, y1], fill=cell_bg)
            draw.rectangle([x0, y0, x1, y1], outline=CELL_BORDER_COLOR, width=1)

            # 日付番号
            day_text = str(day)
            if col_idx == 0:
                day_color = DAY_SUN_COLOR
            elif col_idx == 6:
                day_color = DAY_SAT_COLOR
            else:
                day_color = DAY_WEEKDAY_COLOR

            tw, th = _text_size(draw, day_text, font_day)
            day_x = x0 + (cell_w - tw) // 2
            day_y = y0 + 4
            draw.text((day_x, day_y), day_text, font=font_day, fill=day_color)

            # 医師名リスト
            if not doctors:
                continue

            doc_start_y = day_y + th + 4
            available_h = y1 - 4 - doc_start_y
            if available_h <= 0:
                continue

            # "Dr"サフィックスと特殊文字を除去して短縮表示
            doc_names = []
            for d in doctors:
                name = d.replace("Dr", "").strip()
                # 改行文字を含む異常値の処理
                name = name.split("\n")[0].split("_~")[0].strip()
                if name:
                    doc_names.append(name)

            n = len(doc_names)
            if n <= 3:
                dfont = font_doctor
                line_h = 24
            elif n <= 6:
                dfont = font_doctor_sm
                line_h = 21
            else:
                dfont = font_doctor_xs
                line_h = 18

            max_lines = max(1, available_h // line_h)
            show_names = doc_names[:max_lines]
            has_more = len(doc_names) > max_lines

            # "+N" 表示のために1行分確保
            if has_more:
                show_names = doc_names[: max(1, max_lines - 1)]

            for i, name in enumerate(show_names):
                tw_d, _ = _text_size(draw, name, dfont)
                draw.text(
                    (x0 + max(2, (cell_w - tw_d) // 2), doc_start_y + i * line_h),
                    name,
                    font=dfont,
                    fill=DOCTOR_TEXT_COLOR,
                )

            if has_more:
                remaining = len(doc_names) - len(show_names)
                more_text = f"+{remaining}"
                draw.text(
                    (x0 + 4, y1 - line_h + 2),
                    more_text,
                    font=font_more,
                    fill=(110, 110, 120),
                )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    # スタンドアロンテスト: モックデータで2026-03カレンダーを生成
    mock_data = [
        {"date": "2026-03-02", "doctor_name": "鉄Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-02", "doctor_name": "守屋Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-02", "doctor_name": "小川Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-03", "doctor_name": "中村Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-03", "doctor_name": "橘Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-03", "doctor_name": "北村Dr", "clinic_name": "池袋院"},
        {"date": "2026-03-04", "doctor_name": "王Dr", "clinic_name": "新宿院"},
        {"date": "2026-03-04", "doctor_name": "新井Dr", "clinic_name": "新宿院"},
        {"date": "2026-03-05", "doctor_name": "楠本Dr", "clinic_name": "大阪院"},
        {"date": "2026-03-05", "doctor_name": "山田Dr", "clinic_name": "大阪院"},
        {"date": "2026-03-05", "doctor_name": "原岡Dr", "clinic_name": "大阪院"},
        {"date": "2026-03-06", "doctor_name": "羽根Dr", "clinic_name": "福岡院"},
        {"date": "2026-03-09", "doctor_name": "鉄Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-09", "doctor_name": "小川Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-09", "doctor_name": "中村Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-10", "doctor_name": "守屋Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-11", "doctor_name": "橘Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-11", "doctor_name": "鉄Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-16", "doctor_name": "中村Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-16", "doctor_name": "王Dr", "clinic_name": "新宿院"},
        {"date": "2026-03-17", "doctor_name": "山田Dr", "clinic_name": "大阪院"},
        {"date": "2026-03-18", "doctor_name": "楠本Dr", "clinic_name": "大阪院"},
        {"date": "2026-03-19", "doctor_name": "鉄Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-20", "doctor_name": "橘Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-23", "doctor_name": "守屋Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-24", "doctor_name": "中村Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-25", "doctor_name": "鉄Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-26", "doctor_name": "小川Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-30", "doctor_name": "鉄Dr", "clinic_name": "銀座院"},
        {"date": "2026-03-31", "doctor_name": "橘Dr", "clinic_name": "銀座院"},
    ]

    out = generate_calendar_image(
        schedule_data=mock_data,
        month="2026-03",
        output_path="output/test_calendar.png",
    )
    print(f"生成完了: {out}")
