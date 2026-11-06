import os

import app.automation.actions as actions
from app.automation.actions import (
    ActionError,
    browser_session,
    click_or_skip,
    composer_submit_button,
    ensure_logged_in,
    goto,
    open_composer,
    type_text,
    wait_until_enabled,
)
from app.core.config import settings  # noqa: F401  (kept for backwards-compatible imports)


def publish_to_linkedin(post_content: str, dry_run: bool | None = None) -> bool:
    """
    Publish `post_content` to LinkedIn.

    Returns True when the post was submitted, False in dry-run mode.
    Raises ActionError with the exact failing step on failure.
    """
    if dry_run is None:
        dry_run = actions.is_dry_run()

    with browser_session(headless=True) as page:
        try:
            goto(page, actions.FEED_URL)
            ensure_logged_in(page)

            editor = open_composer(page)
            if not type_text(page, editor, post_content):
                raise ActionError(
                    "Text did not land in the post editor — LinkedIn kept the Post button disabled."
                )

            button = composer_submit_button(page)
            if not wait_until_enabled(button, page):
                raise ActionError("Post button stayed disabled after typing the content.")

            if not click_or_skip(page, button, "Post", dry_run):
                print("Dry run: post was NOT submitted.")
                return False

            try:
                page.locator(".artdeco-toast-item, [role='alert']").get_by_text(
                    "successful", exact=False
                ).wait_for(state="visible", timeout=15_000)
                print("Post Published successfully!")
            except Exception:
                print("Post action triggered, but confirmation banner structure wasn't caught.")
            return True

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
