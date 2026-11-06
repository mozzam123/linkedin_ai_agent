import hashlib
import random
import re
import time
from functools import lru_cache

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


def _is_suggestion_card(post_text: str, author_name: str) -> bool:
    """
    The feed mixes 'people you may know' / 'because you recently followed'
    units in with real posts. They have no post body and are not commentable.
    """
    if not (author_name or "").strip():
        return True
    text = (post_text or "").lower()
    markers = (
        "people you may know",
        "because you recently followed",
        "people skilled in",
        "also follow these people",
        "add these people you may know",
        "suggested for you",
    )
    return any(marker in text for marker in markers)


@lru_cache(maxsize=1)
def _niche_pattern():
    keywords = sorted({k.lower() for k in settings.NICHE_KEYWORDS}, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\b", re.IGNORECASE)


def _has_niche_keyword(text: str) -> bool:
    """
    Cheap pre-filter so off-topic posts never reach the LLM scorer.

    Without it, an 8-post scan burns scoring calls and DB rows on HR posts,
    internship ads and stock-market commentary.
    """
    if not settings.SCRAPER_KEYWORD_PREFILTER:
        return True
    return bool(_niche_pattern().search(text or ""))


def _synthetic_post_key(author_url: str, post_text: str) -> str:
    """
    Stable identity for a post when LinkedIn exposes no permalink.

    The 2026 feed renders no /feed/update/ link anywhere in the card, so the
    same post must be recognisable across runs by its author + content.
    """
    normalized = " ".join((post_text or "").split()).lower()
    digest = hashlib.sha1(f"{author_url or ''}|{normalized}".encode("utf-8")).hexdigest()[:24]
    return f"urn:li:feed-post:{digest}"


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


def _clean_person_name(raw: str) -> str:
    """Turn 'View Harrison Chase’s profile' / 'Name • 3rd+' into 'Harrison Chase'."""
    name = (raw or "").split("\n")[0].strip()
    name = name.split("•")[0].strip()
    for prefix in ("View ", "view "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    for suffix in ("'s profile", "’s profile", "'s Profile", "’s Profile"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.strip()


def _extract_author_name(container) -> str:
    # Prefer the visible name text; aria-labels are often "View X's profile"
    try:
        for link in container.locator(SELECTORS["author_link"]).all():
            text = _clean_person_name(link.inner_text())
            if text and len(text) < 60:
                return text
            text = _clean_person_name(link.get_attribute("aria-label") or "")
            if text and len(text) < 60:
                return text
    except Exception:
        pass
    try:
        return _clean_person_name(container.get_attribute("aria-label") or "")
    except Exception:
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
    """
    Extract the post body, never the author's headline.

    A card contains the author name, the author's headline (job title / bio)
    and the post itself, all as <p> elements. The headline is often longer
    than a short post, so length alone picks the wrong one.

    The fix is positional: everything in the first ~220 characters of the card
    is header (name, headline, timestamp). Any <p> whose text appears there is
    the headline, not the body. Suggestion cards ("Because you recently
    followed X") are rejected too — they are not posts at all.
    """
    try:
        text = container.evaluate(
            """el => {
                const clean = t => t.replace(/\\s+/g, ' ').trim();
                const cardText = clean(el.innerText || '');
                const header = cardText.slice(0, 220).toLowerCase();
                const NOT_A_POST = [
                    'people you may know',
                    'because you recently followed',
                    'people skilled in',
                    'also follow these people',
                    'suggested for you',
                ];
                let best = '';
                el.querySelectorAll('p').forEach(p => {
                    const t = clean(p.innerText || '');
                    const low = t.toLowerCase();
                    if (t.length < 60) return;
                    if (header.includes(low)) return;              // author headline
                    if (t.includes(' | ')) return;                 // headline separator
                    if (low.startsWith('feed post')) return;
                    if (NOT_A_POST.some(m => low.includes(m))) return;
                    if (t.split(' ').length < 12) return;          // too short to be a body
                    if (t.length > best.length) best = t;
                });
                return best;
            }"""
        )
        return (text or "").strip()
    except Exception:
        return ""


def _word_count(text: str) -> int:
    return len(text.split())


def scrape_linkedin_feed(max_posts: int = None, headless: bool = None) -> list[dict]:
    """
    Scrape LinkedIn feed. Scrolls the #workspace container directly
    since LinkedIn's feed does not scroll via window.scrollBy.

    headless: override settings.SCRAPER_HEADLESS (useful for scheduled runs
    and for tests on machines without a desktop session).
    """
    if max_posts is None:
        max_posts = settings.MAX_POSTS_TO_SCRAPE_PER_RUN

    if headless is None:
        headless = settings.SCRAPER_HEADLESS

    collected: list[dict] = []
    seen_urls: set[str]   = set()

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=settings.PLAYWRIGHT_SESSION_DIR,
            headless=headless,
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

                    # The 2026 feed no longer exposes post permalinks at all
                    # (no /feed/update/ links, even on hover), so fall back to
                    # a stable content key for dedupe and lookups.
                    post_url = _extract_post_url(container, page)

                    post_text = _extract_post_text(container)
                    if _word_count(post_text) < settings.MIN_POST_WORD_COUNT:
                        continue

                    author_name = _extract_author_name(container)
                    author_url  = _extract_author_url(container)

                    if _is_suggestion_card(post_text, author_name):
                        continue

                    if not _has_niche_keyword(post_text):
                        continue

                    if not post_url:
                        post_url = _synthetic_post_key(author_url, post_text)

                    if post_url in seen_urls:
                        continue

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