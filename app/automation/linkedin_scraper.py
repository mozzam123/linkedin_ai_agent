import random
import time

from playwright.sync_api import sync_playwright

from app.core.config import settings

# ── Playwright selectors ───────────────────────────────────────────────────────
# All selectors live here so they are easy to update when LinkedIn changes its DOM.
SELECTORS = {
    # Feed post container — each post on the home feed lives inside one of these
    "post_container":   ".feed-shared-update-v2",

    # Author display name inside a post container
    "author_name":      ".update-components-actor__title .visually-hidden",

    # Author profile link inside a post container
    "author_link":      ".update-components-actor__meta-link",

    # The body text of the post
    "post_text":        ".feed-shared-update-v2__description, "
                        ".update-components-text",

    # Timestamp link — its href is the individual post URL
    "timestamp_link":   ".update-components-actor__sub-description a, "
                        "a.app-aware-link[href*='/feed/update/']",

    # Signals that help detect post type
    "article_signal":   ".feed-shared-article",
    "poll_signal":      ".feed-shared-poll",

    # Login / authwall detection — if any of these appear after navigation
    # the session has expired
    "login_signals": [
        "login",
        "authwall",
        "checkpoint",
        "uas/login",
    ],
}


class ScraperError(Exception):
    """Raised when the scraper cannot complete due to a non-recoverable error."""
    pass


class SessionExpiredError(ScraperError):
    """Raised when the LinkedIn session has expired and the user must log in again."""
    pass


def _is_session_expired(url: str) -> bool:
    return any(kw in url for kw in SELECTORS["login_signals"])


def _extract_post_url(container, page_url_base: str) -> str | None:
    """
    Pull the individual post URL from the timestamp anchor inside a container.
    Returns an absolute URL, or None if not found.
    """
    try:
        link = container.locator(SELECTORS["timestamp_link"]).first
        href = link.get_attribute("href")
        if not href:
            return None
        # Convert relative paths to absolute
        if href.startswith("/"):
            return "https://www.linkedin.com" + href
        return href
    except Exception:
        return None


def _extract_author_name(container) -> str:
    """Return the author's display name, empty string if not found."""
    try:
        el = container.locator(SELECTORS["author_name"]).first
        return (el.inner_text() or "").strip()
    except Exception:
        return ""


def _extract_author_url(container) -> str:
    """Return the author's profile URL, empty string if not found."""
    try:
        el = container.locator(SELECTORS["author_link"]).first
        href = el.get_attribute("href") or ""
        if href.startswith("/"):
            return "https://www.linkedin.com" + href
        return href
    except Exception:
        return ""


def _extract_post_text(container) -> str:
    """Return the visible text body of the post, stripped of extra whitespace."""
    try:
        el = container.locator(SELECTORS["post_text"]).first
        raw = el.inner_text() or ""
        # Collapse runs of whitespace / newlines into single spaces
        return " ".join(raw.split())
    except Exception:
        return ""


def _detect_post_type(container) -> str:
    """
    Return 'article', 'poll', or 'text' based on DOM signals inside the container.
    """
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

    Uses the single hardcoded session folder (settings.PLAYWRIGHT_SESSION_DIR).
    No session_dir parameter — this project uses a single account.

    Parameters
    ----------
    max_posts : int, optional
        Maximum number of posts to collect. Defaults to
        settings.MAX_POSTS_TO_SCRAPE_PER_RUN if not provided.

    Returns
    -------
    list[dict]
        Each dict contains:
        - post_url         : str  — absolute URL to the individual post
        - author_name      : str  — display name of the post author
        - author_linkedin_url : str — URL to the author's profile
        - post_text        : str  — full visible text of the post
        - post_type        : str  — one of 'text', 'article', 'poll'

    Raises
    ------
    SessionExpiredError
        If LinkedIn redirects to a login or authwall page after navigation.
    ScraperError
        If a non-recoverable error occurs during scraping.
    """
    if max_posts is None:
        max_posts = settings.MAX_POSTS_TO_SCRAPE_PER_RUN

    collected:  list[dict] = []
    seen_urls:  set[str]   = set()   # deduplication within this single run

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=settings.PLAYWRIGHT_SESSION_DIR,
            headless=False,
        )
        page = browser.new_page()

        try:
            # ── Navigate to feed ───────────────────────────────────────────
            page.goto("https://www.linkedin.com/feed/", timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=20_000)

            # ── Session expiry check ───────────────────────────────────────
            if _is_session_expired(page.url):
                raise SessionExpiredError(
                    "LinkedIn redirected to a login or authwall page. "
                    "Please log in again by running the session capture flow."
                )

            # ── Scroll and collect ─────────────────────────────────────────
            max_scroll_attempts = 8
            scroll_attempt      = 0

            while len(collected) < max_posts and scroll_attempt < max_scroll_attempts:

                # Give the feed a moment to render newly loaded posts
                page.wait_for_load_state("domcontentloaded")

                containers = page.locator(SELECTORS["post_container"]).all()

                for container in containers:
                    if len(collected) >= max_posts:
                        break

                    post_url = _extract_post_url(container, page.url)

                    # Skip if we couldn't find the URL
                    if not post_url:
                        continue

                    # Skip duplicates within this run
                    if post_url in seen_urls:
                        continue

                    post_text = _extract_post_text(container)

                    # Skip posts that are too short to comment meaningfully on
                    if _word_count(post_text) < settings.MIN_POST_WORD_COUNT:
                        continue

                    author_name = _extract_author_name(container)
                    author_url  = _extract_author_url(container)
                    post_type   = _detect_post_type(container)

                    seen_urls.add(post_url)
                    collected.append({
                        "post_url":           post_url,
                        "author_name":        author_name,
                        "author_linkedin_url": author_url,
                        "post_text":          post_text,
                        "post_type":          post_type,
                    })

                # Scroll down to load more posts
                page.evaluate("window.scrollBy(0, 1200)")

                # Random human-like pause between scrolls (1.5 – 3 seconds)
                time.sleep(random.uniform(1.5, 3.0))

                scroll_attempt += 1

        except SessionExpiredError:
            # Re-raise without wrapping so callers can handle specifically
            raise

        except Exception as exc:
            # Non-recoverable error: return whatever was collected so far
            # so partial results are not lost, but also surface the error
            # message for logging.
            print(
                f"[linkedin_scraper] Unexpected error after collecting "
                f"{len(collected)} posts: {exc}"
            )
            if not collected:
                raise ScraperError(
                    f"Scraper failed before collecting any posts: {exc}"
                ) from exc
            # Partial results — caller decides what to do with them

        finally:
            browser.close()

    return collected