from playwright.async_api import async_playwright
import asyncio
import time
import random
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import math
import re

# Test sessions to use
TEST_SESSIONS = [
    {
        'date': '31 OCTOBRE 2024',
        'title': '2ème séance : Restaurer un système de retraite plus juste (suite) ; Expulsion des étrangers constituant une menace grave...',
        'link': 'https://videos.assemblee-nationale.fr/video.15698049_672389e79d4de.2eme-seance--restaurer-un-systeme-de-retraite-plus-juste-suite--expulsion-des-etrangers-constitu-31-octobre-2024',
        'raw_data_title': '<span class=\'date\'><span class=\'jour\'>31</span><span class=\'mois\'>octobre</span><span class=\'annee\'>2024</span></span>2ème séance : Restaurer un système de retraite plus juste (suite) ; Expulsion des étrangers constituant une menace grave pour l\'ordre public ; Réduire les contraintes énergétiques pesant sur l\'offre locative'
    },
    {
        'date': '4 JUIN 2024',
        'title': '1ère séance : Questions au Gouvernement ; Accompagnement des malades et fin de vie (suite)',
        'link': 'https://videos.assemblee-nationale.fr/video.15353351_665f0c4508e20.1ere-seance--questions-au-gouvernement--accompagnement-des-malades-et-fin-de-vie-suite-4-juin-2024',
        'raw_data_title': '<span class=\'date\'><span class=\'jour\'>4</span><span class=\'mois\'>juin</span><span class=\'annee\'>2024</span></span>1ère séance : Questions au Gouvernement ; Accompagnement des malades et fin de vie (suite)'
    },
    {
        'date': '14 MARS 2024',
        'title': '1ère séance : Garantir le versement des pensions alimentaires aux enfants majeurs (PLEC) ; Réduire l\'impact environnemen...',
        'link': 'https://videos.assemblee-nationale.fr/video.14817651_65f2ab0326a4c.1ere-seance--garantir-le-versement-des-pensions-alimentaires-aux-enfants-majeurs-plec--reduire-l-14-mars-2024',
        'raw_data_title': '<span class=\'date\'><span class=\'jour\'>14</span><span class=\'mois\'>mars</span><span class=\'annee\'>2024</span></span>1ère séance : Garantir le versement des pensions alimentaires aux enfants majeurs (PLEC) ; Réduire l\'impact environnemental de l\'industrie textile'
    }
]

async def random_delay(min_seconds=1, max_seconds=3):
    """Add random delay between requests to mimic human behavior"""
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))

