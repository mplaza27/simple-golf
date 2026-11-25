"""One-off exploration script used to reverse-engineer the Uneekor report page (needs playwright + Chrome on :9222). Not part of the pipeline."""
import sys
from playwright.sync_api import sync_playwright
out = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://localhost:9222")
    page = [pg for c in b.contexts for pg in c.pages if "uneekor" in pg.url][0]
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"{out}/page.png", full_page=True)
    print(page.title(), page.url)
    print(page.inner_text("body")[:4000])
    open(f"{out}/page.html","w").write(page.content())
