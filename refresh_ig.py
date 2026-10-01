#!/usr/bin/env python3
"""refresh_ig.py — 日次cron本体。シート更新を検知したら Instagram カードを
再生成して共有ドライブへ再アップロードする。

流れ:
  1) Drive APIでシフトSheetの modifiedTime を取得 → 前回値(state.json)と比較。
     変化なしなら何もせず終了(--force で強制)。
  2) 対象月(当月, +1, +2)を Sheets API で読み、クリニック/医師データを構築。
     記入が薄い月(下書き)は閾値でスキップ。
  3) google-chrome headless で各カードPNG化 → 共有ドライブ月フォルダへアップロード。

chichibu で実行(chromeが要る)。SA鍵はローカルの seo-research を使用。
"""
import calendar
import datetime as dt
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shift_lib as SL  # noqa: E402
import ig_calendar as IG  # noqa: E402
import render_ig_cards as R  # noqa: E402
import drive_upload as DU  # noqa: E402
from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

SA_KEY = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY",
                        "/home/hrmtz/projects/seo-research/secrets/service_account.json")
DRIVE_ID = os.environ.get("IG_DRIVE_ID", "0AIsdXy689B0aUk9PVA")
ZSITE_IMG = "/home/hrmtz/projects/zetith-site/public/img"
WORK = os.environ.get("IG_WORKDIR", "/home/hrmtz/doctor-calender-ig")
STATE = os.path.join(WORK, "state.json")
SPARSE_MIN = int(os.environ.get("IG_SPARSE_MIN", "180"))  # 月あたり総勤務エントリの下限
CLINIC_CODES = ["銀座", "新宿", "池袋", "大阪", "福岡", "静脈", "歯科"]

with open(os.path.join(HERE, "scripts", "list_shifts.py"), encoding="utf-8") as f:
    import re
    SHEET_ID = re.search(r'SHEET_ID\s*=\s*"([^"]+)"', f.read()).group(1)


def _creds(scopes):
    return service_account.Credentials.from_service_account_file(SA_KEY, scopes=scopes)


def sheet_modified_time(drive):
    return drive.files().get(fileId=SHEET_ID, fields="modifiedTime",
                             supportsAllDrives=True).execute()["modifiedTime"]


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {}


def save_state(s):
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def add_months(y, m, n):
    idx = (y * 12 + m - 1) + n
    return idx // 12, idx % 12 + 1


def read_month(sheets, y, m):
    """Return (clinics{code:{day:[fam]}}, doctors{fam:{day:label}}, entries)."""
    meta = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()["sheets"]
    title = SL.resolve_sheet_title(meta, y, m)
    if not title:
        return None, None, 0
    rows = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"'{title}'").execute().get("values", [])
    day_row = next((r for r in rows if len(r) > 2 and r[2].strip() == "1"), None)
    if not day_row:
        return None, None, 0
    day_cols = {i: int(v.strip()) for i, v in enumerate(day_row)
                if i >= 2 and v.strip().isdigit()}
    clinics = {c: {} for c in CLINIC_CODES}
    doctors, entries = {}, 0
    for r in rows:
        if len(r) < 2:
            continue
        name = r[1].strip()
        if "Dr" not in name or "院Dr人数" in name:
            continue
        fam = name.split("Dr")[0].strip().splitlines()[0].strip()
        for ci, day in day_cols.items():
            if ci >= len(r):
                continue
            code = r[ci].strip()
            if code not in CLINIC_CODES:
                continue
            clinics[code].setdefault(str(day), []).append(fam)
            doctors.setdefault(fam, {}).setdefault(str(day), SL.CLINIC_LABEL[code])
            entries += 1
    return clinics, doctors, entries


