#!/usr/bin/env python3
"""ig_calendar.py — Instagram向け 月次シフトカレンダー画像のHTMLを生成する。

意匠: クリニック写真ヘッダー + 医師別カラーチップ + セリフ体。
HTMLを吐き、ヘッドレスChrome/Playwrightで 1080x1350 (IG 4:5) にレンダーしてPNG化。
"""
from __future__ import annotations

import calendar
import json
import sys

# 医師 → 署名カラー。鉄/小川/中村/橘/守屋 は元画像(2026-08 Ginza)から実サンプリング、
# 他は同系のミュート配色を割当(色B: 全院カードが色付きに)。未登録家族名は既定グレー。
DOCTOR_COLORS = {
    "鉄": "#323232", "小川": "#159cb0", "中村": "#9db9af", "橘": "#a8819d", "守屋": "#c5c47e",
    "木塚": "#6f8ca6", "上木原": "#bb8a5e", "林": "#8a9d63", "高梨": "#8a7fa6", "髙梨": "#8a7fa6",
    "桐渕": "#c58a86", "北村": "#5f9e93", "沈": "#b39a5f", "王": "#7086bd", "新井": "#cbae63",
    "副島": "#9a6f9c", "楠本": "#b0725a", "山田": "#6fae8f", "羽根": "#ab7b8c", "佟": "#7f95a5",
    "佐久間": "#c58aa2", "魚住": "#6fa1ad", "矢嶋": "#b89a5c", "井上": "#c99a80", "井上舞": "#c99a80",
    "野村": "#6f9ca0", "富永": "#b884a0", "前田": "#9aa06a", "原岡": "#7ca0b0", "佐藤": "#a88fa0",
    "後藤": "#86a074", "境": "#b09070",
}
DEFAULT_COLOR = "#a0a0a0"
MONTHS_EN = ["", "January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]
WEEKDAYS_EN = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def _chip(fam: str) -> str:
    color = DOCTOR_COLORS.get(fam, DEFAULT_COLOR)
    return f'<span class="chip" style="background:{color}">{fam}</span>'


def build_html(clinic_en: str, year: int, month: int,
               hero_url: str, day_doctors: dict) -> str:
    cal = calendar.Calendar(firstweekday=6)  # Sunday first
    weeks = cal.monthdayscalendar(year, month)

    dow_html = "".join(
        f'<div class="dow {"sun" if i==0 else "sat" if i==6 else ""}">{wd}</div>'
        for i, wd in enumerate(WEEKDAYS_EN)
    )

    cells = []
    for week in weeks:
        for i, day in enumerate(week):
            if day == 0:
                cells.append('<div class="cell pad"></div>')
                continue
            docs = day_doctors.get(str(day), [])
            chips = "".join(_chip(d) for d in docs)
            cls = "sun" if i == 0 else "sat" if i == 6 else ""
            cells.append(
                f'<div class="cell {cls}"><span class="date">{day}</span>'
                f'<div class="chips">{chips}</div></div>'
            )
    grid_html = "".join(cells)
    rows = len(weeks)

    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500;600;700&family=Pinyon+Script&family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ width:1080px; height:1350px; }}
  body {{ font-family:"Cormorant Garamond",serif; background:#fff; }}
  .card {{ width:1080px; height:1350px; display:flex; flex-direction:column; overflow:hidden; }}

  /* ---- header ---- */
  .header {{ position:relative; height:398px; overflow:hidden; background:#1a1618; }}
  .header .hero {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
  .header .veil {{ position:absolute; inset:0;
    background:linear-gradient(100deg, rgba(16,13,15,.82) 0%, rgba(16,13,15,.58) 42%, rgba(16,13,15,.48) 72%, rgba(16,13,15,.62) 100%); }}
  .brand {{ position:absolute; left:64px; top:50%; transform:translateY(-50%); color:#fff; }}
  .brand .sub {{ font-size:31px; letter-spacing:.22em; font-weight:400; opacity:.95; }}
  .brand .name {{ font-size:104px; letter-spacing:.10em; font-weight:500; line-height:1.02; margin-top:2px; }}
  .month {{ position:absolute; right:70px; top:50%; transform:translateY(-52%); color:#fff; text-align:right; }}
  .month .script {{ font-family:"Pinyon Script",cursive; font-size:76px; line-height:.5; position:relative; left:-6px; opacity:.92; }}
  .month .num {{ font-size:232px; font-weight:500; line-height:.82; letter-spacing:-.02em; }}

  /* ---- weekday row ---- */
  .weekdays {{ display:grid; grid-template-columns:repeat(7,1fr); background:#141013; }}
  .dow {{ text-align:center; color:#fff; font-size:33px; font-weight:400; padding:9px 0; letter-spacing:.04em; }}

  /* ---- calendar grid ---- */
  .grid {{ flex:1; display:grid; grid-template-columns:repeat(7,1fr);
           grid-template-rows:repeat({rows},1fr); }}
  .cell {{ border-right:1px solid #e6e6e6; border-bottom:1px solid #e6e6e6;
           padding:9px 8px 6px; display:flex; flex-direction:column; min-width:0; }}
  .cell:nth-child(7n) {{ border-right:none; }}
  .cell.pad {{ background:#fff; }}
  .date {{ font-size:38px; font-weight:400; color:#3b3b3b; line-height:1; margin-bottom:6px;
           font-variant-numeric:lining-nums; font-feature-settings:"lnum" 1,"onum" 0; }}
  .cell.sun .date {{ color:#b06a72; }}
  .cell.sat .date {{ color:#6a86a8; }}
  .chips {{ display:flex; flex-wrap:wrap; gap:5px 6px; align-content:flex-start; }}
  .chip {{ width:calc(50% - 3px); text-align:center; color:#fff;
           font-family:"Noto Sans JP",sans-serif; font-weight:500; font-size:23px;
           line-height:1.5; border-radius:3px; white-space:nowrap; overflow:hidden; }}
</style></head><body>
<div class="card">
  <div class="header">
    <img class="hero" src="{hero_url}">
    <div class="veil"></div>
    <div class="brand"><div class="sub">Zetith Beauty Clinic</div><div class="name">{clinic_en}</div></div>
    <div class="month"><div class="script">{MONTHS_EN[month]}</div><div class="num">{month}</div></div>
  </div>
  <div class="weekdays">{dow_html}</div>
  <div class="grid">{grid_html}</div>
</div></body></html>"""


# ---------------------------------------------------------------------------
# 医師軸: その日の勤務院を院カラーの丸で表す (per-doctor schedule card)
# ---------------------------------------------------------------------------

# 院 → (英表記, 丸カラー)。元画像(鉄9月)から GINZA/OSAKA/FUKUOKA を実サンプリング、
# 他院は識別しやすい配色を付与。
CLINIC_META = {
    "銀座院": ("GINZA", "#7c2237"),
    "大阪院": ("OSAKA", "#e6d488"),
    "福岡院": ("FUKUOKA", "#8398a6"),
    "新宿院": ("SHINJUKU", "#6f8f6a"),
    "池袋院": ("IKEBUKURO", "#b57c43"),
    "静脈科": ("VEIN", "#8a7ba0"),
    "歯科": ("DENTAL", "#c58fa0"),
}


def build_doctor_html(doctor_name: str, year: int, month: int, hero_url: str,
                      photo_url: str, day_clinic: dict) -> str:
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)
    rows = len(weeks)

    # legend = distinct clinics this doctor works at, in a stable order
    present = [c for c in CLINIC_META if c in set(day_clinic.values())]
    legend = "".join(
        f'<span class="lg"><span class="dot" style="background:{CLINIC_META[c][1]}"></span>{CLINIC_META[c][0]}</span>'
        for c in present
    )

    dow_html = "".join(
        f'<div class="dow">{wd.upper()}</div>' for wd in WEEKDAYS_EN
    )
    cells = []
    for week in weeks:
        for i, day in enumerate(week):
            if day == 0:
                cells.append('<div class="cell pad"></div>')
                continue
            clinic = day_clinic.get(str(day))
            dot = (f'<span class="cdot" style="background:{CLINIC_META[clinic][1]}"></span>'
                   if clinic in CLINIC_META else "")
            cls = "sun" if i == 0 else "sat" if i == 6 else ""
            cells.append(
                f'<div class="cell {cls}"><span class="date">{day}</span>'
                f'<div class="dotwrap">{dot}</div></div>'
            )
    grid_html = "".join(cells)

    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500;1,600&family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ width:1080px; height:1350px; }}
  body {{ font-family:"Cormorant Garamond",serif; background:#3d4a54; }}
  .card {{ width:1080px; height:1350px; position:relative; overflow:hidden; display:flex; flex-direction:column; }}
  .bg {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
  .bgveil {{ position:absolute; inset:0;
    background:linear-gradient(120deg, rgba(55,70,84,.86) 0%, rgba(60,74,86,.70) 40%, rgba(70,86,98,.55) 100%); }}
  .photo {{ position:absolute; right:12px; top:18px; height:452px; width:auto;
    -webkit-mask-image:linear-gradient(to right, transparent 0%, #000 34%);
            mask-image:linear-gradient(to right, transparent 0%, #000 34%); }}

  .head {{ position:relative; padding:70px 0 26px 70px; color:#fff; }}
  .head .num {{ font-style:italic; font-weight:500; font-size:150px; line-height:.8;
    letter-spacing:.02em; text-shadow:0 2px 18px rgba(0,0,0,.28); }}
  .head .sched {{ font-style:italic; font-weight:500; font-size:66px; line-height:1.05; margin-top:6px;
    text-shadow:0 2px 14px rgba(0,0,0,.28); }}
  .legend {{ margin-top:20px; display:flex; gap:34px; align-items:center; }}
  .lg {{ display:flex; align-items:center; gap:11px; font-size:31px; letter-spacing:.10em; color:#fff; }}
  .lg .dot {{ width:26px; height:26px; border-radius:50%; display:inline-block; box-shadow:0 0 0 1px rgba(255,255,255,.35); }}

  .weekdays {{ position:relative; display:grid; grid-template-columns:repeat(7,1fr); background:#151013; }}
  .dow {{ text-align:center; color:#fff; font-style:italic; font-size:31px; font-weight:500; padding:11px 0; letter-spacing:.06em; }}

  .grid {{ position:relative; flex:1; display:grid; grid-template-columns:repeat(7,1fr);
           grid-template-rows:repeat({rows},1fr); background:rgba(255,255,255,.0); }}
  .cell {{ border-right:1px solid rgba(120,135,148,.5); border-bottom:1px solid rgba(120,135,148,.5);
           background:#fff; padding:10px 0 0 12px; display:flex; flex-direction:column; }}
  .cell:nth-child(7n) {{ border-right:none; }}
  .cell.pad {{ background:#d9dde1; }}
  .date {{ font-size:34px; font-weight:400; color:#33383d; line-height:1;
           font-variant-numeric:lining-nums; font-feature-settings:"lnum" 1; }}
  .cell.sun .date {{ color:#c98a86; }}
  .cell.sat .date {{ color:#7d97ad; }}
  .dotwrap {{ flex:1; display:flex; align-items:center; justify-content:center; padding-right:12px; }}
  .cdot {{ width:74px; height:74px; border-radius:50%; box-shadow:0 0 0 1px rgba(0,0,0,.06); }}

  .footer {{ position:relative; text-align:center; padding:16px 0 22px;
    color:#fff; font-size:34px; letter-spacing:.10em; background:rgba(30,38,45,.0); }}
</style></head><body>
<div class="card">
  <img class="bg" src="{hero_url}">
  <div class="bgveil"></div>
  <img class="photo" src="{photo_url}">
  <div class="head">
    <div class="num">{month:02d}</div>
    <div class="sched">{MONTHS_EN[month]} schedule</div>
    <div class="legend">{legend}</div>
  </div>
  <div class="weekdays">{dow_html}</div>
  <div class="grid">{grid_html}</div>
  <div class="footer">Zetith Beauty Clinic</div>
</div></body></html>"""


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "clinic":
        data = json.load(open(sys.argv[2], encoding="utf-8"))
        y, m = map(int, sys.argv[3].split("-"))
        sys.stdout.write(build_html(sys.argv[4], y, m, sys.argv[5], data["days"]))
    elif mode == "doctor":
        data = json.load(open(sys.argv[2], encoding="utf-8"))  # {"1":"銀座院",...}
        y, m = map(int, sys.argv[3].split("-"))
        # argv: doctor mode data YYYY-MM name hero photo
        sys.stdout.write(build_doctor_html(sys.argv[4], y, m, sys.argv[5], sys.argv[6], data))
