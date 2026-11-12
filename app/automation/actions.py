"""
Reusable LinkedIn UI actions.

Every browser interaction (publishing, commenting, scraping) goes through the
helpers in this module so that selectors, waits and typing live in one place
instead of being duplicated per feature.

Two rules that came from real failures:
  1. Never assume a wrapper (role="dialog") exists — LinkedIn changes it.
     Anchor on the element you actually need (the editor, the button).
  2. Never assume typing worked. Type, then read the editor back and verify.
     A silent typing failure leaves a disabled button and a useless error.

Dry run:
    LINKEDIN_DRY_RUN=1  (or dry_run=True on click_or_skip)
    performs every step except the final irreversible click.

Self test (safe, posts nothing):
    poetry run python -m app.automation.actions
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from playwright.sync_api import Locator, Page, sync_playwright

from app.core.config import settings

FEED_URL = "https://www.linkedin.com/feed/"
LOGIN_URL_MARKERS = ("login", "authwall", "checkpoint", "uas/login")

# LinkedIn labels its editors. The comment box label is stable and unique.
COMMENT_EDITOR_LABEL = "Text editor for creating comment"
EDITOR_SELECTOR = "[contenteditable='true'][aria-label='{label}']"
ANY_EDITOR_SELECTOR = "[contenteditable='true'][role='textbox']"
POST_CARD_SELECTOR = "div[role='listitem']"


class ActionError(RuntimeError):
    """A LinkedIn step failed and could not be completed."""


class SessionExpiredError(ActionError):
    """The saved LinkedIn session is no longer valid."""


# ── Browser plumbing ──────────────────────────────────────────────────────────

def is_dry_run() -> bool:
    return os.getenv("LINKEDIN_DRY_RUN", "").strip().lower() in ("1", "true", "yes", "on")


@contextmanager
def browser_session(headless: bool = True, profile: str | None = None):
    """Yield a Page backed by the saved LinkedIn profile, and always close it."""
    user_data_dir = profile or settings.PLAYWRIGHT_SESSION_DIR
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            args=["--start-maximized"],
            viewport={"width": 1400, "height": 900},
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            yield page
        finally:
            context.close()


def goto(page: Page, url: str, timeout_ms: int = 45_000) -> None:
    page.goto(url, timeout=timeout_ms)


def ensure_logged_in(page: Page) -> None:
    url = page.url.lower()
    if any(marker in url for marker in LOGIN_URL_MARKERS):
        raise SessionExpiredError(
            "LinkedIn session is not valid. Run `poetry run python login_linkedin.py`."
        )


# ── Generic element helpers ───────────────────────────────────────────────────

def first_visible(locator: Locator) -> Locator | None:
    """Return the first visible element in a locator group, or None."""
    for index in range(locator.count()):
        element = locator.nth(index)
        try:
            if element.is_visible():
                return element
        except Exception:
            continue
    return None


def wait_until_enabled(button: Locator, page: Page, timeout_ms: int = 10_000) -> bool:
    waited = 0
    while waited < timeout_ms:
        if button.is_enabled():
            return True
        page.wait_for_timeout(500)
        waited += 500
    return button.is_enabled()


def type_text(page: Page, editor: Locator, text: str, verify: bool = True) -> bool:
    """
    Type into a contenteditable editor and confirm the text landed.

    keyboard.insert_text() fires a single input event, which Quill-style
    editors (LinkedIn's composer and comment box) accept reliably. Typing
    character-by-character loses focus when the component re-renders.
    """
    editor.click()
    page.wait_for_timeout(600)

    page.keyboard.insert_text(text)
    page.wait_for_timeout(1200)
    if not verify or editor.inner_text().strip():
        return True

    # Fallback: re-focus and type character by character
    editor.click()
    page.wait_for_timeout(400)
    editor.press_sequentially(text, delay=10)
    page.wait_for_timeout(1200)
    return bool(editor.inner_text().strip())


def click_or_skip(page: Page, element: Locator, what: str, dry_run: bool | None = None) -> bool:
    """
    Click unless this is a dry run. Returns True if the click happened.
    The dry run exists so a whole flow (including the last click) can be
    rehearsed without publishing anything.
    """
    if dry_run is None:
        dry_run = is_dry_run()
    if dry_run:
        print(f"[dry-run] would click {what}")
        return False
    element.click()
    return True


def discard_draft(page: Page, url: str = FEED_URL) -> None:
    """
    Abandon an open composer or comment box and return to the feed.

    Reloading is used instead of Escape because Escape can raise a
    "Save this post?" dialog, which then blocks the next action.
    """
    goto(page, url)
    page.wait_for_timeout(1500)


# ── Composer (new post) ───────────────────────────────────────────────────────

def open_composer(page: Page) -> Locator:
    """Open the 'Start a post' composer and return its editor."""
    trigger = page.get_by_text("Start a post")
    if trigger.count() == 0:
        raise ActionError("Could not find the 'Start a post' button on the feed.")
    trigger.first.click()

    editor = None
    for _ in range(20):  # up to ~10s for the composer to mount
        editor = (
            first_visible(page.locator(EDITOR_SELECTOR.format(label="Text editor for creating content")))
            or first_visible(page.locator(ANY_EDITOR_SELECTOR))
            or first_visible(page.locator("[contenteditable='true']"))
        )
        if editor is not None:
            break
        page.wait_for_timeout(500)
    if editor is None:
        raise ActionError("The post composer did not open (no editable text box found).")

    page.wait_for_timeout(500)
    return editor


def composer_submit_button(page: Page) -> Locator:
    """The 'Post' button, once it is visible (caller waits for enabled)."""
    button = first_visible(page.get_by_role("button", name="Post", exact=True))
    if button is None:
        button = first_visible(page.locator("button.share-actions__post-button"))
    if button is None:
        raise ActionError("Could not find the Post button in the composer.")
    return button


# ── Comments ──────────────────────────────────────────────────────────────────

def find_post_card(page: Page, post_url: str) -> Locator | None:
    """
    Best-effort: find the feed card that contains a link to `post_url`.

    The feed does not always expose permalinks, so when this returns None,
    open the post itself with goto_post() instead of scrolling to find it.
    """
    slug = post_url.rstrip("/").split("/")[-1]
    if not slug:
        return None
    cards = page.locator(POST_CARD_SELECTOR)
    for index in range(cards.count()):
        card = cards.nth(index)
        try:
            if card.locator(f"a[href*='{slug}']").count() > 0:
                return card
        except Exception:
            continue
    return None


def find_commentable_card(page: Page, max_scrolls: int = 3) -> Locator | None:
    """
    Return the first feed card that has a visible Comment button.

    The feed renders action bars lazily, so cards in view often have no
    Comment button until the page is scrolled a little.
    """
    for _ in range(max_scrolls + 1):
        cards = page.locator(POST_CARD_SELECTOR)
        for index in range(cards.count()):
            card = cards.nth(index)
            try:
                if first_visible(card.get_by_role("button", name="Comment", exact=True)):
                    return card
            except Exception:
                continue
        page.mouse.wheel(0, 1600)
        page.wait_for_timeout(2000)
    return None


def goto_post(page: Page, post_url: str) -> None:
    """Open a single post page — the reliable way to comment on a known post."""
    goto(page, post_url)
    ensure_logged_in(page)
    page.wait_for_timeout(2500)


def open_comment_box(page: Page, scope: Locator | None = None) -> Locator:
    """
    Return the comment editor, opening it if needed.

    On a single-post page the editor is often already rendered; in the feed
    it only appears after clicking 'Comment'. Both cases are handled.
    """
    search_root = scope if scope is not None else page

    editor = first_visible(search_root.locator(EDITOR_SELECTOR.format(label=COMMENT_EDITOR_LABEL)))
    if editor is not None:
        return editor

    trigger = first_visible(search_root.get_by_role("button", name="Comment", exact=True))
    if trigger is None:
        raise ActionError("Could not find a 'Comment' button to open the comment box.")
    trigger.click()

    editor = None
    for _ in range(16):  # up to ~8s for the editor to mount
        editor = first_visible(
            search_root.locator(EDITOR_SELECTOR.format(label=COMMENT_EDITOR_LABEL))
        ) or first_visible(search_root.locator(ANY_EDITOR_SELECTOR))
        if editor is None and search_root is not page:
            # On some layouts the editor renders outside the card container
            editor = first_visible(page.locator(EDITOR_SELECTOR.format(label=COMMENT_EDITOR_LABEL)))
        if editor is not None:
            break
        page.wait_for_timeout(500)
    if editor is None:
        raise ActionError("The comment box opened but no editor appeared.")
    page.wait_for_timeout(400)
    return editor


def comment_submit_button(page: Page, scope: Locator | None = None, editor: Locator | None = None) -> Locator:
    """
    The submit button of an open comment box.

    LinkedIn shows TWO controls named 'Comment': the action-bar button that
    focuses the box (small, above) and the real submit button (below the
    editor, next to the text box). Picking the first one clicks the action bar
    and nothing is submitted — which is why the editor position is used to
    prefer the button underneath it.
    """
    search_root = scope if scope is not None else page
    buttons = search_root.get_by_role("button", name="Comment", exact=True)

    candidates = []
    for index in range(buttons.count()):
        button = buttons.nth(index)
        try:
            if button.is_visible():
                candidates.append(button)
        except Exception:
            continue
    if not candidates:
        raise ActionError("Could not find the Comment submit button.")

    if editor is not None:
        try:
            editor_box = editor.bounding_box()
            if editor_box:
                below = []
                for button in candidates:
                    box = button.bounding_box()
                    if box and box["y"] >= editor_box["y"] - 5:
                        below.append((box["y"], button))
                if below:
                    return min(below, key=lambda pair: pair[0])[1]
        except Exception:
            pass

    return candidates[-1]


def comment_editor_cleared(page: Page) -> bool:
    """
    True when no visible comment editor still holds text.

    LinkedIn clears the composer when a comment is accepted, so an emptied box
    is a reliable success signal — often more reliable than finding the text,
    which may sit under a collapsed "Load more comments".
    """
    editors = page.locator(EDITOR_SELECTOR.format(label=COMMENT_EDITOR_LABEL))
    for index in range(editors.count()):
        editor = editors.nth(index)
        try:
            if editor.is_visible() and editor.inner_text().strip():
                return False
        except Exception:
            continue
    return True


def comment_visible(page: Page, comment_text: str) -> bool:
    """
    True if the comment text is present on the page *outside* an editor.

    Checking the whole body is useless: the text stays in the comment box
    until it is submitted, so a naive check reports success before clicking.
    Editors are stripped from a copy of the DOM before searching.
    """
    needle = _normalize(comment_text)[:60]
    if not needle:
        return False
    try:
        body = page.evaluate(
            """() => {
                const clone = document.body.cloneNode(true);
                clone.querySelectorAll("[contenteditable='true']").forEach(el => el.remove());
                return clone.innerText || '';
            }"""
        )
        return needle in _normalize(body)
    except Exception:
        return False


# ── Locating a post without a permalink ──────────────────────────────────────

def _normalize(text: str) -> str:
    return " ".join((text or "").split()).lower()


def card_matches(card: Locator, post_text: str, author_name: str | None = None) -> bool:
    """
    Compare a feed card to a stored post by CONTENT only.

    Author names are not used for matching: a post that mentions someone else
    makes the first profile link in the card point at the mentioned person,
    not the author, so a name check rejects the correct card.
    """
    from app.automation.linkedin_scraper import _extract_post_text

    target = _normalize(post_text)
    if not target:
        return False
    card_text = _normalize(_extract_post_text(card))
    if not card_text:
        return False

    return card_text[:120] == target[:120] or target[:80] in card_text


def find_card_by_text(
    page: Page,
    post_text: str,
    author_name: str | None = None,
    max_scrolls: int = 12,
) -> Locator | None:
    """Scroll the feed until the matching post card is found."""
    for _ in range(max_scrolls + 1):
        cards = page.locator(POST_CARD_SELECTOR)
        for index in range(cards.count()):
            card = cards.nth(index)
            try:
                if card_matches(card, post_text, author_name):
                    return card
            except Exception:
                continue
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(1800)
    return None


def resolve_permalink(page: Page, author_url: str, post_text: str, max_scrolls: int = 4) -> str:
    """
    Find a post's real permalink on its author's activity page.

    The feed exposes no links, but `/{profile}/recent-activity/all/` does —
    each post there carries a /feed/update/urn:li:activity:... link. That is
    what makes commenting on an older post possible at all.
    """
    from app.automation.linkedin_scraper import _capture_permalink, _extract_post_text

    if not author_url:
        return ""
    base = author_url.rstrip("/")
    goto(page, f"{base}/recent-activity/all/")
    ensure_logged_in(page)
    page.wait_for_timeout(2500)

    target = _normalize(post_text)
    if not target:
        return ""

    for _ in range(max_scrolls + 1):
        cards = page.locator(POST_CARD_SELECTOR)
        for index in range(cards.count()):
            card = cards.nth(index)
            try:
                card_text = _normalize(_extract_post_text(card))
            except Exception:
                continue
            if not card_text:
                continue
            if not (card_text[:120] == target[:120] or target[:80] in card_text):
                continue

            link = first_visible(card.locator("a[href*='/feed/update/'], a[href*='/posts/']"))
            if link is not None:
                href = (link.get_attribute("href") or "").strip()
                if href.startswith("/"):
                    href = "https://www.linkedin.com" + href
                if href.startswith("http"):
                    return href

            # No timestamp link on this card — ask its menu
            captured = _capture_permalink(card, page)
            if captured:
                return captured
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(1500)

    return ""


def comment_on_post(
    page: Page,
    post_text: str,
    comment_text: str,
    author_name: str | None = None,
    post_url: str | None = None,
    author_url: str | None = None,
    dry_run: bool | None = None,
) -> bool:
    """
    Comment on a post.

    Order matters: the fast, verified path first, the best-effort one last.
      1. a real permalink (captured at discovery) → open the post directly
      2. a card in the live feed with matching content (works while fresh)
      3. the author's activity page, which sometimes exposes a permalink

    Returns True when the comment was submitted, False in dry-run mode.
    """
    permalink = post_url if (post_url or "").startswith("http") else ""

    if permalink:
        return _comment_on_permalink(page, permalink, comment_text, dry_run)

    # 2. Live feed
    goto(page, FEED_URL)
    page.wait_for_timeout(2500)
    card = find_card_by_text(page, post_text, author_name)
    if card is not None:
        card.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        editor = open_comment_box(page, card)
        if not type_text(page, editor, comment_text):
            raise ActionError("Comment text did not land in the comment box.")
        submit = comment_submit_button(page, card, editor=editor)
        if not wait_until_enabled(submit, page, 5000):
            raise ActionError("Comment button stayed disabled after typing.")
        return click_or_skip(page, submit, "Comment", dry_run)

    # 3. Author activity page (best effort)
    if author_url:
        resolved = resolve_permalink(page, author_url, post_text)
        if resolved:
            return _comment_on_permalink(page, resolved, comment_text, dry_run)

    raise ActionError("That post could not be located in the feed or on the author's profile.")


def _comment_on_permalink(page: Page, permalink: str, comment_text: str, dry_run: bool | None) -> bool:
    goto_post(page, permalink)
    editor = open_comment_box(page)
    if not type_text(page, editor, comment_text):
        raise ActionError("Comment text did not land in the comment box.")
    submit = comment_submit_button(page, editor=editor)
    if not wait_until_enabled(submit, page, 5000):
        raise ActionError("Comment button stayed disabled after typing.")
    return click_or_skip(page, submit, "Comment", dry_run)


# ── Self test ─────────────────────────────────────────────────────────────────

def _self_test() -> None:
    """Rehearse the composer and the comment box without publishing anything."""
    with browser_session(headless=True) as page:
        goto(page, FEED_URL)
        ensure_logged_in(page)
        print("✓ session valid")

        # 1. Comment box first — the composer modal would block the feed
        card = find_commentable_card(page)

        if card is None:
            print("! no feed card with a Comment button in view — skipping comment check")
        else:
            print("✓ feed card located")
            comment_editor = open_comment_box(page, card)
            print("✓ comment box opened")
            typed = type_text(page, comment_editor, "Self-test comment — nothing posted.")
            print(f"✓ comment typing verified: {typed}")
            submit = comment_submit_button(page, card, editor=comment_editor)
            print(f"✓ comment submit found, enabled={wait_until_enabled(submit, page, 5000)}")
            discard_draft(page)
            print("✓ comment draft discarded (nothing was posted)")

        # 2. Post composer
        editor = open_composer(page)
        print("✓ composer opened")
        ok = type_text(page, editor, "Self-test draft — nothing is posted.")
        print(f"✓ composer typing verified: {ok} ({len(editor.inner_text().strip())} chars)")
        button = composer_submit_button(page)
        print(f"✓ post button found, enabled={wait_until_enabled(button, page)}")
        discard_draft(page)
        print("✓ composer draft discarded (nothing was posted)")

        print("✓ self test complete — nothing was published")


if __name__ == "__main__":
    _self_test()
