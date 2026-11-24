import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://localhost:9222")
    page = [pg for c in b.contexts for pg in c.pages if "uneekor" in pg.url][0]
    hits = []
    page.on("response", lambda r: hits.append(r) if r.request.resource_type in ("xhr","fetch") else None)
    page.reload(); page.wait_for_load_state("networkidle")
    for r in hits:
        try: body = r.text()
        except Exception: body = ""
        print(r.status, r.url, "\n   ", body[:700].replace("\n"," "))
    print("CLUB BUTTONS:", page.eval_on_selector_all("button[aria-label]", "els=>els.map(e=>e.getAttribute('aria-label'))"))
