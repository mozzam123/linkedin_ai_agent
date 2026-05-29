import random
import re
import time

from playwright.sync_api import sync_playwright

from app.core.config import settings


# ── Stable-ish LinkedIn selectors ────────────────────────────────────────────
SELECTORS = {

    # Better feed container selector
    "post_container": "div[data-id]",

    # Author/profile links
    "author_links": """
        a[href*='/in/'],
        a[href*='/company/']
    """,

    # Post URL
    "timestamp_link": """
        a[href*='/feed/update/'],
        a[href*='/posts/'],
        a[href*='activity']
    """,

    # Post type
    "poll_signal": """
        [data-test-id*='poll'],
        div[role='radiogroup']
    """,

    "article_signal": """
        div[data-test-id*='article'],
        a[href*='/pulse/']
    """,

    # Login detection
    "login_signals": [
        "login",
        "authwall",
        "checkpoint",
        "uas/login",
    ],
}


# ── Noise cleanup patterns ───────────────────────────────────────────────────
NOISE_PATTERNS = [

    r"Feed post",

    r"Promoted",

    r"\d[\d,]* followers",

    r"Like\s+Comment\s+Repost\s+Send",

    r"Copy link",

    r"Open menu",
]


# ── Exceptions ───────────────────────────────────────────────────────────────
class ScraperError(Exception):
    pass


class SessionExpiredError(ScraperError):
    pass


# ── Utility helpers ──────────────────────────────────────────────────────────
def _is_session_expired(url: str) -> bool:

    return any(
        keyword in url.lower()
        for keyword in SELECTORS["login_signals"]
    )


def _clean_text(text: str) -> str:

    if not text:
        return ""

    cleaned = text

    for pattern in NOISE_PATTERNS:

        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def _word_count(text: str) -> int:

    return len(text.split())


def _is_promoted(container) -> bool:

    try:
        text = container.inner_text().lower()

        return "promoted" in text

    except Exception:
        return False


# ── Extraction helpers ───────────────────────────────────────────────────────
def _extract_post_url(container) -> str | None:

    try:

        links = container.locator(
            SELECTORS["timestamp_link"]
        ).all()

        print("\n--- LINK DEBUG ---")

        for link in links:

            href = link.get_attribute("href") or ""

            print(href)

            if (
                "/feed/update/" in href
                or "/posts/" in href
                or "activity" in href
            ):

                clean = href.split("?")[0]

                if clean.startswith("/"):
                    return "https://www.linkedin.com" + clean

                return clean

    except Exception as exc:

        print(f"URL EXTRACTION ERROR: {exc}")

    return None


def _extract_author_name(container) -> str:

    try:

        links = container.locator(
            SELECTORS["author_links"]
        ).all()

        for link in links:

            try:

                text = (
                    link.inner_text() or ""
                ).strip()

                if not text:
                    continue

                text = text.split("\n")[0].strip()

                if text.lower() in [
                    "follow",
                    "message",
                    "connect",
                ]:
                    continue

                if 2 <= len(text) <= 80:
                    return text

            except Exception:
                continue

    except Exception:
        pass

    return ""


def _extract_author_url(container) -> str:

    try:

        links = container.locator(
            SELECTORS["author_links"]
        ).all()

        for link in links:

            href = (
                link.get_attribute("href") or ""
            )

            if (
                "/in/" in href
                or "/company/" in href
            ):

                clean = href.split("?")[0]

                if clean.startswith("/"):
                    return "https://www.linkedin.com" + clean

                return clean

    except Exception:
        pass

    return ""


def _expand_see_more(container) -> None:

    try:

        buttons = container.locator(
            "button:has-text('see more')"
        )

        if buttons.count() > 0:

            try:

                buttons.first.click(timeout=1000)

                time.sleep(
                    random.uniform(0.5, 1.2)
                )

            except Exception:
                pass

    except Exception:
        pass


def _extract_post_text(container) -> str:
    """
    TEMPORARY RAW EXTRACTION VERSION

    First make extraction reliable.
    Then improve cleaning later.
    """

    try:

        _expand_see_more(container)

        raw_text = container.inner_text()

        cleaned = _clean_text(raw_text)

        print("\n--- RAW POST TEXT ---")
        print(cleaned[:1000])

        return cleaned[:3000]

    except Exception as exc:

        print(f"TEXT EXTRACTION ERROR: {exc}")

        return ""


def _detect_post_type(container) -> str:

    try:

        if container.locator(
            SELECTORS["article_signal"]
        ).count() > 0:

            return "article"

        if container.locator(
            SELECTORS["poll_signal"]
        ).count() > 0:

            return "poll"

    except Exception:
        pass

    return "text"


