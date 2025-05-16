import asyncio
from playwright.async_api import async_playwright

async def check_video_params(url):
    """
    Check and print video parameters and URL using Playwright
    """
    async with async_playwright() as p:
        try:
            # Launch browser
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            print(f"\nChecking URL: {url}")
            await page.goto(url)
            
            # Wait for video element
            video = await page.wait_for_selector(
                'video.persistentNativePlayer',
                timeout=30000
            )
            
            if not video:
                print("Video element not found")
                return
                
            # Get all relevant attributes
            attributes = await video.evaluate("""
                video => ({
                    kentryid: video.getAttribute('kentryid'),
                    kpartnerid: video.getAttribute('kpartnerid'),
                    kuiconfid: video.getAttribute('kuiconfid'),
                    kwidgetid: video.getAttribute('kwidgetid'),
                    src: video.getAttribute('src')
                })
            """)
            
            print("\nFound video attributes:")
            for key, value in attributes.items():
                print(f"{key}: {value}")
            
            await browser.close()
            
        except Exception as e:
            print(f"Error: {str(e)}")
            await browser.close()

# Test function
async def main():
    url = "https://www.ft.dk/aktuelt/webtv/video/20101/salen/99.aspx"
    await check_video_params(url)

if __name__ == "__main__":
    asyncio.run(main())