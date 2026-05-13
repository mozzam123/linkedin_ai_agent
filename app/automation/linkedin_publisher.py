from playwright.sync_api import sync_playwright


def publish_to_linkedin(post_content: str):

    with sync_playwright() as p:

        browser = p.chromium.launch_persistent_context(

    user_data_dir="./playwright_user_data",

    headless=False

)

        page = browser.new_page()

        page.goto("https://www.linkedin.com")

        input("Login manually and press ENTER here...")

        page.goto("https://www.linkedin.com/feed/")

        page.wait_for_timeout(5000)

        page.get_by_text("Start a post").click()

        page.wait_for_timeout(3000)

        editor = page.locator('[contenteditable="true"]').first

        editor.click()

        page.wait_for_timeout(2000)

        page.keyboard.type(post_content)

        page.wait_for_timeout(3000)
        # browser.close()