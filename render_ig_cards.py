#!/usr/bin/env python3
"""render_ig_cards.py — 全院+全医師のInstagramカレンダー画像を一括生成する。

月データ(dump_month_all) + 医師資産(写真/役職) を読み、HTMLを組んで
google-chrome headless で PNG 化。出力は <workdir>/out/。
Usage: render_ig_cards.py <workdir> <YYYY-MM>
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ig_calendar as IG  # noqa: E402
import shift_lib as SL  # noqa: E402

CHROME = "/usr/bin/google-chrome"
CLINIC_EN = {"銀座": ("GINZA", "ginza"), "新宿": ("SHINJUKU", "shinjuku"),
             "池袋": ("IKEBUKURO", "ikebukuro"), "大阪": ("OSAKA", "osaka"),
             "福岡": ("FUKUOKA", "fukuoka")}
LABEL_TO_HERO = {"銀座院": "ginza", "新宿院": "shinjuku", "池袋院": "ikebukuro",
                 "大阪院": "osaka", "福岡院": "fukuoka", "静脈科": "vein", "歯科": "dental"}
TITLE_HERO = [("銀座", "ginza"), ("新宿", "shinjuku"), ("池袋", "ikebukuro"),
              ("大阪", "osaka"), ("福岡", "fukuoka"), ("審美歯科", "dental"),
              ("歯科", "dental"), ("静脈", "vein")]


def render(workdir, html_name, out_png):
    html_path = os.path.join(workdir, html_name)
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--window-size=1080,1350", "--force-device-scale-factor=2",
        "--font-render-hinting=none", "--virtual-time-budget=7000",
        f"--screenshot={out_png}", f"file://{html_path}",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    return os.path.exists(out_png) and os.path.getsize(out_png) > 0


def main_clinic_hero(title, data):
    for jp, slug in TITLE_HERO:
        if jp in (title or ""):
            return slug
    if data:
        from collections import Counter
        top = Counter(data.values()).most_common(1)[0][0]
        return LABEL_TO_HERO.get(top, "ginza")
    return "ginza"


def main():
    workdir, ym = sys.argv[1], sys.argv[2]
    y, m = map(int, ym.split("-"))
    outdir = os.path.join(workdir, "out")
    os.makedirs(outdir, exist_ok=True)
    month = json.load(open(os.path.join(workdir, f"month_{y}_{m:02d}.json"), encoding="utf-8"))
    assets = json.load(open(os.path.join(workdir, "doctor_assets.json"), encoding="utf-8"))
    fam_to_slug = SL.DOCTOR_NAME_TO_SLUG

    made = []
    # --- clinic cards (5 main) ---
    for code, (en, hero) in CLINIC_EN.items():
        days = month["clinics"].get(code, {})
        if not days:
            continue
        html = IG.build_html(en, y, m, f"hero-{hero}.webp", days)
        hn = f"clinic_{hero}.html"
        open(os.path.join(workdir, hn), "w", encoding="utf-8").write(html)
        out = os.path.join(outdir, f"【{code}】{y}_{m}月.png")
        ok = render(workdir, hn, out)
        made.append((f"clinic:{en}", ok))
        print(f"  clinic {en:10s} {'OK' if ok else 'FAIL'}")

    # --- doctor cards (all with photo + shifts) ---
    for fam, data in month["doctors"].items():
        slug = fam_to_slug.get(fam)
        a = assets.get(slug) if slug else None
        if not a or not a.get("file"):
            print(f"  doctor {fam:10s} SKIP (no page/photo)")
            continue
        hero = main_clinic_hero(a.get("title", ""), data)
        html = IG.build_doctor_html(fam, y, m, f"hero-{hero}.webp", a["file"], data)
        hn = f"doctor_{slug}.html"
        open(os.path.join(workdir, hn), "w", encoding="utf-8").write(html)
        out = os.path.join(outdir, f"【{fam}】{y}_{m}月.png")
        ok = render(workdir, hn, out)
        made.append((f"doctor:{fam}", ok))
        print(f"  doctor {fam:10s} {'OK' if ok else 'FAIL'} (hero={hero})")

    ok_n = sum(1 for _, o in made if o)
    print(f"\nDONE {ok_n}/{len(made)} images -> {outdir}")


if __name__ == "__main__":
    main()
