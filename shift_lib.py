"""shift_lib.py — pure logic for the doctor-shift calendars.

No Google API writes here beyond reading the Sheet. Everything that decides
*what* goes on a public calendar lives in this one module so the publication
horizon is a single, auditable chokepoint.

Two axes are produced from one shift list:
  - clinic view  : {clinic_slug: {date: [doctor_display, ...]}}   (5 clinics)
  - doctor view  : {doctor_slug: {date: [clinic_label, ...]}}     (~25 doctors)

Publication horizon (structural non-leak):
  The booking system opens the month that is 2 ahead on the 1st of each month
  (confirmed: "8/1 に 10 月が公開される"). So at any date the public horizon is
  the LAST day of (current_month + 2). Shifts beyond it are never emitted, and
  the sync deletes any event beyond it — a single cutoff both ways.
"""

from __future__ import annotations

import calendar
import datetime as dt
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Mappings (recon 2026-07-22 against sheet + zetith-site D1 ec_doctors/ec_clinics)
# ---------------------------------------------------------------------------

# Sheet shift-cell code -> short clinic label shown in DOCTOR calendars.
CLINIC_LABEL: Dict[str, str] = {
    "銀座": "銀座院",
    "新宿": "新宿院",
    "池袋": "池袋院",
    "大阪": "大阪院",
    "福岡": "福岡院",
    "静脈": "静脈科",
    "歯科": "歯科",
}

# Sheet shift-cell code -> zetith-site clinic slug, for the CLINIC calendars.
# Only the 5 physical clinics get their own calendar+embed. 静脈/歯科 have their
# own external sites (osaka-vein / zetith-dental) → excluded from clinic axis,
# but still appear as workplace labels inside the doctor calendars.
CLINIC_CODE_TO_SLUG: Dict[str, str] = {
    "銀座": "ginza",
    "新宿": "shinjuku",
    "池袋": "ikebukuro",
    "大阪": "osaka",
    "福岡": "fukuoka",
}
CLINIC_SLUG_NAME: Dict[str, str] = {
    "ginza": "銀座院",
    "shinjuku": "新宿院",
    "ikebukuro": "池袋院",
    "osaka": "大阪院",
    "fukuoka": "福岡院",
}

# Sheet doctor family-token (the part before "Dr") -> ec_doctors slug.
# Family-token = raw_name.split("Dr")[0].strip(). Doctors without a profile page
# (前田/原岡/佐藤/境/後藤) are intentionally absent → they show up in clinic
# calendars by display name but get no doctor calendar (no embed target).
DOCTOR_NAME_TO_SLUG: Dict[str, str] = {
    "鉄": "tetsu",
    "守屋": "moriya",
    "中村": "hiromitsu-nakamura",
    "小川": "ogawa-satoshi",
    "橘": "tachibana-kiyomi",
    "木塚": "yuichiro-kizuka",
    "上木原": "uekihara",
    "林": "midori-hayashi",
    "高梨": "ryo-takanashi",
    "髙梨": "ryo-takanashi",  # sheet may use either 高/髙
    "桐渕": "hideto-kiribuchi",
    "北村": "sho-kitamura",
    "沈": "jinghui-shen",
    "王": "wang-su",
    "新井": "arai",
    "副島": "soejima-naoto",
    "楠本": "kusumoto-takuya",
    "山田": "yamada-mayuka",
    "羽根": "hane-kazuhide",
    "佟": "tong-xiaoning",
    "佐久間": "ayako-sakuma",
    "魚住": "shuhei-uozumi",
    "矢嶋": "yajima-aika",
    "井上舞": "inoue-mai",
    "井上": "inoue-mai",
    "野村": "nomura-naoto",
    "富永": "tominaga",
}

# Doctor rank for CLINIC-calendar ordering (user: 理事長→院長→…). Derived from
# ec_doctors.title_position (recon 2026-07-22). Lower = shown first.
#   0 理事長 / 1 院長 / 2 副院長 / 3 医師(常勤・歯科医・専門医) / 4 非常勤医師 / 5 その他
# Unknown/unmapped slug → DEFAULT_RANK (mixes in at 医師 level).
DEFAULT_RANK = 3
DOCTOR_SLUG_RANK: Dict[str, int] = {
    "tetsu": 0,               # 医療法人社団SUNSET 理事長
    "tachibana-kiyomi": 1,    # 銀座院 院長
    "wang-su": 1,             # 新宿院 院長
    "sho-kitamura": 1,        # 池袋院 院長
    "hane-kazuhide": 1,       # 福岡院 院長
    "kusumoto-takuya": 1,     # 大阪心斎橋院 院長
    "ayako-sakuma": 1,        # 審美歯科 院長
    "tong-xiaoning": 1,       # 大阪静脈瘤クリニック 院長
    "ogawa-satoshi": 2,       # 銀座院 副院長
    "hiromitsu-nakamura": 3, "moriya": 3, "arai": 3, "inoue-mai": 3,
    "jinghui-shen": 3, "soejima-naoto": 3, "yamada-mayuka": 3,
    "shuhei-uozumi": 3, "yajima-aika": 3, "nomura-naoto": 3,
    "hideto-kiribuchi": 4, "midori-hayashi": 4, "ryo-takanashi": 4,
    "uekihara": 4, "yuichiro-kizuka": 4,
    "tominaga": 5,            # アートメイク専門看護師
}


