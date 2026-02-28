"""
image_poem.py — ポエム/名言画像生成モジュール
1080x1920 (9:16) Instagram Story形式
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# デフォルト名言リスト
# ============================================================
POEM_DEFAULTS = [
    {
        "text": "患者さんの笑顔が\n私たちの原動力です。",
        "author": "クリニックスタッフ一同",
    },
    {
        "text": "美しさとは\n自分らしく輝くこと。",
        "author": "",
    },
    {
        "text": "丁寧な診療と\n真摯なコミュニケーションで\n信頼を築く。",
        "author": "",
    },
    {
        "text": "一期一会の気持ちで\nすべての患者様と\n向き合います。",
        "author": "ドクター一同",
    },
    {
        "text": "健康と美は\n毎日の積み重ねから。",
        "author": "",
    },
]

# ============================================================
# 定数
# ============================================================
CANVAS_W = 1080
CANVAS_H = 1920
SAFE_TOP = 250
SAFE_BOTTOM = 250

# カラーパレット（ネイビー系グラデーション）
COLOR_BG_TOP = (15, 25, 60)       # ダークネイビー
COLOR_BG_BOTTOM = (30, 50, 110)   # 少し明るいネイビー
COLOR_TEXT_MAIN = (255, 255, 255)  # 白
COLOR_TEXT_AUTHOR = (180, 200, 240)  # 薄いブルーホワイト
COLOR_ACCENT = (100, 150, 230)    # アクセントライン（淡ブルー）

# フォントパス（優先順）
FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W2.ttc",
]

# フォールバック用（Noto Sans JP）
NOTO_FONT_PATHS = [
    "fonts/NotoSansJP-Regular.ttf",
    "fonts/NotoSansJP-Medium.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """日本語フォントをロード。見つからない場合はデフォルトフォント。"""
    for path in FONT_PATHS + NOTO_FONT_PATHS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _make_gradient_background(width: int, height: int) -> Image.Image:
    """縦グラデーション背景を生成。"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        r = int(COLOR_BG_TOP[0] + (COLOR_BG_BOTTOM[0] - COLOR_BG_TOP[0]) * t)
        g = int(COLOR_BG_TOP[1] + (COLOR_BG_BOTTOM[1] - COLOR_BG_TOP[1]) * t)
        b = int(COLOR_BG_TOP[2] + (COLOR_BG_BOTTOM[2] - COLOR_BG_TOP[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def _wrap_text_japanese(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """
    日本語テキストを指定幅で折り返す。
    改行コード（\\n）は尊重する。
    """
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            test = current + char
            bbox = font.getbbox(test)
            w = bbox[2] - bbox[0]
            if w > max_width and current:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def generate_poem_image(text: str, output_path: str, author: str = "") -> str:
    """
    ポエム/名言画像を生成して output_path に保存する。

    Args:
        text: 名言テキスト（\\n で改行可）
        output_path: 出力先パス（例: "output/poem_20260301.png"）
        author: 著者名（省略可）

    Returns:
        output_path（保存されたファイルパス）
    """
    # 出力ディレクトリを作成
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # キャンバス生成
    img = _make_gradient_background(CANVAS_W, CANVAS_H)
    draw = ImageDraw.Draw(img)

    # フォント
    font_main = _load_font(68)
    font_author = _load_font(36)

    # 描画エリア（セーフゾーン内）
    draw_top = SAFE_TOP
    draw_bottom = CANVAS_H - SAFE_BOTTOM
    draw_h = draw_bottom - draw_top
    max_text_w = CANVAS_W - 120  # 左右60pxマージン

    # テキスト折り返し
    lines = _wrap_text_japanese(text, font_main, max_text_w)

    # 行高さ計算
    line_spacing = 20
    bbox_sample = font_main.getbbox("あ")
    line_h = bbox_sample[3] - bbox_sample[1]
    total_text_h = line_h * len(lines) + line_spacing * (len(lines) - 1)

    # 著者行の高さ
    author_gap = 60
    author_h = 0
    if author:
        bbox_author = font_author.getbbox(author)
        author_h = bbox_author[3] - bbox_author[1] + author_gap

    # アクセントライン
    accent_line_h = 4
    accent_gap = 40

    total_block_h = total_text_h + accent_line_h + accent_gap * 2 + author_h

    # 縦中央
    start_y = draw_top + (draw_h - total_block_h) // 2

    # --- メインテキスト描画 ---
    y = start_y
    for line in lines:
        if line:
            bbox = font_main.getbbox(line)
            line_w = bbox[2] - bbox[0]
            x = (CANVAS_W - line_w) // 2
            # シャドウ（わずかにオフセット）
            draw.text((x + 2, y + 2), line, font=font_main, fill=(0, 0, 30, 120))
            draw.text((x, y), line, font=font_main, fill=COLOR_TEXT_MAIN)
        y += line_h + line_spacing

    # --- アクセントライン ---
    line_y = y + accent_gap - line_spacing
    accent_w = 120
    accent_x = (CANVAS_W - accent_w) // 2
    draw.rectangle(
        [accent_x, line_y, accent_x + accent_w, line_y + accent_line_h],
        fill=COLOR_ACCENT,
    )

    # --- 著者テキスト ---
    if author:
        author_text = f"— {author}"
        bbox_a = font_author.getbbox(author_text)
        author_w = bbox_a[2] - bbox_a[0]
        ax = (CANVAS_W - author_w) // 2
        ay = line_y + accent_line_h + accent_gap
        draw.text((ax, ay), author_text, font=font_author, fill=COLOR_TEXT_AUTHOR)

    img.save(output_path, "PNG")
    return output_path


# ============================================================
# スタンドアロンテスト
# ============================================================
if __name__ == "__main__":
    poem = POEM_DEFAULTS[0]
    out = generate_poem_image(
        text=poem["text"],
        output_path="output/test_poem.png",
        author=poem["author"],
    )
    print(f"生成完了: {out}")
