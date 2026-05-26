import random
import time
import re
from playwright.sync_api import sync_playwright

from app.core.config import settings

# ── Playwright selectors ───────────────────────────────────────────────────────
# LinkedIn switched to hashed class names in 2025 — these change every deploy.
# All selectors below use stable HTML attributes instead of class names.
# If scraping breaks again, run find_selectors.py to rediscover them.
SELECTORS = {
    # Feed post container — LinkedIn now marks each feed item as role="listitem"
    # with a unique componentkey attribute. This is stable across deploys.
    "post_container": "div[role='listitem'][componentkey]",

    # Author display name — sits inside an anchor with /in/ profile URL
    # We extract it from the aria-label on the container or the anchor text
    "author_link": "a[href*='/in/']",

    # Post text — LinkedIn wraps post body in a span with dir="ltr"
    # Fallback to any div with data-test-id containing 'main-feed-activity'
    "post_text": "span[dir='ltr'], div[data-test-id*='main-feed-activity']",

    # Post URL — the timestamp anchor always links to /feed/update/
    "timestamp_link": "a[href*='/feed/update/'], a[href*='/posts/']",

    # Poll signal — polls have a specific role
    "poll_signal": "[data-test-id*='poll'], div[role='radiogroup']",

    # Article signal
    "article_signal": "div[data-test-id*='article'], a[href*='/pulse/']",

    # Login / authwall detection
    "login_signals": [
        "login",
        "authwall",
        "checkpoint",
        "uas/login",
    ],
}

NOISE_PATTERNS = [

    r"Feed post",

    r"Promoted",

    r"\bfollows\b",

    r"\bFollow\b",

    r"\d[\d,]* followers",

    r"Like\s+Comment\s+Repost\s+Send",

    r"React\s+Comment",

    r"Copy link",

    r"Open menu",

]

def _is_promoted(container) -> bool:
    try:
        text = container.inner_text().lower()
        return "promoted" in text
    except Exception:
        return False

def _clean_text(text: str) -> str:

    """

    Remove LinkedIn UI noise and normalize whitespace.

    """

    if not text:

        return ""

    cleaned = text

    for pattern in NOISE_PATTERNS:

        cleaned = re.sub(

            pattern,

            "",

            cleaned,

            flags=re.IGNORECASE

        )

    # Remove excessive whitespace/newlines

    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()

def _looks_like_post_body(text: str) -> bool:

    """

    Heuristics to decide whether a text block

    is likely to be the real post body.

    """

    if not text:

        return False

    text = text.strip()

    # Too short

    if len(text.split()) < 8:

        return False

    # Ignore obvious UI text

    blacklist = [

        "followers",

        "follow",

        "like",

        "comment",

        "repost",

        "send",

        "copy link",

        "open menu",

    ]

    lower = text.lower()

    if any(word in lower for word in blacklist):

        return False

    return True

class ScraperError(Exception):
    """Raised when the scraper cannot complete due to a non-recoverable error."""
    pass


class SessionExpiredError(ScraperError):
    """Raised when the LinkedIn session has expired and the user must log in again."""
    pass


def _is_session_expired(url: str) -> bool:
    return any(kw in url for kw in SELECTORS["login_signals"])


def _extract_post_url(container) -> str | None:
    """
    Pull the individual post URL from the timestamp anchor inside a container.
    Returns an absolute URL, or None if not found.
    """
    try:
        links = container.locator(SELECTORS["timestamp_link"]).all()
        for link in links:
            href = link.get_attribute("href") or ""
            if "/feed/update/" in href or "/posts/" in href:
                # Strip query params for a clean URL
                clean = href.split("?")[0]
                if clean.startswith("/"):
                    return "https://www.linkedin.com" + clean
                return clean
        return None
    except Exception:
        return None


def _extract_author_name(container) -> str:

    """

    Extract LinkedIn author/company name.

    """

    try:

        links = container.locator("a[href*='/in/'], a[href*='/company/']").all()

        for link in links:

            try:

                text = (link.inner_text() or "").strip()

                if not text:

                    continue

                text = text.split("\n")[0].strip()

                if 2 <= len(text) <= 80:

                    return text

            except Exception:

                continue

    except Exception:

        pass

    return ""


def _extract_author_url(container) -> str:
    """Return the author's profile URL, empty string if not found."""
    try:
        links = container.locator(SELECTORS["author_link"]).all()
        for link in links:
            href = link.get_attribute("href") or ""
            if "/in/" in href:
                clean = href.split("?")[0]
                if clean.startswith("/"):
                    return "https://www.linkedin.com" + clean
                return clean
        return ""
    except Exception:
        return ""


