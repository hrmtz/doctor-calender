"""
image_schedule.py — 出勤情報ストーリー画像生成モジュール (1080x1920, 9:16)
"""

import os
from datetime import datetime
from typing import Dict

from PIL import Image, ImageDraw, ImageFont

CANVAS_W = 1080
CANVAS_H = 1920
SAFE_ZONE = 250  # 上下セーフゾーン px（Instagram UIオーバーレイ回避）

BG_COLOR = (250, 250, 252)
TEXT_COLOR = (30, 30, 40)
ACCENT_COLOR = (30, 100, 200)
SUB_COLOR = (100, 110, 130)

FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    "/System/Library/Fonts/Supplemental/HiraginoSans.ttc",
]

WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    # フォールバック: fonts/配下のNoto Sans JP
    noto_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Regular.ttf")
    if os.path.exists(noto_path):
        return ImageFont.truetype(noto_path, size)

    return ImageFont.load_default()


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    canvas_w: int = CANVAS_W,
) -> int:
    """テキストをX軸中央に描画し、テキスト高さを返す。"""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(((canvas_w - text_w) // 2, y), text, font=font, fill=fill)
    return text_h


def generate_schedule_image(schedule_entry: Dict, output_path: str) -> str:
    """出勤情報ストーリー画像を生成する。

    Args:
        schedule_entry: date, doctor_name, clinic_name, start_time, end_time を持つdict
        output_path: 保存先パス（.png）

    Returns:
        output_path
    """
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(52)
    font_large = _get_font(76)
    font_medium = _get_font(60)
    font_small = _get_font(44)
    font_date = _get_font(46)

    content_top = SAFE_ZONE
    content_bottom = CANVAS_H - SAFE_ZONE
    content_h = content_bottom - content_top

    # アクセントライン（上）
    bar_h = 6
    margin_x = 80
    draw.rectangle(
        [margin_x, content_top + 50, CANVAS_W - margin_x, content_top + 50 + bar_h],
        fill=ACCENT_COLOR,
    )

    # 日付表示
    date_str = schedule_entry.get("date", "")
    if date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = WEEKDAYS_JP[dt.weekday()]
        date_display = f"{dt.year}年{dt.month}月{dt.day}日（{weekday}）"
    else:
        date_display = ""

    doctor_name = schedule_entry.get("doctor_name", "")
    clinic_name = schedule_entry.get("clinic_name", "")
    start_time = schedule_entry.get("start_time", "")
    end_time = schedule_entry.get("end_time", "")

    # コンテンツ縦中央をベースに配置
    # テキストブロック合計高さを推定して縦中央に揃える
    block_h_estimate = 520  # おおよその合計高さ
    y = content_top + (content_h - block_h_estimate) // 2

    # 日付
    if date_display:
        _draw_centered_text(draw, date_display, y, font_date, SUB_COLOR)
    y += 80

    # 区切りライン（細）
    line_y = y + 10
    draw.rectangle(
        [margin_x + 120, line_y, CANVAS_W - margin_x - 120, line_y + 2],
        fill=(200, 210, 230),
    )
    y += 50

    # 「本日」
    _draw_centered_text(draw, "本日", y, font_title, TEXT_COLOR)
    y += 72

    # 「○○先生は」（強調色）
    _draw_centered_text(draw, f"{doctor_name}先生は", y, font_large, ACCENT_COLOR)
    y += 110

    # 「△△に」
    _draw_centered_text(draw, f"{clinic_name}に", y, font_medium, TEXT_COLOR)
    y += 90

    # 「出勤しています」
    _draw_centered_text(draw, "出勤しています", y, font_medium, TEXT_COLOR)
    y += 100

    # 勤務時間（データがあれば）
    if start_time and end_time:
        time_text = f"勤務時間　{start_time} 〜 {end_time}"
        _draw_centered_text(draw, time_text, y, font_small, SUB_COLOR)
        y += 60

    # アクセントライン（下）
    draw.rectangle(
        [margin_x, content_bottom - 56, CANVAS_W - margin_x, content_bottom - 56 + bar_h],
        fill=ACCENT_COLOR,
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
