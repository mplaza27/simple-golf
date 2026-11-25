# Simple Golf

Downloads every shot from a Uneekor Power U report and builds `index.html`, a green-retro dashboard (live at https://mplaza27.github.io/simple-golf/) with a session picker and five tabs: Session, Rounds (18Birdies), Progress, Bag and Drills.

## Layout
```
index.html               the site (generated; GitHub Pages serves it from the root)
config/
  bag.json               your handicap, main bag and par-3 bag (each club `key` = shot folder name)
  courses.json           scorecards (Stoneham Oaks, Killian Greens, Redland G&CC); `birdiesName` links them to rounds
coaching/
  plan.md                overall plan, shown on the Progress tab
  drills.json            Drills tab: practice plan, drills, YouTube video IDs, resources
data/
  simulator/MM-DD-YY/    one Uneekor session
    <club>/<club>_<n>/   one shot (n = 1 is the oldest): CSV, impact photo, 24 top-view frames
    link.md              report link (git-ignored: it contains an access key)
    session.json         optional: curated, per-club caveats, nextSession
    review.md            optional: coach notes for that session
  birdies/MM-DD-YY/      raw 18Birdies exports (git-ignored: they hold your email, phone and friends)
  birdies/rounds.json    sanitized rounds with exact dates (git-ignored; the site only gets the month)
  birdies/tees.json      tee played per round, keyed by date (git-ignored)
scripts/
  download_shots.py      download a session and rebuild the site
  build_dashboard.py     rebuild index.html from data/ + config/ + coaching/
  extract_birdies.py     raw 18Birdies export → data/birdies/rounds.json (allow-listed fields only)
  dashboard_template.html
  dev/                   one-off scripts used to reverse-engineer the Uneekor page
```

## New session
1. Make `data/simulator/MM-DD-YY/link.md` containing the report link. Sessions show up as Session 1, 2, 3… in date order.
2. From `golf/`, run `python3 -I scripts/download_shots.py`. It uses the latest folder in `data/simulator/` (or pass folder names, e.g. `11-24-26`) and rebuilds the site. Shots already downloaded are skipped.
3. If you removed mishits in Uneekor, add a `session.json` with `"curated": true`.
4. Commit and push to update the GitHub Pages site.

To rebuild the site on its own: `python3 -I scripts/build_dashboard.py`.

## New 18Birdies export
Save it as `data/birdies/MM-DD-YY/18Birdies_archive.json`, then run `python3 -I scripts/extract_birdies.py`. Only round data is kept (date, course, per-hole strokes, handicap, fairway/green stats); the script refuses to write if anything that looks like an email, phone number or friend's name gets through. `rounds.json` stays on your machine with exact dates; `build_dashboard.py` publishes each round's month only (rounds keep their order via `seq`).

To record tees, add entries to `data/birdies/tees.json` (`"YYYY-MM-DD | course | n": "White"`, n = 1 unless you played the course twice that day) and rerun the extract. Hole-by-hole analysis needs the course in `config/courses.json` with that tee's yardages.

## Notes
- `CLUB_NAMES` in `scripts/download_shots.py` maps Uneekor club names to folder names. The wood, hybrid and 6-iron names are guesses; check them after your first session with those clubs.
- Benchmarks live in `scripts/dashboard_template.html` (`BENCH`, `AMATEUR`): TrackMan Tour averages, GolfLaunchLab amateur speeds (handicap levels for driver and 7-iron only), Shot Scope handicap distances. Missing numbers are left blank, not estimated.
