import random
import time

from playwright.sync_api import sync_playwright
from app.core.config import settings

# ── Selectors ──────────────────────────────────────────────────────────────────
SELECTORS = {
    "post_container":     "div[role='listitem'][componentkey]",
    "post_text_primary":  "span[data-testid*='expan']",
    "post_text_fallback": "p",
    "author_link":        "a[href*='/in/']",
    "timestamp_link":     "a[href*='/feed/update/']",
    "login_signals":      ["login", "authwall", "checkpoint", "uas/login"],
}

# Text patterns that indicate a job update card — not an original post
JOB_UPDATE_TEXTS = [
    "starting a new position",
    "started a new position",
    "new position",
    "promoted to",
    "joined",
]


class ScraperError(Exception):
    pass


class SessionExpiredError(ScraperError):
    pass


def _is_session_expired(url: str) -> bool:
    return any(kw in url for kw in SELECTORS["login_signals"])


def _get_all_hrefs(container, page) -> list[str]:
    """Return all unique hrefs inside a container."""
    try:
        return page.evaluate("""(el) => {
            const links = el.querySelectorAll('a[href]');
            const seen = new Set();
            for (const a of links) {
                seen.add((a.getAttribute('href') || '').split('?')[0]);
            }
            return [...seen];
        }""", container.element_handle())
    except Exception:
        return []


def _extract_post_url(container, page) -> str | None:
    """
    Return the /feed/update/ URL if present.
    Explicitly excludes /feed/ alone (reaction bar link).
    """
    try:
        hrefs = _get_all_hrefs(container, page)
        for href in hrefs:
            if "/feed/update/" in href:
                clean = href.split("?")[0]
                if clean.startswith("/"):
                    return "https://www.linkedin.com" + clean
                return clean
    except Exception:
        pass
    return None


def _is_job_update(container, page) -> bool:
    """
    Detect job update cards using two signals:
    1. Timestamp link text contains job-update phrases
    2. No /feed/update/ URL exists AND has a /company/ link
    """
    try:
        # Signal 1 — check timestamp anchor text
        links = container.locator(SELECTORS["timestamp_link"]).all()
        for link in links:
            text = (link.inner_text() or "").strip().lower()
            if any(phrase in text for phrase in JOB_UPDATE_TEXTS):
                return True

        # Signal 2 — has company link but no post URL
        hrefs = _get_all_hrefs(container, page)
        has_post_url    = any("/feed/update/" in h for h in hrefs)
        has_company_url = any("/company/" in h and "/posts/" in h for h in hrefs)

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
            texts = []
            for span in spans:
                try:
                    t = (span.inner_text() or "").strip()
                    if t:
                        texts.append(t)
                except Exception:
                    continue
            if texts:
                return " ".join(max(texts, key=len).split())
    except Exception:
        pass

    try:
        paras = container.locator(SELECTORS["post_text_fallback"]).all()
        if paras:
            texts = []
            for p in paras:
                try:
                    t = (p.inner_text() or "").strip()
                    if t and len(t) > 20:
                        texts.append(t)
                except Exception:
                    continue
            if texts:
                return " ".join(max(texts, key=len).split())
    except Exception:
        pass
    return ""


def _word_count(text: str) -> int:
    return len(text.split())


def scrape_linkedin_feed(max_posts: int = None) -> list[dict]:
    """
    Scrape LinkedIn feed. Returns original text posts only.
    Skips: job updates, reshares without post URL, company posts.
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
            page.goto("https://www.linkedin.com/feed/", timeout=30_000)
            time.sleep(5)

            if _is_session_expired(page.url):
                raise SessionExpiredError(
                    "LinkedIn redirected to login. Run session capture flow."
                )

            max_scroll_attempts = 20   # More scrolls — feed has fewer real posts
            scroll_attempt      = 0

            while len(collected) < max_posts and scroll_attempt < max_scroll_attempts:
                time.sleep(2)
                containers = page.locator(SELECTORS["post_container"]).all()

                for container in containers:
                    if len(collected) >= max_posts:
                        break

                    if _is_job_update(container, page):
                        continue

                    post_url = _extract_post_url(container, page)
                    if not post_url:
                        continue

                    if post_url in seen_urls:
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

                page.evaluate("window.scrollBy(0, 1200)")
                time.sleep(random.uniform(1.5, 3.0))
                scroll_attempt += 1

        except SessionExpiredError:
            raise

        except Exception as exc:
            print(f"[linkedin_scraper] Error after {len(collected)} posts: {exc}")
            if not collected:
                raise ScraperError(f"Scraper failed: {exc}") from exc

        finally:
            browser.close()

    return collected