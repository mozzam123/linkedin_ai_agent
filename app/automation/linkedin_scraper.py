import random
import time

from playwright.sync_api import sync_playwright
from app.core.config import settings

SELECTORS = {
    "post_container":     "div[role='listitem'][componentkey]",
    "post_text_primary":  "span[data-testid*='expan']",
    "post_text_fallback": "p",
    "author_link":        "a[href*='/in/']",
    "timestamp_links":    "a[href*='/feed/update/'], a[href*='/posts/']",
    "login_signals":      ["login", "authwall", "checkpoint", "uas/login"],
    # The scrollable feed container — confirmed from DOM inspection
    "feed_scroll_container": "#workspace",
}

JOB_UPDATE_TEXTS = [
    "starting a new position",
    "started a new position",
    "new position",
    "promoted to",
]

COMPANY_URL_PATTERNS = ["/company/", "/showcase/", "/school/"]


class ScraperError(Exception):
    pass


class SessionExpiredError(ScraperError):
    pass


def _is_session_expired(url: str) -> bool:
    return any(kw in url for kw in SELECTORS["login_signals"])


def _is_post_url(href: str) -> bool:
    if not href:
        return False
    is_feed_update = "/feed/update/" in href
    is_posts_page  = "/posts/" in href
    if not (is_feed_update or is_posts_page):
        return False
    if any(p in href for p in COMPANY_URL_PATTERNS):
        return False
    if href.rstrip("/") in (
        "https://www.linkedin.com/feed",
        "https://www.linkedin.com/feed/",
    ):
        return False
    return True


def _get_all_hrefs(container, page) -> list[str]:
    try:
        return page.evaluate("""(el) => {
            const links = el.querySelectorAll('a[href]');
            const seen  = new Set();
            for (const a of links) {
                seen.add((a.getAttribute('href') || '').split('?')[0]);
            }
            return [...seen];
        }""", container.element_handle())
    except Exception:
        return []


def _scroll_feed(page, amount: int = 800) -> None:
    """
    Scroll the LinkedIn feed container directly.
    LinkedIn uses a scrollable <main id='workspace'> element —
    window.scrollBy() has no effect on this layout.
    Falls back to window scroll if the element is not found.
    """
    scrolled = page.evaluate(f"""() => {{
        const el = document.querySelector('{SELECTORS["feed_scroll_container"]}');
        if (el) {{
            el.scrollBy(0, {amount});
            return true;
        }}
        window.scrollBy(0, {amount});
        return false;
    }}""")
    if not scrolled:
        print("[scraper] Warning: feed scroll container not found, using window scroll")


def _wait_for_posts(page, min_containers: int = 5, max_wait: int = 20) -> None:
    """Wait until at least min_containers post shells are in the DOM."""
    for _ in range(max_wait):
        n = page.locator(SELECTORS["post_container"]).count()
        if n >= min_containers:
            time.sleep(3)  # Extra wait for inner content to hydrate
            return
        time.sleep(1)


def _extract_post_url(container, page) -> str | None:
    try:
        hrefs = _get_all_hrefs(container, page)
        for href in hrefs:
            if _is_post_url(href):
                if href.startswith("/"):
                    return "https://www.linkedin.com" + href
                return href
    except Exception:
        pass
    return None


def _is_job_update(container, page) -> bool:
    try:
        links = container.locator(SELECTORS["timestamp_links"]).all()
        for link in links:
            text = (link.inner_text() or "").strip().lower()
            if any(phrase in text for phrase in JOB_UPDATE_TEXTS):
                return True
        hrefs           = _get_all_hrefs(container, page)
        has_post_url    = any(_is_post_url(h) for h in hrefs)
        has_company_url = any(
            any(p in h for p in COMPANY_URL_PATTERNS) and "/posts/" in h
            for h in hrefs
        )
        if has_company_url and not has_post_url:
            return True
    except Exception:
        pass
    return False