def _extract_post_text(container) -> str:

    """

    Extract only the meaningful LinkedIn post body.

    """

    candidates = []

    try:

        # Expand "see more" first

        see_more_buttons = container.locator(

            "button:has-text('see more')"

        )

        if see_more_buttons.count() > 0:

            try:

                see_more_buttons.first.click(timeout=1000)

                time.sleep(random.uniform(0.5, 1.2))

            except Exception:

                pass

        # Primary extraction strategy

        spans = container.locator("span[dir='ltr']").all()

        for span in spans:

            try:

                text = span.inner_text().strip()

                text = _clean_text(text)

                if _looks_like_post_body(text):

                    candidates.append(text)

            except Exception:

                continue

        # Return best candidate

        if candidates:

            return max(candidates, key=len)

    except Exception:

        pass

    return ""


def _detect_post_type(container) -> str:
    """Return 'article', 'poll', or 'text'."""
    try:
        if container.locator(SELECTORS["article_signal"]).count() > 0:
            return "article"
        if container.locator(SELECTORS["poll_signal"]).count() > 0:
            return "poll"
    except Exception:
        pass
    return "text"


def _word_count(text: str) -> int:
    return len(text.split())


def scrape_linkedin_feed(max_posts: int = None) -> list[dict]:
    """
    Open the LinkedIn feed using the saved browser session, scroll through it,
    and collect raw post data.

    Parameters
    ----------
    max_posts : int, optional
        Maximum number of posts to collect.

    Returns
    -------
    list[dict]
        Each dict contains:
        - post_url            : str
        - author_name         : str
        - author_linkedin_url : str
        - post_text           : str
        - post_type           : str  ('text', 'article', 'poll')
    """
    if max_posts is None:
        max_posts = settings.MAX_POSTS_TO_SCRAPE_PER_RUN

    collected: list[dict] = []
    seen_urls: set[str]   = set()

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
        user_data_dir=settings.PLAYWRIGHT_SESSION_DIR,
        headless=False,
        args=[
            "--start-maximized",
        ],
        viewport={"width": 1400, "height": 900},
    )
        page = browser.pages[0] if browser.pages else browser.new_page()

        try:
            # ── Navigate ───────────────────────────────────────────────────
            page.goto("https://www.linkedin.com/feed/", timeout=30_000)

            # Wait for feed to render — networkidle never fires on LinkedIn
            time.sleep(5)

            # ── Session check ──────────────────────────────────────────────
            if _is_session_expired(page.url):
                raise SessionExpiredError(
                    "LinkedIn redirected to a login or authwall page. "
                    "Please log in again by running the session capture flow."
                )

            # ── Scroll and collect ─────────────────────────────────────────
            max_scroll_attempts = 10
            scroll_attempt      = 0

            while len(collected) < max_posts and scroll_attempt < max_scroll_attempts:

                time.sleep(2)  # Let newly scrolled posts render

                containers = page.locator(SELECTORS["post_container"]).all()

                for container in containers:
                    if len(collected) >= max_posts:
                        break

                    post_url = _extract_post_url(container)
                    if not post_url:
                        continue

                    if post_url in seen_urls:
                        continue

                    post_text = _extract_post_text(container)

                    if _word_count(post_text) < settings.MIN_POST_WORD_COUNT:
                        continue

                    author_name = _extract_author_name(container)
                    author_url  = _extract_author_url(container)
                    post_type   = _detect_post_type(container)

                    seen_urls.add(post_url)
                    collected.append({
                        "post_url":            post_url,
                        "author_name":         author_name,
                        "author_linkedin_url": author_url,
                        "post_text":           post_text,
                        "post_type":           post_type,
                    })




                # Human-like scroll
                page.evaluate("window.scrollBy(0, 1200)")
                time.sleep(random.uniform(1.5, 3.0))
                scroll_attempt += 1

        except SessionExpiredError:
            raise

        except Exception as exc:
            print(
                f"[linkedin_scraper] Unexpected error after collecting "
                f"{len(collected)} posts: {exc}"
            )
            if not collected:
                raise ScraperError(
                    f"Scraper failed before collecting any posts: {exc}"
                ) from exc

        finally:
            browser.close()
    print('****collected: ')
    print(collected)

    return collected


if __name__ == "__main__":

    posts = scrape_linkedin_feed()

    print(f"Collected {len(posts)} posts")