async def setup_stealth_browser(playwright):
    """Setup browser with stealth configurations"""
    browser = await playwright.chromium.launch(
        headless=False,  # Run in non-headless mode
        slow_mo=50,  # Add slight delays to see what's happening
        args=['--use-fake-ui-for-media-stream']  # Enable media handling
    )
    
    # Create context with media handling capabilities
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        java_script_enabled=True,
        bypass_csp=True,
        ignore_https_errors=True,  # Handle HTTPS issues
        extra_http_headers={
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': '*/*',  # Accept all content types
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Range': 'bytes=0-',  # Support range requests for media
        }
    )
    
    # Enable request interception
    await context.route("**/*", lambda route: route.continue_())
    
    return browser, context

async def extract_media_info(page) -> Dict:
    """Extract media information from page source and network requests"""
    try:
        print("\nAnalyzing page source and network requests...")
        
        # Initialize variables for media URLs
        video_url = None
        subtitle_url = None
        
        # Wait for page load
        await page.wait_for_load_state('networkidle')
        await random_delay(2, 3)
        
        # Define selectors and media extensions
        video_selectors = [
            'video', 
            'source', 
            'a', 
            'link', 
            '[type*="video"]',
            '[src*=".mp4"]',
            '[src*=".m3u8"]',
            '[src*=".mpd"]',
            '[href*=".mp4"]',
            '[href*=".m3u8"]',
            '[href*=".mpd"]'
        ]
        
        subtitle_selectors = [
            'track',
            '[kind="subtitles"]',
            '[type*="vtt"]',
            '[src*=".vtt"]',
            '[href*=".vtt"]',
            '[src*="caption"]',
            '[src*="subtitle"]'
        ]
        
        video_extensions = [
            '.mp4', '.m4v', '.m4s', '.m3u8', '.m3u', 
            '.mpd', '.webm', '.mkv', '.ts', '.mov', '.avi'
        ]
        
        subtitle_extensions = ['.vtt', '.srt', '.ttml', '.dfxp']
        
        # Get page content
        content = await page.content()
        
        # Save page content for debugging
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_dir = Path("output/debug_content")
        debug_dir.mkdir(parents=True, exist_ok=True)
        with open(debug_dir / f"page_source_{timestamp}.html", 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Check all potential video sources
        print("Searching for video elements...")
        for selector in video_selectors:
            elements = await page.query_selector_all(selector)
            for element in elements:
                for attr in ['src', 'href', 'data-src', 'data-video']:
                    try:
                        value = await element.get_attribute(attr)
                        if value:
                            # Handle relative URLs
                            if value.startswith('//'):
                                value = f"https:{value}"
                            elif value.startswith('/'):
                                value = f"https://videos.assemblee-nationale.fr{value}"
                            elif not value.startswith('http'):
                                value = f"https://videos.assemblee-nationale.fr/{value}"
                            
                            # Check if URL has valid media extension
                            if any(value.lower().endswith(ext) for ext in video_extensions):
                                print(f"Found potential video URL: {value}")
                                video_url = value
                                break
                    except Exception as e:
                        continue
                if video_url:
                    break
            if video_url:
                break
        
        # If no video URL found in elements, try regex patterns
        if not video_url:
            video_patterns = [
                r'https?://[^"\']*?\.(?:mp4|m3u8|mpd)',
                r'//[^"\']*?\.(?:mp4|m3u8|mpd)',
                r'/Datas/[^"\']*?\.(?:mp4|m3u8|mpd)',
                r'anorigin\.vodalys\.com/[^"\']*?\.mp4',
                r'videos-an\.vodalys\.com/[^"\']*?\.(?:mp4|m3u8)'
            ]
            
            for pattern in video_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if match.startswith('//'):
                            match = f"https:{match}"
                        elif match.startswith('/'):
                            match = f"https://videos.assemblee-nationale.fr{match}"
                        print(f"Found video URL through regex: {match}")
                        video_url = match
                        break
                    if video_url:
                        break
        
        # Check all potential subtitle sources
        print("Searching for subtitle elements...")
        for selector in subtitle_selectors:
            elements = await page.query_selector_all(selector)
            for element in elements:
                for attr in ['src', 'href', 'data-src']:
                    try:
                        value = await element.get_attribute(attr)
                        if value:
                            # Handle relative URLs
                            if value.startswith('//'):
                                value = f"https:{value}"
                            elif value.startswith('/'):
                                value = f"https://videos.assemblee-nationale.fr{value}"
                            elif not value.startswith('http'):
                                value = f"https://videos.assemblee-nationale.fr/{value}"
                            
                            # Check if URL has valid subtitle extension
                            if any(value.lower().endswith(ext) for ext in subtitle_extensions):
                                print(f"Found potential subtitle URL: {value}")
                                subtitle_url = value
                                break
                    except Exception as e:
                        continue
                if subtitle_url:
                    break
            if subtitle_url:
                break
        
        # If no subtitle URL found in elements, try regex patterns
        if not subtitle_url:
            subtitle_patterns = [
                r'https?://[^"\']*?\.vtt',
                r'//[^"\']*?\.vtt',
                r'/Datas/[^"\']*?\.vtt',
                r'track\s*src=["\']([^"\']*?\.vtt)["\']',
                r'subtitle:\s*["\']([^"\']*?\.vtt)["\']',
                r'captions:\s*["\']([^"\']*?\.vtt)["\']',
                r'vodalys\.com/[^"\']*?\.vtt'
            ]
            
            for pattern in subtitle_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):  # Handle capture groups
                            match = match[0]
                        if match.startswith('//'):
                            match = f"https:{match}"
                        elif match.startswith('/'):
                            match = f"https://videos.assemblee-nationale.fr{match}"
                        print(f"Found subtitle URL through regex: {match}")
                        subtitle_url = match
                        break
                    if subtitle_url:
                        break
        
        # Get transcript link
        transcript_link = None
        try:
            transcript_button = await page.query_selector('#module_player_report')
            if transcript_button:
                print("Found transcript button, attempting to get link...")
                transcript_page = await page.context.new_page()
                original_url = page.url
                await transcript_button.click()
                await random_delay(1, 2)
                pages = page.context.pages
                for p in pages:
                    if p.url != original_url and 'assemblee-nationale.fr' in p.url:
                        transcript_link = p.url
                        await p.close()
                        break
                
                if transcript_link:
                    print(f"Successfully found transcript link: {transcript_link}")
                else:
                    print("No transcript link found after clicking")
            else:
                print("No transcript button found on page")
                
        except Exception as e:
            print(f"Error getting transcript link: {e}")
        
        print(f"Found video URL: {video_url}")
        print(f"Found subtitle URL: {subtitle_url}")
        print(f"Found transcript link: {transcript_link}")
        
        return {
            'video_link': video_url,
            'subtitle_link': subtitle_url,
            'transcript_link': transcript_link,
            'player_type': 'html5'
        }
    
    except Exception as e:
        print(f"Error extracting media info: {e}")
        return {
            'video_link': None,
            'subtitle_link': None,
            'transcript_link': None,
            'player_type': 'error'
        }

def save_results(sessions: List[Dict], output_file: Path):
    """Save the scraped data to a CSV file"""
    write_headers = not output_file.exists()
    
    with open(output_file, mode='a', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['date', 'title', 'session_link', 'video_link', 'subtitle_link', 
                     'transcript_link', 'player_type', 'raw_data_title']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if write_headers:
            writer.writeheader()
        
        for session in sessions:
            writer.writerow(session)

async def process_session(page, session: Dict, output_file: Path) -> None:
    """Process a single session page"""
    try:
        print(f"\n{'='*80}")
        print(f"Processing session: {session['title'][:100]}...")
        print(f"URL: {session['link']}")
        print(f"Date: {session['date']}")
        
        await page.goto(session['link'], wait_until='networkidle')
        await random_delay()
        
        # Extract media information
        media_info = await extract_media_info(page)
        
        # Combine session info with media info
        result = {
            'date': session['date'],
            'title': session['title'],
            'session_link': session['link'],
            'video_link': media_info['video_link'],
            'subtitle_link': media_info['subtitle_link'],
            'transcript_link': media_info['transcript_link'],
            'player_type': media_info['player_type'],
            'raw_data_title': session.get('raw_data_title', '')
        }
        
        # Print detailed results for testing
        print(f"\nResults for session {session['date']}:")
        print(f"Player Type: {media_info['player_type']}")
        print(f"Video Link: {media_info['video_link']}")
        print(f"Subtitle Link: {media_info['subtitle_link']}")
        print(f"Transcript Link: {media_info['transcript_link']}")
        print("-" * 80)
        
        # Save individual result
        save_results([result], output_file)
        
    except Exception as e:
        print(f"Error processing session {session['link']}: {e}")

async def process_session_batch(context, sessions: List[Dict], output_file: Path) -> None:
    """Process a batch of sessions concurrently"""
    pages = await asyncio.gather(*(context.new_page() for _ in sessions))
    await asyncio.gather(*(process_session(page, session, output_file) 
                         for page, session in zip(pages, sessions)))
    await asyncio.gather(*(page.close() for page in pages))

async def scrape_media_links():
    """Main function to scrape media links"""
    async with async_playwright() as playwright:
        browser, context = await setup_stealth_browser(playwright)
        
        # Create output file
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'media_links_{timestamp}.csv'
        
        # Use test sessions
        sessions = TEST_SESSIONS
        total_sessions = len(sessions)
        print(f"\nTesting with {total_sessions} specific sessions")
        
        batch_size = 1  # Process one session at a time for better debugging
        
        # Process sessions in batches
        for batch_start in range(0, total_sessions, batch_size):
            batch_end = min(batch_start + batch_size, total_sessions)
            batch = sessions[batch_start:batch_end]
            
            print(f"\nProcessing batch {batch_start+1}-{batch_end} of {total_sessions}")
            await process_session_batch(context, batch, output_file)
            
            # Add a small delay between batches
            await random_delay(2, 4)
        
        await browser.close()
        print(f"\nScraping completed. Results saved to: {output_file}")

def main():
    """Entry point with asyncio handling"""
    asyncio.run(scrape_media_links())

if __name__ == "__main__":
    main()
