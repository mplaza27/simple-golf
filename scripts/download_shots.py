"""Download every shot's ALL export from a Uneekor Power U report.

Usage: python3 -I scripts/download_shots.py [MM-DD-YY ...]
With no args, uses the latest dated folder in golf/data/simulator/. Reads the report link from
data/simulator/<folder>/link.md and creates <folder>/<club>/<club>_<n>/ (n = 1 for the oldest shot).
Shots whose folder already has files are skipped.
"""
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

API = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"
GOLF_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = GOLF_DIR / "data" / "simulator"
# Uneekor club_name -> folder name (must match a "key" in bag.json to show up in the Bag tab).
# Confirmed from real exports: IRON7-9, WEDGE_*. The wood/hybrid/6-iron names are best guesses;
# an unmapped club is saved under its raw Uneekor name (e.g. "WOOD_7") so you can add it here.
CLUB_NAMES = {
    "DRIVER": "Dr", "WOOD3": "3W", "WOOD_3": "3W", "WOOD7": "7W", "WOOD_7": "7W",
    "HYBRID3": "3H", "HYBRID_3": "3H", "IRON6": "6i",
    "IRON7": "7i", "IRON8": "8i", "IRON9": "9i",
    "WEDGE_PITCHING": "PW", "WEDGE_LOB": "AW",
    "WEDGE_52": "51", "WEDGE_56": "56", "WEDGE_60": "60",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def safe_extract(data, dest):
    dest = dest.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for m in z.infolist():
            target = (dest / m.filename).resolve()
            if dest not in target.parents and target != dest:
                raise ValueError(f"unsafe path in zip: {m.filename}")
        z.extractall(dest)
        return len(z.infolist())


def download(report_url, out):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(report_url).query)
    rid, key = q["id"][0], q["key"][0]
    dist, speed = q.get("distance", ["yard"])[0], q.get("speed", ["mph"])[0]
    sessions = json.loads(get(f"{API}/{rid}/{key}"))
    # A report can contain several blocks for the same club (e.g. two separate 7-iron sets).
    # Pool them per club and number in time order, so shot numbers never collide.
    by_club = {}
    for s in sessions:
        by_club.setdefault(CLUB_NAMES.get(s["club_name"], s["club_name"]), []).extend(s["shots"])
    for club, pool in by_club.items():
        shots = sorted(pool, key=lambda x: int(x["client_shot_id"]))  # oldest first
        for n, shot in enumerate(shots, 1):
            dest = out / club / f"{club}_{n}"
            if dest.is_dir() and any(dest.iterdir()):
                print(f"{dest.relative_to(out)}  (already downloaded, skipped)")
                continue
            url = f"{API}/export/shotdata/{rid}/{key}/{shot['client_shot_id']}/{shot['id']}/{dist}/{speed}"
            dest.mkdir(parents=True, exist_ok=True)
            count = safe_extract(get(url), dest)
            print(f"{dest.relative_to(out)}  ({count} files)")


def folder_date(p):
    try:
        return datetime.strptime(p.name, "%m-%d-%y")
    except ValueError:
        return None


def read_link(folder):
    m = re.search(r"https://my\.uneekor\.com/\S+", (folder / "link.md").read_text())
    if not m:
        raise SystemExit(f"no Uneekor link found in {folder / 'link.md'}")
    return m.group(0)


if __name__ == "__main__":
    if sys.argv[1:]:
        folders = [DATA_DIR / a for a in sys.argv[1:]]
    else:
        dated = [p for p in DATA_DIR.iterdir() if p.is_dir() and folder_date(p)]
        if not dated:
            raise SystemExit(f"no MM-DD-YY folders in {DATA_DIR}")
        folders = [max(dated, key=folder_date)]
    for folder in folders:
        print(f"== {folder.name}")
        download(read_link(folder), folder)

    import importlib.util  # rebuild golf/index.html (works under python -I)
    spec = importlib.util.spec_from_file_location("build_dashboard", Path(__file__).with_name("build_dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build()
