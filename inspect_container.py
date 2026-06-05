"""
inspect_containers.py
─────────────────────
Dumps ALL anchor hrefs inside each container so we can find
exactly which URL pattern LinkedIn uses for posts missing /feed/update/
Run: python inspect_containers.py
"""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
from app.core.config import settings

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=settings.PLAYWRIGHT_SESSION_DIR,
        headless=False,
    )
    page = browser.new_page()
    page.goto("https://www.linkedin.com/feed/", timeout=30_000)
    time.sleep(6)

    for i in range(3):
        page.evaluate("window.scrollBy(0, 1200)")
        time.sleep(random.uniform(2, 3))

    containers = page.locator("div[role='listitem'][componentkey]").all()
    print(f"\nTotal containers: {len(containers)}\n")

    for i, container in enumerate(containers, 1):
        print(f"{'='*60}")
        print(f"Container {i}")
        print(f"{'='*60}")

        # Dump every unique href in this container
        hrefs = page.evaluate("""(el) => {
            const links = el.querySelectorAll('a[href]');
            const seen = new Set();
            const out = [];
            for (const a of links) {
                const h = (a.getAttribute('href') || '').split('?')[0];
                if (h && !seen.has(h)) {
                    seen.add(h);
                    out.push({
                        href: h,
                        text: (a.innerText || '').trim().slice(0, 40),
                        ariaLabel: (a.getAttribute('aria-label') || '').slice(0, 40)
                    });
                }
            }
            return out;
        }""", container.element_handle())

        for a in hrefs:
            print(f"  href: {a['href'][:90]}")
            if a['text']:
                print(f"        text='{a['text']}'")
            if a['ariaLabel']:
                print(f"        aria='{a['ariaLabel']}'")

        print()

    browser.close()