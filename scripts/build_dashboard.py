"""Build golf/index.html (the GitHub Pages site) from every data/MM-DD-YY session folder plus bag.json.

Usage: python3 -I scripts/build_dashboard.py
Layout: data/simulator/MM-DD-YY/ (shots, session.json, review.md), config/ (bag, courses),
coaching/ (plan.md shown on the Progress tab, drills.json for the Drills tab).
"""
import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path

GOLF_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "dashboard_template.html"
OUT = GOLF_DIR / "index.html"
DATA_DIR = GOLF_DIR / "data" / "simulator"
CONFIG_DIR = GOLF_DIR / "config"
COACHING_DIR = GOLF_DIR / "coaching"
FIELDS = {
    "Carry": "carry", "Total": "total", "Side Dist": "side", "Smash Factor": "smash",
    "Club Speed": "clubSpeed", "Ball Speed": "ballSpeed", "Back Spin": "backSpin",
    "Side Spin": "sideSpin", "Launch Angle": "launch", "Side Angle": "sideAngle",
    "Decent Angle": "descent", "Apex": "apex", "Flight Time": "flightTime",
    "Face Angle": "face", "Club Path": "path",
}


def num(v):
    """'7 L' -> -7, '1320 R' -> 1320, '-9.2' -> -9.2, '' -> None."""
    v = (v or "").strip()
    if not v:
        return None
    parts = v.split()
    try:
        x = float(parts[0])
    except ValueError:
        return None
    if len(parts) > 1 and parts[1] == "L" and x > 0:
        x = -x
    return x


def folder_date(p):
    try:
        return datetime.strptime(p.name, "%m-%d-%y")
    except ValueError:
        return None


def md_to_html(text):
    """Tiny Markdown subset: #/##/### headings, - bullets, **bold**, `code`, paragraphs."""
    out, in_list = [], False

    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        return re.sub(r"`(.+?)`", r"<code>\1</code>", s)

    for line in text.splitlines():
        line = line.rstrip()
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        bullet = re.match(r"^\s*[-*]\s+(.*)", line)
        if in_list and not bullet:
            out.append("</ul>")
            in_list = False
        if m:
            level = min(len(m.group(1)) + 2, 5)
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
        elif bullet:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(bullet.group(1))}</li>")
        elif line:
            out.append(f"<p>{inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def load_session(folder):
    meta_path = folder / "session.json"
    excluded = set(json.loads(meta_path.read_text()).get("exclude", [])) if meta_path.exists() else set()
    clubs = {}
    for club_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        shots = []
        for shot_dir in club_dir.iterdir():
            m = re.match(rf"^{re.escape(club_dir.name)}_(\d+)$", shot_dir.name)
            csvs = list(shot_dir.glob("*.csv")) if m and shot_dir.is_dir() else []
            if not csvs or shot_dir.name in excluded:  # session.json "exclude": ["7i_25", ...] keeps files but drops the shot
                continue
            with open(csvs[0], newline="") as f:
                row = next(csv.DictReader(f), None)
            if not row:
                continue
            shot = {"n": int(m.group(1)), "type": row.get("Type", "")}
            shot.update({k: num(row.get(src)) for src, k in FIELDS.items()})
            rel = lambda p: p.relative_to(GOLF_DIR).as_posix()  # index.html lives in GOLF_DIR
            impact = sorted(shot_dir.glob("*_ballimpact.jpg"))
            shot["img"] = {
                "impact": rel(impact[0]) if impact else None,
                "frames": [rel(p) for p in sorted(shot_dir.glob("*_topview*.jpg"))],
            }
            shots.append(shot)
        if shots:
            clubs[club_dir.name] = sorted(shots, key=lambda s: s["n"])
    review = folder / "review.md"
    meta_file = folder / "session.json"
    return {
        "meta": json.loads(meta_file.read_text()) if meta_file.exists() else {},
        "month": folder_date(folder).strftime("%Y-%m"),  # the site shows month only
        "clubs": clubs,
        "review": md_to_html(review.read_text()) if review.exists() else "",
    }


ROUNDS_FILE = GOLF_DIR / "data" / "birdies" / "rounds.json"
ROUND_FIELDS = ["course", "tee", "holes", "complete", "holeStrokes", "strokes", "toPar", "roundHandicap", "stats"]


def public_rounds():
    """18Birdies rounds for the site: month only (no day, no time). The local rounds.json keeps full dates."""
    if not ROUNDS_FILE.exists():
        return []
    rounds = sorted(json.loads(ROUNDS_FILE.read_text())["rounds"], key=lambda r: r["date"])
    # seq keeps the true order (1 = oldest), even for several rounds in the same month
    out = [{"seq": i, "month": r["date"][:7], **{k: r[k] for k in ROUND_FIELDS if k in r}} for i, r in enumerate(rounds, 1)]
    for r in out:  # guard: nothing day-level may reach the public page
        assert re.fullmatch(r"\d{4}-\d{2}", r["month"]) and "date" not in r, r
    return out


def build():
    folders = sorted((p for p in DATA_DIR.iterdir() if p.is_dir() and folder_date(p)), key=folder_date) if DATA_DIR.exists() else []
    sessions = [s for s in (load_session(f) for f in folders) if s["clubs"]]  # folders are sorted by date
    for i, s in enumerate(sessions, 1):
        s["seq"] = i
    bag = json.loads((CONFIG_DIR / "bag.json").read_text())
    courses_file = CONFIG_DIR / "courses.json"
    courses = json.loads(courses_file.read_text())["courses"] if courses_file.exists() else []
    drills_file = COACHING_DIR / "drills.json"
    drills = json.loads(drills_file.read_text()) if drills_file.exists() else {}
    overall = COACHING_DIR / "plan.md"
    analysis = COACHING_DIR / "analysis.md"   # notes for the "All sessions" view
    data = {
        "sessions": sessions,
        "bag": bag,
        "courses": courses,
        "rounds": public_rounds(),
        "drills": drills,
        "allReview": md_to_html(analysis.read_text()) if analysis.exists() else "",
        "overallReview": md_to_html(overall.read_text()) if overall.exists() else "",
        "built": datetime.now().strftime("%Y-%m"),  # month only, like everything else on the site
    }
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    OUT.write_text(TEMPLATE.read_text().replace("__DATA__", payload))
    shots = sum(len(v) for s in sessions for v in s["clubs"].values())
    print(f"index.html: {len(sessions)} session(s), {shots} shots")


if __name__ == "__main__":
    build()
