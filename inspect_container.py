"""
inspect_containers.py v8
Find the real post wrapper among the 151 componentkey divs.
Run: python inspect_containers.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
from app.core.config import settings
from app.automation.linkedin_scraper import _scroll_feed, _wait_for_posts

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=settings.PLAYWRIGHT_SESSION_DIR,
        headless=False,
    )
    page = browser.new_page()
    page.goto("https://www.linkedin.com/feed/", timeout=60_000, wait_until="domcontentloaded")
    _wait_for_posts(page, min_containers=5)
    for _ in range(4):
        _scroll_feed(page, 800)
        time.sleep(4)

    print("\n→ Scanning 151 componentkey divs for post URLs...\n")

    result = page.evaluate("""() => {
        const all = document.querySelectorAll(
            '#workspace div[componentkey]:not([role="listitem"])'
        );
        const out = [];
        for (const el of all) {
            // Only interested in elements that have a post URL directly inside
            const postLinks = [...el.querySelectorAll(
                'a[href*="/feed/update/"], a[href*="/posts/"]'
            )].filter(a => {
                const h = a.getAttribute('href') || '';
                return !h.includes('/company/') &&
                       !h.includes('/showcase/') &&
                       !h.endsWith('/feed/') &&
                       h !== 'https://www.linkedin.com/feed';
            });

            if (postLinks.length === 0) continue;

            // Make sure this element itself DIRECTLY contains the link
            // (not just a deeply nested ancestor picking up children's links)
            const directLink = postLinks[0];
            const href = (directLink.getAttribute('href') || '').split('?')[0];
            const linkText = (directLink.innerText || '').trim().slice(0, 60);
            const textContent = (el.innerText || '').trim().slice(0, 100)
                .replace(/\\n/g, ' ');
            const ck = (el.getAttribute('componentkey') || '').slice(0, 60);
            const tag = el.tagName.toLowerCase();
            const role = el.getAttribute('role') || '';
            const childCount = el.children.length;

            // Check if listitem children exist inside
            const hasListitems = el.querySelector("[role='listitem']") !== null;

            out.push({
                tag, role, ck, href, linkText,
                textContent, childCount, hasListitems,
                classList: [...el.classList].slice(0, 3).join(' '),
            });
        }
        return out.slice(0, 20);
    }""")

    print(f"  Found {len(result)} elements with post URLs\n")

    for i, r in enumerate(result, 1):
        print(f"── Element {i}")
        print(f"   tag          : <{r['tag']} role='{r['role']}'>")
        print(f"   componentkey : {r['ck']}")
        print(f"   post href    : {r['href']}")
        print(f"   link text    : {r['linkText']}")
        print(f"   text preview : {r['textContent']}")
        print(f"   children     : {r['childCount']} | has listitems: {r['hasListitems']}")
        print(f"   classes      : {r['classList']}")
        print()

    browser.close()