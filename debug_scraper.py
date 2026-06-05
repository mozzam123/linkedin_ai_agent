import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
from app.core.config import settings
from app.automation.linkedin_scraper import (
    _is_job_update, _extract_post_url, _extract_author_name,
    _extract_author_url, _extract_post_text, _get_all_hrefs
)

print("\n" + "="*60)
print("  Debug Scraper v3")
print("="*60)

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=settings.PLAYWRIGHT_SESSION_DIR,
        headless=False,
    )
    page = browser.new_page()
    page.goto("https://www.linkedin.com/feed/", timeout=30_000)
    time.sleep(6)

    for i in range(4):
        page.evaluate("window.scrollBy(0, 1200)")
        time.sleep(random.uniform(2, 3))

    containers = page.locator("div[role='listitem'][componentkey]").all()
    print(f"\n  Total containers: {len(containers)}")

    real, skipped_job, skipped_no_url, skipped_short = 0, 0, 0, 0

    for i, c in enumerate(containers, 1):
        is_job = _is_job_update(c, page)
        url    = _extract_post_url(c, page)
        text   = _extract_post_text(c)
        wc     = len(text.split())

        if is_job:
            skipped_job += 1
            print(f"\n── Container {i} — SKIP (job update)")
            continue

        if not url:
            skipped_no_url += 1
            print(f"\n── Container {i} — SKIP (no post url) | {wc} words | {text[:60].replace(chr(10),' ')}")
            continue

        if wc < 20:
            skipped_short += 1
            print(f"\n── Container {i} — SKIP (too short: {wc} words)")
            continue

        real += 1
        author  = _extract_author_name(c)
        profile = _extract_author_url(c)
        print(f"\n── Container {i} — ✓ REAL POST")
        print(f"   url     : {url[:80]}")
        print(f"   author  : {author}")
        print(f"   profile : {profile[:70]}")
        print(f"   words   : {wc}")
        print(f"   preview : {text[:120].replace(chr(10),' ')}")

    print(f"\n{'='*60}")
    print(f"  ✓ Real posts  : {real}")
    print(f"  ✗ Job updates : {skipped_job}")
    print(f"  ✗ No URL      : {skipped_no_url}")
    print(f"  ✗ Too short   : {skipped_short}")
    print(f"{'='*60}\n")
    browser.close()