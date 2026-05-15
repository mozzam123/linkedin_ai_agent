from playwright.sync_api import sync_playwright


def publish_to_linkedin(post_content: str):
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./playwright_user_data", 
            headless=True
        )
        page = browser.new_page()

        # 1. Navigate to LinkedIn
        page.goto("https://www.linkedin.com/feed/")

        # 2. Wait for the "Start a post" button and click it
        start_post_btn = page.get_by_text("Start a post")
        start_post_btn.wait_for(state="visible")
        start_post_btn.click()

        # 3. Locate the correct modal
        modal = page.get_by_role("dialog", name="Create post modal")
        
        # 4. Locate the text editor inside the correct modal
        editor = modal.locator('[contenteditable="true"]').first
        editor.wait_for(state="visible")
        editor.click()
        editor.press_sequentially(post_content)

        # 5. Locate the "Post" button and ensure it's clickable
        post_button = modal.get_by_role("button", name="Post", exact=True)
        post_button.wait_for(state="visible")
        post_button.click()

        # 6. FIX: Wait for LinkedIn's success message banner instead of modal detachment.
        # LinkedIn pops up a toast banner saying "Post successful" or "Post shared".
        try:
            # We look for a toast banner or the text indicating success
            success_toast = page.locator(".artdeco-toast-item, [role='alert']").get_by_text("successful", exact=False)
            # Give it a shorter 10-second threshold to show up so your FastAPI app doesn't hang
            success_toast.wait_for(state="visible", timeout=10000)
            print("Post Published successfully!")
        except Exception:
            # If the toast locator changes in the future, we don't want our script to crash 
            # if the post actually went through. We log it and gracefully exit.
            print("Post clicked, but success confirmation banner wasn't caught.")

        browser.close()