# ── Main scraper ─────────────────────────────────────────────────────────────
def scrape_linkedin_feed(
    max_posts: int = None
) -> list[dict]:

    if max_posts is None:

        max_posts = (
            settings.MAX_POSTS_TO_SCRAPE_PER_RUN
        )

    collected = []

    seen_urls = set()

    with sync_playwright() as p:

        browser = (
            p.chromium.launch_persistent_context(

                user_data_dir=(
                    settings.PLAYWRIGHT_SESSION_DIR
                ),

                headless=False,

                args=[
                    "--start-maximized",
                ],

                viewport={
                    "width": 1400,
                    "height": 900,
                },

                slow_mo=300,
            )
        )

        page = (
            browser.pages[0]
            if browser.pages
            else browser.new_page()
        )

        try:
            # ── Open LinkedIn feed ───────────────────────
            page.goto(
                "https://www.linkedin.com/feed/",
                timeout=30_000,
            )

            page.wait_for_timeout(5000)

            # ── Session validation ──────────────────────
            if _is_session_expired(page.url):

                raise SessionExpiredError(
                    "LinkedIn session expired."
                )

            # ── Scroll loop ─────────────────────────────
            previous_height = 0

            stagnant_rounds = 0

            while (
                len(collected) < max_posts
                and stagnant_rounds < 3
            ):

                time.sleep(2)

                count = page.locator(
                    SELECTORS["post_container"]
                ).count()

                print(
                    f"\n========== FOUND {count} CONTAINERS =========="
                )

                for i in range(count):

                    if len(collected) >= max_posts:
                        break

                    try:

                        container = page.locator(
                            SELECTORS["post_container"]
                        ).nth(i)

                        # ── DEBUG HTML ─────────────────
                        html = container.inner_html()

                        print(
                            "\n========== HTML DEBUG =========="
                        )

                        print(html[:2000])

                        print(
                            "\n================================"
                        )

                        # ── Skip ads ───────────────────
                        if _is_promoted(container):

                            print(
                                "\nSKIPPED PROMOTED"
                            )

                            continue

                        # ── URL extraction ────────────
                        post_url = _extract_post_url(
                            container
                        )

                        if not post_url:

                            print(
                                "\nNO POST URL"
                            )

                            continue

                        if post_url in seen_urls:

                            print(
                                "\nDUPLICATE"
                            )

                            continue

                        # ── Text extraction ───────────
                        post_text = (
                            _extract_post_text(
                                container
                            )
                        )

                        print(
                            "\n--- FINAL POST TEXT ---"
                        )

                        print(post_text[:1000])

                        # Relaxed threshold
                        if _word_count(post_text) < 5:

                            print(
                                "\nTOO SHORT"
                            )

                            continue

                        # ── Metadata ──────────────────
                        author_name = (
                            _extract_author_name(
                                container
                            )
                        )

                        author_url = (
                            _extract_author_url(
                                container
                            )
                        )

                        post_type = (
                            _detect_post_type(
                                container
                            )
                        )

                        # ── Build object ──────────────
                        post_data = {

                            "post_url": post_url,

                            "author_name": author_name,

                            "author_linkedin_url": (
                                author_url
                            ),

                            "post_text": post_text,

                            "post_type": post_type,
                        }

                        collected.append(post_data)

                        seen_urls.add(post_url)

                        print(
                            "\n====== COLLECTED ======"
                        )

                        print(post_data)

                    except Exception as inner_exc:

                        print(
                            f"\nPOST ERROR: {inner_exc}"
                        )

                # ── Human-like scrolling ──────────────
                scroll_distance = random.randint(
                    900,
                    1800,
                )

                page.mouse.wheel(
                    0,
                    scroll_distance,
                )

                time.sleep(
                    random.uniform(2.0, 4.0)
                )

                current_height = page.evaluate(
                    "document.body.scrollHeight"
                )

                if current_height == previous_height:

                    stagnant_rounds += 1

                else:

                    stagnant_rounds = 0

                previous_height = current_height

        except SessionExpiredError:
            raise

        except Exception as exc:

            print(f"\nSCRAPER ERROR: {exc}")

            if not collected:

                raise ScraperError(
                    f"Scraper failed before collecting posts: {exc}"
                ) from exc

        finally:

            browser.close()

    print("\n\n========== FINAL POSTS ==========")

    print(collected)

    return collected


# ── Run scraper ──────────────────────────────────────────────────────────────
if __name__ == "__main__":

    posts = scrape_linkedin_feed()

    print(
        f"\nCollected {len(posts)} posts"
    )