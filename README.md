# Golf sim data

Downloads every shot from a Uneekor Power U report and builds `index.html`, a retro dashboard (live at https://mplaza27.github.io/golf/) with a date picker and five tabs: Session, Progress, Bag, Course and Drills.

## New session
1. Make a dated folder (`MM-DD-YY`) containing a `link.md` with the report link.
2. From `golf/`, run `python3 -I scripts/download_shots.py`. It uses the latest dated folder (or pass folder names) and rebuilds the dashboard.
3. Open `index.html`, then commit and push to update the GitHub Pages site. Pick a metric to compare against the Tour, pick a club to focus every chart on it, and click any shot (a chart dot or a table row) to see its impact photo and swing frames.

Shots that are already downloaded are skipped. To rebuild the dashboard on its own, run `python3 -I scripts/build_dashboard.py`. `link.md` files are git-ignored because the report link contains an access key.

## Files
- `MM-DD-YY/<club>/<club>_<n>/`: one folder per shot (`n = 1` is the oldest) with the shot CSV, a ball-impact image and 24 top-view images.
- `MM-DD-YY/review.md` (optional): coach notes shown on that date's Session tab.
- `MM-DD-YY/session.json` (optional): `curated` (best shots only, so the dashboard shows a banner), `caveats` per club (e.g. `{"7i": "possible outlier"}`) and `nextSession`.
- `review.md`: the overall plan, shown on the Progress tab.
- `bag.json`: main bag (each `key` matches a club folder name) and the par-3 bag, which borrows yardages from the main-bag club with the same loft (`equiv`).
- `drills.json`: Drills tab content: practice-plan levels, drills, embedded YouTube video IDs and resource links. Swap a video by changing its ID.
- `courses.json`: hole yardages per tee. The Course tab picks a par-3-bag club and an aim offset for each hole. Stoneham Oaks yardages come from online scorecards that disagree, so check them against the real card.
- `scripts/download_shots.py`: `CLUB_NAMES` maps Uneekor club names to folder names. The wood, hybrid and 6-iron names are guesses, so check them after your first session with those clubs.
