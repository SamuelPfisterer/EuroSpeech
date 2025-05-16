from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Any
from playwright.sync_api import sync_playwright
import yt_dlp
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

@dataclass
class DownloadRecipe:
    method_name: str
    url_found: str
    extraction_function: Callable
    parameters: Dict[str, Any]
    estimated_time: float
    priority: int  # Lower number = higher priority (more reliable/efficient)

def find_direct_video_sources(url: str, selectors: List[str] = None, 
                            media_extensions: List[str] = None) -> Optional[str]:
    """Comprehensive direct video source finder"""
    if selectors is None:
        selectors = [
            'video', 'source', 'a', 'link',  # HTML elements
            '[type*="video"]',  # Elements with video type
            '[src*=".mp4"], [src*=".m3u8"], [src*=".mpd"]',  # Direct source attributes
            '[href*=".mp4"], [href*=".m3u8"], [href*=".mpd"]',  # Link attributes
        ]
    
    if media_extensions is None:
        media_extensions = [
            '.mp4', '.m4v', '.m4s',  # MP4 variants
            '.m3u8', '.m3u',  # HLS streams
            '.mpd',  # DASH streams
            '.webm', '.mkv',  # Web formats
            '.ts',  # Transport streams
            '.mov', '.avi',  # Other video formats
        ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Store found URLs for validation
        potential_urls = set()
        
        # Method 1: Check direct video/source elements
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                # Check src attribute
                src = element.get('src')
                if src:
                    potential_urls.add(urljoin(url, src))
                
                # Check href attribute
                href = element.get('href')
                if href:
                    potential_urls.add(urljoin(url, href))
                
                # Check data-src and other common video attributes
                for attr in ['data-src', 'data-video', 'data-url', 'data-href']:
                    if value := element.get(attr):
                        potential_urls.add(urljoin(url, value))
        
        # Method 2: Look for media URLs in all attributes of all elements
        for element in soup.find_all():
            for attr in element.attrs.values():
                if isinstance(attr, str):
                    # Check if attribute value contains media extension
                    if any(ext in attr.lower() for ext in media_extensions):
                        potential_urls.add(urljoin(url, attr))
        
        # Method 3: Search for media URLs in script tags
        for script in soup.find_all('script'):
            if script.string:
                # Look for quoted URLs containing media extensions
                for ext in media_extensions:
                    matches = re.findall(f'"([^"]*{ext}[^"]*)"', script.string)
                    matches.extend(re.findall(f"'([^']*{ext}[^']*)'", script.string))
                    for match in matches:
                        potential_urls.add(urljoin(url, match))
        
        # Validate found URLs
        for potential_url in potential_urls:
            try:
                if any(potential_url.lower().endswith(ext) for ext in media_extensions):
                    response = requests.head(potential_url, timeout=5, headers=headers)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if any(media_type in content_type for media_type in ['video/', 'application/x-mpegurl', 'application/dash+xml']):
                            return potential_url
            except:
                continue
        
        return None
        
    except Exception as e:
        print(f"Error in find_direct_video_sources: {e}")
        return None

def find_streaming_patterns(url: str, patterns: List[str] = None) -> Optional[str]:
    """Efficient streaming pattern finder using known patterns"""
    if patterns is None:
        patterns = [
            r'(https?://[^\s<>"]+?\.(?:m3u8|mpd)(?:\?[^\s<>"]*)?)',
            r'streamUrl[\s]*[=:][\s]*[\'"]([^\'"]+)[\'"]',
            r'videoUrl[\s]*[=:][\s]*[\'"]([^\'"]+)[\'"]',
        ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers)
    
    for pattern in patterns:
        matches = re.findall(pattern, response.text, re.IGNORECASE)
        for match in matches:
            url_to_test = match if isinstance(match, str) else match[0]
            try:
                response = requests.head(url_to_test, timeout=5)
                if response.status_code == 200:
                    return url_to_test
            except:
                continue
    return None

def find_network_stream_with_button(url: str, button_selector: str = None, 
                                  wait_time: int = 2000) -> Optional[str]:
    """Efficient network stream capture using specific button"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        media_urls = set()
        
        def handle_response(response):
            url = response.url
            content_type = response.headers.get('content-type', '').lower()
            
            media_extensions = ('.m3u8', '.mpd', '.mp4', '.ts', '.webm')
            media_types = ('video/', 'application/x-mpegurl', 'application/vnd.apple.mpegurl', 
                         'application/dash+xml')
            
            if (any(url.lower().endswith(ext) for ext in media_extensions) or
                any(media_type in content_type for media_type in media_types)):
                media_urls.add(url)
        
        page.on("response", handle_response)
        page.goto(url, wait_until="networkidle")
        
        if button_selector:
            try:
                element = page.locator(button_selector)
                if element.count() > 0:
                    element.first.wait_for(state="visible", timeout=5000)
                    element.first.click()
                    page.wait_for_timeout(wait_time)
            except Exception as e:
                print(f"Button click failed: {e}")
        
        return next(iter(media_urls)) if media_urls else None

def find_network_stream(url: str) -> Optional[str]:
    """Efficient network stream capture"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        media_urls = set()
        
        def handle_response(response):
            url = response.url
            content_type = response.headers.get('content-type', '').lower()
            
            media_extensions = ('.m3u8', '.mpd', '.mp4', '.ts', '.webm')
            media_types = ('video/', 'application/x-mpegurl', 'application/vnd.apple.mpegurl', 
                         'application/dash+xml')
            
            if (any(url.lower().endswith(ext) for ext in media_extensions) or
                any(media_type in content_type for media_type in media_types)):
                media_urls.add(url)
        
        page.on("response", handle_response)
        page.goto(url, wait_until="networkidle")
        
        return next(iter(media_urls)) if media_urls else None

def check_download_options(url: str) -> List[Dict[str, Any]]:
    """Returns list of working download recipes, sorted by efficiency and reliability"""
    recipes = []
    
    # 1. Try yt-dlp (usually most reliable if supported)
    start_time = time.time()
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'best',
            'ignore_no_formats_error': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                recipes.append({
                    'recipe': DownloadRecipe(
                        method_name='yt-dlp',
                        url_found=info.get('url', ''),
                        extraction_function=lambda u: yt_dlp.YoutubeDL({'format': 'best'}).extract_info(u, download=False)['url'],
                        parameters={'format': 'best'},
                        estimated_time=time.time() - start_time,
                        priority=1  # Highest priority
                    ),
                    'example_code': """
def get_video_url(url: str) -> str:
    with yt_dlp.YoutubeDL({'format': 'best'}) as ydl:
        return ydl.extract_info(url, download=False)['url']
"""
                })
    except Exception as e:
        print(f"yt-dlp check failed: {e}")

    # 2. Check direct video sources in HTML
    start_time = time.time()
    try:
        selectors = [
            'video', 'source', 'a', 'link',
            '[type*="video"]',
            '[src*=".mp4"], [src*=".m3u8"], [src*=".mpd"]',
            '[href*=".mp4"], [href*=".m3u8"], [href*=".mpd"]',
        ]
        media_extensions = [
            '.mp4', '.m4v', '.m4s',
            '.m3u8', '.m3u',
            '.mpd',
            '.webm', '.mkv',
            '.ts',
            '.mov', '.avi',
        ]
        direct_url = find_direct_video_sources(url, selectors, media_extensions)
        if direct_url:
            recipes.append({
                'recipe': DownloadRecipe(
                    method_name='direct_html',
                    url_found=direct_url,
                    extraction_function=find_direct_video_sources,
                    parameters={
                        'selectors': selectors,
                        'media_extensions': media_extensions
                    },
                    estimated_time=time.time() - start_time,
                    priority=2
                ),
                'example_code': """
def get_video_url(url: str, selectors: List[str], media_extensions: List[str]) -> Optional[str]:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check all potential video sources
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            for attr in ['src', 'href', 'data-src', 'data-video']:
                if value := element.get(attr):
                    url = urljoin(url, value)
                    if any(url.lower().endswith(ext) for ext in media_extensions):
                        try:
                            if requests.head(url, timeout=5).status_code == 200:
                                return url
                        except:
                            continue
    return None
"""
            })
    except Exception as e:
        print(f"Direct HTML check failed: {e}")

    # 3. Check streaming patterns
    start_time = time.time()
    try:
        streaming_patterns = [
            r'(https?://[^\s<>"]+?/vod/_definst_/(?:mpflv):[^\s<>"]+?\.(?:mp4|m3u8))',
            r'(https?://[^\s<>"]+?/(?:playlist|manifest)\.(?:m3u8|mpd))',
            r'(https?://[^\s<>"]+?\.(?:m3u8|mpd)(?:\?[^\s<>"]*)?)',
            r'streamUrl[\s]*[=:][\s]*[\'"]([^\'"]+)[\'"]',
            r'videoUrl[\s]*[=:][\s]*[\'"]([^\'"]+)[\'"]',
            r'(https?://[^\s<>"]+?/\d{4}/\d{2}/\d{2}/[^\s<>"]+?\.(?:mp4|m3u8))',
        ]
        stream_url = find_streaming_patterns(url, streaming_patterns)
        if stream_url:
            recipes.append({
                'recipe': DownloadRecipe(
                    method_name='streaming_pattern',
                    url_found=stream_url,
                    extraction_function=find_streaming_patterns,
                    parameters={'patterns': streaming_patterns},
                    estimated_time=time.time() - start_time,
                    priority=3
                ),
                'example_code': """
def get_video_url(url: str, patterns: List[str]) -> str:
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    for pattern in patterns:
        if matches := re.findall(pattern, response.text, re.IGNORECASE):
            url_to_test = matches[0] if isinstance(matches[0], str) else matches[0][0]
            if requests.head(url_to_test, timeout=5).status_code == 200:
                return url_to_test
    return None
"""
            })
    except Exception as e:
        print(f"Streaming pattern check failed: {e}")

    # 4. Try network stream capture with button clicks
    start_time = time.time()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            media_urls = set()
            
            def handle_response(response):
                url = response.url
                content_type = response.headers.get('content-type', '').lower()
                if any(ext in url.lower() for ext in ['.m3u8', '.mpd', '.mp4', '.ts']):
                    media_urls.add(url)
            
            page.on("response", handle_response)
            page.goto(url, wait_until="networkidle")
            
            play_button_selectors = [
                '[aria-label*="play" i]',
                '[role="button"][aria-label*="play" i]',
                ':is(button, div, span):has-text("Play")',
                '[class*="play" i]',
                '[class*="video" i][class*="play" i]',
                'button:has(> svg)',
                '[role="button"]:has(> svg)',
                'video',
            ]
            
            for selector in play_button_selectors:
                try:
                    element = page.locator(selector)
                    if element.count() > 0 and element.first.is_visible():
                        element.first.click()
                        page.wait_for_timeout(2000)
                        
                        if media_urls:  # If we found a stream URL after clicking
                            stream_url = next(iter(media_urls))
                            recipes.append({
                                'recipe': DownloadRecipe(
                                    method_name='network_stream_with_button',
                                    url_found=stream_url,
                                    extraction_function=find_network_stream_with_button,
                                    parameters={
                                        'button_selector': selector,
                                        'wait_time': 2000
                                    },
                                    estimated_time=time.time() - start_time,
                                    priority=4
                                ),
                                'example_code': f"""
def get_video_url(url: str, button_selector: str = "{selector}") -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        media_urls = set()
        
        def handle_response(response):
            if any(ext in response.url.lower() for ext in ['.m3u8', '.mpd', '.mp4']):
                media_urls.add(response.url)
        
        page.on("response", handle_response)
        page.goto(url, wait_until="networkidle")
        page.locator(button_selector).first.click()
        page.wait_for_timeout(2000)
        return next(iter(media_urls))
"""
                            })
                            break
                except Exception as e:
                    continue
            
            browser.close()
    except Exception as e:
        print(f"Network stream check failed: {e}")

    # 5. Try network stream capture
    start_time = time.time()
    try:
        stream_url = find_network_stream(url)
        if stream_url:
            recipes.append({
                'recipe': DownloadRecipe(
                    method_name='network_stream',
                    url_found=stream_url,
                    extraction_function=find_network_stream,
                    parameters={},
                    estimated_time=time.time() - start_time,
                    priority=5
                ),
                'example_code': """
def get_video_url(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        media_urls = set()
        
        def handle_response(response):
            url = response.url
            if any(ext in url.lower() for ext in ['.m3u8', '.mpd', '.mp4', '.ts']):
                media_urls.add(url)
        
        page.on("response", handle_response)
        page.goto(url, wait_until="networkidle")
        
        return next(iter(media_urls)) if media_urls else None
"""
            })
    except Exception as e:
        print(f"Network stream check failed: {e}")

    # Sort recipes by priority first, then by estimated_time
    return sorted(recipes, key=lambda x: (x['recipe'].priority, x['recipe'].estimated_time))

if __name__ == "__main__":
    url = "https://www.stortinget.no/no/Hva-skjer-pa-Stortinget/videoarkiv/Arkiv-TV-sendinger/?meid=10764&del=1&rtid=095501&msid=299"
    recipes = check_download_options(url)
    
    print(f"Found {len(recipes)} working methods:\n")
    
    for i, recipe in enumerate(recipes, 1):
        print(f"\nMethod {i}: {recipe['recipe'].method_name}")
        print(f"Priority: {recipe['recipe'].priority}")
        print(f"Estimated time: {recipe['recipe'].estimated_time:.2f}s")
        print(f"Example URL found: {recipe['recipe'].url_found}")
        print(f"Parameters to use: {recipe['recipe'].parameters}")
        print("\nExample code to use:")
        print(recipe['example_code'])
        print("-" * 80)