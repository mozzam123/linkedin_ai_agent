import os
from playwright.sync_api import sync_playwright


def publish_to_linkedin(post_content: str):
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./playwright_user_data", 
            headless=True
        )
        page = browser.new_page()

        try:
            # 1. Navigate to LinkedIn
            page.goto("https://www.linkedin.com/feed/")

            # ==========================================================
            # 2. DEFENSIVE STEP: Click "Start a post" button
            # ==========================================================
            start_post_btn = page.get_by_text("Start a post")
            
            # Fallback 1: Broad text layout match
            fallback_start_btn = page.locator("button:has-text('post'), .share-box-feed-entry__trigger").first
            
            try:
                start_post_btn.wait_for(state="visible", timeout=8000)
                start_post_btn.click()
            except Exception:
                # If primary text selector fails, try the structural fallback button
                fallback_start_btn.wait_for(state="visible", timeout=5000)
                fallback_start_btn.click()

            # ==========================================================
            # 3. DEFENSIVE STEP: Locate the Modal Container
            # ==========================================================
            modal = page.get_by_role("dialog", name="Create post modal")
            
            # Fallback 2: General dialog role if accessible name changes
            fallback_modal = page.locator("div[role='dialog']:has([contenteditable='true'])").first
            
            active_modal = modal
            try:
                modal.wait_for(state="visible", timeout=8000)
            except Exception:
                fallback_modal.wait_for(state="visible", timeout=5000)
                active_modal = fallback_modal

            # ==========================================================
            # 4. DEFENSIVE STEP: Locate text editor inside active modal
            # ==========================================================
            editor = active_modal.locator('[contenteditable="true"]').first
            editor.wait_for(state="visible", timeout=5000)
            editor.click()
            editor.press_sequentially(post_content)

            # ==========================================================
            # 5. DEFENSIVE STEP: Locate and click "Post" button
            # ==========================================================
            post_button = active_modal.get_by_role("button", name="Post", exact=True)
            
            # Fallback 3: Look for share action classes or any primary button inside modal saying "Post"
            fallback_post_button = active_modal.locator("button:has-text('Post'), .share-actions__post-button").first
            
            try:
                post_button.wait_for(state="visible", timeout=5000)
                post_button.click()
            except Exception:
                fallback_post_button.wait_for(state="visible", timeout=5000)
                fallback_post_button.click()

            # ==========================================================
            # 6. VERIFICATION STEP: Wait for success toast banner
            # ==========================================================
            try:
                success_toast = page.locator(".artdeco-toast-item, [role='alert']").get_by_text("successful", exact=False)
                success_toast.wait_for(state="visible", timeout=10000)
                print("Post Published successfully!")
            except Exception:
                # Don't fail the workflow if the post went out but the toast banner layout changed
                print("Post action triggered, but confirmation banner structure wasn't caught.")

        except Exception as e:
            # ==========================================================
            # FAILURE VISIBILITY: Save diagnostic snapshot on exception
            # ==========================================================
            os.makedirs("error_logs", exist_ok=True)
            screenshot_path = "error_logs/linkedin_automation_error.png"
            page.screenshot(path=screenshot_path)
            
            print(f"Automation execution failed. Diagnostic image saved to {screenshot_path}")
            raise e  # Bubble up the error so your node wrapper catches it properly
            
        finally:
            browser.close()