def _rank_of_display(disp: str) -> int:
    """Rank for a clinic-calendar display name like '鉄Dr'."""
    tok = disp[:-2].strip() if disp.endswith("Dr") else disp.strip()
    slug = DOCTOR_NAME_TO_SLUG.get(tok)
    return DOCTOR_SLUG_RANK.get(slug, DEFAULT_RANK) if slug else DEFAULT_RANK


# Cells that mean "not working".
SKIP_VALUES = {"休", "希", "有", "", "産", "産休"}

SOURCE_TAG = "shift-sync"  # extendedProperties.private.source


# ---------------------------------------------------------------------------
# Horizon
# ---------------------------------------------------------------------------

def add_months(year: int, month: int, n: int) -> Tuple[int, int]:
    idx = (year * 12 + (month - 1)) + n
    return idx // 12, idx % 12 + 1


def month_last_day(year: int, month: int) -> dt.date:
    return dt.date(year, month, calendar.monthrange(year, month)[1])


def published_horizon(today: dt.date) -> dt.date:
    """Last publishable date = last day of (current month + 2)."""
    y, m = add_months(today.year, today.month, 2)
    return month_last_day(y, m)


def target_months(today: dt.date) -> List[Tuple[int, int]]:
    """(year, month) list from the current month through the horizon month."""
    out = []
    y, m = today.year, today.month
    hy, hm = add_months(y, m, 2)
    while (y, m) <= (hy, hm):
        out.append((y, m))
        y, m = add_months(y, m, 1)
    return out


def window_bounds(today: dt.date) -> Tuple[dt.date, dt.date]:
    """[first day of current month, horizon] — the full publishable window."""
    return dt.date(today.year, today.month, 1), published_horizon(today)


# ---------------------------------------------------------------------------
# Sheet parsing
# ---------------------------------------------------------------------------

def _family_token(raw: str) -> str:
    return raw.split("Dr")[0].strip().splitlines()[0].strip()


def _display_name(raw: str) -> str:
    """Doctor label for clinic-calendar events, e.g. '鉄Dr'."""
    tok = _family_token(raw)
    return f"{tok}Dr" if tok else raw.strip()


def resolve_sheet_title(meta_sheets: List[dict], year: int, month: int):
    """Find the exact worksheet title for a year/month (titles carry trailing
    spaces / suffixes; prefer exact 'YYYY.M月', else prefix match)."""
    target = f"{year}.{month}月"
    titles = [s["properties"]["title"] for s in meta_sheets]
    for t in titles:
        if t == target:
            return t
    for t in titles:
        if t.startswith(target):
            return t
    return None


def parse_month_rows(rows: List[List[str]], year: int, month: int) -> List[dict]:
    """Rows from one month worksheet -> [{date, doctor_raw, code}]."""
    if not rows:
        return []
    # Day-number header row = first row whose col index 2 == '1'.
    day_row = next((r for r in rows if len(r) > 2 and r[2].strip() == "1"), None)
    if day_row is None:
        return []
    day_cols: Dict[int, int] = {}
    for col_idx in range(2, len(day_row)):
        v = day_row[col_idx].strip()
        if v.isdigit():
            day_cols[col_idx] = int(v)

    out: List[dict] = []
    for r in rows:
        if len(r) < 2:
            continue
        name = r[1].strip()
        if "Dr" not in name or "院Dr人数" in name:
            continue
        for col_idx, day in day_cols.items():
            if col_idx >= len(r):
                continue
            code = r[col_idx].strip()
            if code in SKIP_VALUES or code not in CLINIC_LABEL:
                continue
            try:
                d = dt.date(year, month, day)
            except ValueError:
                continue
            out.append({"date": d, "doctor_raw": name, "code": code})
    return out


# ---------------------------------------------------------------------------
# View building (horizon enforced here)
# ---------------------------------------------------------------------------

def build_views(shifts: List[dict], today: dt.date):
    """Return (clinic_view, doctor_view, unmapped) with the horizon enforced.

    clinic_view: {clinic_slug: {date: sorted[doctor_display]}}
    doctor_view: {doctor_slug: {date: sorted[clinic_label]}}
    unmapped:    set of doctor family-tokens seen in shifts with no slug
    """
    lo, hi = window_bounds(today)
    clinic_view: Dict[str, Dict[dt.date, list]] = {}
    doctor_view: Dict[str, Dict[dt.date, list]] = {}
    unmapped = set()

    for s in shifts:
        d = s["date"]
        if d < lo or d > hi:  # STRUCTURAL cutoff — never leak beyond horizon
            continue
        code = s["code"]
        # clinic axis (5 physical clinics only)
        cslug = CLINIC_CODE_TO_SLUG.get(code)
        if cslug:
            clinic_view.setdefault(cslug, {}).setdefault(d, [])
            disp = _display_name(s["doctor_raw"])
            if disp not in clinic_view[cslug][d]:
                clinic_view[cslug][d].append(disp)
        # doctor axis
        tok = _family_token(s["doctor_raw"])
        dslug = DOCTOR_NAME_TO_SLUG.get(tok)
        if not dslug:
            unmapped.add(tok)
            continue
        label = CLINIC_LABEL[code]
        doctor_view.setdefault(dslug, {}).setdefault(d, [])
        if label not in doctor_view[dslug][d]:
            doctor_view[dslug][d].append(label)

    # Clinic axis: order the day's doctors by rank (理事長→院長→…), then name.
    for day_map in clinic_view.values():
        for d in day_map:
            day_map[d].sort(key=lambda disp: (_rank_of_display(disp), disp))
    # Doctor axis: clinic labels stay name-sorted.
    for day_map in doctor_view.values():
        for d in day_map:
            day_map[d].sort()
    return clinic_view, doctor_view, unmapped
