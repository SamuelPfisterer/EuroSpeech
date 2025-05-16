import requests
from bs4 import BeautifulSoup
import m3u8
from datetime import datetime, timedelta
import re
import concurrent.futures
from urllib.parse import urlparse, parse_qs

def extract_video_id(url):
    """Extract video ID from ft.dk URL"""
    return url.split('/')[-1].replace('.aspx', '')

def extract_date_from_page(url):
    """Try to extract the date from the webpage"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for date patterns in the page
        date_patterns = [
            r'(\d{2}-\d{2}-\d{4})',  # DD-MM-YYYY
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, response.text)
            if matches:
                try:
                    # Try DD-MM-YYYY first
                    return datetime.strptime(matches[0], '%d-%m-%Y')
                except ValueError:
                    try:
                        # Try YYYY-MM-DD
                        return datetime.strptime(matches[0], '%Y-%m-%d')
                    except ValueError:
                        continue
        
        return None
    except Exception as e:
        print(f"Error extracting date: {str(e)}")
        return None

def verify_m3u8_url(url):
    """Verify if an m3u8 URL is accessible and valid"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            try:
                m3u8_obj = m3u8.loads(response.text)
                if m3u8_obj.data.get('segments') or m3u8_obj.playlists:
                    return True, "Valid m3u8 playlist", response.text
                return False, "No segments found in playlist", None
            except Exception as e:
                return False, f"Invalid m3u8 format: {str(e)}", None
        else:
            return False, f"HTTP {response.status_code}", None
            
    except Exception as e:
        return False, f"Error: {str(e)}", None

def generate_test_urls(video_id, date):
    """Generate possible m3u8 URLs for testing"""
    urls = []
    
    # Format the date in different ways
    formatted_date = date.strftime('%Y_%m_%d')
    year = date.strftime('%Y')
    
    # Base URL pattern
    base_url = "https://ftlive.streaming.ft.dk/vod/_definst_/mp4:"
    
    # Generate variations
    variations = [
        f"{base_url}{year}/{formatted_date}_13_00_F_{video_id}_h264.mp4/playlist.m3u8",
        f"{base_url}{year}/{formatted_date}_14_00_F_{video_id}_h264.mp4/playlist.m3u8",
        f"{base_url}{year}/{formatted_date}_15_00_F_{video_id}_h264.mp4/playlist.m3u8",
    ]
    
    return variations

def test_ft_video(url):
    """Test a specific ft.dk video URL"""
    print(f"\nTesting URL: {url}")
    
    video_id = extract_video_id(url)
    date = extract_date_from_page(url)
    
    if not date:
        print(f"Could not extract date for video {video_id}")
        return None
    
    results = []
    test_dates = [
        date,
        date - timedelta(days=1),
        date + timedelta(days=1)
    ]
    
    for test_date in test_dates:
        possible_urls = generate_test_urls(video_id, test_date)
        
        for test_url in possible_urls:
            print(f"Testing: {test_url}")
            is_valid, message, content = verify_m3u8_url(test_url)
            
            if is_valid:
                result = {
                    'original_url': url,
                    'video_id': video_id,
                    'date': test_date.strftime('%Y-%m-%d'),
                    'stream_url': test_url,
                    'valid': True,
                    'message': message,
                    'content': content
                }
                results.append(result)
                print(f"✓ Valid stream found!")
                return result
    
    print(f"✗ No valid stream found for video {video_id}")
    return None

def test_multiple_videos(urls):
    """Test multiple ft.dk video URLs"""
    results = []
    
    for url in urls:
        result = test_ft_video(url)
        if result:
            results.append(result)
    
    return results

if __name__ == "__main__":
    # Test URLs
    test_urls = [
        "https://www.ft.dk/aktuelt/webtv/video/20101/salen/108.aspx",
        "https://www.ft.dk/aktuelt/webtv/video/20101/salen/107.aspx",
        "https://www.ft.dk/aktuelt/webtv/video/20101/salen/106.aspx",
        "https://www.ft.dk/aktuelt/webtv/video/20101/salen/100.aspx"
    ]
    
    print("Starting tests...")
    results = test_multiple_videos(test_urls)
    
    print("\nSummary of results:")
    if results:
        for result in results:
            print(f"\nOriginal URL: {result['original_url']}")
            print(f"Video ID: {result['video_id']}")
            print(f"Date: {result['date']}")
            print(f"Stream URL: {result['stream_url']}")
            print(f"First few lines of m3u8 content:")
            content_preview = '\n'.join(result['content'].split('\n')[:5])
            print(content_preview)
    else:
        print("No valid streams found")