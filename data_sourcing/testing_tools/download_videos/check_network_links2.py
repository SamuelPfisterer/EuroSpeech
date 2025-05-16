from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import re
from datetime import datetime
import time

def monitor_with_playwright_stealth(url):
    """Monitor video page using Playwright with stealth plugin"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Apply stealth mode
        stealth_sync(page)
        
        m3u8_urls = set()
        
        def handle_request(request):
            url = request.url
            if '.m3u8' in url:
                m3u8_urls.add(url)
                print(f"Found m3u8 URL: {url}")
        
        page.on("request", handle_request)
        
        try:
            print("Loading page with stealth mode...")
            page.goto(url, wait_until="networkidle")
            
            # Try to interact with video player
            try:
                player = page.wait_for_selector('.flowplayer, .video-js', timeout=10000)
                if player:
                    player.click()
                    page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"Couldn't interact with video player: {str(e)}")
            
            time.sleep(10)
            
            if m3u8_urls:
                template = "https://ftlive.streaming.ft.dk/vod/_definst_/mp4:{year}/{date}_13_00_F_{video_id}_h264.mp4/playlist.m3u8"
                return template, list(m3u8_urls)
            
            return None, []
            
        finally:
            browser.close()

if __name__ == "__main__":
    url = "https://www.ft.dk/aktuelt/webtv/video/20101/salen/108.aspx"
    result = monitor_with_playwright_stealth(url)
    print(result)