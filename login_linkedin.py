"""
Log in to the LinkedIn account the agent should use.

The agent never stores your password. It reuses a browser profile folder
(the Playwright "user data dir") that holds the logged-in session cookie.
This script opens a visible browser on that same folder so you can log in
once, after which every publish and scrape reuses that session.

Usage:
    poetry run python login_linkedin.py

To switch accounts:
    1. Quit the app.
    2. Rename or delete the old profile:  mv playwright_user_data playwright_user_data_old
    3. Run this script and log in with the new account.
"""

from playwright.sync_api import sync_playwright

from app.core.config import settings


def main() -> None:
    profile = settings.PLAYWRIGHT_SESSION_DIR
    print(f"Using browser profile: {profile}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=False,
            args=["--start-maximized"],
            viewport={"width": 1400, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.linkedin.com/login", timeout=60_000)

        print("")
        print("1. Log in with the account you want the agent to use.")
        print("2. Wait until you can see your LinkedIn feed.")
        print("3. Come back here and press Enter.")
        input()

        page.goto("https://www.linkedin.com/feed/", timeout=60_000)
        page.wait_for_timeout(3000)

        url = page.url.lower()
        if any(k in url for k in ("login", "authwall", "checkpoint", "uas/login")):
            print("\nNot logged in yet — the session was NOT saved. Run the script again.")
        else:
            print(f"\nSession saved. The agent will now post as this account.")

        context.close()


if __name__ == "__main__":
    main()