def _extract_author_name(container) -> str:
    try:
        links = container.locator(SELECTORS["author_link"]).all()
        for link in links:
            aria = (link.get_attribute("aria-label") or "").strip()
            if aria:
                return aria.split(",")[0].strip()
            text = (link.inner_text() or "").strip().split("\n")[0].strip()
            if text and len(text) < 80:
                return text
    except Exception:
        pass
    try:
        aria = container.get_attribute("aria-label") or ""
        if aria:
            return aria.split(",")[0].strip()
    except Exception:
        pass
    return ""


def _extract_author_url(container) -> str:
    try:
        links = container.locator(SELECTORS["author_link"]).all()
        for link in links:
            href = link.get_attribute("href") or ""
            if "/in/" in href:
                clean = href.split("?")[0]
                if clean.startswith("/"):
                    return "https://www.linkedin.com" + clean
                return clean
    except Exception:
        pass
    return ""


def _extract_post_text(container) -> str:
    try:
        spans = container.locator(SELECTORS["post_text_primary"]).all()
        if spans:
            texts = [(s.inner_text() or "").strip() for s in spans]
            texts = [t for t in texts if t]
            if texts:
                return " ".join(max(texts, key=len).split())
    except Exception:
        pass
    try:
        paras = container.locator(SELECTORS["post_text_fallback"]).all()
        if paras:
            texts = [
                (p.inner_text() or "").strip()
                for p in paras
                if len((p.inner_text() or "").strip()) > 20
            ]
            if texts:
                return " ".join(max(texts, key=len).split())
    except Exception:
        pass
    return ""


def _word_count(text: str) -> int:
    return len(text.split())


def scrape_linkedin_feed(max_posts: int = None) -> list[dict]:
    """
    Scrape LinkedIn feed. Scrolls the #workspace container directly
    since LinkedIn's feed does not scroll via window.scrollBy.
    """
    if max_posts is None:
        max_posts = settings.MAX_POSTS_TO_SCRAPE_PER_RUN

    collected: list[dict] = []
    seen_urls: set[str]   = set()

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=settings.PLAYWRIGHT_SESSION_DIR,
            headless=False,
        )
        page = browser.new_page()

        try:
            page.goto(
                "https://www.linkedin.com/feed/",
                timeout=60_000,
                wait_until="domcontentloaded",
            )

            if _is_session_expired(page.url):
                raise SessionExpiredError(
                    "LinkedIn redirected to login. Run session capture flow."
                )

            _wait_for_posts(page, min_containers=5)

            max_scroll_attempts = 20
            scroll_attempt      = 0
            prev_count          = 0

            while len(collected) < max_posts and scroll_attempt < max_scroll_attempts:

                containers = page.locator(SELECTORS["post_container"]).all()

                for container in containers:
                    if len(collected) >= max_posts:
                        break

                    if _is_job_update(container, page):
                        continue

                    post_url = _extract_post_url(container, page)
                    if not post_url or post_url in seen_urls:
                        continue

                    post_text = _extract_post_text(container)
                    if _word_count(post_text) < settings.MIN_POST_WORD_COUNT:
                        continue

                    author_name = _extract_author_name(container)
                    author_url  = _extract_author_url(container)

                    seen_urls.add(post_url)
                    collected.append({
                        "post_url":            post_url,
                        "author_name":         author_name,
                        "author_linkedin_url": author_url,
                        "post_text":           post_text,
                        "post_type":           "text",
                    })

                # Scroll the feed container, not the window
                _scroll_feed(page, amount=800)
                time.sleep(random.uniform(3.5, 5.0))

                # Detect if feed stopped loading new posts
                new_count = page.locator(SELECTORS["post_container"]).count()
                if new_count == prev_count:
                    scroll_attempt += 1
                else:
                    scroll_attempt = 0  # Reset if new posts appeared
                prev_count = new_count

        except SessionExpiredError:
            raise

        except Exception as exc:
            print(f"[linkedin_scraper] Error after {len(collected)} posts: {exc}")
            if not collected:
                raise ScraperError(f"Scraper failed: {exc}") from exc

        finally:
            browser.close()

    return collected