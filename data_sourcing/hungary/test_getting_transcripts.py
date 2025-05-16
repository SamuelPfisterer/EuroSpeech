from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        # Launch the browser in headed mode (visible)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to your target website
        page.goto("https://www.parlament.hu/web/guest/orszaggyulesi-naplo")
        
        # This will keep the browser open until you press Enter
        input("Press Enter to close the browser...")
        
        context.close()
        browser.close()

if __name__ == "__main__":
    main() 