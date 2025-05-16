from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync  # pip install playwright-stealth

def get_page_with_stealth():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    
    # Apply stealth mode
    stealth_sync(page)
    
    # Additional evasion techniques
    page.set_extra_http_headers({
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    })
    
    page.goto('https://www.ft.dk/aktuelt/webtv/video/20101/salen/93.aspx')
    
    # Wait for real content
    page.wait_for_load_state('networkidle', timeout=60000)
    
    return playwright, browser, page

if __name__ == "__main__":
    playwright, browser, page = get_page_with_stealth()
    try:
        print(page.content())
    finally:
        browser.close()
        playwright.stop()