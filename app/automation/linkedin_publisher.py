import os

from playwright.sync_api import sync_playwright

from app.core.config import settings

# LinkedIn's composer is a Quill-style contenteditable. The visible textbox has
# role="textbox"; other contenteditables can exist elsewhere on the page.


def _first_visible(locator):
    """Return the first visible element in a locator group, or None."""
    for index in range(locator.count()):
        element = locator.nth(index)
        try:
            if element.is_visible():
                return element
        except Exception:
            continue
    return None


def _first_visible_editor(page):
    """
    The composer is a plain contenteditable with role="textbox". It is NOT
    always wrapped in div[role='dialog'] any more, so search the page.
    """
    return (
        _first_visible(page.locator("[contenteditable='true'][role='textbox']"))
        or _first_visible(page.locator("[contenteditable='true']"))
    )


def _type_post(page, editor, content: str) -> bool:
    """
    Type into the composer and confirm the text actually landed.

    press_sequentially() alone proved unreliable: LinkedIn re-renders the
    composer (e.g. the "Collaborative Posts" banner) and focus is lost, so
    every keystroke goes nowhere and the Post button stays disabled.
    keyboard.insert_text() sends one input event, which the editor accepts.
    """
    editor.click()
    page.wait_for_timeout(700)

    page.keyboard.insert_text(content)
    page.wait_for_timeout(1500)
    if editor.inner_text().strip():
        return True

    # Fallback: focus again and type character by character
    editor.click()
    page.wait_for_timeout(400)
    editor.press_sequentially(content, delay=10)
    page.wait_for_timeout(1500)
    return bool(editor.inner_text().strip())


def publish_to_linkedin(post_content: str):
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=settings.PLAYWRIGHT_SESSION_DIR,
            headless=True,
        )
        page = browser.new_page()

        try:
            page.goto("https://www.linkedin.com/feed/", timeout=45_000)

            # Session check — a dead session shows a login wall instead of the feed
            if any(k in page.url.lower() for k in ("login", "authwall", "checkpoint")):
                raise RuntimeError(
                    "LinkedIn session is not valid. Run `python login_linkedin.py` to log in again."
                )

            # 1. Open the composer
            start_post_btn = page.get_by_text("Start a post")
            try:
                start_post_btn.wait_for(state="visible", timeout=15_000)
                start_post_btn.click()
            except Exception:
                page.locator(
                    "button:has-text('post'), .share-box-feed-entry__trigger"
                ).first.wait_for(state="visible", timeout=10_000)
                page.locator(
                    "button:has-text('post'), .share-box-feed-entry__trigger"
                ).first.click()

            # 2. Wait for the composer to appear and find the editor
            editor = None
            for _ in range(20):  # up to ~10s
                editor = _first_visible_editor(page)
                if editor is not None:
                    break
                page.wait_for_timeout(500)
            if editor is None:
                raise RuntimeError("Could not find the post editor — the composer did not open.")
            page.wait_for_timeout(600)

            # 3. Put the text in it
            if not _type_post(page, editor, post_content):
                raise RuntimeError(
                    "Text did not land in the post editor — LinkedIn kept the Post button disabled."
                )

            # 4. Wait for the Post button to become enabled, then click it
            post_button = _first_visible(page.get_by_role("button", name="Post", exact=True))
            if post_button is None:
                post_button = _first_visible(
                    page.locator("button.share-actions__post-button:visible")
                )
            if post_button is None:
                raise RuntimeError("Could not find the Post button in the composer.")

            for _ in range(20):  # up to ~10s for the composer to validate the text
                if post_button.is_enabled():
                    break
                page.wait_for_timeout(500)
            if not post_button.is_enabled():
                raise RuntimeError("Post button stayed disabled after typing the content.")

            post_button.click()

            # 5. Confirm it went out
            try:
                page.locator(
                    ".artdeco-toast-item, [role='alert']"
                ).get_by_text("successful", exact=False).wait_for(state="visible", timeout=15_000)
                print("Post Published successfully!")
            except Exception:
                print("Post action triggered, but confirmation banner structure wasn't caught.")

        except Exception as e:
            os.makedirs("error_logs", exist_ok=True)
            screenshot_path = "error_logs/linkedin_automation_error.png"
            try:
                page.screenshot(path=screenshot_path)
            except Exception:
                pass
            print(f"Publishing failed: {e}")
            print(f"Diagnostic image saved to {screenshot_path}")
            raise

        finally:
            browser.close()
