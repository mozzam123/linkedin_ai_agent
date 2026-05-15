from playwright.sync_api import sync_playwright


def publish_to_linkedin(post_content: str):

    with sync_playwright() as p:

        browser = p.chromium.launch_persistent_context(

    user_data_dir="./playwright_user_data",

    headless=True

)

        page = browser.new_page()

        page.goto("https://www.linkedin.com/feed/")

        page.wait_for_timeout(5000)

        page.get_by_text("Start a post").click()

        page.wait_for_timeout(3000)

        modal = page.locator('[role="dialog"]')

        editor = modal.locator('[contenteditable="true"]').first

        editor.click()

        editor.press_sequentially(post_content)

        page.wait_for_timeout(2000)

        modal.get_by_role(
        "button",
        name="Post",
        exact=True
        ).click()

        page.wait_for_timeout(4000)

        # input("Press ENTER to close browser...")
        # browser.close()