def ensure_heroes():
    os.makedirs(WORK, exist_ok=True)
    for h in ["ginza", "shinjuku", "ikebukuro", "osaka", "fukuoka", "vein", "dental"]:
        src = os.path.join(ZSITE_IMG, f"hero-{h}.webp")
        dst = os.path.join(WORK, f"hero-{h}.webp")
        if os.path.exists(src) and (not os.path.exists(dst)
                                    or os.path.getmtime(src) > os.path.getmtime(dst)):
            shutil.copy2(src, dst)


def render_month(y, m, clinics, doctors, assets):
    outdir = os.path.join(WORK, "out", f"{y}-{m:02d}")
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for code, (en, hero) in R.CLINIC_EN.items():
        days = clinics.get(code, {})
        if not days:
            continue
        hn = f"clinic_{hero}.html"
        open(os.path.join(WORK, hn), "w", encoding="utf-8").write(
            IG.build_html(en, y, m, f"hero-{hero}.webp", days))
        n += R.render(WORK, hn, os.path.join(outdir, f"【{code}】{y}_{m}月.png"))
    for fam, data in doctors.items():
        slug = SL.DOCTOR_NAME_TO_SLUG.get(fam)
        a = assets.get(slug) if slug else None
        if not a or not a.get("file"):
            continue
        hero = R.main_clinic_hero(a.get("title", ""), data)
        hn = f"doctor_{slug}.html"
        open(os.path.join(WORK, hn), "w", encoding="utf-8").write(
            IG.build_doctor_html(fam, y, m, f"hero-{hero}.webp", a["file"], data))
        n += R.render(WORK, hn, os.path.join(outdir, f"【{fam}】{y}_{m}月.png"))
    return outdir, n


def main():
    force = "--force" in sys.argv
    os.makedirs(WORK, exist_ok=True)
    drive = build("drive", "v3", credentials=_creds(
        ["https://www.googleapis.com/auth/drive"]), cache_discovery=False)
    sheets = build("sheets", "v4", credentials=_creds(
        ["https://www.googleapis.com/auth/spreadsheets.readonly"]), cache_discovery=False)

    mtime = sheet_modified_time(drive)
    state = load_state()
    today = dt.date.today()
    window = ["%d-%02d" % add_months(today.year, today.month, n) for n in range(3)]
    # 月が替わると対象月(+2)が増えるので、sheet未更新でも window 変化時は走らせる
    if not force and state.get("sheet_mtime") == mtime and state.get("window") == window:
        print(f"[skip] sheet unchanged since {mtime}")
        return

    print(f"[run] sheet changed -> {mtime}")
    ensure_heroes()
    assets_path = os.path.join(WORK, "doctor_assets.json")
    if not os.path.exists(assets_path):
        print("ERROR: doctor_assets.json missing. Run bootstrap_assets first.")
        sys.exit(2)
    assets = json.load(open(assets_path, encoding="utf-8"))

    import hashlib
    hashes = state.get("month_hashes", {})
    for n in range(3):  # 当月, +1, +2
        y, m = add_months(today.year, today.month, n)
        key = f"{y}-{m:02d}"
        clinics, doctors, entries = read_month(sheets, y, m)
        if clinics is None or entries < SPARSE_MIN:
            print(f"  {key}: skip (entries={entries} < {SPARSE_MIN} or no sheet)")
            continue
        h = hashlib.sha256(json.dumps([clinics, doctors], ensure_ascii=False,
                                      sort_keys=True).encode()).hexdigest()
        if not force and hashes.get(key) == h:
            print(f"  {key}: unchanged (hash match) — skip render")
            continue
        outdir, made = render_month(y, m, clinics, doctors, assets)
        folder = DU.find_or_create_folder(drive, DRIVE_ID, DRIVE_ID, key)
        for f in sorted(os.listdir(outdir)):
            if f.endswith(".png"):
                DU.upload_file(drive, folder, os.path.join(outdir, f))
        hashes[key] = h
        print(f"  {key}: rendered+uploaded {made} cards")

    state["sheet_mtime"] = mtime
    state["month_hashes"] = hashes
    state["window"] = window
    save_state(state)
    print("[done]")


if __name__ == "__main__":
    main()
