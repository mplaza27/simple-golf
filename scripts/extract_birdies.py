"""Turn raw 18Birdies exports into a privacy-safe rounds file.

Usage: python3 -I scripts/extract_birdies.py
Reads every data/birdies/<MM-DD-YY>/*archive*.json (raw exports are git-ignored) and writes
data/birdies/rounds.json with ONLY the round-level fields listed in KEEP_STATS / the round dict below.
Everything else is dropped: account details (email, phone, birth year, user id), friends, feed,
subscription, and internal ids. Newer exports win when the same round appears twice.
The script refuses to write if the output looks like it contains contact details or a friend's name.
rounds.json keeps exact dates and stays local (git-ignored); build_dashboard.py publishes month only.
"""
import json
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

GOLF_DIR = Path(__file__).resolve().parent.parent
BIRDIES_DIR = GOLF_DIR / "data" / "birdies"
OUT = BIRDIES_DIR / "rounds.json"
TEES = BIRDIES_DIR / "tees.json"   # optional, local: {"tees": {"YYYY-MM-DD | course | n": "White"}}
# Dates are calendar days where you played (all courses so far are US Eastern). Time of day is never kept.
LOCAL_TZ = ZoneInfo("America/New_York")

# Allow-list of per-round stats to keep. Putting and strokes-gained are left out: the export
# never records putts, and strokes-gained is a constant placeholder (100).
KEEP_STATS = [
    "birdies", "pars", "bogeys", "doubleBogeyOrWorse", "eagles", "aces",
    "fairwayHoleCount", "fairwayMiddles", "fairwayLefts", "fairwayRights", "fairwayShorts", "fairwayLongs",
    "girHoleCount", "gir", "girLefts", "girRights", "girShorts", "girLongs", "girNoChances",
]


def load_exports():
    exports = sorted(BIRDIES_DIR.glob("*/*archive*.json"), key=lambda p: (p.parent.name, p.name))
    if not exports:
        raise SystemExit(f"no 18Birdies exports found under {BIRDIES_DIR}/<date>/")
    return exports


def sanitize(export_path):
    data = json.loads(export_path.read_text())["myData"]
    courses = {c["clubId"]: c["name"] for c in data.get("clubData", {}).get("playedClubs", [])}
    rounds = []
    for r in data.get("activityData", {}).get("rounds", []):
        holes = [int(x) for x in (r.get("holeStrokes") or [])]
        club = r.get("clubId") or {}
        club_id = club.get("id") if isinstance(club, dict) else club
        stats = r.get("stats") or {}
        hcp = r.get("roundHandicap")
        rounds.append({
            "key": r["id"],  # used only to de-duplicate across exports; removed before writing
            "date": datetime.fromtimestamp(r["timestamp"] / 1000, tz=LOCAL_TZ).strftime("%Y-%m-%d"),
            "course": courses.get(club_id, "Unknown course"),
            "holes": len(holes),
            "complete": bool(holes) and all(h > 0 for h in holes),  # some rounds were only partly entered
            "holeStrokes": holes,
            "strokes": r.get("strokes"),
            "toPar": r.get("score"),
            "roundHandicap": float(hcp) if hcp not in (None, "") else None,
            "stats": {k: stats[k] for k in KEEP_STATS if k in stats},
        })
    return data, rounds


def leak_check(text, raw):
    """Fail loudly if anything personal made it into the output."""
    problems = []
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        problems.append("an email address")
    if re.search(r"\+?\d[\d\s().-]{8,}\d", text.replace('"', " ")):
        # dates and stroke lists are short digit runs; a long run of digits looks like a phone number
        for m in re.finditer(r"\+?\d[\d\s().-]{8,}\d", text):
            if len(re.sub(r"\D", "", m.group())) >= 10:
                problems.append("a phone-like number")
                break
    acct = raw.get("accountData", {})
    for field in ("userId", "userName", "email", "mobileNumber"):
        v = acct.get(field)
        if v and str(v) in text:
            problems.append(f"account {field}")
    for fr in raw.get("friendData", {}).get("friends", []):
        if fr.get("name") and fr["name"] in text:
            problems.append("a friend's name")
            break
    return problems


def main():
    by_key, raws = {}, []
    for path in load_exports():  # oldest first, so newer exports overwrite
        raw, rounds = sanitize(path)
        raws.append(raw)
        for r in rounds:
            by_key[r["key"]] = r
    rounds = sorted(by_key.values(), key=lambda r: r["date"])
    tees = json.loads(TEES.read_text())["tees"] if TEES.exists() else {}
    seen = {}
    for r in rounds:  # rounds are in time order; n counts repeat rounds at the same course on the same day
        del r["key"]
        base = f"{r['date']} | {r['course']}"
        seen[base] = seen.get(base, 0) + 1
        r["tee"] = tees.get(f"{base} | {seen[base]}")
    missing = sum(r["tee"] is None for r in rounds)
    if tees and missing:
        print(f"note: {missing} round(s) have no tee in {TEES.name}")
    out = {"source": "18Birdies export (sanitized by scripts/extract_birdies.py)", "rounds": rounds}
    text = json.dumps(out, indent=1, ensure_ascii=False)
    problems = sorted({p for raw in raws for p in leak_check(text, raw)})
    if problems:
        sys.exit("refusing to write rounds.json: output contains " + ", ".join(problems))
    OUT.write_text(text + "\n")
    done = sum(r["complete"] for r in rounds)
    print(f"{OUT.relative_to(GOLF_DIR)}: {len(rounds)} rounds ({done} complete, {len(rounds) - done} partly entered), "
          f"{len({r['course'] for r in rounds})} courses")


if __name__ == "__main__":
    main()
